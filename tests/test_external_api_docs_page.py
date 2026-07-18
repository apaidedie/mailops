from __future__ import annotations

import unittest

from tests._import_app import clear_login_attempts, import_web_app_module


class ExternalApiDocsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from mailops.db import get_db
            from mailops.repositories import settings as settings_repo

            db = get_db()
            db.execute("DELETE FROM external_api_keys")
            db.execute("DELETE FROM external_api_rate_limits")
            db.execute("DELETE FROM external_api_consumer_usage_daily")
            db.commit()
            settings_repo.set_setting("external_api_key", "docs-key")
            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("external_api_rate_limit_per_minute", "60")
            settings_repo.set_setting("external_api_ip_whitelist", "[]")
            settings_repo.set_setting("pool_external_enabled", "true")
            settings_repo.set_setting("active_mailbox_providers", "")
            settings_repo.set_setting("duckmail_bearer_token", "duckmail-docs-secret-should-not-leak")

    @staticmethod
    def _headers(value: str = "docs-key") -> dict[str, str]:
        return {"X-API-Key": value}

    def test_docs_page_requires_api_key(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/docs")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")

    def test_docs_page_renders_html_from_openapi_without_secret_values(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/docs", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("Content-Type", ""))
        html = resp.get_data(as_text=True)
        self.assertIn("Outlook Email Plus External API", html)
        self.assertIn("Integration Console", html)
        self.assertIn("API Surface", html)
        self.assertIn("Integration Readiness Bundle", html)
        self.assertIn("Session Lifecycle", html)
        self.assertIn("Provider Routing", html)
        self.assertIn("Endpoint Catalog", html)
        self.assertIn("Authenticated integration surface", html)
        self.assertIn("X-API-Key: &lt;your-api-key&gt;", html)
        self.assertIn("/api/v1/external/openapi.json", html)
        self.assertIn("/api/v1/external/integration-bundle", html)
        self.assertIn("/api/v1/external/capabilities", html)
        self.assertIn("/api/v1/external/providers", html)
        self.assertIn("/api/v1/external/mailboxes", html)
        self.assertIn("/api/v1/external/mailbox-sessions/start", html)
        self.assertIn("/api/v1/external/mailbox-sessions/read", html)
        self.assertIn("/api/v1/external/mailbox-sessions/close", html)
        self.assertIn("externalMailboxSessionStart", html)
        self.assertIn("externalMailboxSessionRead", html)
        self.assertIn("externalMailboxSessionClose", html)
        self.assertIn("MailboxSessionStartRequest", html)
        self.assertIn("MailboxSessionReadRequest", html)
        self.assertIn("MailboxSessionCloseRequest", html)
        self.assertIn("Discovery", html)
        self.assertIn("Mailbox Sessions", html)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(180px, 1fr))", html)
        self.assertIn("@media (max-width: 820px)", html)
        self.assertIn("overflow-wrap: anywhere", html)
        self.assertNotIn("docs-key", html)
        self.assertNotIn("duckmail-docs-secret-should-not-leak", html)
        self.assertNotRegex(html, r"dk_[0-9a-fA-F]{20,}")
        self.assertNotRegex(html, r"Bearer\s+[A-Za-z0-9_.-]+")
        self.assertNotIn("consumer_key=", html.lower())
        self.assertNotIn("refresh_token=", html.lower())

    def test_legacy_docs_alias_renders_same_contract(self):
        client = self.app.test_client()

        legacy = client.get("/api/v1/external/docs", headers=self._headers())
        versioned = client.get("/api/v1/external/docs", headers=self._headers())

        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(versioned.status_code, 200)
        legacy_html = legacy.get_data(as_text=True)
        versioned_html = versioned.get_data(as_text=True)
        self.assertIn("/api/v1/external/docs", legacy_html)
        self.assertIn("/api/v1/external/docs", versioned_html)
        self.assertIn("externalApiDocs", legacy_html)

    def test_docs_endpoint_is_discoverable_from_capabilities_and_providers(self):
        client = self.app.test_client()

        capabilities_resp = client.get("/api/v1/external/capabilities", headers=self._headers())
        providers_resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(capabilities_resp.status_code, 200)
        self.assertEqual(providers_resp.status_code, 200)
        capabilities = capabilities_resp.get_json()["data"]
        providers = providers_resp.get_json()["data"]
        for data in (capabilities, providers):
            self.assertEqual(data["endpoints"]["docs"], "/api/v1/external/docs")
            self.assertEqual(data["endpoints"]["integration_bundle"], "/api/v1/external/integration-bundle")
            self.assertEqual(data["legacy_endpoints"], {})
            self.assertEqual(data["documentation"]["entries"]["api_docs"]["endpoint"], "/api/v1/external/docs")
            self.assertNotIn("legacy_endpoint", data["documentation"]["entries"]["api_docs"])
            self.assertEqual(data["integration_manifest"]["discovery"]["endpoints"]["docs"], "/api/v1/external/docs")
            self.assertEqual(
                data["integration_manifest"]["discovery"]["endpoints"]["integration_bundle"],
                "/api/v1/external/integration-bundle",
            )
            self.assertNotIn("duckmail-docs-secret-should-not-leak", str(data))
            self.assertNotRegex(str(data), r"dk_[0-9a-fA-F]{20,}")

    def test_openapi_documents_docs_route_as_canonical_path(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/openapi.json", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("/api/v1/external/docs", data["paths"])
        self.assertIn("/api/v1/external/integration-bundle", data["paths"])
        self.assertNotIn("/api/external/docs", data["paths"])
        self.assertNotIn("/api/external/integration-bundle", data["paths"])
        self.assertEqual(data["paths"]["/api/v1/external/docs"]["get"]["operationId"], "externalApiDocs")
        self.assertEqual(
            data["paths"]["/api/v1/external/integration-bundle"]["get"]["operationId"], "externalIntegrationBundle"
        )
        self.assertEqual(data.get("x-legacy-endpoints") or {}, {})
        self.assertEqual(data["x-capabilities"]["documentation"]["entries"]["api_docs"]["endpoint"], "/api/v1/external/docs")


if __name__ == "__main__":
    unittest.main()
