from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module

CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"


class _ProviderNameRecordingTempMailProvider:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def get_options(self):
        return {
            "domain_strategy": "auto_or_manual",
            "default_mode": "auto",
            "domains": [{"name": "ext-temp.test", "enabled": True, "is_default": True}],
            "prefix_rules": {
                "min_length": 1,
                "max_length": 32,
                "pattern": r"^[a-z0-9][a-z0-9._-]*$",
            },
            "provider": self.provider_name,
            "provider_name": self.provider_name,
            "provider_label": "DuckMail" if self.provider_name == "duckmail" else self.provider_name,
        }

    def create_mailbox(self, *, prefix=None, domain=None):
        return {
            "success": True,
            "email": f"{prefix or 'auto'}@{domain or 'ext-temp.test'}",
            "provider_name": self.provider_name,
            "meta": {
                "provider_name": self.provider_name,
                "provider_capabilities": {"delete_mailbox": True, "delete_message": True, "clear_messages": True},
            },
        }


class _EmptyAddressTempMailProvider(_ProviderNameRecordingTempMailProvider):
    def create_mailbox(self, *, prefix=None, domain=None):
        return {
            "success": True,
            "email": "",
            "provider_name": self.provider_name,
            "meta": {"provider_name": self.provider_name},
        }


class _HealthCheckTempMailProvider(_ProviderNameRecordingTempMailProvider):
    def health_check(self):
        return {
            "success": True,
            "method": "mock_health_check",
            "details": {
                "domain_count": 1,
                "api_base_url": "https://api.example.test",
                "author": "OutlookMail Plus",
                "notes": ["bearer should-not-leak-lowercase", "safe note"],
                "supported_modes": {"domains"},
                "bearer_token": "should-not-leak",
                "headers": ["Bearer should-not-leak"],
                "diagnostic_text": 'password: "secret-pass" refresh_token=rt-secret',
                "nested": {"message": "client_secret=client-secret-value", "safe": "ok"},
            },
        }


class ExternalTempEmailsApiTests(unittest.TestCase):
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
            db.execute("DELETE FROM external_probe_cache")
            db.execute("DELETE FROM accounts WHERE email LIKE '%@ext-temp.test'")
            db.execute("DELETE FROM temp_email_messages WHERE email_address LIKE '%@ext-temp.test'")
            db.execute("DELETE FROM temp_emails WHERE email LIKE '%@ext-temp.test'")
            db.commit()
            settings_repo.set_setting("external_api_key", "contract-key")
            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("external_api_rate_limit_per_minute", "60")
            settings_repo.set_setting("external_api_disable_raw_content", "false")
            settings_repo.set_setting("external_api_disable_wait_message", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_random", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_release", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_complete", "false")
            settings_repo.set_setting("external_api_disable_pool_stats", "false")
            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("pool_default_provider", "")
            settings_repo.set_setting("active_mailbox_providers", "")
            settings_repo.set_setting("temp_mail_domains", "[]")
            settings_repo.set_setting("temp_mail_default_domain", "")
            settings_repo.set_setting(
                "temp_mail_prefix_rules",
                '{"min_length":1,"max_length":32,"pattern":"^[a-z0-9][a-z0-9._-]*$"}',
            )

    @staticmethod
    def _headers(api_key: str = "contract-key") -> dict[str, str]:
        return {"X-API-Key": api_key}

    @staticmethod
    def _facet_map(data: dict, facet_name: str, value_key: str) -> dict:
        return {item[value_key]: item for item in data["facets"][facet_name]}

    def test_apply_endpoint_returns_hidden_task_mailbox_and_persists_record(self):
        client = self.app.test_client()

        with patch("outlook_web.services.gptmail.generate_temp_email", return_value=("demo123@ext-temp.test", None)):
            resp = client.post(
                "/api/v1/external/temp-emails/apply",
                headers=self._headers(),
                json={
                    "caller_id": "register-worker-1",
                    "task_id": "job-001",
                    "prefix": "demo123",
                    "domain": "ext-temp.test",
                },
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["code"], "OK")
        self.assertEqual(data["data"]["email"], "demo123@ext-temp.test")
        self.assertEqual(data["data"]["provider_name"], "custom_domain_temp_mail")
        self.assertEqual(data["data"]["provider_label"], "Compatible Temp Mail Bridge")
        self.assertEqual(data["data"]["read_capability"], "temp_provider")
        self.assertFalse(data["data"]["visible_in_ui"])
        self.assertTrue(data["data"]["task_token"].startswith("tmptask_"))

        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            saved = temp_emails_repo.get_temp_email_by_task_token(data["data"]["task_token"])

        self.assertIsNotNone(saved)
        self.assertEqual(saved["consumer_key"], "legacy:settings.external_api_key")
        self.assertEqual(saved["mailbox_type"], "task")
        self.assertFalse(saved["visible_in_ui"])

    def test_apply_endpoint_accepts_provider_name_and_returns_provider_metadata(self):
        client = self.app.test_client()
        requested_provider_names = []

        def provider_factory(provider_name=None):
            requested_provider_names.append(provider_name)
            return _ProviderNameRecordingTempMailProvider(str(provider_name or "custom_domain_temp_mail"))

        with patch(
            "outlook_web.controllers.external_temp_emails.temp_mail_service._provider_factory",
            side_effect=provider_factory,
        ):
            resp = client.post(
                "/api/v1/external/temp-emails/apply",
                headers=self._headers(),
                json={
                    "caller_id": "register-worker-1",
                    "task_id": "job-provider-001",
                    "prefix": "ducktask",
                    "domain": "ext-temp.test",
                    "provider_name": "duckmail",
                },
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(requested_provider_names, ["duckmail", "duckmail"])
        self.assertEqual(data["email"], "ducktask@ext-temp.test")
        self.assertEqual(data["provider_name"], "duckmail")
        self.assertEqual(data["provider_label"], "DuckMail")
        self.assertEqual(data["read_capability"], "temp_provider")
        next_actions = data["external_mailbox_read_contract"]["next_actions"]
        self.assertEqual(next_actions["read_latest_message"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/messages/latest")
        self.assertEqual(
            next_actions["finish_task_mailbox"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/{{task_token}}/finish"
        )

        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            descriptor = temp_emails_repo.get_temp_email_by_task_token(data["task_token"], view="descriptor")

        self.assertIsNotNone(descriptor)
        self.assertEqual(descriptor["provider_name"], "duckmail")
        self.assertEqual(descriptor["read_capability"], "temp_provider")

    def test_apply_endpoint_rejects_successful_provider_result_without_email(self):
        client = self.app.test_client()

        with patch(
            "outlook_web.controllers.external_temp_emails.temp_mail_service._provider_factory",
            return_value=_EmptyAddressTempMailProvider("duckmail"),
        ):
            resp = client.post(
                "/api/v1/external/temp-emails/apply",
                headers=self._headers(),
                json={
                    "caller_id": "register-worker-1",
                    "task_id": "job-empty-email",
                    "prefix": "emptyaddr",
                    "domain": "ext-temp.test",
                    "provider_name": "duckmail",
                },
            )

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json()["code"], "TEMP_EMAIL_CREATE_FAILED")

    def test_external_providers_endpoint_requires_api_key(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/providers")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["code"], "UNAUTHORIZED")

    def test_external_provider_health_requires_api_key(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/providers/temp/mail_tm/health")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["code"], "UNAUTHORIZED")

    def test_external_provider_preflight_requires_api_key(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/providers/preflight")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["code"], "UNAUTHORIZED")

    def test_external_provider_preflight_reports_local_readiness_without_network_probe(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_bearer_token", "")

        client = self.app.test_client()
        with patch("outlook_web.services.temp_mail_provider_factory.get_temp_mail_provider") as provider_factory:
            resp = client.get("/api/v1/external/providers/preflight", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_not_called()
        preflight = resp.get_json()["data"]
        self.assertEqual(preflight["version"], 1)
        self.assertEqual(preflight["endpoints"]["provider_preflight"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/preflight")
        self.assertFalse(preflight["scope"]["network_probe"])
        rows = {(item["kind"], item["provider"]): item for item in preflight["providers"]}
        self.assertEqual(rows[("temp", "duckmail")]["local_status"], "needs_config")
        self.assertEqual(rows[("temp", "duckmail")]["missing_config"], ["duckmail_bearer_token"])
        self.assertEqual(rows[("temp", "duckmail")]["probe"]["status"], "not_requested")
        self.assertNotRegex(json.dumps(preflight, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")

    def test_external_provider_health_reports_local_readiness_without_network_probe(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_bearer_token", "")

        client = self.app.test_client()
        with patch("outlook_web.services.temp_mail_provider_factory.get_temp_mail_provider") as provider_factory:
            resp = client.get("/api/v1/external/providers/temp/duckmail/health", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_not_called()
        data = resp.get_json()["data"]
        self.assertEqual(data["kind"], "temp")
        self.assertEqual(data["provider"], "duckmail")
        self.assertFalse(data["local_ready"])
        self.assertEqual(data["local_status"], "needs_config")
        self.assertEqual(data["missing_config"], ["duckmail_bearer_token"])
        self.assertFalse(data["probe"]["requested"])
        self.assertFalse(data["probe"]["network_probe"])
        self.assertEqual(data["probe"]["status"], "not_requested")

    def test_external_provider_health_skips_network_probe_when_provider_is_not_ready(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_bearer_token", "")

        client = self.app.test_client()
        with patch("outlook_web.services.temp_mail_provider_factory.get_temp_mail_provider") as provider_factory:
            resp = client.get("/api/v1/external/providers/temp/duckmail/health?probe_network=true", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_not_called()
        data = resp.get_json()["data"]
        self.assertFalse(data["local_ready"])
        self.assertEqual(data["probe"]["status"], "skipped")
        self.assertEqual(data["probe"]["error_code"], "TEMP_MAIL_PROVIDER_NOT_CONFIGURED")
        self.assertFalse(data["probe"]["network_probe"])

    def test_external_provider_health_runs_explicit_network_probe_and_masks_details(self):
        client = self.app.test_client()
        with patch(
            "outlook_web.services.temp_mail_provider_factory.get_temp_mail_provider",
            return_value=_HealthCheckTempMailProvider("mail_tm"),
        ) as provider_factory:
            resp = client.get("/api/v1/external/providers/temp/mail_tm/health?probe_network=true", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_called_once_with("mail_tm")
        data = resp.get_json()["data"]
        self.assertTrue(data["local_ready"])
        self.assertTrue(data["can_probe_network"])
        self.assertTrue(data["probe"]["requested"])
        self.assertTrue(data["probe"]["network_probe"])
        self.assertTrue(data["probe"]["ok"])
        self.assertEqual(data["probe"]["status"], "ok")
        self.assertEqual(data["probe"]["method"], "mock_health_check")
        self.assertEqual(data["probe"]["details"]["domain_count"], 1)
        self.assertEqual(data["probe"]["details"]["author"], "OutlookMail Plus")
        self.assertEqual(data["probe"]["details"]["notes"], ["[redacted]", "safe note"])
        self.assertEqual(data["probe"]["details"]["supported_modes"], ["domains"])
        self.assertNotIn("bearer_token", data["probe"]["details"])
        self.assertEqual(data["probe"]["details"]["headers"], ["[redacted]"])
        self.assertEqual(data["probe"]["details"]["diagnostic_text"], "[redacted]")
        self.assertEqual(data["probe"]["details"]["nested"], {"message": "[redacted]", "safe": "ok"})
        self.assertNotIn("should-not-leak", str(data))
        self.assertNotIn("secret-pass", str(data))
        self.assertNotIn("rt-secret", str(data))
        self.assertNotIn("client-secret-value", str(data))

    def test_external_provider_health_returns_404_for_unknown_provider(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/providers/temp/not_a_provider/health", headers=self._headers())

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["code"], "MAILBOX_PROVIDER_NOT_FOUND")

    def test_external_mailboxes_endpoint_returns_unified_directory(self):
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import groups as groups_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = int(groups_repo.get_default_group_id())
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    imap_host, imap_port, imap_password, group_id, remark, status
                )
                VALUES (?, '', '', '', 'imap', 'custom', 'imap.ext-temp.test', 993, ?, ?, 'external catalog', 'active')
                """,
                (
                    "catalog-account@ext-temp.test",
                    self.module.encrypt_data("imap-secret"),
                    default_group_id,
                ),
            )
            temp_emails_repo.create_temp_email(
                email_addr="catalog-temp@ext-temp.test",
                source="duckmail",
                provider_name="duckmail",
                task_token="tmptask_catalog_secret",
                consumer_key="consumer:catalog-secret",
                status="active",
                meta={
                    "provider_jwt": "jwt-secret",
                    "provider_secret": "provider-secret",
                    "provider_capabilities": {"delete_mailbox": True, "delete_message": True, "clear_messages": True},
                },
            )
            db.commit()

        client = self.app.test_client()
        resp = client.get("/api/v1/external/mailboxes?search=catalog-&sort=email_asc&page_size=20", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertTrue(data["success"])
        self.assertEqual(data["contract"]["version"], 1)
        quick_view_by_key = {item["key"]: item for item in data["contract"]["quick_view_presets"]}
        self.assertEqual(quick_view_by_key["readable"]["filters"]["action"], "read_messages")
        self.assertEqual(quick_view_by_key["attention"]["filters"]["status"], "inactive")
        self.assertNotRegex(str(data["contract"]["quick_view_presets"]), r"dk_[0-9a-fA-F]{20,}")
        self.assertEqual(data["filters"]["sort"], "email_asc")
        self.assertEqual(data["filters"]["read_capability"], "all")
        self.assertEqual(data["filters"]["action"], "all")
        self.assertEqual(data["pagination"]["total_count"], 2)
        provider_context = data["provider_context"]
        self.assertEqual(provider_context["version"], 1)
        self.assertEqual(provider_context["defaults"]["active_mailbox_provider_env"], "ACTIVE_MAILBOX_PROVIDERS")
        self.assertEqual(provider_context["deployment_env"], provider_context["deployment_profile"]["env"])
        self.assertEqual(
            provider_context["selection_policy"]["source_priority"], ["env", "provider_config_file", "settings", "default"]
        )
        self.assertEqual(provider_context["selection_policy"]["scopes"]["explicit_pool_claim"]["request_field"], "provider")
        self.assertIn("duckmail", provider_context["deployment_profile"]["provider_values"]["temp_apply"])
        self.assertEqual(provider_context["discovery"]["providers_endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/providers")
        self.assertEqual(
            provider_context["documentation"]["entries"]["provider_onboarding"]["path"], "docs/provider-onboarding.md"
        )
        self.assertEqual(provider_context["provider_integration_guide"]["documentation"], provider_context["documentation"])
        readiness = provider_context["readiness_summary"]
        self.assertEqual(readiness["version"], 1)
        self.assertEqual(readiness["totals"]["mailboxes"], 2)
        self.assertEqual(readiness["totals"]["account_mailboxes"], 1)
        self.assertEqual(readiness["totals"]["temp_mailboxes"], 1)
        self.assertEqual(readiness["provider_selector_fields"]["pool_claim"], "provider")
        self.assertEqual(readiness["provider_selector_fields"]["task_temp_apply"], "provider_name")
        readiness_rows = {(item["kind"], item["provider"]): item for item in readiness["providers"]}
        self.assertEqual(readiness_rows[("account", "custom")]["mailbox_count"], 1)
        self.assertEqual(readiness_rows[("temp", "duckmail")]["mailbox_count"], 1)
        self.assertEqual(
            readiness_rows[("temp", "duckmail")]["endpoints"]["health"],
            f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health",
        )
        self.assertEqual(
            {item["email"] for item in data["mailboxes"]}, {"catalog-account@ext-temp.test", "catalog-temp@ext-temp.test"}
        )
        by_email = {item["email"]: item for item in data["mailboxes"]}
        account_contract = by_email["catalog-account@ext-temp.test"]["action_contract"]
        temp_contract = by_email["catalog-temp@ext-temp.test"]["action_contract"]
        self.assertEqual(account_contract["external"]["read_messages"]["query"]["email"], "catalog-account@ext-temp.test")
        self.assertEqual(account_contract["internal"]["open_mailbox"]["mode"], "standard")
        self.assertEqual(
            temp_contract["external"]["read_verification_code"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/verification-code"
        )
        self.assertEqual(temp_contract["external"]["read_verification_code"]["query"]["email"], "catalog-temp@ext-temp.test")
        self.assertEqual(temp_contract["internal"]["open_mailbox"]["mode"], "temp-emails")
        facets = {item["provider"]: item for item in data["facets"]["providers"]}
        self.assertEqual(facets["duckmail"]["label"], "DuckMail")
        kind_facets = self._facet_map(data, "kinds", "kind")
        self.assertEqual(kind_facets["account"]["count"], 1)
        self.assertEqual(kind_facets["temp"]["count"], 1)
        status_facets = self._facet_map(data, "statuses", "status")
        self.assertEqual(status_facets["active"]["count"], 2)
        self.assertEqual(status_facets["inactive"]["count"], 0)
        read_capability_facets = self._facet_map(data, "read_capabilities", "read_capability")
        self.assertEqual(read_capability_facets["graph"]["count"], 0)
        self.assertEqual(read_capability_facets["imap"]["count"], 1)
        self.assertEqual(read_capability_facets["temp_provider"]["count"], 1)
        action_facets = {item["action"]: item for item in data["facets"]["actions"]}
        self.assertEqual(action_facets["read_messages"]["count"], 2)
        self.assertEqual(action_facets["refresh_auth"]["count"], 0)
        self.assertEqual(action_facets["delete_remote_mailbox"]["count"], 1)
        self.assertEqual(action_facets["delete_message"]["count"], 1)
        self.assertEqual(action_facets["clear_messages"]["count"], 1)
        self.assertNotIn("imap-secret", str(payload))
        self.assertNotIn("tmptask_catalog_secret", str(payload))
        self.assertNotIn("consumer:catalog-secret", str(payload))
        self.assertNotIn("jwt-secret", str(payload))
        self.assertNotIn("provider-secret", str(payload))
        self.assertNotIn("tmptask_catalog_secret", str(readiness))
        self.assertNotIn("consumer:catalog-secret", str(readiness))
        self.assertNotIn("jwt-secret", str(readiness))
        self.assertNotIn("provider-secret", str(readiness))

        imap_resp = client.get(
            "/api/v1/external/mailboxes?search=catalog-&read_capability=imap&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(imap_resp.status_code, 200)
        imap_data = imap_resp.get_json()["data"]
        self.assertEqual(imap_data["filters"]["read_capability"], "imap")
        self.assertEqual([item["email"] for item in imap_data["mailboxes"]], ["catalog-account@ext-temp.test"])
        imap_read_capability_facets = self._facet_map(imap_data, "read_capabilities", "read_capability")
        self.assertEqual(imap_read_capability_facets["imap"]["count"], 1)
        self.assertEqual(imap_read_capability_facets["temp_provider"]["count"], 1)

        action_resp = client.get(
            "/api/v1/external/mailboxes?search=catalog-&action=delete_remote_mailbox&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(action_resp.status_code, 200)
        action_data = action_resp.get_json()["data"]
        self.assertEqual(action_data["filters"]["action"], "delete_remote_mailbox")
        self.assertEqual([item["email"] for item in action_data["mailboxes"]], ["catalog-temp@ext-temp.test"])
        action_filtered_facets = {item["action"]: item for item in action_data["facets"]["actions"]}
        self.assertEqual(action_filtered_facets["read_messages"]["count"], 2)
        self.assertEqual(action_filtered_facets["delete_remote_mailbox"]["count"], 1)
        action_kind_facets = self._facet_map(action_data, "kinds", "kind")
        self.assertEqual(action_kind_facets["account"]["count"], 0)
        self.assertEqual(action_kind_facets["temp"]["count"], 1)

    def test_external_mailboxes_endpoint_scopes_accounts_before_counts_and_facets(self):
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import external_api_keys as external_api_keys_repo
            from outlook_web.repositories import groups as groups_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = int(groups_repo.get_default_group_id())
            db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active')
                """,
                (
                    "scope-allowed@ext-temp.test",
                    "cid-allowed",
                    self.module.encrypt_data("rt-allowed"),
                    default_group_id,
                ),
            )
            db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active')
                """,
                (
                    "scope-denied@ext-temp.test",
                    "cid-denied",
                    self.module.encrypt_data("rt-denied"),
                    default_group_id,
                ),
            )
            temp_emails_repo.create_temp_email(
                email_addr="scope-temp@ext-temp.test",
                source="mail_tm",
                provider_name="mail_tm",
                status="active",
            )
            external_api_keys_repo.create_external_api_key(
                name="scoped-catalog",
                api_key="scoped-catalog-key",
                allowed_emails=["scope-allowed@ext-temp.test"],
            )
            db.commit()

        client = self.app.test_client()
        resp = client.get("/api/v1/external/mailboxes?search=scope-&page_size=20", headers=self._headers("scoped-catalog-key"))

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        emails = {item["email"] for item in data["mailboxes"]}
        self.assertEqual(emails, {"scope-allowed@ext-temp.test", "scope-temp@ext-temp.test"})
        self.assertEqual(data["pagination"]["total_count"], 2)
        self.assertEqual(data["summary"]["account"], 1)
        self.assertEqual(data["summary"]["temp"], 1)
        facet_providers = {item["provider"] for item in data["facets"]["providers"]}
        self.assertIn("outlook", facet_providers)
        self.assertIn("mail_tm", facet_providers)
        kind_facets = self._facet_map(data, "kinds", "kind")
        self.assertEqual(kind_facets["account"]["count"], 1)
        self.assertEqual(kind_facets["temp"]["count"], 1)
        status_facets = self._facet_map(data, "statuses", "status")
        self.assertEqual(status_facets["active"]["count"], 2)
        read_capability_facets = self._facet_map(data, "read_capabilities", "read_capability")
        self.assertEqual(read_capability_facets["graph"]["count"], 1)
        self.assertEqual(read_capability_facets["imap"]["count"], 0)
        self.assertEqual(read_capability_facets["temp_provider"]["count"], 1)
        action_facets = {item["action"]: item for item in data["facets"]["actions"]}
        self.assertEqual(action_facets["read_messages"]["count"], 2)
        self.assertEqual(action_facets["refresh_auth"]["count"], 1)
        self.assertNotIn("scope-denied@ext-temp.test", str(data))

    def test_external_mailboxes_endpoint_requires_api_key_and_rejects_invalid_filter(self):
        client = self.app.test_client()

        missing_key_resp = client.get("/api/v1/external/mailboxes")
        self.assertEqual(missing_key_resp.status_code, 401)
        self.assertEqual(missing_key_resp.get_json()["code"], "UNAUTHORIZED")

        invalid_kind_resp = client.get("/api/v1/external/mailboxes?kind=bad", headers=self._headers())
        self.assertEqual(invalid_kind_resp.status_code, 400)
        self.assertEqual(invalid_kind_resp.get_json()["code"], "MAILBOX_KIND_INVALID")

        invalid_read_capability_resp = client.get("/api/v1/external/mailboxes?read_capability=bad", headers=self._headers())
        self.assertEqual(invalid_read_capability_resp.status_code, 400)
        self.assertEqual(invalid_read_capability_resp.get_json()["code"], "MAILBOX_READ_CAPABILITY_INVALID")

        invalid_action_resp = client.get("/api/v1/external/mailboxes?action=bad", headers=self._headers())
        self.assertEqual(invalid_action_resp.status_code, 400)
        self.assertEqual(invalid_action_resp.get_json()["code"], "MAILBOX_ACTION_INVALID")

        invalid_sort_resp = client.get("/api/v1/external/mailboxes?sort=bad", headers=self._headers())
        self.assertEqual(invalid_sort_resp.status_code, 400)
        self.assertEqual(invalid_sort_resp.get_json()["code"], "MAILBOX_SORT_INVALID")

    def test_external_providers_endpoint_returns_unified_catalog_and_runtime_defaults(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_provider", "duckmail")
            settings_repo.set_setting("pool_default_provider", "mail_tm")
            settings_repo.set_setting("duckmail_bearer_token", "")

        client = self.app.test_client()
        resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["default_temp_mail_provider"], "duckmail")
        self.assertEqual(data["default_pool_claim_provider"], "mail_tm")
        self.assertEqual(data["default_pool_claim_provider_env"], "EXTERNAL_POOL_DEFAULT_PROVIDER")
        self.assertEqual(
            data["deployment_env"],
            {
                "active_mailbox_providers": "ACTIVE_MAILBOX_PROVIDERS",
                "pool_claim_provider": "EXTERNAL_POOL_DEFAULT_PROVIDER",
                "temp_mail_provider": "TEMP_MAIL_PROVIDER",
            },
        )
        deployment_profile = data["deployment_profile"]
        self.assertEqual(deployment_profile["version"], 1)
        self.assertEqual(deployment_profile["env"], data["deployment_env"])
        selection_policy = data["selection_policy"]
        self.assertEqual(selection_policy["version"], 1)
        self.assertEqual(selection_policy["source_priority"], ["env", "provider_config_file", "settings", "default"])
        self.assertEqual(selection_policy["config_file"]["priority_slot"], "provider_config_file")
        self.assertEqual(selection_policy["config_file"]["diagnostic_source"], "config_file")
        self.assertEqual(selection_policy["templates"], deployment_profile["templates"])
        self.assertEqual(selection_policy["scopes"]["temp_runtime_default"]["request_field"], "provider_name")
        self.assertEqual(selection_policy["scopes"]["pool_claim_default"]["request_field"], "provider")
        self.assertEqual(
            selection_policy["scopes"]["task_temp_apply"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply"
        )
        self.assertIn("mail_tm", selection_policy["scopes"]["temp_runtime_default"]["allowed_values"])
        self.assertIn("duckmail", deployment_profile["provider_values"]["temp_apply"])
        self.assertIn("mail_tm", deployment_profile["provider_values"]["pool_claim"])
        self.assertIn("gptmail", deployment_profile["provider_values"]["active_allowlist"])
        self.assertIn("DUCKMAIL_BEARER_TOKEN", deployment_profile["config_env"]["required"])
        self.assertIn("DUCKMAIL_BEARER_TOKEN", deployment_profile["config_env"]["secret"])
        self.assertEqual(
            deployment_profile["provider_examples"]["duckmail"]["pool_claim_default"]["value"],
            "duckmail",
        )
        self.assertIn(
            "# OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE=.runtime/providers.json", deployment_profile["templates"]["env"]["content"]
        )
        self.assertIn('"active_mailbox_providers": []', deployment_profile["templates"]["provider_config_json"]["content"])
        self.assertFalse(data["default_temp_mail_provider_configured"])
        self.assertEqual(data["runtime_temp_mail_provider_env"], "TEMP_MAIL_PROVIDER")
        self.assertIn("provider", data["pool_claim_fields"])
        self.assertEqual(
            data["provider_health_endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health"
        )
        self.assertEqual(data["provider_health_fields"], ["kind", "provider", "probe_network"])
        self.assertEqual(data["provider_preflight_endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/preflight")
        self.assertEqual(data["provider_preflight_fields"], ["probe_network"])
        documentation = data["documentation"]
        self.assertEqual(documentation["recommended_human_start"], "provider_onboarding")
        self.assertEqual(documentation["entries"]["provider_onboarding"]["path"], "docs/provider-onboarding.md")
        self.assertEqual(documentation["entries"]["openapi"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json")
        self.assertNotIn("legacy_endpoint", documentation["entries"]["openapi"])
        self.assertEqual(data["runtime_temp_mail_provider_aliases"]["gptmail"], "legacy_bridge")
        self.assertEqual(data["runtime_temp_mail_provider_aliases"]["temp_mail"], "legacy_bridge")
        self.assertEqual(
            data["pool_claim_provider_aliases"]["gptmail"]["temp_provider_names"],
            ["custom_domain_temp_mail", "legacy_bridge"],
        )
        self.assertEqual(data["pool_claim_provider_aliases"]["imap"]["kind"], "account")
        self.assertEqual(data["temp_mail_apply_endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply")
        self.assertIn("provider_name", data["temp_mail_apply_fields"])
        readiness = data["readiness_summary"]
        self.assertEqual(readiness["version"], 1)
        routing_matrix = readiness["routing_matrix"]
        self.assertEqual(routing_matrix["version"], 1)
        self.assertEqual(routing_matrix["scopes"]["explicit_pool_claim"]["request_field"], "provider")
        self.assertEqual(routing_matrix["scopes"]["task_temp_apply"]["request_field"], "provider_name")
        task_rows = {item["provider"]: item for item in routing_matrix["scopes"]["task_temp_apply"]["providers"]}
        self.assertFalse(task_rows["duckmail"]["usable"])
        self.assertEqual(task_rows["duckmail"]["status"], "needs_config")
        pool_rows = {item["provider"]: item for item in routing_matrix["scopes"]["explicit_pool_claim"]["providers"]}
        self.assertTrue(pool_rows["auto"]["usable"])
        self.assertEqual(pool_rows["imap"]["reason"], "alias_pool_claim_provider")
        self.assertNotRegex(json.dumps(routing_matrix, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")
        guide = data["provider_integration_guide"]
        self.assertEqual(guide["version"], 1)
        self.assertEqual(guide["documentation"], documentation)
        self.assertEqual(guide["source_priority"], selection_policy["source_priority"])
        self.assertFalse(guide["secret_policy"]["exposes_secret_values"])
        self.assertTrue(guide["secret_policy"]["secret_key_names_allowed"])
        self.assertEqual(guide["endpoints"]["providers"], f"{CANONICAL_EXTERNAL_PREFIX}/providers")
        self.assertEqual(guide["endpoints"]["provider_preflight"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/preflight")
        self.assertEqual(guide["workflow"]["claim_pool_mailbox"]["request_field"], "provider")
        self.assertEqual(guide["workflow"]["create_task_temp_mailbox"]["request_field"], "provider_name")
        self.assertIn("duckmail", guide["workflow"]["create_task_temp_mailbox"]["allowed_values"])
        self.assertEqual(guide["aliases"]["runtime_temp_mail_provider_aliases"]["gptmail"], "legacy_bridge")
        self.assertEqual(guide["aliases"]["pool_claim_provider_aliases"]["imap"]["kind"], "account")
        guide_temp_providers = {item["provider"]: item for item in guide["providers"] if item.get("kind") == "temp"}
        duckmail_guide = guide_temp_providers["duckmail"]
        self.assertEqual(duckmail_guide["required_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(duckmail_guide["optional_env"], ["DUCKMAIL_API_BASE"])
        self.assertEqual(duckmail_guide["configuration"]["env_defaults"], {"DUCKMAIL_API_BASE": "https://api.duckmail.sbs"})
        self.assertEqual(duckmail_guide["secret_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(duckmail_guide["pool_claim_request"]["field"], "provider")
        self.assertEqual(duckmail_guide["pool_claim_request"]["value"], "duckmail")
        self.assertEqual(duckmail_guide["task_temp_apply_request"]["field"], "provider_name")
        self.assertEqual(duckmail_guide["task_temp_apply_request"]["value"], "duckmail")
        self.assertEqual(duckmail_guide["runtime_default"]["env"], {"key": "TEMP_MAIL_PROVIDER", "value": "duckmail"})
        self.assertEqual(duckmail_guide["activation"]["provider_config"]["value"], ["duckmail"])
        self.assertEqual(
            duckmail_guide["health"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health"
        )
        self.assertEqual(duckmail_guide["mailbox_directory_filter"]["query"], {"kind": "temp", "provider": "duckmail"})
        self.assertEqual(guide_temp_providers["mail_tm"]["optional_env"], ["MAILTM_API_BASE"])
        self.assertEqual(
            guide_temp_providers["mail_tm"]["configuration"]["env_defaults"], {"MAILTM_API_BASE": "https://api.mail.tm"}
        )
        self.assertEqual(
            guide_temp_providers["tempmail_lol"]["optional_env"], ["TEMPMAIL_LOL_API_KEY", "TEMP_MAIL_LOL_API_KEY"]
        )
        self.assertEqual(guide_temp_providers["emailnator"]["required_env"], ["EMAILNATOR_API_KEY"])
        self.assertEqual(
            guide_temp_providers["legacy_bridge"]["aliases"]["runtime_temp_mail_provider"],
            ["gptmail", "legacy_gptmail", "temp_mail"],
        )
        manifest = data["integration_manifest"]
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["documentation"], documentation)
        self.assertEqual(manifest["auth"]["header"], "X-API-Key")
        self.assertEqual(manifest["auth"]["placeholder"], "<your-api-key>")
        self.assertEqual(manifest["selection"]["source_priority"], selection_policy["source_priority"])
        self.assertEqual(manifest["selection"]["explicit_pool_claim"]["request_field"], "provider")
        self.assertEqual(manifest["selection"]["task_temp_apply"]["request_field"], "provider_name")
        self.assertEqual(manifest["discovery"]["recommended_sequence"][0]["response_field"], "integration_manifest")
        self.assertEqual(manifest["discovery"]["endpoints"]["providers"], f"{CANONICAL_EXTERNAL_PREFIX}/providers")
        self.assertEqual(
            manifest["discovery"]["endpoints"]["provider_preflight"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/preflight"
        )
        self.assertEqual(manifest["discovery"]["endpoints"]["mailboxes"], f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes")
        workflows = {item["key"]: item for item in manifest["workflows"]}
        self.assertIn("claim_pool_mailbox", workflows)
        self.assertIn("create_task_temp_mailbox", workflows)
        claim_steps = {item["key"]: item for item in workflows["claim_pool_mailbox"]["steps"]}
        self.assertEqual(claim_steps["claim_random"]["request"]["provider_selector"]["field"], "provider")
        self.assertEqual(claim_steps["complete_claim"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-complete")
        task_steps = {item["key"]: item for item in workflows["create_task_temp_mailbox"]["steps"]}
        self.assertEqual(task_steps["apply_task_mailbox"]["request"]["provider_selector"]["field"], "provider_name")
        self.assertEqual(
            task_steps["finish_task_mailbox"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/{{task_token}}/finish"
        )
        self.assertEqual(manifest["deployment"]["source_priority"], selection_policy["source_priority"])
        self.assertEqual(manifest["deployment"]["env"], data["deployment_env"])
        self.assertFalse(manifest["secret_policy"]["exposes_secret_values"])
        self.assertEqual(data["quickstart"], manifest["quickstart"])
        quickstart = data["quickstart"]
        self.assertEqual(quickstart["version"], 1)
        self.assertEqual(quickstart["auth"]["headers"], {"X-API-Key": "<your-api-key>"})
        self.assertEqual(quickstart["provider_selector_fields"]["pool_claim"]["field"], "provider")
        self.assertEqual(quickstart["provider_selector_fields"]["task_temp_apply"]["field"], "provider_name")
        self.assertEqual(quickstart["requests"]["pool_claim"]["body"]["provider"], "<provider-or-auto>")
        self.assertEqual(quickstart["requests"]["task_temp_apply"]["body"]["provider_name"], "<provider-name>")
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", json.dumps(quickstart, ensure_ascii=False))
        manifest_temp_providers = {item["provider"]: item for item in manifest["providers"] if item.get("kind") == "temp"}
        duckmail_manifest = manifest_temp_providers["duckmail"]
        duckmail_env = {item["key"]: item for item in duckmail_manifest["env"]}
        self.assertEqual(duckmail_env["DUCKMAIL_BEARER_TOKEN"]["value"], "")
        self.assertTrue(duckmail_env["DUCKMAIL_BEARER_TOKEN"]["secret"])
        self.assertEqual(duckmail_env["DUCKMAIL_API_BASE"]["default"], "https://api.duckmail.sbs")
        self.assertEqual(duckmail_manifest["request_fields"]["pool_claim"]["value"], "duckmail")
        self.assertEqual(duckmail_manifest["request_fields"]["task_temp_apply"]["request_field"], "provider_name")
        self.assertEqual(duckmail_manifest["config_file_examples"]["activation"]["value"], ["duckmail"])
        mailtm_env = {item["key"]: item for item in manifest_temp_providers["mail_tm"]["env"]}
        self.assertEqual(mailtm_env["MAILTM_API_BASE"]["default"], "https://api.mail.tm")
        self.assertEqual(
            manifest_temp_providers["legacy_bridge"]["aliases"]["runtime_temp_mail_provider"],
            ["gptmail", "legacy_gptmail", "temp_mail"],
        )
        manifest_text = json.dumps(manifest, ensure_ascii=False)
        self.assertNotRegex(manifest_text, r"dk_[0-9a-fA-F]{20,}")
        read_contract = data["external_mailbox_read_contract"]
        self.assertEqual(read_contract["read_by"], ["email", "claim_token"])
        self.assertEqual(read_contract["read_endpoints"]["messages"], f"{CANONICAL_EXTERNAL_PREFIX}/messages")
        self.assertEqual(
            read_contract["read_endpoints"]["verification_code"], f"{CANONICAL_EXTERNAL_PREFIX}/verification-code"
        )
        self.assertEqual(read_contract["next_actions"]["wait_message_async"]["fixed_query"], {"mode": "async"})
        self.assertIn("claim_token", read_contract["next_actions"]["read_latest_message"]["query_fields"])

        catalog = data["mailbox_providers"]
        by_key = {(item.get("kind"), item.get("provider")): item for item in catalog}
        self.assertEqual(by_key[("account", "outlook")]["read_capability"], "graph")
        self.assertEqual(by_key[("account", "gmail")]["read_capability"], "imap")
        self.assertEqual(by_key[("temp", "duckmail")]["label"], "DuckMail")
        self.assertFalse(by_key[("temp", "duckmail")]["configured"])
        self.assertEqual(by_key[("temp", "duckmail")]["missing_config"], ["duckmail_bearer_token"])
        self.assertEqual(by_key[("temp", "duckmail")]["selection"]["pool_claim_provider"], "duckmail")
        self.assertEqual(by_key[("temp", "duckmail")]["selection"]["temp_apply_provider_name"], "duckmail")
        self.assertEqual(by_key[("temp", "duckmail")]["selection"]["runtime_env"], {"TEMP_MAIL_PROVIDER": "duckmail"})
        self.assertEqual(
            by_key[("temp", "duckmail")]["deployment"],
            {
                "activate": {
                    "env": "ACTIVE_MAILBOX_PROVIDERS",
                    "value": "duckmail",
                    "settings_key": "active_mailbox_providers",
                    "settings_value": "duckmail",
                },
                "pool_claim_default": {
                    "env": "EXTERNAL_POOL_DEFAULT_PROVIDER",
                    "value": "duckmail",
                    "settings_key": "pool_default_provider",
                    "settings_value": "duckmail",
                },
                "pool_claim_request": {"field": "provider", "value": "duckmail"},
                "runtime_default": {
                    "env": "TEMP_MAIL_PROVIDER",
                    "value": "duckmail",
                    "settings_key": "temp_mail_provider",
                    "settings_value": "duckmail",
                },
                "task_temp_apply_request": {"field": "provider_name", "value": "duckmail"},
                "config_env": {
                    "required": ["DUCKMAIL_BEARER_TOKEN"],
                    "optional": ["DUCKMAIL_API_BASE"],
                    "defaults": {"DUCKMAIL_API_BASE": "https://api.duckmail.sbs"},
                    "secret": ["DUCKMAIL_BEARER_TOKEN"],
                },
                "config_settings": {
                    "keys": ["duckmail_api_base", "duckmail_bearer_token"],
                    "required": ["duckmail_bearer_token"],
                    "defaults": {"duckmail_api_base": "https://api.duckmail.sbs"},
                    "secret": ["duckmail_bearer_token"],
                },
            },
        )
        self.assertEqual(by_key[("temp", "duckmail")]["configuration"]["required_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(by_key[("temp", "duckmail")]["configuration"]["optional_env"], ["DUCKMAIL_API_BASE"])
        self.assertEqual(
            by_key[("temp", "duckmail")]["configuration"]["env_defaults"], {"DUCKMAIL_API_BASE": "https://api.duckmail.sbs"}
        )
        self.assertEqual(by_key[("temp", "duckmail")]["configuration"]["secret_env"], ["DUCKMAIL_BEARER_TOKEN"])
        duckmail_schema_fields = by_key[("temp", "duckmail")]["configuration"]["config_schema"]["fields"]
        self.assertEqual([field["key"] for field in duckmail_schema_fields], ["duckmail_api_base", "duckmail_bearer_token"])
        self.assertEqual(duckmail_schema_fields[1]["type"], "password")
        self.assertNotIn("default", duckmail_schema_fields[1])
        self.assertEqual(by_key[("temp", "mail_tm")]["read_capability"], "temp_provider")
        self.assertTrue(by_key[("temp", "mail_tm")]["configured"])
        self.assertEqual(by_key[("temp", "mail_tm")]["configuration"]["optional_env"], ["MAILTM_API_BASE"])
        self.assertEqual(
            by_key[("temp", "mail_tm")]["configuration"]["env_defaults"], {"MAILTM_API_BASE": "https://api.mail.tm"}
        )
        self.assertTrue(by_key[("temp", "mail_tm")]["can_dynamic_create"])
        self.assertTrue(by_key[("account", "outlook")]["requires_pool_inventory"])
        self.assertEqual(by_key[("account", "outlook")]["selection"]["pool_claim_provider"], "outlook")
        self.assertEqual(by_key[("account", "outlook")]["configuration"]["secret_fields"], ["refresh_token"])
        self.assertEqual(
            by_key[("account", "custom")]["selection"]["pool_claim_temp_fallback_provider_names"],
            ["custom_domain_temp_mail", "legacy_bridge"],
        )
        self.assertEqual(
            by_key[("temp", "legacy_bridge")]["selection"]["accepted_aliases"], ["gptmail", "legacy_gptmail", "temp_mail"]
        )
        diagnostics = data["provider_diagnostics"]
        self.assertEqual(diagnostics["scope"]["type"], "local_config")
        self.assertFalse(diagnostics["scope"]["network_probe"])
        # Full catalog dual-registers Compatible Temp Mail Bridge keys; diagnostics
        # collapse to a single operator-facing bridge row, so active/total can be
        # one less than len(mailbox_providers).
        self.assertEqual(diagnostics["summary"]["active"], len(diagnostics["providers"]))
        self.assertEqual(diagnostics["summary"]["ready"], diagnostics["summary"]["configured"])
        self.assertEqual(diagnostics["summary"]["total"], len(diagnostics["providers"]))
        self.assertLessEqual(diagnostics["summary"]["total"], len(catalog))
        self.assertGreaterEqual(diagnostics["summary"]["needs_config"], 1)
        diagnostic_by_key = {(item.get("kind"), item.get("provider")): item for item in diagnostics["providers"]}
        self.assertIn(("temp", "legacy_bridge"), diagnostic_by_key)
        self.assertNotIn(("temp", "custom_domain_temp_mail"), diagnostic_by_key)
        self.assertIn(("temp", "custom_domain_temp_mail"), by_key)
        self.assertEqual(diagnostic_by_key[("temp", "duckmail")]["status"], "needs_config")
        self.assertEqual(diagnostic_by_key[("temp", "duckmail")]["required_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(diagnostic_by_key[("temp", "duckmail")]["optional_env"], ["DUCKMAIL_API_BASE"])
        self.assertTrue(data["supports_temp_mail_provider_selection"])

    def test_external_providers_reports_missing_config_file_without_failing_discovery(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("pool_default_provider", "")

        client = self.app.test_client()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_config_path = Path(tmpdir) / "missing-providers.json"
            with patch.dict(
                "os.environ",
                {
                    "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(missing_config_path),
                    "TEMP_MAIL_PROVIDER": "",
                    "EXTERNAL_POOL_DEFAULT_PROVIDER": "",
                    "ACTIVE_MAILBOX_PROVIDERS": "",
                },
                clear=False,
            ):
                resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        selection_config = data["selection_policy"]["config_file"]
        defaults = data["provider_diagnostics"]["defaults"]

        # Operator default matches collapsed bridge key in guide/diagnostics.
        self.assertEqual(data["default_temp_mail_provider"], "legacy_bridge")
        self.assertEqual(defaults["temp_mail_provider"]["raw_provider"], "custom_domain_temp_mail")
        self.assertEqual(defaults["temp_mail_provider"]["provider"], "legacy_bridge")
        guide_temp = {
            item.get("provider")
            for item in (data.get("provider_integration_guide") or {}).get("providers") or []
            if item.get("kind") == "temp"
        }
        self.assertIn(data["default_temp_mail_provider"], guide_temp)
        self.assertEqual(selection_config["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertFalse(selection_config["loaded"])
        self.assertEqual(data["provider_filter"]["source"], "config_file_error")
        self.assertEqual(data["provider_filter"]["config_error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertEqual(data["provider_integration_guide"]["provider_filter"]["source"], "config_file_error")
        self.assertEqual(
            data["provider_integration_guide"]["provider_filter"]["config_error_code"],
            "PROVIDER_CONFIG_FILE_NOT_FOUND",
        )
        self.assertEqual(defaults["temp_mail_provider"]["source"], "config_file_error")
        self.assertEqual(defaults["temp_mail_provider"]["fallback_source"], "settings")
        self.assertEqual(defaults["pool_claim_provider"]["source"], "config_file_error")
        self.assertEqual(defaults["pool_claim_provider"]["fallback_source"], "default")

    def test_external_providers_endpoint_filters_active_mailbox_providers(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        client = self.app.test_client()
        resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["active_mailbox_providers"], ["duckmail"])
        self.assertEqual(data["active_mailbox_provider_env"], "ACTIVE_MAILBOX_PROVIDERS")
        catalog = data["mailbox_providers"]
        self.assertEqual({item["provider"] for item in catalog}, {"duckmail"})
        self.assertTrue(all(item["active"] for item in catalog))
        diagnostics = data["provider_diagnostics"]
        self.assertEqual(diagnostics["filter"]["mode"], "allowlist")
        self.assertGreater(diagnostics["summary"]["total"], diagnostics["summary"]["active"])
        diagnostic_by_provider = {item["provider"]: item for item in diagnostics["providers"] if item.get("kind") == "temp"}
        self.assertTrue(diagnostic_by_provider["duckmail"]["active"])
        self.assertEqual(diagnostic_by_provider["duckmail"]["status"], "needs_config")
        self.assertFalse(diagnostic_by_provider["mail_tm"]["active"])
        self.assertEqual(diagnostic_by_provider["mail_tm"]["status"], "inactive")
        guide = data["provider_integration_guide"]
        self.assertEqual(guide["provider_filter"]["mode"], "allowlist")
        guide_temp_providers = {item["provider"]: item for item in guide["providers"] if item.get("kind") == "temp"}
        self.assertTrue(guide_temp_providers["duckmail"]["active"])
        self.assertFalse(guide_temp_providers["mail_tm"]["active"])
        self.assertEqual(guide_temp_providers["mail_tm"]["readiness_status"], "inactive")

    def test_external_providers_endpoint_reports_unknown_active_mailbox_provider_filter_entries(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail,not_a_provider,gptmail")

        client = self.app.test_client()
        resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        provider_filter = data["provider_diagnostics"]["filter"]
        self.assertEqual(provider_filter["active_providers"], ["duckmail", "not_a_provider", "gptmail"])
        self.assertEqual(provider_filter["unknown_providers"], ["not_a_provider"])
        self.assertIn("gptmail", provider_filter["recognized_aliases"])
        self.assertEqual(data["provider_diagnostics"]["summary"]["unknown_filter_entries"], 1)

    def test_external_providers_endpoint_reports_invalid_default_provider_entries(self):
        client = self.app.test_client()
        with patch.dict(
            "os.environ",
            {
                "TEMP_MAIL_PROVIDER": "bad_temp_default",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "bad_pool_default",
            },
            clear=False,
        ):
            resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        diagnostics = data["provider_diagnostics"]
        defaults = diagnostics["defaults"]

        self.assertFalse(defaults["temp_mail_provider"]["valid"])
        self.assertEqual(defaults["temp_mail_provider"]["source"], "env")
        self.assertEqual(defaults["temp_mail_provider"]["key"], "TEMP_MAIL_PROVIDER")
        self.assertEqual(defaults["temp_mail_provider"]["provider"], "bad_temp_default")
        self.assertFalse(defaults["pool_claim_provider"]["valid"])
        self.assertEqual(defaults["pool_claim_provider"]["source"], "env")
        self.assertEqual(defaults["pool_claim_provider"]["key"], "EXTERNAL_POOL_DEFAULT_PROVIDER")
        self.assertEqual(defaults["pool_claim_provider"]["provider"], "bad_pool_default")
        self.assertEqual(diagnostics["summary"]["invalid_default_entries"], 2)
        self.assertEqual(
            {item["key"]: item["provider"] for item in defaults["invalid_defaults"]},
            {
                "TEMP_MAIL_PROVIDER": "bad_temp_default",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "bad_pool_default",
            },
        )

    def test_external_providers_endpoint_reports_default_provider_entries_excluded_by_allowlist(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        client = self.app.test_client()
        with patch.dict(
            "os.environ",
            {
                "TEMP_MAIL_PROVIDER": "mail_tm",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "mail_tm",
            },
            clear=False,
        ):
            resp = client.get("/api/v1/external/providers", headers=self._headers())

        self.assertEqual(resp.status_code, 200)
        diagnostics = resp.get_json()["data"]["provider_diagnostics"]
        defaults = diagnostics["defaults"]

        self.assertTrue(defaults["temp_mail_provider"]["valid"])
        self.assertFalse(defaults["temp_mail_provider"]["active"])
        self.assertEqual(defaults["temp_mail_provider"]["inactive_reason"], "not_in_active_allowlist")
        self.assertTrue(defaults["pool_claim_provider"]["valid"])
        self.assertFalse(defaults["pool_claim_provider"]["active"])
        self.assertEqual(defaults["pool_claim_provider"]["inactive_reason"], "not_in_active_allowlist")
        self.assertEqual(diagnostics["summary"]["inactive_default_entries"], 2)
        self.assertEqual(
            {item["key"]: item["provider"] for item in defaults["inactive_defaults"]},
            {
                "TEMP_MAIL_PROVIDER": "mail_tm",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "mail_tm",
            },
        )

    def test_apply_endpoint_rejects_inactive_provider_name(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        client = self.app.test_client()
        with patch(
            "outlook_web.controllers.external_temp_emails.temp_mail_service._provider_factory",
            return_value=_ProviderNameRecordingTempMailProvider("mail_tm"),
        ) as provider_factory:
            resp = client.post(
                "/api/v1/external/temp-emails/apply",
                headers=self._headers(),
                json={
                    "caller_id": "register-worker-1",
                    "task_id": "job-inactive-provider",
                    "provider_name": "mail_tm",
                },
            )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "MAILBOX_PROVIDER_NOT_ACTIVE")
        provider_factory.assert_not_called()

    def test_apply_endpoint_requires_caller_id_and_task_id(self):
        client = self.app.test_client()
        payloads = [
            {"task_id": "job-001"},
            {"caller_id": "worker-1"},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                resp = client.post(
                    "/api/v1/external/temp-emails/apply",
                    headers=self._headers(),
                    json=payload,
                )
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.get_json()["code"], "INVALID_PARAM")

    def test_apply_endpoint_rejects_non_object_json_body(self):
        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/temp-emails/apply",
            headers={**self._headers(), "Content-Type": "application/json"},
            data="[]",
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "INVALID_PARAM")

    def test_apply_endpoint_rejects_values_beyond_documented_limits(self):
        client = self.app.test_client()
        payloads = [
            {"caller_id": "c" * 65, "task_id": "job-001"},
            {"caller_id": "worker-1", "task_id": "t" * 129},
            {"caller_id": "worker-1", "task_id": "job-001", "domain": ("d" * 129) + ".test"},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                with patch(
                    "outlook_web.controllers.external_temp_emails.temp_mail_service._provider_factory",
                    return_value=_ProviderNameRecordingTempMailProvider("custom_domain_temp_mail"),
                ) as provider_factory:
                    resp = client.post(
                        "/api/v1/external/temp-emails/apply",
                        headers=self._headers(),
                        json=payload,
                    )
                self.assertEqual(resp.status_code, 400)
                self.assertIn(resp.get_json()["code"], {"INVALID_PARAM", "DOMAIN_INVALID"})
                provider_factory.assert_not_called()

    def test_finish_endpoint_marks_finished_and_cancels_pending_probe(self):
        client = self.app.test_client()

        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="finish@ext-temp.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="finish",
                domain="ext-temp.test",
                task_token="tmptask_finish",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker-1",
                task_id="job-001",
            )
            db = get_db()
            db.execute(
                """
                INSERT INTO external_probe_cache
                    (id, email_addr, folder, from_contains, subject_contains, since_minutes,
                     timeout_seconds, poll_interval, status, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+5 minutes'), datetime('now'), datetime('now'))
                """,
                ("probe-finish", "finish@ext-temp.test", "inbox", "", "", None, 30, 5, "pending"),
            )
            db.commit()

        resp = client.post(
            "/api/v1/external/temp-emails/tmptask_finish/finish",
            headers=self._headers(),
            json={"result": "success", "detail": "done"},
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["task_token"], "tmptask_finish")
        self.assertEqual(data["data"]["status"], "finished")

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            mailbox = db.execute(
                "SELECT status, finished_at FROM temp_emails WHERE task_token = ?",
                ("tmptask_finish",),
            ).fetchone()
            probe = db.execute(
                "SELECT status, error_code FROM external_probe_cache WHERE id = ?",
                ("probe-finish",),
            ).fetchone()

        self.assertEqual(mailbox["status"], "finished")
        self.assertTrue(mailbox["finished_at"])
        self.assertEqual(probe["status"], "cancelled")
        self.assertEqual(probe["error_code"], "PROBE_CANCELLED")

    def test_finish_endpoint_rejects_overlong_audit_fields_before_finishing(self):
        client = self.app.test_client()

        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="finish-too-long@ext-temp.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="finish-too-long",
                domain="ext-temp.test",
                task_token="tmptask_finish_too_long",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker-1",
                task_id="job-too-long",
            )

        resp = client.post(
            "/api/v1/external/temp-emails/tmptask_finish_too_long/finish",
            headers=self._headers(),
            json={"result": "r" * 513, "detail": "done"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "INVALID_PARAM")

        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            mailbox = temp_emails_repo.get_temp_email_by_task_token("tmptask_finish_too_long")

        self.assertEqual(mailbox["status"], "active")
        self.assertFalse(mailbox.get("finished_at"))

    def test_finish_endpoint_rejects_invalid_token_and_repeat_finish(self):
        client = self.app.test_client()

        invalid_resp = client.post(
            "/api/v1/external/temp-emails/tmptask_missing/finish",
            headers=self._headers(),
            json={"result": "failed"},
        )
        self.assertEqual(invalid_resp.status_code, 404)
        self.assertEqual(invalid_resp.get_json()["code"], "TASK_TOKEN_INVALID")

        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="repeat@ext-temp.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="repeat",
                domain="ext-temp.test",
                task_token="tmptask_repeat",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker-1",
                task_id="job-002",
            )

        first_resp = client.post(
            "/api/v1/external/temp-emails/tmptask_repeat/finish",
            headers=self._headers(),
            json={"result": "success"},
        )
        self.assertEqual(first_resp.status_code, 200)

        second_resp = client.post(
            "/api/v1/external/temp-emails/tmptask_repeat/finish",
            headers=self._headers(),
            json={"result": "success"},
        )
        self.assertEqual(second_resp.status_code, 409)
        self.assertEqual(second_resp.get_json()["code"], "TASK_ALREADY_FINISHED")

    def test_finish_endpoint_rejects_other_consumer_key(self):
        with self.app.app_context():
            from outlook_web.repositories import external_api_keys as external_api_keys_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            owner = external_api_keys_repo.create_external_api_key(name="owner", api_key="owner-key")
            external_api_keys_repo.create_external_api_key(name="other", api_key="other-key")
            temp_emails_repo.create_temp_email(
                email_addr="owned@ext-temp.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="owned",
                domain="ext-temp.test",
                task_token="tmptask_owned",
                consumer_key=owner["consumer_key"],
                caller_id="worker-1",
                task_id="job-002",
            )

        client = self.app.test_client()
        resp = client.post(
            "/api/v1/external/temp-emails/tmptask_owned/finish",
            headers=self._headers("other-key"),
            json={"result": "success"},
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "FORBIDDEN")

    def test_wait_message_returns_task_finished_when_finish_happens_during_wait(self):
        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="wait@ext-temp.test",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                prefix="wait",
                domain="ext-temp.test",
                task_token="tmptask_wait",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker-1",
                task_id="job-003",
            )

        call_count = {"value": 0}

        def _finish_during_first_poll(*, email_addr: str, **_: object):
            call_count["value"] += 1
            if call_count["value"] == 1:
                with self.app.app_context():
                    from outlook_web.repositories import temp_emails as temp_emails_repo

                    temp_emails_repo.finish_task_temp_email("tmptask_wait")
                from outlook_web.services import external_api as external_api_service

                raise external_api_service.MailNotFoundError("not yet")
            raise AssertionError("wait-message should stop before a second upstream poll")

        client = self.app.test_client()
        with patch("outlook_web.services.external_api.get_latest_message_for_external", side_effect=_finish_during_first_poll):
            with patch("outlook_web.services.external_api.time.sleep", return_value=None):
                resp = client.get(
                    "/api/v1/external/wait-message?email=wait@ext-temp.test&timeout_seconds=2&poll_interval=1",
                    headers=self._headers(),
                )

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["code"], "TASK_FINISHED")
