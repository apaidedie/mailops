import inspect
import json
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module


class ExternalApiBaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        self._clean_test_records()
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_key", "")
            settings_repo.set_setting("pool_default_provider", "")

    def tearDown(self):
        self._clean_test_records()

    def _clean_test_records(self):
        with self.app.app_context():
            clear_login_attempts()
            from outlook_web.db import get_db

            db = get_db()
            db.execute("DELETE FROM audit_logs WHERE resource_type = 'external_api'")
            # Full wipe so mailbox-directory readiness totals stay isolation-safe
            # when other suites leave residual accounts/temp mailboxes.
            db.execute("DELETE FROM temp_email_messages")
            db.execute("DELETE FROM temp_emails")
            db.execute("DELETE FROM account_claim_logs")
            db.execute("DELETE FROM accounts")
            db.execute("DELETE FROM external_api_keys")
            db.execute("DELETE FROM external_api_consumer_usage_daily")
            db.execute("DELETE FROM external_upstream_probes")
            db.execute("DELETE FROM external_probe_cache")
            db.commit()

    def _set_external_api_key(self, value: str):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_key", value)

    def _create_external_api_key(
        self,
        name: str,
        api_key: str,
        *,
        allowed_emails: list[str] | None = None,
        pool_access: bool = False,
        enabled: bool = True,
    ):
        with self.app.app_context():
            from outlook_web.repositories import external_api_keys as external_api_keys_repo

            return external_api_keys_repo.create_external_api_key(
                name=name,
                api_key=api_key,
                allowed_emails=allowed_emails or [],
                pool_access=pool_access,
                enabled=enabled,
            )

    def _insert_outlook_account(self, email_addr: str | None = None) -> str:
        email_addr = email_addr or f"{uuid.uuid4().hex}@extapi.test"
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, group_id, status, account_type, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email_addr,
                    "pw",
                    "cid-test",
                    "rt-test",
                    1,
                    "active",
                    "outlook",
                    "outlook",
                ),
            )
            db.commit()
        return email_addr

    def _insert_imap_account(self, email_addr: str | None = None) -> str:
        email_addr = email_addr or f"{uuid.uuid4().hex}@extapi.test"
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, group_id, status,
                    account_type, provider, imap_host, imap_port, imap_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email_addr,
                    "pw",
                    "cid-test",
                    "rt-test",
                    1,
                    "active",
                    "imap",
                    "custom",
                    "imap.test.com",
                    993,
                    "imap-pass",
                ),
            )
            db.commit()
        return email_addr

    def _set_account_status(self, email_addr: str, status: str):
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute("UPDATE accounts SET status = ? WHERE email = ?", (status, email_addr))
            db.commit()

    @staticmethod
    def _auth_headers(value: str = "abc123"):
        return {"X-API-Key": value}

    @staticmethod
    def _canonical_external_endpoints() -> dict[str, str]:
        from outlook_web.services.provider_catalog import get_external_api_endpoint_map

        return get_external_api_endpoint_map()

    @staticmethod
    def _legacy_external_endpoints() -> dict[str, str]:
        from outlook_web.services.provider_catalog import get_external_api_legacy_endpoint_map

        return get_external_api_legacy_endpoint_map()

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def _assert_provider_documentation_contract(self, documentation: dict):
        endpoints = self._canonical_external_endpoints()
        legacy_endpoints = self._legacy_external_endpoints()
        self.assertEqual(documentation.get("version"), 1)
        self.assertEqual(documentation.get("recommended_human_start"), "provider_onboarding")
        self.assertEqual(documentation.get("recommended_machine_start"), "openapi")
        entries = documentation.get("entries") or {}
        self.assertEqual(entries.get("provider_onboarding", {}).get("path"), "docs/provider-onboarding.md")
        self.assertEqual(
            entries.get("external_integration_quickstart", {}).get("path"), "docs/external-integration-quickstart.md"
        )
        self.assertEqual(entries.get("plugin_extension", {}).get("path"), "docs/temp-mail-provider-plugin-guide.md")
        self.assertEqual(entries.get("plugin_prompt", {}).get("path"), "docs/temp-mail-provider-plugin-prompt.md")
        self.assertEqual(entries.get("env_example", {}).get("path"), ".env.example")
        self.assertEqual(entries.get("provider_config_json", {}).get("path"), ".runtime/providers.example.json")
        self.assertEqual(entries.get("provider_config_toml", {}).get("path"), ".runtime/providers.example.toml")
        self.assertEqual(entries.get("openapi", {}).get("endpoint"), endpoints["openapi"])
        self.assertEqual(entries.get("api_docs", {}).get("endpoint"), endpoints["docs"])
        self.assertNotIn("legacy_endpoint", entries.get("api_docs", {}))
        self.assertNotRegex(json.dumps(documentation, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")
        for forbidden in ("api_key", "bearer", "jwt", "password", "refresh_token", "task_token", "consumer_key"):
            self.assertNotIn(f"{forbidden}=", json.dumps(documentation, ensure_ascii=False).lower())

    def _assert_provider_capability_matrix_contract(self, matrix: dict):
        endpoints = self._canonical_external_endpoints()
        self.assertEqual(matrix.get("version"), 1)
        self.assertIn("provider_catalog", matrix.get("generated_from") or [])
        for key in (
            "providers",
            "account_providers",
            "temp_providers",
            "dynamic_create_providers",
            "pool_inventory_providers",
            "task_temp_capable_providers",
            "pool_claim_capable_providers",
            "session_capable_providers",
            "needs_config_providers",
        ):
            self.assertIsInstance((matrix.get("totals") or {}).get(key), int, f"capability_matrix.totals.{key} missing")
            self.assertGreaterEqual((matrix.get("totals") or {}).get(key), 0)
        workflows = matrix.get("workflows") or {}
        for workflow in ("mailbox_session", "pool_claim", "task_temp_mailbox", "mailbox_directory", "provider_health"):
            self.assertIn(workflow, workflows)
            self.assertEqual(workflows[workflow]["workflow"], workflow)
            self.assertIsInstance(workflows[workflow]["providers"], list)
            self.assertEqual(workflows[workflow]["provider_count"], len(workflows[workflow]["providers"]))
            self.assertIn("pool_claim", workflows[workflow]["selector_fields"])
            self.assertIn("task_temp_apply", workflows[workflow]["selector_fields"])
        providers = {item["provider"]: item for item in matrix.get("providers") or []}
        for provider in ("mail_tm", "duckmail"):
            self.assertIn(provider, providers)
            row = providers[provider]
            self.assertEqual(row["kind"], "temp")
            self.assertTrue(row["capabilities"]["can_dynamic_create"])
            self.assertTrue(row["capabilities"]["task_temp_capable"])
            self.assertTrue(row["capabilities"]["session_capable"])
            self.assertEqual(row["selection_fields"]["task_temp_apply"], {"field": "provider_name", "value": provider})
            self.assertEqual(row["endpoints"]["mailbox_session_start"], endpoints["mailbox_session_start"])
            self.assertIn("verification_code", row["read"]["actions"])
            self.assertIn("finish_task_mailbox", row["lifecycle_actions"])
        account_rows = [item for item in providers.values() if item.get("kind") == "account"]
        self.assertTrue(account_rows)
        account_row = account_rows[0]
        self.assertTrue(account_row["capabilities"]["requires_pool_inventory"])
        self.assertTrue(account_row["capabilities"]["pool_claim_capable"])
        self.assertIn("claim_pool_mailbox", account_row["lifecycle_actions"])
        serialized = json.dumps(matrix, ensure_ascii=False)
        self.assertNotRegex(serialized, r"dk_[0-9a-fA-F]{20,}")
        self.assertNotRegex(serialized, r"Bearer\s+[A-Za-z0-9_.-]+")
        self.assertNotIn("consumer_key=", serialized.lower())
        self.assertNotIn("refresh_token=", serialized.lower())

    def _assert_external_quickstart_contract(self, data: dict):
        endpoints = self._canonical_external_endpoints()
        manifest = data["integration_manifest"]
        quickstart = data["quickstart"]
        self.assertEqual(quickstart, manifest["quickstart"])
        self.assertEqual(quickstart["version"], 1)
        self.assertEqual(quickstart["auth"]["header"], "X-API-Key")
        self.assertEqual(quickstart["auth"]["placeholder"], "<your-api-key>")
        self.assertEqual(quickstart["auth"]["headers"], {"X-API-Key": "<your-api-key>"})
        self.assertEqual(quickstart["auth"]["curl_header"], "X-API-Key: <your-api-key>")
        sequence = [item["step"] for item in quickstart["recommended_sequence"]]
        self.assertEqual(sequence[:3], ["capabilities", "providers", "mailboxes"])
        self.assertEqual(quickstart["recommended_sequence"][0]["endpoint"], endpoints["capabilities"])
        self.assertEqual(quickstart["recommended_sequence"][1]["endpoint"], endpoints["providers"])
        self.assertEqual(
            quickstart["recommended_sequence"][2]["query"], {"kind": "all", "provider": "all", "sort": "updated_desc"}
        )
        self.assertEqual(quickstart["endpoints"]["capabilities"], endpoints["capabilities"])
        self.assertEqual(quickstart["endpoints"]["openapi"], endpoints["openapi"])
        self.assertEqual(quickstart["endpoints"]["providers"], endpoints["providers"])
        self.assertEqual(quickstart["endpoints"]["provider_preflight"], endpoints["provider_preflight"])
        self.assertEqual(quickstart["endpoints"]["mailboxes"], endpoints["mailboxes"])
        self.assertEqual(quickstart["endpoints"]["mailbox_session_start"], endpoints["mailbox_session_start"])
        self.assertEqual(quickstart["endpoints"]["mailbox_session_close"], endpoints["mailbox_session_close"])
        self.assertEqual(quickstart["endpoints"]["pool_claim_random"], endpoints["pool_claim_random"])
        self.assertEqual(quickstart["endpoints"]["temp_mail_apply"], endpoints["temp_mail_apply"])
        self.assertEqual(quickstart["endpoints"]["messages"], endpoints["messages"])
        self.assertEqual(quickstart["endpoints"]["verification_code"], endpoints["verification_code"])
        selection = data["selection_policy"]["scopes"]
        selectors = quickstart["provider_selector_fields"]
        self.assertEqual(selectors["pool_claim"]["field"], "provider")
        self.assertEqual(selectors["task_temp_apply"]["field"], "provider_name")
        self.assertEqual(selectors["pool_claim"]["allowed_values"], selection["explicit_pool_claim"]["allowed_values"])
        self.assertEqual(selectors["task_temp_apply"]["allowed_values"], selection["task_temp_apply"]["allowed_values"])
        requests = quickstart["requests"]
        self.assertEqual(requests["mailbox_directory"]["method"], "GET")
        self.assertEqual(requests["mailbox_directory"]["query"], {"kind": "all", "provider": "all", "sort": "updated_desc"})
        self.assertEqual(requests["provider_preflight"]["method"], "GET")
        self.assertEqual(requests["provider_preflight"]["endpoint"], endpoints["provider_preflight"])
        self.assertEqual(requests["provider_preflight"]["query"], {"probe_network": False})
        self.assertEqual(requests["pool_claim"]["method"], "POST")
        self.assertEqual(requests["pool_claim"]["body"]["provider"], "<provider-or-auto>")
        self.assertIn("caller_id", requests["pool_claim"]["body"])
        self.assertIn("task_id", requests["pool_claim"]["body"])
        self.assertEqual(requests["task_temp_apply"]["method"], "POST")
        self.assertEqual(requests["task_temp_apply"]["body"]["provider_name"], "<provider-name>")
        self.assertIn("prefix", requests["task_temp_apply"]["body"])
        self.assertIn("domain", requests["task_temp_apply"]["body"])
        self.assertEqual(requests["mailbox_session_start"]["method"], "POST")
        self.assertEqual(requests["mailbox_session_start"]["endpoint"], endpoints["mailbox_session_start"])
        self.assertEqual(requests["mailbox_session_start"]["body"]["source_strategy"], "pool_first")
        self.assertEqual(requests["mailbox_session_close"]["method"], "POST")
        self.assertEqual(requests["mailbox_session_close"]["endpoint"], endpoints["mailbox_session_close"])
        self.assertEqual(requests["mailbox_session_close"]["body"]["session_type"], "<session-type-from-start-response>")
        self.assertEqual(requests["read_messages"]["endpoint"], endpoints["messages"])
        self.assertEqual(requests["read_verification_code"]["endpoint"], endpoints["verification_code"])
        self.assertEqual(quickstart["workflow_keys"]["browse_mailbox_directory"], "browse_mailbox_directory")
        self.assertEqual(quickstart["workflow_keys"]["start_mailbox_session"], "start_mailbox_session")
        self.assertEqual(quickstart["workflow_keys"]["close_mailbox_session"], "start_mailbox_session.close_session")
        self.assertEqual(quickstart["workflow_keys"]["claim_pool_mailbox"], "claim_pool_mailbox")
        self.assertEqual(quickstart["workflow_keys"]["create_task_temp_mailbox"], "create_task_temp_mailbox")
        quickstart_text = json.dumps(quickstart, ensure_ascii=False)
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", quickstart_text)
        self.assertNotRegex(quickstart_text, r"dk_[0-9a-fA-F]{20,}")
        self.assertNotRegex(quickstart_text, r"Bearer\s+[A-Za-z0-9_.-]+")
        self.assertNotRegex(quickstart_text, r"tmptask_[A-Za-z0-9_.:-]+")
        self.assertNotIn("password", quickstart_text.lower())
        self.assertNotIn("consumer_key", quickstart_text.lower())

    @staticmethod
    def _utc_iso(minutes_delta: int = 0) -> str:
        dt = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=minutes_delta)
        return dt.isoformat().replace("+00:00", "Z")

    @classmethod
    def _graph_email(
        cls,
        message_id: str = "msg-1",
        subject: str = "Your verification code",
        sender: str = "noreply@example.com",
        received_at: str | None = None,
    ):
        return {
            "id": message_id,
            "subject": subject,
            "from": {"emailAddress": {"address": sender}},
            "receivedDateTime": received_at or cls._utc_iso(),
            "isRead": False,
            "hasAttachments": False,
            "bodyPreview": "Your code is 123456",
        }

    @classmethod
    def _graph_detail(
        cls,
        message_id: str = "msg-1",
        body_text: str = "Your code is 123456",
        html_text: str = "<p>Your code is 123456</p>",
        received_at: str | None = None,
    ):
        return {
            "id": message_id,
            "subject": "Your verification code",
            "from": {"emailAddress": {"address": "noreply@example.com"}},
            "toRecipients": [{"emailAddress": {"address": "user@outlook.com"}}],
            "receivedDateTime": received_at or cls._utc_iso(),
            "body": {
                "content": body_text if body_text else html_text,
                "contentType": "text" if body_text else "html",
            },
        }

    def _external_audit_logs(self):
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            rows = db.execute("""
                SELECT action, resource_id, details
                FROM audit_logs
                WHERE resource_type = 'external_api'
                ORDER BY id ASC
                """).fetchall()
        return [dict(row) for row in rows]

    def _external_consumer_usage_rows(self):
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            rows = db.execute("""
                SELECT consumer_key, consumer_name, endpoint, total_count, success_count, error_count
                FROM external_api_consumer_usage_daily
                ORDER BY id ASC
                """).fetchall()
        return [dict(row) for row in rows]


class ExternalApiAuthTests(ExternalApiBaseTest):
    def test_external_health_requires_api_key(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        resp = client.get("/api/v1/external/health")

        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "UNAUTHORIZED")

    def test_external_health_returns_403_when_api_key_not_configured(self):
        client = self.app.test_client()

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("abc123"))

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "API_KEY_NOT_CONFIGURED")

    def test_external_health_accepts_valid_api_key(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("abc123"))

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("code"), "OK")

    def test_external_health_accepts_valid_multi_api_key(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-123")

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("multi-123"))

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def test_disabled_multi_api_key_rejected(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-123", enabled=False)

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("multi-123"))

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "API_KEY_NOT_CONFIGURED")

    def test_disabled_multi_api_key_returns_401_when_other_enabled_key_exists(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-123", enabled=False)
        self._create_external_api_key("partner-b", "multi-456", enabled=True)

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("multi-123"))

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")

    def test_legacy_external_api_key_still_works_when_multi_keys_exist(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-a", "multi-123")
        self._set_external_api_key("legacy-123")

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("legacy-123"))

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))


class ExternalApiMessageTests(ExternalApiBaseTest):
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_latest_message_returns_filtered_latest_email(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        newer = self._graph_email(message_id="msg-new", subject="Target mail", received_at=self._utc_iso())
        older = self._graph_email(
            message_id="msg-old",
            subject="Ignore mail",
            received_at=self._utc_iso(minutes_delta=-2),
        )
        mock_get_emails_graph.return_value = {"success": True, "emails": [older, newer]}

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/latest?email={email_addr}&subject_contains=Target",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("id"), "msg-new")

    def test_external_messages_returns_account_not_found(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        resp = client.get(
            "/api/v1/external/messages?email=missing@extapi.test",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "ACCOUNT_NOT_FOUND")

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_messages_returns_list_when_graph_succeeds(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("code"), "OK")
        self.assertEqual(len(data.get("data", {}).get("emails", [])), 1)


class ExternalApiKeyScopeTests(ExternalApiBaseTest):
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_messages_allows_email_within_key_scope(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._create_external_api_key("partner-a", "scope-123", allowed_emails=[email_addr])
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers("scope-123"),
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def test_external_messages_reject_email_outside_key_scope(self):
        allowed_email = self._insert_outlook_account()
        denied_email = self._insert_outlook_account()
        self._create_external_api_key("partner-a", "scope-123", allowed_emails=[allowed_email])

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={denied_email}",
            headers=self._auth_headers("scope-123"),
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "EMAIL_SCOPE_FORBIDDEN")

    def test_external_account_status_reject_email_outside_key_scope(self):
        allowed_email = self._insert_outlook_account()
        denied_email = self._insert_outlook_account()
        self._create_external_api_key("partner-a", "scope-123", allowed_emails=[allowed_email])

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/account-status?email={denied_email}",
            headers=self._auth_headers("scope-123"),
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "EMAIL_SCOPE_FORBIDDEN")

    def test_probe_status_rejects_email_outside_key_scope(self):
        allowed_email = self._insert_outlook_account()
        denied_email = self._insert_outlook_account()
        self._create_external_api_key("partner-a", "scope-123", allowed_emails=[allowed_email])

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            now = datetime.now(timezone.utc).isoformat()
            future = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
            db.execute(
                """
                INSERT INTO external_probe_cache
                    (id, email_addr, status, timeout_seconds, poll_interval, expires_at, created_at, updated_at)
                VALUES (?, ?, 'pending', 30, 5, ?, ?, ?)
                """,
                ("scope-probe-1", denied_email, future, now, now),
            )
            db.commit()

        client = self.app.test_client()
        resp = client.get("/api/v1/external/probe/scope-probe-1", headers=self._auth_headers("scope-123"))

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "EMAIL_SCOPE_FORBIDDEN")


class ExternalApiConsumerAuditTests(ExternalApiBaseTest):
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_multi_key_request_records_consumer_metadata_and_usage(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        created = self._create_external_api_key("partner-a", "audit-123", allowed_emails=[email_addr])
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers("audit-123"),
        )

        self.assertEqual(resp.status_code, 200)
        audit_logs = self._external_audit_logs()
        self.assertEqual(len(audit_logs), 1)
        self.assertIn('"consumer_name": "partner-a"', audit_logs[0]["details"])
        self.assertIn(f'"consumer_id": {created["id"]}', audit_logs[0]["details"])

        usage_rows = self._external_consumer_usage_rows()
        self.assertEqual(len(usage_rows), 1)
        self.assertEqual(usage_rows[0]["consumer_key"], created["consumer_key"])
        self.assertEqual(usage_rows[0]["consumer_name"], "partner-a")
        self.assertEqual(usage_rows[0]["endpoint"], "/api/v1/external/messages")
        self.assertEqual(usage_rows[0]["total_count"], 1)
        self.assertEqual(usage_rows[0]["success_count"], 1)

    @patch("outlook_web.services.imap.get_emails_imap_with_server")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_messages_falls_back_to_imap_when_graph_fails(self, mock_get_emails_graph, mock_get_emails_imap):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {"success": False, "error": "graph failed"}
        mock_get_emails_imap.return_value = {
            "success": True,
            "emails": [
                {
                    "id": "imap-1",
                    "subject": "IMAP Subject",
                    "from": "imap@example.com",
                    "date": "2026-03-08T12:00:00Z",
                    "is_read": False,
                    "has_attachments": False,
                    "body_preview": "preview",
                }
            ],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(len(data.get("data", {}).get("emails", [])), 1)

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    def test_external_message_detail_returns_message_content(self, mock_get_email_detail_graph, mock_get_email_raw_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_email_detail_graph.return_value = self._graph_detail()
        mock_get_email_raw_graph.return_value = "RAW MIME CONTENT"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/msg-1?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("content", data.get("data", {}))
        self.assertIn("raw_content", data.get("data", {}))
        self.assertEqual(data.get("data", {}).get("raw_content"), "RAW MIME CONTENT")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    def test_external_message_raw_returns_raw_content_and_audits(self, mock_get_email_detail_graph, mock_get_email_raw_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_email_detail_graph.return_value = self._graph_detail(body_text="raw test")
        mock_get_email_raw_graph.return_value = "MIME-Version: 1.0\r\nraw test"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/msg-1/raw?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("raw_content"), "MIME-Version: 1.0\r\nraw test")

        audit_logs = self._external_audit_logs()
        self.assertEqual(len(audit_logs), 1)
        self.assertIn("/api/v1/external/messages/{message_id}/raw", audit_logs[0]["details"])


class ExternalApiVerificationTests(ExternalApiBaseTest):
    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_verification_code_returns_code(
        self,
        mock_get_emails_graph,
        mock_get_email_detail_graph,
        mock_get_email_raw_graph,
    ):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }
        mock_get_email_detail_graph.return_value = self._graph_detail(body_text="Your code is 123456")
        mock_get_email_raw_graph.return_value = "RAW MIME CONTENT"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("verification_code"), "123456")

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_verification_code_defaults_to_recent_10_minutes(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email(received_at=self._utc_iso(minutes_delta=-20))],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "MAIL_NOT_FOUND")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_verification_link_returns_preferred_link(
        self,
        mock_get_emails_graph,
        mock_get_email_detail_graph,
        mock_get_email_raw_graph,
    ):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Please verify your email")],
        }
        mock_get_email_detail_graph.return_value = self._graph_detail(
            body_text="Click https://example.com/verify?token=abc to continue",
        )
        mock_get_email_raw_graph.return_value = "RAW MIME CONTENT"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("verify", data.get("data", {}).get("verification_link", ""))

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_verification_link_defaults_to_recent_10_minutes(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [
                self._graph_email(
                    subject="Please verify your email",
                    received_at=self._utc_iso(minutes_delta=-30),
                )
            ],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "MAIL_NOT_FOUND")

    @patch("outlook_web.services.external_api.time.sleep")
    @patch("outlook_web.services.external_api.time.time")
    @patch("outlook_web.services.external_api.probes.get_latest_message_for_external")
    def test_wait_for_message_only_returns_new_messages(self, mock_get_latest_message, mock_time, mock_sleep):
        from outlook_web.services import external_api as external_api_service

        mock_time.side_effect = [100, 100, 100]
        mock_get_latest_message.side_effect = [
            {"id": "old", "timestamp": 99, "method": "Graph API"},
            {"id": "new", "timestamp": 101, "method": "Graph API"},
        ]

        result = external_api_service.wait_for_message(email_addr="user@example.com", timeout_seconds=30, poll_interval=5)

        self.assertEqual(result.get("id"), "new")
        mock_sleep.assert_called_once_with(5)

    def test_external_wait_message_rejects_too_large_timeout(self):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&timeout_seconds=999",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")


class ExternalApiSystemTests(ExternalApiBaseTest):
    def test_external_capabilities_returns_feature_list_and_audits(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("service", data.get("data", {}))
        self.assertIn("version", data.get("data", {}))
        self.assertIn("features", data.get("data", {}))

        audit_logs = self._external_audit_logs()
        self.assertEqual(len(audit_logs), 1)
        self.assertIn("/api/v1/external/capabilities", audit_logs[0]["details"])

    def test_external_health_audits_access(self):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.services import external_api as external_api_service

            external_api_service.record_upstream_probe_summary(
                scope_type="instance",
                scope_key="__instance__",
                email_addr="probe@extapi.test",
                probe_ok=True,
                probe_method="Graph API",
                last_probe_error="",
                last_probe_at=self._utc_iso(),
            )

        resp = client.get("/api/v1/external/health", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertTrue(data.get("upstream_probe_ok"))
        self.assertTrue(data.get("last_probe_at"))
        audit_logs = self._external_audit_logs()
        self.assertEqual(len(audit_logs), 1)
        self.assertIn("/api/v1/external/health", audit_logs[0]["details"])

    @patch("outlook_web.controllers.system.external_api_service.probe_instance_upstream")
    def test_external_health_uses_probe_instance_upstream(self, mock_probe_instance_upstream):
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        mock_probe_instance_upstream.return_value = {
            "upstream_probe_ok": True,
            "last_probe_at": self._utc_iso(),
            "last_probe_error": "",
            "probe_method": "Graph API",
        }

        resp = client.get("/api/v1/external/health", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("data", {}).get("upstream_probe_ok"))
        mock_probe_instance_upstream.assert_called_once()

    def test_external_health_returns_secret_free_readiness_summary(self):
        endpoints = self._canonical_external_endpoints()
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")
            settings_repo.set_setting("duckmail_bearer_token", "test-secret-should-not-leak")
            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        with patch(
            "outlook_web.controllers.system.external_api_service.probe_instance_upstream",
            return_value={"upstream_probe_ok": None, "last_probe_at": "", "last_probe_error": ""},
        ):
            resp = client.get("/api/v1/external/health", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        readiness = resp.get_json().get("data", {}).get("readiness", {})
        self.assertIn(readiness.get("status"), {"ready", "degraded"})
        self.assertEqual(
            readiness.get("discovery", {}).get("next_endpoints", {}).get("capabilities"), endpoints["capabilities"]
        )
        self.assertEqual(readiness.get("discovery", {}).get("next_endpoints", {}).get("providers"), endpoints["providers"])
        self.assertEqual(readiness.get("providers", {}).get("filter_mode"), "allowlist")
        self.assertIn("duckmail", readiness.get("providers", {}).get("active_allowlist", []))
        self.assertEqual(readiness.get("pool", {}).get("status"), "ready")
        self.assertEqual(readiness.get("pool", {}).get("claim_endpoint"), endpoints["pool_claim_random"])
        self.assertEqual(readiness.get("task_temp_mailbox", {}).get("provider_selector_field"), "provider_name")
        self.assertEqual(readiness.get("task_temp_mailbox", {}).get("apply_endpoint"), endpoints["temp_mail_apply"])
        self.assertNotIn("test-secret-should-not-leak", json.dumps(readiness, ensure_ascii=False))

    def test_external_health_returns_mailbox_directory_readiness_inventory(self):
        endpoints = self._canonical_external_endpoints()
        client = self.app.test_client()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import groups as groups_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = int(groups_repo.get_default_group_id())
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, group_id, status,
                    account_type, provider, imap_host, imap_port, imap_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "health-directory-account@extapi.test",
                    "account-password-should-not-leak",
                    "cid-health",
                    "refresh-token-should-not-leak",
                    default_group_id,
                    "active",
                    "imap",
                    "custom",
                    "imap.health.test",
                    993,
                    "imap-secret-should-not-leak",
                ),
            )
            temp_emails_repo.create_temp_email(
                email_addr="health-directory-temp@extapi.test",
                source="duckmail",
                provider_name="duckmail",
                task_token="tmptask_health_secret",
                consumer_key="consumer:health-secret",
                status="active",
                meta={"provider_jwt": "jwt-health-secret", "provider_secret": "provider-health-secret"},
            )
            db.commit()

        with patch(
            "outlook_web.controllers.system.external_api_service.probe_instance_upstream",
            return_value={"upstream_probe_ok": None, "last_probe_at": "", "last_probe_error": ""},
        ):
            resp = client.get("/api/v1/external/health", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        readiness = resp.get_json().get("data", {}).get("readiness", {})
        mailbox_directory = readiness.get("mailbox_directory") or {}
        self.assertEqual(mailbox_directory.get("endpoint"), endpoints["mailboxes"])
        self.assertEqual(mailbox_directory.get("status"), "ready")
        self.assertFalse(mailbox_directory.get("scoped"))
        self.assertEqual(mailbox_directory.get("totals", {}).get("mailboxes"), 2)
        self.assertEqual(mailbox_directory.get("totals", {}).get("account_mailboxes"), 1)
        self.assertEqual(mailbox_directory.get("totals", {}).get("temp_mailboxes"), 1)
        self.assertEqual(mailbox_directory.get("summary", {}).get("account"), 1)
        self.assertEqual(mailbox_directory.get("summary", {}).get("temp"), 1)
        self.assertEqual(
            mailbox_directory.get("quick_probe_params"),
            {
                "page": 1,
                "page_size": 1,
                "kind": "all",
                "status": "all",
                "read_capability": "all",
                "action": "all",
                "provider": "all",
                "sort": "updated_desc",
            },
        )
        readiness_json = json.dumps(readiness, ensure_ascii=False)
        self.assertNotIn("account-password-should-not-leak", readiness_json)
        self.assertNotIn("refresh-token-should-not-leak", readiness_json)
        self.assertNotIn("imap-secret-should-not-leak", readiness_json)
        self.assertNotIn("tmptask_health_secret", readiness_json)
        self.assertNotIn("consumer:health-secret", readiness_json)
        self.assertNotIn("jwt-health-secret", readiness_json)
        self.assertNotIn("provider-health-secret", readiness_json)

    def test_external_health_mailbox_directory_readiness_respects_allowed_email_scope(self):
        client = self.app.test_client()
        self._create_external_api_key(
            "scoped-health",
            "scoped-health-key",
            allowed_emails=["health-scope-allowed@extapi.test"],
        )
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import groups as groups_repo
            from outlook_web.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = int(groups_repo.get_default_group_id())
            for email_addr in ("health-scope-allowed@extapi.test", "health-scope-denied@extapi.test"):
                db.execute(
                    """
                    INSERT INTO accounts (email, password, client_id, refresh_token, group_id, status, account_type, provider)
                    VALUES (?, '', ?, ?, ?, 'active', 'outlook', 'outlook')
                    """,
                    (email_addr, f"cid-{email_addr}", f"rt-{email_addr}", default_group_id),
                )
            temp_emails_repo.create_temp_email(
                email_addr="health-scope-temp@extapi.test",
                source="mail_tm",
                provider_name="mail_tm",
                status="active",
            )
            db.commit()

        with patch(
            "outlook_web.controllers.system.external_api_service.probe_instance_upstream",
            return_value={"upstream_probe_ok": None, "last_probe_at": "", "last_probe_error": ""},
        ):
            resp = client.get("/api/v1/external/health", headers=self._auth_headers("scoped-health-key"))

        self.assertEqual(resp.status_code, 200)
        mailbox_directory = resp.get_json().get("data", {}).get("readiness", {}).get("mailbox_directory") or {}
        self.assertEqual(mailbox_directory.get("status"), "ready")
        self.assertTrue(mailbox_directory.get("scoped"))
        self.assertEqual(mailbox_directory.get("totals", {}).get("mailboxes"), 2)
        self.assertEqual(mailbox_directory.get("totals", {}).get("account_mailboxes"), 1)
        self.assertEqual(mailbox_directory.get("totals", {}).get("temp_mailboxes"), 1)
        self.assertEqual(mailbox_directory.get("summary", {}).get("account"), 1)
        self.assertEqual(mailbox_directory.get("summary", {}).get("temp"), 1)

    def test_external_health_marks_pool_restricted_for_key_without_pool_access(self):
        client = self.app.test_client()
        self._create_external_api_key("partner-no-pool", "multi-no-pool", pool_access=False)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("multi-no-pool"))

        self.assertEqual(resp.status_code, 200)
        readiness = resp.get_json().get("data", {}).get("readiness", {})
        self.assertEqual(readiness.get("pool", {}).get("status"), "restricted")
        self.assertIn("pool_access_required", readiness.get("pool", {}).get("restrictions", []))
        self.assertNotEqual(readiness.get("providers", {}).get("status"), "restricted")

    @patch("outlook_web.services.external_api.graph_service.get_emails_graph")
    def test_external_account_status_returns_account_data_and_audits(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/account-status?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("email"), email_addr)
        self.assertTrue(data.get("data", {}).get("exists"))
        self.assertEqual(data.get("data", {}).get("account_type"), "outlook")
        self.assertEqual(data.get("data", {}).get("provider"), "outlook")
        self.assertIn("preferred_method", data.get("data", {}))
        self.assertIn("last_refresh_at", data.get("data", {}))
        self.assertTrue(data.get("data", {}).get("can_read"))
        self.assertTrue(data.get("data", {}).get("upstream_probe_ok"))
        self.assertTrue(data.get("data", {}).get("last_probe_at"))
        self.assertEqual(data.get("data", {}).get("probe_method"), "Graph API")
        self.assertEqual(data.get("data", {}).get("last_probe_error"), "")

        audit_logs = self._external_audit_logs()
        self.assertEqual(len(audit_logs), 1)
        self.assertIn("/api/v1/external/account-status", audit_logs[0]["details"])

    @patch("outlook_web.services.external_api.imap_service.get_emails_imap_with_server")
    @patch("outlook_web.services.external_api.graph_service.get_emails_graph")
    def test_external_account_status_probe_failure_returns_probe_summary(self, mock_get_emails_graph, mock_get_emails_imap):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": False,
            "error": {"message": "token invalid"},
        }
        mock_get_emails_imap.return_value = {
            "success": False,
            "error": {"message": "imap fallback failed"},
        }
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/account-status?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertFalse(data.get("upstream_probe_ok"))
        self.assertEqual(data.get("probe_method"), "graph")
        self.assertTrue(data.get("last_probe_at"))
        self.assertTrue(data.get("last_probe_error"))


class ExternalApiRegressionTests(ExternalApiBaseTest):
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_internal_email_list_api_still_works(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }

        client = self.app.test_client()
        self._login(client)
        resp = client.get(f"/api/emails/{email_addr}")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("emails", data)

    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_internal_extract_verification_api_still_works(self, mock_get_emails_graph, mock_get_email_detail_graph):
        email_addr = self._insert_outlook_account()
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }
        mock_get_email_detail_graph.return_value = self._graph_detail(body_text="Your code is 123456")

        client = self.app.test_client()
        self._login(client)
        resp = client.get(f"/api/emails/{email_addr}/extract-verification")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("verification_code"), "123456")

    def test_internal_settings_api_still_returns_existing_fields(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/settings")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("refresh_interval_days", data.get("settings", {}))
        self.assertIn("temp_mail_api_key_set", data.get("settings", {}))
        self.assertNotIn("gptmail_api_key_set", data.get("settings", {}))


class ExternalApiSchemaValidationTests(ExternalApiBaseTest):
    """OpenAPI 返回字段抽样校验：确认核心接口的返回字段覆盖 OpenAPI schema required 字段"""

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_messages_response_schema_has_required_fields(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }

        client = self.app.test_client()
        resp = client.get(f"/api/v1/external/messages?email={email_addr}", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        # 顶层统一响应结构
        for key in ("success", "code", "message", "data"):
            self.assertIn(key, body, f"顶层缺少字段: {key}")
        data = body["data"]
        self.assertIn("emails", data)
        self.assertIn("count", data)
        # MessageSummary required 字段
        if data["emails"]:
            msg = data["emails"][0]
            for key in (
                "id",
                "email_address",
                "from_address",
                "subject",
                "has_html",
                "timestamp",
                "created_at",
                "is_read",
            ):
                self.assertIn(key, msg, f"MessageSummary 缺少字段: {key}")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    def test_message_detail_response_schema_has_required_fields(self, mock_detail, mock_raw):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_detail.return_value = self._graph_detail()
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/msg-1?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        for key in (
            "id",
            "email_address",
            "from_address",
            "subject",
            "content",
            "html_content",
            "raw_content",
            "timestamp",
            "created_at",
            "has_html",
        ):
            self.assertIn(key, data, f"MessageDetail 缺少字段: {key}")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_verification_code_response_schema_has_required_fields(self, mock_list, mock_detail, mock_raw):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        mock_detail.return_value = self._graph_detail(body_text="Your code is 123456")
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        for key in (
            "email",
            "verification_code",
            "matched_email_id",
            "from",
            "subject",
            "received_at",
        ):
            self.assertIn(key, data, f"VerificationCodeData 缺少字段: {key}")
        # confidence 枚举校验
        self.assertIn(data.get("confidence"), ("high", "low"), "confidence 应为 high 或 low")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_verification_link_response_schema_has_required_fields(self, mock_list, mock_detail, mock_raw):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Please verify")],
        }
        mock_detail.return_value = self._graph_detail(
            body_text="Click https://example.com/verify?token=abc to verify",
        )
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        for key in (
            "email",
            "verification_link",
            "matched_email_id",
            "from",
            "subject",
            "received_at",
        ):
            self.assertIn(key, data, f"VerificationLinkData 缺少字段: {key}")

    def test_health_response_schema_has_required_fields(self):
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        for key in (
            "status",
            "service",
            "version",
            "server_time_utc",
            "database",
            "upstream_probe_ok",
            "last_probe_at",
            "last_probe_error",
        ):
            self.assertIn(key, data, f"HealthData 缺少字段: {key}")

    def test_capabilities_response_schema_has_required_fields(self):
        self._set_external_api_key("abc123")
        from outlook_web.services.mailbox_directory_contract import get_mailbox_catalog_contract

        endpoints = self._canonical_external_endpoints()
        legacy_endpoints = self._legacy_external_endpoints()
        expected_contract = get_mailbox_catalog_contract()
        client = self.app.test_client()
        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        for key in (
            "service",
            "version",
            "features",
            "endpoints",
            "integration_bundle",
            "external_mailbox_read_contract",
            "mailbox_session",
            "pool",
            "task_temp_mailbox",
            "provider_integration_guide",
            "integration_manifest",
            "quickstart",
            "documentation",
        ):
            self.assertIn(key, data, f"CapabilitiesData 缺少字段: {key}")
        self.assertIsInstance(data["features"], list)
        self.assertIn("openapi_contract", data["features"])
        self.assertIn("api_docs", data["features"])
        self.assertEqual(data["endpoints"]["openapi"], endpoints["openapi"])
        self.assertEqual(data["endpoints"]["docs"], endpoints["docs"])
        self.assertEqual(data["endpoints"]["integration_bundle"], endpoints["integration_bundle"])
        self.assertEqual(data["legacy_endpoints"], {})
        self.assertEqual(data["compatibility"]["canonical_prefix"], "/api/v1/external")
        self.assertEqual(data["compatibility"]["legacy_prefix"], "/api/external")
        self.assertFalse(data["compatibility"]["legacy_supported"])
        self.assertEqual(data["compatibility"]["aliases"], {})
        self.assertEqual(data["compatibility"]["removed_legacy_prefix"], "/api/external")
        self.assertIn("mailbox_directory", data["features"])
        self.assertIn("provider_preflight", data["features"])
        self.assertEqual(data["integration_bundle"]["endpoint"], endpoints["integration_bundle"])
        self.assertEqual(data["integration_bundle"]["response_contract"], "integration_bundle")
        self.assertEqual(
            data["integration_manifest"]["discovery"]["endpoints"]["integration_bundle"], endpoints["integration_bundle"]
        )
        self.assertEqual(data["endpoints"]["mailboxes"], endpoints["mailboxes"])
        self.assertEqual(data["endpoints"]["providers"], endpoints["providers"])
        self.assertEqual(data["endpoints"]["provider_preflight"], endpoints["provider_preflight"])
        self.assertEqual(data["mailbox_directory"]["endpoint"], endpoints["mailboxes"])
        self.assertIn("provider", data["mailbox_directory"]["query_fields"])
        self.assertIn("sort", data["mailbox_directory"]["query_fields"])
        self.assertIn("read_capability", data["mailbox_directory"]["query_fields"])
        self.assertIn("action", data["mailbox_directory"]["query_fields"])
        self.assertEqual(data["mailbox_directory"]["response_contract"], "unified_mailbox_directory")
        self.assertEqual(data["mailbox_directory"]["contract"]["filters"]["kind"], expected_contract["filters"]["kind"])
        self.assertEqual(data["mailbox_directory"]["contract"]["filters"]["status"], expected_contract["filters"]["status"])
        self.assertEqual(
            data["mailbox_directory"]["contract"]["filters"]["read_capability"],
            expected_contract["filters"]["read_capability"],
        )
        self.assertEqual(data["mailbox_directory"]["contract"]["filters"]["action"], expected_contract["filters"]["action"])
        self.assertEqual(data["mailbox_directory"]["contract"]["filters"]["sort"], expected_contract["filters"]["sort"])
        self.assertEqual(
            [item["kind"] for item in data["mailbox_directory"]["kind_definitions"]],
            [item["kind"] for item in expected_contract["kind_definitions"]],
        )
        self.assertEqual(
            [item["status"] for item in data["mailbox_directory"]["status_definitions"]],
            [item["status"] for item in expected_contract["status_definitions"]],
        )
        self.assertEqual(
            [item["sort"] for item in data["mailbox_directory"]["sort_definitions"]],
            [item["sort"] for item in expected_contract["sort_definitions"]],
        )
        self.assertEqual(
            [item["read_capability"] for item in data["mailbox_directory"]["read_capability_definitions"]],
            [item["read_capability"] for item in expected_contract["read_capability_definitions"]],
        )
        self.assertEqual(
            [item["action"] for item in data["mailbox_directory"]["action_definitions"]],
            [item["action"] for item in expected_contract["action_definitions"]],
        )
        self.assertEqual(
            [item["key"] for item in data["mailbox_directory"]["summary_fields"]],
            [item["key"] for item in expected_contract["summary_fields"]],
        )
        self.assertEqual(data["mailbox_directory"]["quick_view_presets"], expected_contract["quick_view_presets"])
        self.assertEqual(
            data["mailbox_directory"]["contract"]["quick_view_presets"],
            expected_contract["quick_view_presets"],
        )
        quick_view_by_key = {item["key"]: item for item in data["mailbox_directory"]["quick_view_presets"]}
        self.assertEqual(quick_view_by_key["readable"]["filters"]["action"], "read_messages")
        self.assertEqual(quick_view_by_key["attention"]["filters"]["status"], "inactive")
        self.assertNotRegex(str(data["mailbox_directory"]["quick_view_presets"]), r"dk_[0-9a-fA-F]{20,}")
        self.assertEqual(data["mailbox_directory"]["provider_context_field"], "provider_context")
        self.assertEqual(data["mailbox_directory"]["item_action_contract_field"], "action_contract")
        self.assertEqual(
            data["mailbox_directory"]["item_action_contract_source"],
            "provider_catalog.external_mailbox_read_contract",
        )
        self.assertEqual(data["pool"]["claim_endpoint"], endpoints["pool_claim_random"])
        self.assertEqual(data["task_temp_mailbox"]["apply_endpoint"], endpoints["temp_mail_apply"])
        self._assert_provider_documentation_contract(data["documentation"])
        guide = data["provider_integration_guide"]
        self.assertEqual(guide["version"], 1)
        self.assertEqual(guide["documentation"], data["documentation"])
        self.assertEqual(guide["endpoints"]["capabilities"], endpoints["capabilities"])
        self.assertEqual(guide["endpoints"]["provider_preflight"], endpoints["provider_preflight"])
        self.assertEqual(guide["workflow"]["discover_providers"]["response_field"], "provider_integration_guide")
        self.assertEqual(guide["workflow"]["preflight_providers"]["endpoint"], endpoints["provider_preflight"])
        self.assertEqual(guide["workflow"]["preflight_providers"]["response_field"], "data")
        self.assertEqual(guide["workflow"]["list_unified_mailboxes"]["provider_context_field"], "provider_context")
        self.assertIn("imap", guide["aliases"]["pool_claim_provider_aliases"])
        guide_providers = {item["provider"]: item for item in guide["providers"]}
        self.assertEqual(guide_providers["duckmail"]["required_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(guide_providers["duckmail"]["pool_claim_request"]["value"], "duckmail")
        self.assertEqual(guide_providers["duckmail"]["task_temp_apply_request"]["value"], "duckmail")
        self.assertEqual(
            guide_providers["mail_tm"]["configuration"]["env_defaults"], {"MAILTM_API_BASE": "https://api.mail.tm"}
        )
        self.assertEqual(guide_providers["legacy_bridge"]["label"], "Compatible Temp Mail Bridge")
        self.assertEqual(
            guide_providers["legacy_bridge"]["aliases"]["pool_claim_provider"], ["gptmail", "legacy_gptmail", "temp_mail"]
        )
        for container in (data["deployment_profile"], data["selection_policy"], guide):
            self.assertIn("selection_recipes", container)
            self.assertIn("selection_recipe_index", container)
        recipe_index = data["selection_policy"]["selection_recipe_index"]
        self.assertNotIn("active_allowlist:auto", recipe_index)
        for provider in ("duckmail", "mail_tm", "legacy_bridge"):
            self.assertIn(f"active_allowlist:{provider}", recipe_index)
            self.assertIn(f"explicit_pool_claim:{provider}", recipe_index)
            self.assertIn(f"task_temp_apply:{provider}", recipe_index)
        duckmail_active_recipe = recipe_index["active_allowlist:duckmail"]
        self.assertEqual(duckmail_active_recipe["configuration"]["env"], {"ACTIVE_MAILBOX_PROVIDERS": "duckmail"})
        self.assertEqual(
            duckmail_active_recipe["configuration"]["provider_config"]["object"],
            {"providers": {"active_mailbox_providers": ["duckmail"]}},
        )
        self.assertIn('"active_mailbox_providers"', duckmail_active_recipe["configuration"]["provider_config"]["json"])
        self.assertIn(
            'active_mailbox_providers = ["duckmail"]', duckmail_active_recipe["configuration"]["provider_config"]["toml"]
        )
        duckmail_recipe_env = {item["key"]: item for item in recipe_index["explicit_pool_claim:duckmail"]["provider_env"]}
        self.assertEqual(duckmail_recipe_env["DUCKMAIL_BEARER_TOKEN"]["value"], "")
        self.assertTrue(duckmail_recipe_env["DUCKMAIL_BEARER_TOKEN"]["secret"])
        self.assertEqual(duckmail_recipe_env["DUCKMAIL_API_BASE"]["default"], "https://api.duckmail.sbs")
        gptmail_recipe_env = {item["key"]: item for item in recipe_index["explicit_pool_claim:gptmail"]["provider_env"]}
        self.assertEqual(gptmail_recipe_env["GPTMAIL_API_KEY"]["value"], "")
        self.assertTrue(gptmail_recipe_env["GPTMAIL_API_KEY"]["secret"])
        self.assertEqual(gptmail_recipe_env["GPTMAIL_BASE_URL"]["default"], "https://mail.chatgpt.org.uk")
        self.assertEqual(recipe_index["explicit_pool_claim:duckmail"]["request"]["body"], {"provider": "duckmail"})
        self.assertEqual(recipe_index["task_temp_apply:duckmail"]["request"]["body"], {"provider_name": "duckmail"})
        self.assertNotRegex(str(guide), r"dk_[0-9a-fA-F]{20,}")
        manifest = data["integration_manifest"]
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["documentation"], data["documentation"])
        self.assertEqual(manifest["auth"]["header"], "X-API-Key")
        self.assertEqual(manifest["auth"]["placeholder"], "<your-api-key>")
        self.assertEqual(manifest["auth"]["curl_header"], "X-API-Key: <your-api-key>")
        self.assertEqual(manifest["discovery"]["recommended_sequence"][0]["endpoint"], endpoints["capabilities"])
        self.assertEqual(manifest["discovery"]["recommended_sequence"][1]["endpoint"], endpoints["providers"])
        self.assertEqual(manifest["discovery"]["recommended_sequence"][2]["query"], {"kind": "all", "provider": "all"})
        self.assertEqual(manifest["discovery"]["endpoints"]["openapi"], endpoints["openapi"])
        self.assertEqual(manifest["discovery"]["endpoints"]["docs"], endpoints["docs"])
        self.assertEqual(manifest["discovery"]["endpoints"]["integration_bundle"], endpoints["integration_bundle"])
        self.assertEqual(manifest["discovery"]["endpoints"]["provider_preflight"], endpoints["provider_preflight"])
        self.assertEqual(manifest["discovery"]["endpoints"]["mailboxes"], endpoints["mailboxes"])
        self.assertEqual(manifest["selection"]["source_priority"], ["env", "provider_config_file", "settings", "default"])
        self.assertEqual(manifest["selection"]["explicit_pool_claim"]["request_field"], "provider")
        self.assertEqual(manifest["selection"]["task_temp_apply"]["request_field"], "provider_name")
        self.assertEqual(manifest["selection_recipes"], data["selection_policy"]["selection_recipes"])
        self.assertEqual(manifest["selection_recipe_index"], data["selection_policy"]["selection_recipe_index"])
        self.assertEqual(manifest["selection"]["recipes"], manifest["selection_recipes"])
        self.assertEqual(manifest["selection"]["recipe_index"], manifest["selection_recipe_index"])
        self.assertEqual(manifest["deployment"]["selection_recipes"], manifest["selection_recipes"])
        self.assertEqual(manifest["deployment"]["selection_recipe_index"], manifest["selection_recipe_index"])
        self.assertFalse(manifest["secret_policy"]["exposes_secret_values"])
        self._assert_external_quickstart_contract(data)
        workflows = {item["key"]: item for item in manifest["workflows"]}
        self.assertEqual(
            list(workflows.keys()),
            [
                "start_mailbox_session",
                "discover_external_api",
                "browse_mailbox_directory",
                "claim_pool_mailbox",
                "create_task_temp_mailbox",
            ],
        )
        session_steps = {item["key"]: item for item in workflows["start_mailbox_session"]["steps"]}
        self.assertEqual(session_steps["start_session"]["endpoint"], endpoints["mailbox_session_start"])
        self.assertEqual(session_steps["start_session"]["request"]["required_body_fields"], ["caller_id", "task_id"])
        self.assertEqual(
            session_steps["start_session"]["request"]["source_strategy_values"],
            ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
        )
        self.assertEqual(session_steps["read_session"]["endpoint"], endpoints["mailbox_session_read"])
        self.assertEqual(session_steps["read_session"]["next"], {"success": "close_session"})
        self.assertEqual(session_steps["close_session"]["endpoint"], endpoints["mailbox_session_close"])
        self.assertEqual(
            session_steps["close_session"]["request"]["body_fields"],
            ["session_type", "account_id", "claim_token", "task_token", "caller_id", "task_id", "result", "detail", "reason"],
        )
        claim_steps = {item["key"]: item for item in workflows["claim_pool_mailbox"]["steps"]}
        self.assertEqual(claim_steps["claim_random"]["endpoint"], endpoints["pool_claim_random"])
        self.assertEqual(claim_steps["claim_random"]["request"]["provider_selector"]["field"], "provider")
        self.assertEqual(
            claim_steps["claim_random"]["request"]["provider_selector"]["allowed_values"],
            manifest["selection"]["explicit_pool_claim"]["allowed_values"],
        )
        self.assertEqual(claim_steps["read_messages"]["endpoint"], endpoints["messages"])
        self.assertEqual(claim_steps["read_verification_code"]["endpoint"], endpoints["verification_code"])
        self.assertEqual(claim_steps["complete_claim"]["endpoint"], endpoints["pool_claim_complete"])
        self.assertEqual(claim_steps["release_claim"]["endpoint"], endpoints["pool_claim_release"])
        task_steps = {item["key"]: item for item in workflows["create_task_temp_mailbox"]["steps"]}
        self.assertEqual(task_steps["apply_task_mailbox"]["endpoint"], endpoints["temp_mail_apply"])
        self.assertEqual(task_steps["apply_task_mailbox"]["request"]["provider_selector"]["field"], "provider_name")
        self.assertEqual(
            task_steps["apply_task_mailbox"]["request"]["provider_selector"]["allowed_values"],
            manifest["selection"]["task_temp_apply"]["allowed_values"],
        )
        self.assertEqual(task_steps["finish_task_mailbox"]["endpoint"], endpoints["temp_mail_finish"])
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", json.dumps(manifest["workflows"], ensure_ascii=False))
        manifest_providers = {item["provider"]: item for item in manifest["providers"]}
        duckmail_manifest = manifest_providers["duckmail"]
        duckmail_env = {item["key"]: item for item in duckmail_manifest["env"]}
        self.assertEqual(duckmail_env["DUCKMAIL_BEARER_TOKEN"]["value"], "")
        self.assertTrue(duckmail_env["DUCKMAIL_BEARER_TOKEN"]["secret"])
        self.assertTrue(duckmail_env["DUCKMAIL_BEARER_TOKEN"]["required"])
        self.assertEqual(duckmail_env["DUCKMAIL_API_BASE"]["default"], "https://api.duckmail.sbs")
        self.assertEqual(duckmail_manifest["request_fields"]["pool_claim"]["request_field"], "provider")
        self.assertEqual(duckmail_manifest["request_fields"]["task_temp_apply"]["request_field"], "provider_name")
        mailtm_env = {item["key"]: item for item in manifest_providers["mail_tm"]["env"]}
        self.assertEqual(mailtm_env["MAILTM_API_BASE"]["default"], "https://api.mail.tm")
        self.assertEqual(manifest_providers["legacy_bridge"]["label"], "Compatible Temp Mail Bridge")
        self.assertEqual(
            manifest_providers["legacy_bridge"]["aliases"]["pool_claim_provider"], ["gptmail", "legacy_gptmail", "temp_mail"]
        )
        self.assertNotRegex(json.dumps(manifest, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")
        contract = data["external_mailbox_read_contract"]
        self.assertIn("claim_token", contract["read_by"])
        self.assertEqual(contract["next_actions"]["read_messages"]["endpoint"], endpoints["messages"])

    def test_capabilities_integration_manifest_does_not_echo_provider_secret_values(self):
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        with patch.dict(
            "os.environ",
            {
                "DUCKMAIL_BEARER_TOKEN": "duck-secret-for-manifest-test",
                "EMAILNATOR_API_KEY": "emailnator-secret-for-manifest-test",
                "GPTMAIL_API_KEY": "gptmail-secret-for-manifest-test",
            },
            clear=False,
        ):
            resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        payload_text = json.dumps(resp.get_json(), ensure_ascii=False)
        self.assertIn("DUCKMAIL_BEARER_TOKEN", payload_text)
        self.assertNotIn("duck-secret-for-manifest-test", payload_text)
        self.assertNotIn("emailnator-secret-for-manifest-test", payload_text)
        self.assertNotIn("gptmail-secret-for-manifest-test", payload_text)
        self.assertNotRegex(payload_text, r"dk_[0-9a-fA-F]{20,}")
        manifest = resp.get_json()["data"]["integration_manifest"]
        duckmail_manifest = {item["provider"]: item for item in manifest["providers"]}["duckmail"]
        duckmail_env = {item["key"]: item for item in duckmail_manifest["env"]}
        self.assertEqual(duckmail_env["DUCKMAIL_BEARER_TOKEN"]["value"], "")
        duckmail_recipe = manifest["selection_recipe_index"]["explicit_pool_claim:duckmail"]
        duckmail_recipe_env = {item["key"]: item for item in duckmail_recipe["provider_env"]}
        self.assertEqual(duckmail_recipe_env["DUCKMAIL_BEARER_TOKEN"]["value"], "")
        self.assertTrue(duckmail_recipe_env["DUCKMAIL_BEARER_TOKEN"]["secret"])
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", json.dumps(manifest["workflows"], ensure_ascii=False))

    def test_integration_manifest_workflows_derive_provider_selectors_from_policy(self):
        from outlook_web.services import provider_catalog

        endpoints = self._canonical_external_endpoints()
        selection_policy = {
            "source_priority": ["env", "provider_config_file", "settings", "default"],
            "scopes": {
                "active_allowlist": {
                    "settings_key": "active_mailbox_providers",
                    "allowed_values": ["future_pool_provider", "future_temp_provider"],
                },
                "pool_claim_default": {
                    "request_field": "provider",
                    "settings_key": "pool_default_provider",
                    "allowed_values": ["auto", "future_pool_provider"],
                },
                "explicit_pool_claim": {
                    "request_field": "provider",
                    "endpoint": "/api/v1/external/pool/claim-random",
                    "allowed_values": ["auto", "future_pool_provider"],
                },
                "temp_runtime_default": {
                    "request_field": "provider_name",
                    "settings_key": "temp_mail_provider",
                    "allowed_values": ["future_temp_provider"],
                },
                "task_temp_apply": {
                    "request_field": "provider_name",
                    "endpoint": "/api/v1/external/temp-emails/apply",
                    "allowed_values": ["future_temp_provider"],
                },
            },
        }
        deployment_profile = {
            "templates": {},
            "aliases": {},
            "provider_values": {
                "active_allowlist": ["future_pool_provider", "future_temp_provider"],
                "pool_claim": ["auto", "future_pool_provider"],
                "temp_runtime": ["future_temp_provider"],
                "temp_apply": ["future_temp_provider"],
            },
            "provider_examples": {
                "future_pool_provider": {"label": "Future Pool", "kind": "account", "active": True},
                "future_temp_provider": {"label": "Future Temp", "kind": "temp", "active": True},
            },
        }
        provider_integration_guide = {
            "secret_policy": {"exposes_secret_values": False},
            "aliases": {},
            "providers": [
                {
                    "provider": "future_pool_provider",
                    "label": "Future Pool",
                    "kind": "account",
                    "active": True,
                    "configuration": {
                        "required_env": ["FUTURE_POOL_SECRET"],
                        "optional_env": ["FUTURE_POOL_BASE"],
                        "secret_env": ["FUTURE_POOL_SECRET"],
                        "env_defaults": {"FUTURE_POOL_BASE": "https://future.pool.test"},
                    },
                },
                {
                    "provider": "future_temp_provider",
                    "label": "Future Temp",
                    "kind": "temp",
                    "active": True,
                    "configuration": {
                        "optional_env": ["FUTURE_TEMP_BASE"],
                        "secret_env": [],
                        "env_defaults": {"FUTURE_TEMP_BASE": "https://future.temp.test"},
                    },
                },
            ],
        }
        manifest = provider_catalog.get_external_integration_manifest(
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_filter={},
            provider_diagnostics={"summary": {}},
            provider_integration_guide=provider_integration_guide,
            endpoints=endpoints,
        )

        workflows = {item["key"]: item for item in manifest["workflows"]}
        session_steps = {item["key"]: item for item in workflows["start_mailbox_session"]["steps"]}
        self.assertEqual(session_steps["start_session"]["endpoint"], endpoints["mailbox_session_start"])
        self.assertEqual(
            session_steps["start_session"]["request"]["source_strategy_values"],
            ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
        )
        self.assertEqual(session_steps["read_session"]["endpoint"], endpoints["mailbox_session_read"])
        self.assertEqual(session_steps["close_session"]["endpoint"], endpoints["mailbox_session_close"])
        claim_steps = {item["key"]: item for item in workflows["claim_pool_mailbox"]["steps"]}
        self.assertEqual(claim_steps["claim_random"]["endpoint"], endpoints["pool_claim_random"])
        self.assertEqual(claim_steps["read_messages"]["endpoint"], endpoints["messages"])
        self.assertEqual(claim_steps["release_claim"]["endpoint"], endpoints["pool_claim_release"])
        self.assertEqual(
            claim_steps["claim_random"]["request"]["provider_selector"]["allowed_values"],
            ["auto", "future_pool_provider"],
        )
        task_steps = {item["key"]: item for item in workflows["create_task_temp_mailbox"]["steps"]}
        self.assertEqual(task_steps["apply_task_mailbox"]["endpoint"], endpoints["temp_mail_apply"])
        self.assertEqual(task_steps["finish_task_mailbox"]["endpoint"], endpoints["temp_mail_finish"])
        self.assertEqual(
            task_steps["apply_task_mailbox"]["request"]["provider_selector"]["allowed_values"],
            ["future_temp_provider"],
        )
        recipe_index = manifest["selection_recipe_index"]
        self.assertIn("active_allowlist:future_pool_provider", recipe_index)
        self.assertIn("pool_claim_default:future_pool_provider", recipe_index)
        self.assertIn("explicit_pool_claim:future_pool_provider", recipe_index)
        self.assertIn("task_temp_apply:future_temp_provider", recipe_index)
        future_pool_env = {
            item["key"]: item for item in recipe_index["explicit_pool_claim:future_pool_provider"]["provider_env"]
        }
        self.assertEqual(future_pool_env["FUTURE_POOL_SECRET"]["value"], "")
        self.assertTrue(future_pool_env["FUTURE_POOL_SECRET"]["secret"])
        self.assertEqual(future_pool_env["FUTURE_POOL_BASE"]["default"], "https://future.pool.test")
        self.assertEqual(
            recipe_index["explicit_pool_claim:future_pool_provider"]["request"]["body"], {"provider": "future_pool_provider"}
        )
        self.assertEqual(
            recipe_index["task_temp_apply:future_temp_provider"]["request"]["body"], {"provider_name": "future_temp_provider"}
        )
        self.assertEqual(manifest["selection"]["recipe_index"], recipe_index)
        self.assertEqual(manifest["deployment"]["selection_recipe_index"], recipe_index)
        workflow_builder_source = inspect.getsource(provider_catalog._integration_manifest_workflows)
        recipe_builder_source = inspect.getsource(provider_catalog._provider_selection_recipe_bundle)
        for provider_name in ("duckmail", "mail_tm", "gptmail", "tempmail_lol", "emailnator"):
            self.assertNotIn(provider_name, workflow_builder_source.lower())
            self.assertNotIn(provider_name, recipe_builder_source.lower())

    def test_capabilities_exposes_pool_and_task_mailbox_discovery_contract(self):
        endpoints = self._canonical_external_endpoints()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")

        client = self.app.test_client()
        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertIn("openapi_contract", data.get("features", []))
        self.assertIn("mailbox_directory", data.get("features", []))
        self.assertIn("provider_discovery", data.get("features", []))
        self.assertIn("pool_claim_random", data.get("features", []))
        self.assertIn("task_temp_mailbox_apply", data.get("features", []))
        self.assertIn("mailbox_session_start", data.get("features", []))
        self.assertIn("mailbox_session_close", data.get("features", []))
        self.assertEqual(data["mailbox_session"]["start_endpoint"], endpoints["mailbox_session_start"])
        self.assertEqual(data["mailbox_session"]["close_endpoint"], endpoints["mailbox_session_close"])
        self.assertEqual(
            data["mailbox_session"]["source_strategy_values"], ["pool_first", "task_temp_first", "pool_only", "task_temp_only"]
        )
        self.assertTrue(data["pool"]["external_enabled"])
        self.assertTrue(data["pool"]["current_consumer_has_access"])
        self.assertEqual(data["pool"]["release_endpoint"], endpoints["pool_claim_release"])
        self.assertEqual(data["pool"]["complete_endpoint"], endpoints["pool_claim_complete"])
        self.assertEqual(data["pool"]["stats_endpoint"], endpoints["pool_stats"])
        self.assertEqual(data["task_temp_mailbox"]["finish_endpoint"], endpoints["temp_mail_finish"])
        self.assertEqual(
            data["pool"]["read_contract"]["next_actions"]["release_claim"]["endpoint"], endpoints["pool_claim_release"]
        )
        self.assertEqual(
            data["task_temp_mailbox"]["read_contract"]["next_actions"]["finish_task_mailbox"]["endpoint"],
            endpoints["temp_mail_finish"],
        )

    def test_capabilities_reports_missing_provider_config_file_without_failing_discovery(self):
        self._set_external_api_key("abc123")
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
                resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        selection_config = data["selection_policy"]["config_file"]
        defaults = data["provider_diagnostics"]["defaults"]

        # Operator-facing default projects bridge dual-register keys to legacy_bridge
        # so it remains present in the collapsed integration guide.
        self.assertEqual(data["defaults"]["temp_mail_provider"], "legacy_bridge")
        self.assertEqual(defaults["temp_mail_provider"]["raw_provider"], "custom_domain_temp_mail")
        self.assertEqual(defaults["temp_mail_provider"]["canonical_provider"], "legacy_bridge")
        self.assertEqual(selection_config["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertFalse(selection_config["loaded"])
        self.assertEqual(data["provider_filter"]["source"], "config_file_error")
        self.assertEqual(defaults["temp_mail_provider"]["config_error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")

    def test_capabilities_marks_pool_restricted_for_multi_key_without_pool_access(self):
        self._create_external_api_key("partner-a", "multi-no-pool", pool_access=False)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")

        client = self.app.test_client()
        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers("multi-no-pool"))

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertFalse(data["pool"]["current_consumer_has_access"])
        self.assertIn("pool_access_required", data["pool"].get("restrictions", []))
        self.assertIn("pool_access_required", data.get("restricted_features", []))
        self.assertNotIn("pool_claim_random", data.get("features", []))

    def test_integration_bundle_response_schema_and_legacy_alias(self):
        self._set_external_api_key("abc123")
        endpoints = self._canonical_external_endpoints()
        client = self.app.test_client()

        unauth = client.get(endpoints["integration_bundle"])
        self.assertEqual(unauth.status_code, 401)

        versioned = client.get(endpoints["integration_bundle"], headers=self._auth_headers())
        legacy = client.get("/api/external/integration-bundle", headers=self._auth_headers())

        self.assertEqual(versioned.status_code, 200)
        self.assertEqual(legacy.status_code, 404)
        data = versioned.get_json().get("data", {})
        for key in (
            "version",
            "service",
            "app_version",
            "status",
            "generated_at",
            "auth",
            "endpoints",
            "legacy_endpoints",
            "compatibility",
            "documentation",
            "quickstart",
            "readiness",
            "provider_selection",
            "openapi",
            "workflows",
            "smoke_checks",
            "recommendations",
            "action_plan",
        ):
            self.assertIn(key, data, f"IntegrationBundleData 缺少字段: {key}")
        self.assertEqual(data["version"], 1)
        self.assertIn(data["status"], {"ready", "needs_config", "degraded"})
        self.assertEqual(data["auth"], {"header": "X-API-Key", "placeholder": "<your-api-key>"})
        self.assertEqual(data["endpoints"]["integration_bundle"], endpoints["integration_bundle"])
        self.assertEqual(data["legacy_endpoints"], {})
        self.assertEqual(data["compatibility"]["aliases"], {})
        self.assertEqual(data["quickstart"]["endpoints"]["integration_bundle"], endpoints["integration_bundle"])
        self.assertEqual(
            data["readiness"]["external_api"]["discovery"]["next_endpoints"]["integration_bundle"],
            endpoints["integration_bundle"],
        )
        self.assertEqual(data["readiness"]["providers"]["version"], 1)
        self._assert_provider_capability_matrix_contract(data["readiness"]["providers"]["capability_matrix"])
        self.assertEqual(data["provider_selection"]["selector_fields"]["pool_claim"], "provider")
        self.assertEqual(data["provider_selection"]["selector_fields"]["task_temp_apply"], "provider_name")
        self.assertEqual(data["openapi"]["endpoint"], endpoints["openapi"])
        self.assertGreater(data["openapi"]["path_count"], 0)
        self.assertGreater(data["openapi"]["schema_count"], 0)
        self.assertGreater(data["openapi"]["operation_count"], 0)
        smoke_keys = {item["key"] for item in data["smoke_checks"]}
        self.assertIn("integration_bundle", smoke_keys)
        recommendation_keys = {item["key"] for item in data["recommendations"]}
        self.assertIn("generate_client", recommendation_keys)
        action_plan = data["action_plan"]
        self.assertEqual(action_plan["version"], 1)
        self.assertEqual(action_plan["status"], data["status"])
        self.assertEqual(action_plan["summary"]["total"], len(action_plan["items"]))
        self.assertGreaterEqual(action_plan["summary"]["high"], 1)
        action_items = {item["key"]: item for item in action_plan["items"]}
        self.assertIn("run_smoke_check", action_items)
        self.assertIn("generate_client", action_items)
        self.assertIn("start_mailbox_session", action_items)
        self.assertEqual(action_items["run_smoke_check"]["priority"], "high")
        self.assertEqual(action_items["run_smoke_check"]["status"], "ready")
        self.assertFalse(action_items["run_smoke_check"]["blocking"])
        self.assertEqual(action_items["run_smoke_check"]["endpoint"], endpoints["integration_bundle"])
        self.assertEqual(
            action_items["run_smoke_check"]["command"],
            "MAILOPS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
        )
        self.assertEqual(action_items["generate_client"]["endpoint"], endpoints["openapi"])
        self.assertEqual(action_items["start_mailbox_session"]["endpoint"], endpoints["mailbox_session_start"])
        for item in action_plan["items"]:
            self.assertIn(item["priority"], {"high", "medium", "low"})
            self.assertIn(item["status"], {"ready", "action_required", "optional", "blocked"})
            self.assertIsInstance(item["blocking"], bool)
            self.assertTrue(item.get("endpoint") or item.get("command") or item.get("docs"))
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("abc123", serialized)
        self.assertNotRegex(serialized, r"dk_[0-9a-fA-F]{20,}")
        self.assertNotRegex(serialized, r"Bearer\s+[A-Za-z0-9_.-]+")
        self.assertNotIn("consumer_key=", serialized.lower())
        self.assertNotIn("refresh_token=", serialized.lower())

    def test_external_provider_discovery_exposes_capability_matrix_on_canonical_and_legacy_routes(self):
        endpoints = self._canonical_external_endpoints()
        legacy_endpoints = self._legacy_external_endpoints()
        client = self.app.test_client()
        self._set_external_api_key("abc123")

        versioned = client.get(endpoints["providers"], headers=self._auth_headers())
        legacy = client.get("/api/external/providers", headers=self._auth_headers())

        self.assertEqual(versioned.status_code, 200)
        self.assertEqual(legacy.status_code, 404)
        data = versioned.get_json().get("data", {})
        matrix = data["readiness_summary"]["capability_matrix"]
        self._assert_provider_capability_matrix_contract(matrix)

    def test_integration_bundle_action_plan_prioritizes_blocking_provider_config(self):
        self._set_external_api_key("abc123")
        endpoints = self._canonical_external_endpoints()
        client = self.app.test_client()

        needs_config_readiness = {
            "version": 1,
            "overall_status": "needs_config",
            "totals": {"providers": 1, "active_providers": 1, "ready_providers": 0, "needs_config_providers": 1},
            "issues": {
                "needs_config": 1,
                "inactive": 0,
                "unknown_filter_entries": 0,
                "invalid_default_entries": 0,
                "inactive_default_entries": 0,
            },
            "source_priority": ["env", "provider_config_file", "settings", "default"],
            "provider_selector_fields": {"pool_claim": "provider", "task_temp_apply": "provider_name"},
            "routing_matrix": {"version": 1, "source_priority": ["env"], "scopes": {}},
            "endpoints": {"providers": endpoints["providers"]},
            "providers": [],
        }
        with patch(
            "outlook_web.services.provider_catalog.get_mailbox_provider_readiness_summary", return_value=needs_config_readiness
        ):
            resp = client.get(endpoints["integration_bundle"], headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertEqual(data["status"], "needs_config")
        items = data["action_plan"]["items"]
        item_keys = [item["key"] for item in items]
        self.assertIn("configure_providers", item_keys)
        self.assertIn("start_mailbox_session", item_keys)
        self.assertLess(item_keys.index("configure_providers"), item_keys.index("start_mailbox_session"))
        configure = items[item_keys.index("configure_providers")]
        session = items[item_keys.index("start_mailbox_session")]
        self.assertEqual(configure["priority"], "high")
        self.assertEqual(configure["status"], "action_required")
        self.assertTrue(configure["blocking"])
        self.assertEqual(configure["endpoint"], endpoints["providers"])
        self.assertEqual(session["status"], "blocked")
        self.assertEqual(data["action_plan"]["summary"]["blocking"], sum(1 for item in items if item["blocking"]))

    def test_openapi_contract_requires_api_key(self):
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get("/api/v1/external/openapi.json")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")

    def test_openapi_contract_exposes_external_api_paths_and_security(self):
        self._set_external_api_key("abc123")
        from outlook_web.services.mailbox_directory_contract import get_mailbox_catalog_contract

        endpoints = self._canonical_external_endpoints()
        legacy_endpoints = self._legacy_external_endpoints()
        expected_contract = get_mailbox_catalog_contract()
        client = self.app.test_client()

        resp = client.get("/api/v1/external/openapi.json", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("openapi"), "3.1.0")
        self.assertEqual(data.get("info", {}).get("title"), "Outlook Email Plus External API")
        self.assertEqual(data.get("components", {}).get("securitySchemes", {}).get("ApiKeyAuth", {}).get("name"), "X-API-Key")
        self.assertIn({"ApiKeyAuth": []}, data.get("security", []))
        paths = data.get("paths", {})
        for path in (
            endpoints["health"],
            endpoints["capabilities"],
            endpoints["integration_bundle"],
            endpoints["docs"],
            endpoints["openapi"],
            endpoints["mailboxes"],
            endpoints["providers"],
            endpoints["provider_preflight"],
            endpoints["mailbox_session_start"],
            endpoints["mailbox_session_read"],
            endpoints["mailbox_session_close"],
            endpoints["messages"],
            endpoints["latest_message"],
            endpoints["message_detail"],
            endpoints["message_raw"],
            endpoints["verification_code"],
            endpoints["verification_link"],
            endpoints["wait_message"],
            endpoints["probe_status"],
            endpoints["account_status"],
            endpoints["pool_claim_random"],
            endpoints["temp_mail_apply"],
        ):
            self.assertIn(path, paths)
        for legacy_path in legacy_endpoints.values():
            self.assertNotIn(legacy_path, paths)
        self.assertEqual(paths[endpoints["docs"]]["get"]["operationId"], "externalApiDocs")
        self.assertEqual(paths[endpoints["integration_bundle"]]["get"]["operationId"], "externalIntegrationBundle")
        self.assertEqual(paths[endpoints["mailboxes"]]["get"]["operationId"], "externalMailboxes")
        self.assertEqual(paths[endpoints["provider_preflight"]]["get"]["operationId"], "externalProviderPreflight")
        preflight_params = {item["name"]: item for item in paths[endpoints["provider_preflight"]]["get"].get("parameters", [])}
        self.assertEqual(preflight_params["probe_network"]["schema"], {"type": "boolean", "default": False})
        mailbox_params = {item["name"]: item for item in paths[endpoints["mailboxes"]]["get"].get("parameters", [])}
        self.assertEqual(mailbox_params["kind"]["schema"]["enum"], expected_contract["filters"]["kind"])
        self.assertEqual(mailbox_params["status"]["schema"]["enum"], expected_contract["filters"]["status"])
        self.assertEqual(mailbox_params["read_capability"]["schema"]["enum"], expected_contract["filters"]["read_capability"])
        self.assertEqual(mailbox_params["action"]["schema"]["enum"], expected_contract["filters"]["action"])
        self.assertEqual(mailbox_params["action"]["schema"]["default"], "all")
        self.assertEqual(mailbox_params["provider"]["schema"]["default"], "all")
        self.assertEqual(mailbox_params["sort"]["schema"]["default"], "updated_desc")
        self.assertEqual(mailbox_params["sort"]["schema"]["enum"], expected_contract["filters"]["sort"])
        self.assertEqual(mailbox_params["page_size"]["schema"]["maximum"], 200)
        schemas = data.get("components", {}).get("schemas", {})
        self.assertIn("readiness", schemas["HealthData"]["required"])
        self.assertEqual(
            schemas["HealthData"]["properties"]["readiness"]["$ref"],
            "#/components/schemas/ExternalReadinessSummary",
        )
        self.assertEqual(
            schemas["ExternalReadinessSummary"]["required"],
            [
                "status",
                "database",
                "upstream_probe",
                "discovery",
                "providers",
                "mailbox_directory",
                "pool",
                "task_temp_mailbox",
                "warnings",
            ],
        )
        self.assertEqual(
            schemas["ExternalReadinessSummary"]["properties"]["mailbox_directory"]["$ref"],
            "#/components/schemas/ExternalReadinessMailboxDirectory",
        )
        self.assertEqual(
            schemas["ExternalReadinessMailboxDirectory"]["required"],
            ["status", "endpoint", "scoped", "summary", "totals", "quick_probe_params"],
        )
        self.assertEqual(
            schemas["CapabilitiesData"]["required"],
            [
                "service",
                "version",
                "public_mode",
                "features",
                "available_features",
                "restricted_features",
                "defaults",
                "deployment_env",
                "deployment_profile",
                "selection_policy",
                "provider_integration_guide",
                "integration_manifest",
                "integration_bundle",
                "quickstart",
                "documentation",
                "provider_filter",
                "provider_diagnostics",
                "endpoints",
                "mailbox_directory",
                "external_mailbox_read_contract",
                "mailbox_session",
                "pool",
                "task_temp_mailbox",
            ],
        )
        capabilities_properties = schemas["CapabilitiesData"]["properties"]
        self.assertEqual(capabilities_properties["defaults"]["$ref"], "#/components/schemas/ExternalCapabilitiesDefaults")
        self.assertEqual(capabilities_properties["endpoints"]["$ref"], "#/components/schemas/ExternalEndpointMap")
        self.assertEqual(
            capabilities_properties["mailbox_directory"]["$ref"], "#/components/schemas/MailboxDirectoryDiscovery"
        )
        self.assertEqual(capabilities_properties["mailbox_session"]["$ref"], "#/components/schemas/MailboxSessionDiscovery")
        self.assertEqual(
            capabilities_properties["deployment_profile"]["$ref"], "#/components/schemas/ProviderDeploymentProfile"
        )
        self.assertEqual(capabilities_properties["selection_policy"]["$ref"], "#/components/schemas/ProviderSelectionPolicy")
        self.assertEqual(
            capabilities_properties["provider_integration_guide"]["$ref"], "#/components/schemas/ProviderIntegrationGuide"
        )
        self.assertEqual(capabilities_properties["integration_manifest"]["$ref"], "#/components/schemas/IntegrationManifest")
        self.assertEqual(
            capabilities_properties["integration_bundle"]["$ref"], "#/components/schemas/IntegrationBundleDiscovery"
        )
        self.assertEqual(capabilities_properties["quickstart"]["$ref"], "#/components/schemas/IntegrationQuickstart")
        self.assertEqual(capabilities_properties["documentation"]["$ref"], "#/components/schemas/ProviderDocumentation")
        self.assertEqual(capabilities_properties["pool"]["$ref"], "#/components/schemas/PoolDiscovery")
        self.assertEqual(capabilities_properties["task_temp_mailbox"]["$ref"], "#/components/schemas/TaskTempMailboxDiscovery")
        self.assertIn("ProviderDocumentation", schemas)
        self.assertIn("ProviderDocumentationEntry", schemas)
        self.assertEqual(
            schemas["ProviderDocumentation"]["required"],
            ["version", "recommended_human_start", "recommended_machine_start", "entries"],
        )
        self.assertEqual(
            schemas["ProviderDocumentation"]["properties"]["entries"]["additionalProperties"]["$ref"],
            "#/components/schemas/ProviderDocumentationEntry",
        )
        self.assertEqual(
            schemas["ProviderDocumentationEntry"]["properties"]["type"]["enum"],
            ["guide", "agent_prompt", "example", "api_contract", "api_docs"],
        )
        self.assertIn("mailboxes", schemas["ExternalEndpointMap"]["required"])
        self.assertIn("docs", schemas["ExternalEndpointMap"]["required"])
        self.assertIn("integration_bundle", schemas["ExternalEndpointMap"]["required"])
        self.assertIn("provider_preflight", schemas["ExternalEndpointMap"]["required"])
        self.assertEqual(schemas["ExternalEndpointMap"]["properties"]["docs"]["example"], endpoints["docs"])
        self.assertEqual(
            schemas["ExternalEndpointMap"]["properties"]["integration_bundle"]["example"], endpoints["integration_bundle"]
        )
        self.assertEqual(schemas["ExternalEndpointMap"]["properties"]["mailboxes"]["example"], endpoints["mailboxes"])
        self.assertEqual(
            schemas["ExternalEndpointMap"]["properties"]["provider_preflight"]["example"], endpoints["provider_preflight"]
        )
        self.assertEqual(
            schemas["ExternalCapabilitiesDefaults"]["required"],
            [
                "pool_claim_provider",
                "pool_claim_provider_env",
                "temp_mail_provider",
                "temp_mail_provider_env",
                "active_mailbox_providers",
                "active_mailbox_provider_env",
            ],
        )
        self.assertEqual(
            schemas["ProviderSelectionPolicy"]["properties"]["source_priority"]["items"]["enum"],
            ["env", "provider_config_file", "settings", "default"],
        )
        self.assertEqual(
            schemas["ProviderSelectionPolicy"]["properties"]["selection_recipes"]["items"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        self.assertEqual(
            schemas["ProviderSelectionPolicy"]["properties"]["selection_recipe_index"]["additionalProperties"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        self.assertIn("ProviderDeploymentProfile", schemas)
        self.assertIn("ProviderDeploymentConfigFile", schemas)
        deployment_profile_schema = schemas["ProviderDeploymentProfile"]
        self.assertIn("selection_recipes", deployment_profile_schema["required"])
        self.assertEqual(
            deployment_profile_schema["properties"]["selection_recipes"]["items"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        self.assertEqual(
            deployment_profile_schema["properties"]["config_file"]["$ref"],
            "#/components/schemas/ProviderDeploymentConfigFile",
        )
        provider_config_schema = schemas["ProviderSelectionConfigFile"]
        for key in (
            "enabled",
            "env",
            "formats",
            "path",
            "resolved_path",
            "loaded",
            "error_code",
            "error",
            "priority_slot",
            "diagnostic_source",
        ):
            self.assertIn(key, provider_config_schema["required"])
            self.assertIn(key, provider_config_schema["properties"])
        self.assertIn("supported_sections", provider_config_schema["properties"])
        self.assertIn("sections", provider_config_schema["properties"])
        self.assertIn("ProviderIntegrationGuide", schemas)
        self.assertIn("ProviderIntegrationGuideProvider", schemas)
        self.assertIn("IntegrationManifest", schemas)
        self.assertIn("IntegrationManifestProvider", schemas)
        self.assertIn("IntegrationManifestKeyHint", schemas)
        self.assertIn("ProviderSelectionRecipe", schemas)
        self.assertIn("ProviderSelectionRecipeConfig", schemas)
        self.assertIn("ProviderSelectionRecipeProviderConfig", schemas)
        self.assertIn("ProviderSelectionRecipeRequest", schemas)
        recipe_schema = schemas["ProviderSelectionRecipe"]
        self.assertEqual(
            recipe_schema["properties"]["scope"]["enum"],
            ["active_allowlist", "temp_runtime_default", "pool_claim_default", "explicit_pool_claim", "task_temp_apply"],
        )
        self.assertEqual(
            recipe_schema["properties"]["provider_env"]["items"]["$ref"], "#/components/schemas/IntegrationManifestKeyHint"
        )
        self.assertEqual(
            recipe_schema["properties"]["configuration"]["$ref"], "#/components/schemas/ProviderSelectionRecipeConfig"
        )
        self.assertEqual(recipe_schema["properties"]["request"]["$ref"], "#/components/schemas/ProviderSelectionRecipeRequest")
        self.assertEqual(
            schemas["ProviderSelectionRecipeConfig"]["properties"]["provider_config"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipeProviderConfig",
        )
        self.assertEqual(schemas["ProviderSelectionRecipeProviderConfig"]["required"], ["object", "json", "toml"])
        integration_manifest_schema = schemas["IntegrationManifest"]
        self.assertIn("auth", integration_manifest_schema["required"])
        self.assertIn("workflows", integration_manifest_schema["required"])
        self.assertIn("providers", integration_manifest_schema["required"])
        self.assertIn("documentation", integration_manifest_schema["required"])
        self.assertIn("quickstart", integration_manifest_schema["required"])
        self.assertIn("selection_recipes", integration_manifest_schema["required"])
        self.assertEqual(
            integration_manifest_schema["properties"]["auth"]["$ref"], "#/components/schemas/IntegrationManifestAuth"
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["quickstart"]["$ref"], "#/components/schemas/IntegrationQuickstart"
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["selection"]["$ref"], "#/components/schemas/IntegrationManifestSelection"
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["deployment"]["$ref"],
            "#/components/schemas/IntegrationManifestDeployment",
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["documentation"]["$ref"], "#/components/schemas/ProviderDocumentation"
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["workflows"]["items"]["$ref"],
            "#/components/schemas/IntegrationManifestWorkflow",
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["providers"]["items"]["$ref"],
            "#/components/schemas/IntegrationManifestProvider",
        )
        self.assertEqual(
            integration_manifest_schema["properties"]["selection_recipes"]["items"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        self.assertEqual(
            schemas["IntegrationManifestSelection"]["properties"]["recipes"]["items"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        self.assertEqual(
            schemas["IntegrationManifestDeployment"]["properties"]["selection_recipe_index"]["additionalProperties"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        self.assertEqual(schemas["IntegrationManifestAuth"]["properties"]["header"]["enum"], ["X-API-Key"])
        self.assertEqual(schemas["IntegrationManifestAuth"]["properties"]["placeholder"]["enum"], ["<your-api-key>"])
        self.assertIn("IntegrationQuickstart", schemas)
        self.assertIn("IntegrationBundleData", schemas)
        self.assertIn("IntegrationBundleReadiness", schemas)
        self.assertIn("IntegrationBundleProviderSelection", schemas)
        self.assertIn("IntegrationBundleActionPlan", schemas)
        self.assertIn("IntegrationBundleActionPlanSummary", schemas)
        self.assertIn("IntegrationBundleActionItem", schemas)
        self.assertIn("action_plan", schemas["IntegrationBundleData"]["required"])
        self.assertEqual(
            schemas["IntegrationBundleData"]["properties"]["auth"]["$ref"], "#/components/schemas/IntegrationBundleAuth"
        )
        self.assertEqual(
            schemas["IntegrationBundleData"]["properties"]["openapi"]["$ref"], "#/components/schemas/IntegrationBundleOpenApi"
        )
        self.assertEqual(
            schemas["IntegrationBundleData"]["properties"]["action_plan"]["$ref"],
            "#/components/schemas/IntegrationBundleActionPlan",
        )
        self.assertEqual(
            schemas["IntegrationBundleActionPlan"]["properties"]["items"]["items"]["$ref"],
            "#/components/schemas/IntegrationBundleActionItem",
        )
        self.assertEqual(schemas["IntegrationBundleActionItem"]["properties"]["priority"]["enum"], ["high", "medium", "low"])
        self.assertEqual(
            schemas["IntegrationBundleActionItem"]["properties"]["status"]["enum"],
            ["ready", "action_required", "optional", "blocked"],
        )
        self.assertEqual(
            schemas["IntegrationBundleReadiness"]["properties"]["external_api"]["$ref"],
            "#/components/schemas/ExternalReadinessSummary",
        )
        self.assertEqual(
            schemas["IntegrationBundleReadiness"]["properties"]["providers"]["$ref"],
            "#/components/schemas/MailboxProviderReadinessSummary",
        )
        self.assertEqual(
            schemas["IntegrationBundleProviderSelection"]["properties"]["routing_matrix"]["$ref"],
            "#/components/schemas/MailboxProviderRoutingMatrix",
        )
        self.assertIn("IntegrationQuickstartAuth", schemas)
        self.assertIn("IntegrationQuickstartRequest", schemas)
        self.assertIn("IntegrationQuickstartProviderSelector", schemas)
        quickstart_schema = schemas["IntegrationQuickstart"]
        self.assertEqual(
            quickstart_schema["required"],
            ["version", "auth", "recommended_sequence", "provider_selector_fields", "endpoints", "requests", "workflow_keys"],
        )
        self.assertEqual(quickstart_schema["properties"]["auth"]["$ref"], "#/components/schemas/IntegrationQuickstartAuth")
        self.assertEqual(
            quickstart_schema["properties"]["requests"]["additionalProperties"]["$ref"],
            "#/components/schemas/IntegrationQuickstartRequest",
        )
        self.assertEqual(
            quickstart_schema["properties"]["provider_selector_fields"]["additionalProperties"]["$ref"],
            "#/components/schemas/IntegrationQuickstartProviderSelector",
        )
        self.assertIn("IntegrationManifestWorkflow", schemas)
        self.assertIn("IntegrationManifestWorkflowStep", schemas)
        self.assertEqual(
            schemas["IntegrationManifestWorkflow"]["properties"]["steps"]["items"]["$ref"],
            "#/components/schemas/IntegrationManifestWorkflowStep",
        )
        self.assertIn("endpoint", schemas["IntegrationManifestWorkflowStep"]["required"])
        self.assertEqual(schemas["IntegrationManifestWorkflowStep"]["properties"]["auth"]["enum"], ["api_key"])
        integration_provider_schema = schemas["IntegrationManifestProvider"]
        self.assertIn("env", integration_provider_schema["required"])
        self.assertIn("settings", integration_provider_schema["required"])
        self.assertEqual(
            integration_provider_schema["properties"]["env"]["items"]["$ref"],
            "#/components/schemas/IntegrationManifestKeyHint",
        )
        self.assertEqual(
            schemas["ProviderCatalogData"]["properties"]["deployment_profile"]["$ref"],
            "#/components/schemas/ProviderDeploymentProfile",
        )
        self.assertEqual(
            schemas["ProviderCatalogData"]["properties"]["integration_manifest"]["$ref"],
            "#/components/schemas/IntegrationManifest",
        )
        self.assertIn("quickstart", schemas["ProviderCatalogData"]["required"])
        self.assertEqual(
            schemas["ProviderCatalogData"]["properties"]["quickstart"]["$ref"], "#/components/schemas/IntegrationQuickstart"
        )
        self.assertIn("documentation", schemas["ProviderCatalogData"]["required"])
        self.assertEqual(
            schemas["ProviderCatalogData"]["properties"]["documentation"]["$ref"], "#/components/schemas/ProviderDocumentation"
        )
        provider_guide_schema = schemas["ProviderIntegrationGuide"]
        self.assertIn("providers", provider_guide_schema["required"])
        self.assertIn("selection_recipes", provider_guide_schema["required"])
        self.assertIn("documentation", provider_guide_schema["required"])
        self.assertEqual(
            provider_guide_schema["properties"]["documentation"]["$ref"], "#/components/schemas/ProviderDocumentation"
        )
        self.assertEqual(
            provider_guide_schema["properties"]["providers"]["items"]["$ref"],
            "#/components/schemas/ProviderIntegrationGuideProvider",
        )
        self.assertEqual(
            provider_guide_schema["properties"]["selection_recipe_index"]["additionalProperties"]["$ref"],
            "#/components/schemas/ProviderSelectionRecipe",
        )
        provider_guide_item_schema = schemas["ProviderIntegrationGuideProvider"]
        self.assertIn("pool_claim_request", provider_guide_item_schema["required"])
        self.assertIn("secret_env", provider_guide_item_schema["required"])
        self.assertIn("task_temp_apply_request", provider_guide_item_schema["properties"])
        self.assertIn("query_fields", schemas["MailboxDirectoryDiscovery"]["required"])
        self.assertIn("quick_view_presets", schemas["MailboxDirectoryDiscovery"]["required"])
        self.assertEqual(
            schemas["MailboxDirectoryDiscovery"]["properties"]["quick_view_presets"]["items"]["$ref"],
            "#/components/schemas/MailboxQuickViewPreset",
        )
        self.assertEqual(
            schemas["MailboxDirectoryDiscovery"]["properties"]["query_fields"]["items"]["enum"],
            ["kind", "status", "read_capability", "action", "provider", "search", "sort", "page", "page_size"],
        )
        self.assertEqual(
            schemas["MailboxDirectoryDiscovery"]["properties"]["response_contract"]["enum"],
            ["unified_mailbox_directory"],
        )
        self.assertIn("MailboxQuickViewPreset", schemas)
        self.assertIn("MailboxQuickViewPresetFilters", schemas)
        quick_view_schema = schemas["MailboxQuickViewPreset"]
        self.assertEqual(
            quick_view_schema["required"],
            ["key", "label", "label_en", "description", "description_en", "filters"],
        )
        self.assertFalse(quick_view_schema["additionalProperties"])
        self.assertEqual(
            quick_view_schema["properties"]["key"]["enum"],
            [item["key"] for item in expected_contract["quick_view_presets"]],
        )
        quick_view_filters_schema = schemas["MailboxQuickViewPresetFilters"]
        self.assertEqual(
            quick_view_filters_schema["required"],
            ["kind", "status", "read_capability", "action", "provider", "search", "sort"],
        )
        self.assertFalse(quick_view_filters_schema["additionalProperties"])
        self.assertEqual(quick_view_filters_schema["properties"]["kind"]["enum"], expected_contract["filters"]["kind"])
        self.assertEqual(quick_view_filters_schema["properties"]["status"]["enum"], expected_contract["filters"]["status"])
        self.assertEqual(
            quick_view_filters_schema["properties"]["read_capability"]["enum"],
            expected_contract["filters"]["read_capability"],
        )
        self.assertEqual(quick_view_filters_schema["properties"]["action"]["enum"], expected_contract["filters"]["action"])
        self.assertEqual(quick_view_filters_schema["properties"]["sort"]["enum"], expected_contract["filters"]["sort"])
        self.assertIn("claim_fields", schemas["PoolDiscovery"]["required"])
        self.assertEqual(
            schemas["PoolDiscovery"]["properties"]["claim_fields"]["items"]["enum"],
            ["caller_id", "task_id", "provider", "email_domain", "project_key"],
        )
        self.assertEqual(
            schemas["TaskTempMailboxDiscovery"]["properties"]["apply_fields"]["items"]["enum"],
            ["caller_id", "task_id", "prefix", "domain", "provider_name"],
        )
        self.assertIn("MailboxSessionDiscovery", schemas)
        self.assertEqual(
            schemas["MailboxSessionDiscovery"]["required"],
            [
                "start_endpoint",
                "read_endpoint",
                "close_endpoint",
                "start_fields",
                "read_fields",
                "close_fields",
                "read_action_values",
                "source_strategy_values",
                "read_contract",
            ],
        )
        self.assertEqual(
            schemas["MailboxSessionDiscovery"]["properties"]["start_endpoint"]["example"],
            endpoints["mailbox_session_start"],
        )
        self.assertEqual(
            schemas["MailboxSessionDiscovery"]["properties"]["read_endpoint"]["example"],
            endpoints["mailbox_session_read"],
        )
        self.assertEqual(
            schemas["MailboxSessionDiscovery"]["properties"]["close_endpoint"]["example"],
            endpoints["mailbox_session_close"],
        )
        self.assertIn("read_action", schemas["MailboxSessionDiscovery"]["properties"]["read_fields"]["items"]["enum"])
        self.assertIn(
            "verification_code", schemas["MailboxSessionDiscovery"]["properties"]["read_action_values"]["items"]["enum"]
        )
        self.assertEqual(
            schemas["MailboxSessionDiscovery"]["properties"]["source_strategy_values"]["items"]["enum"],
            ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
        )
        self.assertEqual(
            paths[endpoints["mailbox_session_start"]]["post"]["operationId"],
            "externalMailboxSessionStart",
        )
        self.assertEqual(
            paths[endpoints["mailbox_session_start"]]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/MailboxSessionStartRequest",
        )
        self.assertEqual(
            paths[endpoints["mailbox_session_close"]]["post"]["operationId"],
            "externalMailboxSessionClose",
        )
        self.assertEqual(
            paths[endpoints["mailbox_session_close"]]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/MailboxSessionCloseRequest",
        )
        self.assertEqual(
            paths[endpoints["mailbox_session_close"]]["post"]["responses"]["200"]["content"]["application/json"]["schema"][
                "allOf"
            ][1]["properties"]["data"]["$ref"],
            "#/components/schemas/MailboxSessionCloseData",
        )
        session_request = schemas["MailboxSessionStartRequest"]
        self.assertEqual(session_request["required"], ["caller_id", "task_id"])
        self.assertFalse(session_request["additionalProperties"])
        self.assertEqual(
            session_request["properties"]["source_strategy"]["enum"],
            ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
        )
        self.assertIn("duckmail", session_request["properties"]["provider"]["enum"])
        self.assertIn("duckmail", session_request["properties"]["provider_name"]["enum"])
        self.assertEqual(
            paths[endpoints["mailbox_session_start"]]["post"]["responses"]["200"]["content"]["application/json"]["schema"][
                "allOf"
            ][1]["properties"]["data"]["$ref"],
            "#/components/schemas/MailboxSessionData",
        )
        self.assertEqual(
            schemas["MailboxSessionData"]["required"],
            [
                "session_type",
                "email",
                "provider",
                "provider_label",
                "read_capability",
                "created_at",
                "lifecycle",
                "external_mailbox_read_contract",
                "next_actions",
            ],
        )
        session_close_request = schemas["MailboxSessionCloseRequest"]
        self.assertEqual(session_close_request["required"], ["session_type", "caller_id", "task_id"])
        self.assertFalse(session_close_request["additionalProperties"])
        self.assertEqual(session_close_request["properties"]["session_type"]["enum"], ["pool_claim", "task_temp_mailbox"])
        self.assertEqual(session_close_request["properties"]["caller_id"]["maxLength"], 64)
        self.assertEqual(session_close_request["properties"]["task_id"]["maxLength"], 128)
        self.assertEqual(session_close_request["properties"]["result"]["maxLength"], 512)
        self.assertEqual(session_close_request["properties"]["detail"]["maxLength"], 512)
        self.assertEqual(session_close_request["properties"]["reason"]["maxLength"], 256)
        session_close_data = schemas["MailboxSessionCloseData"]
        self.assertEqual(session_close_data["required"], ["session_type", "close_action", "status"])
        self.assertFalse(session_close_data["additionalProperties"])
        self.assertEqual(session_close_data["properties"]["status"]["enum"], ["closed"])
        pool_claim_request = schemas["PoolClaimRequest"]
        self.assertEqual(pool_claim_request["required"], ["caller_id", "task_id"])
        self.assertFalse(pool_claim_request["additionalProperties"])
        self.assertEqual(pool_claim_request["properties"]["caller_id"]["maxLength"], 64)
        self.assertEqual(pool_claim_request["properties"]["task_id"]["maxLength"], 128)
        self.assertEqual(pool_claim_request["properties"]["email_domain"]["maxLength"], 128)
        self.assertEqual(pool_claim_request["properties"]["project_key"]["maxLength"], 128)
        self.assertEqual(pool_claim_request["properties"]["provider"]["type"], ["string", "null"])
        self.assertIn("auto", pool_claim_request["properties"]["provider"]["enum"])
        self.assertIn("duckmail", pool_claim_request["properties"]["provider"]["enum"])
        self.assertIn(
            "selection_policy.scopes.explicit_pool_claim", pool_claim_request["properties"]["provider"]["description"]
        )
        self.assertEqual(
            paths[endpoints["pool_claim_release"]]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/PoolReleaseRequest",
        )
        self.assertEqual(
            paths[endpoints["pool_claim_complete"]]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/PoolCompleteRequest",
        )
        release_request = schemas["PoolReleaseRequest"]
        self.assertEqual(release_request["required"], ["account_id", "claim_token", "caller_id", "task_id"])
        self.assertFalse(release_request["additionalProperties"])
        self.assertNotIn("result", release_request["properties"])
        self.assertEqual(release_request["properties"]["reason"]["maxLength"], 256)
        complete_request = schemas["PoolCompleteRequest"]
        self.assertEqual(complete_request["required"], ["account_id", "claim_token", "caller_id", "task_id", "result"])
        self.assertFalse(complete_request["additionalProperties"])
        self.assertIn("success", complete_request["properties"]["result"]["enum"])
        self.assertEqual(complete_request["properties"]["detail"]["maxLength"], 512)
        lifecycle_request = schemas["PoolLifecycleRequest"]
        self.assertEqual(
            lifecycle_request["oneOf"],
            [
                {"$ref": "#/components/schemas/PoolReleaseRequest"},
                {"$ref": "#/components/schemas/PoolCompleteRequest"},
            ],
        )
        task_apply_request = schemas["TaskTempMailboxApplyRequest"]
        self.assertEqual(task_apply_request["required"], ["caller_id", "task_id"])
        self.assertFalse(task_apply_request["additionalProperties"])
        self.assertEqual(task_apply_request["properties"]["caller_id"]["maxLength"], 64)
        self.assertEqual(task_apply_request["properties"]["task_id"]["maxLength"], 128)
        self.assertEqual(task_apply_request["properties"]["prefix"]["maxLength"], 128)
        self.assertIn("Provider-specific prefix rules", task_apply_request["properties"]["prefix"]["description"])
        self.assertEqual(task_apply_request["properties"]["domain"]["maxLength"], 128)
        self.assertEqual(task_apply_request["properties"]["provider_name"]["type"], ["string", "null"])
        self.assertIn("duckmail", task_apply_request["properties"]["provider_name"]["enum"])
        self.assertIn(
            "selection_policy.scopes.task_temp_apply", task_apply_request["properties"]["provider_name"]["description"]
        )
        task_finish_request = schemas["TaskTempMailboxFinishRequest"]
        self.assertFalse(task_finish_request["additionalProperties"])
        self.assertEqual(task_finish_request["properties"]["result"]["type"], ["string", "null"])
        self.assertEqual(task_finish_request["properties"]["result"]["maxLength"], 512)
        self.assertIn("audit label", task_finish_request["properties"]["result"]["description"])
        self.assertEqual(task_finish_request["properties"]["detail"]["maxLength"], 512)
        self.assertIn("UnifiedMailboxDirectory", schemas)
        self.assertEqual(schemas["UnifiedMailboxDirectory"]["properties"]["contract"]["example"]["version"], 1)
        self.assertEqual(
            schemas["UnifiedMailboxDirectory"]["properties"]["contract"]["example"]["quick_view_presets"],
            expected_contract["quick_view_presets"],
        )
        self.assertIn("provider_context", schemas["UnifiedMailboxDirectory"]["required"])
        self.assertEqual(
            schemas["UnifiedMailboxDirectory"]["properties"]["facets"]["$ref"],
            "#/components/schemas/MailboxFacets",
        )
        self.assertEqual(
            schemas["UnifiedMailboxDirectory"]["properties"]["filters"]["$ref"],
            "#/components/schemas/MailboxFilters",
        )
        mailbox_filters_schema = schemas["MailboxFilters"]
        self.assertEqual(
            mailbox_filters_schema["required"],
            ["kind", "status", "read_capability", "action", "provider", "search", "sort"],
        )
        mailbox_filter_properties = mailbox_filters_schema["properties"]
        self.assertEqual(mailbox_filter_properties["kind"]["enum"], expected_contract["filters"]["kind"])
        self.assertEqual(mailbox_filter_properties["status"]["enum"], expected_contract["filters"]["status"])
        self.assertEqual(
            mailbox_filter_properties["read_capability"]["enum"],
            expected_contract["filters"]["read_capability"],
        )
        self.assertEqual(mailbox_filter_properties["action"]["enum"], expected_contract["filters"]["action"])
        self.assertEqual(mailbox_filter_properties["sort"]["enum"], expected_contract["filters"]["sort"])
        self.assertEqual(mailbox_filter_properties["provider"]["type"], "string")
        self.assertEqual(mailbox_filter_properties["search"]["type"], "string")
        self.assertEqual(
            schemas["MailboxFacets"]["required"],
            ["kinds", "statuses", "read_capabilities", "providers", "actions"],
        )
        self.assertEqual(
            schemas["MailboxFacets"]["properties"]["kinds"]["items"]["$ref"],
            "#/components/schemas/MailboxKindFacet",
        )
        self.assertEqual(
            schemas["MailboxFacets"]["properties"]["statuses"]["items"]["$ref"],
            "#/components/schemas/MailboxStatusFacet",
        )
        self.assertEqual(
            schemas["MailboxFacets"]["properties"]["read_capabilities"]["items"]["$ref"],
            "#/components/schemas/MailboxReadCapabilityFacet",
        )
        self.assertEqual(
            schemas["MailboxFacets"]["properties"]["providers"]["items"]["$ref"],
            "#/components/schemas/MailboxProviderFacet",
        )
        self.assertEqual(
            schemas["MailboxFacets"]["properties"]["actions"]["items"]["$ref"],
            "#/components/schemas/MailboxActionFacet",
        )
        self.assertEqual(
            schemas["MailboxKindFacet"]["properties"]["kind"]["enum"],
            [item["kind"] for item in expected_contract["kind_definitions"]],
        )
        self.assertIn("summary_key", schemas["MailboxKindFacet"]["required"])
        self.assertEqual(
            schemas["MailboxStatusFacet"]["properties"]["status"]["enum"],
            [item["status"] for item in expected_contract["status_definitions"]],
        )
        self.assertEqual(
            schemas["MailboxReadCapabilityFacet"]["properties"]["read_capability"]["enum"],
            [item["read_capability"] for item in expected_contract["read_capability_definitions"]],
        )
        self.assertEqual(
            schemas["MailboxActionFacet"]["properties"]["action"]["enum"],
            [item["action"] for item in expected_contract["action_definitions"]],
        )
        self.assertEqual(schemas["MailboxActionFacet"]["properties"]["count"]["minimum"], 0)
        self.assertEqual(schemas["MailboxProviderFacet"]["properties"]["count"]["minimum"], 0)
        self.assertIn("MailboxProviderContext", schemas)
        self.assertIn("readiness_summary", schemas["MailboxProviderContext"]["required"])
        self.assertIn("provider_integration_guide", schemas["MailboxProviderContext"]["required"])
        self.assertIn("documentation", schemas["MailboxProviderContext"]["required"])
        self.assertEqual(
            schemas["MailboxProviderContext"]["properties"]["readiness_summary"]["$ref"],
            "#/components/schemas/MailboxProviderReadinessSummary",
        )
        self.assertEqual(
            schemas["MailboxProviderContext"]["properties"]["documentation"]["$ref"],
            "#/components/schemas/ProviderDocumentation",
        )
        self.assertEqual(
            schemas["MailboxProviderContext"]["properties"]["deployment_profile"]["$ref"],
            "#/components/schemas/ProviderDeploymentProfile",
        )
        self.assertEqual(
            schemas["MailboxProviderContext"]["properties"]["selection_policy"]["$ref"],
            "#/components/schemas/ProviderSelectionPolicy",
        )
        self.assertEqual(
            schemas["MailboxProviderContext"]["properties"]["provider_integration_guide"]["$ref"],
            "#/components/schemas/ProviderIntegrationGuide",
        )
        self.assertIn("MailboxProviderReadinessSummary", schemas)
        self.assertIn("MailboxProviderReadinessProvider", schemas)
        self.assertIn("providers", schemas["MailboxProviderReadinessSummary"]["required"])
        self.assertIn("provider_selector_fields", schemas["MailboxProviderReadinessSummary"]["required"])
        self.assertIn("routing_matrix", schemas["MailboxProviderReadinessSummary"]["required"])
        self.assertIn("capability_matrix", schemas["MailboxProviderReadinessSummary"]["required"])
        self.assertEqual(
            schemas["MailboxProviderReadinessSummary"]["properties"]["providers"]["items"]["$ref"],
            "#/components/schemas/MailboxProviderReadinessProvider",
        )
        self.assertEqual(
            schemas["MailboxProviderReadinessSummary"]["properties"]["routing_matrix"]["$ref"],
            "#/components/schemas/MailboxProviderRoutingMatrix",
        )
        self.assertEqual(
            schemas["MailboxProviderReadinessSummary"]["properties"]["capability_matrix"]["$ref"],
            "#/components/schemas/MailboxProviderCapabilityMatrix",
        )
        for schema_name in (
            "MailboxProviderCapabilityMatrix",
            "MailboxProviderCapabilityTotals",
            "MailboxProviderCapabilityWorkflow",
            "MailboxProviderCapabilityRow",
            "MailboxProviderCapabilityRead",
        ):
            self.assertIn(schema_name, schemas)
        self.assertEqual(
            schemas["MailboxProviderCapabilityMatrix"]["properties"]["providers"]["items"]["$ref"],
            "#/components/schemas/MailboxProviderCapabilityRow",
        )
        self.assertEqual(
            schemas["MailboxProviderCapabilityMatrix"]["properties"]["totals"]["$ref"],
            "#/components/schemas/MailboxProviderCapabilityTotals",
        )
        self.assertEqual(
            schemas["MailboxProviderCapabilityMatrix"]["properties"]["workflows"]["additionalProperties"]["$ref"],
            "#/components/schemas/MailboxProviderCapabilityWorkflow",
        )
        self.assertEqual(
            schemas["MailboxProviderCapabilityRow"]["properties"]["read"]["$ref"],
            "#/components/schemas/MailboxProviderCapabilityRead",
        )
        self.assertIn("MailboxProviderRoutingMatrix", schemas)
        self.assertIn("MailboxProviderRoutingScope", schemas)
        self.assertIn("MailboxProviderRoutingProvider", schemas)
        self.assertIn("scopes", schemas["MailboxProviderRoutingMatrix"]["required"])
        self.assertEqual(
            schemas["MailboxProviderRoutingScope"]["properties"]["providers"]["items"]["$ref"],
            "#/components/schemas/MailboxProviderRoutingProvider",
        )
        self.assertIn("usable", schemas["MailboxProviderRoutingProvider"]["required"])
        self.assertIn("reason", schemas["MailboxProviderRoutingProvider"]["required"])
        self.assertEqual(
            schemas["MailboxProviderReadinessProvider"]["properties"]["mailbox_count"]["minimum"],
            0,
        )
        self.assertIn("MailboxItem", schemas)
        self.assertEqual(schemas["MailboxItem"]["properties"]["kind"]["enum"], expected_contract["kinds"])
        self.assertIn("MailboxActionContract", schemas)
        self.assertIn("action_contract", schemas["MailboxItem"]["required"])
        self.assertEqual(
            schemas["MailboxItem"]["properties"]["action_contract"]["$ref"],
            "#/components/schemas/MailboxActionContract",
        )
        self.assertIn("external", schemas["MailboxActionContract"]["required"])
        self.assertIn("internal", schemas["MailboxActionContract"]["required"])
        self.assertIn("MessagesData", schemas)
        self.assertEqual(schemas["MessagesData"]["required"], ["emails", "count", "has_more"])
        self.assertEqual(
            schemas["MessagesData"]["properties"]["emails"]["items"]["$ref"], "#/components/schemas/MessageSummary"
        )
        self.assertIn("method", schemas["MessageSummary"]["required"])
        self.assertEqual(
            schemas["MessageDetail"]["required"],
            [
                "id",
                "email_address",
                "from_address",
                "to_address",
                "subject",
                "content",
                "html_content",
                "raw_content",
                "timestamp",
                "created_at",
                "has_html",
                "method",
            ],
        )
        self.assertEqual(
            paths[endpoints["message_raw"]]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["allOf"][1][
                "properties"
            ]["data"]["$ref"],
            "#/components/schemas/RawMessageData",
        )
        self.assertEqual(
            schemas["RawMessageData"]["required"],
            ["id", "email_address", "raw_content", "method"],
        )
        self.assertEqual(
            schemas["VerificationResult"]["required"],
            [
                "formatted",
                "verification_code",
                "verification_link",
                "confidence",
                "code_confidence",
                "link_confidence",
                "matched_email_id",
                "method",
                "folder",
                "channel",
            ],
        )
        self.assertEqual(
            schemas["AccountStatusData"]["required"],
            [
                "email",
                "exists",
                "can_read",
                "account_type",
                "provider",
                "status",
                "preferred_method",
                "upstream_probe_ok",
                "probe_method",
                "last_probe_at",
                "last_probe_error",
                "last_refresh_at",
            ],
        )
        self.assertEqual(
            schemas["ProbeStatusData"]["required"],
            ["probe_id", "status", "email", "result", "error_code", "error_message", "created_at", "updated_at"],
        )
        for schema_name in (
            "MessageSummary",
            "MessageDetail",
            "RawMessageData",
            "VerificationResult",
            "AccountStatusData",
            "ProbeStatusData",
        ):
            schema_text = json.dumps(schemas[schema_name], ensure_ascii=False).lower()
            for secret_field in ("password", "refresh_token", "task_token", "provider_jwt", "api_key", "bearer"):
                self.assertNotIn(secret_field, schema_text)
        self.assertEqual(
            data.get("x-capabilities", {}).get("endpoints", {}).get("mailboxes"),
            endpoints["mailboxes"],
        )
        self.assertEqual(data.get("x-legacy-endpoints") or {}, {})
        self.assertEqual(data.get("x-compatibility", {}).get("canonical_prefix"), "/api/v1/external")
        self.assertEqual(data.get("x-compatibility", {}).get("legacy_prefix"), "/api/external")
        self.assertFalse(data.get("x-compatibility", {}).get("legacy_supported"))
        self.assertEqual(
            data.get("x-capabilities", {}).get("provider_integration_guide", {}).get("endpoints", {}).get("providers"),
            endpoints["providers"],
        )
        self.assertEqual(
            data.get("x-capabilities", {})
            .get("provider_integration_guide", {})
            .get("endpoints", {})
            .get("provider_preflight"),
            endpoints["provider_preflight"],
        )
        self.assertEqual(
            data.get("x-capabilities", {}).get("integration_manifest", {}).get("auth", {}).get("placeholder"),
            "<your-api-key>",
        )
        self._assert_provider_documentation_contract(data.get("x-capabilities", {}).get("documentation") or {})
        self.assertEqual(
            data.get("x-capabilities", {}).get("provider_integration_guide", {}).get("documentation"),
            data.get("x-capabilities", {}).get("documentation"),
        )
        self.assertEqual(
            data.get("x-capabilities", {}).get("integration_manifest", {}).get("documentation"),
            data.get("x-capabilities", {}).get("documentation"),
        )
        self.assertEqual(
            data.get("x-capabilities", {})
            .get("integration_manifest", {})
            .get("discovery", {})
            .get("endpoints", {})
            .get("providers"),
            endpoints["providers"],
        )
        self.assertEqual(
            data.get("x-capabilities", {})
            .get("integration_manifest", {})
            .get("discovery", {})
            .get("endpoints", {})
            .get("provider_preflight"),
            endpoints["provider_preflight"],
        )
        x_manifest_workflows = {
            item.get("key"): item
            for item in data.get("x-capabilities", {}).get("integration_manifest", {}).get("workflows", [])
        }
        self.assertIn("start_mailbox_session", x_manifest_workflows)
        self.assertIn("claim_pool_mailbox", x_manifest_workflows)
        self.assertIn("create_task_temp_mailbox", x_manifest_workflows)
        x_session_steps = {item.get("key"): item for item in x_manifest_workflows["start_mailbox_session"].get("steps", [])}
        self.assertEqual(x_session_steps.get("start_session", {}).get("endpoint"), endpoints["mailbox_session_start"])
        self.assertEqual(x_session_steps.get("read_session", {}).get("endpoint"), endpoints["mailbox_session_read"])
        self.assertEqual(x_session_steps.get("close_session", {}).get("endpoint"), endpoints["mailbox_session_close"])
        self.assertEqual(
            x_session_steps.get("start_session", {}).get("request", {}).get("source_strategy_values"),
            ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
        )
        x_claim_steps = {item.get("key"): item for item in x_manifest_workflows["claim_pool_mailbox"].get("steps", [])}
        self.assertEqual(x_claim_steps.get("read_verification_code", {}).get("endpoint"), endpoints["verification_code"])
        self.assertEqual(
            x_claim_steps.get("claim_random", {}).get("request", {}).get("provider_selector", {}).get("field"),
            "provider",
        )
        x_task_steps = {item.get("key"): item for item in x_manifest_workflows["create_task_temp_mailbox"].get("steps", [])}
        self.assertEqual(x_task_steps.get("finish_task_mailbox", {}).get("endpoint"), endpoints["temp_mail_finish"])
        self.assertEqual(
            x_task_steps.get("apply_task_mailbox", {}).get("request", {}).get("provider_selector", {}).get("field"),
            "provider_name",
        )
        manifest_providers = {
            item.get("provider"): item
            for item in data.get("x-capabilities", {}).get("integration_manifest", {}).get("providers", [])
        }
        duckmail_env = {item.get("key"): item for item in manifest_providers.get("duckmail", {}).get("env", [])}
        self.assertEqual(duckmail_env.get("DUCKMAIL_BEARER_TOKEN", {}).get("value"), "")
        self.assertEqual(duckmail_env.get("DUCKMAIL_API_BASE", {}).get("default"), "https://api.duckmail.sbs")
        self.assertNotIn("abc123", str(data))
        self.assertNotRegex(str(data), r"dk_[0-9a-fA-F]{20,}")

    @patch("outlook_web.services.external_api.graph_service.get_emails_graph")
    def test_account_status_response_schema_has_required_fields(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [self._graph_email()],
        }
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/account-status?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        for key in (
            "email",
            "exists",
            "upstream_probe_ok",
            "probe_method",
            "last_probe_at",
            "last_probe_error",
        ):
            self.assertIn(key, data, f"AccountStatusData 缺少字段: {key}")
        self.assertIn("status", data, "AccountStatusData 应返回 status 字段")

    @patch("outlook_web.services.external_api.graph_service.get_emails_graph")
    def test_account_status_marks_inactive_account_as_not_readable(self, mock_get_emails_graph):
        email_addr = self._insert_outlook_account()
        self._set_account_status(email_addr, "inactive")
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/account-status?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertFalse(data.get("can_read"))
        self.assertIsNone(data.get("upstream_probe_ok"))
        mock_get_emails_graph.assert_not_called()


class ExternalApiRawFieldTrimTests(ExternalApiBaseTest):
    """验证 /messages/{id}/raw 仅返回裁剪后的字段"""

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    def test_raw_endpoint_only_returns_trimmed_fields(self, mock_detail, mock_raw):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_detail.return_value = self._graph_detail(body_text="body text here")
        mock_raw.return_value = "MIME-Version: 1.0\r\nraw content"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/msg-1/raw?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        allowed_keys = {"id", "email_address", "raw_content", "method"}
        actual_keys = set(data.keys())
        self.assertEqual(
            actual_keys,
            allowed_keys,
            f"raw 接口应仅返回 {allowed_keys}，实际返回 {actual_keys}",
        )
        self.assertEqual(data["raw_content"], "MIME-Version: 1.0\r\nraw content")
        # 不应包含详情字段
        self.assertNotIn("content", data)
        self.assertNotIn("html_content", data)
        self.assertNotIn("subject", data)


class ExternalApiWaitMessageHttpTests(ExternalApiBaseTest):
    """wait-message HTTP 层集成测试"""

    @patch("outlook_web.services.external_api.time.sleep")
    @patch("outlook_web.services.external_api.time.time")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_wait_message_http_only_returns_new_message(self, mock_get_emails_graph, mock_time, mock_sleep):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")

        # baseline_timestamp = int(time.time()) = 2000000000
        # old email timestamp (~1767225600) < baseline → 不匹配
        # new email timestamp (~2019686400) >= baseline → 命中
        mock_time.side_effect = [
            2000000000,
            2000000000,
            2000000000,
            2000000000,
            2000000000,
        ]
        old_email = self._graph_email(message_id="old-msg", received_at="2026-01-01T00:00:00Z")
        new_email = self._graph_email(message_id="new-msg", received_at="2034-01-01T00:00:00Z")
        mock_get_emails_graph.side_effect = [
            {"success": True, "emails": [old_email]},
            {"success": True, "emails": [new_email]},
        ]

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&timeout_seconds=30&poll_interval=5",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("id"), "new-msg")

    def test_wait_message_http_returns_400_for_invalid_timeout(self):
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&timeout_seconds=0",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")

    def test_wait_message_http_returns_400_for_missing_email(self):
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            "/api/v1/external/wait-message?timeout_seconds=10",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")

    @patch("outlook_web.services.external_api.wait_for_message")
    def test_wait_message_http_unexpected_error_logs_audit(self, mock_wait_for_message):
        """wait-message 未预期异常也应写 external_api 审计日志"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_wait_for_message.side_effect = RuntimeError("boom")

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&timeout_seconds=10&poll_interval=5",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.get_json().get("code"), "INTERNAL_ERROR")

        audit_logs = self._external_audit_logs()
        self.assertGreaterEqual(len(audit_logs), 1)
        last_log = audit_logs[-1]
        details = json.loads(last_log["details"]) if isinstance(last_log["details"], str) else last_log["details"]
        self.assertEqual(details.get("code"), "INTERNAL_ERROR")
        self.assertEqual(details.get("err"), "RuntimeError")


# ---------------------------------------------------------------------------
# TC-AUTH-03: 错误 API Key → 401 UNAUTHORIZED
# ---------------------------------------------------------------------------
class ExternalApiWrongKeyTests(ExternalApiBaseTest):
    """TC-AUTH-03"""

    def test_wrong_api_key_returns_401(self):
        self._set_external_api_key("correct-key-123")
        client = self.app.test_client()

        resp = client.get("/api/v1/external/health", headers=self._auth_headers("wrong-key-456"))

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "UNAUTHORIZED")


# ---------------------------------------------------------------------------
# TC-MSG-04 ~ TC-MSG-15: 消息接口参数校验、过滤、回退、错误路径
# ---------------------------------------------------------------------------
class ExternalApiMessageParamTests(ExternalApiBaseTest):
    """TC-MSG-04, TC-MSG-05, TC-MSG-06, TC-MSG-07, TC-MSG-08"""

    def test_invalid_folder_returns_400(self):
        """TC-MSG-04: folder 参数非法 → 400"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}&folder=spam",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")

    def test_top_param_zero_returns_400(self):
        """TC-MSG-05: top=0 越界"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}&top=0",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")

    def test_top_param_too_large_returns_400(self):
        """TC-MSG-05: top=999 越界"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}&top=999",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_from_contains_filter(self, mock_get_emails_graph):
        """TC-MSG-06: from_contains 过滤"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [
                self._graph_email(message_id="m1", sender="openai@example.com", subject="OpenAI Code"),
                self._graph_email(message_id="m2", sender="google@example.com", subject="Google Code"),
            ],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}&from_contains=openai",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        emails = resp.get_json().get("data", {}).get("emails", [])
        self.assertEqual(len(emails), 1)
        self.assertIn("openai", emails[0].get("from_address", "").lower())

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_since_minutes_filter(self, mock_get_emails_graph):
        """TC-MSG-08: since_minutes 过滤"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {
            "success": True,
            "emails": [
                self._graph_email(message_id="new", received_at=self._utc_iso(minutes_delta=-2)),
                self._graph_email(message_id="old", received_at=self._utc_iso(minutes_delta=-60)),
            ],
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}&since_minutes=10",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        emails = resp.get_json().get("data", {}).get("emails", [])
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].get("id"), "new")


class ExternalApiMessageErrorTests(ExternalApiBaseTest):
    """TC-MSG-10, TC-MSG-13, TC-MSG-14, TC-MSG-15"""

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_latest_message_not_found(self, mock_get_emails_graph):
        """TC-MSG-10: 最新邮件不存在 → 404"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_get_emails_graph.return_value = {"success": True, "emails": []}

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/latest?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "MAIL_NOT_FOUND")

    @patch("outlook_web.services.imap.get_email_detail_imap_with_server")
    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    def test_detail_graph_fail_imap_fallback(self, mock_detail_graph, mock_raw_graph, mock_detail_imap):
        """TC-MSG-13: 详情 Graph 失败后 IMAP 回退成功"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_detail_graph.return_value = None
        mock_raw_graph.return_value = None
        mock_detail_imap.return_value = {
            "id": "msg-1",
            "subject": "IMAP Detail Subject",
            "from": "sender@test.com",
            "date": self._utc_iso(),
            "body": "IMAP body content",
            "html": "<p>IMAP body content</p>",
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/msg-1?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json().get("data", {})
        self.assertIn("content", data)
        self.assertIn("IMAP", data.get("method", ""))

    @patch("outlook_web.services.imap.get_emails_imap_with_server")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_all_upstream_fail_returns_502(self, mock_graph, mock_imap):
        """TC-MSG-14: Graph + IMAP 全部失败 → 502 UPSTREAM_READ_FAILED"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_graph.return_value = {"success": False, "error": "graph error"}
        mock_imap.return_value = {"success": False, "error": "imap error"}

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json().get("code"), "UPSTREAM_READ_FAILED")

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_proxy_error_returns_502(self, mock_graph):
        """TC-MSG-15: Graph 代理错误 → 502 PROXY_ERROR"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_graph.return_value = {
            "success": False,
            "error": {"type": "ProxyError", "message": "Proxy connection failed"},
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json().get("code"), "PROXY_ERROR")

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_proxy_error_with_nested_payload_still_returns_502_proxy_error(self, mock_graph):
        """TC-MSG-15 扩展：Graph 返回结构化错误 payload 时仍应保持 502 PROXY_ERROR"""
        from outlook_web.errors import build_error_payload

        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_graph.return_value = {
            "success": False,
            "error": build_error_payload(
                "GRAPH_TOKEN_EXCEPTION",
                "Proxy tunnel failed",
                err_type="ProxyError",
                status=500,
                details="proxy-down",
                trace_id="test-trace",
            ),
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json().get("code"), "PROXY_ERROR")
        audit_logs = self._external_audit_logs()
        self.assertTrue(audit_logs)
        details = (
            json.loads(audit_logs[-1]["details"]) if isinstance(audit_logs[-1]["details"], str) else audit_logs[-1]["details"]
        )
        self.assertEqual(details.get("code"), "PROXY_ERROR")

    @patch("outlook_web.services.external_api.messages.get_email_detail_imap_generic_result")
    def test_imap_detail_nested_error_uses_final_public_code_in_response_and_audit(self, mock_detail_result):
        email_addr = self._insert_imap_account()
        self._set_external_api_key("abc123")
        mock_detail_result.return_value = {
            "success": False,
            "error": {
                "code": "IMAP_AUTH_FAILED",
                "message": "IMAP 认证失败：Outlook.com 已阻止 Basic Auth（账号密码直连），请改用 Outlook OAuth 导入（client_id + refresh_token）",
                "message_en": "IMAP authentication failed: Outlook.com blocked Basic Auth. Use Outlook OAuth import instead.",
                "type": "IMAPAuthError",
                "status": 401,
                "details": "",
                "trace_id": "test-trace",
            },
            "error_code": "IMAP_AUTH_FAILED",
        }

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/msg-1?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json().get("code"), "IMAP_AUTH_FAILED")
        audit_logs = self._external_audit_logs()
        self.assertTrue(audit_logs)
        details = (
            json.loads(audit_logs[-1]["details"]) if isinstance(audit_logs[-1]["details"], str) else audit_logs[-1]["details"]
        )
        self.assertEqual(details.get("code"), "IMAP_AUTH_FAILED")

    def test_messages_for_inactive_account_returns_403(self):
        email_addr = self._insert_outlook_account()
        self._set_account_status(email_addr, "inactive")
        self._set_external_api_key("abc123")

        client = self.app.test_client()
        resp = client.get(f"/api/v1/external/messages?email={email_addr}", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "ACCOUNT_ACCESS_FORBIDDEN")

    def test_wait_message_for_disabled_account_returns_403(self):
        email_addr = self._insert_outlook_account()
        self._set_account_status(email_addr, "disabled")
        self._set_external_api_key("abc123")

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "ACCOUNT_ACCESS_FORBIDDEN")


# ---------------------------------------------------------------------------
# TC-VER-04, TC-VER-06, TC-VER-09, TC-VER-12: 验证码/链接错误路径
# ---------------------------------------------------------------------------
class ExternalApiVerificationErrorTests(ExternalApiBaseTest):
    """TC-VER-04, TC-VER-06, TC-VER-09, TC-VER-12"""

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_invalid_code_regex_returns_400(self, mock_list, mock_detail, mock_raw):
        """TC-VER-04: 非法正则 → 400 INVALID_PARAM"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        mock_detail.return_value = self._graph_detail(body_text="Code is 123456")
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}&code_regex=[invalid",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("code"), "INVALID_PARAM")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_no_verification_code_returns_404(self, mock_list, mock_detail, mock_raw):
        """TC-VER-06: 邮件存在但无验证码 → 404 VERIFICATION_CODE_NOT_FOUND"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        mock_detail.return_value = self._graph_detail(body_text="Hello, this is a normal email with no code.")
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "VERIFICATION_CODE_NOT_FOUND")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_no_verification_link_returns_404(self, mock_list, mock_detail, mock_raw):
        """TC-VER-09: 邮件存在但无验证链接 → 404 VERIFICATION_LINK_NOT_FOUND"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        mock_detail.return_value = self._graph_detail(body_text="No links here at all.")
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "VERIFICATION_LINK_NOT_FOUND")

    @patch("outlook_web.services.external_api.time.sleep")
    @patch("outlook_web.services.external_api.time.time")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_wait_message_timeout_returns_404(self, mock_graph, mock_time, mock_sleep):
        """TC-VER-12: 等待超时 → 404 MAIL_NOT_FOUND"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        # time.time() 模拟: baseline=100, start=100, 第1次循环检查=100, 第2次=200(超时)
        mock_time.side_effect = [100, 100, 100, 200]
        mock_graph.return_value = {"success": True, "emails": []}

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&timeout_seconds=10&poll_interval=5",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "MAIL_NOT_FOUND")


# ---------------------------------------------------------------------------
# TC-SYS-04: account-status 账号不存在
# ---------------------------------------------------------------------------
class ExternalApiSystemErrorTests(ExternalApiBaseTest):
    """TC-SYS-04"""

    def test_account_status_not_found(self):
        """TC-SYS-04: account-status 账号不存在 → 404 ACCOUNT_NOT_FOUND"""
        self._set_external_api_key("abc123")
        client = self.app.test_client()

        resp = client.get(
            "/api/v1/external/account-status?email=nonexist@nowhere.test",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "ACCOUNT_NOT_FOUND")


# ---------------------------------------------------------------------------
# BUG-00017 止血：营销邮件误命中 & 低置信度拦截
# ---------------------------------------------------------------------------
class ExternalApiVerificationConfidenceTests(ExternalApiBaseTest):
    """BUG-00017: 低置信度结果不再返回 200 OK"""

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_marketing_email_code_returns_404(self, mock_list, mock_detail, mock_raw):
        """营销邮件中的普通数字不应被当作成功验证码返回"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [
                self._graph_email(
                    subject="Runpod - 50% OFF GPU Instances",
                    sender="marketing@runpod.io",
                )
            ],
        }
        # 关键：detail 的 subject 也要与 email 列表一致（营销主题）
        marketing_detail = {
            "id": "msg-1",
            "subject": "Runpod - 50% OFF GPU Instances",
            "from": {"emailAddress": {"address": "marketing@runpod.io"}},
            "toRecipients": [{"emailAddress": {"address": "user@outlook.com"}}],
            "receivedDateTime": self._utc_iso(),
            "body": {
                "content": "Save big on 1181 new GPU instances! Order now for $2999/month.",
                "contentType": "text",
            },
        }
        mock_detail.return_value = marketing_detail
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404, "营销邮件数字不应返回 200 成功")
        self.assertEqual(resp.get_json().get("code"), "VERIFICATION_CODE_NOT_FOUND")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_marketing_email_link_returns_404(self, mock_list, mock_detail, mock_raw):
        """营销邮件中的普通链接不应被当作成功验证链接返回"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [
                self._graph_email(
                    subject="Weekly Newsletter - Check out new features",
                    sender="news@example.com",
                )
            ],
        }
        mock_detail.return_value = {
            "id": "msg-1",
            "subject": "Weekly Newsletter - Check out new features",
            "from": {"emailAddress": {"address": "news@example.com"}},
            "toRecipients": [{"emailAddress": {"address": "user@outlook.com"}}],
            "receivedDateTime": self._utc_iso(),
            "body": {
                "content": "Read more at https://blog.example.com/latest-news and https://shop.example.com/deals",
                "contentType": "text",
            },
        }
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404, "营销链接不应返回 200 成功")
        self.assertEqual(resp.get_json().get("code"), "VERIFICATION_LINK_NOT_FOUND")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_legit_verification_code_still_succeeds(self, mock_list, mock_detail, mock_raw):
        """标准验证码邮件仍可正常成功提取（高置信度 → 200 OK）"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Your verification code")],
        }
        mock_detail.return_value = self._graph_detail(
            body_text="Your verification code is 987654. Do not share this code.",
        )
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["data"]["verification_code"], "987654")
        self.assertEqual(data["data"]["code_confidence"], "high")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_legit_verification_link_still_succeeds(self, mock_list, mock_detail, mock_raw):
        """标准验证链接邮件仍可正常成功提取（高置信度 → 200 OK）"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Confirm your email address")],
        }
        mock_detail.return_value = self._graph_detail(
            body_text="Click https://auth.example.com/verify?token=abc to confirm your email.",
        )
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("verify", data["data"]["verification_link"])
        self.assertEqual(data["data"]["link_confidence"], "high")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_verification_link_returns_link_only_when_code_also_exists(self, mock_list, mock_detail, mock_raw):
        """external link 接口应只返回 link，不混杂 code。"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Your verification code")],
        }
        mock_detail.return_value = self._graph_detail(
            body_text="Your verification code is 123456. Click https://auth.example.com/verify?token=abc",
        )
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("verify", data.get("data", {}).get("verification_link", ""))
        self.assertIsNone(data.get("data", {}).get("verification_code"))

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_external_verification_code_returns_code_only_when_both_exist(self, mock_list, mock_detail, mock_raw):
        """external code 接口应只返回 code，不混杂 link。"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Your verification code")],
        }
        mock_detail.return_value = self._graph_detail(
            body_text="Your verification code is 123456. Click https://auth.example.com/verify?token=abc",
        )
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("verification_code"), "123456")
        self.assertIsNone(data.get("data", {}).get("verification_link"))

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_low_confidence_code_response_includes_confidence_metadata(self, mock_list, mock_detail, mock_raw):
        """低置信度返回 404 时，仍可从错误中辨别原因（非邮件不存在，而是无可信结果）"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="System Report")],
        }
        # 关键：detail 的 subject 也要是非验证码主题
        report_detail = {
            "id": "msg-1",
            "subject": "System Report",
            "from": {"emailAddress": {"address": "noreply@example.com"}},
            "toRecipients": [{"emailAddress": {"address": "user@outlook.com"}}],
            "receivedDateTime": self._utc_iso(),
            "body": {
                "content": "There are 445566 active users this quarter.",
                "contentType": "text",
            },
        }
        mock_detail.return_value = report_detail
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json().get("code"), "VERIFICATION_CODE_NOT_FOUND")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_code_with_custom_regex_still_returns_high_confidence(self, mock_list, mock_detail, mock_raw):
        """调用方传入 code_regex 精确匹配时，关键词命中仍返回 high confidence"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Your OTP code")],
        }
        mock_detail.return_value = self._graph_detail(
            body_text="Your OTP code is AB1234. Enter it within 5 minutes.",
        )
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}&code_regex=%5Cb%5BA-Z0-9%5D%7B6%7D%5Cb",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["data"]["verification_code"], "AB1234")
        self.assertEqual(data["data"]["code_confidence"], "high")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_code_regex_without_keyword_context_still_succeeds(self, mock_list, mock_detail, mock_raw):
        """code_regex 精确匹配，邮件无验证码关键词 → 仍应返回 200"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Account notice")],
        }
        detail = {
            "id": "msg-1",
            "subject": "Account notice",
            "from": {"emailAddress": {"address": "noreply@example.com"}},
            "toRecipients": [{"emailAddress": {"address": "user@outlook.com"}}],
            "receivedDateTime": self._utc_iso(),
            "body": {
                "content": "Use AB1234 within 5 minutes to proceed.",
                "contentType": "text",
            },
        }
        mock_detail.return_value = detail
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-code?email={email_addr}&code_regex=%5Cb%5BA-Z%5D%7B2%7D%5Cd%7B4%7D%5Cb",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200, "code_regex 精确匹配不应被拦截")
        data = resp.get_json()
        self.assertEqual(data["data"]["verification_code"], "AB1234")
        self.assertEqual(data["data"]["code_confidence"], "high")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_opaque_verify_link_with_email_context_succeeds(self, mock_list, mock_detail, mock_raw):
        """URL 不含验证关键词但邮件正文有验证语境 → 应返回 200"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {
            "success": True,
            "emails": [self._graph_email(subject="Please verify your account")],
        }
        detail = {
            "id": "msg-1",
            "subject": "Please verify your account",
            "from": {"emailAddress": {"address": "noreply@example.com"}},
            "toRecipients": [{"emailAddress": {"address": "user@outlook.com"}}],
            "receivedDateTime": self._utc_iso(),
            "body": {
                "content": "Click to verify your email: https://auth.example.com/t/abc123",
                "contentType": "text",
            },
        }
        mock_detail.return_value = detail
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 200, "邮件正文有验证语境时不应拦截链接")
        data = resp.get_json()
        self.assertIn("auth.example.com", data["data"]["verification_link"])
        self.assertEqual(data["data"]["link_confidence"], "high")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_discount_code_email_link_returns_404(self, mock_list, mock_detail, mock_raw):
        """营销邮件正文含 'discount code' + 普通链接 → 不应被提权，应返回 404"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        detail = {
            "id": "msg-1",
            "subject": "Your exclusive discount code inside!",
            "from_address": "deals@shop.example.com",
            "content": "Use discount code SAVE20 at https://shop.example.com/checkout",
            "html_content": "",
            "received_at": "2026-03-08T12:00:00Z",
        }
        mock_detail.return_value = detail
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404, "'discount code' 语境不应让普通链接通过门控")

    @patch("outlook_web.services.graph.get_email_raw_graph")
    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_confirm_your_order_link_returns_404(self, mock_list, mock_detail, mock_raw):
        """'confirm your order' 不是验证语境 → 普通链接应返回 404"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        detail = {
            "id": "msg-1",
            "subject": "Please confirm your order",
            "from_address": "orders@shop.example.com",
            "content": "Click here to confirm your order: https://shop.example.com/orders/status/789",
            "html_content": "",
            "received_at": "2026-03-08T12:00:00Z",
        }
        mock_detail.return_value = detail
        mock_raw.return_value = "RAW"

        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/verification-link?email={email_addr}",
            headers=self._auth_headers(),
        )

        self.assertEqual(resp.status_code, 404, "'confirm your order' 不应让普通链接通过门控")


# ---------------------------------------------------------------------------
class ExternalApiRegressionExtendedTests(ExternalApiBaseTest):
    """TC-REG-02, TC-REG-05"""

    @patch("outlook_web.services.graph.get_email_detail_graph")
    @patch("outlook_web.services.graph.get_emails_graph")
    def test_internal_email_detail_still_works(self, mock_list, mock_detail):
        """TC-REG-02: 旧邮件详情接口仍可用"""
        email_addr = self._insert_outlook_account()
        mock_list.return_value = {"success": True, "emails": [self._graph_email()]}
        mock_detail.return_value = self._graph_detail(body_text="detail body")

        client = self.app.test_client()
        self._login(client)

        resp = client.get(f"/api/email/{email_addr}/msg-1")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))

    def test_settings_put_old_fields_only(self):
        """TC-REG-05: PUT /api/settings 只修改旧字段不影响 external_api_key"""
        self._set_external_api_key("my-secret-key")
        client = self.app.test_client()
        self._login(client)

        resp = client.put("/api/settings", json={"refresh_interval_days": 7})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

        # external_api_key 不应被清空
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            key = settings_repo.get_external_api_key()
            self.assertTrue(key, "external_api_key 不应被清空")

    def test_settings_empty_legacy_gptmail_api_key_does_not_clear_temp_mail_api_key(
        self,
    ):
        client = self.app.test_client()
        self._login(client)

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_api_key", "temp-mail-secret")
            settings_repo.set_setting("gptmail_api_key", "legacy-secret")

        resp = client.put("/api/settings", json={"gptmail_api_key": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_api_key"), "temp-mail-secret")
            self.assertEqual(settings_repo.get_setting("gptmail_api_key"), "legacy-secret")


# ---------------------------------------------------------------------------
# TC-AUD-02, TC-AUD-03: 审计日志错误路径与敏感信息脱敏
# ---------------------------------------------------------------------------
class ExternalApiAuditTests(ExternalApiBaseTest):
    """TC-AUD-02, TC-AUD-03"""

    @patch("outlook_web.services.graph.get_emails_graph")
    def test_failed_api_call_also_logs_audit(self, mock_graph):
        """TC-AUD-02: 失败调用也写审计日志"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        mock_graph.return_value = {"success": True, "emails": []}

        client = self.app.test_client()
        # 触发 MAIL_NOT_FOUND
        resp = client.get(
            f"/api/v1/external/messages/latest?email={email_addr}",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 404)

        audit_logs = self._external_audit_logs()
        self.assertGreaterEqual(len(audit_logs), 1)
        last_log = audit_logs[-1]
        details = json.loads(last_log["details"]) if isinstance(last_log["details"], str) else last_log["details"]
        self.assertEqual(details.get("code"), "MAIL_NOT_FOUND")

    def test_audit_logs_do_not_contain_api_key(self):
        """TC-AUD-03: 审计日志不包含明文 API Key"""
        self._set_external_api_key("super-secret-api-key-12345")
        client = self.app.test_client()

        resp = client.get(
            "/api/v1/external/health",
            headers=self._auth_headers("super-secret-api-key-12345"),
        )
        self.assertEqual(resp.status_code, 200)

        audit_logs = self._external_audit_logs()
        for log in audit_logs:
            details_str = json.dumps(log) if isinstance(log, dict) else str(log)
            self.assertNotIn(
                "super-secret-api-key-12345",
                details_str,
                "审计日志不应包含明文 API Key",
            )


if __name__ == "__main__":
    unittest.main()


# ══════════════════════════════════════════════════════════════════════
# P1 安全守卫测试
# ══════════════════════════════════════════════════════════════════════


class ExternalApiGuardBaseTest(ExternalApiBaseTest):
    """P1 守卫测试基类：提供公网模式配置 helper。"""

    def setUp(self):
        super().setUp()
        # 确保默认关闭公网模式
        self._set_public_mode(False)
        self._set_ip_whitelist([])
        self._set_rate_limit(60)
        self._set_disable_feature("raw_content", False)
        self._set_disable_feature("wait_message", False)
        self._set_disable_feature("pool_claim_random", False)
        self._set_disable_feature("pool_claim_release", False)
        self._set_disable_feature("pool_claim_complete", False)
        self._set_disable_feature("pool_stats", False)

    # ── helper ──

    def _set_public_mode(self, enabled: bool):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_public_mode", "true" if enabled else "false")

    def _set_ip_whitelist(self, ips: list):
        import json as _json

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_ip_whitelist", _json.dumps(ips))

    def _set_rate_limit(self, limit: int):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_rate_limit_per_minute", str(limit))

    def _set_disable_feature(self, feature: str, disabled: bool):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting(f"external_api_disable_{feature}", "true" if disabled else "false")

    def _clear_rate_limits(self):
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute("DELETE FROM external_api_rate_limits")
            db.commit()


class GuardPublicModeOffTests(ExternalApiGuardBaseTest):
    """TC-GUARD-01~03: public_mode=false 时守卫完全透传。"""

    def test_guard_noop_when_private(self):
        """TC-GUARD-01: 私有模式下守卫不生效，请求正常通过"""
        self._set_external_api_key("abc123")
        self._set_public_mode(False)
        self._set_ip_whitelist(["10.0.0.1"])  # 故意设白名单，但私有模式不应检查
        client = self.app.test_client()
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 200)

    def test_rate_limit_noop_when_private(self):
        """TC-GUARD-02: 私有模式下限流不生效"""
        self._set_external_api_key("abc123")
        self._set_public_mode(False)
        self._set_rate_limit(1)
        client = self.app.test_client()
        for _ in range(5):
            resp = client.get("/api/v1/external/health", headers=self._auth_headers())
            self.assertEqual(resp.status_code, 200)

    def test_feature_disable_noop_when_private(self):
        """TC-GUARD-03: 私有模式下功能禁用不生效"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        self._set_public_mode(False)
        self._set_disable_feature("raw_content", True)
        self._set_disable_feature("wait_message", True)
        client = self.app.test_client()
        # raw 端点 → 应正常进入 controller（可能 404 找不到邮件，但不是 403）
        resp = client.get(
            f"/api/v1/external/messages/fake-id/raw",
            headers=self._auth_headers(),
        )
        self.assertNotEqual(resp.status_code, 403)


class GuardIpWhitelistTests(ExternalApiGuardBaseTest):
    """TC-GUARD-04~07: IP 白名单功能。"""

    def test_ip_rejected_when_not_in_whitelist(self):
        """TC-GUARD-04: 公网模式 + IP 不在白名单 → 403 IP_NOT_ALLOWED"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["10.0.0.1"])
        client = self.app.test_client()
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data["code"], "IP_NOT_ALLOWED")

    def test_ip_allowed_when_in_whitelist(self):
        """TC-GUARD-05: 公网模式 + IP 在白名单 → 正常通过"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        client = self.app.test_client()
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 200)

    def test_empty_whitelist_allows_all(self):
        """TC-GUARD-06: 公网模式 + 白名单为空 → 不限制"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist([])
        client = self.app.test_client()
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 200)

    def test_cidr_whitelist(self):
        """TC-GUARD-07: CIDR 白名单匹配"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.0/8"])
        client = self.app.test_client()
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 200)

    def test_xff_ignored_when_proxy_not_trusted(self):
        """公网模式下：不信任代理时忽略 XFF，防止伪造绕过白名单"""
        import os

        old = os.environ.pop("TRUSTED_PROXIES", None)
        try:
            self._set_external_api_key("abc123")
            self._set_public_mode(True)
            # 只允许伪造的 XFF，但不允许真实 remote_addr(127.0.0.1)
            self._set_ip_whitelist(["10.0.0.1"])
            client = self.app.test_client()
            resp = client.get(
                "/api/v1/external/health",
                headers={**self._auth_headers(), "X-Forwarded-For": "10.0.0.1"},
            )
            self.assertEqual(resp.status_code, 403)
            data = resp.get_json()
            self.assertEqual(data["code"], "IP_NOT_ALLOWED")
        finally:
            if old is not None:
                os.environ["TRUSTED_PROXIES"] = old

    def test_xff_honored_when_proxy_trusted(self):
        """公网模式下：来自受信任代理时可使用 XFF 进行白名单判断"""
        import os

        old = os.environ.get("TRUSTED_PROXIES")
        os.environ["TRUSTED_PROXIES"] = "127.0.0.1"
        try:
            self._set_external_api_key("abc123")
            self._set_public_mode(True)
            self._set_ip_whitelist(["10.0.0.1"])
            client = self.app.test_client()
            resp = client.get(
                "/api/v1/external/health",
                headers={**self._auth_headers(), "X-Forwarded-For": "10.0.0.1"},
            )
            self.assertEqual(resp.status_code, 200)
        finally:
            if old is None:
                os.environ.pop("TRUSTED_PROXIES", None)
            else:
                os.environ["TRUSTED_PROXIES"] = old


class GuardFeatureDisableTests(ExternalApiGuardBaseTest):
    """TC-GUARD-08~11: 高风险接口禁用。"""

    def test_raw_disabled(self):
        """TC-GUARD-08: 公网模式 + raw 禁用 → 403 FEATURE_DISABLED"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("raw_content", True)
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/fake-id/raw",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data["code"], "FEATURE_DISABLED")
        self.assertIn("raw_content", data.get("data", {}).get("feature", ""))

    def test_wait_message_disabled(self):
        """TC-GUARD-09: 公网模式 + wait-message 禁用 → 403"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("wait_message", True)
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertEqual(data["code"], "FEATURE_DISABLED")

    def test_raw_allowed_when_not_disabled(self):
        """TC-GUARD-10: 公网模式 + raw 未禁用 → 正常进入 controller"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("raw_content", False)
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/messages/fake-id/raw",
            headers=self._auth_headers(),
        )
        # 不是 403 FEATURE_DISABLED（可能是 404/500 等取决于后续逻辑）
        self.assertNotEqual(resp.status_code, 403)

    def test_wait_message_allowed_when_not_disabled(self):
        """TC-GUARD-11: 公网模式 + wait-message 未禁用 → 正常进入"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("wait_message", False)
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}",
            headers=self._auth_headers(),
        )
        self.assertNotEqual(resp.status_code, 403)


class GuardRateLimitTests(ExternalApiGuardBaseTest):
    """TC-GUARD-12~14: 限流功能。"""

    def test_rate_limit_exceeded(self):
        """TC-GUARD-12: 公网模式 + 超限 → 429 RATE_LIMIT_EXCEEDED"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        # Allow any client IP (Flask test client remote_addr can vary by environment).
        self._set_ip_whitelist([])
        self._set_rate_limit(1)
        self._clear_rate_limits()
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertTrue(settings_repo.get_external_api_public_mode())
            self.assertEqual(settings_repo.get_external_api_rate_limit(), 1)

        client = self.app.test_client()
        first = client.get("/api/v1/external/health", headers=self._auth_headers())
        second = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(
            first.status_code,
            200,
            f"first request should pass, got {first.status_code}: {first.get_json()}",
        )
        self.assertEqual(
            second.status_code,
            429,
            f"second request should be rate-limited, got {second.status_code}: {second.get_json()}",
        )
        data = second.get_json() or {}
        self.assertEqual(data.get("code"), "RATE_LIMIT_EXCEEDED")

    def test_rate_limit_not_exceeded(self):
        """TC-GUARD-13: 公网模式 + 未超限 → 正常通过"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist([])
        self._set_rate_limit(100)
        self._clear_rate_limits()
        client = self.app.test_client()
        for _ in range(5):
            resp = client.get("/api/v1/external/health", headers=self._auth_headers())
            self.assertEqual(resp.status_code, 200)

    def test_rate_limit_response_structure(self):
        """TC-GUARD-14: 429 响应包含 limit/current/ip"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist([])
        self._set_rate_limit(1)
        self._clear_rate_limits()
        client = self.app.test_client()
        first = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(first.status_code, 200)
        resp = client.get("/api/v1/external/health", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 429, resp.get_json())
        data = resp.get_json() or {}
        err_data = data.get("data", {})
        self.assertIn("limit", err_data)
        self.assertIn("current", err_data)
        self.assertIn("ip", err_data)


class GuardCapabilitiesTests(ExternalApiGuardBaseTest):
    """TC-GUARD-15~16: capabilities 端点 P1 增强。"""

    def test_capabilities_private_mode(self):
        """TC-GUARD-15: 私有模式 capabilities 不含 restricted_features"""
        self._set_external_api_key("abc123")
        self._set_public_mode(False)
        client = self.app.test_client()
        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertFalse(data.get("public_mode", False))

    def test_capabilities_public_mode_with_disabled(self):
        """TC-GUARD-16: 公网模式 + 功能禁用 → restricted_features 列出禁用项"""
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("raw_content", True)
        self._set_disable_feature("wait_message", True)
        client = self.app.test_client()
        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertTrue(data.get("public_mode"))
        restricted = data.get("restricted_features", [])
        self.assertIn("raw_content", restricted)
        self.assertIn("wait_message", restricted)

    def test_capabilities_public_mode_marks_disabled_pool_features(self):
        self._set_external_api_key("abc123")
        self._set_public_mode(True)
        self._set_ip_whitelist(["127.0.0.1"])
        self._set_disable_feature("pool_claim_random", True)
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("pool_external_enabled", "true")

        client = self.app.test_client()
        resp = client.get("/api/v1/external/capabilities", headers=self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertNotIn("pool_claim_random", data.get("features", []))
        self.assertIn("pool_claim_random", data.get("restricted_features", []))
        self.assertIn("pool_claim_random_disabled", data["pool"].get("restrictions", []))


class GuardSettingsApiTests(ExternalApiGuardBaseTest):
    """TC-GUARD-17~18: P1 设置读写。"""

    def test_get_settings_contains_p1_fields(self):
        """TC-GUARD-17: GET /api/settings 包含 P1 字段"""
        with self.app.test_client() as client:
            self._login(client)
            resp = client.get("/api/settings")
            self.assertEqual(resp.status_code, 200)
            s = resp.get_json()["settings"]
            self.assertIn("external_api_public_mode", s)
            self.assertIn("external_api_ip_whitelist", s)
            self.assertIn("external_api_rate_limit_per_minute", s)
            self.assertIn("external_api_disable_raw_content", s)
            self.assertIn("external_api_disable_wait_message", s)

    def test_update_p1_settings(self):
        """TC-GUARD-18: PUT /api/settings 可更新 P1 字段"""
        with self.app.test_client() as client:
            self._login(client)
            # 获取 CSRF token
            csrf_resp = client.get("/api/csrf-token")
            csrf_token = csrf_resp.get_json().get("csrf_token", "")
            resp = client.put(
                "/api/settings",
                json={
                    "external_api_public_mode": True,
                    "external_api_ip_whitelist": ["10.0.0.1", "192.168.0.0/16"],
                    "external_api_rate_limit_per_minute": 30,
                    "external_api_disable_raw_content": True,
                    "external_api_disable_wait_message": True,
                },
                headers={"X-CSRFToken": csrf_token},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["success"])
            # 验证设置已保存
            resp2 = client.get("/api/settings")
            s = resp2.get_json()["settings"]
            self.assertTrue(s["external_api_public_mode"])
            self.assertEqual(s["external_api_ip_whitelist"], ["10.0.0.1", "192.168.0.0/16"])
            self.assertEqual(s["external_api_rate_limit_per_minute"], 30)
            self.assertTrue(s["external_api_disable_raw_content"])
            self.assertTrue(s["external_api_disable_wait_message"])


# ======================================================================
# P2 异步探测 (probe) 测试
# ======================================================================


class ExternalApiProbeBaseTest(ExternalApiBaseTest):
    """P2 探测测试基类。"""

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            from outlook_web.db import get_db
            from outlook_web.repositories import settings as settings_repo

            db = get_db()
            db.execute("DELETE FROM external_probe_cache")
            db.commit()
            # 确保公网模式关闭，避免 P1 守卫干扰
            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("external_api_disable_wait_message", "false")
            settings_repo.set_setting("external_api_disable_raw_content", "false")


class ProbeCreateTests(ExternalApiProbeBaseTest):
    """TC-PROBE-01~04: 创建异步探测。"""

    def test_create_probe_async(self):
        """TC-PROBE-01: mode=async 创建探测返回 202 + probe_id"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&mode=async&timeout_seconds=30",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 202)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("probe_id", data["data"])
        self.assertEqual(data["data"]["status"], "pending")
        self.assertIn("poll_url", data["data"])

    def test_create_probe_invalid_email(self):
        """TC-PROBE-02: 不存在的邮箱 → 404"""
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get(
            "/api/v1/external/wait-message?email=nonexist@test.com&mode=async",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_create_probe_invalid_timeout(self):
        """TC-PROBE-03: 无效 timeout → 400"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&mode=async&timeout_seconds=999",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_sync_mode_still_works(self):
        """TC-PROBE-04: mode=sync（默认）保持阻塞等待行为"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        # sync 模式超时会返回 404 MAIL_NOT_FOUND
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&timeout_seconds=1&poll_interval=1",
            headers=self._auth_headers(),
        )
        self.assertIn(resp.status_code, [404, 502])  # MAIL_NOT_FOUND or upstream error


class ProbeStatusTests(ExternalApiProbeBaseTest):
    """TC-PROBE-05~08: 查询探测状态。"""

    def test_get_probe_status_pending(self):
        """TC-PROBE-05: 新建探测状态为 pending"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        # 创建
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&mode=async&timeout_seconds=60",
            headers=self._auth_headers(),
        )
        probe_id = resp.get_json()["data"]["probe_id"]
        # 查询
        resp2 = client.get(
            f"/api/v1/external/probe/{probe_id}",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp2.status_code, 200)
        data = resp2.get_json()["data"]
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["probe_id"], probe_id)

    def test_get_probe_status_not_found(self):
        """TC-PROBE-06: 不存在的 probe_id → 404"""
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get(
            "/api/v1/external/probe/nonexist123",
            headers=self._auth_headers(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_probe_requires_auth(self):
        """TC-PROBE-07: 查询探测需要 API Key"""
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get("/api/v1/external/probe/some-id")
        self.assertEqual(resp.status_code, 401)

    def test_probe_status_contains_email(self):
        """TC-PROBE-08: 探测状态包含邮箱地址"""
        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        client = self.app.test_client()
        resp = client.get(
            f"/api/v1/external/wait-message?email={email_addr}&mode=async&timeout_seconds=60",
            headers=self._auth_headers(),
        )
        probe_id = resp.get_json()["data"]["probe_id"]
        resp2 = client.get(f"/api/v1/external/probe/{probe_id}", headers=self._auth_headers())
        data = resp2.get_json()["data"]
        self.assertEqual(data["email"], email_addr)


class ProbePollTests(ExternalApiProbeBaseTest):
    """TC-PROBE-09~12: 后台探测轮询逻辑。"""

    def test_poll_marks_expired_as_timeout(self):
        """TC-PROBE-09: 过期的 pending 探测被标记为 timeout"""
        from datetime import datetime, timedelta, timezone

        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            past = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
            db.execute(
                """INSERT INTO external_probe_cache
                   (id, email_addr, status, timeout_seconds, poll_interval, expires_at, created_at, updated_at)
                   VALUES (?, ?, 'pending', 30, 5, ?, ?, ?)""",
                ("expired-probe-1", email_addr, past, past, past),
            )
            db.commit()

        with self.app.app_context():
            from outlook_web.services.external_api import poll_pending_probes

            poll_pending_probes()

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            row = db.execute(
                "SELECT status FROM external_probe_cache WHERE id = ?",
                ("expired-probe-1",),
            ).fetchone()
            self.assertEqual(row["status"], "timeout")

    def test_poll_matches_new_email(self):
        """TC-PROBE-10: 后台轮询命中新邮件时标记为 matched"""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        email_addr = self._insert_outlook_account()
        self._set_external_api_key("abc123")

        now = datetime.now(timezone.utc)
        future = (now + timedelta(seconds=120)).isoformat()
        now_iso = now.isoformat()

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute(
                """INSERT INTO external_probe_cache
                   (id, email_addr, status, timeout_seconds, poll_interval, expires_at, created_at, updated_at)
                   VALUES (?, ?, 'pending', 60, 5, ?, ?, ?)""",
                ("match-probe-1", email_addr, future, now_iso, now_iso),
            )
            db.commit()

        mock_msg = {
            "id": "msg-new",
            "subject": "Code 123456",
            "timestamp": int(now.timestamp()) + 1,
            "method": "graph",
        }
        with self.app.app_context():
            with patch(
                "outlook_web.services.external_api.probes.get_latest_message_for_external",
                return_value=mock_msg,
            ):
                from outlook_web.services.external_api import poll_pending_probes

                poll_pending_probes()

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            row = db.execute("SELECT * FROM external_probe_cache WHERE id = ?", ("match-probe-1",)).fetchone()
            self.assertEqual(row["status"], "matched")
            self.assertIn("msg-new", row["result_json"])

    def test_cleanup_old_probes(self):
        """TC-PROBE-11: cleanup 清理过期已完成探测"""
        from datetime import datetime, timedelta, timezone

        email_addr = self._insert_outlook_account()
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            old = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
            db.execute(
                """INSERT INTO external_probe_cache
                   (id, email_addr, status, timeout_seconds, poll_interval, expires_at, created_at, updated_at)
                   VALUES (?, ?, 'timeout', 30, 5, ?, ?, ?)""",
                ("old-probe-1", email_addr, old, old, old),
            )
            db.commit()

        with self.app.app_context():
            from outlook_web.services.external_api import cleanup_expired_probes

            deleted = cleanup_expired_probes(max_age_minutes=30)
            self.assertGreaterEqual(deleted, 1)

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            row = db.execute("SELECT * FROM external_probe_cache WHERE id = ?", ("old-probe-1",)).fetchone()
            self.assertIsNone(row)

    def test_poll_handles_upstream_error(self):
        """TC-PROBE-12: 轮询中上游错误标记为 error"""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        email_addr = self._insert_outlook_account()

        now = datetime.now(timezone.utc)
        future = (now + timedelta(seconds=120)).isoformat()
        now_iso = now.isoformat()

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            db.execute(
                """INSERT INTO external_probe_cache
                   (id, email_addr, status, timeout_seconds, poll_interval, expires_at, created_at, updated_at)
                   VALUES (?, ?, 'pending', 60, 5, ?, ?, ?)""",
                ("error-probe-1", email_addr, future, now_iso, now_iso),
            )
            db.commit()

        with self.app.app_context():
            with patch(
                "outlook_web.services.external_api.probes.get_latest_message_for_external",
                side_effect=RuntimeError("Network down"),
            ):
                from outlook_web.services.external_api import poll_pending_probes

                poll_pending_probes()

        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            row = db.execute("SELECT * FROM external_probe_cache WHERE id = ?", ("error-probe-1",)).fetchone()
            self.assertEqual(row["status"], "error")
            self.assertIn("Network down", row["error_message"])
