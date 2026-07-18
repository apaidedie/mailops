from __future__ import annotations

import importlib
import os
import unittest
from pathlib import Path


class SecurityHeadersTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("SECRET_KEY", "test-secret-key-for-security-headers")
        os.environ.setdefault("DATABASE_PATH", ":memory:")

        import mailops.app as app_module

        app_module._APP_INSTANCE = None
        self.app_module = importlib.reload(app_module)
        self.app = self.app_module.create_app(autostart_scheduler=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_module._APP_INSTANCE = None
        for key in ("SECURITY_HEADERS_ENABLED", "SECURITY_HEADERS_FORCE_HSTS", "SECURITY_HSTS_MAX_AGE"):
            os.environ.pop(key, None)

    def test_html_response_has_baseline_security_headers(self):
        resp = self.client.get("/")

        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("camera=()", resp.headers.get("Permissions-Policy", ""))
        csp = resp.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_json_response_has_security_headers_and_trace_id(self):
        resp = self.client.get("/healthz")

        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", resp.headers.get("Content-Security-Policy", ""))
        self.assertTrue(resp.headers.get("X-Trace-Id"))

    def test_static_cache_control_is_preserved_with_security_headers(self):
        resp = self.client.get("/static/js/core/state/globals.js")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("max-age=3600", resp.headers.get("Cache-Control", ""))
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("default-src 'self'", resp.headers.get("Content-Security-Policy", ""))

    def test_dompurify_is_first_party_static_asset(self):
        template = Path("templates/index.html").read_text(encoding="utf-8")
        self.assertNotIn("cdn.jsdelivr.net", template)
        self.assertIn("vendor/dompurify.min.js", template)

        resp = self.client.get("/static/vendor/dompurify.min.js")

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"DOMPurify 3.0.8", resp.data[:256])
        csp = resp.headers.get("Content-Security-Policy", "")
        self.assertIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertNotIn("cdn.jsdelivr.net", csp)

    def test_hsts_only_on_secure_or_forced_requests(self):
        local_resp = self.client.get("/healthz")
        self.assertNotIn("Strict-Transport-Security", local_resp.headers)

        secure_resp = self.client.get("/healthz", base_url="https://localhost")
        self.assertEqual(secure_resp.headers.get("Strict-Transport-Security"), "max-age=31536000; includeSubDomains")
        self.assertIn("upgrade-insecure-requests", secure_resp.headers.get("Content-Security-Policy", ""))

    def test_force_hsts_env_enables_hsts_for_http(self):
        os.environ["SECURITY_HEADERS_FORCE_HSTS"] = "true"
        os.environ["SECURITY_HSTS_MAX_AGE"] = "86400"
        self.app_module._APP_INSTANCE = None
        self.app = self.app_module.create_app(autostart_scheduler=False)
        self.client = self.app.test_client()

        resp = self.client.get("/healthz")
        self.assertEqual(resp.headers.get("Strict-Transport-Security"), "max-age=86400; includeSubDomains")
        self.assertIn("upgrade-insecure-requests", resp.headers.get("Content-Security-Policy", ""))

    def test_security_headers_can_be_disabled(self):
        os.environ["SECURITY_HEADERS_ENABLED"] = "false"
        self.app_module._APP_INSTANCE = None
        self.app = self.app_module.create_app(autostart_scheduler=False)
        self.client = self.app.test_client()

        resp = self.client.get("/healthz")
        self.assertNotIn("X-Content-Type-Options", resp.headers)
        self.assertNotIn("Content-Security-Policy", resp.headers)

    def test_middleware_does_not_overwrite_existing_headers(self):
        from flask import Response

        from mailops.middleware.security_headers import attach_security_headers

        with self.app.test_request_context("/custom"):
            resp = Response("ok")
            resp.headers["X-Frame-Options"] = "SAMEORIGIN"
            resp.headers["Content-Security-Policy"] = "default-src 'none'"

            attach_security_headers(resp)

        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(resp.headers.get("Content-Security-Policy"), "default-src 'none'")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")

    def test_extension_cors_preflight_keeps_cors_and_security_headers(self):
        resp = self.client.options(
            "/api/v1/external/capabilities",
            headers={
                "Origin": "chrome-extension://abcdefghijklmnop",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-Key",
            },
        )

        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "chrome-extension://abcdefghijklmnop")
        self.assertIn("X-API-Key", resp.headers.get("Access-Control-Allow-Headers", ""))
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("default-src 'self'", resp.headers.get("Content-Security-Policy", ""))


if __name__ == "__main__":
    unittest.main()
