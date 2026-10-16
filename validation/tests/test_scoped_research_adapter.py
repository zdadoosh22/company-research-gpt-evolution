import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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
        self.legacy = copy.deepcopy(self.job)
        data = (self.root / source["path"]).read_bytes()
        context = {"entity": "Example plc", "security": "EXAMPLE:ORD", "period": "FY2026", "basis": "reported", "unit": "million", "currency": "GBP"}
        self.job.update(schema_version=2, packet={"schema_version": 1, "context": context, "max_utf8_bytes": 20000,
            "passages": [{"source_id": "filing", "location": "Page 1, Revenue", "text_file": {"path": source["path"], "sha256": source["sha256"]},
                "range": {"start_byte": 0, "end_byte": len(data), "sha256": source["sha256"]}, "metadata": copy.deepcopy(context),
                "extraction": {"method": "utf8-byte-range", "version": "1", "status": "complete", "original_sha256": source["sha256"]},
                "table_context": {"kind": "prose", "headers": [], "footnotes": []}}]})
        self.runtime_patch = patch("scoped_research_adapter.runtime_capabilities", return_value={"status": "verified", "verified_live": False, "origin": "engineering fake; no live verification"})
        self.runtime = self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.claim = patch("scoped_research_queue.verify_dispatch", return_value={"dispatch_id": "fixture"}).start()
        self.addCleanup(patch.stopall)

    def run_job(self, job=None, **kwargs):
        job = self.job if job is None else job
        kwargs.setdefault("dispatch", {"dispatch_id": "fixture", "attempt": kwargs.get("attempt", 1)})
        return run_scoped_job(self.root, job, **kwargs)

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
        meta = self.run_job( runner=self.fake(), environ={"PATH": "normal", "OPENAI_API_KEY": "secret-value", "TELEGRAM_BOT_TOKEN": "bot-secret"})
        self.assertEqual(meta["status"], "scoped-analysis-complete")
        self.assertFalse(meta["actionable"])
        self.assertFalse(meta["gate_activation"])
        self.assertFalse(meta["analytical_approval"])
        args, kwargs = self.calls[1]
        for arg in ("--ignore-user-config", "--ephemeral", "read-only", 'forced_login_method="chatgpt"', 'service_tier="default"', 'model_reasoning_effort="high"'):
            self.assertIn(arg, args)
        self.assertEqual(kwargs["env"], {"PATH": "normal"})
        self.assertFalse(Path(kwargs["cwd"]).is_relative_to(self.root))
        self.assertFalse(Path(kwargs["cwd"]).exists())
        self.assertTrue(meta["engineering_test"])
        self.assertFalse(meta["runtime_verified_live"])
        self.assertEqual(meta["dispatch_id"], "fixture")
        self.assertIn("--strict-config", args)
        self.assertIn("shell_tool", args)
        self.assertNotIn(str(self.root), kwargs["input"])
        self.claim.assert_called_once()
        folder = Path(meta["metadata_path"]).parent
        self.assertFalse((folder / "candidate.json").exists())
        self.assertNotIn("secret", (folder / "events.json").read_text())

    def test_review_requested_route_honest_unknown_backend(self):
        self.job["role"] = "review"
        self.output["status"] = "review-complete"
        meta = self.run_job( runner=self.fake(model=None))
        self.assertEqual(meta["status"], "review-complete")
        self.assertEqual(meta["model_requested"], "gpt-6-astra")
        self.assertIsNone(meta["actual_model"])
        self.assertEqual(meta["actual_model_verification"], "not-reported")
        self.assertFalse(meta["backend_independently_verified"])
        self.assertTrue(meta["selected_route_completed"])

    def test_finished_review_with_material_findings_still_needs_disposition(self):
        self.job['role']='review';self.output['status']='review-complete'
        self.output['findings']=[dict(id='f1',severity='material',claim='Unsupported comparison',evidence=[],
            proposed_correction='Withhold affected comparison',outcome='withheld',affected_conclusions=['c1'])]
        self.output['conclusions'][0].update(status='withheld',blocking_issues=['f1'])
        meta=self.run_job(runner=self.fake())
        self.assertEqual(meta['execution_outcome'],'completed')
        self.assertTrue(meta['continuation_required'])
        self.assertFalse(meta['analytical_approval'])

    def test_auth_refused(self):
        meta = self.run_job( runner=self.fake(auth="Logged in using API key"))
        self.assertEqual(meta["reason"], "chatgpt-auth-required")
        self.assertEqual(len(self.calls), 1)

    def test_quota_model_timeout_defer_without_fallback(self):
        for failure, reason in [("usage limit reached", "quota-unavailable"), ("model unsupported", "model-unavailable"), ("timeout", "job-timeout")]:
            with self.subTest(failure=failure):
                self.calls.clear()
                # Each explicit attempt has one fresh checkpoint folder.
                temp = tempfile.TemporaryDirectory()
                self.addCleanup(temp.cleanup)
                meta = self.run_job( state_root=self.root / "state" / Path(temp.name).name, runner=self.failure_runner(failure), attempt=3)
                self.assertEqual(meta["reason"], reason)
                self.assertTrue(meta["continuation_required"])
                self.assertEqual(len(self.calls), 2)
                self.assertNotIn("retry_not_before", meta)
                self.assertTrue(meta["retry_decision_required"])

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
        meta = self.run_job( runner=self.fake(model="gpt-6-luna"))
        self.assertEqual(meta["status"], "partial")
        self.assertFalse(Path(meta["result_path"]).exists())

    def test_target_mutation_refused(self):
        meta = self.run_job( runner=self.fake(mutation=lambda: (self.root / self.job["target"]["path"]).write_text("Changed")))
        self.assertTrue(meta["continuation_required"])
        self.assertFalse(Path(meta["result_path"]).exists())

    def test_missing_completion_event_refused(self):
        meta = self.run_job( runner=self.fake(events='{"type":"thread.started"}'))
        self.assertEqual(meta["status"], "partial")

    def test_paths_hashes_and_method_before_call(self):
        for alter in [lambda j: j["target"].update(path="../outside.md"), lambda j: j["sources"][0].update(path=".codex/auth.json"), lambda j: j["target"].update(sha256="0" * 64), lambda j: j["methodology"]["scoped"].update(path="work/arbitrary.md")]:
            with self.subTest(alter=alter):
                job = copy.deepcopy(self.job)
                alter(job)
                with self.assertRaises(ValueError):
                    self.run_job(job, runner=self.fake())
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

    def test_private_account_json_cannot_be_authorized_by_hash(self):
        target=self.root/'state/observation/portfolio-private.json'
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text('{"cash":"300"}',encoding='utf-8')
        self.job['target']={'path':'state/observation/portfolio-private.json','sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(ValueError,'Private operational state'):
            validate_package(self.root,self.job)

    def test_actionable_and_credential_output_rejected(self):
        for text in ["Buy shares now", "Bearer abcdefghijklmnopqrstuvwxyz"]:
            output = copy.deepcopy(self.output)
            output["summary"] = text
            with self.assertRaises(ValueError):
                validate_output(output, self.job, self.root)

    def test_known_environment_secret_output_not_persisted(self):
        self.output["summary"] = "Known confidential value abcdefghijklmno"
        meta = self.run_job( runner=self.fake(), environ={"OPENAI_API_KEY": "abcdefghijklmno"})
        self.assertTrue(meta["continuation_required"])
        folder = Path(meta["metadata_path"]).parent
        self.assertFalse((folder / "candidate.json").exists())
        self.assertFalse((folder / "result.json").exists())
        self.assertNotIn("abcdefghijklmno", (folder / "metadata.json").read_text())

    def test_empty_or_duplicate_coverage_rejected(self):
        self.output["coverage"].append(copy.deepcopy(self.output["coverage"][0]))
        with self.assertRaises(ValueError):
            validate_output(self.output, self.job, self.root)


    def test_runtime_unavailable_never_calls_auth_or_worker(self):
        self.runtime.return_value = {"status": "unavailable", "verified_live": False}
        meta = self.run_job(runner=self.fake())
        self.assertEqual(meta["reason"], "runtime-restrictions-unverified")
        self.assertEqual(self.calls, [])
        self.claim.assert_not_called()
        self.assertFalse(meta["runtime_verified_live"])

    def test_direct_dispatch_bypass_refused(self):
        with self.assertRaisesRegex(ValueError, "Persisted queue dispatch"):
            run_scoped_job(self.root, self.job, runner=self.fake())
        self.assertEqual(self.calls, [])

    def test_legacy_read_compatible_but_new_dispatch_requires_compact(self):
        validate_package(self.root, self.legacy)
        validate_output(self.output, self.legacy, self.root)
        with self.assertRaisesRegex(ValueError, "compact job schema"):
            self.run_job(self.legacy, runner=self.fake())

    def test_unknown_or_mismatched_metadata_and_incomplete_extraction(self):
        for field in ("entity", "security", "period", "basis", "unit", "currency"):
            for value in (None, "different"):
                job = copy.deepcopy(self.job)
                job["packet"]["passages"][0]["metadata"][field] = value
                validate_package(self.root, job)
                with self.assertRaisesRegex(ValueError, "cannot qualify"):
                    validate_output(self.output, job, self.root)
        self.job["packet"]["passages"][0]["extraction"]["status"] = "incomplete"
        with self.assertRaisesRegex(ValueError, "cannot qualify"):
            validate_output(self.output, self.job, self.root)

    def test_unauthorized_tool_and_instruction_events_fail_closed(self):
        for event in ({"type": "item.completed", "item": {"type": "command_execution", "command": "read outside"}},
                      {"type": "unauthorized_tool"}, {"type": "instruction_injection"},
                      {"type": "item.started", "item": {"type": "mcp_tool_call"}}):
            with self.subTest(event=event):
                self.calls.clear()
                events = json.dumps(event) + '\n' + json.dumps({"type": "turn.completed"})
                meta = self.run_job(runner=self.failure_runner_events(events))
                self.assertFalse(Path(meta["result_path"]).exists())
                self.assertTrue(meta["retry_decision_required"])

    def failure_runner_events(self, events):
        def runner(args, **kwargs):
            self.calls.append((args, kwargs))
            if args[1] == "login":
                return subprocess.CompletedProcess(args, 0, "Logged in using ChatGPT", "")
            Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(self.output))
            return subprocess.CompletedProcess(args, 0, events, "")
        return runner

    def test_duplicate_dispatch_claim_prevents_inference(self):
        self.claim.side_effect = ValueError("Already consumed")
        meta = self.run_job(runner=self.fake())
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(meta["selected_route_completed"])


if __name__ == "__main__":
    unittest.main()
