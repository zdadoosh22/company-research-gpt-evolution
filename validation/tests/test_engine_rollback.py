"""Temporary-state compatibility and rollback exercise for the queue migration."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "ccd49d083c0e6921917a5d0b813b10b4955a6d72"
sys.path.insert(0, str(ROOT / "tools"))
from scoped_research_queue import ScopedQueue


class QueueRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.queue_dir = self.root / "state" / "scoped-research"
        self.queue_dir.mkdir(parents=True)
        self.database = self.queue_dir / "queue.sqlite"
        self.backup = Path(self.temp.name) / "pre-migration.sqlite"
        self.config_path = self.root / "monitoring" / "config.json"
        self.config_path.parent.mkdir(parents=True)
        self.config_bytes = b'{"research_enabled":false,"enabled":false,"mode":"observation-only"}\n'
        self.config_path.write_bytes(self.config_bytes)
        self.baseline_rows = [
            ("queued-1", "{\"job_id\":\"queued-1\"}", "a" * 64, "analysis", "queued", "explicitly-enqueued", 0, None, None,
             "2026-10-01T10:00:00+00:00", "2026-10-01T10:00:00+00:00"),
            ("deferred-1", "{\"job_id\":\"deferred-1\"}", "b" * 64, "analysis", "deferred", "job-timeout", 2,
             "2026-10-02T10:00:00+00:00", None, "2026-10-01T11:00:00+00:00", "2026-10-02T10:00:00+00:00"),
            ("complete-1", "{\"job_id\":\"complete-1\"}", "c" * 64, "review", "complete", "analytical-output-validated", 1, None,
             "state/scoped-research/jobs/abc/metadata.json", "2026-10-01T12:00:00+00:00", "2026-10-01T13:00:00+00:00"),
        ]
        self.columns = ("job_id", "package", "package_sha256", "role", "status", "reason", "attempt",
                        "retry_not_before", "metadata_path", "created_at", "updated_at")
        db = sqlite3.connect(self.database)
        try:
            db.execute("""CREATE TABLE scoped_jobs (
                job_id TEXT PRIMARY KEY, package TEXT NOT NULL, package_sha256 TEXT NOT NULL,
                role TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0, retry_not_before TEXT,
                metadata_path TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            db.executemany("INSERT INTO scoped_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", self.baseline_rows)
            db.commit()
        finally:
            db.close()

    def tearDown(self):
        self.temp.cleanup()

    def _rows(self, database):
        db = sqlite3.connect(database)
        try:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM scoped_jobs ORDER BY job_id")]
        finally:
            db.close()

    def _schema(self, database):
        db = sqlite3.connect(database)
        try:
            return [(row[1], row[2], row[3], row[4], row[5]) for row in db.execute("PRAGMA table_info(scoped_jobs)")]
        finally:
            db.close()

    def _load_baseline_queue(self):
        source = subprocess.run(
            ["git", "show", f"{BASELINE}:tools/scoped_research_queue.py"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        baseline_file = Path(self.temp.name) / "baseline_scoped_research_queue.py"
        baseline_file.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("baseline_scoped_research_queue", baseline_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ScopedQueue

    def test_migrate_backup_restore_and_baseline_status_inspection(self):
        baseline_schema = self._schema(self.database)
        baseline_rows = self._rows(self.database)
        # Make a consistent SQLite backup while the legacy database is open, then close it.
        source = sqlite3.connect(self.database)
        destination = sqlite3.connect(self.backup)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        backup_digest = hashlib.sha256(self.backup.read_bytes()).hexdigest()
        self.assertEqual(self._rows(self.backup), baseline_rows)
        self.assertEqual(self._schema(self.backup), baseline_schema)

        migrated = ScopedQueue(self.root)
        migrated_status = migrated.status()
        self.assertEqual([row["job_id"] for row in migrated_status["jobs"]], ["queued-1", "deferred-1", "complete-1"])
        self.assertEqual(next(row for row in migrated_status["jobs"] if row["job_id"] == "deferred-1")["status"], "needs-retry-decision")
        with migrated._db() as db:
            archive = {row["job_id"]: json.loads(row["original_record"])
                       for row in db.execute("SELECT job_id,original_record FROM scoped_legacy_jobs")}
            versions = [row[0] for row in db.execute("SELECT version FROM scoped_queue_migrations")]
        self.assertEqual(archive, {row["job_id"]: row for row in baseline_rows})
        self.assertEqual(versions, [2])
        self.assertEqual(self.config_path.read_bytes(), self.config_bytes)

        # Drop all queue objects/connections before restoring only the temporary database.
        del migrated
        shutil.copyfile(self.backup, self.database)
        db = sqlite3.connect(self.database)
        try:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        finally:
            db.close()
        self.assertEqual(tables, {"scoped_jobs"})
        self.assertEqual(self._schema(self.database), baseline_schema)
        self.assertEqual(self._rows(self.database), baseline_rows)
        self.assertEqual(self.config_path.read_bytes(), self.config_bytes)

        # Exercise the exact status reader from the recorded baseline source.
        baseline_queue = self._load_baseline_queue()(self.root)
        status = baseline_queue.status()
        self.assertEqual([row["job_id"] for row in status["jobs"]], ["queued-1", "deferred-1", "complete-1"])
        self.assertEqual(next(row for row in status["jobs"] if row["job_id"] == "deferred-1")["attempt"], 2)
        self.assertEqual(hashlib.sha256(self.backup.read_bytes()).hexdigest(), backup_digest)


if __name__ == "__main__":
    unittest.main()
