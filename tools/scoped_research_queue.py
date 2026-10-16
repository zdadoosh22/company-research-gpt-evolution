"""Explicit scoped jobs with durable authorization and a shared case call ceiling.

This is the existing SQLite queue and OS worker lock. No scheduler, due-job
selection, automatic retry, or timer dispatch exists. Every attempted dispatch
is charged before adapter entry, including failure or uncertain completion.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

try:
    from .scoped_research_adapter import MODELS, run_scoped_job, validate_package, validate_output, needs_continuation, _no_credentials
except ImportError:
    from scoped_research_adapter import MODELS, run_scoped_job, validate_package, validate_output, needs_continuation, _no_credentials


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def package_sha256(job):
    return hashlib.sha256(_json(job).encode()).hexdigest()


def scope_sha256(job):
    """Freeze every package field except a future result target binding."""
    return package_sha256({key: value for key, value in job.items() if key != "target"})


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return result


def _ident(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", value):
        raise ValueError("Invalid record identity")


class QueueBusy(RuntimeError):
    pass


class ScopedQueue:
    def __init__(self, project_root):
        self.root = Path(project_root).resolve()
        self.folder = (self.root / "state/scoped-research").resolve()
        if not self.folder.is_relative_to(self.root / "state"):
            raise ValueError("Queue path escapes isolated state")
        self.folder.mkdir(parents=True, exist_ok=True)
        self.database = self.folder / "queue.sqlite"
        if self.database.is_symlink() or (self.folder / "worker.lock").is_symlink():
            raise ValueError("Queue files cannot be symlinks")
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_jobs (
                job_id TEXT PRIMARY KEY, package TEXT NOT NULL, package_sha256 TEXT NOT NULL,
                role TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0, retry_not_before TEXT,
                metadata_path TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            db.execute("CREATE TABLE IF NOT EXISTS scoped_queue_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS scoped_legacy_jobs (job_id TEXT PRIMARY KEY, original_record TEXT NOT NULL, migrated_at TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_cases (
                case_id TEXT PRIMARY KEY, batch_id TEXT UNIQUE NOT NULL, call_limit INTEGER NOT NULL,
                legacy_attempts INTEGER NOT NULL, created_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_authorizations (
                batch_id TEXT NOT NULL, version INTEGER NOT NULL, case_id TEXT NOT NULL,
                manifest TEXT NOT NULL, sha256 TEXT NOT NULL, recorded_at TEXT NOT NULL,
                PRIMARY KEY(batch_id,version))""")
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_job_bindings (
                job_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, case_id TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_dispatches (
                dispatch_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, case_id TEXT NOT NULL,
                job_id TEXT NOT NULL, attempt INTEGER NOT NULL, authorization_version INTEGER NOT NULL,
                authorization_sha256 TEXT NOT NULL, package_sha256 TEXT NOT NULL,
                model TEXT NOT NULL, role TEXT NOT NULL, stage TEXT NOT NULL, retry_decision_id TEXT,
                consumed_at TEXT NOT NULL, invocation_claimed_at TEXT, status TEXT NOT NULL,
                reason TEXT NOT NULL, metadata_path TEXT, completed_at TEXT,
                UNIQUE(job_id,attempt))""")
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_retry_decisions (
                decision_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, job_id TEXT NOT NULL,
                prior_attempt INTEGER NOT NULL, rationale TEXT NOT NULL, provenance_refs TEXT NOT NULL,
                recorded_at TEXT NOT NULL, dispatch_id TEXT)""")
            if not db.execute("SELECT 1 FROM scoped_queue_migrations WHERE version=2").fetchone():
                for row in db.execute("SELECT * FROM scoped_jobs").fetchall():
                    db.execute("INSERT INTO scoped_legacy_jobs VALUES (?,?,?)", (row["job_id"], _json(dict(row)), _now()))
                db.execute("""UPDATE scoped_jobs SET status='needs-retry-decision',
                    reason='legacy-deferred-requires-explicit-decision',retry_not_before=NULL,updated_at=?
                    WHERE status='deferred'""", (_now(),))
                db.execute("INSERT INTO scoped_queue_migrations VALUES (2,?)", (_now(),))

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def _worker_lock(self):
        with (self.folder / "worker.lock").open("a+b") as handle:
            try:
                if handle.seek(0, 2) == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise QueueBusy("An explicit scoped job is already running") from exc
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def enqueue(self, job):
        validate_package(self.root, job)
        package, digest, stamp = _json(job), package_sha256(job), _now()
        with self._db() as db:
            previous = db.execute("SELECT package_sha256 FROM scoped_jobs WHERE job_id=?", (job["job_id"],)).fetchone()
            if previous:
                if previous[0] != digest:
                    raise ValueError("Job ID already binds a different frozen package")
                return {"job_id": job["job_id"], "enqueued": False, "reason": "already-recorded"}
            db.execute("INSERT INTO scoped_jobs (job_id,package,package_sha256,role,status,reason,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                       (job["job_id"], package, digest, job["role"], "queued", "explicitly-enqueued", stamp, stamp))
        return {"job_id": job["job_id"], "enqueued": True, "reason": "explicitly-enqueued"}

    def _authorization(self, db, batch_id):
        row = db.execute("SELECT * FROM scoped_authorizations WHERE batch_id=? ORDER BY version DESC LIMIT 1", (batch_id,)).fetchone()
        if row is None or package_sha256(json.loads(row["manifest"])) != row["sha256"]:
            raise ValueError("Missing or invalid batch authorization")
        return row, json.loads(row["manifest"])

    def _remaining(self, db, case_id):
        case = db.execute("SELECT * FROM scoped_cases WHERE case_id=?", (case_id,)).fetchone()
        used = db.execute("SELECT COUNT(*) FROM scoped_dispatches WHERE case_id=?", (case_id,)).fetchone()[0]
        return case["call_limit"] - case["legacy_attempts"] - used

    def authorize_batch(self, manifest):
        """Append a version; only previously unbound named packages may be bound.

        Exactly one batch per case prevents budget reset under another batch ID.
        A pending review/correction target must be a validated predecessor output.
        """
        _no_credentials(manifest)
        required = {"schema_version", "batch_id", "case_id", "version", "created_at", "expires_at", "purpose", "provenance_refs", "call_limit", "permitted_continuation", "jobs"}
        if not isinstance(manifest, dict) or set(manifest) != required or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
            raise ValueError("Invalid batch authorization schema")
        for name in ("batch_id", "case_id"):
            _ident(manifest[name])
        if type(manifest["version"]) is not int or manifest["version"] < 1 or type(manifest["call_limit"]) is not int or not 1 <= manifest["call_limit"] <= 4:
            raise ValueError("Batch version/call ceiling invalid")
        created, expires = _stamp(manifest["created_at"]), _stamp(manifest["expires_at"])
        if created > datetime.now(timezone.utc) or expires <= datetime.now(timezone.utc) or expires <= created:
            raise ValueError("Authorization is future-dated or expired")
        if not isinstance(manifest["purpose"], str) or not manifest["purpose"].strip():
            raise ValueError("Authorization purpose required")
        for field in ("provenance_refs", "permitted_continuation"):
            if not isinstance(manifest[field], list) or any(not isinstance(x, str) or not x.strip() for x in manifest[field]):
                raise ValueError("Invalid authorization provenance/continuation")
        if not manifest["provenance_refs"] or not set(manifest["permitted_continuation"]) <= {"explicit-retry", "material-correction", "material-recheck"}:
            raise ValueError("Explicit provenance and permitted continuation required")
        jobs = manifest["jobs"]
        if not isinstance(jobs, list) or not 1 <= len(jobs) <= 4:
            raise ValueError("One to four named jobs required")
        seen, stages = set(), set()
        for spec in jobs:
            if not isinstance(spec, dict) or set(spec) != {"job_id", "stage", "role", "model", "scope_sha256", "package_sha256", "target_from_job_id"}:
                raise ValueError("Invalid named job authorization")
            _ident(spec["job_id"])
            role = {"analysis": "analysis", "review": "review", "correction": "analysis", "recheck": "review"}.get(spec["stage"])
            if spec["job_id"] in seen or spec["stage"] in stages or role is None or spec["role"] != role or spec["model"] != MODELS[role]:
                raise ValueError("Duplicate scope, unavailable role, or model substitution")
            seen.add(spec["job_id"])
            stages.add(spec["stage"])
            if not isinstance(spec["scope_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", spec["scope_sha256"]):
                raise ValueError("Frozen job scope required")
            digest = spec["package_sha256"]
            if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise ValueError("Invalid package binding")
            predecessor = spec["target_from_job_id"]
            if spec["stage"] == "analysis":
                if predecessor is not None or digest is None:
                    raise ValueError("Initial analysis must bind its full package")
            elif predecessor is None or predecessor == spec["job_id"]:
                raise ValueError("Review/continuation requires a named predecessor")
            if spec["stage"] in {"correction", "recheck"} and "material-" + spec["stage"] not in manifest["permitted_continuation"]:
                raise ValueError("Continuation stage is not permitted")
        by_id = {spec["job_id"]: spec for spec in jobs}
        expected = {"review": "analysis", "correction": "review", "recheck": "correction"}
        for spec in jobs:
            if spec["stage"] != "analysis" and by_id.get(spec["target_from_job_id"], {}).get("stage") != expected[spec["stage"]]:
                raise ValueError("Invalid stage dependency")
        digest = package_sha256(manifest)
        with self._db() as db:
            existing = db.execute("SELECT * FROM scoped_authorizations WHERE batch_id=? ORDER BY version DESC LIMIT 1", (manifest["batch_id"],)).fetchone()
            same = db.execute("SELECT sha256 FROM scoped_authorizations WHERE batch_id=? AND version=?", (manifest["batch_id"], manifest["version"])).fetchone()
            if same:
                if same[0] != digest:
                    raise ValueError("Authorization version already binds another manifest")
                return {"batch_id": manifest["batch_id"], "version": manifest["version"], "recorded": False, "sha256": digest}
            if existing:
                previous = json.loads(existing["manifest"])
                if manifest["version"] != previous["version"] + 1:
                    raise ValueError("Authorization versions must be consecutive")
                # Versions bind missing targets, never widen scope, expiry, or budget.
                old_fixed = {k: v for k, v in previous.items() if k not in {"version", "jobs"}}
                new_fixed = {k: v for k, v in manifest.items() if k not in {"version", "jobs"}}
                if old_fixed != new_fixed or len(previous["jobs"]) != len(jobs):
                    raise ValueError("Authorization scope or budget cannot be expanded")
                for before, after in zip(previous["jobs"], jobs):
                    if {k: v for k, v in before.items() if k != "package_sha256"} != {k: v for k, v in after.items() if k != "package_sha256"} or (before["package_sha256"] is not None and before != after):
                        raise ValueError("Named job authorization cannot change")
            else:
                if manifest["version"] != 1 or db.execute("SELECT 1 FROM scoped_cases WHERE case_id=?", (manifest["case_id"],)).fetchone():
                    raise ValueError("Case budget already exists or initial version invalid")
                legacy = 0
                for spec in jobs:
                    if db.execute("SELECT 1 FROM scoped_job_bindings WHERE job_id=?", (spec["job_id"],)).fetchone():
                        raise ValueError("Job is already scoped to another batch")
                    prior = db.execute("SELECT original_record FROM scoped_legacy_jobs WHERE job_id=?", (spec["job_id"],)).fetchone()
                    legacy += json.loads(prior[0])["attempt"] if prior else 0
                if legacy > manifest["call_limit"]:
                    raise ValueError("Historical attempts exhaust the case ceiling")
                db.execute("INSERT INTO scoped_cases VALUES (?,?,?,?,?)", (manifest["case_id"], manifest["batch_id"], manifest["call_limit"], legacy, _now()))
                for spec in jobs:
                    db.execute("INSERT INTO scoped_job_bindings VALUES (?,?,?)", (spec["job_id"], manifest["batch_id"], manifest["case_id"]))
            for spec in jobs:
                if spec["package_sha256"] is not None:
                    row = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (spec["job_id"],)).fetchone()
                    if row is None:
                        raise ValueError("Bound package must be explicitly enqueued")
                    self._validate_binding(db, row, spec)
            db.execute("INSERT INTO scoped_authorizations VALUES (?,?,?,?,?,?)", (manifest["batch_id"], manifest["version"], manifest["case_id"], _json(manifest), digest, _now()))
        return {"batch_id": manifest["batch_id"], "version": manifest["version"], "recorded": True, "sha256": digest}

    def _validate_binding(self, db, row, spec):
        job = json.loads(row["package"])
        validate_package(self.root, job)
        if package_sha256(job) != row["package_sha256"] or row["package_sha256"] != spec["package_sha256"] or scope_sha256(job) != spec["scope_sha256"] or job["role"] != spec["role"]:
            raise ValueError("Frozen package differs from authorized scope")
        if spec["target_from_job_id"]:
            previous = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (spec["target_from_job_id"],)).fetchone()
            if previous is None or previous["status"] not in {"complete", "needs-input"} or not previous["metadata_path"]:
                raise ValueError("Predecessor has no validated output")
            meta = self._checkpoint(previous, Path(previous["metadata_path"]), db=db)
            if job["target"]["sha256"] != meta["output_sha256"] or (self.root / job["target"]["path"]).resolve() != Path(meta["result_path"]).resolve():
                raise ValueError("Continuation target differs from predecessor output")
            if spec["stage"] == "correction":
                result = json.loads(Path(meta["result_path"]).read_text(encoding="utf-8"))
                if not any(f["severity"] == "material" and f["outcome"] != "resolved" for f in result["findings"]):
                    raise ValueError("Correction requires material review findings")
        return job

    def export_result(self, job_id, *, case_id):
        """Publish only a revalidated research output, never private queue state.

        Rewrite the target's path to its archived identical bytes so research
        records remain usable without the operational database. The frozen
        packet is path-independent; its hash must remain identical.
        """
        try:
            from .research_checkpoint import identifier, _safe_directory, _atomic, make_reference
            from .scoped_research_adapter import _packet, _file
        except ImportError:
            from research_checkpoint import identifier, _safe_directory, _atomic, make_reference
            from scoped_research_adapter import _packet, _file
        identifier(case_id)
        with self._db() as db:
            row = db.execute('SELECT * FROM scoped_jobs WHERE job_id=?', (job_id,)).fetchone()
            if row is None or row['status'] not in {'complete', 'needs-input'} or not row['metadata_path']:
                raise ValueError('No validated result to export')
            binding=db.execute('SELECT case_id,batch_id FROM scoped_job_bindings WHERE job_id=?',(job_id,)).fetchone()
            if binding is None or binding['case_id']!=case_id:
                raise ValueError('Export case differs from the durable authorization')
            meta = self._checkpoint(row, Path(row['metadata_path']), db=db)
            if meta.get('selected_route_completed') is not True:
                raise ValueError('No completed route output')
            job = json.loads(row['package'])
            old_packet = _packet(self.root, job)
            relative = 'monitoring/research-engine/cases/' + case_id + '/workers/' + row['package_sha256'] + '/attempt-' + str(row['attempt'])
            folder = _safe_directory(self.root, relative)

            def immutable(name, data):
                target = folder / name
                if target.exists():
                    if target.is_symlink() or target.read_bytes() != data:
                        raise ValueError('Conflicting archived worker output')
                else:
                    _atomic(target, data)
                return make_reference(self.root, relative + '/' + name)

            target_bytes=_file(self.root, job['target']).read_bytes()
            if hashlib.sha256(target_bytes).hexdigest()!=job['target']['sha256']:
                raise ValueError('Target changed during export')
            target = immutable('target.txt', target_bytes)
            job['target'] = target
            packet = _packet(self.root, job)
            if packet['sha256'] != old_packet['sha256']:
                raise ValueError('Export changed the model-visible evidence packet')
            request = immutable('job.json', _json(job).encode('utf-8') + b'\n')
            result_bytes=Path(meta['result_path']).read_bytes()
            if hashlib.sha256(result_bytes).hexdigest()!=meta['output_sha256']:
                raise ValueError('Result changed during export')
            _no_credentials(json.loads(result_bytes.decode('utf-8')))
            result = immutable('result.json', result_bytes)
            fields = {'schema_version', 'job_id', 'role', 'dispatch_id', 'status', 'reason',
                'model_requested', 'reasoning_effort', 'speed', 'authentication', 'actual_model',
                'actual_model_verification', 'models_observed', 'backend_independently_verified',
                'started_at', 'completed_at', 'selected_route_completed', 'independent_review',
                'engineering_test', 'runtime_verified_live', 'execution_outcome', 'attempt',
                'target_sha256', 'output_sha256', 'packet_sha256', 'packet_utf8_bytes',
                'prompt_sha256', 'prompt_utf8_bytes', 'original_bytes', 'usage', 'continuation'}
            public = {key: meta[key] for key in fields if key in meta}
            public.update(case_id=case_id,batch_id=binding['batch_id'],
                original_package_sha256=row['package_sha256'], archived_package_sha256=package_sha256(job))
            execution = immutable('execution.json', _json(public).encode('utf-8') + b'\n')
            packet_ref = immutable('packet.json', packet['bytes'])
            return dict(job=request, result=result, execution=execution, packet=packet_ref)

    def status(self):
        with self._db() as db:
            jobs = [dict(r) for r in db.execute("SELECT job_id,role,status,reason,attempt,retry_not_before,metadata_path,created_at,updated_at FROM scoped_jobs ORDER BY created_at,job_id")]
            cases = [dict(r) for r in db.execute("SELECT * FROM scoped_cases ORDER BY case_id")]
            for case in cases:
                case["remaining_attempts"] = self._remaining(db, case["case_id"])
                case["consumed_attempts"] = case["call_limit"] - case["remaining_attempts"]
            dispatches = [dict(r) for r in db.execute("SELECT * FROM scoped_dispatches ORDER BY consumed_at,dispatch_id")]
            decisions = [dict(r) for r in db.execute("SELECT * FROM scoped_retry_decisions ORDER BY recorded_at,decision_id")]
        return {"schema_version": 2, "mode": "explicit-run-only", "background_enabled": False, "database": str(self.database), "jobs": jobs, "cases": cases, "dispatches": dispatches, "retry_decisions": decisions}

    def _checkpoint(self, row, path, *, db, returned=None):
        root = (self.folder / "jobs" / row["package_sha256"]).resolve()
        path = path.resolve()
        if not root.is_relative_to(self.folder) or path.name != "metadata.json" or path.parent.parent != root or not path.is_relative_to(root):
            raise ValueError("Checkpoint path escapes its job")
        meta = json.loads(path.read_text(encoding="utf-8"))
        _no_credentials(meta)
        if returned is not None and meta != returned:
            raise ValueError("Returned metadata differs from checkpoint")
        if meta.get("job_id") != row["job_id"] or type(meta.get("attempt")) is not int or meta["attempt"] != row["attempt"] or not meta.get("completed_at") or Path(meta.get("metadata_path", "")).resolve() != path:
            raise ValueError("Checkpoint identity differs")
        _stamp(meta["completed_at"])
        job = json.loads(row["package"])
        if package_sha256(job) != row["package_sha256"]:
            raise ValueError("Frozen package hash differs")
        validate_package(self.root, job)
        request_path = path.parent / "request.json"
        if request_path.resolve().parent != path.parent or package_sha256(json.loads(request_path.read_text(encoding="utf-8"))) != row["package_sha256"]:
            raise ValueError("Saved request differs")
        dispatch = db.execute("SELECT * FROM scoped_dispatches WHERE job_id=? AND attempt=?", (row["job_id"], row["attempt"])).fetchone()
        if dispatch and meta.get("dispatch_id") != dispatch["dispatch_id"]:
            raise ValueError("Checkpoint dispatch differs")
        if meta.get("model_requested") != MODELS[job["role"]] or meta.get("actual_model") not in {None, MODELS[job["role"]]}:
            raise ValueError("Checkpoint model substitution")
        if meta.get("reason") == "analytical-output-validated":
            if meta.get("selected_route_completed") is not True or (dispatch and dispatch["invocation_claimed_at"] is None):
                raise ValueError("Completed output lacks a claimed route dispatch")
            result_path = Path(meta["result_path"]).resolve()
            if result_path.parent != path.parent or result_path.name != "result.json" or hashlib.sha256(result_path.read_bytes()).hexdigest() != meta["output_sha256"]:
                raise ValueError("Checkpoint result binding differs")
            result = validate_output(json.loads(result_path.read_text(encoding="utf-8")), job, self.root)
            if result["status"] != meta.get("status") or meta.get("continuation_required") != needs_continuation(result):
                raise ValueError("Checkpoint result status differs")
        elif meta.get("continuation_required") is not True:
            raise ValueError("Unvalidated completion refused")
        return meta

    def _finish(self, db, row, meta):
        if meta["reason"] == "analytical-output-validated":
            status = "needs-input" if meta["continuation_required"] else "complete"
        else:
            status = "needs-retry-decision"
        db.execute("UPDATE scoped_jobs SET status=?,reason=?,retry_not_before=NULL,metadata_path=?,updated_at=? WHERE job_id=?", (status, meta["reason"], meta["metadata_path"], _now(), row["job_id"]))
        db.execute("UPDATE scoped_dispatches SET status=?,reason=?,metadata_path=?,completed_at=? WHERE job_id=? AND attempt=?", (status, meta["reason"], meta["metadata_path"], _now(), row["job_id"], row["attempt"]))
        return status

    def _uncertain(self, db, row, reason):
        db.execute("UPDATE scoped_jobs SET status='needs-retry-decision',reason=?,retry_not_before=NULL,updated_at=? WHERE job_id=?", (reason, _now(), row["job_id"]))
        db.execute("UPDATE scoped_dispatches SET status='needs-retry-decision',reason=?,completed_at=? WHERE job_id=? AND attempt=?", (reason, _now(), row["job_id"], row["attempt"]))

    def _recover_interrupted(self, db):
        for row in db.execute("SELECT * FROM scoped_jobs WHERE status='running'").fetchall():
            valid, invalid = [], False
            root = self.folder / "jobs" / row["package_sha256"]
            for path in root.glob("*/metadata.json"):
                try:
                    candidate = json.loads(path.read_text(encoding="utf-8"))
                    if candidate.get("attempt") != row["attempt"]:
                        continue
                    valid.append(self._checkpoint(row, path, db=db))
                except (OSError, ValueError, KeyError, TypeError):
                    invalid = True
            if len(valid) == 1 and not invalid:
                self._finish(db, row, valid[0])
            else:
                self._uncertain(db, row, "recovery-checkpoint-invalid" if invalid or valid else "worker-interrupted")

    def recover(self):
        try:
            with self._worker_lock():
                with self._db() as db:
                    self._recover_interrupted(db)
            return self.status()
        except QueueBusy:
            return {"status": "busy", "reason": "another-scoped-job-running", "job_attempts_started": 0}

    def retry(self, *, job_id, batch_id, decision_id, rationale, provenance_refs):
        """Record one explicit decision; a subsequent named dispatch charges it."""
        for value in (job_id, batch_id, decision_id):
            _ident(value)
        if not isinstance(rationale, str) or not rationale.strip() or not isinstance(provenance_refs, list) or not provenance_refs or any(not isinstance(x, str) or not x.strip() for x in provenance_refs):
            raise ValueError("Retry rationale and provenance required")
        _no_credentials([rationale, provenance_refs])
        with self._db() as db:
            prior = db.execute("SELECT * FROM scoped_retry_decisions WHERE decision_id=?", (decision_id,)).fetchone()
            if prior:
                if (prior["job_id"], prior["batch_id"], prior["rationale"], prior["provenance_refs"]) != (job_id, batch_id, rationale, _json(provenance_refs)):
                    raise ValueError("Decision ID already records a different retry")
                return {"decision_id": decision_id, "recorded": False, "dispatch_id": prior["dispatch_id"]}
            _, auth = self._authorization(db, batch_id)
            if _stamp(auth["expires_at"]) <= datetime.now(timezone.utc) or "explicit-retry" not in auth["permitted_continuation"] or self._remaining(db, auth["case_id"]) <= 0:
                raise ValueError("Retry is expired, prohibited, or budget exhausted")
            if job_id not in {s["job_id"] for s in auth["jobs"]}:
                raise ValueError("Retry job outside batch scope")
            row = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None or row["status"] not in {"needs-retry-decision", "needs-input"}:
                raise ValueError("Job does not need a retry decision")
            db.execute("INSERT INTO scoped_retry_decisions VALUES (?,?,?,?,?,?,?,NULL)", (decision_id, batch_id, job_id, row["attempt"], rationale, _json(provenance_refs), _now()))
            db.execute("UPDATE scoped_jobs SET status='retry-authorized',reason='explicit-retry-decision',retry_not_before=NULL,updated_at=? WHERE job_id=?", (_now(), job_id))
        return {"decision_id": decision_id, "recorded": True, "dispatch_id": None}

    def run_one(self, *, job_id, batch_id, adapter=run_scoped_job, **adapter_kwargs):
        """Run only this named job once, under this exact durable batch."""
        _ident(job_id)
        _ident(batch_id)
        if {"state_root", "attempt", "dispatch"} & set(adapter_kwargs):
            raise ValueError("Queue owns checkpoint root, dispatch and attempt")
        try:
            with self._worker_lock():
                with self._db() as db:
                    self._recover_interrupted(db)
                    authorization, auth = self._authorization(db, batch_id)
                    spec = next((s for s in auth["jobs"] if s["job_id"] == job_id), None)
                    if spec is None:
                        raise ValueError("Selected job is outside authorized batch scope")
                    if _stamp(auth["expires_at"]) <= datetime.now(timezone.utc):
                        raise ValueError("Batch authorization expired")
                    row = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (job_id,)).fetchone()
                    if row is None:
                        raise ValueError("Selected job has not been enqueued")
                    if row["status"] not in {"queued", "retry-authorized"}:
                        return {"status": row["status"], "reason": row["reason"], "job_id": job_id, "job_attempts_started": 0}
                    if self._remaining(db, auth["case_id"]) <= 0:
                        return {"status": "blocked", "reason": "case-attempt-limit", "job_id": job_id, "job_attempts_started": 0}
                    if spec["package_sha256"] is None:
                        raise ValueError("Named job package is not yet bound")
                    try:
                        job = self._validate_binding(db, row, spec)
                    except (ValueError, OSError, KeyError, TypeError):
                        self._uncertain(db, row, "package-invalid-or-mutated")
                        return {"status": "needs-retry-decision", "reason": "package-invalid-or-mutated", "job_id": job_id, "job_attempts_started": 0}
                    decision = None
                    if row["status"] == "retry-authorized":
                        decision = db.execute("SELECT decision_id FROM scoped_retry_decisions WHERE job_id=? AND batch_id=? AND prior_attempt=? AND dispatch_id IS NULL", (job_id, batch_id, row["attempt"])).fetchone()
                        if decision is None:
                            raise ValueError("Missing explicit retry decision")
                    attempt, dispatch_id = row["attempt"] + 1, uuid4().hex
                    db.execute("""INSERT INTO scoped_dispatches (dispatch_id,batch_id,case_id,job_id,attempt,authorization_version,authorization_sha256,package_sha256,model,role,stage,retry_decision_id,consumed_at,status,reason)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'running','dispatch-intent-consumed')""", (dispatch_id, batch_id, auth["case_id"], job_id, attempt, auth["version"], authorization["sha256"], row["package_sha256"], spec["model"], spec["role"], spec["stage"], decision[0] if decision else None, _now()))
                    db.execute("UPDATE scoped_jobs SET status='running',reason='explicit-run-in-progress',attempt=?,retry_not_before=NULL,updated_at=? WHERE job_id=?", (attempt, _now(), job_id))
                    if decision:
                        db.execute("UPDATE scoped_retry_decisions SET dispatch_id=? WHERE decision_id=?", (dispatch_id, decision[0]))
                    dispatch = dict(db.execute("SELECT * FROM scoped_dispatches WHERE dispatch_id=?", (dispatch_id,)).fetchone())
                # The authorization, intent, and consumed attempt are now committed.
                try:
                    meta = adapter(self.root, job, state_root=self.folder / "jobs" / row["package_sha256"], attempt=attempt, dispatch=dispatch, **adapter_kwargs)
                    with self._db() as db:
                        current = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (job_id,)).fetchone()
                        meta = self._checkpoint(current, Path(meta["metadata_path"]), db=db, returned=meta)
                        status = self._finish(db, current, meta)
                    return {"job_id": job_id, "status": status, "reason": meta["reason"], "metadata_path": meta["metadata_path"], "dispatch_id": dispatch_id, "job_attempts_started": 1}
                except Exception:
                    # Error text may contain private worker data; persist a fixed reason.
                    with self._db() as db:
                        current = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (job_id,)).fetchone()
                        self._uncertain(db, current, "adapter-failed-or-checkpoint-invalid")
                    return {"status": "needs-retry-decision", "reason": "adapter-failed-or-checkpoint-invalid", "job_id": job_id, "dispatch_id": dispatch_id, "job_attempts_started": 1}
        except QueueBusy:
            return {"status": "busy", "reason": "another-scoped-job-running", "job_attempts_started": 0}


def verify_dispatch(project_root, dispatch, job):
    """Atomically claim a persisted inference intent once, immediately before exec.

    This is a local capability/consistency check, not a cryptographic model or
    caller identity attestation. A failed claim never refunds a consumed call.
    """
    queue = ScopedQueue(project_root)
    with queue._db() as db:
        row = db.execute("SELECT * FROM scoped_dispatches WHERE dispatch_id=?", (dispatch.get("dispatch_id"),)).fetchone()
        if row is None or dict(row) != dispatch or row["invocation_claimed_at"] is not None or row["status"] != "running":
            raise ValueError("Dispatch capability missing, changed, or already claimed")
        current = db.execute("SELECT * FROM scoped_jobs WHERE job_id=?", (row["job_id"],)).fetchone()
        authorization = db.execute("SELECT * FROM scoped_authorizations WHERE batch_id=? AND version=?", (row["batch_id"], row["authorization_version"])).fetchone()
        if current is None or current["status"] != "running" or current["attempt"] != row["attempt"] or package_sha256(job) != row["package_sha256"] or current["package_sha256"] != row["package_sha256"] or authorization is None or authorization["sha256"] != row["authorization_sha256"]:
            raise ValueError("Dispatch identity differs from durable queue")
        auth = json.loads(authorization["manifest"])
        if package_sha256(auth) != authorization["sha256"] or _stamp(auth["expires_at"]) <= datetime.now(timezone.utc) or row["model"] != MODELS.get(job["role"]) or row["role"] != job["role"] or queue._remaining(db, row["case_id"]) < 0:
            raise ValueError("Dispatch authorization is invalid or expired")
        spec = next((s for s in auth["jobs"] if s["job_id"] == job["job_id"]), None)
        if spec is None:
            raise ValueError("Job outside dispatch authorization")
        queue._validate_binding(db, current, spec)
        db.execute("UPDATE scoped_dispatches SET invocation_claimed_at=? WHERE dispatch_id=?", (_now(), row["dispatch_id"]))
        return dict(row)


def main():
    parser = argparse.ArgumentParser(description="Explicit scoped queue: no background worker or automatic retry")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("enqueue", "authorize-batch"):
        commands.add_parser(command).add_argument("package")
    commands.add_parser("status")
    commands.add_parser("recover")
    run = commands.add_parser("run-one")
    retry = commands.add_parser("retry")
    for command in (run, retry):
        command.add_argument("--job-id", required=True)
        command.add_argument("--batch-id", required=True)
    retry.add_argument("--decision-id", required=True)
    retry.add_argument("--rationale", required=True)
    retry.add_argument("--provenance-ref", action="append", required=True)
    args = parser.parse_args()
    queue = ScopedQueue(args.project_root)
    if args.command in {"enqueue", "authorize-batch"}:
        path = Path(args.package).resolve()
        if not path.is_relative_to(queue.root) or any(p.lower() == ".codex" or p.lower().startswith(".env") or p.lower() == "auth.json" or p.lower().endswith(".dpapi") for p in path.parts):
            parser.error("Package must be a noncredential project file")
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = queue.enqueue(payload) if args.command == "enqueue" else queue.authorize_batch(payload)
    elif args.command == "status":
        result = queue.status()
    elif args.command == "recover":
        result = queue.recover()
    elif args.command == "retry":
        result = queue.retry(job_id=args.job_id, batch_id=args.batch_id, decision_id=args.decision_id, rationale=args.rationale, provenance_refs=args.provenance_ref)
    else:
        result = queue.run_one(job_id=args.job_id, batch_id=args.batch_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
