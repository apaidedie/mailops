from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from outlook_web import config


class ExternalApiCorsConfigTests(unittest.TestCase):
    def test_origin_config_normalizes_deduplicates_and_rejects_unsafe_values(self):
        raw = "\n".join(
            [
                "https://console.example.com/",
                "https://console.example.com",
                "http://localhost:3000",
                "*",
                "https://user:pass@example.com",
                "https://example.com/path",
                "https://example.com?query=1",
                "ftp://example.com",
                "not-an-origin",
            ]
        )

        with patch.dict(os.environ, {"EXTERNAL_API_CORS_ORIGINS": raw}, clear=False):
            result = config.get_external_api_cors_origin_config()

        self.assertEqual(result["origins"], ["https://console.example.com", "http://localhost:3000"])
        self.assertEqual(result["invalid_origin_count"], 6)
        self.assertNotIn("invalid_origins", result)

    def test_extension_origin_switch_defaults_true_and_can_be_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(config.get_external_api_cors_allow_chrome_extension())

        with patch.dict(os.environ, {"EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION": "false"}, clear=True):
            self.assertFalse(config.get_external_api_cors_allow_chrome_extension())


class ExternalApiCorsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="outlookEmail-cors-")
        self.app_module = None
        os.environ["SECRET_KEY"] = "test-secret-key-for-external-cors-policy"
        os.environ["DATABASE_PATH"] = str(Path(self.temp_dir.name) / "cors.db")
        os.environ["SCHEDULER_AUTOSTART"] = "false"
        os.environ["LOGIN_PASSWORD"] = "cors-test-password"

    def tearDown(self):
        if self.app_module is not None:
            self.app_module._APP_INSTANCE = None
        self.temp_dir.cleanup()
        for key in (
            "SECRET_KEY",
            "DATABASE_PATH",
            "SCHEDULER_AUTOSTART",
            "LOGIN_PASSWORD",
            "EXTERNAL_API_CORS_ORIGINS",
            "EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION",
        ):
            os.environ.pop(key, None)

    def _build_app(self, *, origins: str = "", allow_extension: bool | None = None):
        if origins:
            os.environ["EXTERNAL_API_CORS_ORIGINS"] = origins
        else:
            os.environ.pop("EXTERNAL_API_CORS_ORIGINS", None)
        if allow_extension is None:
            os.environ.pop("EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION", None)
        else:
            os.environ["EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION"] = "true" if allow_extension else "false"

        import outlook_web.app as app_module

        app_module._APP_INSTANCE = None
        self.app_module = importlib.reload(app_module)
        return self.app_module.create_app(autostart_scheduler=False)

    @staticmethod
    def _preflight(client, path: str, origin: str):
        return client.options(
            path,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type, X-API-Key, X-Request-Id, X-Trace-Id",
            },
        )

    def test_default_policy_allows_extensions_and_denies_web_origins(self):
        client = self._build_app().test_client()

        extension = self._preflight(client, "/api/v1/external/capabilities", "chrome-extension://abcdefghijklmnop")
        web = self._preflight(client, "/api/v1/external/capabilities", "https://console.example.com")

        self.assertEqual(extension.headers.get("Access-Control-Allow-Origin"), "chrome-extension://abcdefghijklmnop")
        self.assertIsNone(web.headers.get("Access-Control-Allow-Origin"))

    def test_configured_web_origin_covers_canonical_and_legacy_external_paths(self):
        client = self._build_app(origins="https://console.example.com,http://localhost:3000").test_client()

        for path in ("/api/v1/external/capabilities", "/api/v1/external/capabilities"):
            response = self._preflight(client, path, "https://console.example.com")
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "https://console.example.com")
            allow_headers = response.headers.get("Access-Control-Allow-Headers", "")
            for header in ("Content-Type", "X-API-Key", "X-Request-Id", "X-Trace-Id"):
                self.assertIn(header, allow_headers)
            self.assertIn("X-Trace-Id", response.headers.get("Access-Control-Expose-Headers", ""))

    def test_extension_support_can_be_disabled_without_disabling_web_origin(self):
        client = self._build_app(origins="https://console.example.com", allow_extension=False).test_client()

        extension = self._preflight(client, "/api/v1/external/capabilities", "chrome-extension://abcdefghijklmnop")
        web = self._preflight(client, "/api/v1/external/capabilities", "https://console.example.com")

        self.assertIsNone(extension.headers.get("Access-Control-Allow-Origin"))
        self.assertEqual(web.headers.get("Access-Control-Allow-Origin"), "https://console.example.com")

    def test_external_cors_policy_never_applies_to_internal_api(self):
        client = self._build_app(origins="https://console.example.com").test_client()

        response = self._preflight(client, "/api/accounts", "https://console.example.com")

        self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))

    def test_cors_does_not_bypass_external_api_key_authentication(self):
        client = self._build_app(origins="https://console.example.com").test_client()

        response = client.get("/api/v1/external/capabilities", headers={"Origin": "https://console.example.com"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "https://console.example.com")

    def test_capabilities_and_readiness_expose_safe_cors_contract(self):
        app = self._build_app(
            origins="https://console.example.com,*,https://example.com/path",
            allow_extension=False,
        )
        with app.app_context():
            from outlook_web.services.provider_catalog import (
                get_external_api_capabilities_contract,
                get_external_api_readiness_summary,
            )

            capabilities = get_external_api_capabilities_contract(consumer={"is_legacy": True})
            readiness = get_external_api_readiness_summary(consumer={"is_legacy": True})

        for contract in (capabilities["cors"], readiness["cors"]):
            self.assertEqual(contract["status"], "configured")
            self.assertEqual(contract["mode"], "allowlist")
            self.assertEqual(contract["allowed_origins"], ["https://console.example.com"])
            self.assertEqual(contract["allowed_origin_count"], 1)
            self.assertEqual(contract["invalid_origin_count"], 2)
            self.assertFalse(contract["chrome_extension_enabled"])
            self.assertFalse(contract["credentials"])
            self.assertNotIn("*", str(contract))
            self.assertNotIn("https://example.com/path", str(contract))


if __name__ == "__main__":
    unittest.main()
