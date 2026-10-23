"""
Aegis Dashboard Server - Local High-Aesthetic Web Command Room
Isolated Tactical Laboratory: daytrading/ui/serve_dashboard.py

Launches a lightweight, dependency-free local HTTP server serving the
Cyber-Institutional Trading War Room Dashboard on http://localhost:8765.
"""
from __future__ import annotations

import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

UI_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = UI_DIR.parent
TOOLS_DIR = DAYTRADING_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    from telemetry_blackbox import TelemetryBlackbox
    from adaptive_execution_engine import AdaptiveExecutionEngine
except ImportError:
    TelemetryBlackbox = None
    AdaptiveExecutionEngine = None


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/dashboard.html"
            return super().do_GET()
        elif self.path == "/api/10epochs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            ep_file = DAYTRADING_ROOT / "evidence" / "full_universe_10epoch_results.json"
            if ep_file.exists():
                self.wfile.write(ep_file.read_bytes())
            else:
                self.wfile.write(b"{}")
            return
        elif self.path == "/api/allweather":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            aw_file = DAYTRADING_ROOT / "evidence" / "allweather_converged_6cycle_results.json"
            if aw_file.exists():
                self.wfile.write(aw_file.read_bytes())
            else:
                self.wfile.write(b"{}")
            return
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            status_data = {
                "system": "AEGIS_TACTICAL_COMMAND",
                "version": "2.0.0",
                "timestamp": time.time(),
                "regime": "BULL_TREND",
                "tactical_cash_pct": 0.0,
                "sleeve_equity_gbp": 1000.00
            }
            if TelemetryBlackbox:
                try:
                    bb = TelemetryBlackbox()
                    status_data["telemetry"] = bb.summarize_telemetry()
                except Exception:
                    pass
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return
        return super().do_GET()

    def log_message(self, format, *args):
        # Quiet standard HTTP request logging
        pass


def run_server(port: int = 8765, open_browser: bool = True):
    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, DashboardHandler)
    except OSError:
        port = port + 1
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address, DashboardHandler)

    url = f"http://127.0.0.1:{port}/dashboard.html"
    print("\n" + "=" * 76)
    print("      AEGIS // CYBER-INSTITUTIONAL TRADING WAR ROOM DASHBOARD")
    print("=" * 76)
    print(f"[*] Serving locally at : {url}")
    print("[*] Architecture       : 100% Zero-Dependency Standalone Pure HTML5/Canvas/CSS")
    print("[*] Active Features    : Aegis Cash Reactor, Sonar Squeeze Radar, Crash Replayer")
    print("[*] Press Ctrl+C in terminal to stop server.\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Aegis Dashboard Server terminated gracefully.")
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="Serve Aegis Tactical Command Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Local port (default 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    run_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
