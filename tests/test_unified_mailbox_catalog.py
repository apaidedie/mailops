from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module

CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"


class UnifiedMailboxCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        self._clean_test_records()

    def tearDown(self):
        self._clean_test_records()

    def _clean_test_records(self):
        with self.app.app_context():
            clear_login_attempts()
            from mailops.db import get_db

            db = get_db()
            db.execute("DELETE FROM temp_emails WHERE email LIKE '%@unified-mailbox.test'")
            db.execute("""
                DELETE FROM tags
                WHERE name LIKE 'unified-tag-%'
                  AND id NOT IN (SELECT tag_id FROM account_tags)
                """)
            db.execute("DELETE FROM accounts WHERE email LIKE '%@unified-mailbox.test'")
            db.execute("DELETE FROM tags WHERE name LIKE 'unified-tag-%'")
            db.execute("DELETE FROM groups WHERE name LIKE 'unified-group-%'")
            db.commit()

    def _login(self, client):
        resp = client.post("/login", json={"password": "testpass123"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def _default_group_id(self) -> int:
        with self.app.app_context():
            from mailops.repositories import groups as groups_repo

            return int(groups_repo.get_default_group_id())

    def _facet_map(self, data: dict, facet_name: str, value_key: str) -> dict:
        return {item[value_key]: item for item in data["facets"][facet_name]}

    def test_api_mailboxes_returns_accounts_and_temp_mailboxes_in_one_shape(self):
        unique = uuid.uuid4().hex
        outlook_email = f"outlook-{unique}@unified-mailbox.test"
        imap_email = f"imap-{unique}@unified-mailbox.test"
        temp_email = f"temp-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db
            from mailops.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = self._default_group_id()
            outlook_cursor = db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    group_id, remark, status, latest_email_subject, latest_email_from,
                    latest_email_folder, latest_email_received_at, latest_verification_code,
                    latest_verification_folder, latest_verification_received_at
                )
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'primary outlook', 'active', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outlook_email,
                    "cid_" + unique,
                    self.module.encrypt_data("rt_" + unique),
                    default_group_id,
                    "Welcome",
                    "sender@example.com",
                    "inbox",
                    "2026-07-01T10:00:00Z",
                    "123456",
                    "inbox",
                    "2026-07-01T10:01:00Z",
                ),
            )
            outlook_account_id = int(outlook_cursor.lastrowid)
            tag_cursor = db.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)",
                ("unified-tag-" + unique, "#123456"),
            )
            db.execute(
                "INSERT INTO account_tags (account_id, tag_id) VALUES (?, ?)",
                (outlook_account_id, int(tag_cursor.lastrowid)),
            )
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    imap_host, imap_port, imap_password, group_id, remark, status
                )
                VALUES (?, '', '', '', 'imap', 'qq', 'imap.qq.com', 993, ?, ?, 'backup imap', 'inactive')
                """,
                (
                    imap_email,
                    self.module.encrypt_data("imap_pw_" + unique),
                    default_group_id,
                ),
            )
            created = temp_emails_repo.create_temp_email(
                email_addr=temp_email,
                mailbox_type="user",
                visible_in_ui=True,
                source="DuckMail",
                provider_name="DuckMail",
                task_token="tmptask_unified_" + unique,
                consumer_key="consumer:unified:" + unique,
                status="active",
                meta={
                    "provider_jwt": "jwt-" + unique,
                    "provider_secret": "secret-" + unique,
                    "provider_capabilities": {
                        "delete_mailbox": True,
                        "delete_message": True,
                        "clear_messages": True,
                    },
                },
            )
            self.assertTrue(created)
            ignored_email = f"ignored-{uuid.uuid4().hex}@outside-mailbox.test"
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    group_id, remark, status
                )
                VALUES (?, '', '', '', 'outlook', 'outlook', ?, 'not part of this filtered directory', 'active')
                """,
                (ignored_email, default_group_id),
            )
            db.commit()

        client = self.app.test_client()
        self._login(client)
        resp = client.get(f"/api/mailboxes?kind=all&search={unique}&page_size=20")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        from mailops.services.mailbox_directory_contract import (
            get_mailbox_catalog_contract,
        )

        expected_contract = get_mailbox_catalog_contract()
        self.assertTrue(data["success"])
        self.assertEqual(data["contract"]["version"], 1)
        self.assertEqual(data["contract"]["item_id_format"], "{kind}:{source_id}")
        self.assertEqual(data["contract"]["kinds"], expected_contract["kinds"])
        self.assertEqual(data["contract"]["filters"]["kind"], expected_contract["filters"]["kind"])
        self.assertEqual(
            data["contract"]["filters"]["status"],
            expected_contract["filters"]["status"],
        )
        self.assertEqual(
            data["contract"]["filters"]["read_capability"],
            expected_contract["filters"]["read_capability"],
        )
        self.assertEqual(
            data["contract"]["filters"]["action"],
            expected_contract["filters"]["action"],
        )
        self.assertEqual(data["contract"]["filters"]["sort"], expected_contract["filters"]["sort"])
        self.assertEqual(
            [item["kind"] for item in data["contract"]["kind_definitions"]],
            [item["kind"] for item in expected_contract["kind_definitions"]],
        )
        self.assertEqual(
            [item["status"] for item in data["contract"]["status_definitions"]],
            [item["status"] for item in expected_contract["status_definitions"]],
        )
        self.assertEqual(
            [item["sort"] for item in data["contract"]["sort_definitions"]],
            [item["sort"] for item in expected_contract["sort_definitions"]],
        )
        self.assertEqual(
            [item["read_capability"] for item in data["contract"]["read_capability_definitions"]],
            [item["read_capability"] for item in expected_contract["read_capability_definitions"]],
        )
        self.assertEqual(
            [item["action"] for item in data["contract"]["action_definitions"]],
            [item["action"] for item in expected_contract["action_definitions"]],
        )
        self.assertEqual(
            [item["key"] for item in data["contract"]["summary_fields"]],
            [item["key"] for item in expected_contract["summary_fields"]],
        )
        self.assertEqual(
            data["contract"]["quick_view_presets"],
            expected_contract["quick_view_presets"],
        )
        quick_view_keys = [item["key"] for item in data["contract"]["quick_view_presets"]]
        self.assertEqual(quick_view_keys, ["all", "accounts", "temp", "readable", "attention"])
        quick_view_by_key = {item["key"]: item for item in data["contract"]["quick_view_presets"]}
        self.assertEqual(quick_view_by_key["readable"]["filters"]["action"], "read_messages")
        self.assertEqual(quick_view_by_key["attention"]["filters"]["status"], "inactive")
        provider_context = data["provider_context"]
        self.assertEqual(provider_context["version"], 1)
        self.assertEqual(provider_context["defaults"]["temp_mail_provider_env"], "TEMP_MAIL_PROVIDER")
        self.assertEqual(
            provider_context["defaults"]["pool_claim_provider_env"],
            "EXTERNAL_POOL_DEFAULT_PROVIDER",
        )
        self.assertEqual(
            provider_context["deployment_env"],
            provider_context["deployment_profile"]["env"],
        )
        self.assertEqual(
            provider_context["selection_policy"]["templates"],
            provider_context["deployment_profile"]["templates"],
        )
        self.assertEqual(
            provider_context["selection_policy"]["scopes"]["task_temp_apply"]["request_field"],
            "provider_name",
        )
        self.assertEqual(
            provider_context["discovery"]["provider_health_endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health",
        )
        documentation = provider_context["documentation"]
        self.assertEqual(documentation["recommended_human_start"], "provider_onboarding")
        self.assertEqual(
            documentation["entries"]["provider_onboarding"]["path"],
            "docs/provider-onboarding.md",
        )
        self.assertEqual(
            documentation["entries"]["openapi"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json",
        )
        self.assertNotIn("legacy_endpoint", documentation["entries"]["openapi"])
        guide = provider_context["provider_integration_guide"]
        self.assertEqual(guide["version"], 1)
        self.assertEqual(guide["documentation"], documentation)
        self.assertEqual(
            guide["source_priority"],
            provider_context["selection_policy"]["source_priority"],
        )
        self.assertEqual(guide["endpoints"]["mailboxes"], f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes")
        self.assertEqual(
            guide["workflow"]["create_task_temp_mailbox"]["request_field"],
            "provider_name",
        )
        self.assertEqual(
            guide["aliases"]["runtime_temp_mail_provider_aliases"]["gptmail"],
            "legacy_bridge",
        )
        guide_providers = {item["provider"]: item for item in guide["providers"]}
        self.assertEqual(guide_providers["duckmail"]["required_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(
            guide_providers["duckmail"]["task_temp_apply_request"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
        )
        self.assertEqual(guide_providers["mail_tm"]["optional_env"], ["MAILTM_API_BASE"])
        self.assertFalse(guide["secret_policy"]["exposes_secret_values"])
        readiness = provider_context["readiness_summary"]
        self.assertEqual(readiness["version"], 1)
        self.assertIn(readiness["overall_status"], {"ready", "needs_config", "degraded"})
        self.assertEqual(readiness["totals"]["mailboxes"], 3)
        self.assertEqual(readiness["totals"]["account_mailboxes"], 2)
        self.assertEqual(readiness["totals"]["temp_mailboxes"], 1)
        self.assertGreaterEqual(readiness["totals"]["providers"], 3)
        self.assertEqual(readiness["provider_selector_fields"]["pool_claim"], "provider")
        self.assertEqual(readiness["provider_selector_fields"]["task_temp_apply"], "provider_name")
        self.assertEqual(
            readiness["endpoints"]["mailboxes"],
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes",
        )
        self.assertEqual(
            readiness["endpoints"]["providers"],
            f"{CANONICAL_EXTERNAL_PREFIX}/providers",
        )
        routing_matrix = readiness["routing_matrix"]
        self.assertEqual(routing_matrix["version"], 1)
        self.assertEqual(
            set(routing_matrix["scopes"]),
            {
                "temp_runtime_default",
                "task_temp_apply",
                "pool_claim_default",
                "explicit_pool_claim",
            },
        )
        task_scope = routing_matrix["scopes"]["task_temp_apply"]
        self.assertEqual(task_scope["request_field"], "provider_name")
        self.assertEqual(task_scope["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply")
        self.assertEqual(task_scope["counts"]["total"], len(task_scope["providers"]))
        task_rows = {item["provider"]: item for item in task_scope["providers"]}
        self.assertEqual(task_rows["duckmail"]["kind"], "temp")
        self.assertEqual(
            task_rows["duckmail"]["endpoints"]["request"],
            f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
        )
        runtime_rows = {item["provider"]: item for item in routing_matrix["scopes"]["temp_runtime_default"]["providers"]}
        self.assertEqual(runtime_rows["gptmail"]["canonical_provider"], "legacy_bridge")
        pool_rows = {item["provider"]: item for item in routing_matrix["scopes"]["explicit_pool_claim"]["providers"]}
        self.assertEqual(pool_rows["imap"]["kind"], "account")
        self.assertTrue(pool_rows["auto"]["usable"])
        readiness_rows = {(item["kind"], item["provider"]): item for item in readiness["providers"]}
        self.assertEqual(readiness_rows[("account", "outlook")]["mailbox_count"], 1)
        self.assertEqual(readiness_rows[("account", "qq")]["mailbox_count"], 1)
        self.assertEqual(readiness_rows[("temp", "duckmail")]["mailbox_count"], 1)
        self.assertEqual(readiness_rows[("temp", "duckmail")]["temp_count"], 1)
        self.assertNotIn("tmptask_unified_", str(readiness))
        self.assertNotIn("consumer:unified", str(readiness))
        self.assertNotIn("jwt-", str(readiness))
        self.assertNotIn("secret-", str(readiness))
        self.assertIn("provider_context", data["contract"])
        kind_facets = self._facet_map(data, "kinds", "kind")
        self.assertEqual(kind_facets["account"]["count"], 2)
        self.assertEqual(kind_facets["account"]["summary_key"], "account")
        self.assertEqual(kind_facets["temp"]["count"], 1)
        status_facets = self._facet_map(data, "statuses", "status")
        self.assertEqual(status_facets["active"]["count"], 2)
        self.assertEqual(status_facets["inactive"]["count"], 1)
        self.assertEqual(status_facets["finished"]["count"], 0)
        read_capability_facets = self._facet_map(data, "read_capabilities", "read_capability")
        self.assertEqual(read_capability_facets["graph"]["count"], 1)
        self.assertEqual(read_capability_facets["imap"]["count"], 1)
        self.assertEqual(read_capability_facets["temp_provider"]["count"], 1)
        by_email = {item["email"]: item for item in data["mailboxes"]}

        self.assertEqual(by_email[outlook_email]["kind"], "account")
        self.assertEqual(by_email[outlook_email]["provider"], "outlook")
        self.assertEqual(by_email[outlook_email]["provider_label"], "Outlook")
        self.assertEqual(by_email[outlook_email]["read_capability"], "graph")
        self.assertEqual(by_email[outlook_email]["latest"]["verification_code"], "123456")
        self.assertIn("unified-tag-" + unique, by_email[outlook_email]["labels"])
        self.assertTrue(by_email[outlook_email]["actions"]["refresh_auth"])
        self.assertFalse(by_email[outlook_email]["actions"]["delete_remote_mailbox"])
        outlook_contract = by_email[outlook_email]["action_contract"]
        self.assertEqual(outlook_contract["version"], 1)
        self.assertEqual(outlook_contract["read_by"], ["email"])
        self.assertEqual(outlook_contract["read_capability"], "graph")
        self.assertEqual(
            outlook_contract["external_read_contract"]["source"],
            "provider_catalog.external_mailbox_read_contract",
        )
        self.assertEqual(
            outlook_contract["external"]["read_messages"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/messages",
        )
        self.assertEqual(
            outlook_contract["external"]["read_messages"]["query"]["email"],
            outlook_email,
        )
        self.assertEqual(
            outlook_contract["external"]["wait_message_async"]["query"],
            {"mode": "async", "email": outlook_email},
        )
        self.assertEqual(outlook_contract["internal"]["open_mailbox"]["mode"], "standard")
        self.assertEqual(
            outlook_contract["internal"]["open_mailbox"]["group_id"],
            self._default_group_id(),
        )
        self.assertEqual(
            outlook_contract["internal"]["read_messages"]["endpoint"],
            "/api/emails/{email}",
        )
        self.assertNotIn("refresh_token", by_email[outlook_email])
        self.assertNotIn("refresh_token", by_email[outlook_email]["actions"])
        self.assertNotIn("refresh_token", str(outlook_contract))

        self.assertEqual(by_email[imap_email]["kind"], "account")
        self.assertEqual(by_email[imap_email]["provider"], "qq")
        self.assertEqual(by_email[imap_email]["provider_label"], "QQ 邮箱")
        self.assertEqual(by_email[imap_email]["read_capability"], "imap")
        self.assertFalse(by_email[imap_email]["actions"]["refresh_auth"])
        self.assertEqual(by_email[imap_email]["status"], "inactive")

        self.assertEqual(by_email[temp_email]["kind"], "temp")
        self.assertEqual(by_email[temp_email]["source"], "duckmail")
        self.assertEqual(by_email[temp_email]["provider"], "duckmail")
        self.assertEqual(by_email[temp_email]["provider_label"], "DuckMail")
        self.assertEqual(by_email[temp_email]["read_capability"], "temp_provider")
        self.assertTrue(by_email[temp_email]["actions"]["delete_remote_mailbox"])
        self.assertFalse(by_email[temp_email]["actions"]["refresh_auth"])
        temp_contract = by_email[temp_email]["action_contract"]
        self.assertEqual(temp_contract["version"], 1)
        self.assertEqual(temp_contract["read_capability"], "temp_provider")
        self.assertEqual(
            temp_contract["external"]["read_latest_message"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/messages/latest",
        )
        self.assertEqual(
            temp_contract["external"]["read_latest_message"]["query"]["email"],
            temp_email,
        )
        self.assertEqual(temp_contract["internal"]["open_mailbox"]["mode"], "temp-emails")
        self.assertEqual(temp_contract["internal"]["open_mailbox"]["group_id"], None)
        self.assertEqual(
            temp_contract["internal"]["read_messages"]["endpoint"],
            "/api/temp-emails/{email}/messages",
        )
        self.assertNotIn("refresh_token", by_email[temp_email]["actions"])
        self.assertNotIn("task_token", by_email[temp_email]["meta"])
        self.assertNotIn("consumer_key", by_email[temp_email]["meta"])
        self.assertNotIn("provider_jwt", by_email[temp_email]["meta"])
        self.assertNotIn("provider_secret", by_email[temp_email]["meta"])
        self.assertNotIn("tmptask_unified_", str(temp_contract))
        self.assertNotIn("consumer:unified", str(temp_contract))
        self.assertNotIn("jwt-", str(temp_contract))
        self.assertNotIn("secret-", str(temp_contract))

    def test_api_mailboxes_reports_missing_provider_config_file_in_provider_context(
        self,
    ):
        client = self.app.test_client()
        self._login(client)

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
                resp = client.get("/api/mailboxes?page_size=5")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        provider_context = data["provider_context"]
        config_file = provider_context["selection_policy"]["config_file"]

        self.assertEqual(config_file["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertFalse(config_file["loaded"])
        self.assertEqual(provider_context["provider_filter"]["source"], "config_file_error")
        self.assertEqual(
            provider_context["provider_diagnostics"]["defaults"]["temp_mail_provider"]["config_error_code"],
            "PROVIDER_CONFIG_FILE_NOT_FOUND",
        )

    def test_api_mailboxes_filters_kind_status_and_reports_counts(self):
        unique = uuid.uuid4().hex
        active_temp = f"active-{unique}@unified-mailbox.test"
        finished_temp = f"finished-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.repositories import temp_emails as temp_emails_repo

            self.assertTrue(
                temp_emails_repo.create_temp_email(email_addr=active_temp, provider_name="mail_tm", status="active")
            )
            self.assertTrue(
                temp_emails_repo.create_temp_email(email_addr=finished_temp, provider_name="mail_tm", status="finished")
            )

        client = self.app.test_client()
        self._login(client)
        resp = client.get(f"/api/mailboxes?kind=temp&status=active&search={unique}&page=1&page_size=10")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        emails = [item["email"] for item in data["mailboxes"]]
        self.assertIn(active_temp, emails)
        self.assertNotIn(finished_temp, emails)
        self.assertTrue(all(item["kind"] == "temp" for item in data["mailboxes"]))
        self.assertEqual(data["summary"]["temp"], 1)
        self.assertEqual(data["summary"]["active"], 1)
        kind_facets = self._facet_map(data, "kinds", "kind")
        self.assertEqual(kind_facets["account"]["count"], 0)
        self.assertEqual(kind_facets["temp"]["count"], 1)
        status_facets = self._facet_map(data, "statuses", "status")
        self.assertEqual(status_facets["active"]["count"], 1)
        self.assertEqual(status_facets["finished"]["count"], 1)
        self.assertEqual(status_facets["inactive"]["count"], 0)
        read_capability_facets = self._facet_map(data, "read_capabilities", "read_capability")
        self.assertEqual(read_capability_facets["graph"]["count"], 0)
        self.assertEqual(read_capability_facets["imap"]["count"], 0)
        self.assertEqual(read_capability_facets["temp_provider"]["count"], 1)

    def test_api_mailboxes_filters_read_capability(self):
        unique = uuid.uuid4().hex
        outlook_email = f"graph-{unique}@unified-mailbox.test"
        imap_email = f"imap-{unique}@unified-mailbox.test"
        temp_email = f"temp-capability-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db
            from mailops.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = self._default_group_id()
            db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active')
                """,
                (
                    outlook_email,
                    "cid_graph_" + unique,
                    self.module.encrypt_data("rt_graph_" + unique),
                    default_group_id,
                ),
            )
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    imap_host, imap_port, imap_password, group_id, status
                )
                VALUES (?, '', '', '', 'imap', 'qq', 'imap.qq.com', 993, ?, ?, 'active')
                """,
                (
                    imap_email,
                    self.module.encrypt_data("imap_pw_" + unique),
                    default_group_id,
                ),
            )
            temp_emails_repo.create_temp_email(email_addr=temp_email, provider_name="mail_tm", status="active")
            db.commit()

        client = self.app.test_client()
        self._login(client)
        graph_resp = client.get(f"/api/mailboxes?search={unique}&read_capability=graph&page_size=10")
        imap_resp = client.get(f"/api/mailboxes?search={unique}&read_capability=imap&page_size=10")
        temp_resp = client.get(f"/api/mailboxes?search={unique}&read_capability=temp_provider&page_size=10")

        self.assertEqual(graph_resp.status_code, 200)
        graph_data = graph_resp.get_json()
        self.assertEqual([item["email"] for item in graph_data["mailboxes"]], [outlook_email])
        self.assertEqual(graph_data["filters"]["read_capability"], "graph")
        self.assertEqual(
            {item["provider"] for item in graph_data["facets"]["providers"]},
            {"outlook"},
        )

        self.assertEqual(imap_resp.status_code, 200)
        imap_data = imap_resp.get_json()
        self.assertEqual([item["email"] for item in imap_data["mailboxes"]], [imap_email])
        self.assertEqual(imap_data["filters"]["read_capability"], "imap")
        self.assertEqual({item["provider"] for item in imap_data["facets"]["providers"]}, {"qq"})

        self.assertEqual(temp_resp.status_code, 200)
        temp_data = temp_resp.get_json()
        self.assertEqual([item["email"] for item in temp_data["mailboxes"]], [temp_email])
        self.assertEqual(temp_data["filters"]["read_capability"], "temp_provider")
        self.assertEqual({item["provider"] for item in temp_data["facets"]["providers"]}, {"mail_tm"})

    def test_api_mailboxes_filters_action_capability(self):
        unique = uuid.uuid4().hex
        outlook_email = f"action-outlook-{unique}@unified-mailbox.test"
        imap_email = f"action-imap-{unique}@unified-mailbox.test"
        temp_email = f"action-temp-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db
            from mailops.repositories import temp_emails as temp_emails_repo

            db = get_db()
            default_group_id = self._default_group_id()
            db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active')
                """,
                (
                    outlook_email,
                    "cid_action_" + unique,
                    self.module.encrypt_data("rt_action_" + unique),
                    default_group_id,
                ),
            )
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    imap_host, imap_port, imap_password, group_id, status
                )
                VALUES (?, '', '', '', 'imap', 'qq', 'imap.qq.com', 993, ?, ?, 'active')
                """,
                (
                    imap_email,
                    self.module.encrypt_data("imap_pw_action_" + unique),
                    default_group_id,
                ),
            )
            temp_emails_repo.create_temp_email(
                email_addr=temp_email,
                source="duckmail",
                provider_name="duckmail",
                status="active",
                meta={
                    "provider_capabilities": {
                        "delete_mailbox": True,
                        "delete_message": True,
                        "clear_messages": True,
                    }
                },
            )
            db.commit()

        client = self.app.test_client()
        self._login(client)
        refresh_resp = client.get(f"/api/mailboxes?search={unique}&action=refresh_auth&page_size=10")
        remote_delete_resp = client.get(f"/api/mailboxes?search={unique}&action=delete_remote_mailbox&page_size=10")
        clear_resp = client.get(f"/api/mailboxes?search={unique}&action=clear_messages&page_size=10")
        read_resp = client.get(f"/api/mailboxes?search={unique}&action=read_messages&page_size=10")

        self.assertEqual(refresh_resp.status_code, 200)
        refresh_data = refresh_resp.get_json()
        self.assertEqual(refresh_data["filters"]["action"], "refresh_auth")
        self.assertEqual([item["email"] for item in refresh_data["mailboxes"]], [outlook_email])
        self.assertEqual(
            {item["provider"] for item in refresh_data["facets"]["providers"]},
            {"outlook"},
        )
        refresh_action_facets = {item["action"]: item for item in refresh_data["facets"]["actions"]}
        self.assertEqual(refresh_action_facets["read_messages"]["count"], 3)
        self.assertEqual(refresh_action_facets["refresh_auth"]["count"], 1)
        self.assertEqual(refresh_action_facets["delete_remote_mailbox"]["count"], 1)
        self.assertEqual(refresh_action_facets["delete_message"]["count"], 1)
        self.assertEqual(refresh_action_facets["clear_messages"]["count"], 1)
        self.assertEqual(refresh_action_facets["delete_remote_mailbox"]["label"], "删除远端邮箱")
        self.assertEqual(
            refresh_action_facets["delete_remote_mailbox"]["label_en"],
            "Delete remote mailbox",
        )

        self.assertEqual(remote_delete_resp.status_code, 200)
        remote_delete_data = remote_delete_resp.get_json()
        self.assertEqual(remote_delete_data["filters"]["action"], "delete_remote_mailbox")
        self.assertEqual([item["email"] for item in remote_delete_data["mailboxes"]], [temp_email])
        self.assertEqual(
            {item["provider"] for item in remote_delete_data["facets"]["providers"]},
            {"duckmail"},
        )
        remote_delete_action_facets = {item["action"]: item for item in remote_delete_data["facets"]["actions"]}
        self.assertEqual(remote_delete_action_facets["read_messages"]["count"], 3)
        self.assertEqual(remote_delete_action_facets["refresh_auth"]["count"], 1)
        self.assertEqual(remote_delete_action_facets["delete_remote_mailbox"]["count"], 1)

        self.assertEqual(clear_resp.status_code, 200)
        clear_data = clear_resp.get_json()
        self.assertEqual(clear_data["filters"]["action"], "clear_messages")
        self.assertEqual([item["email"] for item in clear_data["mailboxes"]], [temp_email])

        self.assertEqual(read_resp.status_code, 200)
        read_data = read_resp.get_json()
        self.assertEqual(read_data["filters"]["action"], "read_messages")
        self.assertEqual(
            {item["email"] for item in read_data["mailboxes"]},
            {outlook_email, imap_email, temp_email},
        )

    def test_api_mailboxes_filters_provider_and_returns_provider_facets(self):
        unique = uuid.uuid4().hex
        duckmail_email = f"duck-{unique}@unified-mailbox.test"
        mailtm_email = f"mailtm-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.repositories import temp_emails as temp_emails_repo

            self.assertTrue(
                temp_emails_repo.create_temp_email(
                    email_addr=duckmail_email,
                    source="duckmail",
                    provider_name="duckmail",
                    status="active",
                )
            )
            self.assertTrue(
                temp_emails_repo.create_temp_email(
                    email_addr=mailtm_email,
                    source="mail_tm",
                    provider_name="mail_tm",
                    status="active",
                )
            )

        client = self.app.test_client()
        self._login(client)
        resp = client.get(f"/api/mailboxes?kind=temp&search={unique}&provider=duckmail&page_size=10")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["filters"]["provider"], "duckmail")
        self.assertEqual([item["email"] for item in data["mailboxes"]], [duckmail_email])
        self.assertEqual(data["summary"]["total"], 1)
        kind_facets = self._facet_map(data, "kinds", "kind")
        self.assertEqual(kind_facets["account"]["count"], 0)
        self.assertEqual(kind_facets["temp"]["count"], 1)
        status_facets = self._facet_map(data, "statuses", "status")
        self.assertEqual(status_facets["active"]["count"], 1)
        self.assertEqual(status_facets["inactive"]["count"], 0)
        read_capability_facets = self._facet_map(data, "read_capabilities", "read_capability")
        self.assertEqual(read_capability_facets["graph"]["count"], 0)
        self.assertEqual(read_capability_facets["imap"]["count"], 0)
        self.assertEqual(read_capability_facets["temp_provider"]["count"], 1)
        action_facets = {item["action"]: item for item in data["facets"]["actions"]}
        self.assertEqual(action_facets["read_messages"]["count"], 1)
        self.assertEqual(action_facets["refresh_auth"]["count"], 0)
        self.assertEqual(action_facets["delete_remote_mailbox"]["count"], 0)
        facets = {item["provider"]: item for item in data["facets"]["providers"]}
        self.assertEqual(facets["duckmail"]["label"], "DuckMail")
        self.assertEqual(facets["duckmail"]["count"], 1)
        self.assertEqual(facets["mail_tm"]["label"], "Mail.tm")
        self.assertEqual(facets["mail_tm"]["count"], 1)

        unknown_resp = client.get(f"/api/mailboxes?kind=temp&search={unique}&provider=not_real&page_size=10")
        self.assertEqual(unknown_resp.status_code, 200)
        unknown_data = unknown_resp.get_json()
        self.assertTrue(unknown_data["success"])
        self.assertEqual(unknown_data["mailboxes"], [])
        self.assertEqual(unknown_data["filters"]["provider"], "not_real")
        self.assertEqual(unknown_data["summary"]["total"], 0)

    def test_api_mailboxes_supports_stable_sort_options(self):
        unique = uuid.uuid4().hex
        older_email = f"a-older-{unique}@unified-mailbox.test"
        newer_email = f"b-newer-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db

            db = get_db()
            default_group_id = self._default_group_id()
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    group_id, status, created_at, updated_at
                )
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active', ?, ?)
                """,
                (
                    older_email,
                    "cid_older_" + unique,
                    self.module.encrypt_data("rt_older_" + unique),
                    default_group_id,
                    "2026-07-01 08:00:00",
                    "2026-07-01 09:00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO accounts (
                    email, password, client_id, refresh_token, account_type, provider,
                    group_id, status, created_at, updated_at
                )
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active', ?, ?)
                """,
                (
                    newer_email,
                    "cid_newer_" + unique,
                    self.module.encrypt_data("rt_newer_" + unique),
                    default_group_id,
                    "2026-07-02 08:00:00",
                    "2026-07-02T09:00:00Z",
                ),
            )
            db.commit()

        client = self.app.test_client()
        self._login(client)
        updated_resp = client.get(f"/api/mailboxes?search={unique}&sort=updated_desc&page_size=10")
        email_resp = client.get(f"/api/mailboxes?search={unique}&sort=email_asc&page_size=10")

        self.assertEqual(updated_resp.status_code, 200)
        updated_data = updated_resp.get_json()
        self.assertEqual(updated_data["filters"]["sort"], "updated_desc")
        self.assertEqual(
            [item["email"] for item in updated_data["mailboxes"]],
            [newer_email, older_email],
        )

        self.assertEqual(email_resp.status_code, 200)
        email_data = email_resp.get_json()
        self.assertEqual(email_data["filters"]["sort"], "email_asc")
        self.assertEqual(
            [item["email"] for item in email_data["mailboxes"]],
            [older_email, newer_email],
        )

    def test_api_mailboxes_searches_labels_group_and_domain(self):
        unique = uuid.uuid4().hex
        email = f"search-{unique}@unified-mailbox.test"
        group_name = "unified-group-" + unique
        tag_name = "unified-tag-search-" + unique

        with self.app.app_context():
            from mailops.db import get_db

            db = get_db()
            group_cursor = db.execute(
                "INSERT INTO groups (name, description, color) VALUES (?, '', '#654321')",
                (group_name,),
            )
            account_cursor = db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, remark, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, '', 'active')
                """,
                (
                    email,
                    "cid_" + unique,
                    self.module.encrypt_data("rt_" + unique),
                    int(group_cursor.lastrowid),
                ),
            )
            tag_cursor = db.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (tag_name, "#123456"))
            db.execute(
                "INSERT INTO account_tags (account_id, tag_id) VALUES (?, ?)",
                (int(account_cursor.lastrowid), int(tag_cursor.lastrowid)),
            )
            db.commit()

        client = self.app.test_client()
        self._login(client)
        tag_resp = client.get(f"/api/mailboxes?search={tag_name}")
        group_resp = client.get(f"/api/mailboxes?search={group_name}")
        domain_resp = client.get("/api/mailboxes?search=unified-mailbox.test")

        self.assertEqual(tag_resp.status_code, 200)
        self.assertIn(email, [item["email"] for item in tag_resp.get_json()["mailboxes"]])
        self.assertEqual(group_resp.status_code, 200)
        self.assertIn(email, [item["email"] for item in group_resp.get_json()["mailboxes"]])
        self.assertEqual(domain_resp.status_code, 200)
        self.assertIn(email, [item["email"] for item in domain_resp.get_json()["mailboxes"]])

    def test_api_mailboxes_rejects_invalid_filters(self):
        client = self.app.test_client()
        self._login(client)

        kind_resp = client.get("/api/mailboxes?kind=invalid")
        self.assertEqual(kind_resp.status_code, 400)
        self.assertEqual(kind_resp.get_json()["error"]["code"], "MAILBOX_KIND_INVALID")

        status_resp = client.get("/api/mailboxes?status=not-real")
        self.assertEqual(status_resp.status_code, 400)
        self.assertEqual(status_resp.get_json()["error"]["code"], "MAILBOX_STATUS_INVALID")

        read_capability_resp = client.get("/api/mailboxes?read_capability=not-real")
        self.assertEqual(read_capability_resp.status_code, 400)
        self.assertEqual(
            read_capability_resp.get_json()["error"]["code"],
            "MAILBOX_READ_CAPABILITY_INVALID",
        )

        action_resp = client.get("/api/mailboxes?action=not-real")
        self.assertEqual(action_resp.status_code, 400)
        self.assertEqual(action_resp.get_json()["error"]["code"], "MAILBOX_ACTION_INVALID")

        sort_resp = client.get("/api/mailboxes?sort=not-real")
        self.assertEqual(sort_resp.status_code, 400)
        self.assertEqual(sort_resp.get_json()["error"]["code"], "MAILBOX_SORT_INVALID")

    def test_unified_mailbox_message_preview_requires_login(self):
        client = self.app.test_client()

        for path in [
            "/api/mailboxes/account/1/messages",
            "/api/mailboxes/account/1/messages/msg-1",
            "/api/mailboxes/account/1/verification",
        ]:
            resp = client.get(path)
            self.assertEqual(resp.status_code, 401)
            self.assertEqual(resp.get_json()["error"]["code"], "AUTH_REQUIRED")

    def test_unified_mailbox_message_preview_rejects_invalid_kind(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/mailboxes/not-real/1/messages")

        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertEqual(data["error"]["code"], "MAILBOX_KIND_INVALID")
        self.assertEqual(data["allowed_kinds"], ["account", "temp"])
        self.assertEqual(data["status"], 400)

    def test_unified_mailbox_message_preview_reports_missing_sources(self):
        client = self.app.test_client()
        self._login(client)

        account_resp = client.get("/api/mailboxes/account/999999991/messages")
        temp_resp = client.get("/api/mailboxes/temp/999999992/messages")

        self.assertEqual(account_resp.status_code, 404)
        self.assertEqual(account_resp.get_json()["error"]["code"], "ACCOUNT_NOT_FOUND")
        self.assertEqual(temp_resp.status_code, 404)
        self.assertEqual(temp_resp.get_json()["error"]["code"], "TEMP_EMAIL_NOT_FOUND")

    def test_unified_mailbox_message_preview_reads_account_messages_and_strips_secrets(
        self,
    ):
        unique = uuid.uuid4().hex
        email = f"preview-account-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db

            db = get_db()
            default_group_id = self._default_group_id()
            cursor = db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active')
                """,
                (
                    email,
                    "cid_preview_" + unique,
                    self.module.encrypt_data("refresh-secret-" + unique),
                    default_group_id,
                ),
            )
            account_id = int(cursor.lastrowid)
            db.commit()

        client = self.app.test_client()
        self._login(client)
        with patch("mailops.services.external_api.list_messages_for_external") as list_mock:
            list_mock.return_value = (
                [
                    {
                        "id": "msg-account-1",
                        "from_address": "sender@example.com",
                        "subject": "Account subject",
                        "body_preview": "Account preview",
                        "created_at": "2026-07-10T08:00:00Z",
                        "timestamp": 1783670400,
                        "refresh_token": "must-not-leak",
                    }
                ],
                "Graph",
            )
            resp = client.get(f"/api/mailboxes/account/{account_id}/messages?folder=inbox&top=10")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mailbox"]["kind"], "account")
        self.assertEqual(data["mailbox"]["email"], email)
        self.assertEqual(data["method"], "Graph")
        self.assertEqual(data["messages"][0]["id"], "msg-account-1")
        self.assertEqual(data["messages"][0]["subject"], "Account subject")
        self.assertNotIn("refresh-secret", str(data))
        self.assertNotIn("must-not-leak", str(data))
        list_mock.assert_called_once_with(email_addr=email, folder="inbox", skip=0, top=10)

    def test_unified_mailbox_message_preview_reads_temp_messages_without_external_api(
        self,
    ):
        unique = uuid.uuid4().hex
        email = f"preview-temp-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db
            from mailops.repositories import temp_emails as temp_emails_repo

            self.assertTrue(
                temp_emails_repo.create_temp_email(
                    email_addr=email,
                    source="duckmail",
                    provider_name="duckmail",
                    status="active",
                    task_token="task-secret-" + unique,
                    consumer_key="consumer-secret-" + unique,
                    meta={
                        "provider_jwt": "jwt-secret-" + unique,
                        "provider_secret": "provider-secret-" + unique,
                    },
                )
            )
            db = get_db()
            temp_id = int(db.execute("SELECT id FROM temp_emails WHERE email = ?", (email,)).fetchone()["id"])

        class FakeTempMailService:
            def list_messages(self, target, *, sync_remote=True):
                self.target = target
                self.sync_remote = sync_remote
                return [
                    {
                        "id": "tmp-msg-1",
                        "from_address": "noreply@example.com",
                        "subject": "Temp subject",
                        "content_preview": "Temp preview",
                        "timestamp": 1783670401,
                        "method": "DuckMail",
                        "provider_secret": "must-not-leak",
                    }
                ]

        fake_service = FakeTempMailService()
        client = self.app.test_client()
        self._login(client)
        with (
            patch("mailops.services.external_api.list_messages_for_external") as external_mock,
            patch(
                "mailops.services.temp_mail_service.get_temp_mail_service",
                return_value=fake_service,
            ),
        ):
            resp = client.get(f"/api/mailboxes/temp/{temp_id}/messages")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mailbox"]["kind"], "temp")
        self.assertEqual(data["mailbox"]["email"], email)
        self.assertEqual(data["messages"][0]["method"], "DuckMail")
        self.assertEqual(data["messages"][0]["body_preview"], "Temp preview")
        self.assertFalse(external_mock.called)
        self.assertNotIn("task-secret", str(data))
        self.assertNotIn("consumer-secret", str(data))
        self.assertNotIn("jwt-secret", str(data))
        self.assertNotIn("provider-secret", str(data))
        self.assertNotIn("must-not-leak", str(data))

    def test_unified_mailbox_message_preview_falls_back_to_cached_temp_messages(self):
        unique = uuid.uuid4().hex
        email = f"preview-cache-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db
            from mailops.repositories import temp_emails as temp_emails_repo

            self.assertTrue(
                temp_emails_repo.create_temp_email(
                    email_addr=email,
                    source="duckmail",
                    provider_name="duckmail",
                    status="active",
                )
            )
            db = get_db()
            temp_id = int(db.execute("SELECT id FROM temp_emails WHERE email = ?", (email,)).fetchone()["id"])

        class CachedFallbackTempMailService:
            def list_messages(self, target, *, sync_remote=True):
                if sync_remote:
                    from mailops.services.temp_mail_service import TempMailError

                    raise TempMailError(
                        "TEMP_EMAIL_UPSTREAM_READ_FAILED",
                        "upstream unavailable",
                        status=502,
                    )
                return [
                    {
                        "id": "cached-msg-1",
                        "from_address": "cache@example.com",
                        "subject": "Cached subject",
                        "content_preview": "Cached preview",
                        "timestamp": 1783670402,
                        "method": "Cached Temp Mail",
                    }
                ]

            def refresh_message_detail(self, target, message_id):
                from mailops.services.temp_mail_service import TempMailError

                raise TempMailError(
                    "TEMP_EMAIL_UPSTREAM_READ_FAILED",
                    "upstream unavailable",
                    status=502,
                )

            def get_message_detail(self, target, message_id, *, refresh_if_missing=True):
                self.refresh_if_missing = refresh_if_missing
                return {
                    "id": message_id,
                    "from_address": "cache@example.com",
                    "subject": "Cached subject",
                    "content": "Cached body",
                    "timestamp": 1783670402,
                }

        fake_service = CachedFallbackTempMailService()
        client = self.app.test_client()
        self._login(client)
        with patch(
            "mailops.services.temp_mail_service.get_temp_mail_service",
            return_value=fake_service,
        ):
            list_resp = client.get(f"/api/mailboxes/temp/{temp_id}/messages")
            detail_resp = client.get(f"/api/mailboxes/temp/{temp_id}/messages/cached-msg-1")

        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.get_json()
        self.assertEqual(list_data["messages"][0]["id"], "cached-msg-1")
        self.assertEqual(list_data["messages"][0]["method"], "Cached Temp Mail")

        self.assertEqual(detail_resp.status_code, 200)
        detail_data = detail_resp.get_json()
        self.assertEqual(detail_data["message"]["id"], "cached-msg-1")
        self.assertEqual(detail_data["message"]["body"], "Cached body")
        self.assertFalse(fake_service.refresh_if_missing)

    def test_unified_mailbox_message_detail_and_verification_are_secret_safe(self):
        unique = uuid.uuid4().hex
        email = f"preview-detail-{unique}@unified-mailbox.test"

        with self.app.app_context():
            from mailops.db import get_db

            db = get_db()
            default_group_id = self._default_group_id()
            cursor = db.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, status)
                VALUES (?, '', ?, ?, 'outlook', 'outlook', ?, 'active')
                """,
                (
                    email,
                    "cid_preview_detail_" + unique,
                    self.module.encrypt_data("refresh-detail-" + unique),
                    default_group_id,
                ),
            )
            account_id = int(cursor.lastrowid)
            db.commit()

        client = self.app.test_client()
        self._login(client)
        with (
            patch("mailops.services.external_api.get_message_detail_for_external") as detail_mock,
            patch("mailops.services.external_api.get_verification_result") as verification_mock,
        ):
            detail_mock.return_value = {
                "id": "detail-1",
                "from_address": "sender@example.com",
                "to_address": email,
                "subject": "Detail subject",
                "body_html": "<p>Code 123456</p>",
                "body_text": "Code 123456",
                "has_html": True,
                "refresh_token": "must-not-leak-detail",
            }
            verification_mock.return_value = {
                "verification_code": "123456",
                "verification_link": "https://example.com/verify",
                "formatted": "123456",
                "confidence": "high",
                "claim_token": "must-not-leak-verification",
            }

            detail_resp = client.get(f"/api/mailboxes/account/{account_id}/messages/detail-1")
            verification_resp = client.get(f"/api/mailboxes/account/{account_id}/verification")

        self.assertEqual(detail_resp.status_code, 200)
        detail_data = detail_resp.get_json()
        self.assertTrue(detail_data["success"])
        self.assertEqual(detail_data["message"]["body_type"], "html")
        self.assertEqual(detail_data["message"]["body"], "<p>Code 123456</p>")
        self.assertNotIn("must-not-leak", str(detail_data))

        self.assertEqual(verification_resp.status_code, 200)
        verification_data = verification_resp.get_json()
        self.assertTrue(verification_data["success"])
        self.assertEqual(verification_data["verification"]["verification_code"], "123456")
        self.assertNotIn("must-not-leak", str(verification_data))

    def test_api_mailboxes_coerces_invalid_pagination_and_allows_empty_results(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/mailboxes?search=no-such-unified-mailbox&page=bad&page_size=also-bad")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mailboxes"], [])
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 50)
        self.assertEqual(data["pagination"]["total_count"], 0)
        self.assertEqual(data["pagination"]["total_pages"], 0)

    def test_service_mailboxes_coerces_invalid_pagination_values(self):
        with self.app.app_context():
            from mailops.services.mailbox_catalog import list_unified_mailboxes

            data = list_unified_mailboxes(page="bad", page_size="also-bad")

        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 50)

    def test_mailbox_source_registry_tracks_directory_contract_kinds(self):
        from mailops.services.mailbox_catalog import get_mailbox_source_loader_kinds
        from mailops.services.mailbox_directory_contract import (
            get_mailbox_catalog_contract,
        )

        self.assertEqual(get_mailbox_source_loader_kinds(), get_mailbox_catalog_contract()["kinds"])

    def test_mailbox_catalog_contract_exposes_provider_agnostic_quick_view_presets(
        self,
    ):
        from mailops.services.mailbox_directory_contract import (
            get_mailbox_catalog_contract,
        )

        contract = get_mailbox_catalog_contract()
        presets = contract["quick_view_presets"]
        self.assertEqual(
            [item["key"] for item in presets],
            ["all", "accounts", "temp", "readable", "attention"],
        )
        for preset in presets:
            self.assertEqual(
                set(preset["filters"].keys()),
                {
                    "kind",
                    "status",
                    "read_capability",
                    "action",
                    "provider",
                    "sort",
                    "search",
                },
            )
            self.assertIn(preset["filters"]["kind"], contract["filters"]["kind"])
            self.assertIn(preset["filters"]["status"], contract["filters"]["status"])
            self.assertIn(
                preset["filters"]["read_capability"],
                contract["filters"]["read_capability"],
            )
            self.assertIn(preset["filters"]["action"], contract["filters"]["action"])
            self.assertIn(preset["filters"]["sort"], contract["filters"]["sort"])
            self.assertEqual(preset["filters"]["provider"], "all")

        quick_view_text = str(presets)
        for provider_name in [
            "duckmail",
            "mail_tm",
            "emailnator",
            "gptmail",
            "legacy_bridge",
        ]:
            self.assertNotIn(provider_name, quick_view_text.lower())
        self.assertNotRegex(quick_view_text, r"dk_[0-9a-fA-F]{20,}")

    def test_service_mailboxes_loads_items_through_source_registry(self):
        with self.app.app_context():
            from mailops.services import mailbox_catalog

            registry_email = "registry-source@unified-mailbox.test"
            registry_item = {
                "id": "account:registry-source",
                "source_id": 901,
                "kind": "account",
                "email": registry_email,
                "domain": "unified-mailbox.test",
                "status": "active",
                "pool_status": "",
                "source": "account",
                "provider": "registry_provider",
                "provider_label": "Registry Provider",
                "account_type": "imap",
                "read_capability": "imap",
                "group": {"id": None, "name": "Registry", "color": "#666666"},
                "labels": [],
                "remark": "loaded from source registry",
                "latest": {},
                "timestamps": {
                    "created_at": "2026-07-01T00:00:00Z",
                    "updated_at": "2026-07-01T00:00:00Z",
                },
                "notification_enabled": False,
                "actions": {"read_messages": True},
                "action_contract": {},
                "meta": {},
            }
            original_loaders = mailbox_catalog.MAILBOX_SOURCE_LOADERS
            mailbox_catalog.MAILBOX_SOURCE_LOADERS = (
                mailbox_catalog.MailboxSourceLoader(kind="account", load=lambda: [registry_item]),
            )
            try:
                data = mailbox_catalog.list_unified_mailboxes(search="registry-source")
            finally:
                mailbox_catalog.MAILBOX_SOURCE_LOADERS = original_loaders

        self.assertEqual([item["email"] for item in data["mailboxes"]], [registry_email])
        self.assertEqual(data["summary"]["total"], 1)
        self.assertEqual(data["summary"]["account"], 1)
        kind_facets = self._facet_map(data, "kinds", "kind")
        self.assertEqual(kind_facets["account"]["count"], 1)
        self.assertEqual(kind_facets["temp"]["count"], 0)
        status_facets = self._facet_map(data, "statuses", "status")
        self.assertEqual(status_facets["active"]["count"], 1)
        read_capability_facets = self._facet_map(data, "read_capabilities", "read_capability")
        self.assertEqual(read_capability_facets["imap"]["count"], 1)
        self.assertEqual(read_capability_facets["graph"]["count"], 0)
        self.assertEqual(read_capability_facets["temp_provider"]["count"], 0)
        self.assertEqual(data["facets"]["providers"][0]["provider"], "registry_provider")
        action_facets = {item["action"]: item for item in data["facets"]["actions"]}
        self.assertEqual(action_facets["read_messages"]["count"], 1)
        self.assertEqual(action_facets["refresh_auth"]["count"], 0)

    def test_bridge_dual_register_inventory_and_facets_collapse(self):
        """custom_domain_temp_mail + legacy_bridge must collapse in facets/inventory."""
        from mailops.services.mailbox_catalog import (
            _apply_provider_filter,
            _canonical_inventory_provider,
            _mailbox_provider_inventory,
            _provider_facets,
        )

        items = [
            {
                "provider": "custom_domain_temp_mail",
                "provider_label": "Compatible Temp Mail Bridge",
                "kind": "temp",
                "read_capability": "temp_provider",
            },
            {
                "provider": "legacy_bridge",
                "provider_label": "Compatible Temp Mail Bridge",
                "kind": "temp",
                "read_capability": "temp_provider",
            },
            {
                "provider": "duckmail",
                "provider_label": "DuckMail",
                "kind": "temp",
                "read_capability": "temp_provider",
            },
        ]

        self.assertEqual(_canonical_inventory_provider("custom_domain_temp_mail"), "legacy_bridge")
        self.assertEqual(_canonical_inventory_provider("gptmail"), "legacy_bridge")

        facets = {row["provider"]: row for row in _provider_facets(items)}
        self.assertIn("legacy_bridge", facets)
        self.assertNotIn("custom_domain_temp_mail", facets)
        self.assertEqual(facets["legacy_bridge"]["count"], 2)
        self.assertEqual(facets["duckmail"]["count"], 1)

        inventory = _mailbox_provider_inventory(items)
        providers = {row["provider"]: row for row in inventory["providers"]}
        self.assertEqual(set(providers), {"legacy_bridge", "duckmail"})
        self.assertEqual(providers["legacy_bridge"]["mailbox_count"], 2)
        self.assertEqual(inventory["totals"]["providers"], 2)

        # Filter by either alias returns both bridge rows.
        self.assertEqual(len(_apply_provider_filter(items, "custom_domain_temp_mail")), 2)
        self.assertEqual(len(_apply_provider_filter(items, "legacy_bridge")), 2)
        self.assertEqual(len(_apply_provider_filter(items, "duckmail")), 1)

    def test_bridge_allowlist_family_activates_dual_register_twins(self):
        """Allowlisting either bridge catalog key keeps the twin active."""
        from mailops.services import provider_catalog as provider_catalog_mod

        original = provider_catalog_mod._active_provider_names
        try:
            provider_catalog_mod._active_provider_names = lambda strict=True: {"legacy_bridge"}
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "legacy_bridge"))
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "custom_domain_temp_mail"))
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "gptmail"))
            self.assertFalse(provider_catalog_mod.is_mailbox_provider_active("temp", "duckmail"))

            provider_catalog_mod._active_provider_names = lambda strict=True: {"custom_domain_temp_mail"}
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "custom_domain_temp_mail"))
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "legacy_bridge"))
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "gptmail"))

            provider_catalog_mod._active_provider_names = lambda strict=True: {"gptmail"}
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "legacy_bridge"))
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "custom_domain_temp_mail"))

            provider_catalog_mod._active_provider_names = lambda strict=True: {"duckmail"}
            self.assertFalse(provider_catalog_mod.is_mailbox_provider_active("temp", "legacy_bridge"))
            self.assertFalse(provider_catalog_mod.is_mailbox_provider_active("temp", "custom_domain_temp_mail"))
            self.assertTrue(provider_catalog_mod.is_mailbox_provider_active("temp", "duckmail"))
        finally:
            provider_catalog_mod._active_provider_names = original

    def test_operator_default_temp_provider_matches_collapsed_guide(self):
        """Discovery defaults project bridge dual-register keys to legacy_bridge."""
        from mailops.repositories import settings as settings_repo
        from mailops.services.provider_catalog import (
            get_external_api_capabilities_contract,
            get_operator_temp_mail_default_provider,
            get_provider_integration_guide,
        )

        # Stored/runtime name may remain the historical dual-register key.
        self.assertEqual(
            settings_repo.get_temp_mail_runtime_provider_name(strict=False),
            "custom_domain_temp_mail",
        )
        operator_default = get_operator_temp_mail_default_provider(strict=False)
        self.assertEqual(operator_default, "legacy_bridge")

        guide = get_provider_integration_guide()
        guide_temp = {item.get("provider") for item in (guide.get("providers") or []) if item.get("kind") == "temp"}
        self.assertIn(operator_default, guide_temp)
        self.assertNotIn("custom_domain_temp_mail", guide_temp)

        capabilities = get_external_api_capabilities_contract()
        self.assertEqual(
            (capabilities.get("defaults") or {}).get("temp_mail_provider"),
            "legacy_bridge",
        )
        defaults = ((capabilities.get("provider_diagnostics") or {}).get("defaults") or {}).get("temp_mail_provider") or {}
        self.assertEqual(defaults.get("provider"), "legacy_bridge")
        self.assertEqual(defaults.get("raw_provider"), "custom_domain_temp_mail")

    def test_bridge_dual_register_diagnostics_and_guide_collapse(self):
        """Diagnostics and integration guide collapse bridge dual-register rows."""
        from mailops.services.provider_catalog import (
            get_mailbox_provider_catalog,
            get_mailbox_provider_diagnostics,
            get_provider_integration_guide,
        )

        catalog = get_mailbox_provider_catalog(include_inactive=True, strict=False)
        catalog_temp = {item.get("provider") for item in catalog if item.get("kind") == "temp"}
        self.assertIn("custom_domain_temp_mail", catalog_temp)
        self.assertIn("legacy_bridge", catalog_temp)

        diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
        diag_providers = {item.get("provider") for item in (diagnostics.get("providers") or []) if item.get("kind") == "temp"}
        self.assertIn("legacy_bridge", diag_providers)
        self.assertNotIn("custom_domain_temp_mail", diag_providers)
        self.assertEqual(diagnostics.get("summary", {}).get("total"), len(diagnostics.get("providers") or []))
        self.assertEqual(diagnostics.get("summary", {}).get("temp"), len(diag_providers))

        guide = get_provider_integration_guide()
        guide_providers = {item.get("provider") for item in (guide.get("providers") or []) if item.get("kind") == "temp"}
        self.assertIn("legacy_bridge", guide_providers)
        self.assertNotIn("custom_domain_temp_mail", guide_providers)
        bridge_labels = [
            item.get("label") for item in (guide.get("providers") or []) if item.get("label") == "Compatible Temp Mail Bridge"
        ]
        self.assertEqual(len(bridge_labels), 1)


if __name__ == "__main__":
    unittest.main()
