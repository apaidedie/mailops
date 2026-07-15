from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from scripts import healthcheck

REPO_ROOT = Path(__file__).resolve().parents[1]


class _HealthHandler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, str, bytes]] = {}

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        status, content_type, body = self.routes.get(
            self.path,
            (404, "application/json", b'{"status":"missing"}'),
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class HealthcheckScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _HealthHandler.routes = {
            "/healthz": (200, "application/json", json.dumps({"status": "ok"}).encode("utf-8")),
            "/bad-status": (200, "application/json", json.dumps({"status": "starting"}).encode("utf-8")),
            "/invalid-json": (200, "application/json", b"not-json"),
            "/plain-ok": (200, "text/plain", b"ok"),
            "/error": (503, "application/json", json.dumps({"status": "down"}).encode("utf-8")),
        }
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_healthy_json_response_succeeds(self) -> None:
        result = healthcheck.check_health(f"{self.base_url}/healthz", timeout=1)

        self.assertTrue(result.ok)
        self.assertIn("healthcheck ok", result.message)

    def test_plain_200_response_succeeds_without_json_contract(self) -> None:
        result = healthcheck.check_health(f"{self.base_url}/plain-ok", timeout=1)

        self.assertTrue(result.ok)

    def test_non_200_response_fails(self) -> None:
        result = healthcheck.check_health(f"{self.base_url}/error", timeout=1)

        self.assertFalse(result.ok)
        self.assertIn("HTTP 503", result.message)

    def test_json_status_must_be_ok(self) -> None:
        result = healthcheck.check_health(f"{self.base_url}/bad-status", timeout=1)

        self.assertFalse(result.ok)
        self.assertIn("status is not ok", result.message)

    def test_invalid_json_fails(self) -> None:
        result = healthcheck.check_health(f"{self.base_url}/invalid-json", timeout=1)

        self.assertFalse(result.ok)
        self.assertIn("invalid JSON", result.message)

    def test_connection_failure_exits_non_zero(self) -> None:
        with patch("scripts.healthcheck.urllib.request.urlopen", side_effect=OSError("connection refused")):
            result = healthcheck.check_health(f"{self.base_url}/healthz", timeout=1)

        self.assertFalse(result.ok)
        self.assertIn("connection refused", result.message)

    def test_cli_returns_expected_exit_codes(self) -> None:
        healthy = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/healthcheck.py"),
                "--url",
                f"{self.base_url}/healthz",
                "--timeout",
                "1",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        unhealthy = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/healthcheck.py"),
                "--url",
                f"{self.base_url}/bad-status",
                "--timeout",
                "1",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(healthy.returncode, 0, healthy.stderr)
        self.assertIn("healthcheck ok", healthy.stdout)
        self.assertEqual(unhealthy.returncode, 1)
        self.assertIn("status is not ok", unhealthy.stderr)
        self.assertEqual(healthcheck.main(["--url", f"{self.base_url}/healthz", "--timeout", "0"]), 2)


if __name__ == "__main__":
    unittest.main()
