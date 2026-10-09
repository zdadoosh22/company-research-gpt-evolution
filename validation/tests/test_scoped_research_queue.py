import copy
import hashlib
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from scoped_research_queue import ScopedQueue
import test_scoped_research_adapter as adapter_fixture


class ScopedQueueTests(unittest.TestCase):
    def setUp(self):
        self.fixture = adapter_fixture.ScopedAdapterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root, self.job = self.fixture.root, self.fixture.job
        self.queue = ScopedQueue(self.root)
        self.calls = []

    def adapter(self, root, job, **kwargs):
        self.calls.append((root, job, kwargs))
        state = self.queue.status()["jobs"][0]
        self.assertEqual(state["status"], "running")
        return {"status": "scoped-analysis-complete", "reason": "analytical-output-validated", "continuation_required": False, "metadata_path": str(kwargs["state_root"] / "metadata.json")}

    def test_enqueue_persisted_idempotent_no_execution(self):
        self.assertTrue(self.queue.enqueue(self.job)["enqueued"])
        self.assertFalse(ScopedQueue(self.root).enqueue(self.job)["enqueued"])
        self.assertEqual(self.queue.status()["jobs"][0]["status"], "queued")
        self.assertFalse(self.queue.status()["background_enabled"])
        self.assertFalse((self.root / "state/observation").exists())
        changed = copy.deepcopy(self.job)
        changed["role"] = "review"
        with self.assertRaises(ValueError):
            self.queue.enqueue(changed)

    def test_explicit_one_job_then_stop(self):
        self.queue.enqueue(self.job)
        second = copy.deepcopy(self.job)
        second["job_id"] = "j2"
        self.queue.enqueue(second)
        result = self.queue.run_one(adapter=self.adapter)
        self.assertEqual(result["job_attempts_started"], 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([x["status"] for x in self.queue.status()["jobs"]], ["complete", "queued"])

    def test_worker_lock_prevents_second_job(self):
        self.queue.enqueue(self.job)
        with self.queue._worker_lock():
            result = ScopedQueue(self.root).run_one(adapter=self.adapter)
        self.assertEqual(result["status"], "busy")
        self.assertEqual(self.calls, [])

    def test_quota_deferred_backoff_visible(self):
        self.queue.enqueue(self.job)
        retry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        def deferred(root, job, **kwargs):
            return {"status": "partial", "reason": "quota-unavailable", "continuation_required": True, "retry_not_before": retry, "metadata_path": "saved-checkpoint"}
        self.queue.run_one(adapter=deferred)
        state = self.queue.status()["jobs"][0]
        self.assertEqual(state["status"], "deferred")
        self.assertEqual(state["retry_not_before"], retry)
        self.assertEqual(self.queue.run_one(adapter=self.adapter)["status"], "idle")
        self.assertEqual(self.calls, [])

    def test_partial_analytical_result_needs_input(self):
        self.queue.enqueue(self.job)
        def partial(root, job, **kwargs):
            return {"status": "withheld", "reason": "analytical-output-validated", "continuation_required": True, "metadata_path": "saved-checkpoint"}
        self.queue.run_one(adapter=partial)
        self.assertEqual(self.queue.status()["jobs"][0]["status"], "needs-input")
        self.assertEqual(self.queue.run_one(adapter=self.adapter)["status"], "idle")

    def test_package_mutation_before_model_prevents_call(self):
        self.queue.enqueue(self.job)
        (self.root / self.job["target"]["path"]).write_text("Modified")
        result = self.queue.run_one(adapter=self.adapter)
        self.assertEqual(result["reason"], "package-invalid-or-mutated")
        self.assertEqual(self.calls, [])

    def test_interruption_recovery_without_immediate_retry(self):
        self.queue.enqueue(self.job)
        with self.queue._db() as db:
            db.execute("UPDATE scoped_jobs SET status='running',attempt=1")
        result = ScopedQueue(self.root).run_one(adapter=self.adapter)
        self.assertEqual(result["status"], "idle")
        self.assertEqual(self.queue.status()["jobs"][0]["reason"], "worker-interrupted")
        self.assertEqual(self.calls, [])

    def completed_checkpoint(self):
        self.queue.enqueue(self.job)
        with self.queue._db() as db:
            digest = db.execute("SELECT package_sha256 FROM scoped_jobs").fetchone()[0]
            db.execute("UPDATE scoped_jobs SET status='running',attempt=1")
        checkpoint = self.queue.folder / "jobs" / digest / "run1" / "metadata.json"
        checkpoint.parent.mkdir(parents=True)
        result_path = checkpoint.parent / "result.json"
        result_path.write_text(json.dumps(self.fixture.output))
        meta = {"job_id": "j1", "attempt": 1, "completed_at": datetime.now(timezone.utc).isoformat(), "status": "scoped-analysis-complete", "reason": "analytical-output-validated", "continuation_required": False, "metadata_path": str(checkpoint), "result_path": str(result_path), "output_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}
        checkpoint.write_text(json.dumps(meta))
        return result_path

    def test_completed_checkpoint_recovers_without_duplicate_model_job(self):
        self.completed_checkpoint()
        self.assertEqual(self.queue.run_one(adapter=self.adapter)["status"], "idle")
        self.assertEqual(self.queue.status()["jobs"][0]["status"], "complete")
        self.assertEqual(self.calls, [])

    def test_missing_recovery_result_needs_input(self):
        self.completed_checkpoint().unlink()
        self.queue.run_one(adapter=self.adapter)
        self.assertEqual(self.queue.status()["jobs"][0]["reason"], "recovery-checkpoint-invalid")
        self.assertEqual(self.calls, [])

    def test_tampered_recovery_result_needs_input(self):
        self.completed_checkpoint().write_text("{}")
        self.queue.run_one(adapter=self.adapter)
        self.assertEqual(self.queue.status()["jobs"][0]["reason"], "recovery-checkpoint-invalid")
        self.assertEqual(self.calls, [])

    def test_exception_details_redacted_and_checkpoint_deferred(self):
        self.queue.enqueue(self.job)
        def failure(*args, **kwargs):
            raise RuntimeError("private-token-do-not-store")
        self.assertEqual(self.queue.run_one(adapter=failure)["reason"], "adapter-interrupted")
        self.assertNotIn("private-token", json.dumps(self.queue.status()))

    def test_queue_rejects_checkpoint_override(self):
        with self.assertRaises(ValueError):
            self.queue.run_one(adapter=self.adapter, state_root=self.root / "state/observation")


if __name__ == "__main__":
    unittest.main()
