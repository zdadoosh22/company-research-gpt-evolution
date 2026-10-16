import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from scoped_research_queue import ScopedQueue, package_sha256, scope_sha256, verify_dispatch
from scoped_research_adapter import MODELS
import test_scoped_research_adapter as adapter_tests


class ScopedQueueTests(unittest.TestCase):
    def setUp(self):
        fixture = adapter_tests.ScopedAdapterTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.fixture, self.root, self.job = fixture, fixture.root, fixture.job
        self.queue, self.calls = ScopedQueue(self.root), []

    def spec(self, job, stage="analysis", predecessor=None, bound=True):
        return {"job_id": job["job_id"], "stage": stage, "role": job["role"], "model": MODELS[job["role"]],
                "scope_sha256": scope_sha256(job), "package_sha256": package_sha256(job) if bound else None,
                "target_from_job_id": predecessor}

    def manifest(self, jobs=None):
        return {"schema_version": 1, "batch_id": "b1", "case_id": "case1", "version": 1,
                "created_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "purpose": "Fixture research and independent review", "provenance_refs": ["fixture-authority"],
                "call_limit": 4, "permitted_continuation": ["explicit-retry", "material-correction", "material-recheck"],
                "jobs": jobs or [self.spec(self.job)]}

    def prepare(self, manifest=None):
        self.queue.enqueue(self.job)
        auth = manifest or self.manifest()
        self.queue.authorize_batch(auth)
        return auth

    def run_job(self, **kwargs):
        return self.queue.run_one(job_id="j1", batch_id="b1", adapter=kwargs.pop("adapter", self.adapter), **kwargs)

    def decide(self, decision_id="retry1"):
        return self.queue.retry(job_id="j1", batch_id="b1", decision_id=decision_id,
                                rationale="Inspect failure and explicitly retry unchanged fixture", provenance_refs=["fixture-decision"])

    def checkpoint(self, job, kwargs, output=None, reason="analytical-output-validated"):
        # Fake workers save real request/result bytes; metadata alone is insufficient.
        folder = kwargs["state_root"] / ("fixture" + str(kwargs["attempt"]))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "request.json").write_text(json.dumps(job), encoding="utf-8")
        result = copy.deepcopy(output or self.fixture.output)
        if job["role"] == "review" and result["status"] == "scoped-analysis-complete":
            result["status"] = "review-complete"
        result_path, metadata_path = folder / "result.json", folder / "metadata.json"
        meta = {"job_id": job["job_id"], "attempt": kwargs["attempt"], "dispatch_id": kwargs["dispatch"]["dispatch_id"],
                "completed_at": datetime.now(timezone.utc).isoformat(), "model_requested": MODELS[job["role"]],
                "actual_model": MODELS[job["role"]], "status": result["status"], "reason": reason,
                "selected_route_completed": reason == "analytical-output-validated",
                "continuation_required": result["status"] in {"partial", "withheld"} or reason != "analytical-output-validated",
                "metadata_path": str(metadata_path), "result_path": str(result_path)}
        if reason == "analytical-output-validated":
            result_path.write_text(json.dumps(result), encoding="utf-8")
            meta["output_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        metadata_path.write_text(json.dumps(meta), encoding="utf-8")
        return meta

    def adapter(self, root, job, **kwargs):
        self.calls.append((root, job, kwargs))
        state = self.queue.status()
        self.assertEqual(next(r for r in state["jobs"] if r["job_id"] == job["job_id"])["status"], "running")
        self.assertEqual(state["dispatches"][-1]["dispatch_id"], kwargs["dispatch"]["dispatch_id"])
        self.assertGreaterEqual(state["cases"][0]["consumed_attempts"], 1)
        verify_dispatch(root, kwargs["dispatch"], job)
        return self.checkpoint(job, kwargs)

    def failed(self, root, job, **kwargs):
        self.calls.append((root, job, kwargs))
        verify_dispatch(root, kwargs["dispatch"], job)
        return self.checkpoint(job, kwargs, reason="job-timeout")

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

    def test_run_requires_both_names_and_recorded_authorization(self):
        self.queue.enqueue(self.job)
        with self.assertRaises(TypeError):
            self.queue.run_one(adapter=self.adapter)
        with self.assertRaises(TypeError):
            self.queue.run_one(job_id="j1", adapter=self.adapter)
        with self.assertRaises(ValueError):
            self.run_job()
        self.assertEqual(self.calls, [])

    def test_selected_job_leaves_older_unrelated_job_untouched(self):
        older = copy.deepcopy(self.job)
        older["job_id"] = "unrelated"
        self.queue.enqueue(older)
        self.prepare()
        self.assertEqual(self.run_job()["status"], "complete")
        self.assertEqual(self.queue.status()["jobs"][0]["status"], "queued")
        with self.assertRaises(ValueError):
            self.queue.run_one(job_id="unrelated", batch_id="b1", adapter=self.adapter)
        self.assertEqual(len(self.calls), 1)

    def test_completed_job_cannot_dispatch_twice(self):
        self.prepare()
        self.run_job()
        self.assertEqual(self.run_job()["job_attempts_started"], 0)
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)

    def test_worker_lock_prevents_second_job(self):
        self.prepare()
        with self.queue._worker_lock():
            result = ScopedQueue(self.root).run_one(job_id="j1", batch_id="b1", adapter=self.adapter)
        self.assertEqual(result["status"], "busy")
        self.assertEqual(self.calls, [])

    def test_failure_requires_explicit_decision_and_no_timer(self):
        self.prepare()
        self.assertEqual(self.run_job(adapter=self.failed)["status"], "needs-retry-decision")
        state = self.queue.status()
        self.assertIsNone(state["jobs"][0]["retry_not_before"])
        self.assertEqual(state["cases"][0]["consumed_attempts"], 1)
        self.assertEqual(self.run_job()["job_attempts_started"], 0)
        self.assertEqual(len(self.calls), 1)
        self.decide()
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        self.assertEqual(self.run_job()["status"], "complete")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 2)

    def test_retry_decision_idempotent_and_single_use(self):
        self.prepare()
        self.run_job(adapter=self.failed)
        self.assertTrue(self.decide()["recorded"])
        self.assertFalse(self.decide()["recorded"])
        self.run_job(adapter=self.failed)
        self.assertFalse(self.decide()["recorded"])
        self.assertEqual(self.run_job()["job_attempts_started"], 0)
        self.assertEqual(len(self.queue.status()["retry_decisions"]), 1)
        with self.assertRaises(ValueError):
            self.queue.retry(job_id="j1", batch_id="b1", decision_id="retry1", rationale="Changed", provenance_refs=["fixture-decision"])

    def test_four_attempt_ceiling_includes_failures(self):
        self.prepare()
        for number in range(4):
            if number:
                self.decide("retry" + str(number))
            self.assertEqual(self.run_job(adapter=self.failed)["job_attempts_started"], 1)
        with self.assertRaises(ValueError):
            self.decide("retry4")
        self.assertEqual(self.run_job()["job_attempts_started"], 0)
        self.assertEqual(self.queue.status()["cases"][0]["remaining_attempts"], 0)
        self.assertEqual(len(self.calls), 4)

    def test_authorization_rejects_fake_models_and_invalid_limits(self):
        self.queue.enqueue(self.job)
        for value in ("gpt-6-sol", "gpt-6-astra", "fake", "auto"):
            auth = self.manifest()
            auth["jobs"][0]["model"] = value
            with self.assertRaises(ValueError):
                self.queue.authorize_batch(auth)
        for limit in (0, 5, True):
            auth = self.manifest()
            auth["call_limit"] = limit
            with self.assertRaises(ValueError):
                self.queue.authorize_batch(auth)

    def test_versions_and_case_identity_cannot_reset_budget(self):
        auth = self.prepare()
        self.run_job(adapter=self.failed)
        self.assertFalse(self.queue.authorize_batch(auth)["recorded"])
        changed = copy.deepcopy(auth)
        changed["version"] = 2
        self.queue.authorize_batch(changed)
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        for key, value in (("case_id", "newcase"), ("call_limit", 3), ("expires_at", (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())):
            candidate = copy.deepcopy(changed)
            candidate.update(version=3)
            candidate[key] = value
            with self.assertRaises(ValueError):
                self.queue.authorize_batch(candidate)
        changed = copy.deepcopy(auth)
        changed["batch_id"] = "newbatch"
        with self.assertRaises(ValueError):
            self.queue.authorize_batch(changed)
        changed["case_id"] = "newcase"
        with self.assertRaises(ValueError):
            self.queue.authorize_batch(changed)

    def test_expired_batch_never_dispatches(self):
        self.prepare()
        with patch("scoped_research_queue.datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) + timedelta(days=1)
            clock.fromisoformat.side_effect = datetime.fromisoformat
            with self.assertRaises(ValueError):
                self.run_job()
        self.assertEqual(self.calls, [])

    def test_partial_output_needs_input_without_retry(self):
        self.prepare()
        def partial(root, job, **kwargs):
            verify_dispatch(root, kwargs["dispatch"], job)
            output = copy.deepcopy(self.fixture.output)
            output["status"] = "withheld"
            return self.checkpoint(job, kwargs, output=output)
        self.assertEqual(self.run_job(adapter=partial)["status"], "needs-input")
        self.assertEqual(self.run_job()["job_attempts_started"], 0)

    def test_mutation_prevents_call(self):
        self.prepare()
        (self.root / self.job["target"]["path"]).write_text("Modified")
        self.assertEqual(self.run_job()["reason"], "package-invalid-or-mutated")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 0)

    def test_exception_redacted_and_attempt_consumed(self):
        self.prepare()
        def failure(*args, **kwargs):
            raise RuntimeError("private-token-do-not-store")
        self.assertEqual(self.run_job(adapter=failure)["status"], "needs-retry-decision")
        state = self.queue.status()
        self.assertNotIn("private-token", json.dumps(state))
        self.assertEqual(state["cases"][0]["consumed_attempts"], 1)

    def test_metadata_only_success_rejected(self):
        self.prepare()
        def fabricated(root, job, **kwargs):
            return {"status": "scoped-analysis-complete", "reason": "analytical-output-validated", "continuation_required": False,
                    "metadata_path": str(kwargs["state_root"] / "fake" / "metadata.json")}
        self.assertEqual(self.run_job(adapter=fabricated)["status"], "needs-retry-decision")

    def test_result_schema_validated_not_just_hash(self):
        self.prepare()
        def invalid(root, job, **kwargs):
            verify_dispatch(root, kwargs["dispatch"], job)
            output = copy.deepcopy(self.fixture.output)
            output["conclusions"][0]["evidence"] = []
            return self.checkpoint(job, kwargs, output=output)
        self.assertEqual(self.run_job(adapter=invalid)["status"], "needs-retry-decision")

    def test_saved_request_mismatch_rejected(self):
        self.prepare()
        def changed(root, job, **kwargs):
            meta = self.adapter(root, job, **kwargs)
            (Path(meta["metadata_path"]).parent / "request.json").write_text("{}")
            return meta
        self.assertEqual(self.run_job(adapter=changed)["status"], "needs-retry-decision")

    def test_metadata_must_match_saved_file(self):
        self.prepare()
        def changed(root, job, **kwargs):
            meta = self.adapter(root, job, **kwargs)
            meta["reason"] = "different"
            return meta
        self.assertEqual(self.run_job(adapter=changed)["status"], "needs-retry-decision")

    def test_unknown_identity_consumed_without_backend_claim(self):
        self.prepare()
        def unknown(root, job, **kwargs):
            meta = self.adapter(root, job, **kwargs)
            meta.update(actual_model=None, backend_independently_verified=False)
            Path(meta["metadata_path"]).write_text(json.dumps(meta))
            return meta
        result = self.run_job(adapter=unknown)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        self.assertFalse(json.loads(Path(result["metadata_path"]).read_text())["backend_independently_verified"])

    def test_wrong_dispatch_identity_rejected(self):
        self.prepare()
        def changed(root, job, **kwargs):
            meta = self.adapter(root, job, **kwargs)
            meta["dispatch_id"] = "wrong-dispatch"
            Path(meta["metadata_path"]).write_text(json.dumps(meta))
            return meta
        self.assertEqual(self.run_job(adapter=changed)["status"], "needs-retry-decision")

    def test_success_without_claiming_dispatch_rejected(self):
        self.prepare()
        self.assertEqual(self.run_job(adapter=lambda root, job, **kwargs: self.checkpoint(job, kwargs))["status"], "needs-retry-decision")

    def test_model_substitution_checkpoint_rejected(self):
        self.prepare()
        def changed(root, job, **kwargs):
            meta = self.adapter(root, job, **kwargs)
            meta["actual_model"] = "gpt-6-sol"
            Path(meta["metadata_path"]).write_text(json.dumps(meta))
            return meta
        self.assertEqual(self.run_job(adapter=changed)["status"], "needs-retry-decision")

    def test_dispatch_claimed_once_and_fabrication_refused(self):
        self.prepare()
        def worker(root, job, **kwargs):
            with self.assertRaises(ValueError):
                verify_dispatch(root, dict(kwargs["dispatch"], model="fake"), job)
            verify_dispatch(root, kwargs["dispatch"], job)
            with self.assertRaises(ValueError):
                verify_dispatch(root, kwargs["dispatch"], job)
            return self.checkpoint(job, kwargs)
        self.assertEqual(self.run_job(adapter=worker)["status"], "complete")

    def interrupted(self, completed=False):
        self.prepare()
        def interrupted(root, job, **kwargs):
            verify_dispatch(root, kwargs["dispatch"], job)
            if completed:
                self.checkpoint(job, kwargs)
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_job(adapter=interrupted)

    def test_interruption_recovery_never_resubmits(self):
        self.interrupted()
        self.assertEqual(self.run_job()["status"], "needs-retry-decision")
        self.assertEqual(self.queue.status()["jobs"][0]["reason"], "worker-interrupted")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        self.assertEqual(self.calls, [])

    def test_completed_checkpoint_recovers_idempotently(self):
        self.interrupted(completed=True)
        for _ in range(2):
            self.assertEqual(self.run_job()["status"], "complete")
            self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        self.assertEqual(self.calls, [])

    def test_tampered_recovery_output_requires_decision(self):
        self.interrupted(completed=True)
        next(self.queue.folder.glob("jobs/*/*/result.json")).write_text("{}")
        self.assertEqual(self.run_job()["status"], "needs-retry-decision")
        self.assertEqual(self.queue.status()["jobs"][0]["reason"], "recovery-checkpoint-invalid")
        self.assertEqual(self.calls, [])

    def test_missing_recovery_output_requires_decision(self):
        self.interrupted(completed=True)
        next(self.queue.folder.glob("jobs/*/*/result.json")).unlink()
        self.assertEqual(self.run_job()["status"], "needs-retry-decision")
        self.assertEqual(self.queue.status()["jobs"][0]["reason"], "recovery-checkpoint-invalid")

    def test_duplicate_completed_checkpoint_is_ambiguous(self):
        self.interrupted(completed=True)
        original = next(self.queue.folder.glob("jobs/*/*/metadata.json"))
        second = original.parent.parent / "duplicate"
        second.mkdir()
        for name in ("request.json", "result.json"):
            (second / name).write_bytes((original.parent / name).read_bytes())
        meta = json.loads(original.read_text())
        meta.update(metadata_path=str(second / "metadata.json"), result_path=str(second / "result.json"))
        (second / "metadata.json").write_text(json.dumps(meta))
        self.assertEqual(self.run_job()["status"], "needs-retry-decision")

    def test_retry_cannot_run_without_permitted_continuation(self):
        auth = self.manifest()
        auth["permitted_continuation"] = []
        self.prepare(auth)
        self.run_job(adapter=self.failed)
        with self.assertRaises(ValueError):
            self.decide()

    def test_review_target_binds_later_without_new_scope_or_budget(self):
        review = copy.deepcopy(self.job)
        review.update(job_id="review1", role="review")
        auth = self.prepare(self.manifest([self.spec(self.job), self.spec(review, "review", "j1", False)]))
        meta = json.loads(Path(self.run_job()["metadata_path"]).read_text())
        review["target"] = {"path": str(Path(meta["result_path"]).relative_to(self.root)), "sha256": meta["output_sha256"]}
        self.queue.enqueue(review)
        with self.assertRaises(ValueError):
            self.queue.run_one(job_id="review1", batch_id="b1", adapter=self.adapter)
        auth["version"] = 2
        auth["jobs"][1]["package_sha256"] = package_sha256(review)
        self.queue.authorize_batch(auth)
        self.assertEqual(self.queue.run_one(job_id="review1", batch_id="b1", adapter=self.adapter)["status"], "complete")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 2)
        changed = copy.deepcopy(auth)
        changed["version"] = 3
        changed["jobs"][1]["job_id"] = "unlisted"
        with self.assertRaises(ValueError):
            self.queue.authorize_batch(changed)

    def test_review_cannot_bind_arbitrary_target(self):
        review = copy.deepcopy(self.job)
        review.update(job_id="review1", role="review")
        auth = self.prepare(self.manifest([self.spec(self.job), self.spec(review, "review", "j1", False)]))
        self.run_job()
        self.queue.enqueue(review)
        auth["version"] = 2
        auth["jobs"][1]["package_sha256"] = package_sha256(review)
        with self.assertRaises(ValueError):
            self.queue.authorize_batch(auth)

    def test_legacy_migration_preserves_records_and_attempts(self):
        self.queue.enqueue(self.job)
        with self.queue._db() as db:
            db.execute("DELETE FROM scoped_queue_migrations")
            db.execute("UPDATE scoped_jobs SET status='deferred',reason='job-timeout',attempt=2,retry_not_before='2020-01-01T00:00:00Z'")
            original = dict(db.execute("SELECT * FROM scoped_jobs").fetchone())
        self.queue = ScopedQueue(self.root)
        row = self.queue.status()["jobs"][0]
        self.assertEqual(row["status"], "needs-retry-decision")
        self.assertIsNone(row["retry_not_before"])
        with self.queue._db() as db:
            self.assertEqual(json.loads(db.execute("SELECT original_record FROM scoped_legacy_jobs").fetchone()[0]), original)
        self.queue.authorize_batch(self.manifest())
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 2)
        self.assertEqual(self.run_job()["job_attempts_started"], 0)
        self.decide()
        self.assertEqual(self.run_job()["status"], "complete")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 3)

    def test_owned_dispatch_parameters_cannot_be_overridden(self):
        for kwargs in ({"state_root": self.root / "state/observation"}, {"attempt": 0}, {"dispatch": {}}):
            with self.assertRaises(ValueError):
                self.run_job(**kwargs)


if __name__ == "__main__":
    unittest.main()
