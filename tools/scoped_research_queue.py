"""Durable, opt-in scoped model queue, isolated from the observation service.

No background loop or service integration: run_one is an explicit caller action.
An OS process lock spans the complete job; process death releases the lock.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3

try:
    from .scoped_research_adapter import run_scoped_job, validate_package, validate_output, _no_credentials
except ImportError:
    from scoped_research_adapter import run_scoped_job, validate_package, validate_output, _no_credentials


def _now():
    return datetime.now(timezone.utc).isoformat()


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

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def _worker_lock(self):
        path = self.folder / "worker.lock"
        with path.open("a+b") as handle:
            try:
                if path.stat().st_size == 0:
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
        _no_credentials(job)
        package = json.dumps(job, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(package.encode()).hexdigest()
        stamp = _now()
        with self._db() as db:
            previous = db.execute("SELECT package_sha256 FROM scoped_jobs WHERE job_id=?", (job["job_id"],)).fetchone()
            if previous:
                if previous[0] != digest:
                    raise ValueError("Job ID already binds a different frozen package")
                return {"job_id": job["job_id"], "enqueued": False, "reason": "already-recorded"}
            db.execute("INSERT INTO scoped_jobs (job_id,package,package_sha256,role,status,reason,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                       (job["job_id"], package, digest, job["role"], "queued", "explicitly-enqueued", stamp, stamp))
        return {"job_id": job["job_id"], "enqueued": True, "reason": "explicitly-enqueued"}

    def status(self):
        with self._db() as db:
            rows = db.execute("SELECT job_id,role,status,reason,attempt,retry_not_before,metadata_path,created_at,updated_at FROM scoped_jobs ORDER BY created_at,job_id").fetchall()
        return {"mode": "explicit-run-only", "background_enabled": False, "database": str(self.database), "jobs": [dict(row) for row in rows]}

    def _recover_interrupted(self, db):
        for row in db.execute("SELECT * FROM scoped_jobs WHERE status='running'").fetchall():
            # A held OS lock means this cannot execute while a live worker runs.
            # Recover only completed adapter checkpoints for this exact queue job.
            checkpoint_root = self.folder / "jobs" / row["package_sha256"]
            recovered = None
            for path in sorted(checkpoint_root.glob("*/metadata.json"), reverse=True):
                try:
                    meta = json.loads(path.read_text(encoding="utf-8"))
                    if meta.get("job_id") == row["job_id"] and meta.get("attempt") == row["attempt"] and meta.get("completed_at"):
                        recovered = meta
                        break
                except (OSError, ValueError):
                    continue
            if recovered:
                try:
                    if hashlib.sha256(row["package"].encode()).hexdigest() != row["package_sha256"]:
                        raise ValueError("Frozen package hash differs")
                    job = json.loads(row["package"])
                    validate_package(self.root, job)
                    if recovered.get("reason") == "analytical-output-validated" or not recovered.get("continuation_required", True):
                        result_path = Path(recovered["result_path"]).resolve()
                        metadata_path = Path(recovered["metadata_path"]).resolve()
                        if metadata_path != path.resolve() or result_path.parent != path.parent.resolve() or not result_path.is_relative_to(checkpoint_root.resolve()):
                            raise ValueError("Recovery result escapes its checkpoint")
                        if hashlib.sha256(result_path.read_bytes()).hexdigest() != recovered["output_sha256"]:
                            raise ValueError("Recovery result hash differs")
                        result = json.loads(result_path.read_text(encoding="utf-8"))
                        validate_output(result, job, self.root)
                        if result["status"] != recovered["status"] or recovered["continuation_required"] != (result["status"] in {"partial", "withheld"}):
                            raise ValueError("Recovery status differs")
                    self._finish(db, row["job_id"], recovered)
                except (OSError, ValueError, KeyError, TypeError):
                    db.execute("UPDATE scoped_jobs SET status='needs-input',reason='recovery-checkpoint-invalid',retry_not_before=NULL,updated_at=? WHERE job_id=?", (_now(), row["job_id"]))
            else:
                retry = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
                db.execute("UPDATE scoped_jobs SET status='deferred', reason='worker-interrupted',retry_not_before=?,updated_at=? WHERE job_id=?", (retry, _now(), row["job_id"]))

    def _finish(self, db, job_id, meta):
        if not meta["continuation_required"]:
            status = "complete"
        elif meta["reason"] == "analytical-output-validated":
            status = "needs-input"
        else:
            status = "deferred"
        db.execute("UPDATE scoped_jobs SET status=?,reason=?,retry_not_before=?,metadata_path=?,updated_at=? WHERE job_id=?",
            (status, meta["reason"], meta.get("retry_not_before") if status == "deferred" else None, meta["metadata_path"], _now(), job_id))

    def run_one(self, *, adapter=run_scoped_job, **adapter_kwargs):
        """Explicit invocation consumes at most one due job; never waits or loops."""
        if "state_root" in adapter_kwargs or "attempt" in adapter_kwargs:
            raise ValueError("Queue owns checkpoint root and attempt")
        try:
            with self._worker_lock():
                with self._db() as db:
                    self._recover_interrupted(db)
                    row = db.execute("SELECT * FROM scoped_jobs WHERE status IN ('queued','deferred') AND (retry_not_before IS NULL OR retry_not_before<=?) ORDER BY created_at,job_id LIMIT 1", (_now(),)).fetchone()
                    if row is None:
                        return {"status": "idle", "reason": "no-due-job", "job_attempts_started": 0}
                    if row["attempt"] >= 100:
                        db.execute("UPDATE scoped_jobs SET status='needs-input',reason='attempt-limit',updated_at=? WHERE job_id=?", (_now(), row["job_id"]))
                        return {"status": "needs-input", "reason": "attempt-limit", "job_id": row["job_id"], "job_attempts_started": 0}
                    try:
                        package = row["package"]
                        if hashlib.sha256(package.encode()).hexdigest() != row["package_sha256"]:
                            raise ValueError("Frozen package changed")
                        job = json.loads(package)
                        validate_package(self.root, job)
                    except (ValueError, OSError, KeyError, TypeError):
                        db.execute("UPDATE scoped_jobs SET status='needs-input',reason='package-invalid-or-mutated',updated_at=? WHERE job_id=?", (_now(), row["job_id"]))
                        return {"status": "needs-input", "reason": "package-invalid-or-mutated", "job_id": row["job_id"], "job_attempts_started": 0}
                    attempt = row["attempt"] + 1
                    db.execute("UPDATE scoped_jobs SET status='running',reason='explicit-run-in-progress',attempt=?,updated_at=? WHERE job_id=?", (attempt, _now(), row["job_id"]))
                # Transaction committed before any model subprocess.
                try:
                    meta = adapter(self.root, job, state_root=self.folder / "jobs" / row["package_sha256"], attempt=attempt, **adapter_kwargs)
                except Exception:
                    # Never persist exception text: it may include raw model data.
                    with self._db() as db:
                        db.execute("UPDATE scoped_jobs SET status='deferred',reason='adapter-interrupted',retry_not_before=?,updated_at=? WHERE job_id=?",
                            ((datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat(), _now(), row["job_id"]))
                    return {"status": "deferred", "reason": "adapter-interrupted", "job_id": row["job_id"], "job_attempts_started": 1}
                with self._db() as db:
                    self._finish(db, row["job_id"], meta)
                return {"job_id": row["job_id"], "status": meta["status"], "reason": meta["reason"], "metadata_path": meta["metadata_path"], "job_attempts_started": 1}
        except QueueBusy:
            return {"status": "busy", "reason": "another-scoped-job-running", "job_attempts_started": 0}


def main():
    parser = argparse.ArgumentParser(description="Isolated scoped model queue; no background worker")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    commands = parser.add_subparsers(dest="command", required=True)
    enqueue = commands.add_parser("enqueue")
    enqueue.add_argument("package")
    commands.add_parser("status")
    commands.add_parser("run-one")
    args = parser.parse_args()
    queue = ScopedQueue(args.project_root)
    if args.command == "enqueue":
        package_path = Path(args.package).resolve()
        if not package_path.is_relative_to(queue.root) or any(part.lower() == ".codex" or part.lower().startswith(".env") or part.lower() == "auth.json" or part.lower().endswith(".dpapi") for part in package_path.parts):
            parser.error("Package must be a noncredential project file")
        result = queue.enqueue(json.loads(package_path.read_text(encoding="utf-8")))
    elif args.command == "status":
        result = queue.status()
    else:
        result = queue.run_one()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

