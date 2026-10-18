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


def _validate_sanitized_events(events):
    """Validate only the fields intentionally retained by the adapter audit."""
    lifecycle = {"thread.started", "turn.started", "turn.completed", "turn.failed", "error",
                 "item.started", "item.completed", "item.updated"}
    if not isinstance(events, list) or not events:
        raise ValueError("Sanitized lifecycle events are missing")
    for event in events:
        if not isinstance(event, dict) or set(event) - {"type", "item_type", "usage"}:
            raise ValueError("Sanitized event fields differ")
        if event.get("type") not in lifecycle:
            raise ValueError("Unknown sanitized lifecycle event")
        if event["type"].startswith("item."):
            if event.get("item_type") not in {"reasoning", "agent_message", "disabled-code-host-diagnostic"}:
                raise ValueError("Sanitized event contains unauthorized item")
        elif "item_type" in event:
            raise ValueError("Unexpected item type on lifecycle event")
        if "usage" in event:
            usage = event["usage"]
            if not isinstance(usage, dict) or not usage or set(usage) - {"input_tokens", "cached_input_tokens", "output_tokens"}:
                raise ValueError("Sanitized usage fields differ")
            if any(type(value) is not int or value < 0 for value in usage.values()):
                raise ValueError("Sanitized usage values differ")
    if any(e["type"] in {"turn.failed", "error"} for e in events) or sum(e["type"] == "turn.completed" for e in events) != 1:
        raise ValueError("Sanitized turn is incomplete or repeated")
    return [e["usage"] for e in events if "usage" in e]


def _failure_projection(meta, original_bytes):
    fields = ('job_id','role','dispatch_id','status','reason','model_requested','reasoning_effort','speed',
        'authentication','actual_model','actual_model_verification','models_observed','backend_independently_verified',
        'started_at','completed_at','selected_route_completed','independent_review','engineering_test',
        'runtime_verified_live','execution_outcome','attempt','target_sha256','packet_sha256','packet_utf8_bytes',
        'original_bytes','prompt_sha256','prompt_utf8_bytes','returncode','validation_stage','validation_error_class',
        'validation_detail','unaccepted_output_sha256')
    safe = {key: meta[key] for key in fields if key in meta}
    safe.update(schema_version=1, original_private_metadata_sha256=hashlib.sha256(original_bytes).hexdigest(),
        input_manifest_sha256=hashlib.sha256(_json(meta.get('input_manifest', {})).encode('utf-8')).hexdigest(),
        staged_input_manifest=meta.get('staged_input_manifest'),
        limitations=['Original operational metadata is retained and validated locally; this projection does not reproduce its private bytes.'])
    return safe


class QueueBusy(RuntimeError):
    pass


class ScopedQueue:
    def __init__(self, project_root, *, fixture_only=False):
        self.root = Path(project_root).resolve()
        if type(fixture_only) is not bool:
            raise ValueError("Fixture mode must be an explicit boolean")
        self.fixture_only = fixture_only
        if self.fixture_only:
            import tempfile
            temporary_root = Path(tempfile.gettempdir()).resolve()
            if self.root == temporary_root or not self.root.is_relative_to(temporary_root):
                raise ValueError("Engineering fixture mode is restricted to a temporary project root")
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
            db.execute("""CREATE TABLE IF NOT EXISTS scoped_review_exceptions (
                case_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, sha256 TEXT NOT NULL,
                recorded_at TEXT NOT NULL)""")
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

    def _review_exception(self, db, case_id):
        row = db.execute("SELECT * FROM scoped_review_exceptions WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            return None
        manifest = json.loads(row["manifest"])
        if package_sha256(manifest) != row["sha256"]:
            raise ValueError("Review exception hash differs")
        self._validate_review_exception(db, manifest)
        return manifest

    def _validate_review_exception(self, db, manifest):
        required = {"schema_version", "case_id", "batch_id", "job_id", "created_at",
                    "authorization_sha256", "package_sha256", "failed_dispatch_id",
                    "failure_metadata_sha256", "authority"}
        if (not isinstance(manifest, dict) or set(manifest) != required or
                type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1):
            raise ValueError("Invalid review exception schema")
        _no_credentials(manifest)
        for key in ("case_id", "batch_id", "job_id", "failed_dispatch_id"):
            _ident(manifest[key])
        stamp = _stamp(manifest["created_at"])
        if stamp > datetime.now(timezone.utc):
            raise ValueError("Review exception is future-dated")
        authority = manifest["authority"]
        if not isinstance(authority, dict) or set(authority) != {"path", "sha256"}:
            raise ValueError("Explicit hash-bound user authority required")
        relative = Path(authority["path"])
        path = (self.root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(self.root / "validation") or path.suffix != ".md":
            raise ValueError("Authority must be an explicit validation Markdown record")
        if hashlib.sha256(path.read_bytes()).hexdigest() != authority["sha256"]:
            raise ValueError("User authority hash differs")
        auth_row = db.execute("SELECT * FROM scoped_authorizations WHERE batch_id=? AND sha256=?",
                              (manifest["batch_id"], manifest["authorization_sha256"])).fetchone()
        if auth_row is None:
            raise ValueError("Review exception authorization differs")
        auth = json.loads(auth_row["manifest"])
        if package_sha256(auth) != auth_row["sha256"] or auth["case_id"] != manifest["case_id"]:
            raise ValueError("Review exception authorization differs")
        _, current_auth = self._authorization(db, manifest["batch_id"])
        if ({k: v for k, v in auth.items() if k not in {"version", "jobs"}} !=
                {k: v for k, v in current_auth.items() if k not in {"version", "jobs"}} or
                len(auth["jobs"]) != len(current_auth["jobs"])):
            raise ValueError("Review exception authorization scope changed")
        if stamp < _stamp(auth["created_at"]) or stamp >= _stamp(auth["expires_at"]):
            raise ValueError("Review exception outside original authorization interval")
        spec = next((x for x in auth["jobs"] if x["job_id"] == manifest["job_id"]), None)
        if (spec is None or spec["role"] != "review" or spec["stage"] != "review" or
                spec["model"] != MODELS["review"] or spec["package_sha256"] != manifest["package_sha256"]):
            raise ValueError("Exception only permits the existing frozen Astra review")
        if next((x for x in current_auth["jobs"] if x["job_id"] == manifest["job_id"]), None) != spec:
            raise ValueError("Review exception frozen job changed")
        failure = db.execute("SELECT * FROM scoped_dispatches WHERE dispatch_id=?",
                             (manifest["failed_dispatch_id"],)).fetchone()
        if (failure is None or failure["case_id"] != manifest["case_id"] or
                failure["job_id"] != manifest["job_id"] or failure["invocation_claimed_at"] is not None or
                failure["reason"] != "runtime-restrictions-unverified" or
                failure["package_sha256"] != manifest["package_sha256"] or
                failure["status"] != "needs-retry-decision" or not failure["metadata_path"]):
            raise ValueError("Exception requires a preserved unclaimed runtime preflight failure")
        case = db.execute("SELECT * FROM scoped_cases WHERE case_id=?", (manifest["case_id"],)).fetchone()
        preceding = db.execute("SELECT COUNT(*) FROM scoped_dispatches WHERE case_id=? AND consumed_at<=?",
                               (manifest["case_id"], failure["consumed_at"])).fetchone()[0]
        if case is None or preceding + case["legacy_attempts"] != case["call_limit"]:
            raise ValueError("Exception must follow the last original-budget dispatch")
        metadata = Path(failure["metadata_path"]).resolve()
        if not metadata.is_relative_to(self.folder / "jobs"):
            raise ValueError("Failure metadata escapes queue")
        raw = metadata.read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["failure_metadata_sha256"]:
            raise ValueError("Failure metadata hash differs")
        meta = json.loads(raw)
        if (meta.get("dispatch_id") != failure["dispatch_id"] or
                meta.get("runtime_capabilities", {}).get("inference_calls") != 0 or meta.get("usage")):
            raise ValueError("Failure does not establish zero inference")
        return auth

    def authorize_review_exception(self, manifest):
        """Record at most one explicitly user-authorized extra review, never a refund.

        The authority record is local provenance, not a cryptographic human
        signature. Operators must obtain actual user authorization before use.
        """
        with self._worker_lock(), self._db() as db:
            auth = self._validate_review_exception(db, manifest)
            prior = db.execute("SELECT * FROM scoped_review_exceptions WHERE case_id=?",
                               (manifest["case_id"],)).fetchone()
            digest = package_sha256(manifest)
            if prior:
                if prior["sha256"] != digest or prior["manifest"] != _json(manifest):
                    raise ValueError("A case can have only one immutable review exception")
                return {"recorded": False, "sha256": digest, "additional_attempts": 1}
            if _stamp(auth["expires_at"]) <= datetime.now(timezone.utc):
                raise ValueError("Original authorization expired")
            if self._remaining(db, manifest["case_id"]) != 0:
                raise ValueError("Review exception requires exhausted original ceiling")
            db.execute("INSERT INTO scoped_review_exceptions VALUES (?,?,?,?)",
                       (manifest["case_id"], _json(manifest), digest, _now()))
            return {"recorded": True, "sha256": digest, "additional_attempts": 1}

    def _remaining(self, db, case_id, job_id=None):
        case = db.execute("SELECT * FROM scoped_cases WHERE case_id=?", (case_id,)).fetchone()
        used = db.execute("SELECT COUNT(*) FROM scoped_dispatches WHERE case_id=?", (case_id,)).fetchone()[0]
        exception = self._review_exception(db, case_id)
        extra = int(exception is not None and (job_id is None or exception["job_id"] == job_id))
        return case["call_limit"] + extra - case["legacy_attempts"] - used

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
            if meta.get('processing_receipt'):
                supplied = job['target'].get('processing')
                expected = {name: meta['lineage_sha256'][field] for name, field in
                    [('receipt','processing_receipt'), ('raw_output','unaccepted_output'),
                     ('failure_projection','failure_projection'), ('events','events')]}
                if not isinstance(supplied, dict) or {k: v.get('sha256') for k,v in supplied.items()} != expected:
                    raise ValueError('Continuation target omits or changes predecessor processing context')
            elif 'processing' in job['target']:
                raise ValueError('Continuation target invents predecessor processing context')
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
            if 'processing' in job['target']:
                processing_refs = {}
                for key, ref in job['target']['processing'].items():
                    processing_refs[key] = immutable('target-processing-' + key + '.json', _file(self.root, ref).read_bytes())
                target = dict(target, processing=processing_refs)
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
            lineage = {}
            if meta.get('processing_receipt'):
                for field, filename in (('failure_projection', 'failure-projection.json'),
                                        ('unaccepted_output', 'unaccepted-output.json'),
                                        ('events', 'events.json'),
                                        ('processing_receipt', 'processing-receipt.json')):
                    source = Path(meta['metadata_path']).parent / filename
                    if not source.is_file() or source.is_symlink():
                        raise ValueError('Processed failure lineage is incomplete')
                    data = source.read_bytes()
                    digest = meta['lineage_sha256'].get(field)
                    if hashlib.sha256(data).hexdigest() != digest:
                        raise ValueError('Processed failure lineage changed')
                    lineage[field] = immutable(filename, data)
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
            if lineage:
                public['processing_receipt'] = lineage['processing_receipt']
                public['failure_projection'] = lineage['failure_projection']
                public['unaccepted_output'] = lineage['unaccepted_output']
                public['events'] = lineage['events']
                public['lineage_sha256'] = dict(meta['lineage_sha256'])
                public['normalization_timestamp'] = meta['normalization_timestamp']
                public['processing'] = dict(receipt=lineage['processing_receipt'],
                    raw_output=lineage['unaccepted_output'], failure_projection=lineage['failure_projection'],
                    events=lineage['events'])
                try:
                    from .research_processing import processing_context
                except ImportError:
                    from research_processing import processing_context
                processing_context(self.root, public['processing'], result_bytes, execution=public)
                public['original_failure_metadata_sha256'] = meta['lineage_sha256']['failure_metadata']
                public['failure_metadata_verification'] = 'original private metadata verified locally; exported safe projection only'
            execution = immutable('execution.json', _json(public).encode('utf-8') + b'\n')
            packet_ref = immutable('packet.json', packet['bytes'])
            return dict(job=request, result=result, execution=execution, packet=packet_ref)

    def revalidate_failed_output(self, *, job_id, batch_id):
        """Explicitly normalize one retained failed response under its claimed dispatch.

        This is a deterministic post-processing operation. It does not dispatch,
        create an attempt, refund a call, or treat an engineering run as live.
        """
        try:
            from .research_output import normalize_issue_references
            from .research_checkpoint import _atomic
            from .scoped_research_adapter import (_packet, _audit_events, _no_credentials,
                SCHEMA, PINNED_CATALOG_PATH, PINNED_CATALOG_SHA256, validate_output)
            from .research_runtime import freeze_catalog, write_model_catalog
            from .research_packet import stage_packet
        except ImportError:
            from research_output import normalize_issue_references
            from research_checkpoint import _atomic
            from scoped_research_adapter import (_packet, _audit_events, _no_credentials,
                SCHEMA, PINNED_CATALOG_PATH, PINNED_CATALOG_SHA256, validate_output)
            from research_runtime import freeze_catalog, write_model_catalog
            from research_packet import stage_packet
        _ident(job_id); _ident(batch_id)
        with self._worker_lock():
            with self._db() as db:
                row = db.execute('SELECT * FROM scoped_jobs WHERE job_id=?', (job_id,)).fetchone()
                if row is None:
                    raise ValueError('Unknown job')
                binding = db.execute('SELECT * FROM scoped_job_bindings WHERE job_id=?', (job_id,)).fetchone()
                if binding is None or binding['batch_id'] != batch_id:
                    raise ValueError('Failed output is outside the named authorization')
                if row['status'] in {'needs-input','complete'} and row['metadata_path']:
                    already = self._checkpoint(row, Path(row['metadata_path']), db=db)
                    if already.get('processing_receipt'):
                        return {'job_id':job_id,'status':row['status'],'revalidated':False,'reason':'already-revalidated',
                            'dispatch_id':already['dispatch_id'],'attempt':already['attempt']}
                if row['status']=='needs-retry-decision' and row['metadata_path']:
                    committed = self._checkpoint(row,Path(row['metadata_path']),db=db)
                    if committed.get('processing_receipt') and committed.get('reason')=='analytical-output-validated':
                        self._finish_revalidation(db,row,committed)
                        return {'job_id':job_id,'status':'needs-input' if committed['continuation_required'] else 'complete',
                            'revalidated':False,'reason':'recovered-committed-revalidation',
                            'dispatch_id':committed['dispatch_id'],'attempt':committed['attempt']}
                if row['status'] != 'needs-retry-decision' or row['attempt'] < 1:
                    raise ValueError('Only a retained failed dispatch can be revalidated')
                binding = db.execute('SELECT * FROM scoped_job_bindings WHERE job_id=?', (job_id,)).fetchone()
                if binding is None or binding['batch_id'] != batch_id:
                    raise ValueError('Failed output is outside the named authorization')
                dispatch = db.execute('SELECT * FROM scoped_dispatches WHERE job_id=? AND attempt=?', (job_id, row['attempt'])).fetchone()
                auth_row, auth = self._authorization(db, batch_id)
                if (dispatch is None or dispatch['batch_id'] != batch_id or
                    dispatch['case_id'] != binding['case_id'] or
                    dispatch['status'] != 'needs-retry-decision' or
                    dispatch['invocation_claimed_at'] is None or
                    auth_row['version'] != dispatch['authorization_version'] or
                    auth_row['sha256'] != dispatch['authorization_sha256'] or
                    _stamp(auth['expires_at']) <= datetime.now(timezone.utc)):
                    raise ValueError('Dispatch authorization is stale, unclaimed, or expired')
                spec = next((x for x in auth['jobs'] if x['job_id'] == job_id), None)
                job = json.loads(row['package'])
                if (spec is None or spec['package_sha256'] != row['package_sha256'] or
                    spec['scope_sha256'] != scope_sha256(job) or spec['model'] != dispatch['model'] or
                    spec['role'] != dispatch['role'] or spec['stage'] != dispatch['stage'] or
                    dispatch['attempt'] != row['attempt'] or dispatch['package_sha256'] != row['package_sha256']):
                    raise ValueError('Current package, stage, model, role, or attempt differs')
                folder = Path(row['metadata_path']).resolve().parent
                meta_path = Path(row['metadata_path']).resolve()
                if meta_path.name != 'metadata.json' or meta_path.parent.parent != (self.folder / 'jobs' / row['package_sha256']).resolve():
                    raise ValueError('Failure checkpoint escapes its package attempt')
                failure_bytes = meta_path.read_bytes()
                original = self._checkpoint(row, meta_path, db=db)
                live_failure = (original.get('engineering_test') is False and original.get('runtime_verified_live') is True)
                fixture_failure = (self.fixture_only and original.get('engineering_test') is True and
                    original.get('runtime_verified_live') is False and original.get('actual_model') is None and
                    original.get('models_observed') == [])
                if (original.get('reason') != 'invalid-output-input-or-unauthorized-event' or
                    original.get('validation_stage') != 'output-schema-and-provenance' or
                    original.get('returncode') != 0 or original.get('authentication') != 'chatgpt-subscription' or
                    not (live_failure or fixture_failure) or
                    original.get('selected_route_completed') is not False):
                    raise ValueError('Failed output is not eligible for live deterministic revalidation or the isolated engineering fixture')
                raw_path, events_path = folder / 'unaccepted-output.json', folder / 'events.json'
                if raw_path.is_symlink() or events_path.is_symlink() or not raw_path.is_file() or not events_path.is_file():
                    raise ValueError('Retained raw output or sanitized events are missing')
                raw_bytes, events_bytes = raw_path.read_bytes(), events_path.read_bytes()
                if hashlib.sha256(raw_bytes).hexdigest() != original.get('unaccepted_output_sha256'):
                    raise ValueError('Retained raw output hash differs')
                raw = json.loads(raw_bytes.decode('utf-8'))
                _no_credentials(raw)
                events = json.loads(events_bytes.decode('utf-8'))
                usage = _validate_sanitized_events(events)
                if original.get('models_observed') not in ([], [MODELS[job['role']]]) or original.get('actual_model') not in {None,MODELS[job['role']]}:
                    raise ValueError('Sanitized event identity differs')
                input_manifest = validate_package(self.root, job)
                if original.get('input_manifest') != input_manifest:
                    raise ValueError('Original source input manifest changed')
                packet = _packet(self.root, job)
                if original.get('packet_sha256') != packet['sha256'] or original.get('target_sha256') != job['target']['sha256']:
                    raise ValueError('Frozen packet or target changed')
                if original.get('staged_input_manifest') is None:
                    raise ValueError('Staged input manifest unavailable')
                # Rebuild only the previously staged immutable inputs. No CLI or model call occurs.
                import tempfile
                with tempfile.TemporaryDirectory(prefix='cr2-revalidate-') as tmp:
                    staged_root = Path(tmp).resolve()
                    staged = stage_packet(packet, SCHEMA, staged_root)
                    catalog = freeze_catalog(self.root / PINNED_CATALOG_PATH, expected_sha256=PINNED_CATALOG_SHA256)
                    model_catalog = write_model_catalog(staged_root, catalog)
                    staged[model_catalog.name] = hashlib.sha256(model_catalog.read_bytes()).hexdigest()
                    if staged != original['staged_input_manifest']:
                        raise ValueError('Reconstructed staged input manifest differs')
                normalized, helper_receipt = normalize_issue_references(raw)
                if not helper_receipt['edits']:
                    raise ValueError('No permitted reference repair is needed')
                try:
                    validate_output(raw, job, self.root)
                except ValueError:
                    pass
                else:
                    raise ValueError('Retained original does not reproduce a strict validation failure')
                result = validate_output(normalized, job, self.root)
                result_bytes = _json(result).encode('utf-8') + b'\n'
                algorithm_path = Path(__file__).resolve().with_name('research_output.py')
                failure_hash = hashlib.sha256(failure_bytes).hexdigest()
                failure_projection_bytes = _json(_failure_projection(original, failure_bytes)).encode('utf-8') + b'\n'
                failure_projection_hash = hashlib.sha256(failure_projection_bytes).hexdigest()
                raw_hash = hashlib.sha256(raw_bytes).hexdigest()
                events_hash = hashlib.sha256(events_bytes).hexdigest()
                processed_hash = hashlib.sha256(result_bytes).hexdigest()
                normalization_timestamp = datetime.now(timezone.utc).isoformat()
                receipt = {
                    'schema_version': 1, 'job_id': job_id, 'batch_id': batch_id,
                    'case_id': binding['case_id'], 'authorization_version': dispatch['authorization_version'],
                    'authorization_sha256': dispatch['authorization_sha256'], 'dispatch_id': dispatch['dispatch_id'],
                    'attempt': dispatch['attempt'], 'role': dispatch['role'], 'model': dispatch['model'], 'stage': dispatch['stage'],
                    'package_sha256': row['package_sha256'], 'scope_sha256': scope_sha256(job),
                    'target_sha256': job['target']['sha256'], 'packet_sha256': packet['sha256'],
                    'catalog_sha256': PINNED_CATALOG_SHA256,
                    'input_manifest_sha256': hashlib.sha256(_json(input_manifest).encode('utf-8')).hexdigest(),
                    'staged_input_manifest': original['staged_input_manifest'],
                    'failure_metadata_sha256': failure_hash, 'raw_output_sha256': raw_hash,
                    'failure_projection_sha256': failure_projection_hash,
                    'events_sha256': events_hash, 'processed_result_sha256': processed_hash,
                    'normalization_timestamp': normalization_timestamp,
                    'engineering_fixture_only': bool(self.fixture_only),
                    'algorithm_sha256': hashlib.sha256(algorithm_path.read_bytes()).hexdigest(),
                    'normalization': helper_receipt, 'limitations': ['Deterministic formatting repair only; no analytical or investment approval.']}
                receipt_bytes = _json(receipt).encode('utf-8') + b'\n'
                existing_receipt_path = folder / 'processing-receipt.json'
                if existing_receipt_path.exists():
                    if existing_receipt_path.is_symlink():
                        raise ValueError('Conflicting prior revalidation artifact')
                    prior_receipt_bytes = existing_receipt_path.read_bytes()
                    prior_receipt = json.loads(prior_receipt_bytes.decode('utf-8'))
                    comparable = dict(prior_receipt)
                    comparable.pop('normalization_timestamp', None)
                    expected_comparable = dict(receipt)
                    expected_comparable.pop('normalization_timestamp', None)
                    if comparable != expected_comparable:
                        raise ValueError('Conflicting prior revalidation receipt')
                    normalization_timestamp = prior_receipt.get('normalization_timestamp')
                    receipt = prior_receipt
                    receipt_bytes = prior_receipt_bytes
                receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()
                # Stable names plus byte equality make replay idempotent. The original failure
                # snapshot is written before result/receipt; active metadata is replaced last.
                def preserve(name, data):
                    path = folder / name
                    if path.exists():
                        if path.is_symlink() or path.read_bytes() != data:
                            raise ValueError('Conflicting prior revalidation artifact')
                    else:
                        _atomic(path, data)
                preserve('failure-metadata.json', failure_bytes)
                preserve('failure-projection.json', failure_projection_bytes)
                preserve('processing-receipt.json', receipt_bytes)
                preserve('result.json', result_bytes)
                finalized = dict(original)
                finalized.update(reason='analytical-output-validated', status=result['status'],
                    continuation_required=needs_continuation(result), selected_route_completed=True,
                    execution_outcome='completed', output_sha256=processed_hash,
                    continuation=result['continuation'], retry_decision_required=False,
                    independent_review=job['role']=='review',
                    normalization_timestamp=normalization_timestamp,
                    processing_receipt={'path': 'processing-receipt.json', 'sha256': receipt_hash},
                    lineage_sha256={'failure_metadata': failure_hash, 'unaccepted_output': raw_hash,
                        'failure_projection': failure_projection_hash, 'events': events_hash,
                        'processing_receipt': receipt_hash}, usage=usage)
                # Revalidate everything immediately before committing metadata last.
                self._validate_processing_lineage(row, finalized, db, job=job,
                    parts={'failure':failure_bytes,'raw':raw_bytes,'events':events_bytes,'receipt':receipt_bytes,
                        'result':result_bytes,'failure_projection':failure_projection_bytes})
                _atomic(meta_path, _json(finalized).encode('utf-8') + b'\n')
                # The final metadata's completed_at remains the original completion time.
                self._finish_revalidation(db, row, finalized)
                return {'job_id': job_id, 'status': 'needs-input' if finalized['continuation_required'] else 'complete',
                    'dispatch_id': dispatch['dispatch_id'], 'attempt': dispatch['attempt'], 'revalidated': True,
                    'normalization_timestamp': finalized['normalization_timestamp'], 'receipt_sha256': receipt_hash}

    def _finish_revalidation(self, db, row, meta):
        status = 'needs-input' if meta['continuation_required'] else 'complete'
        db.execute("UPDATE scoped_jobs SET status=?,reason='analytical-output-validated',metadata_path=?,updated_at=? WHERE job_id=?",
                   (status, meta['metadata_path'], _now(), row['job_id']))
        db.execute("UPDATE scoped_dispatches SET status=?,reason='analytical-output-validated',metadata_path=? WHERE job_id=? AND attempt=?",
                   (status, meta['metadata_path'], row['job_id'], row['attempt']))

    def _validate_processing_lineage(self, row, meta, db, *, job=None, parts=None):
        """Recompute the deterministic transformation and verify all receipt bindings."""
        try:
            from .research_output import normalize_issue_references
            from .scoped_research_adapter import (_packet, SCHEMA, PINNED_CATALOG_PATH,
                PINNED_CATALOG_SHA256, validate_output)
            from .research_runtime import freeze_catalog, write_model_catalog
            from .research_packet import stage_packet
        except ImportError:
            from research_output import normalize_issue_references
            from scoped_research_adapter import (_packet, SCHEMA, PINNED_CATALOG_PATH,
                PINNED_CATALOG_SHA256, validate_output)
            from research_runtime import freeze_catalog, write_model_catalog
            from research_packet import stage_packet
        folder=Path(meta['metadata_path']).resolve().parent
        def read(key,name):
            if parts and key in parts:return parts[key]
            path=folder/name
            if path.is_symlink() or not path.is_file():raise ValueError('Processing lineage artifact missing')
            return path.read_bytes()
        raw_bytes=read('raw','unaccepted-output.json');events_bytes=read('events','events.json')
        failure_bytes=read('failure','failure-metadata.json');receipt_bytes=read('receipt','processing-receipt.json')
        projection_bytes=read('failure_projection','failure-projection.json')
        result_bytes=read('result','result.json')
        hashes={'failure_metadata':hashlib.sha256(failure_bytes).hexdigest(),
            'unaccepted_output':hashlib.sha256(raw_bytes).hexdigest(),'events':hashlib.sha256(events_bytes).hexdigest(),
            'processing_receipt':hashlib.sha256(receipt_bytes).hexdigest()}
        original=json.loads(failure_bytes.decode('utf-8'));raw=json.loads(raw_bytes.decode('utf-8'))
        events=json.loads(events_bytes.decode('utf-8'));receipt=json.loads(receipt_bytes.decode('utf-8'))
        job=job or json.loads(row['package']);binding=db.execute('SELECT * FROM scoped_job_bindings WHERE job_id=?',(row['job_id'],)).fetchone()
        dispatch=db.execute('SELECT * FROM scoped_dispatches WHERE job_id=? AND attempt=?',(row['job_id'],row['attempt'])).fetchone()
        auth_row,auth=self._authorization(db,dispatch['batch_id']) if dispatch else (None,None)
        auth_history=db.execute('SELECT * FROM scoped_authorizations WHERE batch_id=? ORDER BY version',(dispatch['batch_id'],)).fetchall() if dispatch else []
        spec=next((x for x in auth['jobs'] if x['job_id']==row['job_id']),None) if auth else None
        packet=_packet(self.root,job);manifest=validate_package(self.root,job)
        expected_projection=_json(_failure_projection(original,failure_bytes)).encode('utf-8')+b'\n'
        hashes['failure_projection']=hashlib.sha256(projection_bytes).hexdigest()
        if (projection_bytes!=expected_projection or meta.get('lineage_sha256')!=hashes or
            meta.get('processing_receipt')!={'path':'processing-receipt.json','sha256':hashes['processing_receipt']}):
            raise ValueError('Processing lineage hashes or safe failure projection differ')
        fixed={'job_id':row['job_id'],'batch_id':dispatch['batch_id'],'case_id':binding['case_id'],
            'authorization_version':dispatch['authorization_version'],'authorization_sha256':dispatch['authorization_sha256'],
            'dispatch_id':dispatch['dispatch_id'],'attempt':dispatch['attempt'],'role':dispatch['role'],'model':dispatch['model'],
            'stage':dispatch['stage'],'package_sha256':row['package_sha256'],'scope_sha256':scope_sha256(job),
            'target_sha256':job['target']['sha256'],'packet_sha256':packet['sha256'],'catalog_sha256':PINNED_CATALOG_SHA256,
            'input_manifest_sha256':hashlib.sha256(_json(manifest).encode('utf-8')).hexdigest(),
            'staged_input_manifest':original.get('staged_input_manifest'),
            'failure_metadata_sha256':hashes['failure_metadata'],'raw_output_sha256':hashes['unaccepted_output'],
            'failure_projection_sha256':hashes['failure_projection'],
            'events_sha256':hashes['events'],'processed_result_sha256':hashlib.sha256(result_bytes).hexdigest(),
            'algorithm_sha256':hashlib.sha256(Path(__file__).resolve().with_name('research_output.py').read_bytes()).hexdigest()}
        if not dispatch or not binding or not auth_history or any(receipt.get(k)!=v for k,v in fixed.items()):
            raise ValueError('Processing receipt bindings differ')
        dispatch_auth_row = next((a for a in auth_history if a['version']==dispatch['authorization_version']),None)
        dispatch_auth = json.loads(dispatch_auth_row['manifest']) if dispatch_auth_row else None
        if (dispatch_auth_row is None or dispatch_auth_row['sha256']!=dispatch['authorization_sha256'] or
            package_sha256(dispatch_auth)!=dispatch_auth_row['sha256']):
            raise ValueError('Historical dispatch authorization is missing or changed')
        expires=_stamp(dispatch_auth['expires_at'])
        normalized_at=_stamp(meta.get('normalization_timestamp')) if meta.get('normalization_timestamp') else None
        if (binding['batch_id']!=dispatch['batch_id'] or spec is None or spec['package_sha256']!=row['package_sha256'] or
            spec['scope_sha256']!=scope_sha256(job) or dispatch['package_sha256']!=row['package_sha256'] or
            dispatch['model']!=MODELS[job['role']] or dispatch['role']!=job['role'] or dispatch['invocation_claimed_at'] is None or
            _stamp(dispatch['consumed_at'])>expires or normalized_at is None or normalized_at>expires or
            not (_stamp(original['started_at'])<=_stamp(original['completed_at'])<=normalized_at<=datetime.now(timezone.utc))):
            raise ValueError('Processing dispatch or authorization is no longer current')
        previous_manifest=dispatch_auth
        expected_version=dispatch['authorization_version']
        for successor_row in auth_history:
            if successor_row['version']<=expected_version:
                continue
            successor=json.loads(successor_row['manifest'])
            old_fixed={k:v for k,v in previous_manifest.items() if k not in {'version','jobs'}}
            new_fixed={k:v for k,v in successor.items() if k not in {'version','jobs'}}
            if (successor['version']!=expected_version+1 or old_fixed!=new_fixed or
                len(previous_manifest['jobs'])!=len(successor['jobs'])):
                raise ValueError('Authorization successor widened or changed scope')
            for before,after in zip(previous_manifest['jobs'],successor['jobs']):
                before_fixed={k:v for k,v in before.items() if k!='package_sha256'}
                after_fixed={k:v for k,v in after.items() if k!='package_sha256'}
                if before_fixed!=after_fixed or (before['package_sha256'] is not None and before!=after):
                    raise ValueError('Authorization successor changed a named job')
                if before['package_sha256'] is None and after['package_sha256'] is not None:
                    successor_job=db.execute('SELECT * FROM scoped_jobs WHERE job_id=?',(after['job_id'],)).fetchone()
                    if successor_job is None:
                        raise ValueError('Authorization successor bound an unknown package')
                    successor_package=json.loads(successor_job['package'])
                    validate_package(self.root,successor_package)
                    if (successor_job['package_sha256']!=after['package_sha256'] or
                        package_sha256(successor_package)!=after['package_sha256'] or
                        scope_sha256(successor_package)!=after['scope_sha256']):
                        raise ValueError('Authorization successor package binding differs')
                    if after['target_from_job_id']==row['job_id']:
                        predecessor_meta=meta
                    else:
                        predecessor=db.execute('SELECT * FROM scoped_jobs WHERE job_id=?',(after['target_from_job_id'],)).fetchone()
                        if predecessor is None or not predecessor['metadata_path']:
                            raise ValueError('Authorization successor predecessor is unavailable')
                        predecessor_meta=self._checkpoint(predecessor,Path(predecessor['metadata_path']),db=db)
                    if (successor_package['target']['sha256']!=predecessor_meta.get('output_sha256') or
                        (self.root/successor_package['target']['path']).resolve()!=Path(predecessor_meta['result_path']).resolve()):
                        raise ValueError('Authorization successor target differs from predecessor result')
            if package_sha256(successor)!=successor_row['sha256']:
                raise ValueError('Authorization successor hash differs')
            expected_version=successor['version'];previous_manifest=successor
        if (original.get('reason')!='invalid-output-input-or-unauthorized-event' or original.get('returncode')!=0 or
            original.get('authentication')!='chatgpt-subscription' or
            original.get('input_manifest')!=manifest or
            original.get('packet_sha256')!=packet['sha256']):
            raise ValueError('Original failure evidence is not eligible or has changed')
        live_flags=(original.get('engineering_test') is False and original.get('runtime_verified_live') is True)
        fixture_flags=(receipt.get('engineering_fixture_only') is True and original.get('engineering_test') is True and
            original.get('runtime_verified_live') is False and original.get('actual_model') is None and
            original.get('models_observed')==[])
        if not (live_flags or fixture_flags):
            raise ValueError('Original runtime identity flags differ')
        usage=_validate_sanitized_events(events)
        import tempfile
        with tempfile.TemporaryDirectory(prefix='cr2-revalidate-check-') as tmp:
            stage=Path(tmp).resolve();staged=stage_packet(packet,SCHEMA,stage)
            catalog=freeze_catalog(self.root/PINNED_CATALOG_PATH,expected_sha256=PINNED_CATALOG_SHA256)
            mc=write_model_catalog(stage,catalog);staged[mc.name]=hashlib.sha256(mc.read_bytes()).hexdigest()
            if staged!=original.get('staged_input_manifest'):raise ValueError('Staged input manifest differs')
        normalized,edit_receipt=normalize_issue_references(raw)
        if not edit_receipt['edits'] or receipt.get('normalization')!=edit_receipt:raise ValueError('Normalization edits differ')
        try:
            validate_output(raw,job,self.root)
        except ValueError:
            pass
        else:
            raise ValueError('Original strict validation failure does not reproduce')
        result=validate_output(normalized,job,self.root)
        if _json(result).encode('utf-8')+b'\n'!=result_bytes or meta.get('output_sha256')!=hashlib.sha256(result_bytes).hexdigest():
            raise ValueError('Strictly validated normalized result differs')
        preserved_identity=('job_id','role','dispatch_id','model_requested','reasoning_effort','speed','authentication',
            'actual_model','actual_model_verification','models_observed','backend_independently_verified','started_at',
            'completed_at','engineering_test','runtime_verified_live','attempt','target_sha256',
            'packet_sha256','returncode','validation_stage','validation_error_class','validation_detail','input_manifest',
            'staged_input_manifest','prompt_sha256','packet_utf8_bytes','original_bytes','prompt_utf8_bytes')
        if (meta.get('reason')!='analytical-output-validated' or meta.get('dispatch_id')!=dispatch['dispatch_id'] or
            meta.get('attempt')!=dispatch['attempt'] or any(meta.get(key)!=original.get(key) for key in preserved_identity) or
            receipt.get('normalization_timestamp') != meta.get('normalization_timestamp') or
            meta.get('continuation')!=result['continuation'] or meta.get('retry_decision_required') is not False or
            meta.get('independent_review') is not (job['role']=='review') or
            receipt.get('engineering_fixture_only') is not fixture_flags or meta.get('normalization_timestamp') is None or
            meta.get('usage')!=usage):
            raise ValueError('Final processing execution metadata differs')
        return True

    def status(self):
        with self._db() as db:
            jobs = [dict(r) for r in db.execute("SELECT job_id,role,status,reason,attempt,retry_not_before,metadata_path,created_at,updated_at FROM scoped_jobs ORDER BY created_at,job_id")]
            cases = [dict(r) for r in db.execute("SELECT * FROM scoped_cases ORDER BY case_id")]
            for case in cases:
                case["remaining_attempts"] = self._remaining(db, case["case_id"])
                exception = self._review_exception(db, case["case_id"])
                case["additional_review_attempts"] = int(exception is not None)
                case["effective_call_limit"] = case["call_limit"] + case["additional_review_attempts"]
                case["consumed_attempts"] = case["effective_call_limit"] - case["remaining_attempts"]
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
            if meta.get('processing_receipt'):
                self._validate_processing_lineage(row, meta, db, job=job)
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
        # Metadata is the final filesystem write. A rollback can therefore leave
        # a valid processed checkpoint attached to the old retry-decision row.
        for row in db.execute("SELECT * FROM scoped_jobs WHERE status='needs-retry-decision' AND metadata_path IS NOT NULL").fetchall():
            try:
                candidate=self._checkpoint(row,Path(row['metadata_path']),db=db)
            except (OSError,ValueError,KeyError,TypeError):
                continue
            if candidate.get('processing_receipt') and candidate.get('reason')=='analytical-output-validated':
                self._finish_revalidation(db,row,candidate)
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
            if _stamp(auth["expires_at"]) <= datetime.now(timezone.utc) or "explicit-retry" not in auth["permitted_continuation"] or self._remaining(db, auth["case_id"], job_id) <= 0:
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
                    if self._remaining(db, auth["case_id"], job_id) <= 0:
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
        if package_sha256(auth) != authorization["sha256"] or _stamp(auth["expires_at"]) <= datetime.now(timezone.utc) or row["model"] != MODELS.get(job["role"]) or row["role"] != job["role"] or queue._remaining(db, row["case_id"], row["job_id"]) < 0:
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
    for command in ("enqueue", "authorize-batch", "authorize-review-exception"):
        commands.add_parser(command).add_argument("package")
    commands.add_parser("status")
    commands.add_parser("recover")
    run = commands.add_parser("run-one")
    run.add_argument("--executable", default="codex",
        help="Concrete Codex executable; real dispatch requires the reviewed pinned Windows binary")
    retry = commands.add_parser("retry")
    for command in (run, retry):
        command.add_argument("--job-id", required=True)
        command.add_argument("--batch-id", required=True)
    retry.add_argument("--decision-id", required=True)
    retry.add_argument("--rationale", required=True)
    retry.add_argument("--provenance-ref", action="append", required=True)
    args = parser.parse_args()
    queue = ScopedQueue(args.project_root)
    if args.command in {"enqueue", "authorize-batch", "authorize-review-exception"}:
        path = Path(args.package).resolve()
        if not path.is_relative_to(queue.root) or any(p.lower() == ".codex" or p.lower().startswith(".env") or p.lower() == "auth.json" or p.lower().endswith(".dpapi") for p in path.parts):
            parser.error("Package must be a noncredential project file")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if args.command == "enqueue":
            result = queue.enqueue(payload)
        elif args.command == "authorize-batch":
            result = queue.authorize_batch(payload)
        else:
            result = queue.authorize_review_exception(payload)
    elif args.command == "status":
        result = queue.status()
    elif args.command == "recover":
        result = queue.recover()
    elif args.command == "retry":
        result = queue.retry(job_id=args.job_id, batch_id=args.batch_id, decision_id=args.decision_id, rationale=args.rationale, provenance_refs=args.provenance_ref)
    else:
        result = queue.run_one(job_id=args.job_id, batch_id=args.batch_id, executable=args.executable)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
