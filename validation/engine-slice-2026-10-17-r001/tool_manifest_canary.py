"""Synthetic loopback-only request inspection: no model, auth or forwarding.

This observes a custom-provider request, not the subscription route. Never
promote its result into a production capability attestation on its own.
"""
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from scoped_research_adapter import DISABLED_FEATURES


def main():
    executable = Path(sys.argv[1]).resolve(strict=True)
    observations = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 1024 * 1024:
                self.send_error(413)
                return
            payload = json.loads(self.rfile.read(size))
            tools = payload.get("tools", [])
            observations.append({"path": self.path,
                "model": payload.get("model"),
                "tools": [{"type": t.get("type"), "name": t.get("name"),
                    "schema_sha256": hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()}
                    for t in tools],
                "tool_choice": payload.get("tool_choice")})
            # No model exists here; reject permanently, never forward.
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"Synthetic inspection complete; no inference service","type":"invalid_request_error"}}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="cr2-tools-synthetic-") as stage:
            home = Path(stage) / "home"
            home.mkdir()
            env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP", "PATH") if k in os.environ}
            env.update(CODEX_HOME=str(home), NO_PROXY="127.0.0.1,localhost")
            base = f"http://127.0.0.1:{server.server_address[1]}/v1"
            settings = [
                'model_provider="cr2_synthetic"',
                'model_providers.cr2_synthetic.name="Local synthetic inspection only"',
                f'model_providers.cr2_synthetic.base_url="{base}"',
                'model_providers.cr2_synthetic.wire_api="responses"',
                'model_providers.cr2_synthetic.requires_openai_auth=false',
                'model_providers.cr2_synthetic.request_max_retries=0',
                'model_providers.cr2_synthetic.stream_max_retries=0',
                'web_search="disabled"', 'mcp_servers={}', 'project_doc_max_bytes=0',
                'approval_policy="never"', 'apps._default.enabled=false',
            ]
            args = [str(executable), "exec", "--ignore-user-config", "--ignore-rules", "--strict-config",
                "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
                "--model", "gpt-6.1-sol", "--json", "--color", "never"]
            for setting in settings:
                args += ["-c", setting]
            for feature in DISABLED_FEATURES:
                args += ["--disable", feature]
            args.append("-")
            result = subprocess.run(args, input="SYNTHETIC TOOL INVENTORY ONLY. No task or company data.",
                cwd=stage, env=env, text=True, encoding="utf-8", errors="replace",
                capture_output=True, timeout=35)
            record = {"created_at": datetime.now(timezone.utc).isoformat(),
                "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "provider": "cr2_synthetic", "authentication": "none; empty temporary CODEX_HOME",
                "remote_inference_calls": 0, "forwarding": False,
                "requests": observations, "returncode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr,
                "limitation": "Custom-provider tool inventory only; not subscription-route identity or isolation proof."}
            target = Path(__file__).with_name("SYNTHETIC-TOOL-MANIFEST.json")
            target.write_bytes((json.dumps(record, indent=2) + "\n").encode())
            print(json.dumps({"record": str(target), "requests": observations, "returncode": result.returncode}))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
