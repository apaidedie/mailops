from __future__ import annotations

import unittest

from tests._import_app import clear_login_attempts, import_web_app_module


class ExternalApiVersionedAliasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from outlook_web.db import get_db
            from outlook_web.repositories import settings as settings_repo

            db = get_db()
            db.execute("DELETE FROM external_api_keys")
            db.execute("DELETE FROM external_api_rate_limits")
            db.execute("DELETE FROM external_api_consumer_usage_daily")
            db.commit()
            settings_repo.set_setting("external_api_key", "v1-key")
            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("external_api_rate_limit_per_minute", "60")
            settings_repo.set_setting("external_api_ip_whitelist", "[]")
            settings_repo.set_setting("pool_external_enabled", "false")
            settings_repo.set_setting("active_mailbox_providers", "")
            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("pool_default_provider", "")

    @staticmethod
    def _headers(value: str = "v1-key") -> dict[str, str]:
        return {"X-API-Key": value}

    def test_v1_discovery_is_authenticated_and_reports_legacy_removed(self):
        client = self.app.test_client()

        missing_key = client.get("/api/v1/external/capabilities")
        self.assertEqual(missing_key.status_code, 401)

        resp = client.get("/api/v1/external/capabilities", headers=self._headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]

        self.assertEqual(data["endpoints"]["capabilities"], "/api/v1/external/capabilities")
        self.assertEqual(data["endpoints"]["mailbox_session_read"], "/api/v1/external/mailbox-sessions/read")
        self.assertEqual(data["integration_manifest"]["discovery"]["endpoints"]["providers"], "/api/v1/external/providers")
        self.assertEqual(data["quickstart"]["endpoints"]["mailbox_session_start"], "/api/v1/external/mailbox-sessions/start")
        self.assertEqual(data["legacy_endpoints"], {})
        self.assertFalse(data["compatibility"]["legacy_supported"])
        self.assertEqual(data["compatibility"]["aliases"], {})
        self.assertEqual(data["compatibility"]["removed_legacy_prefix"], "/api/external")

    def test_v1_openapi_uses_canonical_paths_without_legacy_extension_map(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/openapi.json", headers=self._headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("/api/v1/external/capabilities", data["paths"])
        self.assertIn("/api/v1/external/mailbox-sessions/read", data["paths"])
        self.assertIn("/api/v1/external/pool/claim-random", data["paths"])
        self.assertIn("/api/v1/external/temp-emails/apply", data["paths"])
        self.assertNotIn("/api/external/capabilities", data["paths"])
        self.assertEqual(data["x-external-api-version"], "v1")
        self.assertEqual(data.get("x-legacy-endpoints") or {}, {})

    def test_representative_v1_routes_work(self):
        client = self.app.test_client()

        providers_resp = client.get("/api/v1/external/providers", headers=self._headers())
        self.assertEqual(providers_resp.status_code, 200)
        providers = providers_resp.get_json()["data"]
        self.assertEqual(providers["provider_health_endpoint"], "/api/v1/external/providers/{kind}/{provider}/health")

        health_resp = client.get("/api/v1/external/providers/temp/mail_tm/health", headers=self._headers())
        self.assertIn(health_resp.status_code, {200, 404})

        read_resp = client.post(
            "/api/v1/external/mailbox-sessions/read",
            headers=self._headers(),
            json={"session_type": "pool_claim", "read_action": "verification_code", "caller_id": "v1", "task_id": "v1"},
        )
        self.assertIn(read_resp.status_code, {400, 403, 404, 422})

    def test_legacy_paths_are_gone(self):
        client = self.app.test_client()

        legacy_resp = client.get("/api/external/capabilities", headers=self._headers())
        self.assertEqual(legacy_resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
