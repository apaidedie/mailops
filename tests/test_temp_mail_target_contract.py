from __future__ import annotations

from tests.frontend_js_bundle import load_feature_package_js,  load_frontend_app_js
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._import_app import clear_login_attempts, import_web_app_module


class TempMailTargetContractTests(unittest.TestCase):
    """
    这组测试用于固定 TDD 中的目标契约。
    已落地的契约应直接转成正式通过，剩余未完成项再继续补。
    """

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
            db.execute("DELETE FROM external_probe_cache")
            db.execute("DELETE FROM external_api_keys")
            db.execute("DELETE FROM temp_email_messages WHERE email_address LIKE '%@test.example'")
            db.execute("DELETE FROM temp_emails WHERE email LIKE '%@test.example'")
            db.commit()
            settings_repo.set_setting("external_api_key", "contract-key")
            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("temp_mail_api_base_url", "")
            settings_repo.set_setting("temp_mail_api_key", "")
            settings_repo.set_setting("gptmail_api_key", "")
            settings_repo.set_setting("temp_mail_domains", "[]")
            settings_repo.set_setting("temp_mail_default_domain", "")
            settings_repo.set_setting("temp_mail_prefix_rules", "{}")

    def _login(self, client):
        resp = client.post("/login", json={"password": "testpass123"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def _get_text(self, client, path: str) -> str:
        resp = client.get(path)
        try:
            self.assertEqual(resp.status_code, 200)
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    def test_temp_email_options_endpoint_returns_domain_and_prefix_rules(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.get("/api/temp-emails/options")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("options", data)
        self.assertEqual(data["options"]["domain_strategy"], "auto_or_manual")
        self.assertIn("domains", data["options"])
        self.assertIn("prefix_rules", data["options"])

    def test_temp_email_extract_verification_endpoint_returns_code_and_link(self):
        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="demo123@test.example",
                mailbox_type="user",
                visible_in_ui=True,
                source="custom_domain_temp_mail",
            )
            temp_emails_repo.save_temp_email_messages(
                "demo123@test.example",
                [
                    {
                        "id": "msg-1",
                        "from_address": "noreply@example.com",
                        "subject": "Verify your account",
                        "content": "Code: 123456 https://verify.example/link",
                        "html_content": "",
                        "timestamp": 1711111111,
                    }
                ],
            )

        client = self.app.test_client()
        self._login(client)
        with patch(
            "outlook_web.services.gptmail.gptmail_request",
            side_effect=[
                {
                    "success": True,
                    "data": {
                        "emails": [
                            {
                                "id": "msg-1",
                                "from_address": "noreply@example.com",
                                "subject": "Verify your account",
                                "content": "Code: 123456 https://verify.example/link",
                                "html_content": "",
                                "timestamp": 1711111111,
                            }
                        ]
                    },
                },
                {
                    "success": True,
                    "data": {
                        "id": "msg-1",
                        "from_address": "noreply@example.com",
                        "subject": "Verify your account",
                        "content": "Code: 123456 https://verify.example/link",
                        "html_content": "",
                        "timestamp": 1711111111,
                    },
                },
            ],
        ):
            resp = client.get("/api/temp-emails/demo123@test.example/extract-verification")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        self.assertIn("verification_code", data["data"])
        self.assertIn("verification_link", data["data"])
        self.assertIn("formatted", data["data"])

    def test_external_apply_endpoint_returns_hidden_task_mailbox(self):
        client = self.app.test_client()

        with patch("outlook_web.services.gptmail.generate_temp_email", return_value=("demo123@test.example", None)):
            resp = client.post(
                "/api/v1/external/temp-emails/apply",
                headers={"X-API-Key": "contract-key"},
                json={
                    "caller_id": "register-worker-1",
                    "task_id": "job-001",
                    "prefix": "demo123",
                    "domain": "test.example",
                },
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["code"], "OK")
        self.assertIn("data", data)
        self.assertIn("email", data["data"])
        self.assertIn("task_token", data["data"])
        self.assertEqual(data["data"]["visible_in_ui"], False)

    def test_external_finish_endpoint_marks_task_mailbox_finished(self):
        with self.app.app_context():
            from outlook_web.repositories import temp_emails as temp_emails_repo

            temp_emails_repo.create_temp_email(
                email_addr="finish@test.example",
                mailbox_type="task",
                visible_in_ui=False,
                source="custom_domain_temp_mail",
                task_token="tmptask_demo",
                consumer_key="legacy:settings.external_api_key",
                caller_id="worker",
                task_id="job-001",
            )

        client = self.app.test_client()

        resp = client.post(
            "/api/v1/external/temp-emails/tmptask_demo/finish",
            headers={"X-API-Key": "contract-key"},
            json={"result": "success", "detail": "done"},
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["task_token"], "tmptask_demo")
        self.assertEqual(data["data"]["status"], "finished")

    def test_settings_get_returns_temp_mail_contract_fields(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_provider", "custom_domain_temp_mail")
            settings_repo.set_setting("temp_mail_api_base_url", "https://temp.example")
            settings_repo.set_setting("temp_mail_api_key", "temp-mail-secret")
            settings_repo.set_setting(
                "temp_mail_domains",
                '[{"name":"mail.example.com","enabled":true},{"name":"temp.example.net","enabled":true}]',
            )
            settings_repo.set_setting("temp_mail_default_domain", "mail.example.com")
            settings_repo.set_setting(
                "temp_mail_prefix_rules",
                '{"min_length":2,"max_length":24,"pattern":"^[a-z0-9-]+$"}',
            )

        client = self.app.test_client()
        self._login(client)
        resp = client.get("/api/settings")

        self.assertEqual(resp.status_code, 200)
        settings = resp.get_json()["settings"]
        self.assertEqual(settings["temp_mail_provider"], "custom_domain_temp_mail")
        self.assertEqual(settings["temp_mail_api_base_url"], "https://temp.example")
        self.assertTrue(settings["temp_mail_api_key_set"])
        self.assertTrue(settings["temp_mail_api_key_masked"])
        self.assertNotIn("gptmail_api_key_set", settings)
        self.assertNotIn("gptmail_api_key_masked", settings)
        self.assertNotEqual(settings["temp_mail_api_key_masked"], "temp-mail-secret")
        self.assertEqual(
            settings["temp_mail_domains"],
            [
                {"name": "mail.example.com", "enabled": True},
                {"name": "temp.example.net", "enabled": True},
            ],
        )
        self.assertEqual(settings["temp_mail_default_domain"], "mail.example.com")
        self.assertEqual(
            settings["temp_mail_prefix_rules"],
            {"min_length": 2, "max_length": 24, "pattern": "^[a-z0-9-]+$"},
        )

    def test_settings_put_persists_temp_mail_contract_fields(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put(
            "/api/settings",
            json={
                "temp_mail_provider": "custom_domain_temp_mail",
                "temp_mail_api_base_url": "https://bridge.example",
                "temp_mail_api_key": "new-temp-secret",
                "temp_mail_domains": [
                    {"name": "mail.example.com", "enabled": True},
                    {"name": "temp.example.net", "enabled": False},
                ],
                "temp_mail_default_domain": "mail.example.com",
                "temp_mail_prefix_rules": {
                    "min_length": 3,
                    "max_length": 18,
                    "pattern": "^[a-z][a-z0-9._-]*$",
                },
            },
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_provider"), "custom_domain_temp_mail")
            self.assertEqual(settings_repo.get_setting("temp_mail_api_base_url"), "https://bridge.example")
            self.assertEqual(settings_repo.get_setting("temp_mail_api_key"), "new-temp-secret")
            self.assertEqual(settings_repo.get_setting("gptmail_api_key"), "new-temp-secret")
            self.assertEqual(
                settings_repo.get_temp_mail_domains(),
                [
                    {"name": "mail.example.com", "enabled": True},
                    {"name": "temp.example.net", "enabled": False},
                ],
            )
            self.assertEqual(settings_repo.get_temp_mail_default_domain(), "mail.example.com")
            self.assertEqual(
                settings_repo.get_temp_mail_prefix_rules(),
                {"min_length": 3, "max_length": 18, "pattern": "^[a-z][a-z0-9._-]*$"},
            )

    def test_settings_put_normalizes_gptmail_docs_page_base_url(self):
        client = self.app.test_client()
        self._login(client)

        resp = client.put(
            "/api/settings",
            json={"temp_mail_api_base_url": "https://mail.chatgpt.org.uk/zh/api/"},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_api_base_url"), "https://mail.chatgpt.org.uk")
            self.assertEqual(settings_repo.get_temp_mail_api_base_url(), "https://mail.chatgpt.org.uk")

    def test_settings_masked_temp_mail_api_key_placeholder_does_not_overwrite(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_api_key", "keep-this-secret")

        client = self.app.test_client()
        self._login(client)
        masked = client.get("/api/settings").get_json()["settings"]["temp_mail_api_key_masked"]

        resp = client.put("/api/settings", json={"temp_mail_api_key": masked, "temp_mail_provider": "custom_domain_temp_mail"})
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_api_key"), "keep-this-secret")

    def test_settings_legacy_gptmail_api_key_still_reads_into_temp_contract_fields(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_api_key", "")
            settings_repo.set_setting("gptmail_api_key", "legacy-only-secret")

        client = self.app.test_client()
        self._login(client)
        resp = client.get("/api/settings")

        self.assertEqual(resp.status_code, 200)
        settings = resp.get_json()["settings"]
        self.assertTrue(settings["temp_mail_api_key_set"])
        self.assertTrue(settings["temp_mail_api_key_masked"])
        self.assertNotEqual(settings["temp_mail_api_key_masked"], "legacy-only-secret")

    def test_settings_legacy_gptmail_api_key_put_does_not_reverse_pollute_temp_mail_api_key(self):
        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            settings_repo.set_setting("temp_mail_api_key", "formal-secret")
            settings_repo.set_setting("gptmail_api_key", "legacy-secret")

        client = self.app.test_client()
        self._login(client)
        resp = client.put("/api/settings", json={"gptmail_api_key": "legacy-updated"})

        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            from outlook_web.repositories import settings as settings_repo

            self.assertEqual(settings_repo.get_setting("temp_mail_api_key"), "formal-secret")
            self.assertEqual(settings_repo.get_setting("gptmail_api_key"), "legacy-updated")

    def test_temp_emails_schema_supports_visibility_and_task_ownership_fields(self):
        with self.app.app_context():
            from outlook_web.db import get_db

            db = get_db()
            rows = db.execute("PRAGMA table_info(temp_emails)").fetchall()

        columns = {row["name"] for row in rows}
        self.assertIn("mailbox_type", columns)
        self.assertIn("visible_in_ui", columns)
        self.assertIn("source", columns)
        self.assertIn("prefix", columns)
        self.assertIn("domain", columns)
        self.assertIn("task_token", columns)
        self.assertIn("consumer_key", columns)
        self.assertIn("caller_id", columns)
        self.assertIn("task_id", columns)
        self.assertIn("finished_at", columns)

    def test_temp_email_frontend_references_options_endpoint(self):
        client = self.app.test_client()
        self._login(client)
        js = load_feature_package_js('static/js/features/temp_emails')
        self.assertIn("/api/temp-emails/options", js)
        self.assertIn("tempEmailOptionsStatus", self._get_text(client, "/"))
        self.assertIn("域名配置加载失败", js)
        self.assertIn("status: 'error'", js)

    def test_temp_email_frontend_displays_provider_config_status(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")
        main_js = load_frontend_app_js()
        temp_js = load_feature_package_js('static/js/features/temp_emails')

        self.assertIn('id="tempEmailProviderStatus"', index_html)
        self.assertIn("getMailboxProviderCatalogItem", main_js)
        self.assertIn("renderTempEmailProviderStatus", temp_js)
        self.assertIn("getTempEmailProviderDisplayLabel", temp_js)
        self.assertIn("resolveMailboxProviderLabel", temp_js)
        self.assertIn("缺配置", temp_js)
        self.assertIn("syncTempEmailProviderSelection", temp_js)
        self.assertIn("正在读取域名配置", temp_js)
        self.assertNotIn('id="tempEmailProviderSelect" onchange=', index_html)
        # Status badge paint only on temp-emails page (catalog soft re-entry safe).
        status_start = temp_js.index("function renderTempEmailProviderStatus")
        status_end = temp_js.index("function getTempEmailProviderDisplayLabel", status_start) if "function getTempEmailProviderDisplayLabel" in temp_js[status_start:] else temp_js.index("function syncTempEmailProviderSelection", status_start)
        status_slice = temp_js[status_start:status_end]
        self.assertIn("isCurrentTempEmailsPage()", status_slice)
        self.assertIn("currentPage !== 'temp-emails'", status_slice)
        # Catalog success only paints status when already on temp-emails page.
        catalog_start = main_js.index("async function loadMailboxProviderCatalog")
        catalog_success = main_js[catalog_start:catalog_start + 5000]
        self.assertIn("currentPage === 'temp-emails'", catalog_success)
        self.assertIn("renderTempEmailProviderStatus()", catalog_success)

    def test_temp_email_provider_select_is_catalog_driven(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")
        main_js = load_frontend_app_js()
        temp_js = load_feature_package_js('static/js/features/temp_emails')
        plugins_js = self._get_text(client, "/static/js/features/plugins.js")

        self.assertIn('id="tempEmailProviderSelect"', index_html)
        self.assertIn("function getTempEmailProviderCatalogOptions", main_js)
        self.assertIn("function syncTempEmailProviderSelectWithCatalog", main_js)
        self.assertIn("kind !== 'temp' || !provider || provider === 'auto'", main_js)
        self.assertIn("seen.has(provider)", main_js)
        self.assertIn("option.dataset.providerCatalog = '1';", main_js)
        self.assertIn("removeDuplicateTempEmailProviderOptions(select, previousValue);", main_js)
        self.assertIn("previousValue && findTempEmailProviderOption(select, previousValue)", main_js)
        self.assertIn("syncTempEmailProviderSelectWithCatalog();", main_js)
        # Catalog soft re-entry must not rewrite hidden create-temp select off that page.
        sync_start = main_js.index("function syncTempEmailProviderSelectWithCatalog()")
        sync_end = main_js.index("async function loadMailboxProviderCatalog", sync_start)
        sync_slice = main_js[sync_start:sync_end]
        self.assertIn("currentPage !== 'temp-emails'", sync_slice)
        self.assertIn("getMailboxProviderCatalogItem(providerName, 'temp')", temp_js)
        self.assertIn("catalogItem.label || catalogItem.provider_label", temp_js)
        # Prefer shared catalog label helper when main.js has loaded /api/providers.
        self.assertIn("function getTempEmailProviderDisplayLabel", temp_js)
        self.assertIn("resolveMailboxProviderLabel", temp_js)
        self.assertIn("const existing = Array.from(sel.options).find(opt => opt.value === p.name);", plugins_js)
        self.assertIn("existing.setAttribute('data-plugin', p.name);", plugins_js)
        # Plugin list load soft-refreshes catalog; lifecycle mutations can force-refresh.
        self.assertIn("async function _refreshMailboxProviderCatalogFromPlugins", plugins_js)
        self.assertIn("await loadMailboxProviderCatalog(Boolean(forceRefresh || emptyWarmCache))", plugins_js)
        self.assertIn("await _refreshMailboxProviderCatalogFromPlugins(forceCatalogRefresh)", plugins_js)
        self.assertIn("loadPlugins({ forceCatalogRefresh: true })", plugins_js)
        self.assertIn("loadPlugins({ forceCatalogRefresh: false })", plugins_js)
        # Boot must not eagerly fetch /api/plugins; temp-mail tab/card expand loads on demand.
        self.assertIn("async function ensureLoaded", plugins_js)
        self.assertIn("Intentionally do not fetch /api/plugins on every page boot", plugins_js)
        self.assertIn("temp-mail Settings tab", plugins_js)
        self.assertIn("let _pluginsLoaded = false", plugins_js)
        self.assertIn("_pluginsLoaded = true", plugins_js)
        self.assertIn("_pluginsLoadPromise", plugins_js)
        self.assertIn("let _pluginsLoadForce = false", plugins_js)
        self.assertIn("if (!forceReload || _pluginsLoadForce)", plugins_js)
        self.assertIn("_pluginsLoadForce = forceReload", plugins_js)
        self.assertIn("_pluginsLoadPromise !== request", plugins_js)
        self.assertIn("_pluginsLoaded && opts.force !== true", plugins_js)
        # Soft loadPlugins re-entry returns warm list without network / loading flash.
        load_start = plugins_js.index("async function loadPlugins(options = {})")
        load_end = plugins_js.index("function _renderPluginList", load_start)
        load_slice = plugins_js[load_start:load_end]
        self.assertIn("if (!forceReload && _pluginsLoaded)", load_slice)
        self.assertIn("_renderPluginList(installedCount)", load_slice)
        # Paint list chrome only when plugin manager card is expanded.
        self.assertIn("function shouldPaintPluginList()", plugins_js)
        self.assertIn("shouldPaintPluginList()", load_slice)
        self.assertIn("if (content && shouldPaintPluginList())", load_slice)
        warm_idx = load_slice.index("if (!forceReload && _pluginsLoaded)")
        promise_idx = load_slice.index("if (_pluginsLoadPromise)")
        self.assertLess(warm_idx, promise_idx)
        self.assertLess(warm_idx, load_slice.index("content.innerHTML"))
        # Soft ensureLoaded re-paints warm list when plugin card re-opens (no second GET).
        ensure_start = plugins_js.index("async function ensureLoaded(options = {})")
        ensure_end = plugins_js.index("// ── Public API", ensure_start) if "// ── Public API" in plugins_js[ensure_start:] else plugins_js.index("return {", ensure_start)
        ensure_slice = plugins_js[ensure_start:ensure_end]
        self.assertIn("shouldPaintPluginList()", ensure_slice)
        self.assertIn("_renderPluginList(installedCount)", ensure_slice)
        self.assertIn("status === 'installed'", ensure_slice)
        # Language change soft-paints warm plugin list without network.
        self.assertIn("window.addEventListener('ui-language-changed'", plugins_js)
        self.assertIn("softPaintOnLanguageChange", plugins_js)
        self.assertIn("function plT(text)", plugins_js)
        self.assertIn("window.translateAppText(text)", plugins_js)
        lang_start = plugins_js.index("window.addEventListener('ui-language-changed'")
        lang_slice = plugins_js[lang_start:lang_start + 500]
        self.assertIn("softPaintOnLanguageChange()", lang_slice)
        self.assertNotIn("loadPlugins({ force: true })", lang_slice)
        # Provider config panel chrome translates at paint time; language soft re-paints open form.
        self.assertIn("plT('插件 Provider 配置')", plugins_js)
        self.assertIn("plT('请选择一个已安装插件 Provider。')", plugins_js)
        self.assertIn("plT('测试连接')", plugins_js)
        self.assertIn("plT('保存')", plugins_js)
        self.assertIn("let _activeConfigFields = null", plugins_js)
        soft_fn = plugins_js[plugins_js.index("function softPaintOnLanguageChange()"):plugins_js.index("// ── Public API")]
        self.assertIn("_renderConfigForm(_activeConfig, _activeConfigFields, liveConfig)", soft_fn)
        self.assertNotIn("/api/plugins/", soft_fn)
        # Install/uninstall/test/apply action chrome uses live plT (not raw Chinese literals).
        install_start = plugins_js.index("async function install(name, url)")
        install_end = plugins_js.index("function confirmUninstall", install_start)
        install_slice = plugins_js[install_start:install_end]
        self.assertIn("plT('安装中…')", install_slice)
        self.assertIn("plT('安装失败')", install_slice)
        self.assertIn("plT('安装成功，请点击「应用变更」')", install_slice)
        self.assertIn("plT('卸载失败')", plugins_js)
        self.assertIn("plT('插件已卸载')", plugins_js)
        self.assertIn("plT('配置已保存')", plugins_js)
        self.assertIn("plT('连接成功')", plugins_js)
        self.assertIn("plT('应用失败')", plugins_js)
        self.assertIn("plT('请输入插件名称')", plugins_js)
        # Manual refresh must force-reload even after a successful empty list.
        self.assertIn("PluginManager.loadPlugins({ force: true })", plugins_js)
        init_start = plugins_js.index("function init()")
        init_end = plugins_js.index("async function ensureLoaded", init_start)
        init_js = plugins_js[init_start:init_end]
        self.assertNotIn("loadPlugins()", init_js)
        # Catalog rewrite settles first; plugin DOM injection re-applies afterward.
        catalog_refresh_pos = plugins_js.index("await _refreshMailboxProviderCatalogFromPlugins(forceCatalogRefresh)")
        radios_pos = plugins_js.index("_refreshProviderRadios()", catalog_refresh_pos)
        select_pos = plugins_js.index("_refreshProviderSelect()", catalog_refresh_pos)
        self.assertLess(catalog_refresh_pos, radios_pos)
        self.assertLess(radios_pos, select_pos)
        # Existing catalog radios/options keep authoritative labels; inject only tags source.
        self.assertIn("only tag source, do not overwrite labels", plugins_js)
        self.assertIn("Catalog option text is authoritative when already present", plugins_js)
        self.assertNotIn("if (nameEl) nameEl.textContent = p.display_name || p.name;", plugins_js)
        self.assertNotIn("existing.textContent = `🧩 ${p.display_name || p.name}`;", plugins_js)
        # Do not force Settings/create-temp reroute on every plugin list refresh.
        self.assertIn("injectedNewPluginRadio", plugins_js)
        self.assertIn("selectionChanged || injectedNewPluginRadio", plugins_js)
        self.assertIn("selectionChanged && typeof onTempEmailProviderChange", plugins_js)

    def test_settings_page_does_not_expose_legacy_gptmail_field_name(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")

        self.assertNotIn("gptmail_api_key", index_html)
        self.assertIn("旧版临时邮箱 API Key 字段", index_html)

    def test_temp_email_frontend_uses_temp_email_extract_endpoint(self):
        client = self.app.test_client()
        groups_js = load_feature_package_js('static/js/features/groups')
        temp_js = load_feature_package_js('static/js/features/temp_emails')
        emails_js = load_feature_package_js('static/js/features/emails')
        combined = groups_js + "\n" + temp_js + "\n" + emails_js

        self.assertIn("/api/temp-emails/", combined)
        self.assertIn("extract-verification", combined)
        self.assertIn("buildVerificationExtractEndpoint", groups_js)
        self.assertIn("source: 'temp'", temp_js)
        self.assertIn("copyVerificationInfo(currentAccount, buttonElement", emails_js)
        self.assertIn("fallbackExtractor", groups_js)

    def test_temp_email_page_has_visible_detail_panel_contract(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")
        temp_section = re.search(r'id="page-temp-emails".*?(?=id="page-refresh-log")', index_html, re.DOTALL)

        self.assertIsNotNone(temp_section)
        section_html = temp_section.group(0)
        self.assertIn('id="tempEmailDetailSection"', section_html)
        self.assertIn('id="tempEmailDetailToolbar"', section_html)
        self.assertIn('id="tempEmailDetail"', section_html)

    def test_temp_email_detail_handler_targets_temp_detail_panel(self):
        client = self.app.test_client()
        temp_js = load_feature_package_js('static/js/features/temp_emails')

        self.assertIn("showEmailDetailContainer({ source: 'temp' })", temp_js)
        self.assertIn("setEmailDetailToolbarVisibility(true, { source: 'temp' })", temp_js)
        self.assertIn("getEmailDetailRefs({ source: 'temp' })", temp_js)
        self.assertIn("renderEmailDetail(data.email, { source: 'temp' })", temp_js)

    def test_normal_mailbox_selection_resets_method_and_temp_page_no_longer_mutates_it(self):
        client = self.app.test_client()
        accounts_js = load_feature_package_js('static/js/features/accounts')
        temp_js = load_feature_package_js('static/js/features/temp_emails')

        self.assertIn("currentMethod = 'graph';", accounts_js)
        self.assertNotIn("currentMethod = 'temp-mail'", temp_js)

    def test_temp_email_frontend_removes_gptmail_branding_from_temp_email_page(self):
        client = self.app.test_client()
        js = load_feature_package_js('static/js/features/temp_emails')
        self.assertNotIn("currentMethod = 'gptmail'", js)
        self.assertNotIn("methodTag.textContent = 'GPTMail'", js)


class TempMailFrontendHelperBehaviorTests(unittest.TestCase):
    def test_build_verification_extract_endpoint_routes_temp_and_normal_mailboxes(self):
        if shutil.which("node") is None:
            self.skipTest("node is not installed")

        groups_js = load_feature_package_js("static/js/features/groups")
        self.assertIn("function buildVerificationExtractEndpoint", groups_js)

        node_script = r"""
const fs = require('fs');
const vm = require('vm');

const filePath = process.argv[2] || process.argv[1];
const code = fs.readFileSync(filePath, 'utf8');
const match = code.match(/function buildVerificationExtractEndpoint\(email, options = \{\}\) \{[\s\S]*?\n        \}/);
if (!match) {
  throw new Error('buildVerificationExtractEndpoint definition not found');
}

const context = {};
vm.createContext(context);
vm.runInContext(`${match[0]}\nthis.buildVerificationExtractEndpoint = buildVerificationExtractEndpoint;`, context, { filename: filePath });

if (typeof context.buildVerificationExtractEndpoint !== 'function') {
  throw new Error('buildVerificationExtractEndpoint is not executable');
}

const tempResult = context.buildVerificationExtractEndpoint('demo+1@test.example', { source: 'temp-mail' });
if (tempResult !== '/api/temp-emails/demo%2B1%40test.example/extract-verification') {
  throw new Error(`unexpected temp endpoint: ${tempResult}`);
}

const normalResult = context.buildVerificationExtractEndpoint('demo+1@test.example', { source: 'outlook' });
if (normalResult !== '/api/emails/demo%2B1%40test.example/extract-verification') {
  throw new Error(`unexpected normal endpoint: ${normalResult}`);
}

const defaultResult = context.buildVerificationExtractEndpoint('demo+1@test.example');
if (defaultResult !== '/api/emails/demo%2B1%40test.example/extract-verification') {
  throw new Error(`unexpected default endpoint: ${defaultResult}`);
}

process.stdout.write('OK');
"""

        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp.write(groups_js)
            groups_js_path = Path(tmp.name)
        try:
            result = subprocess.run(
                ["node", "-e", node_script, "--", str(groups_js_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            groups_js_path.unlink(missing_ok=True)

        self.assertEqual(
            result.returncode,
            0,
            msg=f"node stdout:\n{result.stdout}\nnode stderr:\n{result.stderr}",
        )
