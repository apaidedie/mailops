import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module

CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"


class _HealthCheckTempMailProvider:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def health_check(self):
        return {
            "success": True,
            "method": "mock_health_check",
            "network_probe": True,
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


class MultiMailboxSupportTests(unittest.TestCase):
    """
    对齐：PRD-00005 / FD-00005 / TDD-00005 / TEST-00005
    目标：验证多邮箱（Outlook + IMAP provider）核心能力与回归门禁。
    """

    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("external_api_public_mode", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_random", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_release", "false")
            settings_repo.set_setting("external_api_disable_pool_claim_complete", "false")
            settings_repo.set_setting("external_api_disable_pool_stats", "false")
            settings_repo.set_setting("pool_default_provider", "")
            settings_repo.set_setting("active_mailbox_providers", "")

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)

    def _default_group_id(self) -> int:
        conn = self.module.create_sqlite_connection()
        try:
            row = conn.execute("SELECT id FROM groups WHERE name = '默认分组' LIMIT 1").fetchone()
            return int(row["id"]) if row else 1
        finally:
            conn.close()

    def test_db_schema_v3_has_multi_mailbox_columns(self):
        conn = self.module.create_sqlite_connection()
        try:
            cols = conn.execute("PRAGMA table_info(accounts)").fetchall()
            names = {c[1] for c in cols}  # (cid, name, type, notnull, dflt_value, pk)
        finally:
            conn.close()

        self.assertIn("account_type", names)
        self.assertIn("provider", names)
        self.assertIn("imap_host", names)
        self.assertIn("imap_port", names)
        self.assertIn("imap_password", names)

    def test_providers_api_returns_fixed_order(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)

        providers = data.get("providers") or []
        # PRD-00006 / FD-00006：providers 列表新增 "auto"（智能识别混合导入）
        self.assertEqual(len(providers), 9)
        self.assertEqual(providers[0].get("key"), "auto")
        self.assertEqual(providers[1].get("key"), "outlook")
        self.assertEqual(providers[-1].get("key"), "custom")

        keys = [p.get("key") for p in providers]
        self.assertIn("auto", keys)
        self.assertIn("qq", keys)
        self.assertIn("163", keys)

    def test_providers_api_includes_unified_mailbox_catalog(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_bearer_token", "")
            settings_repo.set_setting("emailnator_api_key", "")
            settings_repo.set_setting("pool_default_provider", "duckmail")

        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        catalog = data.get("mailbox_providers") or []
        self.assertEqual(data.get("default_pool_claim_provider"), "duckmail")
        self.assertEqual(data.get("default_pool_claim_provider_env"), "EXTERNAL_POOL_DEFAULT_PROVIDER")
        # Operator-facing default temp provider matches collapsed guide bridge key.
        self.assertEqual(data.get("default_temp_mail_provider"), "legacy_bridge")
        self.assertEqual(data.get("default_temp_mail_provider_env"), "TEMP_MAIL_PROVIDER")
        self.assertIn("default_temp_mail_provider_label", data)
        self.assertIn("default_temp_mail_provider_configured", data)
        self.assertIsInstance(data.get("default_temp_mail_provider_missing_config"), list)
        guide_temp = {
            item.get("provider")
            for item in (data.get("provider_integration_guide") or {}).get("providers") or []
            if item.get("kind") == "temp"
        }
        self.assertIn(data.get("default_temp_mail_provider"), guide_temp)
        self.assertEqual(
            data.get("deployment_env"),
            {
                "active_mailbox_providers": "ACTIVE_MAILBOX_PROVIDERS",
                "pool_claim_provider": "EXTERNAL_POOL_DEFAULT_PROVIDER",
                "temp_mail_provider": "TEMP_MAIL_PROVIDER",
            },
        )
        deployment_profile = data.get("deployment_profile") or {}
        self.assertEqual(deployment_profile.get("version"), 1)
        self.assertEqual(deployment_profile.get("env"), data.get("deployment_env"))
        selection_policy = data.get("selection_policy") or {}
        self.assertEqual(selection_policy.get("version"), 1)
        self.assertEqual(selection_policy.get("source_priority"), ["env", "provider_config_file", "settings", "default"])
        self.assertEqual(selection_policy.get("templates"), deployment_profile.get("templates"))
        self.assertEqual(selection_policy.get("config_file", {}).get("priority_slot"), "provider_config_file")
        self.assertEqual(selection_policy.get("config_file", {}).get("diagnostic_source"), "config_file")
        self.assertEqual(
            selection_policy.get("scopes", {}).get("active_allowlist", {}).get("config_keys"),
            ["ACTIVE_MAILBOX_PROVIDERS", "active_mailbox_providers", "active_providers"],
        )
        self.assertEqual(
            selection_policy.get("scopes", {}).get("pool_claim_default", {}).get("request_field"),
            "provider",
        )
        self.assertIn("auto", selection_policy.get("scopes", {}).get("pool_claim_default", {}).get("allowed_values") or [])
        self.assertIn(
            "duckmail",
            selection_policy.get("scopes", {}).get("task_temp_apply", {}).get("allowed_values") or [],
        )
        self.assertEqual(
            selection_policy.get("scopes", {}).get("temp_runtime_default", {}).get("aliases", {}).get("gptmail"),
            "legacy_bridge",
        )
        guide = data.get("provider_integration_guide") or {}
        self.assertEqual(guide.get("version"), 1)
        self.assertEqual(
            (data.get("documentation") or {}).get("entries", {}).get("provider_onboarding", {}).get("path"),
            "docs/provider-onboarding.md",
        )
        self.assertEqual(guide.get("documentation"), data.get("documentation"))
        self.assertEqual(guide.get("source_priority"), selection_policy.get("source_priority"))
        self.assertEqual((guide.get("endpoints") or {}).get("providers"), f"{CANONICAL_EXTERNAL_PREFIX}/providers")
        self.assertEqual((guide.get("workflow") or {}).get("claim_pool_mailbox", {}).get("request_field"), "provider")
        self.assertEqual(
            (guide.get("workflow") or {}).get("create_task_temp_mailbox", {}).get("request_field"), "provider_name"
        )
        self.assertEqual(
            (guide.get("aliases") or {}).get("runtime_temp_mail_provider_aliases", {}).get("gptmail"), "legacy_bridge"
        )
        self.assertEqual(
            (guide.get("aliases") or {}).get("pool_claim_provider_aliases", {}).get("imap", {}).get("kind"), "account"
        )
        guide_providers = {item.get("provider"): item for item in guide.get("providers") or []}
        # Operator/API guide collapses Compatible Temp Mail Bridge dual-register keys.
        self.assertIn("legacy_bridge", guide_providers)
        self.assertNotIn("custom_domain_temp_mail", guide_providers)
        self.assertEqual(guide_providers.get("duckmail", {}).get("required_env"), ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(guide_providers.get("duckmail", {}).get("pool_claim_request", {}).get("value"), "duckmail")
        self.assertEqual(guide_providers.get("duckmail", {}).get("task_temp_apply_request", {}).get("field"), "provider_name")
        self.assertEqual(
            guide_providers.get("mail_tm", {}).get("configuration", {}).get("env_defaults"),
            {"MAILTM_API_BASE": "https://api.mail.tm"},
        )
        self.assertFalse((guide.get("secret_policy") or {}).get("exposes_secret_values"))
        manifest = data.get("integration_manifest") or {}
        self.assertEqual(manifest.get("version"), 1)
        self.assertEqual(manifest.get("documentation"), data.get("documentation"))
        self.assertEqual((manifest.get("auth") or {}).get("placeholder"), "<your-api-key>")
        self.assertEqual((manifest.get("selection") or {}).get("source_priority"), selection_policy.get("source_priority"))
        self.assertEqual((manifest.get("selection") or {}).get("explicit_pool_claim", {}).get("request_field"), "provider")
        self.assertEqual((manifest.get("selection") or {}).get("task_temp_apply", {}).get("request_field"), "provider_name")
        self.assertEqual(
            (manifest.get("discovery") or {}).get("endpoints", {}).get("providers"), f"{CANONICAL_EXTERNAL_PREFIX}/providers"
        )
        workflows = {item.get("key"): item for item in manifest.get("workflows") or []}
        self.assertIn("claim_pool_mailbox", workflows)
        self.assertIn("create_task_temp_mailbox", workflows)
        claim_steps = {item.get("key"): item for item in workflows.get("claim_pool_mailbox", {}).get("steps") or []}
        self.assertEqual(
            claim_steps.get("claim_random", {}).get("request", {}).get("provider_selector", {}).get("field"), "provider"
        )
        self.assertEqual(claim_steps.get("read_messages", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/messages")
        self.assertEqual(
            claim_steps.get("complete_claim", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-complete"
        )
        task_steps = {item.get("key"): item for item in workflows.get("create_task_temp_mailbox", {}).get("steps") or []}
        self.assertEqual(
            task_steps.get("apply_task_mailbox", {}).get("request", {}).get("provider_selector", {}).get("field"),
            "provider_name",
        )
        self.assertEqual(
            task_steps.get("finish_task_mailbox", {}).get("endpoint"),
            f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/{{task_token}}/finish",
        )
        self.assertEqual(data.get("quickstart"), manifest.get("quickstart"))
        quickstart = data.get("quickstart") or {}
        self.assertEqual(quickstart.get("version"), 1)
        self.assertEqual((quickstart.get("auth") or {}).get("headers"), {"X-API-Key": "<your-api-key>"})
        self.assertEqual((quickstart.get("provider_selector_fields") or {}).get("pool_claim", {}).get("field"), "provider")
        self.assertEqual(
            (quickstart.get("provider_selector_fields") or {}).get("task_temp_apply", {}).get("field"), "provider_name"
        )
        self.assertEqual(
            (quickstart.get("requests") or {}).get("pool_claim", {}).get("body", {}).get("provider"), "<provider-or-auto>"
        )
        self.assertEqual(
            (quickstart.get("requests") or {}).get("task_temp_apply", {}).get("body", {}).get("provider_name"),
            "<provider-name>",
        )
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", json.dumps(quickstart, ensure_ascii=False))
        manifest_providers = {item.get("provider"): item for item in manifest.get("providers") or []}
        duckmail_manifest = manifest_providers.get("duckmail") or {}
        duckmail_env = {item.get("key"): item for item in duckmail_manifest.get("env") or []}
        self.assertEqual(duckmail_env.get("DUCKMAIL_BEARER_TOKEN", {}).get("value"), "")
        self.assertTrue(duckmail_env.get("DUCKMAIL_BEARER_TOKEN", {}).get("secret"))
        self.assertEqual(duckmail_env.get("DUCKMAIL_API_BASE", {}).get("default"), "https://api.duckmail.sbs")
        self.assertEqual(
            (duckmail_manifest.get("request_fields") or {}).get("task_temp_apply", {}).get("request_field"), "provider_name"
        )
        self.assertNotRegex(json.dumps(manifest, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")
        provider_values = deployment_profile.get("provider_values") or {}
        self.assertIn("duckmail", provider_values.get("all") or [])
        self.assertIn("mail_tm", provider_values.get("temp_runtime") or [])
        self.assertIn("gptmail", provider_values.get("temp_runtime") or [])
        self.assertIn("imap", provider_values.get("pool_claim") or [])
        self.assertIn("auto", provider_values.get("pool_claim") or [])
        self.assertIn("DUCKMAIL_BEARER_TOKEN", deployment_profile.get("config_env", {}).get("required") or [])
        self.assertIn("DUCKMAIL_BEARER_TOKEN", deployment_profile.get("config_env", {}).get("secret") or [])
        self.assertEqual(
            deployment_profile.get("config_env", {}).get("defaults", {}).get("MAILTM_API_BASE"),
            "https://api.mail.tm",
        )
        self.assertIn("duckmail_bearer_token", deployment_profile.get("config_settings", {}).get("required") or [])
        self.assertEqual(
            deployment_profile.get("provider_examples", {}).get("duckmail", {}).get("runtime_default", {}).get("value"),
            "duckmail",
        )
        templates = deployment_profile.get("templates") or {}
        self.assertEqual(templates.get("priority"), ["env", "provider_config_file", "settings", "default"])
        env_template = templates.get("env", {}).get("content") or ""
        self.assertIn("# OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE=.runtime/providers.json", env_template)
        self.assertNotIn("\nOUTLOOK_EMAIL_PROVIDER_CONFIG_FILE=.runtime/providers.json", env_template)
        self.assertIn("MAILTM_API_BASE=https://api.mail.tm", env_template)
        self.assertIn("DUCKMAIL_BEARER_TOKEN=", env_template)
        for secret_env in deployment_profile.get("config_env", {}).get("secret") or []:
            self.assertIn(f"{secret_env}=", env_template)
        self.assertNotIn("dk_", env_template)
        self.assertNotIn("secret-default", env_template)
        provider_config = templates.get("provider_config_object") or {}
        self.assertEqual(provider_config.get("providers", {}).get("pool_default_provider"), "auto")
        self.assertIn('"pool_default_provider": "auto"', templates.get("provider_config_json", {}).get("content") or "")
        self.assertIn('pool_default_provider = "auto"', templates.get("provider_config_toml", {}).get("content") or "")
        read_contract = data.get("external_mailbox_read_contract") or {}
        self.assertEqual(
            read_contract.get("read_endpoints", {}).get("latest_message"), f"{CANONICAL_EXTERNAL_PREFIX}/messages/latest"
        )
        self.assertEqual(
            read_contract.get("next_actions", {}).get("read_verification_code", {}).get("endpoint"),
            f"{CANONICAL_EXTERNAL_PREFIX}/verification-code",
        )

        by_key = {(item.get("kind"), item.get("provider")): item for item in catalog}
        # Account import selector reuses mailbox_providers notes from get_provider_list().
        self.assertEqual((by_key.get(("account", "auto")) or {}).get("note"), "自动识别每行的账号类型，支持混合文件一键导入")
        self.assertIn("OAuth2", (by_key.get(("account", "outlook")) or {}).get("note") or "")
        self.assertIn("IMAP", (by_key.get(("account", "gmail")) or {}).get("note") or "")
        # Account import selector reuses mailbox_providers notes from get_provider_list().
        self.assertEqual((by_key.get(("account", "auto")) or {}).get("note"), "自动识别每行的账号类型，支持混合文件一键导入")
        self.assertIn("OAuth2", (by_key.get(("account", "outlook")) or {}).get("note") or "")
        self.assertIn("IMAP", (by_key.get(("account", "gmail")) or {}).get("note") or "")
        self.assertEqual(by_key[("account", "outlook")]["read_capability"], "graph")
        self.assertEqual(by_key[("account", "gmail")]["read_capability"], "imap")
        self.assertEqual(by_key[("temp", "mail_tm")]["label"], "Mail.tm")
        self.assertEqual(by_key[("temp", "duckmail")]["label"], "DuckMail")
        self.assertEqual(by_key[("temp", "emailnator")]["read_capability"], "temp_provider")
        self.assertTrue(by_key[("temp", "mail_tm")]["configured"])
        self.assertEqual(by_key[("temp", "mail_tm")]["selection"]["runtime_env"], {"TEMP_MAIL_PROVIDER": "mail_tm"})
        self.assertEqual(by_key[("temp", "mail_tm")]["deployment"]["runtime_default"]["value"], "mail_tm")
        self.assertEqual(
            by_key[("temp", "mail_tm")]["deployment"]["pool_claim_request"], {"field": "provider", "value": "mail_tm"}
        )
        self.assertEqual(by_key[("temp", "mail_tm")]["deployment"]["config_env"]["optional"], ["MAILTM_API_BASE"])
        self.assertEqual(by_key[("temp", "mail_tm")]["configuration"]["optional_env"], ["MAILTM_API_BASE"])
        self.assertEqual(
            by_key[("temp", "mail_tm")]["configuration"]["env_defaults"], {"MAILTM_API_BASE": "https://api.mail.tm"}
        )
        self.assertFalse(by_key[("temp", "duckmail")]["configured"])
        self.assertEqual(by_key[("temp", "duckmail")]["missing_config"], ["duckmail_bearer_token"])
        self.assertEqual(by_key[("temp", "duckmail")]["configuration"]["required_env"], ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual(
            by_key[("temp", "duckmail")]["configuration"]["settings_defaults"],
            {"duckmail_api_base": "https://api.duckmail.sbs"},
        )
        self.assertEqual(by_key[("temp", "duckmail")]["configuration"]["secret_settings"], ["duckmail_bearer_token"])
        duckmail_schema_fields = by_key[("temp", "duckmail")]["configuration"]["config_schema"]["fields"]
        self.assertEqual([field["key"] for field in duckmail_schema_fields], ["duckmail_api_base", "duckmail_bearer_token"])
        self.assertEqual(duckmail_schema_fields[1]["type"], "password")
        self.assertNotIn("default", duckmail_schema_fields[1])
        self.assertFalse(by_key[("temp", "emailnator")]["configured"])
        self.assertEqual(by_key[("temp", "emailnator")]["missing_config"], ["emailnator_api_key"])
        self.assertEqual(by_key[("temp", "emailnator")]["configuration"]["required_env"], ["EMAILNATOR_API_KEY"])
        self.assertEqual(
            by_key[("temp", "emailnator")]["configuration"]["settings_defaults"],
            {"emailnator_email_types": ["public_gmail_plus"]},
        )
        emailnator_schema_fields = by_key[("temp", "emailnator")]["configuration"]["config_schema"]["fields"]
        self.assertEqual(
            [field["key"] for field in emailnator_schema_fields], ["emailnator_api_key", "emailnator_email_types"]
        )
        self.assertEqual(emailnator_schema_fields[0]["type"], "password")
        self.assertEqual(by_key[("account", "gmail")]["configuration"]["account_import_fields"], ["email", "password"])
        self.assertEqual(by_key[("account", "gmail")]["configuration"]["secret_fields"], ["password"])
        self.assertEqual(
            by_key[("account", "custom")]["selection"]["pool_claim_temp_fallback_provider_names"],
            ["custom_domain_temp_mail", "legacy_bridge"],
        )
        self.assertEqual(
            by_key[("temp", "legacy_bridge")]["selection"]["accepted_aliases"], ["gptmail", "legacy_gptmail", "temp_mail"]
        )
        diagnostics = data.get("provider_diagnostics") or {}
        self.assertEqual(diagnostics.get("scope", {}).get("type"), "local_config")
        self.assertFalse(diagnostics.get("scope", {}).get("network_probe"))
        self.assertEqual(diagnostics.get("summary", {}).get("total"), len(diagnostics.get("providers") or []))
        diagnostic_by_key = {(item.get("kind"), item.get("provider")): item for item in diagnostics.get("providers") or []}
        # Full mailbox_providers catalog still dual-registers for source compatibility,
        # but diagnostics collapse to a single operator-facing bridge row.
        self.assertIn(("temp", "legacy_bridge"), diagnostic_by_key)
        self.assertNotIn(("temp", "custom_domain_temp_mail"), diagnostic_by_key)
        self.assertIn(("temp", "custom_domain_temp_mail"), by_key)
        self.assertIn(("temp", "legacy_bridge"), by_key)
        self.assertEqual(diagnostic_by_key[("temp", "duckmail")]["status"], "needs_config")
        self.assertEqual(diagnostic_by_key[("account", "outlook")]["status"], "ready")

        readiness = data.get("readiness_summary") or {}
        self.assertEqual(readiness.get("version"), 1)
        routing_matrix = readiness.get("routing_matrix") or {}
        self.assertEqual(routing_matrix.get("version"), 1)
        routing_scopes = routing_matrix.get("scopes") or {}
        self.assertEqual(
            set(routing_scopes),
            {"temp_runtime_default", "task_temp_apply", "pool_claim_default", "explicit_pool_claim"},
        )
        task_scope = routing_scopes["task_temp_apply"]
        self.assertEqual(task_scope.get("request_field"), "provider_name")
        self.assertEqual(task_scope.get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply")
        self.assertIn("duckmail", task_scope.get("allowed_values") or [])
        self.assertEqual(task_scope.get("counts", {}).get("total"), len(task_scope.get("providers") or []))
        task_rows = {item.get("provider"): item for item in task_scope.get("providers") or []}
        self.assertEqual(task_rows["duckmail"]["kind"], "temp")
        self.assertFalse(task_rows["duckmail"]["usable"])
        self.assertEqual(task_rows["duckmail"]["status"], "needs_config")
        self.assertEqual(task_rows["duckmail"]["endpoints"]["request"], f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply")
        runtime_rows = {item.get("provider"): item for item in routing_scopes["temp_runtime_default"].get("providers") or []}
        self.assertEqual(runtime_rows["gptmail"]["canonical_provider"], "legacy_bridge")
        self.assertEqual(runtime_rows["gptmail"]["kind"], "temp")
        pool_rows = {item.get("provider"): item for item in routing_scopes["explicit_pool_claim"].get("providers") or []}
        self.assertTrue(pool_rows["auto"]["usable"])
        self.assertEqual(pool_rows["imap"]["kind"], "account")
        self.assertEqual(pool_rows["imap"]["reason"], "alias_pool_claim_provider")
        self.assertNotRegex(json.dumps(routing_matrix, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")

    def test_gptmail_provider_reports_needs_config_without_db_or_env_api_key(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo
            from mailops.services.provider_catalog import get_mailbox_provider_diagnostics

            settings_repo.set_setting("temp_mail_api_key", "")
            settings_repo.set_setting("gptmail_api_key", "")
            with patch.dict("os.environ", {"GPTMAIL_API_KEY": ""}, clear=False):
                diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)

        diagnostic_by_key = {(item.get("kind"), item.get("provider")): item for item in diagnostics.get("providers") or []}
        legacy_bridge = diagnostic_by_key[("temp", "legacy_bridge")]
        self.assertEqual(legacy_bridge["status"], "needs_config")
        self.assertIn("temp_mail_api_key", legacy_bridge["missing_config"])

    def test_bridge_dual_register_collapsed_in_diagnostics_and_integration_guide(self):
        """Operator diagnostics/guide must not double Compatible Temp Mail Bridge rows."""
        with self.app.app_context():
            from mailops.services.provider_catalog import (
                get_mailbox_provider_catalog,
                get_mailbox_provider_diagnostics,
                get_provider_integration_guide,
            )

            full_catalog = get_mailbox_provider_catalog(include_inactive=True, strict=False)
            catalog_bridge = {
                item.get("provider")
                for item in full_catalog
                if item.get("provider") in {"custom_domain_temp_mail", "legacy_bridge"}
            }
            # Registry dual-register remains for stored-source compatibility.
            self.assertEqual(catalog_bridge, {"custom_domain_temp_mail", "legacy_bridge"})

            diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
            diag_providers = [item.get("provider") for item in diagnostics.get("providers") or []]
            self.assertIn("legacy_bridge", diag_providers)
            self.assertNotIn("custom_domain_temp_mail", diag_providers)
            summary = diagnostics.get("summary") or {}
            self.assertEqual(summary.get("total"), len(diag_providers))
            self.assertEqual(
                summary.get("temp"),
                sum(1 for item in diagnostics.get("providers") or [] if item.get("kind") == "temp"),
            )

            guide = get_provider_integration_guide()
            guide_providers = [item.get("provider") for item in guide.get("providers") or []]
            self.assertIn("legacy_bridge", guide_providers)
            self.assertNotIn("custom_domain_temp_mail", guide_providers)
            bridge_row = next(item for item in guide.get("providers") or [] if item.get("provider") == "legacy_bridge")
            self.assertEqual(bridge_row.get("label"), "Compatible Temp Mail Bridge")

    def test_providers_api_reflects_active_mailbox_provider_filter(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("active_mailbox_providers"), ["duckmail"])
        self.assertEqual(data.get("active_mailbox_provider_env"), "ACTIVE_MAILBOX_PROVIDERS")
        catalog = data.get("mailbox_providers") or []
        self.assertEqual({item.get("provider") for item in catalog}, {"duckmail"})
        diagnostics = data.get("provider_diagnostics") or {}
        self.assertEqual(diagnostics.get("filter", {}).get("active_providers"), ["duckmail"])
        self.assertGreater(diagnostics.get("summary", {}).get("inactive", 0), 0)

    def test_providers_api_reports_unknown_active_mailbox_provider_filter_entries(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail,not_a_provider,gptmail")

        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        diagnostics = data.get("provider_diagnostics") or {}
        provider_filter = diagnostics.get("filter") or {}
        self.assertEqual(provider_filter.get("active_providers"), ["duckmail", "not_a_provider", "gptmail"])
        self.assertEqual(provider_filter.get("unknown_providers"), ["not_a_provider"])
        self.assertIn("duckmail", provider_filter.get("supported_providers") or [])
        self.assertIn("gptmail", provider_filter.get("recognized_aliases") or [])
        self.assertEqual(diagnostics.get("summary", {}).get("unknown_filter_entries"), 1)

    def test_providers_api_reports_invalid_default_provider_entries(self):
        client = self.app.test_client()
        self._login(client)

        with patch.dict(
            "os.environ",
            {
                "TEMP_MAIL_PROVIDER": "not_a_temp_provider",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "not_a_pool_provider",
            },
            clear=False,
        ):
            resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        diagnostics = data.get("provider_diagnostics") or {}
        defaults = diagnostics.get("defaults") or {}
        temp_default = defaults.get("temp_mail_provider") or {}
        pool_default = defaults.get("pool_claim_provider") or {}
        invalid_defaults = defaults.get("invalid_defaults") or []

        self.assertFalse(temp_default.get("valid"))
        self.assertEqual(temp_default.get("source"), "env")
        self.assertEqual(temp_default.get("key"), "TEMP_MAIL_PROVIDER")
        self.assertEqual(temp_default.get("provider"), "not_a_temp_provider")
        self.assertFalse(pool_default.get("valid"))
        self.assertEqual(pool_default.get("source"), "env")
        self.assertEqual(pool_default.get("key"), "EXTERNAL_POOL_DEFAULT_PROVIDER")
        self.assertEqual(pool_default.get("provider"), "not_a_pool_provider")
        self.assertEqual(
            {item.get("key"): item.get("provider") for item in invalid_defaults},
            {
                "TEMP_MAIL_PROVIDER": "not_a_temp_provider",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "not_a_pool_provider",
            },
        )
        self.assertEqual(diagnostics.get("summary", {}).get("invalid_default_entries"), 2)

    def test_providers_api_accepts_default_provider_aliases_without_invalid_diagnostics(self):
        client = self.app.test_client()
        self._login(client)

        with patch.dict(
            "os.environ",
            {
                "TEMP_MAIL_PROVIDER": "gptmail",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "imap",
            },
            clear=False,
        ):
            resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        diagnostics = resp.get_json().get("provider_diagnostics") or {}
        defaults = diagnostics.get("defaults") or {}

        self.assertTrue(defaults.get("temp_mail_provider", {}).get("valid"))
        self.assertEqual(defaults.get("temp_mail_provider", {}).get("provider"), "legacy_bridge")
        self.assertTrue(defaults.get("pool_claim_provider", {}).get("valid"))
        self.assertEqual(defaults.get("pool_claim_provider", {}).get("provider"), "imap")
        self.assertEqual(defaults.get("invalid_defaults"), [])
        self.assertEqual(diagnostics.get("summary", {}).get("invalid_default_entries"), 0)

    def test_providers_api_reports_config_file_provider_sources(self):
        client = self.app.test_client()
        self._login(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "providers.json"
            config_path.write_text(
                '{"providers":{"temp_mail_provider":"mail_tm","pool_default_provider":"mail_tm","active_mailbox_providers":["mail_tm"]}}',
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE": str(config_path)}, clear=False):
                resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        diagnostics = data.get("provider_diagnostics") or {}
        defaults = diagnostics.get("defaults") or {}
        provider_filter = diagnostics.get("filter") or {}

        self.assertEqual(data.get("active_mailbox_providers"), ["mail_tm"])
        self.assertEqual(data.get("selection_policy", {}).get("config_file", {}).get("sections"), ["providers"])
        self.assertEqual(
            data.get("selection_policy", {}).get("config_file", {}).get("supported_sections"),
            ["mailbox_providers", "providers", "mailbox", "env"],
        )
        self.assertEqual(provider_filter.get("source"), "config_file")
        self.assertTrue(provider_filter.get("config_file", {}).get("enabled"))
        self.assertEqual(defaults.get("temp_mail_provider", {}).get("source"), "config_file")
        self.assertEqual(defaults.get("temp_mail_provider", {}).get("config_key"), "temp_mail_provider")
        self.assertEqual(defaults.get("pool_claim_provider", {}).get("source"), "config_file")
        self.assertEqual(defaults.get("pool_claim_provider", {}).get("config_key"), "pool_default_provider")

    def test_providers_api_reports_missing_config_file_without_failing_discovery(self):
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
                resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        selection_config = data["selection_policy"]["config_file"]
        diagnostics = data.get("provider_diagnostics") or {}
        defaults = diagnostics.get("defaults") or {}
        provider_filter = data.get("provider_filter") or {}

        self.assertTrue(selection_config["enabled"])
        self.assertFalse(selection_config["loaded"])
        self.assertEqual(selection_config["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertEqual(provider_filter["source"], "config_file_error")
        self.assertEqual(provider_filter["config_error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertEqual(defaults["temp_mail_provider"]["source"], "config_file_error")
        self.assertEqual(defaults["temp_mail_provider"]["config_error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")
        self.assertTrue(defaults["temp_mail_provider"]["valid"])
        self.assertEqual(defaults["pool_claim_provider"]["source"], "config_file_error")
        self.assertEqual(data["deployment_profile"]["config_file"]["error_code"], "PROVIDER_CONFIG_FILE_NOT_FOUND")

    def test_providers_api_reports_default_provider_entries_excluded_by_allowlist(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        client = self.app.test_client()
        self._login(client)

        with patch.dict(
            "os.environ",
            {
                "TEMP_MAIL_PROVIDER": "mail_tm",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "mail_tm",
            },
            clear=False,
        ):
            resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        diagnostics = resp.get_json().get("provider_diagnostics") or {}
        defaults = diagnostics.get("defaults") or {}
        temp_default = defaults.get("temp_mail_provider") or {}
        pool_default = defaults.get("pool_claim_provider") or {}
        inactive_defaults = defaults.get("inactive_defaults") or []

        self.assertTrue(temp_default.get("valid"))
        self.assertFalse(temp_default.get("active"))
        self.assertEqual(temp_default.get("inactive_reason"), "not_in_active_allowlist")
        self.assertTrue(pool_default.get("valid"))
        self.assertFalse(pool_default.get("active"))
        self.assertEqual(pool_default.get("inactive_reason"), "not_in_active_allowlist")
        self.assertEqual(
            {item.get("key"): item.get("provider") for item in inactive_defaults},
            {
                "TEMP_MAIL_PROVIDER": "mail_tm",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "mail_tm",
            },
        )
        self.assertEqual(diagnostics.get("summary", {}).get("inactive_default_entries"), 2)
        self.assertEqual(diagnostics.get("summary", {}).get("invalid_default_entries"), 0)

    def test_providers_api_does_not_report_auto_pool_default_as_inactive(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("active_mailbox_providers", "duckmail")

        client = self.app.test_client()
        self._login(client)

        with patch.dict(
            "os.environ",
            {
                "TEMP_MAIL_PROVIDER": "duckmail",
                "EXTERNAL_POOL_DEFAULT_PROVIDER": "auto",
            },
            clear=False,
        ):
            resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        diagnostics = resp.get_json().get("provider_diagnostics") or {}
        defaults = diagnostics.get("defaults") or {}
        pool_default = defaults.get("pool_claim_provider") or {}

        self.assertTrue(pool_default.get("valid"))
        self.assertTrue(pool_default.get("active"))
        self.assertEqual(pool_default.get("provider"), "auto")
        self.assertEqual(diagnostics.get("summary", {}).get("inactive_default_entries"), 0)

    def test_unified_mailbox_catalog_uses_plugin_label(self):
        with self.app.app_context():
            from mailops.services.provider_catalog import (
                get_mailbox_provider_catalog,
                get_mailbox_provider_deployment_profile,
            )
            from mailops.services.temp_mail_provider_base import _REGISTRY, register_provider

            @register_provider
            class FancyTempMail:
                provider_name = "fancy_temp_mail"
                provider_label = "Fancy Temp Mail"
                provider_version = "9.9.9"
                provider_author = "Tests"
                provider_capabilities = {"delete_mailbox": True, "delete_message": False, "clear_messages": False}
                config_schema = {
                    "fields": [
                        {
                            "key": "base_url",
                            "label": "Base URL",
                            "type": "text",
                            "required": True,
                            "default": "https://fancy.test",
                        },
                        {
                            "key": "api_key",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "default": "secret-default",
                        },
                    ]
                }

            try:
                catalog = get_mailbox_provider_catalog()
            finally:
                _REGISTRY.pop("fancy_temp_mail", None)

            plugin = next(item for item in catalog if item.get("provider") == "fancy_temp_mail")
            self.assertEqual(plugin["kind"], "temp")
            self.assertEqual(plugin["label"], "Fancy Temp Mail")
            self.assertEqual(plugin["config_source"], "plugin")
            self.assertTrue(plugin["can_delete_mailbox"])
            self.assertFalse(plugin["can_delete_message"])
            self.assertFalse(plugin["can_clear_messages"])
            self.assertFalse(plugin["configured"])
            self.assertEqual(plugin["missing_config"], ["plugin.fancy_temp_mail.base_url", "plugin.fancy_temp_mail.api_key"])
            self.assertEqual(plugin["selection"]["runtime_env"], {"TEMP_MAIL_PROVIDER": "fancy_temp_mail"})
            self.assertEqual(plugin["deployment"]["runtime_default"]["value"], "fancy_temp_mail")
            self.assertEqual(
                plugin["deployment"]["config_settings"]["keys"],
                ["plugin.fancy_temp_mail.base_url", "plugin.fancy_temp_mail.api_key"],
            )
            self.assertEqual(plugin["configuration"]["required_env"], [])
            self.assertEqual(
                plugin["configuration"]["settings_keys"], ["plugin.fancy_temp_mail.base_url", "plugin.fancy_temp_mail.api_key"]
            )
            self.assertEqual(
                plugin["configuration"]["required_settings"],
                ["plugin.fancy_temp_mail.base_url", "plugin.fancy_temp_mail.api_key"],
            )
            self.assertEqual(
                plugin["configuration"]["settings_defaults"], {"plugin.fancy_temp_mail.base_url": "https://fancy.test"}
            )
            self.assertNotIn("secret-default", str(plugin["deployment"]["config_settings"]["defaults"]))
            self.assertEqual(plugin["configuration"]["secret_settings"], ["plugin.fancy_temp_mail.api_key"])
            self.assertEqual(plugin["configuration"]["config_schema"]["fields"][0]["key"], "base_url")
            self.assertNotIn("default", plugin["configuration"]["config_schema"]["fields"][1])
            self.assertEqual(plugin["settings_ui"]["panel"], "schema")
            self.assertEqual(plugin["settings_ui"]["description"], "Third-party provider plugin")
            self.assertEqual(plugin["settings_ui"]["description_zh"], "第三方临时邮箱插件")
            self.assertEqual(plugin["settings_ui"]["aliases"], [])
            self.assertEqual(plugin["settings_ui"]["fields"][0]["key"], "base_url")
            self.assertNotIn("default", plugin["settings_ui"]["fields"][1])
            self.assertEqual(plugin["contract_validation"]["provider"], "fancy_temp_mail")
            self.assertEqual(plugin["contract_validation"]["status"], "invalid")
            self.assertIn(
                "CONFIG_FIELD_SECRET_DEFAULT",
                {issue["code"] for issue in plugin["contract_validation"]["issues"]},
            )
            self.assertNotIn("secret-default", str(plugin["contract_validation"]))
            deployment_profile = get_mailbox_provider_deployment_profile(catalog)
            self.assertIn("fancy_temp_mail", deployment_profile["provider_values"]["temp_runtime"])
            self.assertIn("plugin.fancy_temp_mail.api_key", deployment_profile["config_settings"]["secret"])
            self.assertNotIn("secret-default", str(deployment_profile["config_settings"]["defaults"]))
            self.assertEqual(
                deployment_profile["provider_examples"]["fancy_temp_mail"]["runtime_default"]["value"],
                "fancy_temp_mail",
            )

    def test_builtin_temp_provider_settings_ui_contract(self):
        with self.app.app_context():
            from mailops.services.provider_catalog import get_mailbox_provider_catalog

            catalog = get_mailbox_provider_catalog(include_inactive=True, strict=False)
            by_provider = {item["provider"]: item for item in catalog if item.get("kind") == "temp"}

            legacy = by_provider["legacy_bridge"]
            self.assertEqual(legacy["settings_ui"]["panel"], "schema")
            self.assertEqual(legacy["settings_ui"]["sort_order"], 10)
            self.assertEqual(
                set(legacy["settings_ui"]["aliases"]),
                {"gptmail", "legacy_gptmail", "temp_mail", "custom_domain_temp_mail"},
            )
            self.assertTrue(legacy["settings_ui"]["description"])
            self.assertTrue(legacy["settings_ui"]["description_zh"])
            legacy_field_keys = {field.get("key") for field in legacy["settings_ui"]["fields"]}
            self.assertIn("temp_mail_api_base_url", legacy_field_keys)
            self.assertIn("temp_mail_api_key", legacy_field_keys)
            self.assertIn("temp_mail_domains", legacy_field_keys)
            self.assertIn("temp_mail_prefix_rules", legacy_field_keys)

            cloudflare = by_provider["cloudflare_temp_mail"]
            self.assertEqual(cloudflare["settings_ui"]["panel"], "schema")
            self.assertEqual(cloudflare["settings_ui"]["sort_order"], 20)
            self.assertEqual(cloudflare["settings_ui"]["aliases"], [])
            cf_field_keys = {field.get("key") for field in cloudflare["settings_ui"]["fields"]}
            self.assertIn("cf_worker_base_url", cf_field_keys)
            self.assertIn("cf_worker_admin_key", cf_field_keys)
            self.assertIn("cf_worker_domains", cf_field_keys)
            self.assertTrue(
                any(
                    field.get("readonly")
                    for field in cloudflare["settings_ui"]["fields"]
                    if field.get("key") == "cf_worker_domains"
                )
            )
            actions = cloudflare["settings_ui"].get("actions") or []
            self.assertTrue(any(action.get("key") == "sync_domains" for action in actions))
            sync_action = next(action for action in actions if action.get("key") == "sync_domains")
            self.assertEqual(sync_action.get("endpoint"), "/api/settings/cf-worker-sync-domains")
            self.assertEqual(sync_action.get("method"), "POST")

            mail_tm = by_provider["mail_tm"]
            self.assertEqual(mail_tm["settings_ui"]["panel"], "schema")
            self.assertEqual(mail_tm["settings_ui"]["sort_order"], 30)
            self.assertEqual(mail_tm["settings_ui"]["fields"], [])

            duckmail = by_provider["duckmail"]
            self.assertEqual(duckmail["settings_ui"]["panel"], "schema")
            self.assertTrue(any(field.get("key") == "duckmail_bearer_token" for field in duckmail["settings_ui"]["fields"]))

    def test_plugin_schema_settings_round_trip_through_generic_settings_api(self):
        with self.app.app_context():
            from mailops.services.temp_mail_provider_base import _REGISTRY, register_provider

            @register_provider
            class GenericSettingsTempMail:
                provider_name = "generic_settings_temp_mail"
                provider_label = "Generic Settings Temp Mail"
                config_schema = {
                    "fields": [
                        {"key": "base_url", "label": "Base URL", "type": "url", "required": True},
                        {"key": "api_key", "label": "API Key", "type": "password", "required": True},
                    ]
                }

            client = self.app.test_client()
            self._login(client)
            try:
                response = client.put(
                    "/api/settings",
                    json={
                        "plugin.generic_settings_temp_mail.base_url": "https://generic.test",
                        "plugin.generic_settings_temp_mail.api_key": "generic-secret-value",
                    },
                )
                self.assertEqual(response.status_code, 200)

                settings = client.get("/api/settings").get_json()["settings"]
            finally:
                _REGISTRY.pop("generic_settings_temp_mail", None)

            self.assertEqual(settings["plugin.generic_settings_temp_mail.base_url"], "https://generic.test")
            self.assertTrue(settings["plugin.generic_settings_temp_mail.api_key_set"])
            self.assertNotEqual(settings["plugin.generic_settings_temp_mail.api_key_masked"], "generic-secret-value")
            self.assertNotIn("plugin.generic_settings_temp_mail.api_key", settings)

    def test_plugin_contract_validation_flows_into_provider_guide_and_manifest(self):
        with self.app.app_context():
            from mailops.services.provider_catalog import (
                get_external_integration_manifest,
                get_mailbox_provider_catalog,
                get_mailbox_provider_deployment_profile,
                get_mailbox_provider_selection_policy,
                get_provider_integration_guide,
            )
            from mailops.services.temp_mail_provider_base import _REGISTRY, TempMailProviderBase, register_provider
            from mailops.services.temp_mail_provider_factory import get_available_providers

            @register_provider
            class FlowContractTempMail(TempMailProviderBase):
                provider_name = "flow_contract_temp_mail"
                provider_label = "Flow Contract Temp Mail"
                provider_version = "1.0.0"
                provider_author = "Tests"
                config_schema = {"fields": [{"key": "base_url", "label": "Base URL", "type": "url"}]}

                def get_options(self):
                    return {"domains": []}

                def create_mailbox(self, *, prefix=None, domain=None):
                    return {"success": False}

                def delete_mailbox(self, mailbox):
                    return True

                def list_messages(self, mailbox):
                    return []

                def get_message_detail(self, mailbox, message_id):
                    return None

                def delete_message(self, mailbox, message_id):
                    return True

                def clear_messages(self, mailbox):
                    return True

            try:
                provider_info = next(item for item in get_available_providers() if item["name"] == "flow_contract_temp_mail")
                catalog = get_mailbox_provider_catalog(include_inactive=True, strict=False)
                catalog_item = next(item for item in catalog if item["provider"] == "flow_contract_temp_mail")
                deployment_profile = get_mailbox_provider_deployment_profile(catalog=catalog, strict=False)
                selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
                guide = get_provider_integration_guide(
                    catalog=catalog,
                    deployment_profile=deployment_profile,
                    selection_policy=selection_policy,
                )
                guide_item = next(item for item in guide["providers"] if item["provider"] == "flow_contract_temp_mail")
                manifest = get_external_integration_manifest(
                    deployment_profile=deployment_profile,
                    selection_policy=selection_policy,
                    provider_integration_guide=guide,
                )
                manifest_item = next(item for item in manifest["providers"] if item["provider"] == "flow_contract_temp_mail")
            finally:
                _REGISTRY.pop("flow_contract_temp_mail", None)

        self.assertEqual(provider_info["contract_validation"]["status"], "valid")
        self.assertEqual(catalog_item["contract_validation"]["status"], "valid")
        self.assertEqual(guide_item["contract_validation"]["status"], "valid")
        self.assertEqual(manifest_item["contract_validation"]["status"], "valid")
        self.assertEqual(
            manifest_item["contract_validation"]["summary"],
            guide_item["contract_validation"]["summary"],
        )

    def test_plugin_provider_default_health_check_does_not_claim_network_probe(self):
        with self.app.app_context():
            from mailops.services.provider_catalog import get_mailbox_provider_health
            from mailops.services.temp_mail_provider_base import _REGISTRY, TempMailProviderBase, register_provider

            @register_provider
            class HealthyOptionsTempMail(TempMailProviderBase):
                provider_name = "healthy_options_temp_mail"
                provider_label = "Healthy Options Temp Mail"
                provider_version = "1.0.0"
                provider_author = "Tests"

                def __init__(self, *, provider_name=None):
                    self.provider_name = provider_name or self.provider_name

                def get_options(self):
                    return {
                        "domain_strategy": "auto",
                        "default_mode": "auto",
                        "domains": [{"name": "plugin.test", "enabled": True, "is_default": True}],
                        "provider_name": self.provider_name,
                        "api_base_url": "https://plugin.test",
                    }

                def create_mailbox(self, *, prefix=None, domain=None):
                    return {"success": False}

                def delete_mailbox(self, mailbox):
                    return True

                def list_messages(self, mailbox):
                    return []

                def get_message_detail(self, mailbox, message_id):
                    return None

                def delete_message(self, mailbox, message_id):
                    return True

                def clear_messages(self, mailbox):
                    return True

            try:
                health = get_mailbox_provider_health("temp", "healthy_options_temp_mail", probe_network=True)
            finally:
                _REGISTRY.pop("healthy_options_temp_mail", None)

        self.assertTrue(health["local_ready"])
        self.assertTrue(health["probe"]["requested"])
        self.assertTrue(health["probe"]["ok"])
        self.assertFalse(health["probe"]["network_probe"])
        self.assertFalse(health["scope"]["network_probe"])
        self.assertEqual(health["probe"]["method"], "get_options")

    def test_provider_health_api_requires_login(self):
        client = self.app.test_client()

        resp = client.get("/api/providers/temp/mail_tm/health")

        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error", {}).get("code"), "AUTH_REQUIRED")

    def test_provider_health_api_reports_local_readiness_without_network_probe(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_bearer_token", "")

        client = self.app.test_client()
        self._login(client)

        with patch("mailops.services.temp_mail_provider_factory.get_temp_mail_provider") as provider_factory:
            resp = client.get("/api/providers/temp/duckmail/health")

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_not_called()
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        health = data.get("provider_health") or {}
        self.assertEqual(health.get("kind"), "temp")
        self.assertEqual(health.get("provider"), "duckmail")
        self.assertFalse(health.get("local_ready"))
        self.assertEqual(health.get("local_status"), "needs_config")
        self.assertEqual(health.get("missing_config"), ["duckmail_bearer_token"])
        self.assertFalse((health.get("probe") or {}).get("requested"))
        self.assertEqual((health.get("probe") or {}).get("status"), "not_requested")

    def test_provider_health_api_runs_explicit_probe_and_keeps_payload_sanitized(self):
        client = self.app.test_client()
        self._login(client)

        with patch(
            "mailops.services.temp_mail_provider_factory.get_temp_mail_provider",
            return_value=_HealthCheckTempMailProvider("mail_tm"),
        ) as provider_factory:
            resp = client.get("/api/providers/temp/mail_tm/health?probe_network=true")

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_called_once_with("mail_tm")
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        health = data.get("provider_health") or {}
        probe = health.get("probe") or {}
        self.assertTrue(health.get("local_ready"))
        self.assertTrue(probe.get("requested"))
        self.assertTrue(probe.get("network_probe"))
        self.assertTrue(probe.get("ok"))
        self.assertEqual(probe.get("method"), "mock_health_check")
        self.assertEqual(probe.get("details", {}).get("domain_count"), 1)
        self.assertNotIn("bearer_token", probe.get("details") or {})
        self.assertEqual(probe.get("details", {}).get("diagnostic_text"), "[redacted]")
        self.assertEqual(probe.get("details", {}).get("nested"), {"message": "[redacted]", "safe": "ok"})
        self.assertNotIn("should-not-leak", str(data))
        self.assertNotIn("secret-pass", str(data))
        self.assertNotIn("rt-secret", str(data))
        self.assertNotIn("client-secret-value", str(data))

    def test_provider_health_api_returns_404_for_unknown_provider(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/providers/temp/not_a_provider/health")

        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error", {}).get("code"), "MAILBOX_PROVIDER_NOT_FOUND")

    def test_provider_preflight_api_requires_login(self):
        client = self.app.test_client()

        resp = client.get("/api/providers/preflight")

        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error", {}).get("code"), "AUTH_REQUIRED")

    def test_provider_preflight_api_reports_batch_local_readiness_without_network_probe(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo

            settings_repo.set_setting("duckmail_bearer_token", "")

        client = self.app.test_client()
        self._login(client)

        with patch("mailops.services.temp_mail_provider_factory.get_temp_mail_provider") as provider_factory:
            resp = client.get("/api/providers/preflight")

        self.assertEqual(resp.status_code, 200)
        provider_factory.assert_not_called()
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        preflight = data.get("provider_preflight") or {}
        self.assertEqual(preflight.get("version"), 1)
        self.assertEqual(
            preflight.get("endpoints", {}).get("provider_preflight"), f"{CANONICAL_EXTERNAL_PREFIX}/providers/preflight"
        )
        self.assertEqual(
            preflight.get("endpoints", {}).get("provider_health"),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health",
        )
        self.assertFalse(preflight.get("scope", {}).get("network_probe"))
        rows = {(item.get("kind"), item.get("provider")): item for item in preflight.get("providers") or []}
        duckmail = rows[("temp", "duckmail")]
        self.assertFalse(duckmail.get("local_ready"))
        self.assertEqual(duckmail.get("local_status"), "needs_config")
        self.assertEqual(duckmail.get("missing_config"), ["duckmail_bearer_token"])
        self.assertFalse(duckmail.get("probe", {}).get("requested"))
        self.assertEqual(duckmail.get("probe", {}).get("status"), "not_requested")
        self.assertNotRegex(json.dumps(preflight, ensure_ascii=False), r"dk_[0-9a-fA-F]{20,}")
        self.assertNotIn("should-not-leak", json.dumps(preflight, ensure_ascii=False))

    def test_provider_preflight_api_runs_explicit_probe_and_keeps_payload_sanitized(self):
        client = self.app.test_client()
        self._login(client)

        with patch(
            "mailops.services.temp_mail_provider_factory.get_temp_mail_provider",
            return_value=_HealthCheckTempMailProvider("mail_tm"),
        ) as provider_factory:
            resp = client.get("/api/providers/preflight?probe_network=true")

        self.assertEqual(resp.status_code, 200)
        probed_provider_names = [call.args[0] for call in provider_factory.call_args_list]
        self.assertIn("mail_tm", probed_provider_names)
        preflight = resp.get_json().get("provider_preflight") or {}
        self.assertGreaterEqual((preflight.get("summary") or {}).get("probed", 0), 1)
        self.assertEqual((preflight.get("summary") or {}).get("probe_failed"), 0)
        rows = {(item.get("kind"), item.get("provider")): item for item in preflight.get("providers") or []}
        outlook = rows[("account", "outlook")]
        self.assertFalse((outlook.get("probe") or {}).get("requested"))
        self.assertEqual((outlook.get("probe") or {}).get("status"), "not_requested")
        mail_tm = rows[("temp", "mail_tm")]
        probe = mail_tm.get("probe") or {}
        self.assertTrue(probe.get("requested"))
        self.assertTrue(probe.get("network_probe"))
        self.assertTrue(probe.get("ok"))
        self.assertEqual(probe.get("method"), "mock_health_check")
        self.assertEqual(probe.get("details", {}).get("diagnostic_text"), "[redacted]")
        self.assertNotIn("bearer_token", probe.get("details") or {})
        payload_text = json.dumps(preflight, ensure_ascii=False)
        self.assertNotIn("should-not-leak", payload_text)
        self.assertNotIn("secret-pass", payload_text)
        self.assertNotIn("rt-secret", payload_text)
        self.assertNotIn("client-secret-value", payload_text)

    def test_external_api_capabilities_contract_uses_current_consumer_and_settings(self):
        with self.app.app_context():
            from mailops.repositories import settings as settings_repo
            from mailops.services.mailbox_directory_contract import get_mailbox_catalog_contract
            from mailops.services.provider_catalog import get_external_api_capabilities_contract

            settings_repo.set_setting("pool_external_enabled", "true")
            settings_repo.set_setting("external_api_public_mode", "true")
            settings_repo.set_setting("external_api_disable_pool_claim_random", "true")
            expected_contract = get_mailbox_catalog_contract()

            contract = get_external_api_capabilities_contract(consumer={"is_legacy": False, "pool_access": False})

        self.assertTrue(contract["public_mode"])
        self.assertFalse(contract["pool"]["current_consumer_has_access"])
        self.assertIn("pool_access_required", contract["restricted_features"])
        self.assertIn("pool_claim_random_disabled", contract["pool"]["restrictions"])
        self.assertIn("provider_health", contract["features"])
        self.assertIn("mailbox_directory", contract["features"])
        self.assertEqual(contract["endpoints"]["mailboxes"], f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes")
        self.assertEqual(contract["endpoints"]["providers"], f"{CANONICAL_EXTERNAL_PREFIX}/providers")
        self.assertEqual(
            contract["endpoints"]["provider_health"], f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health"
        )
        self.assertEqual(contract["mailbox_directory"]["endpoint"], f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes")
        self.assertEqual(contract["mailbox_directory"]["response_contract"], "unified_mailbox_directory")
        self.assertEqual(contract["mailbox_directory"]["contract"]["filters"]["kind"], expected_contract["filters"]["kind"])
        self.assertEqual(
            contract["mailbox_directory"]["quick_view_presets"],
            expected_contract["quick_view_presets"],
        )
        self.assertEqual(
            [item["key"] for item in contract["mailbox_directory"]["summary_fields"]],
            [item["key"] for item in expected_contract["summary_fields"]],
        )
        self.assertEqual(
            contract["deployment_env"],
            {
                "active_mailbox_providers": "ACTIVE_MAILBOX_PROVIDERS",
                "pool_claim_provider": "EXTERNAL_POOL_DEFAULT_PROVIDER",
                "temp_mail_provider": "TEMP_MAIL_PROVIDER",
            },
        )
        self.assertEqual(contract["deployment_profile"]["env"], contract["deployment_env"])
        self.assertEqual(
            contract["selection_policy"]["source_priority"], ["env", "provider_config_file", "settings", "default"]
        )
        self.assertEqual(
            contract["selection_policy"]["scopes"]["explicit_pool_claim"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-random",
        )
        self.assertIn("duckmail", contract["deployment_profile"]["provider_values"]["temp_apply"])
        self.assertIn("DUCKMAIL_BEARER_TOKEN", contract["deployment_profile"]["config_env"]["secret"])
        self.assertEqual(contract["provider_diagnostics"]["scope"]["type"], "local_config")
        self.assertIn("summary", contract["provider_diagnostics"])
        self.assertNotIn("providers", contract["provider_diagnostics"])
        self.assertEqual(contract["external_mailbox_read_contract"]["read_by"], ["email", "claim_token"])
        self.assertEqual(
            contract["pool"]["read_contract"]["next_actions"]["complete_claim"]["endpoint"],
            f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-complete",
        )

    def test_provider_folder_candidates_contains_utf7_for_qq_junk(self):
        from mailops.services.providers import get_imap_folder_candidates

        candidates = get_imap_folder_candidates("qq", "junkemail")
        self.assertIn("&V4NXPpCuTvY-", candidates)

        default_candidates = get_imap_folder_candidates("unknown", "inbox")
        self.assertIn("INBOX", default_candidates)

    def test_import_imap_qq_stores_encrypted_password_and_imap_fields(self):
        client = self.app.test_client()
        self._login(client)

        unique = uuid.uuid4().hex
        email_addr = f"qq_{unique}@qq.com"
        imap_pwd = f"auth_{unique}"

        resp = client.post(
            "/api/accounts",
            json={
                "provider": "qq",
                "account_string": f"{email_addr}----{imap_pwd}",
                "group_id": self._default_group_id(),
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("success"), True)

        conn = self.module.create_sqlite_connection()
        try:
            row = conn.execute(
                """
                SELECT account_type, provider, imap_host, imap_port, imap_password, client_id, refresh_token
                FROM accounts
                WHERE email = ?
                LIMIT 1
                """,
                (email_addr,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["account_type"], "imap")
        self.assertEqual(row["provider"], "qq")
        self.assertEqual(row["imap_host"], "imap.qq.com")
        self.assertEqual(int(row["imap_port"]), 993)
        self.assertEqual(row["client_id"], "")
        self.assertEqual(row["refresh_token"], "")

        stored_imap_pwd = row["imap_password"]
        self.assertTrue(stored_imap_pwd)
        self.assertNotEqual(stored_imap_pwd, imap_pwd)
        self.assertTrue(stored_imap_pwd.startswith("enc:"))

    def test_emails_api_routes_to_imap_generic_by_account_type(self):
        client = self.app.test_client()
        self._login(client)

        unique = uuid.uuid4().hex
        email_addr = f"imap_{unique}@example.com"

        encrypted_pwd = self.module.encrypt_data("pw_" + unique)

        conn = self.module.create_sqlite_connection()
        try:
            conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, imap_host, imap_port, imap_password, group_id, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email_addr,
                    "",
                    "",
                    "",
                    "imap",
                    "qq",
                    "imap.qq.com",
                    993,
                    encrypted_pwd,
                    self._default_group_id(),
                    "",
                    "active",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        fake_result = {
            "success": True,
            "emails": [
                {
                    "id": "1",
                    "subject": "s",
                    "from": "f",
                    "date": "d",
                    "is_read": True,
                    "has_attachments": False,
                    "body_preview": "p",
                }
            ],
            "method": "IMAP (Generic)",
            "has_more": False,
        }

        with patch(
            "mailops.controllers.emails.get_emails_imap_generic",
            return_value=fake_result,
        ):
            resp = client.get(f"/api/emails/{email_addr}?folder=inbox&skip=0&top=20")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), fake_result)

        delete_resp = client.post("/api/emails/delete", json={"email": email_addr, "ids": ["1"]})
        self.assertEqual(delete_resp.status_code, 400)
        delete_data = delete_resp.get_json()
        self.assertEqual(delete_data.get("success"), False)
        err = delete_data.get("error") or {}
        self.assertIsInstance(err, dict)
        self.assertIn("不支持远程删除", err.get("message", ""))

    def test_imap_generic_connect_error_does_not_leak_password(self):
        from mailops.services.imap_generic import get_emails_imap_generic

        secret_pwd = "top-secret-imap-password"
        result = get_emails_imap_generic(
            email_addr="u@example.com",
            imap_password=secret_pwd,
            imap_host="",  # 触发 ValueError -> connect failed
            imap_port=993,
            folder="inbox",
            provider="qq",
            skip=0,
            top=1,
        )
        self.assertEqual(result.get("success"), False)
        self.assertEqual(result.get("error_code"), "IMAP_CONNECT_FAILED")

        # 确保返回内容不包含明文密码
        self.assertNotIn(secret_pwd, str(result))

    def test_scheduler_skips_imap_accounts(self):
        from mailops.services.scheduler import scheduled_refresh_task

        unique = uuid.uuid4().hex
        outlook_email = f"out_{unique}@outlook.com"
        imap_email = f"imap_{unique}@example.com"

        conn = self.module.create_sqlite_connection()
        try:
            conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outlook_email,
                    "",
                    "client_" + unique,
                    self.module.encrypt_data("rt_" + unique),
                    "outlook",
                    "outlook",
                    self._default_group_id(),
                    "",
                    "active",
                ),
            )
            conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, imap_host, imap_port, imap_password, group_id, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    imap_email,
                    "",
                    "",
                    "",
                    "imap",
                    "qq",
                    "imap.qq.com",
                    993,
                    self.module.encrypt_data("pw_" + unique),
                    self._default_group_id(),
                    "",
                    "active",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        called = []

        def fake_test_refresh_token(client_id, refresh_token, proxy_url):
            called.append((client_id, refresh_token, proxy_url))
            return True, "ok", "rt_new_" + unique

        with (
            patch("mailops.services.scheduler.time.sleep", return_value=None),
            patch(
                "mailops.services.scheduler.acquire_distributed_lock",
                return_value=(True, {}),
            ),
            patch("mailops.services.scheduler.release_distributed_lock", return_value=None),
        ):
            scheduled_refresh_task(self.app, fake_test_refresh_token)

        self.assertGreaterEqual(len(called), 1)
        self.assertTrue(any(cid == "client_" + unique for cid, _, _ in called))
        self.assertFalse(any(cid == "" for cid, _, _ in called))  # 不应包含 IMAP 账号（空 client_id）

        # 成功刷新时应写回滚动更新后的 refresh_token（加密存储）
        conn = self.module.create_sqlite_connection()
        try:
            row = conn.execute(
                "SELECT refresh_token, last_refresh_at FROM accounts WHERE email = ?", (outlook_email,)
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(self.module.decrypt_data(row["refresh_token"]), "rt_new_" + unique)
            self.assertTrue(row["last_refresh_at"])
        finally:
            conn.close()

    def test_export_format_outlook_first_then_imap_grouped(self):
        client = self.app.test_client()
        self._login(client)

        unique = uuid.uuid4().hex
        outlook_email = f"exp_out_{unique}@outlook.com"
        imap_email = f"exp_qq_{unique}@qq.com"

        conn = self.module.create_sqlite_connection()
        try:
            conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, group_id, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outlook_email,
                    self.module.encrypt_data("p_" + unique),
                    "cid_" + unique,
                    self.module.encrypt_data("rt_" + unique),
                    "outlook",
                    "outlook",
                    self._default_group_id(),
                    "",
                    "active",
                ),
            )
            conn.execute(
                """
                INSERT INTO accounts (email, password, client_id, refresh_token, account_type, provider, imap_host, imap_port, imap_password, group_id, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    imap_email,
                    "",
                    "",
                    "",
                    "imap",
                    "qq",
                    "imap.qq.com",
                    993,
                    self.module.encrypt_data("imap_pw_" + unique),
                    self._default_group_id(),
                    "",
                    "active",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        verify = client.post("/api/export/verify", json={"password": "testpass123"})
        self.assertEqual(verify.status_code, 200)
        verify_data = verify.get_json()
        self.assertEqual(verify_data.get("success"), True)
        token = verify_data.get("verify_token")
        self.assertTrue(token)

        export_resp = client.get("/api/accounts/export", headers={"X-Export-Token": token})
        self.assertEqual(export_resp.status_code, 200)
        content = export_resp.get_data(as_text=True)

        outlook_pos = content.find("# === Outlook 账号 ===")
        imap_pos = content.find("# === IMAP 账号（QQ 邮箱）===")
        self.assertNotEqual(outlook_pos, -1)
        self.assertNotEqual(imap_pos, -1)
        self.assertLess(outlook_pos, imap_pos)

        self.assertIn(outlook_email, content)
        self.assertIn(imap_email, content)
        self.assertIn("----qq", content)  # IMAP 行格式：email----imap_password----provider
