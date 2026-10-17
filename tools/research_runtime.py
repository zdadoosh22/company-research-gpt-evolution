"""Restricted Codex client command construction and loopback tool inspection.

The inspection observes only the serialized request sent by this installed
client to a local provider that always rejects inference. It is not evidence of
backend model identity, subscription entitlement, or server-side restrictions.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from datetime import datetime, timezone


ROLE_MODELS = {"analysis": "gpt-6.1-sol", "review": "gpt-6-astra"}
CAPABILITY_CATALOG = Path("validation/engine-slice-2026-10-17-r001/MODEL-CAPABILITIES.json")
CLIENT_VERSION_RE = re.compile(r"(?<![A-Za-z0-9])\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?(?![A-Za-z0-9])")

DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "apps", "plugins", "remote_plugin", "hooks",
    "memories", "multi_agent", "multi_agent_v2", "browser_use", "browser_use_external",
    "computer_use", "in_app_browser", "image_generation", "view_image", "code_mode",
    "code_mode_host", "workspace_dependencies", "goals", "skill_search",
    "skill_mcp_dependency_install", "shell_snapshot", "unbounded_connection_retries",
    "send_message_to_user_async",
)


class RuntimeVerificationError(ValueError):
    """The candidate client did not satisfy a required runtime observation."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _windows_executable(executable) -> Path:
    path = Path(executable).resolve(strict=True)
    if os.name != "nt":
        raise RuntimeVerificationError("Windows client verification must run on Windows")
    if not path.is_file() or path.suffix.lower() != ".exe":
        raise RuntimeVerificationError("Candidate must be a concrete Windows executable")
    return path


def freeze_catalog(catalog_path=CAPABILITY_CATALOG, *, expected_sha256=None):
    """Freeze the two selected entries from an explicit, sanitized catalog.

    Source documents may expose ``selected_models`` or ``models``. The file
    written for the CLI always uses its model catalog object shape and contains
    only the two role-bound entries, preserving their complete metadata.
    """
    path = Path(catalog_path).resolve(strict=True)
    try:
        source_bytes = path.read_bytes()
        document = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeVerificationError("Capability catalog is unreadable or invalid JSON") from exc
    source_hash = _sha256(source_bytes)
    if expected_sha256 is not None and source_hash != expected_sha256:
        raise RuntimeVerificationError("Capability catalog hash differs from the pinned hash")
    if not isinstance(document, dict):
        raise RuntimeVerificationError("Capability catalog must be a JSON object")
    entries = document.get("selected_models", document.get("models"))
    if not isinstance(entries, list):
        raise RuntimeVerificationError("Capability catalog has no model entries")
    by_slug = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("slug"), str):
            raise RuntimeVerificationError("Capability catalog contains an invalid model entry")
        slug = entry["slug"]
        if slug in ROLE_MODELS.values() and slug in by_slug:
            raise RuntimeVerificationError("Capability catalog contains duplicate model entries")
        if slug in ROLE_MODELS.values():
            by_slug[slug] = entry
    if set(by_slug) != set(ROLE_MODELS.values()):
        raise RuntimeVerificationError("Capability catalog must contain both selected models")
    frozen = []
    for slug in ROLE_MODELS.values():
        entry = by_slug.get(slug)
        if not isinstance(entry, dict) or entry.get("tool_mode") != "code_mode_only":
            raise RuntimeVerificationError("Selected model is not explicitly code_mode_only")
        frozen.append(entry)
    roles = dict(ROLE_MODELS)
    cli_catalog = {"models": frozen}
    catalog_bytes = _canonical(cli_catalog)
    return {
        "models": frozen,
        "model_catalog_json": catalog_bytes.decode("utf-8"),
        "model_catalog_bytes": catalog_bytes,
        "catalog_sha256": source_hash,
        "frozen_catalog_sha256": _sha256(catalog_bytes),
        "roles_sha256": _sha256(_canonical(roles)),
        "roles": roles,
    }


def write_model_catalog(stage, catalog):
    """Write and hash-check the exact frozen catalog bytes for CLI startup."""
    destination = Path(stage).resolve() / "model_catalog.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(catalog["model_catalog_bytes"])
    if _sha256(destination.read_bytes()) != catalog["frozen_catalog_sha256"]:
        raise RuntimeVerificationError("Staged model catalog hash differs")
    return destination.resolve(strict=True)


def _assert_pinned_model_catalog(path, catalog):
    try:
        digest = _sha256(Path(path).read_bytes())
    except OSError as exc:
        raise RuntimeVerificationError("Pinned model catalog disappeared") from exc
    if digest != catalog["frozen_catalog_sha256"]:
        raise RuntimeVerificationError("Pinned model catalog bytes changed")


def restricted_settings(model_catalog_path, *, provider_override=None):
    """Return shared deny-by-default settings; provider override is probe-only."""
    settings = [
        'model_reasoning_effort="high"', 'service_tier="default"',
        'web_search="disabled"', 'approval_policy="never"',
        'project_doc_max_bytes=0', 'mcp_servers={}', 'apps._default.enabled=false',
        'features.code_mode_host=false', 'default_permissions="cr2_packet"',
        'windows.sandbox="mxc"',
        'permissions.cr2_packet.filesystem={":minimal"="read",":workspace_roots"="read","C:/Windows/Temp"="deny"}',
        'permissions.cr2_packet.network.enabled=false',
        'permissions.cr2_packet.network.allow_local_binding=false',
        "model_catalog_json=" + json.dumps(str(Path(model_catalog_path).resolve()), ensure_ascii=False),
    ]
    if provider_override is None:
        settings[:0] = ['forced_login_method="chatgpt"', 'model_provider="openai"']
    else:
        settings[:0] = [
            'model_provider="cr2_synthetic"',
            'model_providers.cr2_synthetic.name="Local synthetic inspection only"',
            'model_providers.cr2_synthetic.base_url=' + json.dumps(provider_override),
            'model_providers.cr2_synthetic.wire_api="responses"',
            'model_providers.cr2_synthetic.requires_openai_auth=false',
            'model_providers.cr2_synthetic.request_max_retries=0',
            'model_providers.cr2_synthetic.stream_max_retries=0',
        ]
    return settings


def build_exec_args(executable, *, model, model_catalog_path, output_schema=None,
                    output_path=None, provider_override=None):
    """Build the one CLI profile used by workers and the local inspection."""
    args = [str(executable), "exec", "--ignore-user-config", "--ignore-rules", "--strict-config",
        "--ephemeral", "--skip-git-repo-check", "--model", model, "--json", "--color", "never"]
    for setting in restricted_settings(model_catalog_path, provider_override=provider_override):
        args.extend(["-c", setting])
    for feature in DISABLED_FEATURES:
        args.extend(["--disable", feature])
    if output_schema is not None:
        args.extend(["--output-schema", str(output_schema)])
    if output_path is not None:
        args.extend(["--output-last-message", str(output_path)])
    return args


def build_worker_args(executable, *, role, catalog_path, expected_catalog_sha256,
                      model_catalog_path, output_schema, output_path):
    """Build worker args after revalidating and writing the pinned catalog."""
    catalog = freeze_catalog(catalog_path, expected_sha256=expected_catalog_sha256)
    written_path = write_model_catalog(Path(model_catalog_path).parent, catalog)
    if Path(model_catalog_path).resolve() != written_path:
        raise RuntimeVerificationError("Worker model catalog path must be model_catalog.json in its stage")
    if role not in catalog["roles"]:
        raise RuntimeVerificationError("Unknown worker role")
    return build_exec_args(executable, model=catalog["roles"][role],
        model_catalog_path=written_path, output_schema=output_schema,
        output_path=output_path)


def _allowlisted_environment(home):
    keys = ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP", "PATH")
    env = {key: os.environ[key] for key in keys if key in os.environ}
    env.update(CODEX_HOME=str(home), NO_PROXY="127.0.0.1,localhost")
    return env


def _version_and_hash(executable, expected_version, expected_sha256, runner, env, cwd):
    digest = _sha256(executable.read_bytes())
    if digest != expected_sha256:
        raise RuntimeVerificationError("Candidate executable hash differs from the pinned hash")
    try:
        completed = runner([str(executable), "--version"], cwd=str(cwd), env=env,
            text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=15)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeVerificationError("Version check timed out") from exc
    if completed.returncode != 0:
        raise RuntimeVerificationError("Candidate version check failed")
    version_text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    versions = set(CLIENT_VERSION_RE.findall(version_text))
    if versions != {expected_version}:
        raise RuntimeVerificationError("Candidate client version differs from the pinned version")
    return {"sha256": digest, "version": expected_version}


def verify_client_tools(executable, *, expected_version, expected_sha256,
                        catalog_path=CAPABILITY_CATALOG, runner=subprocess.run,
                        expected_catalog_sha256=None, timeout_seconds=35):
    """Capture both model request tool lists locally; never calls inference.

    The returned object is an evidence record, not a readiness boolean. Any
    unexpected request, tool, model, response, catalog value, or timeout raises.
    """
    executable = _windows_executable(executable)
    catalog = freeze_catalog(catalog_path, expected_sha256=expected_catalog_sha256)
    observations = []
    unexpected = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            # A partial local request must not strand shutdown after the CLI
            # timeout. This diagnostic never accepts a public connection.
            self.connection.settimeout(5)

        def send_error(self, code, message=None, explain=None):
            unexpected.append("unexpected-http-request")
            return super().send_error(code, message, explain)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 1024 * 1024:
                    raise ValueError("invalid body length")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("request body is not an object")
                # Responses requests may omit the optional tools field when
                # no tools are offered. Preserve omission distinctly; a
                # present null/object field is not accepted as an empty list.
                tools = payload.get("tools", [])
                if not isinstance(tools, list):
                    raise ValueError("serialized tools field is missing or invalid")
                observations.append({"path": self.path, "model": payload.get("model"),
                    "tools": tools,
                    "tools_field_present": "tools" in payload,
                    "tool_list_sha256": _sha256(_canonical(tools)),
                    "tool_choice": payload.get("tool_choice")})
            except (ValueError, TypeError, json.JSONDecodeError):
                unexpected.append("invalid-request")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"Synthetic inspection complete; no inference service","type":"invalid_request_error"}}')

        def do_GET(self):
            unexpected.append("unexpected-http-method")
            self.send_error(400)

        def do_PUT(self):
            unexpected.append("unexpected-http-method")
            self.send_error(400)

        def do_DELETE(self):
            unexpected.append("unexpected-http-method")
            self.send_error(400)

        def log_message(self, *_args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.2
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="cr2-runtime-inspection-") as stage:
            stage_path = Path(stage)
            home = stage_path / "home"
            home.mkdir()
            env = _allowlisted_environment(home)
            version_info = _version_and_hash(executable, expected_version, expected_sha256,
                runner, env, stage_path)
            model_catalog_path = write_model_catalog(stage_path, catalog)
            endpoint = f"http://127.0.0.1:{server.server_address[1]}/v1"
            attempts = []
            for model in catalog["roles"].values():
                _assert_pinned_model_catalog(model_catalog_path, catalog)
                args = build_exec_args(executable, model=model,
                    model_catalog_path=model_catalog_path, provider_override=endpoint)
                request_offset = len(observations)
                unexpected_offset = len(unexpected)
                try:
                    result = runner(args, input="SYNTHETIC TOOL INVENTORY ONLY. No task or company data.",
                        cwd=stage, env=env, text=True, encoding="utf-8", errors="replace",
                        capture_output=True, timeout=timeout_seconds)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeVerificationError("Synthetic client inspection timed out") from exc
                attempts.append({"requested_model": model, "returncode": result.returncode,
                    "stdout_sha256": _sha256((result.stdout or "").encode("utf-8")),
                    "stderr_sha256": _sha256((result.stderr or "").encode("utf-8")),
                    "code_mode_host_disabled_warning": "code-mode host is disabled" in
                        ((result.stdout or "") + (result.stderr or "")).lower()})
                if result.returncode == 0:
                    raise RuntimeVerificationError("Synthetic provider rejection did not fail the client turn")
                _assert_pinned_model_catalog(model_catalog_path, catalog)
                received = observations[request_offset:]
                if len(received) != 1 or len(unexpected) != unexpected_offset:
                    error = RuntimeVerificationError("Each model process must make exactly one valid loopback request")
                    # This process used no account authentication and only a
                    # synthetic prompt. Preserve bounded diagnostics so a
                    # configuration failure does not invite blind retries.
                    error.diagnostic = {"model": model, "returncode": result.returncode,
                        "stdout": (result.stdout or "")[:4096],
                        "stderr": (result.stderr or "")[:4096],
                        "requests": received, "unexpected": unexpected[unexpected_offset:]}
                    raise error
                item = received[0]
                if item.get("path") != "/v1/responses" or item.get("model") != model:
                    raise RuntimeVerificationError("Unexpected path or model mismatch in model process request")
                if item["tools"]:
                    raise RuntimeVerificationError("Serialized request contained tools")
            if unexpected or len(observations) != len(catalog["roles"]):
                raise RuntimeVerificationError("Unexpected or missing loopback request")
            by_model = {}
            for item in observations:
                model = item.get("model")
                if item.get("path") != "/v1/responses" or model not in catalog["roles"].values() or model in by_model:
                    raise RuntimeVerificationError("Unexpected path, model, or duplicate request")
                by_model[model] = item
            if set(by_model) != set(catalog["roles"].values()):
                raise RuntimeVerificationError("Not every selected model was observed")
            for attempt in attempts:
                observed = by_model[attempt["requested_model"]]
                if observed["model"] != attempt["requested_model"]:
                    raise RuntimeVerificationError("Requested model and serialized model differ")
            configuration = {
                "base_args": ["exec", "--ignore-user-config", "--ignore-rules", "--strict-config",
                    "--ephemeral", "--skip-git-repo-check", "--json", "--color", "never"],
                "disabled_features": list(DISABLED_FEATURES),
                "worker_settings": restricted_settings(model_catalog_path),
                "verification_settings": restricted_settings(model_catalog_path,
                    provider_override=endpoint),
                "sandbox_profile_evidence": "MXC command profile from dated canary evidence",
                "provider_override_scope": "unauthenticated loopback only for verification",
            }
            return {
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "client": version_info,
                "capability_catalog_sha256": catalog["catalog_sha256"],
                "frozen_selected_catalog_sha256": catalog["frozen_catalog_sha256"],
                "selected_capabilities": [{key: entry.get(key) for key in
                    ("slug", "tool_mode", "shell_type", "experimental_supported_tools")}
                    for entry in catalog["models"]],
                "model_catalog_path": str(model_catalog_path),
                "roles_sha256": catalog["roles_sha256"],
                "configuration_sha256": _sha256(_canonical(configuration)),
                "configuration": configuration,
                "requests": observations,
                "attempts": attempts,
                "authentication": "none; empty temporary CODEX_HOME and environment allowlist",
                "remote_inference_calls": 0,
                "forwarding": False,
                "scope": "client-serialized tool lists for the selected models and this exact installed CLI configuration",
                "limitations": [
                    "Does not establish backend model identity, subscription entitlement, or current call availability.",
                    "Does not establish server-side tool restrictions or exhaustive sandbox behavior.",
                    "MXC filesystem/network behavior remains supported only by the separately dated command canaries.",
                ],
            }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
