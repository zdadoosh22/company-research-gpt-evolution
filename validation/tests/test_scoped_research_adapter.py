import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from scoped_research_adapter import MODELS, run_scoped_job, validate_output, validate_package


class ScopedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        def artifact(path, text):
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            return {"path": path, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
        base = artifact("methodology/base.md", "Approved base")
        (self.root / "methodology/current.json").write_text(json.dumps({"file": base["path"], "sha256": base["sha256"]}))
        scoped = artifact("monitoring/DECISION-SCOPE.md", "Scoped design")
        target = artifact("work/target.md", "Scoped target")
        source = artifact("sources/filing.md", "Revenue 10. Archived filing")
        source.update(source_id="filing", published_at="2026-10-01T12:00:00Z", accessed_at="2026-10-02T12:00:00Z", read_locations=["Page 1, Revenue"])
        self.job = {"job_id": "j1", "role": "analysis", "as_of": "2026-10-02T12:00:00Z", "scope": {"required_categories": ["resilience"]}, "methodology": {"base": base, "scoped": scoped}, "target": target, "sources": [source]}
        self.ref = {"source_id": "filing", "location": "Page 1, Revenue"}
        self.output = {"status": "scoped-analysis-complete", "summary": "Source reviewed within scope.", "sources": [self.ref], "coverage": [{"category": "resilience", "status": "covered", "evidence": [self.ref]}], "findings": [], "gaps": [], "conclusions": [{"id": "c1", "claim": "Revenue disclosed.", "status": "supported", "evidence": [self.ref], "blocking_issues": [], "numerical_inputs": [{"name": "revenue", "value": 10, "basis": "reported", "explanation": "Archived filing in source units.", "evidence": [self.ref]}]}], "continuation": "Analytical scope complete; no trading approval."}
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def fake(self, *, auth="Logged in using ChatGPT", model="default", failure=None, mutation=None, output=None, events=None):
        def runner(args, **kwargs):
            self.calls.append((args, kwargs))
            if args[1] == "login":
                checkpoints = list(self.root.glob("state/scoped-research/*/metadata.json"))
                self.assertEqual(len(checkpoints), 1)
                self.assertEqual(json.loads(checkpoints[0].read_text())["reason"], "not-started")
                return subprocess.CompletedProcess(args, 0, "", auth)
            checkpoint = list(self.root.glob("state/scoped-research/*/metadata.json"))[0]
            self.assertEqual(json.loads(checkpoint.read_text())["reason"], "in-progress")
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, kwargs["timeout"])
            if failure:
                return subprocess.CompletedProcess(args, 1, "", failure)
            if mutation:
                mutation()
            Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(self.output if output is None else output))
            initial = {"type": "thread.started"}
            if model is not None:
                initial["model"] = args[args.index("--model") + 1] if model == "default" else model
            stdout = events if events is not None else json.dumps(initial) + "\n" + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10}, "secret": "sk-do-not-persist-credential"})
            return subprocess.CompletedProcess(args, 0, stdout, "Do not persist raw stderr")
        return runner

    def test_safe_subscription_command_and_checkpoint(self):
        meta = run_scoped_job(self.root, self.job, runner=self.fake(), environ={"PATH": "normal", "OPENAI_API_KEY": "secret-value", "TELEGRAM_BOT_TOKEN": "bot-secret"})
        self.assertEqual(meta["status"], "scoped-analysis-complete")
        self.assertFalse(meta["actionable"])
        self.assertFalse(meta["gate_activation"])
        self.assertFalse(meta["analytical_approval"])
        args, kwargs = self.calls[1]
        for arg in ("--ignore-user-config", "--ephemeral", "read-only", 'forced_login_method="chatgpt"', 'service_tier="default"', 'model_reasoning_effort="high"'):
            self.assertIn(arg, args)
        self.assertEqual(kwargs["env"], {"PATH": "normal"})
        folder = Path(meta["metadata_path"]).parent
        self.assertFalse((folder / "candidate.json").exists())
        self.assertNotIn("secret", (folder / "events.json").read_text())

    def test_review_requested_route_honest_unknown_backend(self):
        self.job["role"] = "review"
        self.output["status"] = "review-complete"
        meta = run_scoped_job(self.root, self.job, runner=self.fake(model=None))
        self.assertEqual(meta["status"], "review-complete")
        self.assertEqual(meta["model_requested"], "gpt-6-astra")
        self.assertIsNone(meta["actual_model"])
        self.assertEqual(meta["actual_model_verification"], "not-reported")
        self.assertFalse(meta["backend_independently_verified"])
        self.assertTrue(meta["selected_route_completed"])

    def test_auth_refused(self):
        meta = run_scoped_job(self.root, self.job, runner=self.fake(auth="Logged in using API key"))
        self.assertEqual(meta["reason"], "chatgpt-auth-required")
        self.assertEqual(len(self.calls), 1)

    def test_quota_model_timeout_defer_without_fallback(self):
        for failure, reason in [("usage limit reached", "quota-unavailable"), ("model unsupported", "model-unavailable"), ("timeout", "job-timeout")]:
            with self.subTest(failure=failure):
                self.calls.clear()
                # Each explicit attempt has one fresh checkpoint folder.
                temp = tempfile.TemporaryDirectory()
                self.addCleanup(temp.cleanup)
                meta = run_scoped_job(self.root, self.job, state_root=self.root / "state" / Path(temp.name).name, runner=self.failure_runner(failure), attempt=3)
                self.assertEqual(meta["reason"], reason)
                self.assertTrue(meta["continuation_required"])
                self.assertEqual(len(self.calls), 2)
                self.assertGreater((datetime.fromisoformat(meta["retry_not_before"]) - datetime.now(timezone.utc)).total_seconds(), 230)

    def failure_runner(self, failure):
        def runner(args, **kwargs):
            self.calls.append((args, kwargs))
            if args[1] == "login":
                return subprocess.CompletedProcess(args, 0, "Logged in using ChatGPT", "")
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 30)
            return subprocess.CompletedProcess(args, 1, "", failure)
        return runner

    def test_model_substitution_refused(self):
        meta = run_scoped_job(self.root, self.job, runner=self.fake(model="gpt-6-luna"))
        self.assertEqual(meta["status"], "partial")
        self.assertFalse(Path(meta["result_path"]).exists())

    def test_target_mutation_refused(self):
        meta = run_scoped_job(self.root, self.job, runner=self.fake(mutation=lambda: (self.root / self.job["target"]["path"]).write_text("Changed")))
        self.assertTrue(meta["continuation_required"])
        self.assertFalse(Path(meta["result_path"]).exists())

    def test_missing_completion_event_refused(self):
        meta = run_scoped_job(self.root, self.job, runner=self.fake(events='{"type":"thread.started"}'))
        self.assertEqual(meta["status"], "partial")

    def test_paths_hashes_and_method_before_call(self):
        for alter in [lambda j: j["target"].update(path="../outside.md"), lambda j: j["sources"][0].update(path=".codex/auth.json"), lambda j: j["target"].update(sha256="0" * 64), lambda j: j["methodology"]["scoped"].update(path="work/arbitrary.md")]:
            with self.subTest(alter=alter):
                job = copy.deepcopy(self.job)
                alter(job)
                with self.assertRaises(ValueError):
                    run_scoped_job(self.root, job, runner=self.fake())
                self.assertEqual(self.calls, [])

    def test_source_chronology(self):
        self.job["sources"][0]["published_at"] = "2026-10-03T12:00:00Z"
        with self.assertRaises(ValueError):
            validate_package(self.root, self.job)

    def test_unknown_publication_snapshot_date_contract(self):
        source = self.job["sources"][0]
        source["published_at"] = None
        with self.assertRaises(ValueError):
            validate_package(self.root, self.job)
        source.update(date_status="publication-date-unknown-snapshot", captured_at="2026-10-02T10:00:00Z")
        validate_package(self.root, self.job)
        source["captured_at"] = "2026-10-03T10:00:00Z"
        with self.assertRaises(ValueError):
            validate_package(self.root, self.job)
        source["captured_at"] = "2026-10-02T10:00:00Z"
        source["published_at"] = "2026-10-01T10:00:00Z"
        with self.assertRaises(ValueError):
            validate_package(self.root, self.job)

    def test_unknown_source_or_location(self):
        for field, value in [("source_id", "invented"), ("location", "Page 99")]:
            output = copy.deepcopy(self.output)
            output["sources"][0][field] = value
            with self.assertRaises(ValueError):
                validate_output(output, self.job, self.root)

    def test_missing_value_stays_null_and_blocks(self):
        number = self.output["conclusions"][0]["numerical_inputs"][0]
        number["basis"] = "missing"
        with self.assertRaises(ValueError):
            validate_output(self.output, self.job, self.root)
        number["value"] = None
        self.output["conclusions"][0]["status"] = "withheld"
        self.output["status"] = "partial"
        self.assertEqual(validate_output(self.output, self.job, self.root)["status"], "partial")

    def test_material_findings_block_conclusions(self):
        self.output["findings"] = [{"id": "f1", "severity": "material", "claim": "Unsupported timing", "evidence": [self.ref], "proposed_correction": "Reconcile", "outcome": "unresolved", "affected_conclusions": ["c1"]}]
        with self.assertRaises(ValueError):
            validate_output(self.output, self.job, self.root)
        self.output["status"] = "partial"
        self.output["conclusions"][0].update(status="withheld", blocking_issues=["f1"])
        validate_output(self.output, self.job, self.root)

    def test_actionable_and_credential_output_rejected(self):
        for text in ["Buy shares now", "Bearer abcdefghijklmnopqrstuvwxyz"]:
            output = copy.deepcopy(self.output)
            output["summary"] = text
            with self.assertRaises(ValueError):
                validate_output(output, self.job, self.root)

    def test_known_environment_secret_output_not_persisted(self):
        self.output["summary"] = "Known confidential value abcdefghijklmno"
        meta = run_scoped_job(self.root, self.job, runner=self.fake(), environ={"OPENAI_API_KEY": "abcdefghijklmno"})
        self.assertTrue(meta["continuation_required"])
        folder = Path(meta["metadata_path"]).parent
        self.assertFalse((folder / "candidate.json").exists())
        self.assertFalse((folder / "result.json").exists())
        self.assertNotIn("abcdefghijklmno", (folder / "metadata.json").read_text())

    def test_empty_or_duplicate_coverage_rejected(self):
        self.output["coverage"].append(copy.deepcopy(self.output["coverage"][0]))
        with self.assertRaises(ValueError):
            validate_output(self.output, self.job, self.root)


if __name__ == "__main__":
    unittest.main()
