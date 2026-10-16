# Scoped queue rollback verification — 2026-10-16

The rollback exercise uses only a temporary project directory. It creates a legacy `scoped_jobs` SQLite database with queued, deferred, and completed records, plus a small observation-only config fixture. Before migration, it makes a consistent SQLite backup with the SQLite backup API and closes both connections.

The current `ScopedQueue` migration is then run against that temporary database. The test checks that all three records remain inspectable, that the original full row values are archived in `scoped_legacy_jobs`, that the deferred record is moved to `needs-retry-decision`, and that migration version 2 is recorded. The fixture config bytes remain unchanged.

After the queue object and database handles are closed, the test restores only the temporary queue database from the backup. It checks SQLite `integrity_check`, the original table set and column layout, and every original row value. It loads the queue source from baseline commit `ccd49d083c0e6921917a5d0b813b10b4955a6d72` and confirms that its `status()` reader can inspect the restored records, including the deferred attempt count.

Focused verification on 2026-10-16:

```text
python -m unittest validation.tests.test_engine_rollback
Ran 1 test in 0.096s
OK
```

This demonstrates a deterministic code-level rollback path for a temporary fixture. It does not demonstrate maintenance of a real service, an actual production database backup/restore, process shutdown coordination, or operational recovery. No model, queue worker, production database, or live service was invoked.
