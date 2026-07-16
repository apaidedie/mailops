"""tests/test_settings_tab_refactor_frontend.py — B 类：前端契约测试

目标：验证设置页面 UI 重构（Tab 化 + 临时邮箱配置区分离）的前端代码已正确存在：
  - index.html: 4 个 Tab 按钮、4 个 Tab 面板、Provider radio button（非 select）
  - index.html: 兼容临时邮箱桥接配置面板字段、CF Worker 配置面板字段、只读属性
  - main.js:  switchSettingsTab / onTempMailProviderChange / autoSaveSettings 函数
  - main.css: .settings-tab-nav / .settings-tab / .settings-tab-pane / .provider-radio-group / .readonly-field 样式

关联文档：
  - TDD: docs/TDD/2026-04-04-设置页面UI重构-TDD.md
  - FD:  docs/FD/2026-04-04-设置页面UI重构-FD.md
"""

from __future__ import annotations

from tests.frontend_js_bundle import load_frontend_app_js
import json
import unittest
from unittest.mock import patch

from tests._import_app import import_web_app_module

CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"


class SettingsTabRefactorFrontendTests(unittest.TestCase):
    """B 类：前端契约测试 — 设置页面 Tab 重构"""

    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def _get_text(self, client, path: str = "/") -> str:
        resp = client.get(path)
        try:
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    # ──────────────────────────────────────────────────────
    # TC-B01：index.html 包含 4 个 Tab 按钮
    # ──────────────────────────────────────────────────────

    def test_index_html_contains_four_settings_tabs(self):
        """index.html 应包含 4 个 settings-tab 按钮及导航栏"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        # Tab 导航栏容器
        self.assertIn('class="settings-tab-nav"', html, "应包含 .settings-tab-nav 导航栏")

        # 4 个 Tab 的 data-tab 属性
        self.assertIn('data-tab="basic"', html, "应包含基础 Tab 按钮")
        self.assertIn('data-tab="temp-mail"', html, "应包含临时邮箱 Tab 按钮")
        self.assertIn('data-tab="api-security"', html, "应包含 API 安全 Tab 按钮")
        self.assertIn('data-tab="automation"', html, "应包含自动化 Tab 按钮")

    # ──────────────────────────────────────────────────────
    # TC-B02：index.html 包含 4 个 Tab 面板
    # ──────────────────────────────────────────────────────

    def test_index_html_contains_four_tab_panes(self):
        """index.html 应包含 4 个 settings-tab-pane 内容面板"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        self.assertIn('id="settings-tab-basic"', html, "应包含基础 Tab 面板")
        self.assertIn('id="settings-tab-temp-mail"', html, "应包含临时邮箱 Tab 面板")
        self.assertIn('id="settings-tab-api-security"', html, "应包含 API 安全 Tab 面板")
        self.assertIn('id="settings-tab-automation"', html, "应包含自动化 Tab 面板")

    # ──────────────────────────────────────────────────────
    # TC-B03：index.html 包含 Provider 单选按钮组（非下拉框）
    # ──────────────────────────────────────────────────────

    def test_index_html_contains_provider_radio_buttons(self):
        """index.html 应暴露 Provider 动态挂载点，且不再硬编码旧选择器。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        # Settings Provider 选项由 main.js 从 /api/providers 动态渲染。
        self.assertIn('id="tempMailProviderOptions"', html, "应包含 tempMailProvider 动态挂载点")
        self.assertIn('class="provider-radio-group" id="tempMailProviderOptions"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('provider-radio-loading', html)
        mount_start = html.index('id="tempMailProviderOptions"')
        # Mount ends before the schema-driven config panel / legacy compatibility mounts.
        for marker in (
            'id="tempMailProviderConfigPanel"',
            'id="gptmailConfigPanel"',
            '<!-- Legacy specialized mounts',
            '<!-- Catalog/schema-driven built-in Provider configuration -->',
        ):
            if marker in html[mount_start:]:
                mount_end = html.index(marker, mount_start)
                break
        else:
            mount_end = mount_start + 800
        mount_html = html[mount_start:mount_end]
        self.assertNotIn('name="tempMailProvider"', mount_html, "Provider radio 应由 JS 动态渲染")
        self.assertNotIn('onchange="onTempMailProviderChange', mount_html, "Provider radio 不应依赖模板内联 onchange")
        self.assertNotIn('value="legacy_bridge"', mount_html, "Provider 选项不应在模板中硬编码")

        # 不应再有旧的 Provider 下拉框
        self.assertNotIn(
            '<select id="settingsTempMailProvider"',
            html,
            "不应保留旧的 Provider <select> 元素",
        )

    def test_index_html_contains_provider_config_status_targets(self):
        """Provider 卡片和临时邮箱创建栏应有配置状态展示挂载点。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        self.assertIn('id="tempEmailProviderStatus"', html, "临时邮箱创建栏应显示当前 Provider 配置状态")
        self.assertIn('id="externalApiCommandCenter"', html, "API 安全页应显示外部 API 指挥台")
        self.assertIn('class="provider-workbench" id="providerWorkbench"', html, "API 安全页应显示邮箱来源运营台")
        self.assertIn('id="providerWorkbenchSummary" aria-live="polite"', html, "邮箱来源运营台应有概览挂载点")
        self.assertIn('id="providerWorkbenchBadge"', html, "邮箱来源运营台应有状态徽标")
        self.assertIn('邮箱来源运营台', html)
        self.assertIn('统一查看启用范围、运行默认、领取默认、发现入口和配置风险', html)
        self.assertIn('class="provider-preflight-console" id="providerPreflightConsole"', html, "邮箱来源运营台应显示 Provider 批量预检")
        self.assertIn('id="providerPreflightSummary" aria-live="polite"', html, "Provider 批量预检应有概览挂载点")
        self.assertIn('id="providerPreflightList" aria-live="polite"', html, "Provider 批量预检应有明细挂载点")
        self.assertIn('data-provider-preflight-probe', html, "Provider 批量预检应有显式探测按钮")
        self.assertIn('Provider 批量预检', html)
        self.assertIn('本地只读检查全部邮箱来源；手动触发时才探测可用临时邮箱上游', html)
        self.assertIn('加载 Provider 预检…', html)
        self.assertIn('class="provider-contract-status" id="providerContractStatus"', html, "邮箱来源运营台应显示 Provider 扩展契约状态")
        self.assertIn('id="providerContractStatusSummary" aria-live="polite"', html, "Provider 契约状态应有概览挂载点")
        self.assertIn('id="providerContractStatusList" aria-live="polite"', html, "Provider 契约状态应有明细挂载点")
        self.assertIn('Provider 扩展契约', html)
        self.assertIn('查看临时邮箱 Provider 插件是否满足统一邮箱与外部 API 接入契约', html)
        self.assertIn('id="providerDiagnosticsSummary"', html, "API 安全页应显示邮箱来源诊断摘要")
        self.assertIn('id="providerConsole"', html, "API 安全页应显示邮箱来源控制台")
        self.assertIn('id="providerConsoleTable"', html, "邮箱来源控制台应有明细表挂载点")
        self.assertIn('data-provider-console-filter="needs_config"', html, "邮箱来源控制台应支持缺配置筛选")
        self.assertIn('data-provider-console-filter="all" aria-pressed="true"', html, "邮箱来源控制台应标记默认筛选状态")
        self.assertIn('data-provider-console-filter="active" aria-pressed="false"', html, "邮箱来源控制台筛选按钮应暴露可访问状态")
        self.assertIn('id="tempMailProviderOptions"', html, "Provider 卡片状态挂载点应由动态 renderer 创建")

    def test_external_api_command_center_mounts_before_api_key_field(self):
        """外部 API 指挥台应位于 API Key 表单之前。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        command_center_index = html.find('id="externalApiCommandCenter"')
        api_key_index = html.find('id="settingsExternalApiKey"')
        workbench_index = html.find('id="providerWorkbench"')
        preflight_index = html.find('id="providerPreflightConsole"')
        contract_index = html.find('id="providerContractStatus"')
        diagnostics_index = html.find('id="providerDiagnosticsSummary"')
        self.assertNotEqual(command_center_index, -1)
        self.assertNotEqual(api_key_index, -1)
        self.assertNotEqual(workbench_index, -1)
        self.assertNotEqual(preflight_index, -1)
        self.assertNotEqual(contract_index, -1)
        self.assertNotEqual(diagnostics_index, -1)
        self.assertLess(command_center_index, api_key_index)
        self.assertLess(workbench_index, preflight_index)
        self.assertLess(preflight_index, contract_index)
        self.assertLess(contract_index, diagnostics_index)
        self.assertIn('data-state="loading" aria-live="polite"', html)
        self.assertIn('正在读取外部 API 服务…', html)

    def test_index_html_contains_provider_config_template_panel(self):
        """API 安全页应展示可复制的 provider 部署配置模板。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        self.assertIn('id="providerConfigTemplates"', html)
        self.assertIn('id="providerConfigTemplateMeta" aria-live="polite"', html)
        self.assertIn('id="providerConfigTemplateCode"', html)
        self.assertIn('class="provider-config-template-code" tabindex="0"', html)
        self.assertIn('role="group" aria-label="部署配置模板格式"', html)
        self.assertIn('data-provider-template-format="env" aria-pressed="true"', html)
        self.assertIn('data-provider-template-format="json" aria-pressed="false"', html)
        self.assertIn('data-provider-template-format="toml" aria-pressed="false"', html)
        self.assertIn('data-provider-template-copy', html)
        self.assertIn('data-provider-template-copy disabled', html)
        self.assertNotIn('id="providerConfigTemplates" aria-live="polite"', html)

    def test_index_html_contains_provider_integration_guide_panel(self):
        """API 安全页应展示 provider 接入指南入口。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)

        self.assertIn('id="providerIntegrationGuide"', html)
        self.assertIn('id="providerIntegrationGuideSummary" aria-live="polite"', html)
        self.assertIn('id="providerIntegrationGuideList" aria-live="polite"', html)
        self.assertIn('Provider 接入指南', html)
        self.assertIn('data-provider-integration-filter="all" aria-pressed="true"', html)
        self.assertIn('data-provider-integration-filter="temp" aria-pressed="false"', html)
        self.assertIn('加载 Provider 接入指南…', html)

    def test_main_js_loads_provider_catalog_for_config_status(self):
        """main.js 应复用 /api/providers 的统一 catalog 渲染配置状态。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("function loadMailboxProviderCatalog", js_text)
        self.assertIn("/api/providers", js_text)
        self.assertIn("mailboxProviderSelectionPolicyCache", js_text)
        self.assertIn("data.selection_policy", js_text)
        # Operator default temp provider from admin /api/providers (bridge-canonical).
        self.assertIn("let mailboxProviderDefaultTempMailProvider", js_text)
        self.assertIn("function getOperatorDefaultTempMailProvider", js_text)
        self.assertIn("data.default_temp_mail_provider", js_text)
        self.assertIn("mailboxProviderDefaultTempMailProvider = normalizeTempMailSettingsProviderName(", js_text)
        self.assertIn("function getCurrentTempMailSettingsProviderSelection", js_text)
        get_current_start = js_text.index("function getCurrentTempMailSettingsProviderSelection")
        get_current_end = js_text.index("function isTempMailSettingsProviderMountBound", get_current_start)
        get_current_js = js_text[get_current_start:get_current_end]
        self.assertIn("isTempMailSettingsProviderMountBound(target)", get_current_js)
        self.assertIn("tempMailSettingsSnapshot", get_current_js)
        # Pending only when bound; unbound falls back to snapshot then operator default.
        self.assertIn("dataset.pendingProvider", get_current_js)
        self.assertIn("getOperatorDefaultTempMailProvider()", get_current_js)
        self.assertIn("function getPoolDefaultProviderAllowedValues", js_text)
        self.assertIn("function renderPoolDefaultProviderDatalist", js_text)
        self.assertIn("renderPoolDefaultProviderDatalist();", js_text)
        # Pool/active allowlists collapse bridge aliases (custom_domain_temp_mail → legacy_bridge).
        self.assertIn("function canonicalizeMailboxProviderAllowlistValue", js_text)
        self.assertIn("function canonicalizeMailboxProviderAllowlistValues", js_text)
        self.assertIn("function dedupeMailboxProviderDiagnosticRows", js_text)
        self.assertIn("canonicalizeMailboxProviderAllowlistValue(item)", js_text)
        self.assertIn("canonicalizeMailboxProviderAllowlistValues(", js_text)
        self.assertIn("dedupeMailboxProviderDiagnosticRows(", js_text)
        self.assertIn("resolveMailboxProviderLabel(value", js_text)
        # Contract + integration guide provider rows also collapse bridge aliases.
        self.assertIn("canonicalizeMailboxProviderAllowlistValue(rawProviderName)", js_text)
        self.assertIn("return dedupeMailboxProviderDiagnosticRows(providers)", js_text)
        # Textarea chip matching must use the same canonical keys.
        self.assertIn("canonicalizeMailboxProviderAllowlistValue(item)", js_text)
        self.assertIn("function getActiveMailboxProvidersFromTextarea", js_text)
        textarea_start = js_text.index("function getActiveMailboxProvidersFromTextarea")
        textarea_end = js_text.index("function renderActiveMailboxProviderSuggestions", textarea_start)
        textarea_js = js_text[textarea_start:textarea_end]
        self.assertIn("canonicalizeMailboxProviderAllowlistValue(item)", textarea_js)
        self.assertIn("canonicalizeMailboxProviderAllowlistValue(providerName)", textarea_js)
        # Load/save paths also go through canonical helpers.
        self.assertIn("setActiveMailboxProvidersTextarea(activeProviders)", js_text)
        self.assertIn("settings.active_mailbox_providers = getActiveMailboxProvidersFromTextarea()", js_text)
        self.assertIn("settings.pool_default_provider = canonicalizeMailboxProviderAllowlistValue(", js_text)
        # Catalog label lookup also tries canonical alias keys.
        label_start = js_text.index("function getMailboxProviderCatalogLabel")
        label_end = js_text.index("function resolveMailboxProviderLabel", label_start)
        label_js = js_text[label_start:label_end]
        self.assertIn("canonicalizeMailboxProviderAllowlistValue(key)", label_js)
        self.assertIn("candidates.push(canonical)", label_js)
        self.assertIn("function refreshAccountProviderTagsFromCatalog", js_text)
        self.assertIn("refreshAccountProviderTagsFromCatalog();", js_text)
        # Catalog success/warm soft-load re-paints pool-admin type filter without a second GET.
        self.assertIn("ensurePoolAdminProviderOptions(false)", js_text)
        self.assertNotIn("ensurePoolAdminProviderOptions(true)", js_text)
        catalog_start = js_text.index("async function loadMailboxProviderCatalog")
        catalog_end = js_text.index("async function", catalog_start + 10)
        # Use a safer end: next major function after catalog if needed
        if "function getMailboxProviderCatalogItem" in js_text[catalog_start:]:
            catalog_end = js_text.index("function getMailboxProviderCatalogItem", catalog_start)
        catalog_js = js_text[catalog_start:catalog_end]
        self.assertIn("ensurePoolAdminProviderOptions(false)", catalog_js)
        # Warm soft path also re-paints pool filter.
        warm_idx = catalog_js.index("!force && Array.isArray(mailboxProviderCatalogCache)")
        soft_pool_idx = catalog_js.index("ensurePoolAdminProviderOptions(false)")
        self.assertLess(warm_idx, soft_pool_idx)
        # And import-account provider select if already mounted/opened (soft re-paint).
        self.assertIn("loadProviders(false)", js_text)
        self.assertNotIn("loadProviders(true)", js_text)
        # And unified mailbox cards/readiness labels when already loaded.
        self.assertIn("refreshUnifiedMailboxProviderLabelsFromCatalog()", js_text)
        self.assertIn("function getMailboxProviderCatalogLabel", js_text)
        self.assertIn("function resolveMailboxProviderLabel", js_text)
        # Schema panel title also prefers shared catalog labels.
        self.assertIn("resolveMailboxProviderLabel(normalizedProvider", js_text)
        # Plugin missing_config keys should resolve via catalog field labels.
        missing_fn_start = js_text.index("function getMissingConfigDisplayName")
        missing_fn_end = js_text.index("function getMailboxProviderCatalogItem", missing_fn_start)
        missing_fn = js_text[missing_fn_start:missing_fn_end]
        self.assertIn("pluginMatch", missing_fn)
        self.assertIn("getMailboxProviderCatalogItem(providerName, 'temp')", missing_fn)
        self.assertIn("config_schema", missing_fn)
        # Boot path should preload catalog without blocking first paint consumers.
        self.assertIn("document.addEventListener('DOMContentLoaded'", js_text)
        self.assertIn("loadMailboxProviderCatalog(false)", js_text)
        self.assertIn("scopes.pool_claim_default", js_text)
        self.assertIn("function getActiveMailboxProviderAllowedValues", js_text)
        self.assertIn("function renderActiveMailboxProviderSuggestions", js_text)
        self.assertIn("function toggleActiveMailboxProviderSuggestion", js_text)
        self.assertIn("renderActiveMailboxProviderSuggestions();", js_text)
        self.assertIn("scopes.active_allowlist", js_text)
        self.assertIn("data-active-mailbox-provider", js_text)
        self.assertIn("function updateTempMailProviderStatusBadges", js_text)
        self.assertIn("function renderProviderDiagnostics", js_text)
        self.assertIn("function renderProviderWorkbench", js_text)
        self.assertIn("function getProviderWorkbenchConfigFileStatus", js_text)
        self.assertIn("function getProviderWorkbenchSecretPolicyText", js_text)
        self.assertIn("function getProviderWorkbenchRuntimeDefault", js_text)
        self.assertIn("function renderProviderWorkbenchDiscovery", js_text)
        self.assertIn("function renderProviderWorkbenchMetric", js_text)
        self.assertIn("function renderProviderConsole", js_text)
        self.assertIn("function renderProviderHealthCell", js_text)
        self.assertIn("async function probeMailboxProviderHealth", js_text)
        self.assertIn("function getProviderHealthResultText", js_text)
        self.assertIn("function setProviderConsoleFilter", js_text)
        self.assertIn("function normalizeProviderConsoleFilter", js_text)
        self.assertIn("function syncProviderConsoleFilterButtons", js_text)
        self.assertIn("function getProviderDeploymentText", js_text)
        self.assertIn("function getProviderDeploymentAssignment", js_text)
        self.assertIn("data-provider-health-action", js_text)
        self.assertIn("/api/providers/${encodeURIComponent(normalizedKind)}/${encodeURIComponent(normalizedProvider)}/health?probe_network=true", js_text)
        self.assertIn("mailboxProviderHealthState = {};", js_text)
        self.assertIn("上游探测", js_text)
        self.assertIn("账号池不用探测", js_text)
        self.assertIn("先补齐配置", js_text)
        self.assertIn("本地检查通过", js_text)
        self.assertIn("syncProviderConsoleFilterButtons();", js_text)
        self.assertIn("button.setAttribute('aria-pressed'", js_text)
        self.assertIn("deployment.activate", js_text)
        self.assertIn("deployment.pool_claim_default", js_text)
        self.assertIn("deployment.runtime_default", js_text)
        self.assertIn("deployment.pool_claim_request", js_text)
        self.assertIn("deployment.task_temp_apply_request", js_text)
        self.assertIn("deployment.config_env", js_text)
        self.assertIn("deployment.config_settings", js_text)
        self.assertIn("target.env || target.field", js_text)
        self.assertIn("target.value || target.settings_value", js_text)
        self.assertIn("filter.unknown_providers", js_text)
        self.assertIn("未知来源白名单项", js_text)
        self.assertIn("defaults.invalid_defaults", js_text)
        self.assertIn("默认来源配置无效", js_text)
        self.assertIn("defaults.inactive_defaults", js_text)
        self.assertIn("默认来源未启用", js_text)
        self.assertIn("provider_diagnostics", js_text)
        self.assertIn("mailboxProviderDiagnosticsCache", js_text)
        self.assertIn("deployment_profile", js_text)
        self.assertIn("mailboxProviderDeploymentProfileCache", js_text)
        self.assertIn("provider_integration_guide", js_text)
        self.assertIn("mailboxProviderIntegrationGuideCache", js_text)
        self.assertIn("integration_manifest", js_text)
        self.assertIn("mailboxProviderIntegrationManifestCache", js_text)
        self.assertIn("data.integration_manifest", js_text)
        self.assertIn("let mailboxProviderIntegrationQuickstartCache = null;", js_text)
        self.assertIn("data.quickstart", js_text)
        self.assertIn("mailboxProviderIntegrationQuickstartCache = data.quickstart", js_text)
        self.assertIn("function renderProviderIntegrationGuide", js_text)
        # Guide card titles prefer shared catalog labels over payload-only label.
        self.assertIn("resolveMailboxProviderLabel(providerName", js_text)
        self.assertIn("function buildProviderIntegrationEnvSnippet", js_text)
        self.assertIn("function getProviderIntegrationSecretKeySets", js_text)
        self.assertIn("async function copyProviderIntegrationSnippet", js_text)
        self.assertIn("function setProviderIntegrationFilter", js_text)
        self.assertIn("function syncProviderIntegrationFilterButtons", js_text)
        self.assertIn("function getProviderIntegrationProvider", js_text)
        self.assertIn("data-provider-integration-filter", js_text)
        self.assertIn("data-provider-integration-copy", js_text)
        self.assertIn("secretKeys.env.has(envKey) ? ''", js_text)
        self.assertIn("secretKeys.settings.has(settingsKey) ? ''", js_text)
        self.assertIn("secretSet.has(envKey) ?", js_text)
        self.assertIn("const nextLine = `${envKey}=${nextValue}`", js_text)
        self.assertIn("copyTextToClipboard(snippet)", js_text)
        self.assertIn("Provider 接入片段已复制", js_text)
        self.assertIn("function renderProviderConfigTemplates", js_text)
        self.assertIn("function getProviderTemplateDescriptor", js_text)
        self.assertIn("function copyProviderConfigTemplate", js_text)
        self.assertIn("function copyTextToClipboard", js_text)
        self.assertIn("provider_config_json", js_text)
        self.assertIn("provider_config_toml", js_text)
        self.assertIn("data-provider-template-format", js_text)
        self.assertIn("data-provider-template-copy", js_text)
        self.assertIn("copyTextToClipboard(copyValue)", js_text)
        self.assertIn("copyTextToClipboard(descriptor.content)", js_text)
        self.assertIn("tempInput.parentNode.removeChild(tempInput)", js_text)
        self.assertIn("missing_config", js_text)
        self.assertIn("let externalApiSettingsSnapshot = {};", js_text)

    def test_pool_default_provider_datalist_is_catalog_driven(self):
        """默认领取来源 datalist 应由 selection_policy 动态填充，而非模板硬编码。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertIn('id="poolDefaultProvider"', html)
        self.assertIn('list="poolDefaultProviderOptions"', html)
        self.assertIn('id="poolDefaultProviderOptions"', html)
        # Hard-coded option values must not live in the template mount.
        datalist_start = html.index('id="poolDefaultProviderOptions"')
        datalist_end = html.index("</datalist>", datalist_start)
        datalist_html = html[datalist_start:datalist_end]
        for provider in (
            "outlook",
            "gmail",
            "custom",
            "imap",
            "mail_tm",
            "duckmail",
            "tempmail_lol",
            "emailnator",
            "cloudflare_temp_mail",
            "gptmail",
        ):
            self.assertNotIn(f'value="{provider}"', datalist_html)

        self.assertIn("function getPoolDefaultProviderAllowedValues", js_text)
        self.assertIn("function renderPoolDefaultProviderDatalist", js_text)
        self.assertIn("mailboxProviderSelectionPolicyCache", js_text)
        self.assertIn("scopes.pool_claim_default", js_text)
        self.assertIn("scopes.explicit_pool_claim", js_text)
        self.assertIn("allowed_values", js_text)
        self.assertIn("poolDefaultProviderOptions", js_text)
        self.assertIn("values.unshift('auto')", js_text)
        self.assertIn("renderPoolDefaultProviderDatalist();", js_text)

    def test_active_mailbox_providers_suggestions_are_catalog_driven(self):
        """启用邮箱来源应提供 catalog/selection_policy 驱动的建议 chips。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()
        css_text = self._get_text(client, "/static/css/main.css")

        self.assertIn('id="activeMailboxProviders"', html)
        self.assertIn('id="activeMailboxProviderSuggestions"', html)
        self.assertNotIn("支持 duckmail、mail_tm、emailnator、outlook、imap、gptmail 等。", html)
        self.assertNotIn("每行一个 provider，如 duckmail", html)

        self.assertIn("function getActiveMailboxProviderAllowedValues", js_text)
        self.assertIn("function renderActiveMailboxProviderSuggestions", js_text)
        self.assertIn("function toggleActiveMailboxProviderSuggestion", js_text)
        self.assertIn("scopes.active_allowlist", js_text)
        self.assertIn("data-active-mailbox-provider", js_text)
        self.assertIn("active-mailbox-provider-chip", js_text)
        self.assertIn("renderActiveMailboxProviderSuggestions();", js_text)
        self.assertIn(".active-mailbox-provider-chip", css_text)
        self.assertIn(".active-mailbox-provider-chip.active", css_text)

    def test_settings_temp_mail_provider_options_are_catalog_driven(self):
        """Settings 临时邮箱 Provider 单选卡片应完全由 catalog 渲染。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertIn('id="tempMailProviderOptions"', html)
        self.assertIn('id="tempMailProviderConfigPanel"', html)
        self.assertIn('id="tempMailProviderConfigBody"', html)
        self.assertNotIn("TEMP_MAIL_SETTINGS_PROVIDER_FALLBACKS", js_text)
        self.assertNotIn("TEMP_MAIL_SETTINGS_PROVIDER_ALIAS_MAP", js_text)
        self.assertNotIn("TEMP_MAIL_SETTINGS_SCHEMA_PANEL_PROVIDERS", js_text)
        self.assertIn("function renderTempProviderSettingsActions", js_text)
        self.assertIn("function runTempProviderSettingsAction", js_text)
        self.assertIn("function syncTempProviderSchemaInputsToSnapshot", js_text)
        self.assertIn("data-temp-provider-action", js_text)
        self.assertIn("data-temp-provider-readonly", js_text)
        self.assertIn("/api/settings/cf-worker-sync-domains", js_text)
        # CF Worker sync chrome translates at paint time.
        self.assertIn("function syncCfWorkerDomains", js_text)
        self.assertIn("function updateCfWorkerReadonlyFields", js_text)
        self.assertIn("async function syncCfWorkerDomains()", js_text)
        self.assertIn("runTempProviderSettingsAction", js_text)
        self.assertIn("/api/settings/cf-worker-sync-domains", js_text)
        # CF Worker sync/readonly copy is translated at paint/action time.
        self.assertIn("同步成功", js_text)
        self.assertIn("上次同步", js_text)
        self.assertIn("function updateCfWorkerReadonlyFields", js_text)
        # Settings tab switch / auto-save / proxy test chrome translates at paint time.
        self.assertIn(
            "translateAppTextLocal('密码修改未保存，如需修改请在「基础」Tab 重新输入后点击保存')",
            js_text,
        )
        self.assertIn(
            "translateAppTextLocal('保存失败，[' + tabName + '] Tab 的修改尚未保存，请手动重试')",
            js_text,
        )
        self.assertIn("translateAppTextLocal('✅ 连通')", js_text)
        # Provider catalog fallback descriptions translate at paint time.
        self.assertIn("translateAppTextLocal('第三方插件 Provider')", js_text)
        self.assertIn("translateAppTextLocal('支持动态创建临时邮箱')", js_text)
        self.assertIn("translateAppTextLocal('临时邮箱 Provider')", js_text)
        self.assertIn("translateAppTextLocal('当前已保存的临时邮箱 Provider')", js_text)
        self.assertIn("syncTempProviderSchemaInputsToSnapshot()", js_text)
        # Dedicated specialized field panels should no longer be the source of truth.
        self.assertNotIn("settingsTempMailApiBaseUrl", html)
        self.assertNotIn("settingsCfWorkerBaseUrl", html)
        self.assertNotIn("btnSyncCfWorkerDomains", html)
        self.assertIn('id="gptmailConfigPanel"', html)
        self.assertIn('id="cfWorkerConfigPanel"', html)

        # 创建临时邮箱栏：静态 provider 选项改为 catalog 加载占位，并由 sync 清理占位。
        select_start = html.index('id="tempEmailProviderSelect"')
        select_end = html.index('</select>', select_start)
        select_html = html[select_start:select_end]
        self.assertIn("正在加载 Provider 目录", select_html)
        self.assertNotIn('value="legacy_bridge"', select_html)
        self.assertNotIn('value="cloudflare_temp_mail"', select_html)
        self.assertNotIn('value="mail_tm"', select_html)
        self.assertNotIn('value="duckmail"', select_html)
        self.assertNotIn('value="tempmail_lol"', select_html)
        self.assertNotIn('value="emailnator"', select_html)
        sync_start = js_text.index("function syncTempEmailProviderSelectWithCatalog")
        sync_end = js_text.index("async function loadMailboxProviderCatalog", sync_start)
        sync_text = js_text[sync_start:sync_end]
        self.assertIn("catalogProviders.has(value)", sync_text)
        self.assertIn("option.remove()", sync_text)
        self.assertIn("catalogOptions[0].provider", sync_text)
        options_start = js_text.index("function getTempEmailProviderCatalogOptions")
        options_end = js_text.index("function findTempEmailProviderOption", options_start)
        options_text = js_text[options_start:options_end]
        self.assertIn("normalizeTempMailSettingsProviderName", options_text)
        self.assertIn("seen.has(provider)", options_text)

        for helper in [
            "function normalizeTempMailSettingsProviderName",
            "function normalizeTempMailSettingsProviderOption",
            "function getTempMailSettingsProviderOptions",
            "function renderTempMailSettingsProviderOption",
            "function renderTempMailProviderOptions",
            "function getTempProviderConfiguration",
            "function providerUsesTempSettingsSchemaPanel",
            "function getTempProviderSchemaFields",
            "function renderTempMailProviderConfigPanel",
            "function hydrateTempProviderSchemaInputs",
            "function collectTempProviderSchemaSettings",
            "function initTempMailProviderOptions",
            "function findTempMailSettingsProviderRadio",
        ]:
            self.assertIn(helper, js_text)

        renderer_start = js_text.index("function normalizeTempMailSettingsProviderName")
        renderer_end = js_text.index("function getTempEmailProviderCatalogOptions", renderer_start)
        renderer_text = js_text[renderer_start:renderer_end]
        self.assertIn("String(item?.kind || '').trim().toLowerCase() === 'temp'", renderer_text)
        self.assertIn("provider === 'auto'", renderer_text)
        self.assertIn("mailboxProviderDiagnosticsCache || {}", renderer_text)
        self.assertIn("diagnosticProviders", renderer_text)
        self.assertIn('input type="radio" name="tempMailProvider"', renderer_text)
        self.assertIn('data-provider-status="${escapeHtml(provider)}"', renderer_text)
        self.assertIn("description: translateAppTextLocal('当前已保存的临时邮箱 Provider')", renderer_text)
        self.assertIn("item.settings_ui.aliases.map(normalizeProviderCatalogName).includes(provider)", renderer_text)
        self.assertIn("mount.addEventListener('change'", renderer_text)
        self.assertIn("configuration.config_schema", js_text)
        self.assertIn("String(item?.settings_ui?.panel || 'schema')", js_text)
        self.assertIn("data-temp-provider-setting", js_text)
        self.assertIn("data-temp-provider-field", js_text)
        self.assertIn("data-temp-provider-secret", js_text)
        self.assertIn("data-loaded-value", js_text)
        self.assertIn("field.settingKey || field.key", js_text)
        self.assertIn("inputEl.dataset.maskedValue = maskedValue", js_text)
        # Dirty-key collector: only edited/action-updated schema keys enter the payload.
        self.assertIn("tempMailSettingsDirtyKeys", js_text)
        self.assertIn("tempMailSettingsDirtyKeys.forEach", js_text)
        self.assertIn("settings[key] = tempMailSettingsSnapshot[key]", js_text)
        self.assertIn("syncTempProviderSchemaInputsToSnapshot", js_text)
        self.assertIn("collectTempProviderSchemaSettings", js_text)

        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, renderer_text)

        self.assertIn("renderTempMailProviderOptions();", js_text)
        self.assertIn("function applyTempMailSettingsSelection", js_text)
        self.assertIn("applyTempMailSettingsSelection(mappedProvider)", js_text)
        apply_start = js_text.index("function applyTempMailSettingsSelection")
        apply_end = js_text.index("function paintApiSecuritySurfacesFromSnapshot", apply_start)
        apply_js = js_text[apply_start:apply_end]
        # Unbound path clears pending; does not leave canonicalized pending on Basic load.
        self.assertIn("isTempMailSettingsProviderMountBound(providerGroup)", apply_js)
        self.assertIn("providerGroup.dataset.pendingProvider = ''", apply_js)
        self.assertIn("function initTempMailProviderOptions", js_text)
        # Boot must not force-render Settings radios / update-method toggles; init runs when Settings opens.
        boot_start = js_text.index("document.addEventListener('DOMContentLoaded'")
        boot_end = js_text.index("setTimeout(checkVersionUpdate", boot_start)
        boot_js = js_text[boot_start:boot_end]
        self.assertNotIn("initTempMailProviderOptions()", boot_js)
        self.assertNotIn("initUpdateMethodConfigToggles()", boot_js)
        self.assertIn("loadMailboxProviderCatalog(false)", boot_js)
        # loadSettings soft-loads catalog when warm; save paths still force-refresh.
        self.assertIn("const forceCatalogLoad = !(", js_text)
        self.assertIn("mailboxProviderCatalogCache.length", js_text)
        self.assertIn("loadMailboxProviderCatalog(forceCatalogLoad)", js_text)
        # Preflight is api-security scoped (not every Settings open).
        self.assertNotIn("loadProviderPreflightSnapshot(forceCatalogLoad, false)", js_text)
        # Post-save still forces catalog refresh after settings mutations.
        self.assertIn("await loadMailboxProviderCatalog(true)", js_text)
        # Temp-mail auto-save forces catalog but must not force preflight network.
        auto_save_start = js_text.index("async function autoSaveSettings")
        auto_save_end = js_text.index("function onTempMailProviderChange", auto_save_start)
        auto_save_js = js_text[auto_save_start:auto_save_end]
        # Success-handler temp-mail branch (after PUT), not the collect payload branch.
        temp_mail_success_marker = "await refreshTempMailSettingsSnapshotFromServer()"
        self.assertIn(temp_mail_success_marker, auto_save_js)
        temp_mail_save = auto_save_js[auto_save_js.index(temp_mail_success_marker):]
        self.assertIn("loadMailboxProviderCatalog(true)", temp_mail_save)
        self.assertNotIn("loadProviderPreflightSnapshot(true, false)", temp_mail_save)
        self.assertIn("providerPreflightCache = null", temp_mail_save)
        # Global Settings save closes modal: invalidate panel caches without forced network.
        save_settings_start = js_text.index("async function saveSettings")
        save_settings_end = js_text.index("async function testTelegramPush", save_settings_start)
        save_settings_js = js_text[save_settings_start:save_settings_end]
        self.assertIn("providerPreflightCache = null", save_settings_js)
        self.assertIn("operationalReadinessSnapshotCache = null", save_settings_js)
        self.assertIn("externalApiContractCheckCache = null", save_settings_js)
        self.assertNotIn("loadProviderPreflightSnapshot(true, false)", save_settings_js)
        self.assertNotIn("loadOperationalReadinessSnapshot(true)", save_settings_js)
        # API security auto-save still force-refreshes preflight.
        api_success_marker = "externalApiSettingsSnapshot = { ...externalApiSettingsSnapshot, ...settings }"
        self.assertIn(api_success_marker, auto_save_js)
        api_save = auto_save_js[auto_save_js.index(api_success_marker):auto_save_js.index(temp_mail_success_marker)]
        self.assertIn("loadProviderPreflightSnapshot(true, false)", api_save)
        # Settings open uses tab-specific ready hooks only; empty shared stub is gone.
        self.assertNotIn("ensureSettingsSurfaceReady", js_text)
        self.assertIn("function isSettingsSurfaceActive", js_text)
        self.assertIn("function isSettingsPageActive", js_text)
        self.assertIn("function ensureTempMailSettingsTabReady", js_text)
        self.assertIn("function ensureAutomationSettingsTabReady", js_text)
        self.assertIn("function applyTempMailSettingsSelection", js_text)
        load_settings_plugin_start = js_text.index("async function loadSettings(forceRefresh = false)")
        load_settings_plugin_end = js_text.index("console.error('loadSettings error:'", load_settings_plugin_start)
        load_settings_plugin_js = js_text[load_settings_plugin_start:load_settings_plugin_end]
        self.assertIn("currentSettingsTab === 'temp-mail'", load_settings_plugin_js)
        self.assertIn("ensureTempMailSettingsTabReady()", load_settings_plugin_js)
        self.assertIn("currentSettingsTab === 'automation'", load_settings_plugin_js)
        self.assertIn("ensureAutomationSettingsTabReady()", load_settings_plugin_js)
        self.assertIn("applyTempMailSettingsSelection(mappedProvider)", load_settings_plugin_js)
        settings_modal_start = js_text.index("async function showSettingsModal()")
        settings_modal_end = js_text.index("function hideSettingsModal", settings_modal_start)
        settings_modal_js = js_text[settings_modal_start:settings_modal_end]
        self.assertIn("await loadSettings()", settings_modal_js)
        self.assertNotIn("ensureSettingsSurfaceReady", settings_modal_js)
        load_settings_start = js_text.index("async function loadSettings(forceRefresh = false)")
        load_settings_end = js_text.index("console.error('loadSettings error:'", load_settings_start)
        load_settings_js = js_text[load_settings_start:load_settings_end]
        # Soft-load: page GET is owned by fetchSettingsPagePayload, not a raw fetch in loadSettings.
        self.assertLess(
            load_settings_js.index("currentSettingsTab === 'temp-mail'"),
            load_settings_js.index("fetchSettingsPagePayload(forceRefresh)"),
        )
        self.assertNotIn("fetch('/api/settings')", load_settings_js)
        # Remaining Settings provider-name fallbacks use the operator default helper.
        self.assertIn(
            "normalizeTempMailSettingsProviderName(providerName) || getOperatorDefaultTempMailProvider()",
            js_text,
        )
        self.assertIn(
            "normalizeTempMailSettingsProviderName(provider) || getOperatorDefaultTempMailProvider()",
            js_text,
        )
        self.assertEqual(js_text.count("|| 'legacy_bridge'"), 1)
        # Catalog-driven re-render skips the hidden mount until Settings has bound it.
        render_opts_start = js_text.index("function renderTempMailProviderOptions")
        render_opts_end = js_text.index("function initTempMailProviderOptions", render_opts_start)
        render_opts_js = js_text[render_opts_start:render_opts_end]
        self.assertIn("isTempMailSettingsProviderMountBound", render_opts_js)
        self.assertIn("function rehydrateTempMailSettingsFromCatalog", js_text)
        rehydrate_start = js_text.index("function rehydrateTempMailSettingsFromCatalog")
        rehydrate_end = js_text.index("function renderTempMailProviderOptions", rehydrate_start)
        rehydrate_js = js_text[rehydrate_start:rehydrate_end]
        self.assertIn("isTempMailSettingsProviderMountBound()", rehydrate_js)
        self.assertIn("onTempMailProviderChange", rehydrate_js)
        # Catalog load paths refresh Settings-only surfaces through a visibility gate.
        self.assertIn("function isSettingsModalVisible", js_text)
        self.assertIn("function refreshSettingsProviderSurfaces", js_text)
        catalog_start = js_text.index("async function loadMailboxProviderCatalog")
        catalog_end = js_text.index("function canonicalizeMailboxProviderAllowlistValue", catalog_start)
        catalog_js = js_text[catalog_start:catalog_end]
        self.assertIn("refreshSettingsProviderSurfaces(", catalog_js)
        self.assertIn("syncTempEmailProviderSelectWithCatalog()", catalog_js)
        self.assertIn("refreshAccountProviderTagsFromCatalog()", catalog_js)
        # Force supersedes soft in-flight; soft responses must not write after supersede.
        self.assertIn("let mailboxProviderCatalogLoadForce = false", js_text)
        self.assertIn("mailboxProviderCatalogLoadForce = force", catalog_js)
        self.assertIn("if (!force || mailboxProviderCatalogLoadForce)", catalog_js)
        self.assertIn("if (mailboxProviderCatalogPromise !== request)", catalog_js)
        self.assertIn("// Abandon soft in-flight bookkeeping; stale response identity check fails.", catalog_js)
        # Direct Settings-only renderers must not be called unguarded on catalog load.
        self.assertNotIn("renderProviderWorkbench(externalApiSettingsSnapshot, 'ready')", catalog_js)
        self.assertNotIn("renderExternalApiCommandCenter(externalApiSettingsSnapshot, 'ready')", catalog_js)
        self.assertNotIn("renderProviderDiagnostics();", catalog_js)
        self.assertNotIn("onTempMailProviderChange(getCurrentTempMailSettingsProviderSelection", catalog_js)
        refresh_start = js_text.index("function refreshSettingsProviderSurfaces")
        refresh_end = js_text.index("function renderTempMailProviderOptions", refresh_start)
        refresh_js = js_text[refresh_start:refresh_end]
        self.assertIn("isSettingsSurfaceActive()", refresh_js)
        self.assertNotIn("isSettingsModalVisible()", refresh_js)
        self.assertIn("paintApiSecuritySurfacesFromSnapshot(settingsSnapshot, workbenchState)", refresh_js)
        self.assertIn("rehydrateTempMailSettingsFromCatalog()", refresh_js)
        self.assertIn("let externalApiStarterMode = 'curl';", js_text)
        self.assertIn("let externalApiWorkflowKey = 'claim_pool_mailbox';", js_text)
        self.assertIn("let externalProviderRecipeKey = '';", js_text)
        self.assertIn("let externalApiContractCheckCache = null;", js_text)
        self.assertIn("let externalApiContractCheckPromise = null;", js_text)
        self.assertIn("let externalApiContractCheckLoadForce = false;", js_text)
        self.assertIn("let externalApiContractCheckState = { status: 'idle'", js_text)
        self.assertIn("let providerPreflightCache = null;", js_text)
        self.assertIn("let providerPreflightPromise = null;", js_text)
        self.assertIn("let providerPreflightState = { status: 'idle'", js_text)
        self.assertIn("const EXTERNAL_API_CANONICAL_PREFIX = '/api/v1/external';", js_text)
        self.assertIn("const EXTERNAL_API_LEGACY_PREFIX = '/api/external';", js_text)
        self.assertIn("function externalApiCanonicalPath", js_text)
        self.assertIn("function externalApiLegacyPath", js_text)
        self.assertIn("const EXTERNAL_API_COMMAND_ENDPOINTS", js_text)
        self.assertIn("{ key: 'integration_bundle', label: 'Integration Readiness Bundle'", js_text)
        self.assertIn("const EXTERNAL_API_STARTER_MODES", js_text)
        self.assertIn("async function loadProviderPreflightSnapshot", js_text)
        self.assertIn("function getProviderPreflightSnapshot", js_text)
        self.assertIn("function getProviderPreflightStatusLabel", js_text)
        self.assertIn("function renderProviderPreflightConsole", js_text)
        self.assertIn("function renderProviderPreflightProviderRow", js_text)
        self.assertIn("/api/providers/preflight", js_text)
        self.assertIn("/api/providers/preflight?probe_network=true", js_text)
        self.assertIn("data.provider_preflight", js_text)
        self.assertIn("data-provider-preflight-probe", js_text)
        self.assertIn("loadProviderPreflightSnapshot(true, false);", js_text)
        self.assertIn("loadProviderPreflightSnapshot(true, true);", js_text)
        self.assertIn("renderProviderPreflightConsole();", js_text)
        self.assertIn("function renderExternalApiCommandCenter", js_text)
        self.assertIn("function getExternalApiCommandStarterCommand", js_text)
        self.assertIn("function normalizeExternalApiStarterMode", js_text)
        self.assertIn("function setExternalApiStarterMode", js_text)
        self.assertIn("function getExternalApiStarterSnippet", js_text)
        self.assertIn("function getExternalIntegrationManifest", js_text)
        self.assertIn("function getExternalIntegrationManifestAuth", js_text)
        self.assertIn("function getExternalIntegrationManifestDiscovery", js_text)
        self.assertIn("function getExternalIntegrationManifestProviders", js_text)
        self.assertIn("function getExternalIntegrationManifestWorkflows", js_text)
        self.assertIn("function getExternalIntegrationManifestSourcePriority", js_text)
        self.assertIn("function getExternalIntegrationQuickstart", js_text)
        self.assertIn("function getExternalQuickstartAuth", js_text)
        self.assertIn("function getExternalQuickstartSequence", js_text)
        self.assertIn("function getExternalQuickstartSelectors", js_text)
        self.assertIn("function getExternalQuickstartRequests", js_text)
        self.assertIn("function renderExternalApiQuickstartCockpit", js_text)
        self.assertIn("function getExternalApiQuickstartText", js_text)
        self.assertIn("async function copyExternalApiQuickstart", js_text)
        self.assertIn("function getExternalApiSmokeCoverageItems", js_text)
        self.assertIn("function getExternalApiSmokeCommand", js_text)
        self.assertIn("function renderExternalApiSmokeCheckPanel", js_text)
        self.assertIn("async function copyExternalApiSmokeCommand", js_text)
        self.assertIn("async function loadExternalApiContractCheck", js_text)
        self.assertIn("/api/settings/external-api/contract-check", js_text)
        self.assertIn("data.contract_check", js_text)
        self.assertIn("function getExternalApiContractCheckSnapshot", js_text)
        self.assertIn("function getExternalApiContractCheckTone", js_text)
        self.assertIn("function renderExternalApiContractCheckPanel", js_text)
        self.assertIn("function renderExternalApiContractCheckGroup", js_text)
        self.assertIn("function renderExternalApiContractCheckRow", js_text)
        self.assertIn("data-external-api-contract-refresh", js_text)
        self.assertIn("loadExternalApiContractCheck(false);", js_text)
        self.assertIn("loadExternalApiContractCheck(true);", js_text)
        switch_tab_start = js_text.index("function switchSettingsTab")
        switch_tab_end = js_text.index("async function autoSaveSettings", switch_tab_start)
        switch_tab_text = js_text[switch_tab_start:switch_tab_end]
        self.assertIn("nextTab === 'api-security'", switch_tab_text)
        self.assertIn("loadExternalApiContractCheck(false);", switch_tab_text)
        self.assertIn("loadProviderPreflightSnapshot(false, false)", switch_tab_text)
        # loadSettings only soft-loads api-security network panels when already on that tab.
        load_settings_start = js_text.index("async function loadSettings(forceRefresh = false)")
        load_settings_end = js_text.index("console.error('loadSettings error:'", load_settings_start)
        load_settings_js = js_text[load_settings_start:load_settings_end]
        self.assertIn("currentSettingsTab === 'api-security'", load_settings_js)
        self.assertIn("loadProviderPreflightSnapshot(false, false)", load_settings_js)
        self.assertIn("loadExternalApiContractCheck(false)", load_settings_js)
        self.assertIn("loadOperationalReadinessSnapshot(false)", load_settings_js)
        self.assertIn("function getExternalApiBundleEndpointDescriptor", js_text)
        self.assertIn("function getExternalApiBundleCopyCommand", js_text)
        self.assertIn("function getExternalApiBundleSummaryCards", js_text)
        self.assertIn("function renderExternalApiBundleSummaryCard", js_text)
        self.assertIn("function renderExternalApiBundleEndpointRow", js_text)
        self.assertIn("function getExternalApiActionPlan", js_text)
        self.assertIn("function renderExternalApiActionPlan", js_text)
        self.assertIn("function renderExternalApiActionPlanItem", js_text)
        self.assertIn("function renderExternalApiBundleLaunchpad", js_text)
        self.assertIn("function formatExternalApiHandoffValue", js_text)
        self.assertIn("function getExternalApiHandoffDocs", js_text)
        self.assertIn("function getExternalApiHandoffSections", js_text)
        self.assertIn("function getExternalApiHandoffActionPlanLines", js_text)
        self.assertIn("function getExternalApiHandoffKitText", js_text)
        self.assertIn("function renderExternalApiHandoffKit", js_text)
        self.assertIn("function getExternalApiConsumerUsageItems", js_text)
        self.assertIn("function getExternalApiConsumerUsageSummary", js_text)
        self.assertIn("function renderExternalApiConsumerUsageConsole", js_text)
        self.assertIn("async function copyExternalApiHandoffKit", js_text)
        self.assertIn("let externalApiCommandRenderState = 'ready';", js_text)
        self.assertIn("async function copyExternalApiBundleCommand", js_text)
        self.assertIn("function getExternalProviderSelectionRecipes", js_text)
        self.assertIn("function normalizeExternalProviderRecipe", js_text)
        self.assertIn("function normalizeExternalProviderRecipeKey", js_text)
        self.assertIn("function getExternalProviderRecipeSecretEnvKeys", js_text)
        self.assertIn("function buildExternalProviderRecipeEnvSnippet", js_text)
        self.assertIn("function buildExternalProviderRecipeProviderEnvSnippet", js_text)
        self.assertIn("function renderExternalProviderRecipeGuide", js_text)
        self.assertIn("function getExternalProviderRecipeText", js_text)
        self.assertIn("function setExternalProviderRecipe", js_text)
        self.assertIn("async function copyExternalProviderRecipe", js_text)
        self.assertIn("function getExternalApiStarterDiscoverySteps", js_text)
        self.assertIn("function appendExternalApiStarterQuery", js_text)
        self.assertIn("function buildExternalApiStarterCurlSnippet", js_text)
        self.assertIn("function buildExternalApiStarterJavaScriptSnippet", js_text)
        self.assertIn("function buildExternalApiStarterPythonSnippet", js_text)
        self.assertIn("function buildExternalApiStarterEnvSnippet", js_text)
        self.assertIn("function syncExternalApiStarterModeButtons", js_text)
        self.assertIn("function renderExternalApiStarterModeButton", js_text)
        self.assertIn("function getExternalApiWorkflowFallbacks", js_text)
        self.assertIn("function getExternalApiWorkflowPlaybooks", js_text)
        self.assertIn("function normalizeExternalApiWorkflowKey", js_text)
        self.assertIn("function formatExternalApiWorkflowValue", js_text)
        self.assertIn("function renderExternalApiWorkflowPlaybooks", js_text)
        self.assertIn("function getExternalApiWorkflowPlaybookText", js_text)
        self.assertIn("function setExternalApiWorkflowPlaybook", js_text)
        self.assertIn("async function copyExternalApiWorkflowPlaybook", js_text)
        self.assertIn("function getExternalApiMailboxSessionWorkflow", js_text)
        self.assertIn("function getExternalApiMailboxSessionRequestExamples", js_text)
        self.assertIn("function getExternalApiMailboxSessionReadModes", js_text)
        self.assertIn("function renderExternalApiMailboxSessionLifecycle", js_text)
        self.assertIn("function getExternalApiMailboxSessionLifecycleText", js_text)
        self.assertIn("async function copyExternalApiMailboxSessionLifecycle", js_text)
        self.assertIn("function getExternalApiCommandPoolStatus", js_text)
        self.assertIn("function getExternalApiOnboardingSteps", js_text)
        self.assertIn("function renderExternalApiOnboardingChecklist", js_text)
        self.assertIn("async function copyExternalApiCommandSnippet", js_text)
        self.assertIn("{ key: 'curl', label: 'curl' }", js_text)
        self.assertIn("{ key: 'javascript', label: 'JavaScript' }", js_text)
        self.assertIn("{ key: 'python', label: 'Python' }", js_text)
        self.assertIn("{ key: 'env', label: '.env' }", js_text)
        self.assertIn("data-external-api-starter-mode", js_text)
        self.assertIn("externalApiStarterModeTarget", js_text)
        self.assertIn("setExternalApiStarterMode(externalApiStarterModeTarget.getAttribute('data-external-api-starter-mode')", js_text)
        self.assertIn("data-external-api-workflow-key", js_text)
        self.assertIn("data-external-api-workflow-copy", js_text)
        self.assertIn("data-external-api-quickstart-copy", js_text)
        self.assertIn("data-external-api-smoke-copy", js_text)
        self.assertIn("data-external-api-contract-refresh", js_text)
        self.assertIn("data-external-api-bundle-copy", js_text)
        self.assertIn("data-external-api-handoff-copy", js_text)
        self.assertIn("data-external-api-session-copy", js_text)
        self.assertIn("externalApiWorkflowTarget", js_text)
        self.assertIn("setExternalApiWorkflowPlaybook(externalApiWorkflowTarget.getAttribute('data-external-api-workflow-key')", js_text)
        self.assertIn("data-external-provider-recipe-key", js_text)
        self.assertIn("data-external-provider-recipe-copy", js_text)
        self.assertIn("externalProviderRecipeTarget", js_text)
        self.assertIn("setExternalProviderRecipe(externalProviderRecipeTarget.getAttribute('data-external-provider-recipe-key')", js_text)
        self.assertIn("external_api_disable_pool_claim_random", js_text)
        self.assertIn("external_api_disable_pool_stats", js_text)
        self.assertIn("部分启用", js_text)
        # Catalog/language paths go through visibility-gated refreshSettingsProviderSurfaces;
        # loadSettings paints api-security surfaces only when that tab is active.
        self.assertIn("refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'ready')", js_text)
        self.assertIn("refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'provider_error')", js_text)
        self.assertIn("paintApiSecuritySurfacesFromSnapshot(data.settings || {}, 'ready')", js_text)
        self.assertIn("updateProviderContractStateFromCatalog(data);", js_text)
        language_handler_start = js_text.index("window.addEventListener('ui-language-changed', () => {")
        language_handler_end = js_text.index("function formatAccountStatusLabel", language_handler_start)
        language_handler_text = js_text[language_handler_start:language_handler_end]
        self.assertIn("isSettingsSurfaceActive()", language_handler_text)
        self.assertIn("refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'ready')", language_handler_text)
        self.assertIn("currentSettingsTab === 'api-security'", language_handler_text)
        self.assertNotIn("renderProviderWorkbench(externalApiSettingsSnapshot, 'ready')", language_handler_text)
        self.assertIn("updateProviderContractStateFromCatalog({ mailbox_providers: [] });", js_text)
        self.assertIn("paintApiSecuritySurfacesFromSnapshot(data.settings || {}, 'ready')", js_text)
        # loadSettings gates api-security paint to that tab.
        load_settings_start = js_text.index("async function loadSettings(forceRefresh = false)")
        load_settings_end = js_text.index("console.error('loadSettings error:'", load_settings_start)
        load_settings_js = js_text[load_settings_start:load_settings_end]
        paint_pos = load_settings_js.index("paintApiSecuritySurfacesFromSnapshot(data.settings || {}, 'ready')")
        gate_pos = load_settings_js.index("currentSettingsTab === 'api-security'")
        self.assertLess(gate_pos, paint_pos)
        switch_tab_start = js_text.index("function switchSettingsTab")
        switch_tab_end = js_text.index("async function autoSaveSettings", switch_tab_start)
        switch_tab_js = js_text[switch_tab_start:switch_tab_end]
        self.assertIn("paintApiSecuritySurfacesFromSnapshot(externalApiSettingsSnapshot, 'ready')", switch_tab_js)
        self.assertLess(
            switch_tab_js.index("paintApiSecuritySurfacesFromSnapshot(externalApiSettingsSnapshot, 'ready')"),
            switch_tab_js.index("loadProviderPreflightSnapshot(false, false)"),
        )
        # Gate helper still owns the Settings-only render fan-out used by catalog/language paths.
        self.assertIn("function paintApiSecuritySurfacesFromSnapshot", js_text)
        paint_start = js_text.index("function paintApiSecuritySurfacesFromSnapshot")
        paint_end = js_text.index("function refreshSettingsProviderSurfaces", paint_start)
        paint_js = js_text[paint_start:paint_end]
        self.assertIn("renderPoolDefaultProviderDatalist()", paint_js)
        self.assertIn("renderActiveMailboxProviderSuggestions()", paint_js)
        self.assertIn("renderProviderDiagnostics()", paint_js)
        self.assertIn("renderProviderConfigTemplates()", paint_js)
        self.assertIn("renderProviderIntegrationGuide()", paint_js)
        self.assertIn("renderProviderContractStatus()", paint_js)
        self.assertIn("renderProviderWorkbench(settingsSnapshot, workbenchState)", paint_js)
        self.assertIn("renderExternalApiCommandCenter(settingsSnapshot, workbenchState)", paint_js)
        refresh_helper_start = js_text.index("function refreshSettingsProviderSurfaces")
        refresh_helper_end = js_text.index("function renderTempMailProviderOptions", refresh_helper_start)
        refresh_helper_js = js_text[refresh_helper_start:refresh_helper_end]
        self.assertIn("rehydrateTempMailSettingsFromCatalog()", refresh_helper_js)
        self.assertIn("currentSettingsTab !== 'api-security'", refresh_helper_js)
        self.assertIn("paintApiSecuritySurfacesFromSnapshot(settingsSnapshot, workbenchState)", refresh_helper_js)
        # Full api-security paint is after the tab gate.
        self.assertLess(
            refresh_helper_js.index("currentSettingsTab !== 'api-security'"),
            refresh_helper_js.index("paintApiSecuritySurfacesFromSnapshot(settingsSnapshot, workbenchState)"),
        )
        self.assertIn("externalApiSettingsSnapshot = data.settings || {};", js_text)
        workbench_start = js_text.index("function getProviderWorkbenchConfigFileStatus")
        workbench_end = js_text.index("function renderExternalApiCommandMetric", workbench_start)
        workbench_text = js_text[workbench_start:workbench_end]
        self.assertIn("getProviderWorkbenchRuntimeDefault", workbench_text)
        self.assertIn("settings.temp_mail_provider", workbench_text)
        self.assertIn("safeSettings.pool_default_provider", workbench_text)
        self.assertIn("renderProviderWorkbenchDiscovery(endpointMap.capabilities, sourcePriorityText)", workbench_text)
        self.assertLess(
            workbench_text.index("renderProviderWorkbenchMetric('运行默认'"),
            workbench_text.index("renderProviderWorkbenchMetric('默认领取来源'"),
        )
        self.assertLess(
            workbench_text.index("renderProviderWorkbenchMetric('默认领取来源'"),
            workbench_text.index("renderProviderWorkbenchMetric('路由模式'"),
        )
        self.assertIn("detail: translateAppTextLocal('Provider catalog 未加载')", js_text)
        self.assertIn("data-external-api-command-copy", js_text)
        self.assertIn("external-api-onboarding", js_text)
        self.assertIn("生成 API Key 后保存设置", js_text)
        self.assertIn("renderExternalApiWorkflowPlaybooks(workflowPlaybooks)", js_text)
        self.assertIn("renderExternalApiQuickstartCockpit()", js_text)
        self.assertIn("renderExternalApiMailboxSessionLifecycle()", js_text)
        self.assertIn("renderExternalApiSmokeCheckPanel()", js_text)
        self.assertIn("renderExternalApiContractCheckPanel()", js_text)
        self.assertIn("renderExternalApiActionPlan(actionPlan)", js_text)
        self.assertIn("copyTextToClipboard(quickstartText)", js_text)
        self.assertIn("copyTextToClipboard(smokeCommand)", js_text)
        self.assertIn("copyTextToClipboard(handoff)", js_text)
        self.assertIn("copyTextToClipboard(lifecycle)", js_text)
        self.assertIn("const workflowPlaybooks = getExternalApiWorkflowPlaybooks();", js_text)
        self.assertIn("renderExternalProviderRecipeGuide(providerRecipes)", js_text)
        self.assertIn("const providerRecipes = getExternalProviderSelectionRecipes();", js_text)
        self.assertIn("manifest.workflows", js_text)
        self.assertIn("manifest.selection_recipes", js_text)
        self.assertIn("selection.recipes", js_text)
        self.assertIn("guide.selection_recipes", js_text)
        self.assertIn("profile.selection_recipes", js_text)
        self.assertIn("poolClaimRelease", js_text)
        self.assertIn("poolClaimComplete", js_text)
        self.assertIn("integrationBundle", js_text)
        self.assertIn("verificationCode", js_text)
        self.assertIn("mailboxSessionStart", js_text)
        self.assertIn("mailboxSessionRead", js_text)
        self.assertIn("mailboxSessionClose", js_text)
        self.assertIn("tempMailFinish", js_text)
        self.assertIn('X-API-Key: <your-api-key>', js_text)
        self.assertNotIn("X-API-Key: ${", js_text)
        self.assertIn("OUTLOOK_EMAIL_EXTERNAL_API_BASE", js_text)
        self.assertIn("OUTLOOK_EMAIL_EXTERNAL_API_INTEGRATION_BUNDLE", js_text)
        self.assertIn("OUTLOOK_EMAIL_EXTERNAL_API_KEY=${auth.placeholder}", js_text)
        self.assertIn("OUTLOOK_EMAIL_EXTERNAL_API_MAILBOX_SESSION_START", js_text)
        self.assertIn("OUTLOOK_EMAIL_EXTERNAL_API_MAILBOX_SESSION_READ", js_text)
        self.assertIn("OUTLOOK_EMAIL_EXTERNAL_API_MAILBOX_SESSION_CLOSE", js_text)
        self.assertIn("TEMP_MAIL_PROVIDER=${tempMailDefault}", js_text)
        self.assertIn("ACTIVE_MAILBOX_PROVIDERS=${activeProviders.join(',')}", js_text)
        self.assertIn("# Provider env keys from current integration manifest", js_text)
        self.assertIn("# Provider env keys from current catalog", js_text)
        self.assertIn("copyTextToClipboard(command)", js_text)
        self.assertIn("const command = getExternalApiStarterSnippet(externalApiStarterMode, externalApiSettingsSnapshot);", js_text)
        self.assertIn("const smokeCommand = getExternalApiSmokeCommand();", js_text)
        self.assertIn("copyTextToClipboard(playbook)", js_text)
        self.assertIn("const playbook = getExternalApiWorkflowPlaybookText(externalApiWorkflowKey);", js_text)
        self.assertIn("copyTextToClipboard(recipe)", js_text)
        self.assertIn("const recipe = getExternalProviderRecipeText(externalProviderRecipeKey);", js_text)
        snippet_start = js_text.index("async function copyExternalApiCommandSnippet")
        snippet_end = js_text.index("function normalizeProviderIntegrationFilter", snippet_start)
        snippet_text = js_text[snippet_start:snippet_end]
        recipe_start = js_text.index("function normalizeExternalProviderRecipe")
        recipe_end = js_text.index("function getExternalApiCommandUrl", recipe_start)
        recipe_text = js_text[recipe_start:recipe_end]
        starter_start = js_text.index("function normalizeExternalApiStarterMode")
        starter_end = js_text.index("function getProviderWorkbenchConfigFileStatus", starter_start)
        starter_text = js_text[starter_start:starter_end]
        workflow_start = js_text.index("function getExternalApiWorkflowFallbacks")
        workflow_end = js_text.index("function getProviderWorkbenchConfigFileStatus", workflow_start)
        workflow_text = js_text[workflow_start:workflow_end]
        workflow_copy_start = js_text.index("function getExternalApiWorkflowPlaybookText")
        workflow_copy_end = js_text.index("function getProviderWorkbenchConfigFileStatus", workflow_copy_start)
        workflow_copy_text = js_text[workflow_copy_start:workflow_copy_end]
        session_start = js_text.index("function getExternalApiMailboxSessionWorkflow")
        session_end = js_text.index("function normalizeProviderContractSummary", session_start)
        session_text = js_text[session_start:session_end]
        manifest_workflow_start = js_text.index("function getExternalIntegrationManifestWorkflows")
        manifest_workflow_end = js_text.index("function getExternalIntegrationManifestSourcePriority", manifest_workflow_start)
        manifest_workflow_text = js_text[manifest_workflow_start:manifest_workflow_end]
        quickstart_start = js_text.index("function getExternalIntegrationQuickstart")
        quickstart_end = js_text.index("function normalizeExternalProviderRecipe", quickstart_start)
        quickstart_text = js_text[quickstart_start:quickstart_end]
        smoke_start = js_text.index("function getExternalApiSmokeCoverageItems")
        smoke_end = js_text.index("function getOperationalReadinessMailboxSnapshot", smoke_start)
        smoke_text = js_text[smoke_start:smoke_end]
        contract_start = js_text.index("function getExternalApiContractCheckSnapshot")
        contract_end = js_text.index("function getExternalApiBundleEndpointDescriptor", contract_start)
        contract_text = js_text[contract_start:contract_end]
        handoff_start = js_text.index("function formatExternalApiHandoffValue")
        handoff_end = js_text.index("function getOperationalReadinessMailboxSnapshot", handoff_start)
        handoff_text = js_text[handoff_start:handoff_end]
        self.assertIn("OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key>", smoke_text)
        self.assertIn("python scripts/external_api_smoke.py", smoke_text)
        self.assertIn("--base-url", smoke_text)
        self.assertIn("externalApiCanonicalPath('/health')", smoke_text)
        self.assertIn("externalApiCanonicalPath('/capabilities')", smoke_text)
        self.assertIn("externalApiCanonicalPath('/providers')", smoke_text)
        self.assertIn("externalApiCanonicalPath('/mailboxes')", smoke_text)
        self.assertIn("?page_size=1", smoke_text)
        self.assertIn("externalApiCanonicalPath('/openapi.json')", smoke_text)
        self.assertIn("external-api-smoke-check", smoke_text)
        self.assertIn("external-api-smoke-command", smoke_text)
        self.assertIn("data-external-api-smoke-copy", smoke_text)
        self.assertIn("contract_check", contract_text)
        self.assertIn("summary.failed", contract_text)
        self.assertIn("network_probes", contract_text)
        self.assertIn("mutation_safe", contract_text)
        self.assertIn("external-api-contract-check", contract_text)
        self.assertIn("external-api-contract-groups", contract_text)
        self.assertIn("data-external-api-contract-refresh", contract_text)
        self.assertNotIn("/api/v1/external/", contract_text)
        self.assertNotIn("/api/v1/external/", contract_text)
        self.assertIn("getExternalIntegrationManifestAuth()", handoff_text)
        self.assertIn("getExternalIntegrationQuickstart()", handoff_text)
        self.assertIn("getExternalApiSmokeCommand()", handoff_text)
        self.assertIn("getExternalApiActionPlan(settings, state, providerSummary)", handoff_text)
        self.assertIn("getExternalApiMailboxSessionRequestExamples()", handoff_text)
        self.assertIn("getExternalApiStarterBaseUrl()", handoff_text)
        self.assertIn("getExternalApiCommandUrl(sections.bundle.canonical)", handoff_text)
        self.assertIn("X-API-Key: <your-api-key>", handoff_text)
        self.assertIn("mailbox_session_start", handoff_text)
        self.assertIn("mailbox_session_read", handoff_text)
        self.assertIn("mailbox_session_close", handoff_text)
        self.assertIn("docs/external-integration-quickstart.md", handoff_text)
        self.assertIn("docs/provider-onboarding.md", handoff_text)
        self.assertIn("External Integration Handoff Kit", handoff_text)
        self.assertIn("data-external-api-handoff-copy", handoff_text)
        self.assertIn("mailboxProviderIntegrationQuickstartCache", quickstart_text)
        self.assertIn("manifest.quickstart", quickstart_text)
        self.assertIn("provider_selector_fields", quickstart_text)
        self.assertIn("recommended_sequence", quickstart_text)
        self.assertIn("requests.pool_claim", quickstart_text)
        self.assertIn("requests.task_temp_apply", quickstart_text)
        self.assertIn("requests.mailbox_session_start", quickstart_text)
        self.assertIn("requests.mailbox_session_read", quickstart_text)
        self.assertIn("requests.mailbox_session_close", quickstart_text)
        self.assertIn("<your-api-key>", quickstart_text)
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", quickstart_text)
        self.assertIn("getExternalIntegrationManifestAuth()", starter_text)
        self.assertIn("getExternalIntegrationManifestDiscovery()", starter_text)
        self.assertIn("getExternalIntegrationManifestProviders()", starter_text)
        self.assertIn("auth.placeholder", starter_text)
        self.assertIn("auth.curlHeader", starter_text)
        self.assertIn("discovery.recommended_sequence", starter_text)
        self.assertIn("const methodArg = method && method !== 'GET'", starter_text)
        self.assertIn('"${url}"', starter_text)
        self.assertIn("item.env", starter_text)
        self.assertIn("addExternalIntegrationManifestEnvLine(lines, hint)", starter_text)
        self.assertIn("addExternalIntegrationRequestFieldLines(manifestLines, item.request_fields)", starter_text)
        self.assertIn("getProviderIntegrationGuideProviders()", starter_text)
        self.assertIn("getProviderIntegrationSecretKeySets(item).env", starter_text)
        self.assertIn("addProviderIntegrationEnvLine(lines, key, envDefaults[key], secretKeys)", starter_text)
        self.assertLess(
            starter_text.index("const manifestProviders = getExternalIntegrationManifestProviders();"),
            starter_text.index("const providers = getProviderIntegrationGuideProviders();"),
        )
        self.assertIn("getExternalIntegrationManifestWorkflows()", workflow_text)
        self.assertIn(".map(normalizeExternalApiWorkflow)", workflow_text)
        self.assertLess(
            workflow_text.index("const manifestWorkflows = getExternalIntegrationManifestWorkflows()"),
            workflow_text.index("return getExternalApiWorkflowFallbacks()"),
        )
        self.assertIn("request.provider_selector", workflow_text)
        self.assertIn("provider selector:", workflow_text)
        self.assertIn("formatExternalApiWorkflowValue(value[key])", workflow_text)
        self.assertIn("# Auth: ${auth.header}: ${auth.placeholder}", workflow_copy_text)
        self.assertIn("requestHints.join(' | ')", workflow_copy_text)
        self.assertIn("manifest.workflows", manifest_workflow_text)
        self.assertIn("start_mailbox_session", workflow_text)
        self.assertIn("mailboxSessionRead", workflow_text)
        self.assertIn("externalApiCanonicalPath('/mailbox-sessions/read')", js_text)
        self.assertIn("session_type: 'pool_claim'", session_text)
        self.assertIn("session_type: 'task_temp_mailbox'", session_text)
        self.assertIn("claim_token: '<claim-token>'", session_text)
        self.assertIn("task_token: '<task-token>'", session_text)
        self.assertIn("read_action: 'verification_code'", session_text)
        self.assertIn("read_action: 'latest_message'", session_text)
        self.assertIn("# Mailbox session lifecycle", session_text)
        self.assertIn("manifest.selection_recipes", recipe_text)
        self.assertIn("manifest.selection_recipe_index", recipe_text)
        self.assertIn("selection.recipes", recipe_text)
        self.assertIn("selection.recipe_index", recipe_text)
        self.assertIn("guide.selection_recipes", recipe_text)
        self.assertIn("profile.selection_recipes", recipe_text)
        self.assertIn("item.secret === true ? ''", recipe_text)
        self.assertIn("secretKeys.has(envKey) ? ''", recipe_text)
        self.assertIn("# auth: ${auth.header}: ${auth.placeholder}", recipe_text)
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, snippet_text)
            self.assertNotIn(secret_input_id, smoke_text)
            self.assertNotIn(secret_input_id, starter_text)
            self.assertNotIn(secret_input_id, workflow_text)
            self.assertNotIn(secret_input_id, workflow_copy_text)
            self.assertNotIn(secret_input_id, session_text)
            self.assertNotIn(secret_input_id, recipe_text)
            self.assertNotIn(secret_input_id, handoff_text)
            self.assertNotIn(secret_input_id, contract_text)
        for provider_name in [
            "duckmail",
            "mail_tm",
            "emailnator",
            "gptmail",
            "tempmail_lol",
        ]:
            self.assertNotIn(provider_name, workflow_text.lower())
            self.assertNotIn(provider_name, session_text.lower())
            self.assertNotIn(provider_name, recipe_text.lower())
            self.assertNotIn(provider_name, handoff_text.lower())
            self.assertNotIn(provider_name, contract_text.lower())
        workbench_start = js_text.index("function getProviderWorkbenchConfigFileStatus")
        workbench_end = js_text.index("function renderExternalApiCommandMetric", workbench_start)
        workbench_text = js_text[workbench_start:workbench_end]
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, workbench_text)
        onboarding_start = js_text.index("function getExternalApiOnboardingSteps")
        onboarding_end = js_text.index("function renderExternalApiCommandCenter", onboarding_start)
        onboarding_text = js_text[onboarding_start:onboarding_end]
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, onboarding_text)
        command_center_start = js_text.index("function renderExternalApiCommandCenter")
        command_center_end = js_text.index("async function copyExternalApiQuickstart", command_center_start)
        command_center_text = js_text[command_center_start:command_center_end]
        self.assertLess(
            command_center_text.index("renderExternalApiOnboardingChecklist(onboardingSteps)"),
            command_center_text.index("'<div class=\"external-api-command-metrics\">'"),
        )
        self.assertLess(
            command_center_text.index("'<div class=\"external-api-command-metrics\">'"),
            command_center_text.index("renderExternalApiSmokeCheckPanel()"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiSmokeCheckPanel()"),
            command_center_text.index("renderExternalApiContractCheckPanel()"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiContractCheckPanel()"),
            command_center_text.index("renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary)"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary)"),
            command_center_text.index("renderExternalApiHandoffKit(safeSettings, renderState, providerSummary)"),
        )
        self.assertIn("external-api-advanced-tools", command_center_text)
        self.assertIn("external-api-contract-details", js_text)
        self.assertIn("mailboxProviderDiagnosticsCache", workbench_text)
        self.assertIn("mailboxProviderDeploymentProfileCache", workbench_text)
        self.assertIn("mailboxProviderIntegrationGuideCache", workbench_text)
        self.assertIn("externalApiSettingsSnapshot", js_text)

    def test_provider_contract_status_ui_consumes_catalog_and_plugin_summaries(self):
        """Provider 扩展契约状态应由 catalog/plugin payload 驱动且不读取密钥输入。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()
        plugin_js = self._get_text(client, "/static/js/features/plugins.js")

        self.assertIn("let providerContractState =", js_text)
        self.assertIn("function updateProviderContractStateFromCatalog", js_text)
        self.assertIn("function updateProviderContractStateFromPlugins", js_text)
        self.assertIn("function getProviderContractCatalogRows", js_text)
        self.assertIn("function getProviderContractPluginMap", js_text)
        self.assertIn("function normalizeProviderContractSummary", js_text)
        self.assertIn("function getProviderContractStatusTone", js_text)
        self.assertIn("function renderProviderContractCounter", js_text)
        self.assertIn("function renderProviderContractRow", js_text)
        self.assertIn("function renderProviderContractStatus", js_text)
        # Contract rows prefer shared catalog labels when available.
        self.assertIn("resolveMailboxProviderLabel(row.provider", js_text)
        self.assertIn("provider.contract_validation", js_text)
        self.assertIn("plugin.contract_validation", js_text)
        self.assertIn("issue_codes", js_text)
        self.assertIn("summary.errors", js_text)
        self.assertIn("summary.warnings", js_text)
        self.assertIn("summary.checks", js_text)
        self.assertIn("status === 'invalid'", js_text)
        self.assertIn("status === 'warning'", js_text)
        self.assertIn("status === 'valid'", js_text)
        self.assertIn("if (normalized === 'valid') return translateAppTextLocal('契约有效');", js_text)
        self.assertIn("if (normalized === 'warning') return translateAppTextLocal('契约告警');", js_text)
        self.assertIn("if (normalized === 'invalid') return translateAppTextLocal('契约无效');", js_text)
        self.assertIn("getProviderContractPluginMap", js_text)
        self.assertIn("updateProviderContractStateFromPlugins(_plugins)", plugin_js)
        # Plugin list soft-refreshes catalog; apply/uninstall can force-refresh.
        self.assertIn("async function _refreshMailboxProviderCatalogFromPlugins", plugin_js)
        self.assertIn("await loadMailboxProviderCatalog(Boolean(forceRefresh || emptyWarmCache))", plugin_js)
        self.assertIn("await _refreshMailboxProviderCatalogFromPlugins(forceCatalogRefresh)", plugin_js)
        self.assertIn("loadPlugins({ forceCatalogRefresh: true })", plugin_js)
        # Plugin list / temp-mail controls are deferred to temp-mail Settings tab.
        self.assertIn("function ensureTempMailPluginsReady", js_text)
        self.assertIn("function ensureTempMailSettingsTabReady", js_text)
        self.assertIn("PluginManager.ensureLoaded", js_text)
        self.assertIn("async function showSettingsModal", js_text)
        show_start = js_text.index("async function showSettingsModal")
        show_end = js_text.index("function hideSettingsModal", show_start)
        show_js = js_text[show_start:show_end]
        self.assertIn("await loadSettings()", show_js)
        self.assertNotIn("ensureSettingsSurfaceReady", show_js)
        self.assertNotIn("ensureTempMailSettingsTabReady()", show_js)
        switch_tab_start = js_text.index("function switchSettingsTab")
        switch_tab_end = js_text.index("async function autoSaveSettings", switch_tab_start)
        switch_tab_js = js_text[switch_tab_start:switch_tab_end]
        self.assertIn("nextTab === 'temp-mail'", switch_tab_js)
        self.assertIn("ensureTempMailSettingsTabReady()", switch_tab_js)
        self.assertIn("applyTempMailSettingsSelection(", switch_tab_js)
        self.assertIn("nextTab === 'automation'", switch_tab_js)
        self.assertIn("ensureAutomationSettingsTabReady()", switch_tab_js)
        self.assertIn("updateProviderContractStateFromPlugins([])", plugin_js)

        contract_start = js_text.index("function getProviderContractCatalogRows")
        contract_end = js_text.index("function getProviderWorkbenchConfigFileStatus", contract_start)
        contract_text = js_text[contract_start:contract_end]
        self.assertIn("mailbox_providers", contract_text)
        self.assertIn("provider_integration_guide", contract_text)
        self.assertIn("contract_validation", contract_text)
        self.assertNotIn("safe_metadata", contract_text)
        self.assertNotIn("config_fields", contract_text)
        self.assertNotIn("checks.map", contract_text)
        self.assertNotIn("issues.map", contract_text)
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, contract_text)
        for provider_name in [
            "duckmail",
            "mail_tm",
            "emailnator",
            "gptmail",
            "tempmail_lol",
        ]:
            self.assertNotIn(provider_name, contract_text.lower())

    def test_external_api_operational_readiness_console_contract(self):
        """外部 API 指挥台应聚合本地运行就绪状态且不读取密钥输入。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("let operationalReadinessSnapshotCache = null;", js_text)
        self.assertIn("let operationalReadinessSnapshotPromise = null;", js_text)
        self.assertIn("let operationalReadinessSnapshotLoadForce = false;", js_text)
        self.assertIn("async function loadOperationalReadinessSnapshot", js_text)
        self.assertIn("/api/mailboxes?${params.toString()}", js_text)
        self.assertIn("page_size: '1'", js_text)
        self.assertIn("function getOperationalReadinessMailboxSnapshot", js_text)
        self.assertIn("function getOperationalReadinessCards", js_text)
        self.assertIn("function getOperationalReadinessTaskTempStatus", js_text)
        self.assertIn("function renderOperationalReadinessConsole", js_text)
        self.assertIn("operationalReadinessSnapshotCache = {", js_text)
        self.assertIn("provider_context: data.provider_context", js_text)
        self.assertIn("summary: data.summary", js_text)
        command_center_start = js_text.index("function renderExternalApiCommandCenter")
        command_center_end = js_text.index("async function copyExternalApiQuickstart", command_center_start)
        command_center_text = js_text[command_center_start:command_center_end]
        self.assertIn("renderOperationalReadinessConsole(safeSettings, renderState)", command_center_text)
        self.assertLess(
            command_center_text.index("renderOperationalReadinessConsole(safeSettings, renderState)"),
            command_center_text.index("renderExternalApiQuickstartCockpit()"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiQuickstartCockpit()"),
            command_center_text.index("renderExternalApiMailboxSessionLifecycle()"),
        )
        self.assertIn("loadOperationalReadinessSnapshot(true);", js_text)
        self.assertIn("loadOperationalReadinessSnapshot(false);", js_text)
        readiness_load_start = js_text.index("async function loadOperationalReadinessSnapshot")
        readiness_load_end = js_text.index("async function loadExternalApiContractCheck", readiness_load_start)
        readiness_load = js_text[readiness_load_start:readiness_load_end]
        # Soft warm path re-paints command center without network (api-security surface only).
        self.assertIn("!force && operationalReadinessSnapshotCache", readiness_load)
        self.assertIn("function isCurrentApiSecuritySurface()", js_text)
        self.assertIn("isCurrentApiSecuritySurface()", readiness_load)
        self.assertIn(
            "renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready')",
            readiness_load,
        )

        readiness_start = js_text.index("function getOperationalReadinessMailboxSnapshot")
        readiness_end = js_text.index("function renderExternalApiCommandCenter", readiness_start)
        readiness_text = js_text[readiness_start:readiness_end]
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, readiness_text)
        for provider_name in [
            "duckmail",
            "mail_tm",
            "emailnator",
            "gptmail",
            "tempmail_lol",
        ]:
            self.assertNotIn(provider_name, readiness_text.lower())

    def test_external_api_contract_check_console_contract_is_local_and_secret_safe(self):
        """外部 API 契约校验面板应只消费管理端本地报告且不读取密钥输入。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("let externalApiContractCheckCache = null;", js_text)
        self.assertIn("let externalApiContractCheckPromise = null;", js_text)
        self.assertIn("let externalApiContractCheckLoadForce = false;", js_text)
        self.assertIn("let externalApiContractCheckState = { status: 'idle'", js_text)
        self.assertIn("async function loadExternalApiContractCheck", js_text)
        self.assertIn("/api/settings/external-api/contract-check", js_text)
        self.assertIn("function getExternalApiContractCheckSnapshot", js_text)
        self.assertIn("function getExternalApiContractCheckTone", js_text)
        self.assertIn("function renderExternalApiContractCheckPanel", js_text)
        self.assertIn("function renderExternalApiContractCheckGroup", js_text)
        self.assertIn("function renderExternalApiContractCheckRow", js_text)
        self.assertIn("function renderExternalApiContractCheckAction", js_text)
        self.assertIn("summary.critical", js_text)
        self.assertIn("report.local_only", js_text)
        self.assertIn("report.network_probes", js_text)
        self.assertIn("report.mutation_safe", js_text)
        self.assertIn("data-external-api-contract-refresh", js_text)
        self.assertIn("externalApiContractRefreshTarget", js_text)
        self.assertIn("loadExternalApiContractCheck(false);", js_text)
        self.assertIn("loadExternalApiContractCheck(true);", js_text)
        contract_load_start = js_text.index("async function loadExternalApiContractCheck")
        contract_load_end = js_text.index(
            "async function loadProviderPreflightSnapshot",
            contract_load_start,
        ) if "async function loadProviderPreflightSnapshot" in js_text[contract_load_start:] else js_text.index(
            "function getExternalApiContractCheckSnapshot",
            contract_load_start,
        )
        contract_load = js_text[contract_load_start:contract_load_end]
        # Soft warm path re-paints command center without network (api-security surface only).
        self.assertIn("!force && externalApiContractCheckCache", contract_load)
        self.assertIn("isCurrentApiSecuritySurface()", contract_load)
        self.assertIn(
            "renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready')",
            contract_load,
        )
        switch_tab_start = js_text.index("function switchSettingsTab")
        switch_tab_end = js_text.index("async function autoSaveSettings", switch_tab_start)
        switch_tab_text = js_text[switch_tab_start:switch_tab_end]
        self.assertIn("nextTab === 'api-security'", switch_tab_text)
        self.assertIn("loadExternalApiContractCheck(false);", switch_tab_text)
        # loadSettings gates these network loads to the api-security tab.
        load_settings_start = js_text.index("async function loadSettings(forceRefresh = false)")
        load_settings_end = js_text.index("console.error('loadSettings error:'", load_settings_start)
        load_settings_js = js_text[load_settings_start:load_settings_end]
        self.assertIn("currentSettingsTab === 'api-security'", load_settings_js)

        command_center_start = js_text.index("function renderExternalApiCommandCenter")
        command_center_end = js_text.index("async function copyExternalApiQuickstart", command_center_start)
        command_center_text = js_text[command_center_start:command_center_end]
        self.assertLess(
            command_center_text.index("renderExternalApiSmokeCheckPanel()"),
            command_center_text.index("renderExternalApiContractCheckPanel()"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiContractCheckPanel()"),
            command_center_text.index("renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary)"),
        )

        contract_start = js_text.index("function getExternalApiContractCheckSnapshot")
        contract_end = js_text.index("function getExternalApiBundleEndpointDescriptor", contract_start)
        contract_text = js_text[contract_start:contract_end]
        self.assertIn("contract_check", contract_text)
        self.assertIn("external-api-contract-check", contract_text)
        self.assertIn("external-api-contract-summary", contract_text)
        self.assertIn("external-api-contract-groups", contract_text)
        self.assertIn("external-api-contract-actions", contract_text)
        self.assertNotIn("document.getElementById", contract_text)
        self.assertNotIn("/api/v1/external/", contract_text)
        self.assertNotIn("/api/v1/external/", contract_text)
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, contract_text)
        for provider_name in [
            "duckmail",
            "mail_tm",
            "emailnator",
            "gptmail",
            "tempmail_lol",
        ]:
            self.assertNotIn(provider_name, contract_text.lower())

    def test_external_api_bundle_launchpad_contract_is_secret_safe(self):
        """外部接入指挥台应把 integration bundle 作为安全的一站式启动入口。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("{ key: 'integration_bundle', label: 'Integration Readiness Bundle'", js_text)
        self.assertIn("path: externalApiCanonicalPath('/integration-bundle')", js_text)
        self.assertIn("externalApiLegacyPath('/integration-bundle')", js_text)
        self.assertIn("integrationBundle: getExternalApiStarterManifestEndpoint", js_text)
        self.assertIn("{ key: 'integration_bundle', label: 'Bundle', endpoint: externalApiCanonicalPath('/integration-bundle') }", js_text)
        self.assertIn("function getExternalApiBundleEndpointDescriptor", js_text)
        self.assertIn("function getExternalApiBundleCopyCommand", js_text)
        self.assertIn("function getExternalApiBundleSummaryCards", js_text)
        self.assertIn("function getExternalApiActionPlan", js_text)
        self.assertIn("function renderExternalApiActionPlan", js_text)
        self.assertIn("function renderExternalApiActionPlanItem", js_text)
        self.assertIn("function renderExternalApiBundleLaunchpad", js_text)
        self.assertIn("function getExternalApiHandoffSections", js_text)
        self.assertIn("function getExternalApiHandoffKitText", js_text)
        self.assertIn("function renderExternalApiHandoffKit", js_text)
        self.assertIn("async function copyExternalApiHandoffKit", js_text)
        self.assertIn("data-external-api-bundle-copy", js_text)
        self.assertIn("data-external-api-handoff-copy", js_text)
        self.assertIn("async function copyExternalApiBundleCommand", js_text)
        self.assertIn("copyTextToClipboard(command)", js_text)
        self.assertIn("copyTextToClipboard(handoff)", js_text)
        self.assertIn("Bundle 命令已复制", js_text)
        self.assertIn("交接包已复制", js_text)
        self.assertIn("X-API-Key: <your-api-key>", js_text)

        command_center_start = js_text.index("function renderExternalApiCommandCenter")
        command_center_end = js_text.index("async function copyExternalApiQuickstart", command_center_start)
        command_center_text = js_text[command_center_start:command_center_end]
        # Primary band first (metrics), then checks; advanced tools stay later (collapsed).
        self.assertLess(
            command_center_text.index("'<div class=\"external-api-command-metrics\">'"),
            command_center_text.index("renderExternalApiSmokeCheckPanel()"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiSmokeCheckPanel()"),
            command_center_text.index("renderExternalApiContractCheckPanel()"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiContractCheckPanel()"),
            command_center_text.index("renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary)"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary)"),
            command_center_text.index("renderExternalApiHandoffKit(safeSettings, renderState, providerSummary)"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiHandoffKit(safeSettings, renderState, providerSummary)"),
            command_center_text.index("renderExternalApiConsumerUsageConsole(safeSettings)"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary)"),
            command_center_text.index("renderOperationalReadinessConsole(safeSettings, renderState)"),
        )
        self.assertIn("external-api-advanced-tools", command_center_text)

        bundle_start = js_text.index("function getExternalApiBundleEndpointDescriptor")
        bundle_end = js_text.index("function getOperationalReadinessMailboxSnapshot", bundle_start)
        bundle_text = js_text[bundle_start:bundle_end]
        self.assertIn("getExternalIntegrationManifestAuth()", bundle_text)
        self.assertIn("getOperationalReadinessMailboxSnapshot()", bundle_text)
        self.assertIn("getExternalApiCommandProviderSummary(state)", bundle_text)
        self.assertIn("getExternalApiCommandAccessStatus(safeSettings)", bundle_text)
        self.assertIn("getExternalApiActionPlan(settings, state, providerSummary)", bundle_text)
        self.assertIn("getExternalApiSmokeCommand()", bundle_text)
        self.assertIn("start_mailbox_session", bundle_text)
        self.assertIn("run_smoke_check", bundle_text)
        self.assertNotIn("document.getElementById", bundle_text)

        handoff_start = js_text.index("function formatExternalApiHandoffValue")
        handoff_end = js_text.index("function getOperationalReadinessMailboxSnapshot", handoff_start)
        handoff_text = js_text[handoff_start:handoff_end]
        self.assertIn("getExternalIntegrationManifestAuth()", handoff_text)
        self.assertIn("getExternalIntegrationQuickstart()", handoff_text)
        self.assertIn("getExternalApiBundleEndpointDescriptor(endpointMap)", handoff_text)
        self.assertIn("getExternalApiSmokeCommand()", handoff_text)
        self.assertIn("getExternalApiActionPlan(settings, state, providerSummary)", handoff_text)
        self.assertIn("getExternalApiMailboxSessionRequestExamples()", handoff_text)
        self.assertIn("X-API-Key: <your-api-key>", handoff_text)
        self.assertIn("mailbox_session_start", handoff_text)
        self.assertIn("mailbox_session_read", handoff_text)
        self.assertIn("mailbox_session_close", handoff_text)
        self.assertIn("docs/external-integration-quickstart.md", handoff_text)
        self.assertNotIn("document.getElementById", handoff_text)
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, bundle_text)
            self.assertNotIn(secret_input_id, handoff_text)
        for provider_branch in [
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
        ]:
            self.assertNotIn(provider_branch, bundle_text)
            self.assertNotIn(provider_branch, handoff_text)

        click_start = js_text.index("document.addEventListener('click'")
        click_end = js_text.index("if (typeof window !== 'undefined')", click_start)
        click_text = js_text[click_start:click_end]
        self.assertIn("externalApiBundleCopyTarget", click_text)
        self.assertIn("copyExternalApiBundleCommand();", click_text)
        self.assertIn("externalApiHandoffCopyTarget", click_text)
        self.assertIn("copyExternalApiHandoffKit();", click_text)

    def test_external_api_consumer_usage_console_contract_is_safe(self):
        """外部 API 消费方用量台应只消费 settings 安全字段，不读取密钥输入。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        for helper in [
            "function normalizeExternalApiConsumerUsageCount",
            "function normalizeExternalApiConsumerUsageBool",
            "function getExternalApiConsumerUsageItems",
            "function getExternalApiConsumerUsageTone",
            "function getExternalApiConsumerUsageStatusLabel",
            "function getExternalApiConsumerUsageBadgeClass",
            "function getExternalApiConsumerScopeText",
            "function formatExternalApiConsumerLastUsed",
            "function getExternalApiConsumerUsageSummary",
            "function renderExternalApiConsumerSummaryMetric",
            "function renderExternalApiConsumerUsageCard",
            "function renderExternalApiConsumerUsageConsole",
        ]:
            self.assertIn(helper, js_text)

        consumer_start = js_text.index("function normalizeExternalApiConsumerUsageCount")
        consumer_end = js_text.index("function getOperationalReadinessMailboxSnapshot", consumer_start)
        consumer_text = js_text[consumer_start:consumer_end]
        self.assertIn("safeSettings.external_api_keys", consumer_text)
        self.assertIn("source.consumer_key", consumer_text)
        self.assertIn("source.allowed_emails", consumer_text)
        self.assertIn("source.today_total_count", consumer_text)
        self.assertIn("source.today_success_count", consumer_text)
        self.assertIn("source.today_error_count", consumer_text)
        self.assertIn("source.today_last_used_at || source.last_used_at", consumer_text)
        self.assertIn("external-api-consumer-console", consumer_text)
        self.assertIn("external-api-consumer-summary", consumer_text)
        self.assertIn("external-api-consumer-card", consumer_text)
        self.assertIn("data-tone=", consumer_text)
        self.assertIn("badge-red", consumer_text)
        self.assertIn("badge-green", consumer_text)
        self.assertIn("badge-gray", consumer_text)
        self.assertIn("badge-gold", consumer_text)
        self.assertIn("今日有错误", consumer_text)
        self.assertIn("今日未调用", consumer_text)
        self.assertIn("暂无多 Key 消费方", consumer_text)
        self.assertIn("'总计'", consumer_text)
        self.assertIn("'成功数'", consumer_text)
        self.assertIn("'错误数'", consumer_text)
        self.assertIn("'请求数'", consumer_text)
        self.assertIn("formatUiDateTime(lastUsedAt", consumer_text)

        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "source.api_key",
            "source.api_key_masked",
            ".api_key",
            ".api_key_masked",
            "document.getElementById",
            "'configured'",
            "'requests'",
            "'total'",
            "'success'",
            "'error'",
        ]:
            self.assertNotIn(forbidden, consumer_text)

        command_center_start = js_text.index("function renderExternalApiCommandCenter")
        command_center_end = js_text.index("async function copyExternalApiQuickstart", command_center_start)
        command_center_text = js_text[command_center_start:command_center_end]
        self.assertLess(
            command_center_text.index("renderExternalApiHandoffKit(safeSettings, renderState, providerSummary)"),
            command_center_text.index("renderExternalApiConsumerUsageConsole(safeSettings)"),
        )
        self.assertLess(
            command_center_text.index("'<div class=\"external-api-command-metrics\">'"),
            command_center_text.index("renderExternalApiConsumerUsageConsole(safeSettings)"),
        )
        self.assertLess(
            command_center_text.index("renderExternalApiConsumerUsageConsole(safeSettings)"),
            command_center_text.index("renderOperationalReadinessConsole(safeSettings, renderState)"),
        )
        self.assertIn("external-api-advanced-tools", command_center_text)

    def test_provider_preflight_console_contract_is_secret_safe_and_provider_agnostic(self):
        """Provider 批量预检 UI 应只读 authenticated preflight payload 且不读取密钥输入。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        loader_start = js_text.index("async function loadProviderPreflightSnapshot")
        loader_end = js_text.index("function updateTempMailProviderStatusBadges", loader_start)
        loader_text = js_text[loader_start:loader_end]
        self.assertIn("/api/providers/preflight", loader_text)
        self.assertIn("/api/providers/preflight?probe_network=true", loader_text)
        self.assertIn("provider_preflight", loader_text)
        self.assertIn("fetch(endpoint, { cache: 'no-store' })", loader_text)
        self.assertNotIn("/api/v1/external/providers/preflight", loader_text)
        # Force/probe supersedes soft in-flight; abandoned soft must not write cache.
        self.assertIn("let providerPreflightLoadForce = false", js_text)
        self.assertIn("providerPreflightLoadForce = force", loader_text)
        self.assertIn("if (!force || providerPreflightLoadForce)", loader_text)
        self.assertIn("providerPreflightPromise !== request", loader_text)
        self.assertIn("// Abandon soft in-flight bookkeeping; identity check blocks stale apply.", loader_text)
        # Paint preflight console only while api-security Settings tab is active.
        self.assertIn("isCurrentApiSecuritySurface()", loader_text)
        self.assertIn("if (isCurrentApiSecuritySurface())", loader_text)

        preflight_start = js_text.index("function getProviderPreflightSnapshot")
        preflight_end = js_text.index("function getProviderWorkbenchConfigFileStatus", preflight_start)
        preflight_text = js_text[preflight_start:preflight_end]
        self.assertIn("summary.total", preflight_text)
        self.assertIn("summary.ready", preflight_text)
        self.assertIn("summary.needs_config", preflight_text)
        self.assertIn("summary.inactive", preflight_text)
        self.assertIn("summary.probed", preflight_text)
        self.assertIn("summary.probe_failed", preflight_text)
        self.assertIn("item.missing_config", preflight_text)
        self.assertIn("item.endpoints", preflight_text)
        self.assertNotIn("getMissingConfigDisplayName", preflight_text)
        for secret_input_id in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
        ]:
            self.assertNotIn(secret_input_id, loader_text)
            self.assertNotIn(secret_input_id, preflight_text)
        for provider_branch in [
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
        ]:
            self.assertNotIn(provider_branch, preflight_text)

        click_start = js_text.index("document.addEventListener('click'")
        click_end = js_text.index("if (typeof window !== 'undefined')", click_start)
        click_text = js_text[click_start:click_end]
        self.assertIn("data-provider-preflight-probe", click_text)
        self.assertIn("loadProviderPreflightSnapshot(true, true);", click_text)

    def test_provider_health_console_styles_and_translations_exist(self):
        """Provider 控制台应包含上游探测的样式与中英文本。"""
        client = self.app.test_client()
        css_resp = client.get("/static/css/main.css")
        js_resp = client.get("/static/js/i18n.js")
        css_text = css_resp.data.decode("utf-8")
        i18n_text = js_resp.data.decode("utf-8")

        self.assertIn(".provider-console-health", css_text)
        self.assertIn(".provider-health-button", css_text)
        self.assertIn(".provider-health-result.ok", css_text)
        self.assertIn(".provider-health-result.skipped", css_text)
        self.assertIn(".provider-health-result.error", css_text)
        self.assertIn(".toast.warning", css_text)
        self.assertIn("上游探测", i18n_text)
        self.assertIn("Upstream probe", i18n_text)
        self.assertIn("Provider 上游探测通过", i18n_text)
        self.assertIn("Provider upstream probe passed", i18n_text)
        self.assertIn("Provider 本地检查通过", i18n_text)
        self.assertIn("Provider local check passed", i18n_text)
        self.assertIn(".provider-config-templates", css_text)
        self.assertIn(".provider-config-template-code", css_text)
        self.assertIn(".provider-config-template-copy", css_text)
        self.assertIn("部署配置模板", i18n_text)
        self.assertIn("Deployment config templates", i18n_text)
        self.assertIn("复制模板", i18n_text)
        self.assertIn("Copy template", i18n_text)
        self.assertIn("配置模板已复制", i18n_text)
        self.assertIn("Config template copied", i18n_text)
        self.assertIn(".provider-integration-guide", css_text)
        self.assertIn(".provider-integration-guide-summary", css_text)
        self.assertIn(".provider-integration-card", css_text)
        self.assertIn(".provider-integration-copy", css_text)
        self.assertIn(".provider-integration-chip", css_text)
        self.assertIn("Provider 接入指南", i18n_text)
        self.assertIn("Provider integration guide", i18n_text)
        self.assertIn("复制接入片段", i18n_text)
        self.assertIn("Copy integration snippet", i18n_text)
        self.assertIn("Provider 接入片段已复制", i18n_text)
        self.assertIn("Provider integration snippet copied", i18n_text)
        self.assertIn("只显示密钥字段名", i18n_text)
        self.assertIn("邮箱来源运营台", i18n_text)
        self.assertIn("Mailbox source operations console", i18n_text)
        self.assertIn("统一查看启用范围、运行默认、领取默认、发现入口和配置风险", i18n_text)
        self.assertIn("运行默认", i18n_text)
        self.assertIn("发现入口", i18n_text)
        self.assertIn("External projects should read", i18n_text)
        self.assertIn("可审计", i18n_text)
        self.assertIn("Auditable", i18n_text)
        self.assertIn(".provider-workbench", css_text)
        self.assertIn(".provider-workbench-summary", css_text)
        self.assertIn(".provider-workbench-discovery", css_text)
        self.assertIn(".provider-workbench-discovery-copy", css_text)
        self.assertIn(".provider-workbench-metric", css_text)
        self.assertIn(".provider-preflight-console", css_text)
        self.assertIn(".provider-preflight-head", css_text)
        self.assertIn(".provider-preflight-probe", css_text)
        self.assertIn(".provider-preflight-summary", css_text)
        self.assertIn(".provider-preflight-counter", css_text)
        self.assertIn(".provider-preflight-list", css_text)
        self.assertIn(".provider-preflight-row", css_text)
        self.assertIn(".provider-preflight-config", css_text)
        self.assertIn(".provider-preflight-chip", css_text)
        self.assertIn(".provider-preflight-probe-state", css_text)
        self.assertIn("Provider 批量预检", i18n_text)
        self.assertIn("Provider preflight", i18n_text)
        self.assertIn("本地只读检查全部邮箱来源；手动触发时才探测可用临时邮箱上游", i18n_text)
        self.assertIn("Run local-only checks across mailbox providers", i18n_text)
        self.assertIn("Provider 预检暂不可用", i18n_text)
        self.assertIn("Provider preflight unavailable", i18n_text)
        self.assertIn("预检通过", i18n_text)
        self.assertIn("Preflight passed", i18n_text)
        self.assertIn("预检中…", i18n_text)
        self.assertIn("Checking…", i18n_text)
        self.assertIn("本地只读", i18n_text)
        self.assertIn("Local only", i18n_text)
        self.assertIn("显式网络探测", i18n_text)
        self.assertIn("Explicit network probe", i18n_text)
        self.assertIn("显式探测", i18n_text)
        self.assertIn("Run probe", i18n_text)
        self.assertIn(".provider-contract-status", css_text)
        self.assertIn(".provider-contract-status-head", css_text)
        self.assertIn(".provider-contract-status-summary", css_text)
        self.assertIn(".provider-contract-counter", css_text)
        self.assertIn(".provider-contract-row", css_text)
        self.assertIn(".provider-contract-row.invalid", css_text)
        self.assertIn(".provider-contract-row.warning", css_text)
        self.assertIn(".provider-contract-issues", css_text)
        self.assertIn(".provider-contract-chip", css_text)
        self.assertIn(".provider-contract-plugin", css_text)
        self.assertIn("Provider 扩展契约", i18n_text)
        self.assertIn("Provider extension contract", i18n_text)
        self.assertIn("查看临时邮箱 Provider 插件是否满足统一邮箱与外部 API 接入契约", i18n_text)
        self.assertIn("Check whether temp-mail providers satisfy the unified mailbox and external API contract", i18n_text)
        self.assertIn("契约有效", i18n_text)
        self.assertIn("Contract valid", i18n_text)
        self.assertIn("契约告警", i18n_text)
        self.assertIn("Contract warnings", i18n_text)
        self.assertIn("契约无效", i18n_text)
        self.assertIn("Contract invalid", i18n_text)
        self.assertIn("契约未知", i18n_text)
        self.assertIn("Contract unknown", i18n_text)
        self.assertIn("overflow-wrap: anywhere", css_text)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", css_text)
        self.assertIn("grid-column: 1 / -1", css_text)
        self.assertIn("#page-settings .settings-tab-pane .card-body", css_text)
        self.assertIn("padding: 1rem !important", css_text)
        self.assertIn("Secret key names only", i18n_text)
        self.assertIn(".external-api-command-center", css_text)
        self.assertIn(".external-api-command-metrics", css_text)
        self.assertIn(".external-api-command-endpoints", css_text)
        self.assertIn(".external-api-command-code", css_text)
        self.assertIn(".external-api-command-copy", css_text)
        self.assertIn(".external-api-smoke-check", css_text)
        self.assertIn(".external-api-smoke-grid", css_text)
        self.assertIn(".external-api-smoke-coverage", css_text)
        self.assertIn(".external-api-smoke-command", css_text)
        self.assertIn(".external-api-smoke-copy", css_text)
        self.assertIn(".external-api-contract-check", css_text)
        self.assertIn(".external-api-contract-head", css_text)
        self.assertIn(".external-api-contract-summary", css_text)
        self.assertIn(".external-api-contract-card", css_text)
        self.assertIn(".external-api-contract-safety", css_text)
        self.assertIn(".external-api-contract-groups", css_text)
        self.assertIn(".external-api-contract-group", css_text)
        self.assertIn(".external-api-contract-row", css_text)
        self.assertIn(".external-api-contract-actions", css_text)
        self.assertIn(".external-api-contract-refresh", css_text)
        self.assertIn(".external-api-bundle-launchpad", css_text)
        self.assertIn(".external-api-bundle-head", css_text)
        self.assertIn(".external-api-bundle-summary", css_text)
        self.assertIn(".external-api-bundle-card", css_text)
        self.assertIn(".external-api-bundle-routes", css_text)
        self.assertIn(".external-api-bundle-route", css_text)
        self.assertIn(".external-api-bundle-route-main", css_text)
        self.assertIn(".external-api-bundle-command", css_text)
        self.assertIn(".external-api-bundle-copy", css_text)
        self.assertIn(".external-api-action-plan", css_text)
        self.assertIn(".external-api-action-list", css_text)
        self.assertIn(".external-api-action-item", css_text)
        self.assertIn(".external-api-action-head", css_text)
        self.assertIn(".external-api-action-meta", css_text)
        self.assertIn(".external-api-action-code", css_text)
        self.assertIn(".external-api-handoff-kit", css_text)
        self.assertIn(".external-api-handoff-head", css_text)
        self.assertIn(".external-api-handoff-subtitle", css_text)
        self.assertIn(".external-api-handoff-chips", css_text)
        self.assertIn(".external-api-handoff-chip", css_text)
        self.assertIn(".external-api-handoff-preview", css_text)
        self.assertIn(".external-api-handoff-copy", css_text)
        self.assertIn(".external-api-consumer-console", css_text)
        self.assertIn(".external-api-consumer-head", css_text)
        self.assertIn(".external-api-consumer-summary", css_text)
        self.assertIn(".external-api-consumer-summary-card", css_text)
        self.assertIn(".external-api-consumer-list", css_text)
        self.assertIn(".external-api-consumer-card", css_text)
        self.assertIn(".external-api-consumer-card[data-tone=\"ready\"]", css_text)
        self.assertIn(".external-api-consumer-card[data-tone=\"warning\"]", css_text)
        self.assertIn(".external-api-consumer-card[data-tone=\"danger\"]", css_text)
        self.assertIn(".external-api-consumer-card[data-tone=\"disabled\"]", css_text)
        self.assertIn(".external-api-consumer-counts", css_text)
        self.assertIn(".external-api-consumer-chips", css_text)
        self.assertIn(".external-api-consumer-last-used", css_text)
        self.assertIn(".external-api-consumer-empty", css_text)
        self.assertIn(".external-api-quickstart-cockpit", css_text)
        self.assertIn(".external-api-quickstart-grid", css_text)
        self.assertIn(".external-api-quickstart-sequence", css_text)
        self.assertIn(".external-api-quickstart-code", css_text)
        self.assertIn(".external-api-quickstart-copy", css_text)
        self.assertIn(".external-api-session-lifecycle", css_text)
        self.assertIn(".external-api-session-summary", css_text)
        self.assertIn(".external-api-session-body", css_text)
        self.assertIn(".external-api-session-step", css_text)
        self.assertIn(".external-api-session-example", css_text)
        self.assertIn(".external-api-session-code", css_text)
        self.assertIn(".external-api-session-copy", css_text)
        self.assertIn(".external-api-onboarding", css_text)
        self.assertIn(".external-api-onboarding-step", css_text)
        self.assertIn(".external-api-onboarding-step.warning", css_text)
        self.assertIn(".external-api-onboarding-dot", css_text)
        self.assertIn(".external-api-starter-modes", css_text)
        self.assertIn(".external-api-starter-mode", css_text)
        self.assertIn(".external-api-starter-mode[aria-pressed=\"true\"]", css_text)
        self.assertIn(".external-api-starter-code", css_text)
        self.assertIn("本地契约校验", i18n_text)
        self.assertIn("Local contract validation", i18n_text)
        self.assertIn("服务端只读验证 discovery、OpenAPI、Bundle 和 Provider 合同", i18n_text)
        self.assertIn("Server-side read-only validation", i18n_text)
        self.assertIn("重新校验", i18n_text)
        self.assertIn("Validate again", i18n_text)
        self.assertIn("不探测上游", i18n_text)
        self.assertIn("No upstream probes", i18n_text)
        self.assertIn("不变更邮箱", i18n_text)
        self.assertIn("No mailbox mutations", i18n_text)
        self.assertIn(".external-api-recipe-guide", css_text)
        self.assertIn(".external-api-recipe-head", css_text)
        self.assertIn(".external-api-recipe-body", css_text)
        self.assertIn(".external-api-recipe-tabs", css_text)
        self.assertIn(".external-api-recipe-tab", css_text)
        self.assertIn(".external-api-recipe-tab[aria-pressed=\"true\"]", css_text)
        self.assertIn(".external-api-recipe-detail", css_text)
        self.assertIn(".external-api-recipe-code", css_text)
        self.assertIn(".external-api-recipe-copy", css_text)
        self.assertIn(".external-api-workflow-playbooks", css_text)
        self.assertIn(".external-api-workflow-head", css_text)
        self.assertIn(".external-api-workflow-body", css_text)
        self.assertIn(".external-api-workflow-tabs", css_text)
        self.assertIn(".external-api-workflow-tab", css_text)
        self.assertIn(".external-api-workflow-tab[aria-pressed=\"true\"]", css_text)
        self.assertIn(".external-api-workflow-detail", css_text)
        self.assertIn(".external-api-workflow-step", css_text)
        self.assertIn(".external-api-workflow-endpoint-line", css_text)
        self.assertIn(".external-api-workflow-hints", css_text)
        self.assertIn(".external-api-workflow-copy", css_text)
        self.assertIn("grid-template-columns: minmax(12rem, 0.9fr) minmax(0, 1.7fr)", css_text)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", css_text)
        self.assertIn("max-height: 14rem", css_text)
        self.assertIn("overflow-wrap: anywhere", css_text)
        self.assertIn("Read-only integration smoke check", i18n_text)
        self.assertIn("Copy smoke command", i18n_text)
        self.assertIn("Smoke command copied", i18n_text)
        self.assertIn("Read-only discovery endpoints", i18n_text)
        self.assertIn("Integration Readiness Bundle", i18n_text)
        self.assertIn("Read integration readiness in one payload", i18n_text)
        self.assertIn("外部服务优先读取这个一站式 payload", i18n_text)
        self.assertIn("External services should read this one-stop payload first", i18n_text)
        self.assertIn("推荐入口", i18n_text)
        self.assertIn("Recommended entry", i18n_text)
        self.assertIn("认证占位", i18n_text)
        self.assertIn("Auth placeholder", i18n_text)
        self.assertIn("邮箱库存", i18n_text)
        self.assertIn("Mailbox inventory", i18n_text)
        self.assertIn("Canonical v1", i18n_text)
        self.assertIn("Legacy alias", i18n_text)
        self.assertIn("只读 Bundle 命令", i18n_text)
        self.assertIn("Read-only bundle command", i18n_text)
        self.assertIn("复制 Bundle 命令", i18n_text)
        self.assertIn("Copy bundle command", i18n_text)
        self.assertIn("Bundle 命令已复制", i18n_text)
        self.assertIn("Bundle command copied", i18n_text)
        self.assertIn("External Integration Handoff Kit", i18n_text)
        self.assertIn("一键交给外部开发者的安全接入说明", i18n_text)
        self.assertIn("Safe integration notes to hand to external developers in one copy", i18n_text)
        self.assertIn("复制交接包", i18n_text)
        self.assertIn("Copy handoff kit", i18n_text)
        self.assertIn("交接包已复制", i18n_text)
        self.assertIn("Handoff kit copied", i18n_text)
        self.assertIn("Fallback quickstart", i18n_text)
        self.assertIn("外部 API 消费方", i18n_text)
        self.assertIn("External API consumers", i18n_text)
        self.assertIn("按调用方查看今日用量、错误和访问范围", i18n_text)
        self.assertIn("Review today\\'s usage, errors, and access scope by caller", i18n_text)
        self.assertIn("暂无多 Key 消费方；配置多 Key 后这里会显示每个调用方的今日调用、错误和授权范围。", i18n_text)
        self.assertIn("No multi-key consumers yet", i18n_text)
        self.assertIn("今日活跃", i18n_text)
        self.assertIn("active today", i18n_text)
        self.assertIn("调用方", i18n_text)
        self.assertIn("Callers", i18n_text)
        self.assertIn("今日调用", i18n_text)
        self.assertIn("Calls today", i18n_text)
        self.assertIn("今日错误", i18n_text)
        self.assertIn("Errors today", i18n_text)
        self.assertIn("今日有错误", i18n_text)
        self.assertIn("今日未调用", i18n_text)
        self.assertIn("No calls today", i18n_text)
        self.assertIn("Pool 可用", i18n_text)
        self.assertIn("Pool allowed", i18n_text)
        self.assertIn("最近使用", i18n_text)
        self.assertIn("Last used", i18n_text)
        self.assertIn("总计", i18n_text)
        self.assertIn("Total", i18n_text)
        self.assertIn("请求数", i18n_text)
        self.assertIn("Request count", i18n_text)
        self.assertIn("外部接入指挥台", i18n_text)
        self.assertIn("External access command center", i18n_text)
        self.assertIn("接入启动包", i18n_text)
        self.assertIn("Integration starter kit", i18n_text)
        self.assertIn("Quickstart", i18n_text)
        self.assertIn("最短接入路径", i18n_text)
        self.assertIn("Shortest integration path", i18n_text)
        self.assertIn("复制 Quickstart", i18n_text)
        self.assertIn("Copy Quickstart", i18n_text)
        self.assertIn("Quickstart 已复制", i18n_text)
        self.assertIn("Quickstart copied", i18n_text)
        self.assertIn("暂无 quickstart 契约", i18n_text)
        self.assertIn("No quickstart contract available", i18n_text)
        self.assertIn("邮箱会话生命周期", i18n_text)
        self.assertIn("Mailbox session lifecycle", i18n_text)
        self.assertIn("复制会话流程", i18n_text)
        self.assertIn("Copy session flow", i18n_text)
        self.assertIn("会话流程已复制", i18n_text)
        self.assertIn("Session flow copied", i18n_text)
        self.assertIn("读取请求模板", i18n_text)
        self.assertIn("Read request templates", i18n_text)
        self.assertIn("接入检查", i18n_text)
        self.assertIn("Integration checklist", i18n_text)
        self.assertIn("生成 API Key 后保存设置", i18n_text)
        self.assertIn("Generate an API key, then save settings", i18n_text)
        self.assertIn("接入片段格式", i18n_text)
        self.assertIn("Integration snippet format", i18n_text)
        self.assertIn("复制启动命令", i18n_text)
        self.assertIn("Copy starter command", i18n_text)
        self.assertIn("启动命令已复制", i18n_text)
        self.assertIn("Starter command copied", i18n_text)
        self.assertIn("复制接入片段", i18n_text)
        self.assertIn("Copy integration snippet", i18n_text)
        self.assertIn("接入片段已复制", i18n_text)
        self.assertIn("Integration snippet copied", i18n_text)
        self.assertIn("Provider 选择 Recipes", i18n_text)
        self.assertIn("Provider selection recipes", i18n_text)
        self.assertIn("从当前 integration_manifest 读取 provider 选择示例", i18n_text)
        self.assertIn("Read provider selection examples from the current integration_manifest", i18n_text)
        self.assertIn("复制 Recipe", i18n_text)
        self.assertIn("Copy recipe", i18n_text)
        self.assertIn("Recipe 已复制", i18n_text)
        self.assertIn("Recipe copied", i18n_text)
        self.assertIn("暂无 provider selection recipes", i18n_text)
        self.assertIn("No provider selection recipes available", i18n_text)
        self.assertIn("工作流 Playbooks", i18n_text)
        self.assertIn("Workflow playbooks", i18n_text)
        self.assertIn("外部接入工作流", i18n_text)
        self.assertIn("External integration workflows", i18n_text)
        self.assertIn("复制工作流", i18n_text)
        self.assertIn("Copy workflow", i18n_text)
        self.assertIn("工作流已复制", i18n_text)
        self.assertIn("Workflow copied", i18n_text)
        self.assertIn("发现外部 API", i18n_text)
        self.assertIn("Discover external API", i18n_text)
        self.assertIn("领取池内邮箱", i18n_text)
        self.assertIn("Claim pool mailbox", i18n_text)
        self.assertIn("创建任务临时邮箱", i18n_text)
        self.assertIn("Create task temp mailbox", i18n_text)
        self.assertIn("全部端点可用", i18n_text)
        self.assertIn("All endpoints available", i18n_text)
        self.assertIn("部分启用", i18n_text)
        self.assertIn("Partially enabled", i18n_text)
        self.assertIn(".operational-readiness-console", css_text)
        self.assertIn(".operational-readiness-grid", css_text)
        self.assertIn(".operational-readiness-card", css_text)
        self.assertIn(".operational-readiness-card[data-tone=\"ready\"]", css_text)
        self.assertIn(".operational-readiness-card[data-tone=\"degraded\"]", css_text)
        self.assertIn(".operational-readiness-status", css_text)
        self.assertIn("运行就绪检查台", i18n_text)
        self.assertIn("Operational readiness console", i18n_text)
        self.assertIn("聚合 API 鉴权、Provider、目录库存、Pool 与任务临时邮箱状态", i18n_text)
        self.assertIn("Aggregate API auth, providers, mailbox inventory, pool, and task-temp readiness", i18n_text)
        self.assertIn("Mailbox directory snapshot unavailable", i18n_text)

    def test_api_providers_guide_is_available_and_secret_free_for_ui(self):
        """设置页使用的 /api/providers 应返回 secret-free 接入指南。"""
        client = self.app.test_client()
        self._login(client)
        with patch.dict(
            "os.environ",
            {
                "DUCKMAIL_API_BASE": "https://api.duckmail.sbs",
                "DUCKMAIL_BEARER_TOKEN": "duck-secret-for-ui-test",
            },
            clear=False,
        ):
            resp = client.get("/api/providers")

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        guide = payload.get("provider_integration_guide") or {}
        self.assertEqual(guide.get("version"), 1)
        self.assertFalse((guide.get("secret_policy") or {}).get("exposes_secret_values"))
        guide_text = json.dumps(guide, ensure_ascii=False)
        self.assertIn("DUCKMAIL_BEARER_TOKEN", guide_text)
        self.assertIn("provider_name", guide_text)
        self.assertIn("provider", guide_text)
        self.assertNotIn("duck-secret-for-ui-test", guide_text)
        self.assertNotRegex(guide_text, r"dk_[0-9a-f]{20,}")
        guide_providers = {item.get("provider"): item for item in guide.get("providers") or []}
        duckmail = guide_providers.get("duckmail") or {}
        self.assertEqual(duckmail.get("required_env"), ["DUCKMAIL_BEARER_TOKEN"])
        self.assertEqual((duckmail.get("task_temp_apply_request") or {}).get("field"), "provider_name")
        self.assertEqual((duckmail.get("pool_claim_request") or {}).get("field"), "provider")
        self.assertEqual((guide.get("aliases") or {}).get("runtime_temp_mail_provider_aliases", {}).get("gptmail"), "legacy_bridge")
        manifest = payload.get("integration_manifest") or {}
        self.assertEqual(manifest.get("version"), 1)
        self.assertEqual((manifest.get("auth") or {}).get("placeholder"), "<your-api-key>")
        quickstart = payload.get("quickstart") or {}
        self.assertEqual(quickstart, manifest.get("quickstart"))
        quickstart_text = json.dumps(quickstart, ensure_ascii=False)
        self.assertEqual((quickstart.get("auth") or {}).get("headers"), {"X-API-Key": "<your-api-key>"})
        self.assertEqual((quickstart.get("provider_selector_fields") or {}).get("pool_claim", {}).get("field"), "provider")
        self.assertEqual((quickstart.get("provider_selector_fields") or {}).get("task_temp_apply", {}).get("field"), "provider_name")
        self.assertEqual((quickstart.get("requests") or {}).get("pool_claim", {}).get("body", {}).get("provider"), "<provider-or-auto>")
        self.assertEqual((quickstart.get("requests") or {}).get("task_temp_apply", {}).get("body", {}).get("provider_name"), "<provider-name>")
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", quickstart_text)
        self.assertNotIn("duck-secret-for-ui-test", quickstart_text)
        manifest_text = json.dumps(manifest, ensure_ascii=False)
        self.assertIn("DUCKMAIL_BEARER_TOKEN", manifest_text)
        self.assertNotIn("duck-secret-for-ui-test", manifest_text)
        self.assertNotRegex(manifest_text, r"dk_[0-9a-f]{20,}")
        manifest_providers = {item.get("provider"): item for item in manifest.get("providers") or []}
        duckmail_manifest = manifest_providers.get("duckmail") or {}
        duckmail_env = {item.get("key"): item for item in duckmail_manifest.get("env") or []}
        self.assertEqual(duckmail_env.get("DUCKMAIL_BEARER_TOKEN", {}).get("value"), "")
        self.assertEqual(duckmail_env.get("DUCKMAIL_API_BASE", {}).get("default"), "https://api.duckmail.sbs")
        for container in (manifest, manifest.get("deployment") or {}, guide, payload.get("deployment_profile") or {}):
            self.assertIn("selection_recipes", container)
            self.assertIn("selection_recipe_index", container)
        self.assertIn("recipes", manifest.get("selection") or {})
        self.assertIn("recipe_index", manifest.get("selection") or {})
        self.assertEqual(manifest.get("selection_recipes"), (manifest.get("selection") or {}).get("recipes"))
        self.assertEqual(manifest.get("selection_recipe_index"), (manifest.get("selection") or {}).get("recipe_index"))
        self.assertEqual(manifest.get("selection_recipes"), (manifest.get("deployment") or {}).get("selection_recipes"))
        recipe_index = manifest.get("selection_recipe_index") or {}
        self.assertIn("explicit_pool_claim:duckmail", recipe_index)
        self.assertIn("task_temp_apply:duckmail", recipe_index)
        duckmail_pool_recipe = recipe_index.get("explicit_pool_claim:duckmail") or {}
        duckmail_recipe_env = {item.get("key"): item for item in duckmail_pool_recipe.get("provider_env") or []}
        self.assertEqual(duckmail_recipe_env.get("DUCKMAIL_BEARER_TOKEN", {}).get("value"), "")
        self.assertTrue(duckmail_recipe_env.get("DUCKMAIL_BEARER_TOKEN", {}).get("secret"))
        self.assertEqual((duckmail_pool_recipe.get("request") or {}).get("body"), {"provider": "duckmail"})
        workflows = {item.get("key"): item for item in manifest.get("workflows") or []}
        self.assertIn("discover_external_api", workflows)
        self.assertIn("browse_mailbox_directory", workflows)
        self.assertIn("claim_pool_mailbox", workflows)
        self.assertIn("create_task_temp_mailbox", workflows)
        claim_steps = {item.get("key"): item for item in workflows.get("claim_pool_mailbox", {}).get("steps") or []}
        self.assertEqual(claim_steps.get("read_messages", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/messages")
        self.assertEqual(claim_steps.get("read_verification_code", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/verification-code")
        self.assertEqual(claim_steps.get("complete_claim", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-complete")
        self.assertEqual(claim_steps.get("release_claim", {}).get("endpoint"), f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-release")
        self.assertNotIn("DUCKMAIL_BEARER_TOKEN", json.dumps(manifest.get("workflows") or [], ensure_ascii=False))

    # ──────────────────────────────────────────────────────
    # TC-B04：index.html 包含兼容临时邮箱桥接配置面板及其字段
    # ──────────────────────────────────────────────────────

    def test_index_html_contains_gptmail_config_panel(self):
        """index.html 应保留兼容挂载点，字段由 schema 面板渲染。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertIn(
            'id="gptmailConfigPanel"',
            html,
            "应包含兼容临时邮箱桥接配置面板 #gptmailConfigPanel",
        )
        # Static hard-coded bridge fields are removed; schema renderer owns them.
        self.assertNotIn('id="settingsTempMailApiBaseUrl"', html)
        self.assertNotIn('id="settingsTempMailApiKey"', html)
        self.assertIn("temp_mail_api_base_url", js_text)
        self.assertIn("temp_mail_api_key", js_text)
        self.assertIn("data-temp-provider-setting", js_text)

    # ──────────────────────────────────────────────────────
    # TC-B05：index.html 包含 CF Worker 配置面板及只读字段
    # ──────────────────────────────────────────────────────

    def test_index_html_contains_cf_worker_config_panel(self):
        """index.html 应保留 CF Worker 兼容挂载点，字段由 schema 面板渲染。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertIn(
            'id="cfWorkerConfigPanel"',
            html,
            "应包含 CF Worker 配置面板 #cfWorkerConfigPanel",
        )
        self.assertNotIn('id="settingsCfWorkerBaseUrl"', html)
        self.assertNotIn('id="settingsCfWorkerAdminKey"', html)
        self.assertNotIn('id="settingsCfWorkerDomains"', html)
        self.assertNotIn('id="btnSyncCfWorkerDomains"', html)
        self.assertIn("cf_worker_base_url", js_text)
        self.assertIn("cf_worker_admin_key", js_text)
        self.assertIn("cf_worker_domains", js_text)
        self.assertIn("data-temp-provider-action", js_text)
        self.assertIn("/api/settings/cf-worker-sync-domains", js_text)

    def test_index_html_uses_schema_panel_for_duckmail_settings(self):
        """DuckMail 应由 catalog/schema 配置面板渲染，不再依赖专属模板字段。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertNotIn('id="duckmailConfigPanel"', html)
        self.assertNotIn('id="settingsDuckmailApiBase"', html)
        self.assertNotIn('id="settingsDuckmailBearerToken"', html)
        self.assertNotIn('id="duckmailBearerTokenHint"', html)
        self.assertIn("providerUsesTempSettingsSchemaPanel(normalizedProvider)", js_text)
        self.assertIn("data-temp-provider-setting", js_text)
        provider_options = js_text[js_text.index("function normalizeTempMailSettingsProviderName") : js_text.index("function getTempEmailProviderCatalogOptions")]
        self.assertNotIn("duckmail_api_base", provider_options)
        self.assertNotIn("duckmail_bearer_token", provider_options)

    def test_index_html_uses_schema_panel_for_emailnator_settings(self):
        """Emailnator 应由 catalog/schema 配置面板渲染，不再依赖专属模板字段。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertNotIn('id="emailnatorConfigPanel"', html)
        self.assertNotIn('id="settingsEmailnatorApiKey"', html)
        self.assertNotIn('id="settingsEmailnatorEmailTypes"', html)
        self.assertNotIn('id="emailnatorApiKeyHint"', html)
        self.assertIn("providerUsesTempSettingsSchemaPanel(normalizedProvider)", js_text)
        provider_options = js_text[js_text.index("function normalizeTempMailSettingsProviderName") : js_text.index("function getTempEmailProviderCatalogOptions")]
        self.assertNotIn("emailnator_api_key", provider_options)
        self.assertNotIn("emailnator_email_types", provider_options)

    # ──────────────────────────────────────────────────────
    # TC-B06：index.html 中 CF Worker 只读字段有 readonly 属性
    # ──────────────────────────────────────────────────────

    def test_cf_worker_domain_fields_have_readonly_attribute(self):
        """CF Worker 域名字段应通过 schema readonly 契约渲染，而非静态模板字段。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client)
        js_text = load_frontend_app_js()

        self.assertNotIn('id="settingsCfWorkerDomains"', html)
        self.assertNotIn('id="settingsCfWorkerDefaultDomain"', html)
        self.assertIn("data-temp-provider-readonly", js_text)
        self.assertIn("field?.readonly === true || field?.read_only === true", js_text)
        self.assertIn("readonly-field", js_text)

    # ──────────────────────────────────────────────────────
    # TC-B07：main.js 包含 switchSettingsTab 函数
    # ──────────────────────────────────────────────────────

    def test_main_js_contains_switch_settings_tab_function(self):
        """main.js 应包含 switchSettingsTab 函数定义"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn(
            "function switchSettingsTab",
            js_text,
            "main.js 应包含 switchSettingsTab 函数",
        )

    # ──────────────────────────────────────────────────────
    # TC-B08：main.js 包含 onTempMailProviderChange 函数
    # ──────────────────────────────────────────────────────

    def test_main_js_contains_on_temp_mail_provider_change(self):
        """main.js 应包含 onTempMailProviderChange 函数定义"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn(
            "function onTempMailProviderChange",
            js_text,
            "main.js 应包含 onTempMailProviderChange 函数",
        )

    # ──────────────────────────────────────────────────────
    # TC-B09：main.js 包含 autoSaveSettings 函数
    # ──────────────────────────────────────────────────────

    def test_main_js_contains_auto_save_settings_function(self):
        """main.js 应包含 autoSaveSettings 函数定义"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("function autoSaveSettings", js_text, "main.js 应包含 autoSaveSettings 函数")

    def test_production_static_scripts_do_not_leave_debug_console_output(self):
        """生产静态脚本不应残留 console.log/debug 调试输出。"""
        script_paths = [
            "static/js/core/",
            "static/js/features/poll-engine.js",
            "static/js/features/mailbox_compact.js",
            "static/js/features/emails/globals.js",
        ]
        client = self.app.test_client()

        for path in script_paths:
            with self.subTest(path=path):
                text = self._get_text(client, f"/{path}")
                self.assertNotIn("console.log(", text)
                self.assertNotIn("console.debug(", text)

    def test_main_js_preserves_env_backed_duckmail_base_until_user_edits(self):
        """DuckMail API Base 未被用户编辑时不应被保存固化到数据库。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("data-loaded-value", js_text)
        self.assertIn("const loadedValue = String(inputEl.dataset.loadedValue || '').trim();", js_text)
        self.assertIn("if (rawValue === loadedValue) continue;", js_text)
        self.assertIn("tempMailSettingsDirtyKeys", js_text)
        self.assertIn("tempMailSettingsDirtyKeys.add(settingKey)", js_text)
        # Dirty-key tracking ensures only user-edited schema values are submitted.
        self.assertIn("tempMailSettingsDirtyKeys.forEach", js_text)

    def test_main_js_reuses_shared_settings_payload_collectors(self):
        """手动保存和自动保存应复用同一套设置 payload 组装逻辑。"""
        client = self.app.test_client()
        js_text = load_frontend_app_js()

        self.assertIn("function collectTempMailSettingsPayload", js_text)
        self.assertIn("function collectApiSecuritySettingsPayload", js_text)
        self.assertIn("function assignSecretSettingFromInput", js_text)
        self.assertIn("function collectTempProviderSchemaSettings", js_text)
        self.assertIn("function syncTempProviderSchemaInputsToSnapshot", js_text)
        # Unbound temp-mail radios must not overwrite stored provider with operator default.
        collect_start = js_text.index("function collectTempMailSettingsPayload")
        collect_end = js_text.index("async function refreshTempMailSettingsSnapshotFromServer", collect_start)
        collect_js = js_text[collect_start:collect_end]
        self.assertIn("isTempMailSettingsProviderMountBound", collect_js)
        self.assertIn("dataset.pendingProvider", collect_js)
        self.assertIn("tempMailSettingsSnapshot", collect_js)
        self.assertIn("getOperatorDefaultTempMailProvider()", collect_js)
        # Unbound path preserves snapshot exactly (no forced alias canonicalize).
        self.assertIn("settings.temp_mail_provider = snapshotProvider", collect_js)
        self.assertIn("if (bound)", collect_js)
        self.assertIn("else if (snapshotProvider)", collect_js)

        save_start = js_text.index("async function saveSettings")
        save_end = js_text.index("async function testTelegramPush", save_start)
        save_settings_js = js_text[save_start:save_end]

        self.assertIn("collectTempMailSettingsPayload()", save_settings_js)
        self.assertIn("collectApiSecuritySettingsPayload()", save_settings_js)

        auto_start = js_text.index("async function autoSaveSettings")
        auto_end = js_text.index("// Provider 切换面板显隐", auto_start)
        auto_save_js = js_text[auto_start:auto_end]

        self.assertIn("collectTempMailSettingsPayload()", auto_save_js)
        self.assertIn("collectApiSecuritySettingsPayload()", auto_save_js)
        # After temp-mail save, refresh snapshot so plugin/builtin secret state is current.
        self.assertIn("function refreshTempMailSettingsSnapshotFromServer", js_text)
        self.assertIn("await refreshTempMailSettingsSnapshotFromServer()", js_text)
        self.assertIn("tempMailSettingsDirtyKeys = new Set()", js_text)
        # Server reload must not re-sync stale empty secret inputs over the snapshot.
        self.assertIn("skipSnapshotSync", js_text)
        self.assertIn("renderTempMailProviderConfigPanel(selectedProvider, { skipSnapshotSync: true })", js_text)
        self.assertIn("!opts.skipSnapshotSync && !syncTempProviderSchemaInputsToSnapshot()", js_text)
        for duplicated_branch in [
            "provider === 'legacy_bridge'",
            "provider === 'cloudflare_temp_mail'",
            "provider === 'duckmail'",
            "provider === 'emailnator'",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsExternalApiKeysJson",
        ]:
            self.assertNotIn(duplicated_branch, auto_save_js)

        router_start = js_text.index("function onTempMailProviderChange")
        router_end = js_text.index("// Compatibility wrapper kept for older callers/tests.", router_start)
        router_js = js_text[router_start:router_end]
        self.assertIn(
            "const normalizedProvider = normalizeTempMailSettingsProviderName(provider) || getOperatorDefaultTempMailProvider();",
            router_js,
        )
        self.assertIn("renderTempMailProviderConfigPanel(normalizedProvider)", router_js)
        self.assertIn("const usesSchemaPanel = providerUsesTempSettingsSchemaPanel(normalizedProvider);", router_js)
        self.assertIn("gptmailConfigPanel", router_js)
        self.assertIn("cfWorkerConfigPanel", router_js)
        self.assertNotIn("legacy_bridge: gptmailPanel", router_js)
        self.assertNotIn("cloudflare: cfWorkerPanel", router_js)
        self.assertNotIn("dedicatedPanels", router_js)
        self.assertNotIn("duckmail: duckmailPanel", router_js)
        self.assertNotIn("emailnator: emailnatorPanel", router_js)
        self.assertNotIn("['mail_tm', 'tempmail_lol'].includes(normalizedProvider)", router_js)
        self.assertIn("pluginManager.showProviderConfig(normalizedProvider)", router_js)

        # Catalog-ready plugins use schema panel; warmup still protects missing catalog.
        route_fn_start = js_text.index("function providerUsesTempSettingsSchemaPanel")
        route_fn_end = js_text.index("function getTempProviderSchemaFields", route_fn_start)
        route_fn = js_text[route_fn_start:route_fn_end]
        self.assertIn("function getBuiltinTempSettingsSchemaFallbackProviders", js_text)
        self.assertIn("configSource === 'plugin'", route_fn)
        self.assertIn("return panel === 'schema'", route_fn)
        self.assertIn("hasInstalledProvider", route_fn)
        self.assertIn("getBuiltinTempSettingsSchemaFallbackProviders()", route_fn)
        # Built-in schema fallback roster lives in the dedicated helper, not inlined in the router.
        fallback_start = js_text.index("function getBuiltinTempSettingsSchemaFallbackProviders")
        fallback_end = js_text.index("function providerUsesTempSettingsSchemaPanel", fallback_start)
        fallback_js = js_text[fallback_start:fallback_end]
        self.assertIn("'legacy_bridge'", fallback_js)
        self.assertIn("'cloudflare_temp_mail'", fallback_js)
        self.assertIn("'duckmail'", fallback_js)
        self.assertIn("'emailnator'", fallback_js)
        # Plugin test-connection is available from the schema action row.
        self.assertIn("function getPluginSchemaTestConnectionAction", js_text)
        self.assertIn("/api/plugins/", js_text)
        self.assertIn("test-connection", js_text)
        self.assertIn("getPluginSchemaTestConnectionAction(providerName)", js_text)
        # Warmup alias map keeps historical built-in names on schema path before catalog.
        self.assertIn("function getBuiltinTempSettingsProviderAliasMap", js_text)
        self.assertIn("gptmail: 'legacy_bridge'", js_text)
        self.assertIn("custom_domain_temp_mail: 'legacy_bridge'", js_text)
        self.assertIn("getBuiltinTempSettingsProviderAliasMap()", js_text)

    def test_schema_plugin_action_strings_are_i18n_ready(self):
        """Schema/plugin action copy used by translateAppTextLocal must exist in i18n map."""
        client = self.app.test_client()
        i18n_text = self._get_text(client, "/static/js/i18n.js")
        for phrase in (
            "测试连接",
            "处理中…",
            "操作端点不可用",
            "根据 Provider 目录渲染配置字段",
            "该 Provider 无需本地配置",
            "Provider 配置目录暂不可用",
            "只读字段，可通过操作按钮更新",
            "输入新值；留空则保留已保存配置",
        ):
            self.assertIn(f"'{phrase}'", i18n_text)

    # ──────────────────────────────────────────────────────
    # TC-B10：main.css 包含 Tab 相关样式类
    # ──────────────────────────────────────────────────────

    def test_main_css_contains_tab_styles(self):
        """main.css 应包含 .settings-tab-nav / .settings-tab / .settings-tab-pane 样式"""
        client = self.app.test_client()
        resp = client.get("/static/css/main.css")
        css_text = resp.data.decode("utf-8")

        self.assertIn(".settings-tab-nav", css_text, "main.css 应包含 .settings-tab-nav 样式")
        self.assertIn(".settings-tab", css_text, "main.css 应包含 .settings-tab 样式")
        self.assertIn(".settings-tab-pane", css_text, "main.css 应包含 .settings-tab-pane 样式")

    # ──────────────────────────────────────────────────────
    # TC-B11：main.css 包含 Provider 单选按钮样式
    # ──────────────────────────────────────────────────────

    def test_main_css_contains_provider_radio_styles(self):
        """main.css 应包含 .provider-radio-group 和 .provider-radio 样式"""
        client = self.app.test_client()
        resp = client.get("/static/css/main.css")
        css_text = resp.data.decode("utf-8")

        self.assertIn(
            ".provider-radio-group",
            css_text,
            "main.css 应包含 .provider-radio-group 样式",
        )
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));", css_text)
        self.assertIn(".provider-radio-loading", css_text)
        self.assertIn(".provider-source-badge", css_text)
        self.assertIn(".provider-radio", css_text, "main.css 应包含 .provider-radio 样式")
        self.assertIn(".temp-provider-config-grid", css_text)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));", css_text)
        self.assertIn(".temp-provider-config-hints code", css_text)

    # ──────────────────────────────────────────────────────
    # TC-B12：main.css 包含只读字段样式
    # ──────────────────────────────────────────────────────

    def test_main_css_contains_readonly_field_styles(self):
        """main.css 应包含 .readonly-field 样式"""
        client = self.app.test_client()
        resp = client.get("/static/css/main.css")
        css_text = resp.data.decode("utf-8")

        self.assertIn(".readonly-field", css_text, "main.css 应包含 .readonly-field 样式")


if __name__ == "__main__":
    unittest.main()
