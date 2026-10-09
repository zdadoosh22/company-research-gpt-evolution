import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from observation_research import MODEL, run_research, subscription_environment, validate_observation


def result():
    return {"status": "draft", "summary": "A dated filing observation.",
            "observations": [{"claim": "Revenue was disclosed.", "classification": "reported-fact",
                              "sources": [{"uri": "https://example.com/filing", "location": "Page 3, Revenue",
                                           "accessed_at": "2026-10-07T12:00:00Z", "read": True}]}],
            "uncertainties": ["Issuer statement needs review."], "continuation": "Review source."}


class FakeRunner:
    def __init__(self, auth="Logged in using ChatGPT", exit_code=0, detail="", output=None, timeout=False, model=MODEL, events=None, before_result=None):
        self.auth, self.exit_code, self.detail = auth, exit_code, detail
        self.output = result() if output is None else output
        self.timeout, self.model, self.calls = timeout, model, []
        self.events, self.before_result = events, before_result

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if args[1] == "login":
            return subprocess.CompletedProcess(args, 0, "", self.auth)
        if self.timeout:
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        if self.before_result:
            self.before_result()
        path = Path(args[args.index("--output-last-message") + 1])
        path.write_text(self.output if isinstance(self.output, str) else json.dumps(self.output), encoding="utf-8")
        events = json.dumps({"type": "thread.started", "model": self.model}) + "\n" + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 4}})
        return subprocess.CompletedProcess(args, self.exit_code, self.events if self.events is not None else events, self.detail)


class ObservationResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "context.md").write_text("Evidence", encoding="utf-8")
        self.job = {"job_id": "j1", "company": "APP", "question": "Inspect latest filing", "context_paths": ["context.md"]}

    def tearDown(self):
        self.temp.cleanup()

    def test_subscription_draft_and_explicit_safe_command(self):
        fake = FakeRunner()
        meta = run_research(self.root, self.job, runner=fake, environ={"PATH": "x", "OPENAI_API_KEY": "secret", "CODEX_HOME": "auth-location"})
        self.assertFalse(meta["continuation_required"])
        self.assertEqual(meta["status"], "needs-review")
        self.assertFalse(meta["analytical_approval"])
        args, kwargs = fake.calls[1]
        self.assertIn("--ignore-user-config", args)
        self.assertIn("--ephemeral", args)
        self.assertIn("read-only", args)
        self.assertIn('web_search="live"', args)
        self.assertIn('service_tier="default"', args)
        self.assertIn('forced_login_method="chatgpt"', args)
        self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
        self.assertEqual(kwargs["env"]["CODEX_HOME"], "auth-location")
        self.assertFalse(kwargs["shell"])
        self.assertTrue(Path(meta["metadata_path"]).is_relative_to(self.root / "state" / "research"))
        self.assertFalse((self.root / "companies").exists())

    def test_api_auth_refused_without_research_call(self):
        fake = FakeRunner(auth="Logged in using an API key")
        meta = run_research(self.root, self.job, runner=fake)
        self.assertEqual(meta["reason"], "chatgpt-auth-required")
        self.assertEqual(len(fake.calls), 1)

    def test_timeout_queues_continuation(self):
        meta = run_research(self.root, self.job, runner=FakeRunner(timeout=True))
        self.assertEqual(meta["reason"], "research-timeout")
        self.assertTrue(meta["continuation_required"])

    def test_quota_or_model_failure_no_paid_fallback(self):
        for detail, expected in [("usage limit reached", "quota-unavailable"), ("model unavailable", "model-unavailable")]:
            fake = FakeRunner(exit_code=1, detail=detail)
            meta = run_research(self.root, self.job, runner=fake)
            self.assertEqual(meta["reason"], expected)
            self.assertEqual(len(fake.calls), 2)
            self.assertTrue(meta["continuation_required"])

    def test_model_fallback_rejected(self):
        meta = run_research(self.root, self.job, runner=FakeRunner(model="gpt-6-luna"))
        self.assertEqual(meta["reason"], "invalid-research-output")

    def test_malformed_output_refused(self):
        for output in ["not json", {"status": "approved"}, {**result(), "buy_price": 10}]:
            meta = run_research(self.root, self.job, runner=FakeRunner(output=output))
            self.assertEqual(meta["reason"], "invalid-research-output")

    def test_unread_or_unlocated_citations_refused(self):
        for field, value in [("read", False), ("location", "unknown"), ("accessed_at", "2026-10-07")]:
            output = result()
            output["observations"][0]["sources"][0][field] = value
            with self.assertRaises(ValueError):
                validate_observation(output, self.root)

    def test_local_citation_boundary_and_existence(self):
        output = result()
        source = output["observations"][0]["sources"][0]
        for uri in ["../outside.md", "missing.md", "file:///etc/passwd"]:
            source["uri"] = uri
            with self.assertRaises(ValueError):
                validate_observation(output, self.root)
        source["uri"] = "context.md"
        self.assertEqual(validate_observation(output, self.root)["status"], "draft")

    def test_context_and_state_cannot_escape_root(self):
        with self.assertRaises(ValueError):
            run_research(self.root, {**self.job, "context_paths": ["../other"]}, runner=FakeRunner())
        with self.assertRaises(ValueError):
            run_research(self.root, self.job, state_root=self.root.parent, runner=FakeRunner())

    def test_credentials_and_provider_overrides_removed(self):
        env = subscription_environment({"OPENAI_BASE_URL": "host", "CODEX_API_KEY": "x", "GEMINI_API_KEY": "x", "AWS_SECRET_ACCESS_KEY": "x", "PATH": "ok"})
        self.assertEqual(env, {"PATH": "ok"})

    def test_actionable_text_refused(self):
        output = result()
        output["summary"] = "Buy now."
        with self.assertRaises(ValueError):
            validate_observation(output, self.root)

    def test_malformed_lifecycle_and_missing_completion_are_recoverable(self):
        for events in ["[]", "null", '{"type":"thread.started"}', '{"type":"turn.failed"}']:
            meta = run_research(self.root, self.job, runner=FakeRunner(events=events))
            self.assertEqual(meta["reason"], "invalid-research-output")
            self.assertTrue(meta["continuation_required"])
            self.assertTrue(Path(meta["metadata_path"]).exists())

    def test_no_actual_identity_is_inferred_from_requested_model(self):
        fake = FakeRunner(events='{"type":"turn.completed","usage":{"input_tokens":2}}')
        meta = run_research(self.root, self.job, runner=fake)
        self.assertFalse(meta["continuation_required"])
        self.assertIsNone(meta["actual_model"])
        self.assertEqual(meta["actual_model_verification"], "not-reported")
        self.assertFalse(meta["requested_settings_verified"])

    def test_audit_does_not_persist_raw_tool_or_error_secrets(self):
        events = '\n'.join([json.dumps({"type": "item.completed", "item": {"text": "sensitive-token-123"}}),
                           json.dumps({"type": "turn.completed", "usage": {"input_tokens": 2, "secret": "sensitive-token-123"}})])
        meta = run_research(self.root, self.job, runner=FakeRunner(events=events))
        audit = (Path(meta["metadata_path"]).parent / "events.jsonl").read_text()
        self.assertNotIn("sensitive-token-123", audit)
        self.assertNotIn("sensitive-token-123", Path(meta["metadata_path"]).read_text())

    def test_checkpoint_precedes_model_and_request_is_recoverable(self):
        def inspect_checkpoint():
            folder = next((self.root / "state" / "research").iterdir())
            meta = json.loads((folder / "metadata.json").read_text())
            self.assertEqual(meta["reason"], "research-in-progress")
            self.assertTrue(meta["continuation_required"])
            self.assertEqual(json.loads((folder / "request.json").read_text()), self.job)
            self.assertFalse(meta["context_manifest"][0]["reading_verified"])
        meta = run_research(self.root, self.job, runner=FakeRunner(before_result=inspect_checkpoint))
        self.assertFalse(meta["continuation_required"])

    def test_changed_context_requires_review_continuation(self):
        def change_context():
            (self.root / "context.md").write_text("Revised evidence")
        meta = run_research(self.root, self.job, runner=FakeRunner(before_result=change_context))
        self.assertEqual(meta["reason"], "invalid-research-output")
        self.assertTrue(meta["continuation_required"])

    def test_future_evidence_or_empty_unexplained_research_refused(self):
        output = result()
        output["observations"][0]["sources"][0]["accessed_at"] = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):
            validate_observation(output, self.root)
        output = result()
        output["observations"], output["uncertainties"] = [], []
        with self.assertRaises(ValueError):
            validate_observation(output, self.root)

    def test_forbidden_context_and_invalid_timeout_do_not_invoke_cli(self):
        (self.root / ".env.local").write_text("private")
        fake = FakeRunner()
        with self.assertRaises(ValueError):
            run_research(self.root, {**self.job, "context_paths": [".env.local"]}, runner=fake)
        for timeout in [True, 0, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                run_research(self.root, self.job, runner=fake, timeout_seconds=timeout)
        self.assertEqual(fake.calls, [])

    def test_non_provider_notification_secrets_are_not_inherited(self):
        env = subscription_environment({"TELEGRAM_BOT_TOKEN": "private", "SERVICE_PASSWORD": "private", "PATH": "ok"})
        self.assertEqual(env, {"PATH": "ok"})


if __name__ == "__main__":
    unittest.main()
