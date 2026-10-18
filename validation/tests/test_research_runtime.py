import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import time
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import research_runtime as runtime


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / runtime.CAPABILITY_CATALOG
TOOLS_OMITTED = object()


class FakeClient:
    def __init__(self, *, tools=TOOLS_OMITTED, timeout=False, request_model=None,
                 skip_model=None, duplicate=False, mutate_catalog=False):
        self.tools = tools
        self.timeout = timeout
        self.request_model = request_model
        self.skip_model = skip_model
        self.duplicate = duplicate
        self.mutate_catalog = mutate_catalog
        self.calls = []
        self.catalog_hashes = []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, "codex 0.162.0-alpha.17.2\n", "")
        if self.timeout:
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        requested = args[args.index("--model") + 1]
        if requested == self.skip_model:
            return subprocess.CompletedProcess(args, 1, "", "")
        model = self.request_model or args[args.index("--model") + 1]
        endpoint = json.loads(next(a.split("=", 1)[1] for a in args
            if a.startswith('model_providers.cr2_synthetic.base_url=')))
        catalog_path = json.loads(next(a.split("=", 1)[1] for a in args
            if a.startswith("model_catalog_json=")))
        catalog_bytes = Path(catalog_path).read_bytes()
        catalog = json.loads(catalog_bytes)
        assert set(catalog) == {"models"}
        assert {entry["slug"] for entry in catalog["models"]} == set(runtime.ROLE_MODELS.values())
        self.catalog_hashes.append(hashlib.sha256(catalog_bytes).hexdigest())
        for _ in range(2 if self.duplicate else 1):
            payload = {"model": model, "tool_choice": "auto"}
            if self.tools is not TOOLS_OMITTED:
                payload["tools"] = self.tools
            payload = json.dumps(payload).encode()
            request = Request(endpoint + "/responses", data=payload, headers={"Content-Type": "application/json"})
            try:
                urlopen(request, timeout=2)
            except HTTPError as exc:
                if exc.code != 400:
                    raise
                exc.read()
                exc.close()
        if self.mutate_catalog:
            Path(catalog_path).write_bytes(catalog_bytes + b" ")
        return subprocess.CompletedProcess(args, 1,
            '{"type":"item.completed","item":{"type":"error","message":"Code mode is unavailable because code-mode host is disabled"}}\n',
            "")


class ResearchRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.exe = self.root / "codex.exe"
        self.exe.write_bytes(b"synthetic test executable bytes")
        self.exe_hash = hashlib.sha256(self.exe.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def catalog_copy(self, mutate=None):
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        data = copy.deepcopy(data)
        if mutate:
            mutate(data)
        path = self.root / "catalog.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def verify(self, runner, catalog_path=CATALOG, **kwargs):
        # These tests exercise the Windows-specific contract on the supported
        # project host. Keep the executable check deterministic under mocks.
        with patch.object(runtime.os, "name", "nt"):
            return runtime.verify_client_tools(self.exe, expected_version="0.162.0-alpha.17.2",
                expected_sha256=self.exe_hash, catalog_path=catalog_path, runner=runner, **kwargs)

    def test_client_capture_is_pinned_and_factory_uses_same_restrictions(self):
        fake = FakeClient()
        facts = self.verify(fake)
        self.assertEqual([r["model"] for r in facts["requests"]], list(runtime.ROLE_MODELS.values()))
        self.assertEqual([r["tools"] for r in facts["requests"]], [[], []])
        self.assertEqual([r["tools_field_present"] for r in facts["requests"]], [False, False])
        self.assertEqual(facts["remote_inference_calls"], 0)
        self.assertFalse(facts["forwarding"])
        self.assertIn("backend model identity", facts["limitations"][0])
        source_hash = runtime.freeze_catalog(CATALOG)["catalog_sha256"]
        worker = runtime.build_worker_args(self.exe, role="analysis", catalog_path=CATALOG,
            expected_catalog_sha256=source_hash, model_catalog_path=self.root / "model_catalog.json",
            output_schema="schema.json", output_path="result.json")
        probe = fake.calls[1][0]
        for required in ("--ignore-user-config", "--ignore-rules", "--strict-config", "--ephemeral",
                "--skip-git-repo-check", "default_permissions=\"cr2_packet\"", "windows.sandbox=\"mxc\"",
                "permissions.cr2_packet.network.enabled=false", 'web_search="disabled"', "mcp_servers={}"):
            self.assertIn(required, worker)
            self.assertIn(required, probe)
        self.assertNotIn("--sandbox", worker)
        self.assertNotIn("read-only", worker)
        catalog_setting = next(a for a in worker if a.startswith("model_catalog_json="))
        staged_path = Path(json.loads(catalog_setting.split("=", 1)[1]))
        self.assertEqual(json.loads(staged_path.read_bytes()).keys(), {"models"})
        self.assertEqual(len(set(fake.catalog_hashes)), 1)
        self.assertNotIn("send_user_message_async", worker)
        self.assertNotIn("clock", worker)
        self.assertIn("send_message_to_user_async", worker)

    def test_unknown_model_catalog_is_rejected(self):
        path = self.catalog_copy(lambda data: data["selected_models"][0].update(slug="gpt-unknown"))
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "both selected"):
            runtime.freeze_catalog(path)

    def test_non_code_mode_catalog_is_rejected(self):
        path = self.catalog_copy(lambda data: data["selected_models"][0].update(tool_mode="text_only"))
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "code_mode_only"):
            runtime.freeze_catalog(path)

    def test_missing_selected_model_catalog_entry_is_rejected(self):
        path = self.catalog_copy(lambda data: data["selected_models"].pop())
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "both selected"):
            runtime.freeze_catalog(path)

    def test_models_catalog_filters_unrelated_models_and_preserves_selected_metadata(self):
        def mutate(data):
            data["models"] = copy.deepcopy(data.pop("selected_models")) + [
                {"slug": "unrelated-model", "tool_mode": "other", "private_unrelated_metadata": "discard"}]
            data["models"][0]["full_metadata_fixture"] = {"retained": True}
        path = self.catalog_copy(mutate)
        frozen = runtime.freeze_catalog(path)
        emitted = json.loads(frozen["model_catalog_json"])
        self.assertEqual(set(emitted), {"models"})
        self.assertEqual({item["slug"] for item in emitted["models"]}, set(runtime.ROLE_MODELS.values()))
        self.assertTrue(emitted["models"][0]["full_metadata_fixture"]["retained"])
        self.assertNotIn("private_unrelated_metadata", frozen["model_catalog_json"])

    def test_extra_serialized_tool_fails_closed(self):
        fake = FakeClient(tools=[{"type": "function", "name": "unexpected"}])
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "contained tools"):
            self.verify(fake)

    def test_present_null_or_object_tools_field_fails_closed(self):
        for malformed in (None, {"type": "function", "name": "unexpected"}):
            with self.subTest(tools=malformed):
                fake = FakeClient(tools=malformed)
                with self.assertRaisesRegex(runtime.RuntimeVerificationError, "exactly one valid"):
                    self.verify(fake)

    def test_client_timeout_fails_closed(self):
        fake = FakeClient(timeout=True)
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "timed out"):
            self.verify(fake)

    def test_real_timeout_kills_owned_descendant_holding_capture_pipes(self):
        # A child inherits stdout/stderr and outlives its sleeping parent.
        # Killing only the parent leaves communicate waiting for that child.
        code = ("import subprocess,sys,time; "
                "subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)']); "
                "print('started',flush=True); time.sleep(20)")
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            runtime.bounded_client_run([sys.executable, "-c", code],
                capture_output=True, text=True, timeout=0.5)
        self.assertLess(time.monotonic() - started, 10)

    def test_bounded_client_preserves_successful_capture_and_input(self):
        result = runtime.bounded_client_run([sys.executable, "-c",
            "import sys; print(sys.stdin.read()); print('diagnostic',file=sys.stderr)"],
            input="synthetic", capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "synthetic")
        self.assertEqual(result.stderr.strip(), "diagnostic")

    def test_synthetic_environment_retains_required_os_paths_not_credentials(self):
        with patch.dict(runtime.os.environ, {"SystemDrive": "C:",
                "LOCALAPPDATA": "C:/synthetic/local", "OPENAI_API_KEY": "synthetic-secret"}):
            env = runtime._allowlisted_environment(self.root)
        self.assertEqual(env["SystemDrive"], "C:")
        self.assertEqual(env["LOCALAPPDATA"], "C:/synthetic/local")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertEqual(env["CODEX_HOME"], str(self.root))

    def test_exited_parent_does_not_wait_for_descendant_capture_eof(self):
        code = ("import subprocess,sys; "
                "subprocess.Popen([sys.executable,'-c','import time; time.sleep(2)']); "
                "print('parent-complete',flush=True)")
        started = time.monotonic()
        result = runtime.bounded_client_run([sys.executable, "-c", code],
            capture_output=True, text=True, timeout=1)
        self.assertEqual(result.returncode, 0)
        self.assertIn("parent-complete", result.stdout)
        self.assertLess(time.monotonic() - started, 1.8)

    def test_outer_deadline_bounds_a_child_stuck_outside_subprocess_execution(self):
        probe = self.root / "stuck-synthetic-probe.py"
        probe.write_text("import time; print('stuck cleanup',flush=True); time.sleep(20)")
        started = time.monotonic()
        with patch.object(runtime, "__file__", str(probe)), patch.object(runtime, "MAX_INSPECTION_SECONDS", 0.5):
            with self.assertRaisesRegex(runtime.RuntimeVerificationError, "Outer synthetic inspection deadline"):
                runtime.verify_client_tools(self.exe, expected_version="fixture",
                    expected_sha256=self.exe_hash, catalog_path=CATALOG)
        self.assertLess(time.monotonic() - started, 10)

    def test_unexpected_serialized_model_fails_closed(self):
        fake = FakeClient(request_model="gpt-other")
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "model mismatch"):
            self.verify(fake)

    def test_missing_request_from_one_process_fails_closed(self):
        fake = FakeClient(skip_model="gpt-6-astra")
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "exactly one valid"):
            self.verify(fake)

    def test_duplicate_request_from_one_process_fails_closed(self):
        fake = FakeClient(duplicate=True)
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "exactly one valid"):
            self.verify(fake)

    def test_staged_model_catalog_mutation_fails_closed(self):
        fake = FakeClient(mutate_catalog=True)
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "bytes changed"):
            self.verify(fake)

    def test_worker_factory_rejects_changed_source_catalog_hash(self):
        path = self.catalog_copy()
        pinned_hash = runtime.freeze_catalog(path)["catalog_sha256"]
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(runtime.RuntimeVerificationError, "hash differs"):
            runtime.build_worker_args(self.exe, role="analysis", catalog_path=path,
                expected_catalog_sha256=pinned_hash, model_catalog_path=self.root / "model_catalog.json",
                output_schema="schema.json", output_path="result.json")


if __name__ == "__main__":
    unittest.main()
