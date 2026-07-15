from __future__ import annotations

from tests.frontend_js_bundle import load_feature_package_js, load_frontend_app_js, load_mailboxes_js
import unittest

from tests._import_app import import_web_app_module


class UnifiedMailboxFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json() or {}
        self.assertEqual(data.get("success"), True)

    def _get_text(self, client, path: str) -> str:
        resp = client.get(path)
        try:
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    def test_index_html_exposes_unified_mailbox_mode_and_controls(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")

        for expected in [
            'id="mailboxUnifiedModeBtn"',
            '统一工作台',
            '账号视图',
            '紧凑视图',
            "switchMailboxViewMode('unified')",
            'id="mailboxUnifiedLayout"',
            'class="unified-workspace-masthead"',
            'aria-labelledby="unifiedWorkspaceTitle"',
            'class="unified-workspace-kicker"',
            'Mailbox Fabric',
            'id="unifiedWorkspaceTitle"',
            '统一邮箱聚合服务',
            'class="unified-workspace-pipeline"',
            'aria-label="统一邮箱链路"',
            '目录库存',
            'Provider 路由',
            '验证码读取',
            '外部 API',
            'id="unifiedWorkspaceViewSwitch"',
            'class="unified-workspace-view-switch"',
            'data-unified-workspace-view="inbox"',
            'data-unified-workspace-view="diagnostics"',
            '日常收件箱',
            '高级诊断',
            'id="unifiedInboxWorkflow"',
            'class="unified-inbox-workflow"',
            'data-view="inbox"',
            'id="unifiedDiagnosticsWorkspace"',
            'class="unified-diagnostics-workspace"',
            'data-view="diagnostics"',
            'id="unifiedMailboxCommandCenter"',
            'class="unified-command-center"',
            'data-state="loading"',
            'class="unified-command-state loading"',
            'class="unified-command-state-copy"',
            'class="unified-command-state-grid"',
            '正在读取统一邮箱服务…',
            '正在同步目录库存、来源策略和推荐视图',
            'id="unifiedMailboxSetupGuide"',
            'class="unified-setup-guide"',
            'aria-labelledby="unifiedSetupGuideTitle"',
            'class="unified-setup-guide-head"',
            'class="unified-setup-guide-kicker"',
            'Setup Path',
            'id="unifiedSetupGuideTitle"',
            '统一邮箱启动路径',
            '正在整理账号、临时邮箱、Provider 路由和外部 API 接入状态',
            'class="unified-setup-guide-status"',
            '读取中',
            'class="unified-setup-guide-steps"',
            'class="unified-setup-step-skeleton"',
            'id="unifiedMailboxSearch"',
            'class="unified-toolbar-field unified-toolbar-field-search"',
            'class="unified-filter-label" for="unifiedMailboxSearch"',
            'id="unifiedMailboxKindFilter"',
            'id="unifiedMailboxStatusFilter"',
            'id="unifiedMailboxReadCapabilityFilter"',
            'aria-label="读取方式"',
            'id="unifiedMailboxActionFilter"',
            'aria-label="邮箱能力"',
            'id="unifiedMailboxProviderFilter"',
            'aria-label="邮箱来源"',
            'id="unifiedMailboxSortFilter"',
            'aria-label="排序方式"',
            'value="updated_desc"',
            'id="unifiedMailboxRefreshBtn"',
            'id="unifiedMailboxQuickViews"',
            'class="unified-quick-views"',
            'role="group"',
            'aria-label="聚合邮箱快速视图"',
            'hidden',
            'id="unifiedMailboxResultBar"',
            'class="unified-result-bar"',
            'aria-live="polite"',
            'aria-label="当前筛选条件"',
            'id="unifiedMailboxOperationalLens"',
            'class="unified-operational-lens"',
            'data-state="loading"',
            '正在分析当前视图…',
            '正在整理筛选、库存和 Provider 就绪度',
            'id="unifiedMailboxSummary"',
            'id="unifiedMailboxProviderContext"',
            'id="unifiedProviderCapabilityMatrix"',
            'class="unified-provider-capability-matrix"',
            '正在读取 Provider 能力…',
            'id="unifiedMailboxList"',
            'id="unifiedMailboxPagination"',
            'id="unifiedMailboxMessagePreview"',
            'class="unified-message-preview"',
            'data-state="empty"',
            'aria-labelledby="unifiedMessagePreviewTitle"',
            'Inbox Preview',
            '统一收件箱预览',
            '选择一个邮箱查看邮件',
        ]:
            self.assertIn(expected, index_html)

        self.assertNotIn('unified-command-center-empty', index_html)

        toolbar_pos = index_html.index('class="unified-toolbar"')
        masthead_pos = index_html.index('class="unified-workspace-masthead"')
        view_switch_pos = index_html.index('id="unifiedWorkspaceViewSwitch"')
        inbox_workflow_pos = index_html.index('id="unifiedInboxWorkflow"')
        command_center_pos = index_html.index('id="unifiedMailboxCommandCenter"')
        setup_guide_pos = index_html.index('id="unifiedMailboxSetupGuide"')
        diagnostics_pos = index_html.index('id="unifiedDiagnosticsWorkspace"')
        quick_views_pos = index_html.index('id="unifiedMailboxQuickViews"')
        result_bar_pos = index_html.index('id="unifiedMailboxResultBar"')
        operational_lens_pos = index_html.index('id="unifiedMailboxOperationalLens"')
        provider_context_pos = index_html.index('id="unifiedMailboxProviderContext"')
        provider_matrix_pos = index_html.index('id="unifiedProviderCapabilityMatrix"')
        mailbox_list_pos = index_html.index('id="unifiedMailboxList"')
        mailbox_pagination_pos = index_html.index('id="unifiedMailboxPagination"')
        message_preview_pos = index_html.index('id="unifiedMailboxMessagePreview"')
        self.assertLess(masthead_pos, view_switch_pos)
        self.assertLess(view_switch_pos, inbox_workflow_pos)
        self.assertLess(inbox_workflow_pos, toolbar_pos)
        self.assertLess(toolbar_pos, quick_views_pos)
        self.assertLess(quick_views_pos, result_bar_pos)
        self.assertLess(result_bar_pos, mailbox_list_pos)
        self.assertLess(mailbox_list_pos, mailbox_pagination_pos)
        self.assertLess(mailbox_pagination_pos, message_preview_pos)
        self.assertLess(message_preview_pos, diagnostics_pos)
        self.assertLess(diagnostics_pos, command_center_pos)
        self.assertLess(command_center_pos, setup_guide_pos)
        self.assertLess(setup_guide_pos, operational_lens_pos)
        self.assertLess(operational_lens_pos, provider_context_pos)
        self.assertLess(provider_context_pos, provider_matrix_pos)

        status_start = index_html.index('id="unifiedMailboxStatusFilter"')
        kind_start = index_html.index('id="unifiedMailboxKindFilter"')
        kind_html = index_html[kind_start:status_start]
        self.assertIn('value="all"', kind_html)
        self.assertNotIn('value="account"', kind_html)
        self.assertNotIn('value="temp"', kind_html)

        provider_start = index_html.index('id="unifiedMailboxProviderFilter"')
        status_html = index_html[status_start:provider_start]
        self.assertIn('value="all"', status_html)
        self.assertNotIn('value="cooldown"', status_html)

        read_capability_start = index_html.index('id="unifiedMailboxReadCapabilityFilter"')
        read_capability_html = index_html[read_capability_start:provider_start]
        self.assertIn('value="all"', read_capability_html)
        self.assertNotIn('value="temp_provider"', read_capability_html)

        action_start = index_html.index('id="unifiedMailboxActionFilter"')
        action_html = index_html[action_start:provider_start]
        self.assertIn('value="all"', action_html)
        self.assertNotIn('value="delete_remote_mailbox"', action_html)

        sort_start = index_html.index('id="unifiedMailboxSortFilter"')
        refresh_start = index_html.index('id="unifiedMailboxRefreshBtn"')
        sort_html = index_html[sort_start:refresh_start]
        self.assertIn('value="updated_desc"', sort_html)
        self.assertNotIn('value="email_asc"', sort_html)

    def test_scripts_load_unified_mailbox_module_after_legacy_feature_modules(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")

        groups_pos = index_html.index("/static/js/features/groups/globals.js")
        temp_pos = index_html.index("/static/js/features/temp_emails/globals.js")
        accounts_pos = index_html.index("/static/js/features/accounts/globals.js")
        mailboxes_pos = index_html.index("/static/js/features/mailboxes/globals.js")
        self.assertLess(groups_pos, mailboxes_pos)
        self.assertLess(temp_pos, mailboxes_pos)
        self.assertLess(accounts_pos, mailboxes_pos)

    def test_view_mode_switcher_supports_unified_layout(self):
        client = self.app.test_client()
        module_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        self.assertIn("['standard', 'compact', 'unified'].includes(mode)", module_js)
        self.assertIn("document.getElementById('mailboxUnifiedLayout')", module_js)
        self.assertIn("unifiedLayout.style.display = mailboxViewMode === 'unified' ? 'block' : 'none';", module_js)
        self.assertIn("loadUnifiedMailboxes(false)", module_js)

    def test_account_and_temp_force_refresh_invalidate_unified_directory_cache(self):
        """Inventory force-refresh must drop unified soft directory cache."""
        client = self.app.test_client()
        groups_js = load_feature_package_js('static/js/features/groups')
        temp_js = load_feature_package_js('static/js/features/temp_emails')
        mailboxes_js = load_mailboxes_js()

        self.assertIn("window.invalidateUnifiedMailboxDirectoryCache = invalidateUnifiedMailboxDirectoryCache", mailboxes_js)
        self.assertIn("window.invalidateUnifiedMailboxDirectoryCache()", groups_js)
        self.assertIn("window.invalidateAuditLogPageCache()", groups_js)
        self.assertIn("window.invalidateUnifiedMailboxDirectoryCache()", temp_js)
        self.assertIn("window.invalidateAuditLogPageCache()", temp_js)

    def test_topbar_handles_unified_mode_without_account_only_actions(self):
        client = self.app.test_client()
        main_js = load_frontend_app_js()

        self.assertIn("const isUnifiedMode = mailboxViewMode === 'unified';", main_js)
        self.assertIn("'mailbox': ['统一邮箱工作台', '聚合账号库存、Provider 路由与外部会话入口']", main_js)
        self.assertIn("统一查看账号库存、临时邮箱、Provider 路由与外部会话入口", main_js)
        self.assertIn("管理账号与邮件详情", main_js)
        self.assertIn("document.getElementById('mailboxUnifiedModeBtn')", main_js)
        self.assertIn("unifiedBtn.classList.toggle('active', mailboxViewMode === 'unified');", main_js)

    def test_unified_mailbox_module_uses_unified_catalog_api_and_existing_open_flows(self):
        client = self.app.test_client()
        module_js = load_mailboxes_js()

        for expected in [
            "/api/mailboxes?${params.toString()}",
            "kind: unifiedMailboxState.filters.kind",
            "status: unifiedMailboxState.filters.status",
            "read_capability: unifiedMailboxState.filters.readCapability",
            "action: unifiedMailboxState.filters.action",
            "provider: unifiedMailboxState.filters.provider",
            "sort: unifiedMailboxState.filters.sort",
            "search: unifiedMailboxState.filters.search",
            "const definitions = Array.isArray(contract.kind_definitions) ? contract.kind_definitions : [];",
            "const fields = Array.isArray(contract.summary_fields) && contract.summary_fields.length > 0",
            "unifiedMailboxState.contract = data.contract || {}",
            "renderUnifiedKindOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.kind, (data.facets || {}).kinds || [])",
            "renderUnifiedStatusOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.status, (data.facets || {}).statuses || [])",
            "renderUnifiedReadCapabilityOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.readCapability, (data.facets || {}).read_capabilities || [])",
            "renderUnifiedActionOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.action, (data.facets || {}).actions || [])",
            "renderUnifiedSortOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.sort)",
            "renderUnifiedDefinitionOptions",
            "buildUnifiedFacetCountMap",
            "getUnifiedActionDefinitions",
            "renderUnifiedActionSummary",
            "const actions = item && item.actions && typeof item.actions === 'object' ? item.actions : {};",
            "const definitions = getUnifiedActionDefinitions(item);",
            "${renderUnifiedActionSummary(item)}",
            "data-action=\"${escapeHtml(action)}\"",
            "const stateLabel = translateUnifiedText(isEnabled ? '可用' : '不可用');",
            "aria-label=\"${escapeHtml(`${displayLabel}: ${stateLabel}`)}\"",
            "normalizeUnifiedFacetCount",
            "const countsByValue = buildUnifiedFacetCountMap(facets, 'kind');",
            "countsByValue: buildUnifiedFacetCountMap(facets, 'status')",
            "countsByValue: buildUnifiedFacetCountMap(facets, 'read_capability')",
            "countsByValue: buildUnifiedFacetCountMap(facets, 'action')",
            "const displayLabel = countValue === null ? translatedLabel : `${translatedLabel} (${countValue})`;",
            "const readCapabilityFilter = safeFilters.read_capability || safeFilters.readCapability || 'all';",
            "contract.status_definitions",
            "contract.read_capability_definitions",
            "contract.action_definitions",
            "contract.sort_definitions",
            "UNIFIED_SORT_PLACEHOLDER_DEFINITIONS",
            "UNIFIED_QUICK_VIEW_PRESETS",
            "UNIFIED_QUICK_VIEW_DEFAULT_FILTERS",
            "UNIFIED_QUICK_VIEW_FILTER_KEYS",
            "normalizeUnifiedQuickViewPreset",
            "getUnifiedQuickViewPresets",
            "Array.isArray(sourceContract.quick_view_presets)",
            "const sourcePresets = contractPresets.length > 0 ? contractPresets : UNIFIED_QUICK_VIEW_PRESETS;",
            "source.description || source.detail || source.description_en",
            "pendingReload: false",
            "pendingForceRefresh: false",
            "workspaceView: 'inbox'",
            "function normalizeUnifiedWorkspaceView",
            "function renderUnifiedWorkspaceViewSwitch",
            "function setUnifiedWorkspaceView",
            "document.getElementById('unifiedWorkspaceViewSwitch')",
            "document.getElementById('unifiedInboxWorkflow')",
            "document.getElementById('unifiedDiagnosticsWorkspace')",
            "data-unified-workspace-view",
            "unifiedMailboxState.workspaceView = normalizeUnifiedWorkspaceView(view);",
            "renderUnifiedWorkspaceViewSwitch();",
            "setUnifiedWorkspaceView(button.dataset.unifiedWorkspaceView || 'inbox');",
            "key: 'all'",
            "key: 'accounts'",
            "key: 'temp'",
            "key: 'readable'",
            "key: 'attention'",
            "filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, kind: 'account' }",
            "filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, kind: 'temp' }",
            "filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, action: 'read_messages' }",
            "filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, status: 'inactive' }",
            "normalizeUnifiedQuickViewFilters",
            "getUnifiedQuickViewPreset",
            "getUnifiedQuickViewPresets(contract).find(preset => preset.key === normalizedKey)",
            "isUnifiedQuickViewPresetAvailable",
            "getUnifiedQuickViewKey",
            "getUnifiedQuickViewPresets(contract).find(item => {",
            "setUnifiedQuickViewDomFilters",
            "renderUnifiedQuickViews",
            "syncUnifiedQuickViews",
            "applyUnifiedQuickView",
            "getUnifiedMailboxRequestSignature",
            "document.getElementById('unifiedMailboxQuickViews')",
            "data-unified-quick-view",
            "button.dataset.unifiedQuickView || 'all'",
            "unifiedMailboxState.filters = normalizeUnifiedQuickViewFilters(preset.filters || {})",
            "const availablePresets = getUnifiedQuickViewPresets(contract).filter(preset => isUnifiedQuickViewPresetAvailable(preset, contract));",
            "setUnifiedQuickViewDomFilters(unifiedMailboxState.filters)",
            "unifiedMailboxState.page = 1",
            "loadUnifiedMailboxes(true)",
            "renderUnifiedQuickViews(unifiedMailboxState.filters, unifiedMailboxState.contract)",
            "renderUnifiedQuickViews(unifiedMailboxState.filters, unifiedMailboxState.contract || {})",
            "syncUnifiedQuickViews();",
            "renderUnifiedWorkspaceViewSwitch();",
            "quickViews.dataset.boundUnifiedQuickViews = '1';",
            "quickViews.addEventListener('click', event => {",
            "target.closest('.unified-quick-view[data-unified-quick-view]')",
            "if (unifiedMailboxState.loading) {",
            "unifiedMailboxState.pendingReload = true;",
            "unifiedMailboxState.pendingForceRefresh = unifiedMailboxState.pendingForceRefresh || force;",
            "const requestSignature = getUnifiedMailboxRequestSignature();",
            "if (requestSignature !== getUnifiedMailboxRequestSignature()) {",
            "const pendingForceRefresh = unifiedMailboxState.pendingForceRefresh;",
            "loadUnifiedMailboxes(pendingForceRefresh);",
            "directoryPayload: null",
            "directorySignature: ''",
            "directoryLoadSeq: 0",
            "directoryLoadForce: false",
            "directoryInFlightSignature: ''",
            "function invalidateUnifiedMailboxDirectoryCache",
            "window.invalidateUnifiedMailboxDirectoryCache = invalidateUnifiedMailboxDirectoryCache",
            "resetUnifiedMessagePreview()",
            "messagesLoadForce: false",
            "detailLoadForce: false",
            "verificationLoadForce: false",
            # Language change soft-paints warm directory (no forced network).
            "window.addEventListener('ui-language-changed'",
            "applyUnifiedMailboxDirectoryPayload(unifiedMailboxState.directoryPayload)",
            "function applyUnifiedMailboxDirectoryPayload",
            "unifiedMailboxState.directorySignature === requestSignature",
            "applyUnifiedMailboxDirectoryPayload(unifiedMailboxState.directoryPayload)",
            "unifiedMailboxState.directoryPayload = data",
            "unifiedMailboxState.directorySignature = requestSignature",
            "applyUnifiedMailboxDirectoryPayload(data)",
            "if (seq !== unifiedMailboxState.directoryLoadSeq)",
            "unifiedMailboxState.directoryLoadForce = force",
            "force && !unifiedMailboxState.directoryLoadForce",
            # Surface paint guard: always warm directory; paint only on unified view + same signature.
            "function isCurrentUnifiedMailboxSurface()",
            "mailboxViewMode === 'unified'",
            "const isCurrentUnifiedDirectoryView = () => (",
            "getUnifiedMailboxRequestSignature() === requestSignature",
            "if (isCurrentUnifiedDirectoryView())",
            "// Always warm directory soft cache; paint only while still current view.",
            "class=\"unified-quick-view ${active ? 'active' : ''}\"",
            "class=\"unified-quick-view custom ${customActive ? 'active' : ''}\"",
            "aria-pressed=\"${active ? 'true' : 'false'}\"",
            "container.hidden = false;",
            "getUnifiedKindDefinition",
            "getUnifiedKindLabel(kind)",
            "const kindClass = getUnifiedKindClass(kind)",
            "renderUnifiedProviderOptions(unifiedMailboxState.providerFacets, unifiedMailboxState.filters.provider)",
            "renderUnifiedProviderContext",
            "renderUnifiedProviderCapabilityMatrix",
            "renderUnifiedProviderFacetChips",
            "setUnifiedProviderFilter",
            "renderUnifiedResultBar",
            "getUnifiedSetupGuideEndpoint",
            "getUnifiedSetupGuideStatusLabel",
            "getUnifiedSetupGuideModel",
            "renderUnifiedSetupGuideAction",
            "renderUnifiedSetupGuideStep",
            "renderUnifiedSetupGuide",
            "renderUnifiedCommandCenter",
            "getUnifiedOperationalActiveFilterCount",
            "getUnifiedOperationalViewLabel",
            "getUnifiedOperationalProviderCounts",
            "getUnifiedOperationalLensState",
            "getUnifiedOperationalRecommendation",
            "renderUnifiedLensAction",
            "renderUnifiedOperationalLens",
            "document.getElementById('unifiedMailboxOperationalLens')",
            "renderUnifiedOperationalLens({}, 'loading')",
            "renderUnifiedOperationalLens({}, 'error')",
            "renderUnifiedOperationalLens(data, 'ready')",
            "document.getElementById('unifiedMailboxSetupGuide')",
            "renderUnifiedSetupGuide({}, 'loading')",
            "renderUnifiedSetupGuide({}, 'error')",
            "renderUnifiedSetupGuide(data, 'ready')",
            "data-unified-setup-action",
            "data-unified-setup-view",
            "setupGuide.dataset.boundUnifiedSetupGuide = '1';",
            "target.closest('.unified-setup-action[data-unified-setup-action]')",
            "applyUnifiedQuickView(button.dataset.unifiedSetupView || 'all')",
            "switchMailboxViewMode('standard')",
            "navigate('temp-emails')",
            "switchSettingsTab('api-security')",
            "统一邮箱启动路径",
            "账号库存、临时邮箱、Provider 路由和外部 API 接入",
            "data-unified-lens-action",
            "data-unified-lens-view",
            "operationalLens.dataset.boundUnifiedOperationalLens = '1';",
            "target.closest('.unified-lens-action[data-unified-lens-action]')",
            "applyUnifiedQuickView(button.dataset.unifiedLensView || 'all')",
            "providerContext.scrollIntoView({ block: 'nearest', behavior: 'smooth' });",
            "运营态势",
            "当前视图状态",
            "Provider 就绪",
            "建议动作",
            "筛选条件",
            "getUnifiedCommandEndpoint",
            "getUnifiedCommandProviderMode",
            "getUnifiedCommandProviderCount",
            "getUnifiedCommandActionCount",
            "getUnifiedCommandDefaultProvider",
            "getUnifiedCommandSourcePriority",
            "renderUnifiedCommandInsight",
            "renderUnifiedCommandMetric",
            "renderUnifiedCommandChip",
            "renderUnifiedCommandQuickViews",
            "getUnifiedQuickViewPresets(contract).filter(preset => isUnifiedQuickViewPresetAvailable(preset, contract))",
            "getUnifiedQuickViewKey(filters, contract)",
            "data-unified-command-view",
            "aria-label=\"${escapeHtml(translateUnifiedText('推荐视图'))}\"",
            "renderUnifiedCommandState",
            "正在同步目录库存、来源策略和推荐视图",
            "保留当前筛选，稍后可重试刷新目录",
            "document.getElementById('unifiedMailboxCommandCenter')",
            "providerContext.provider_integration_guide",
            "providerContext.provider_diagnostics",
            "providerContext.readiness_summary",
            "getUnifiedProviderReadinessSummary",
            "renderUnifiedProviderReadinessSummary",
            "readinessSummary.totals",
            "readinessSummary.provider_selector_fields",
            "readinessSummary.routing_matrix",
            "readinessSummary.providers",
            "getUnifiedProviderRoutingMatrix",
            "renderUnifiedProviderRoutingMatrix",
            "unified-provider-readiness-summary",
            "unified-provider-routing-matrix",
            "unified-provider-routing-scope",
            "unified-provider-routing-providers",
            "unified-provider-readiness-row",
            "providerContext.selection_policy",
            "providerContext.defaults",
            "defaults.temp_mail_provider",
            "defaults.pool_claim_provider",
            "contract.action_definitions",
            "Number(diagnostics.total || 0)",
            "guideEndpoints.mailboxes || discovery.mailboxes_endpoint || discovery.external_mailboxes_endpoint",
            "getUnifiedCommandSourcePriority(providerContext)",
            "getUnifiedCommandDefaultProvider(providerContext, 'temp_mail_provider')",
            "getUnifiedCommandDefaultProvider(providerContext, 'pool_claim_provider', 'auto')",
            "renderUnifiedCommandCenter({}, 'loading')",
            "renderUnifiedProviderCapabilityMatrix({}, {}, 'loading', 'all')",
            "renderUnifiedCommandCenter({}, 'error')",
            "renderUnifiedProviderCapabilityMatrix({}, {}, 'error', 'all')",
            "renderUnifiedCommandCenter(data, 'ready')",
            "renderUnifiedCommandQuickViews(currentFilters, contract)",
            "统一邮箱工作台",
            "集中管理 Outlook、IMAP、临时邮箱与外部 API 调用",
            "Graph/IMAP 读信与验证码提取",
            "按 provider 创建、读取与远端清理",
            "aria-label=\"${escapeHtml(translateUnifiedText('统一邮箱路由摘要'))}\"",
            "renderUnifiedCommandInsight('运行默认', tempDefaultProvider, translateUnifiedText('临时邮箱默认'))",
            "renderUnifiedCommandInsight('领取默认', poolDefaultProvider, translateUnifiedText('Pool 默认'))",
            "renderUnifiedCommandInsight('来源优先级', sourcePriority, translateUnifiedText('Provider 选择'))",
            "renderUnifiedCommandInsight('目录入口', providerEndpoint, translateUnifiedText('外部调用'))",
            "getUnifiedSelectLabel",
            "setUnifiedRefreshBusy",
            "document.getElementById('unifiedMailboxResultBar')",
            "document.getElementById('unifiedMailboxRefreshBtn')",
            "button.setAttribute('aria-busy', 'true')",
            "button.removeAttribute('aria-busy')",
            "button.disabled = Boolean(isBusy)",
            "button.textContent = translateUnifiedText('刷新中...')",
            "data.provider_context || {}",
            "(data.facets || {}).providers || []",
            "data.pagination || {}",
            "data.filters || unifiedMailboxState.filters",
            "const selectedProvider = (data.filters || unifiedMailboxState.filters).provider || 'all';",
            "renderUnifiedProviderContext(unifiedMailboxState.providerContext, 'ready', unifiedMailboxState.providerFacets, selectedProvider)",
            "renderUnifiedProviderCapabilityMatrix(unifiedMailboxState.providerContext, unifiedMailboxState.contract, 'ready', selectedProvider)",
            "providerContext.provider_diagnostics",
            "providerDiagnostics.defaults",
            "selectionPolicy.source_priority",
            "getUnifiedProviderConfigFile(selectionPolicy, deploymentProfile, providerFilter)",
            "buildUnifiedProviderNoticeMessages(providerFilter, defaultsDiagnostics, configFile, diagnostics)",
            "getUnifiedProviderContextState(providerFilter, defaultsDiagnostics, configFile, diagnostics)",
            "container.dataset.state = status;",
            "providerFilter.config_error_code",
            "configFile.error_code",
            "providerFilter.unknown_providers",
            "defaultsDiagnostics.invalid_defaults",
            "defaultsDiagnostics.inactive_defaults",
            "formatUnifiedProviderSourceDetail(tempDefaultDiagnostic, defaults.temp_mail_provider_env)",
            "config_file_error: '配置文件错误'",
            "formatUnifiedProviderConfigFileStatus(configFile)",
            "discovery.provider_health_endpoint",
            "unified-provider-context-status",
            "unified-provider-context-alert",
            "getUnifiedOpenTarget",
            "item.action_contract || {}",
            "internalActions.open_mailbox || {}",
            "openTarget.mode || kind",
            "normalizedKind === 'temp' || normalizedKind === 'temp-emails'",
            "bindUnifiedMailboxControls",
            "document.getElementById('unifiedMailboxProviderFilter')",
            "document.getElementById('unifiedMailboxReadCapabilityFilter')",
            "document.getElementById('unifiedMailboxActionFilter')",
            "document.getElementById('unifiedMailboxSortFilter')",
            "document.getElementById('unifiedMailboxProviderContext')",
            "document.getElementById('unifiedProviderCapabilityMatrix')",
            "document.getElementById('unifiedMailboxCommandCenter')",
            "commandCenter.dataset.boundUnifiedCommandViews = '1';",
            "target.closest('.unified-command-view[data-unified-command-view]')",
            "applyUnifiedQuickView(button.dataset.unifiedCommandView || 'all')",
            "container.dataset.state = isLoading ? 'loading' : (state === 'error' ? 'error' : 'warning');",
            "${renderUnifiedProviderFacetChips(providerFacets, selectedProvider)}",
            "select.value = provider;",
            "unifiedMailboxState.filters.provider = provider;",
            "data-provider=\"${escapeHtml(item.provider)}\"",
            "aria-pressed=\"${item.provider === selected ? 'true' : 'false'}\"",
            "facets.reduce((sum, item) => sum + normalizeUnifiedFacetCount(item && item.count), 0)",
            "providerContext.dataset.boundUnifiedProviderFacets = '1';",
            "providerContext.addEventListener('click', event => {",
            "providerCapabilityMatrix.dataset.boundUnifiedProviderCapabilityMatrix = '1';",
            "providerCapabilityMatrix.addEventListener('click', event => {",
            "const target = event.target && typeof event.target.closest === 'function' ? event.target : null;",
            "const button = target ? target.closest('.unified-provider-facet') : null;",
            "const button = target ? target.closest('.unified-provider-capability-filter') : null;",
            "setUnifiedProviderFilter(button.dataset.provider || 'all');",
            "openUnifiedMailbox",
            "selectAccount(email)",
            "selectTempEmail(email)",
            "copyVerificationInfo",
        ]:
            self.assertIn(expected, module_js)

        for expected in [
            "items: [],",
            "preview: {",
            "function getUnifiedMessageMailboxKey",
            "function getUnifiedMessageEndpoint",
            "function getUnifiedMessageDetailEndpoint",
            "function renderUnifiedMessagePreview",
            "function loadUnifiedMailboxMessages",
            "function openUnifiedMessagePreviewFromCard",
            "function loadUnifiedMailboxMessageDetail",
            "function loadUnifiedMailboxVerification",
            "function copyUnifiedPreviewValue",
            "document.getElementById('unifiedMailboxMessagePreview')",
            "`/api/mailboxes/${cleanKind}/${cleanSourceId}/${cleanSuffix}`",
            "messages/${encodeURIComponent(String(messageId || ''))}",
            "window.DOMPurify",
            "openUnifiedMessagePreviewFromCard('${escapeJs(kind)}', ${sourceId})",
            "openUnifiedMailbox(${openSourceId}",
            "预览邮件",
            "打开原页面",
            "renderUnifiedMessagePreview();",
            "function getUnifiedMailboxProviderDisplayLabel",
            "resolveMailboxProviderLabel",
            "getUnifiedMailboxProviderDisplayLabel(item)",
            "getUnifiedMailboxProviderDisplayLabel(mailbox)",
            "getUnifiedMailboxProviderDisplayLabel(provider)",
            "payload.provider_label || payload.label",
            "function refreshUnifiedMailboxProviderLabelsFromCatalog",
            "providerContext: {}",
            "providerFacets: []",
            "function canonicalizeUnifiedTempProviderKey",
            "function dedupeUnifiedTempProviderRows",
            "function normalizeUnifiedProviderFacets",
            "custom_domain_temp_mail: 'legacy_bridge'",
            "dedupeUnifiedTempProviderRows(",
            "normalizeUnifiedProviderFacets(facets)",
            "normalizeUnifiedProviderFacets(providerFacets)",
        ]:
            self.assertIn(expected, module_js)

        # Capability matrix rows also resolve labels through the shared helper.
        self.assertIn(
            "label: getUnifiedMailboxProviderDisplayLabel({",
            module_js,
        )
        # Catalog success can repaint from cached items without a network reload.
        self.assertIn("renderUnifiedMailboxList(unifiedMailboxState.items)", module_js)
        self.assertIn("renderUnifiedProviderContext(", module_js)
        self.assertIn("renderUnifiedProviderCapabilityMatrix(", module_js)

        preview_start = module_js.index("function normalizeUnifiedPreviewKind")
        preview_end = module_js.index("function renderUnifiedMailboxCard")
        preview_js = module_js[preview_start:preview_end]
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "/api/v1/external/",
            "/api/v1/external/",
            "DUCKMAIL_BEARER_TOKEN",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
            "provider === 'legacy_bridge'",
            'provider === "legacy_bridge"',
        ]:
            self.assertNotIn(forbidden, preview_js)

        self.assertNotIn("onclick=\"setUnifiedProviderFilter", module_js)
        self.assertNotIn("const UNIFIED_STATUS_FALLBACK_DEFINITIONS", module_js)
        self.assertNotIn("const UNIFIED_SORT_FALLBACK_DEFINITIONS", module_js)
        self.assertNotIn("{ status: 'cooldown'", module_js)
        self.assertNotIn("{ read_capability: 'temp_provider'", module_js)
        self.assertNotIn("{ action: 'delete_remote_mailbox'", module_js)
        self.assertNotIn("{ sort: 'email_asc'", module_js)

        quick_view_start = module_js.index("const UNIFIED_QUICK_VIEW_PRESETS")
        quick_view_end = module_js.index("function normalizeUnifiedFacetCount")
        quick_view_js = module_js[quick_view_start:quick_view_end]
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "DUCKMAIL_BEARER_TOKEN",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
        ]:
            self.assertNotIn(forbidden, quick_view_js)

        command_start = module_js.index("function getUnifiedCommandEndpoint")
        command_end = module_js.index("function renderUnifiedLoadingState")
        command_js = module_js[command_start:command_end]
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "DUCKMAIL_BEARER_TOKEN",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
        ]:
            self.assertNotIn(forbidden, command_js)

        lens_start = module_js.index("function getUnifiedOperationalActiveFilterCount")
        lens_end = module_js.index("function getUnifiedCommandEndpoint")
        lens_js = module_js[lens_start:lens_end]
        for expected in [
            "normalizeUnifiedQuickViewFilters(filters || {})",
            "getUnifiedQuickViewKey(filters, contract)",
            "getUnifiedProviderReadinessSummary(providerContext)",
            "provider_context",
            "provider_diagnostics",
            "summary.inactive",
            "pagination.total_count",
            "data-unified-lens-action",
            "data-unified-lens-view",
            "focus-provider-context",
            "quick-view",
            "refresh",
        ]:
            self.assertIn(expected, lens_js)
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "DUCKMAIL_BEARER_TOKEN",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
            "provider === 'legacy_bridge'",
            'provider === "legacy_bridge"',
        ]:
            self.assertNotIn(forbidden, lens_js)

        setup_start = module_js.index("function getUnifiedSetupGuideEndpoint")
        setup_end = module_js.index("function getUnifiedOperationalActiveFilterCount")
        setup_js = module_js[setup_start:setup_end]
        for expected in [
            "providerContext.provider_integration_guide",
            "providerContext.documentation",
            "readinessSummary.endpoints",
            "getUnifiedProviderReadinessSummary(providerContext)",
            "getUnifiedOperationalProviderCounts(providerContext)",
            "summary.account || readinessTotals.account_mailboxes",
            "summary.temp || readinessTotals.temp_mailboxes",
            "guideEndpoints.mailboxes",
            "guideEndpoints.providers",
            "guideEndpoints.integration_bundle",
            "steps.some(step => step.status === 'warning' || step.status === 'action')",
            "data-unified-setup-action",
            "data-unified-setup-view",
            "open-account-view",
            "open-temp-workspace",
            "open-api-security",
            "focus-provider-context",
            "quick-view",
            "refresh",
        ]:
            self.assertIn(expected, setup_js)
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "DUCKMAIL_BEARER_TOKEN",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
            "provider === 'legacy_bridge'",
            'provider === "legacy_bridge"',
        ]:
            self.assertNotIn(forbidden, setup_js)

        routing_start = module_js.index("function getUnifiedProviderRoutingMatrix")
        routing_end = module_js.index("function renderUnifiedProviderReadinessSummary")
        routing_js = module_js[routing_start:routing_end]
        for expected in [
            "readinessSummary.routing_matrix",
            "Number(routingMatrix.version || 0) !== 1",
            "Object.values(scopes)",
            "scope.request_field",
            "scope.endpoint",
            "scope.counts",
            "scope.providers",
            "provider.usable",
            "unified-provider-routing-matrix",
            "unified-provider-routing-scope",
            "unified-provider-routing-providers",
        ]:
            self.assertIn(expected, routing_js)
        for forbidden in [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "DUCKMAIL_BEARER_TOKEN",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
        ]:
            self.assertNotIn(forbidden, routing_js)

    def test_unified_provider_capability_matrix_consumes_matrix_with_guide_fallback_without_secret_values(self):
        client = self.app.test_client()
        module_js = load_mailboxes_js()
        block_start = module_js.index("function getUnifiedProviderGuideProviders")
        block_end = module_js.index("function normalizeUnifiedStatus")
        matrix_js = module_js[block_start:block_end]

        for expected in [
            "function getUnifiedProviderCapabilityMatrix(providerContext = {})",
            "providerContext.readiness_summary",
            "readinessSummary.capability_matrix",
            "function getUnifiedProviderCapabilityMatrixProviders(providerContext = {})",
            "function getUnifiedProviderCapabilityMatrixWorkflows(providerContext = {})",
            "const matrixProviders = getUnifiedProviderCapabilityMatrixProviders(providerContext);",
            "const workflows = getUnifiedProviderCapabilityMatrixWorkflows(providerContext);",
            "const providers = dedupeUnifiedTempProviderRows(",
            "matrixProviders.length > 0 ? matrixProviders : getUnifiedProviderGuideProviders(providerContext)",
            "providerContext.provider_integration_guide",
            "return Array.isArray(guide.providers)",
            "const capabilities = provider.capabilities && typeof provider.capabilities === 'object' ? provider.capabilities : {};",
            "const configuration = normalizeUnifiedProviderCapabilityObject(provider.configuration);",
            "const read = normalizeUnifiedProviderCapabilityObject(provider.read);",
            "const inventory = normalizeUnifiedProviderCapabilityObject(provider.inventory);",
            "provider.workflow_support",
            "provider.selection_fields",
            "read.actions",
            "provider.lifecycle_actions",
            "provider.endpoints",
            "configuration.needs_config",
            "configuration.missing_config_count",
            "capabilities.can_dynamic_create",
            "capabilities.can_delete_mailbox",
            "capabilities.can_delete_message",
            "capabilities.can_clear_messages",
            "provider.active",
            "provider.configured",
            "provider.readiness_status",
            "provider.missing_config || configuration.missing_config",
            "provider.required_env || configuration.required_env",
            "provider.optional_env || configuration.optional_env",
            "provider.secret_env || configuration.secret_env",
            "provider.secret_settings || configuration.secret_settings",
            "secretKeys: [...secretEnv, ...secretSettings]",
            "workflowEntries",
            "selectionFields",
            "readActions",
            "lifecycleActions",
            "renderUnifiedProviderCapabilityWorkflowSummary(workflows)",
            "renderUnifiedProviderCapabilityWorkflowChips(row.workflowEntries)",
            "renderUnifiedProviderCapabilitySelectorFields(row.selectionFields)",
            "renderUnifiedProviderCapabilityActionList('读取动作', row.readActions)",
            "renderUnifiedProviderCapabilityActionList('生命周期', row.lifecycleActions)",
            "renderUnifiedProviderCapabilityEndpointList(row.endpoints)",
            "renderUnifiedProviderCapabilityKeys(row.secretKeys, '无')",
            "renderUnifiedProviderCapabilityBadge('动态创建', row.canDynamicCreate)",
            "renderUnifiedProviderCapabilityBadge('删除远端邮箱', row.canDeleteMailbox)",
            "renderUnifiedProviderCapabilityBadge('删除邮件', row.canDeleteMessage)",
            "renderUnifiedProviderCapabilityBadge('清空邮件', row.canClearMessages)",
        ]:
            self.assertIn(expected, matrix_js)

        for forbidden in [
            "provider_diagnostics.providers",
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "copyToClipboard",
            "DUCKMAIL_BEARER_TOKEN",
            "dk_",
            "provider === 'duckmail'",
            'provider === "duckmail"',
            "provider === 'mail_tm'",
            'provider === "mail_tm"',
            "provider === 'tempmail_lol'",
            'provider === "tempmail_lol"',
            "provider === 'emailnator'",
            'provider === "emailnator"',
            "provider === 'gptmail'",
            'provider === "gptmail"',
            "provider === 'legacy_bridge'",
            'provider === "legacy_bridge"',
        ]:
            self.assertNotIn(forbidden, matrix_js)

    def test_unified_mailbox_css_defines_responsive_directory_layout(self):
        client = self.app.test_client()
        css = self._get_text(client, "/static/css/main.css")

        for expected in [
            ".mailbox-unified-layout",
            ".unified-workspace-masthead",
            ".unified-workspace-masthead::after",
            ".unified-workspace-kicker",
            ".unified-workspace-pipeline",
            ".unified-workspace-pipeline span",
            ".unified-command-center",
            ".unified-command-center[data-state=\"loading\"]",
            ".unified-command-center[data-state=\"error\"]",
            ".unified-command-state",
            ".unified-command-state-copy",
            ".unified-command-state-grid",
            "@keyframes unifiedCommandPulse",
            "@media (prefers-reduced-motion: reduce)",
            ".unified-mailbox-card,",
            ".unified-command-main",
            "grid-row: span 2;",
            ".unified-workspace-view-switch",
            ".unified-workspace-view-button",
            ".unified-workspace-view-button.active",
            ".unified-inbox-workflow",
            ".unified-inbox-main",
            ".unified-directory-pane",
            ".unified-diagnostics-workspace",
            ".unified-diagnostics-workspace[data-active=\"false\"]",
            ".unified-command-route",
            ".unified-command-insights",
            ".unified-command-insight",
            ".unified-command-insight-label",
            ".unified-command-insight strong",
            ".unified-command-metrics",
            ".unified-command-metric",
            ".unified-command-views",
            "grid-column: 2;",
            ".unified-command-views-head",
            ".unified-command-view-rail",
            ".unified-command-view",
            ".unified-command-view:hover",
            ".unified-command-view:focus-visible",
            ".unified-command-view.active",
            ".unified-command-workflows",
            ".unified-command-chip",
            ".unified-command-notice",
            ".unified-toolbar",
            ".unified-toolbar-field",
            ".unified-toolbar-field-search",
            ".unified-filter-label",
            ".unified-toolbar-refresh",
            "repeat(auto-fit, minmax(124px, 1fr))",
            "grid-column: span 2;",
            ".unified-quick-views",
            ".unified-quick-views[hidden]",
            ".unified-quick-view",
            ".unified-quick-view:hover",
            ".unified-quick-view:focus-visible",
            ".unified-quick-view.active",
            ".unified-quick-view.custom",
            ".unified-quick-view.custom:not(.active)",
            ".unified-quick-view-label",
            ".unified-quick-view-detail",
            ".unified-result-bar",
            ".unified-result-chip",
            ".unified-result-chip.muted",
            ".unified-result-bar[data-state=\"loading\"]",
            ".unified-result-bar[data-state=\"error\"]",
            ".unified-setup-guide",
            ".unified-setup-guide[data-state=\"ready\"]",
            ".unified-setup-guide[data-state=\"warning\"]",
            ".unified-setup-guide[data-state=\"error\"]",
            ".unified-setup-guide-head",
            ".unified-setup-guide-kicker",
            ".unified-setup-guide-status",
            ".unified-setup-guide-steps",
            ".unified-setup-step",
            ".unified-setup-step[data-setup-step-state=\"ready\"]",
            ".unified-setup-step[data-setup-step-state=\"warning\"]",
            ".unified-setup-step[data-setup-step-state=\"action\"]",
            ".unified-setup-step-index",
            ".unified-setup-step-body",
            ".unified-setup-step-topline",
            ".unified-setup-step-actions",
            ".unified-setup-action",
            ".unified-setup-action:focus-visible",
            ".unified-setup-step-skeleton",
            ".unified-operational-lens",
            ".unified-operational-lens[data-state=\"ready\"]",
            ".unified-operational-lens[data-state=\"warning\"]",
            ".unified-operational-lens[data-state=\"empty\"]",
            ".unified-operational-lens[data-state=\"error\"]",
            ".unified-operational-lens[data-state=\"loading\"]",
            ".unified-lens-state",
            ".unified-lens-head",
            ".unified-lens-title-wrap",
            ".unified-lens-kicker",
            ".unified-lens-status",
            ".unified-lens-grid",
            "repeat(auto-fit, minmax(220px, 1fr))",
            ".unified-lens-card",
            ".unified-lens-label",
            ".unified-lens-actions",
            ".unified-lens-action",
            ".unified-lens-action:focus-visible",
            ".unified-summary",
            ".unified-provider-context",
            ".unified-provider-context[data-state=\"ok\"]",
            ".unified-provider-context[data-state=\"warning\"]",
            ".unified-provider-context[data-state=\"error\"]",
            ".unified-provider-context[data-state=\"loading\"]",
            ".unified-provider-context-title-wrap",
            ".unified-provider-context-status",
            ".unified-provider-context-alert",
            ".unified-provider-context-alert-text",
            ".unified-provider-context-grid",
            ".unified-provider-facets",
            ".unified-provider-facets.empty",
            ".unified-provider-facet",
            ".unified-provider-facet.active",
            ".unified-provider-facet-label",
            ".unified-provider-facet-meta",
            ".unified-provider-capability-matrix",
            ".unified-provider-capability-matrix[data-state=\"loading\"]",
            ".unified-provider-capability-matrix[data-state=\"error\"]",
            ".unified-provider-capability-head",
            ".unified-provider-capability-title-wrap",
            ".unified-provider-capability-workflows",
            ".unified-provider-capability-workflows span",
            ".unified-provider-capability-workflows strong",
            ".unified-provider-capability-grid",
            ".unified-provider-capability-row",
            ".unified-provider-capability-row.active",
            ".unified-provider-capability-filter",
            ".unified-provider-capability-state-badge.ready",
            ".unified-provider-capability-state-badge.needs-config",
            ".unified-provider-capability-chips",
            ".unified-provider-capability-chip.enabled",
            ".unified-provider-capability-chip.muted",
            ".unified-provider-capability-keys",
            ".unified-provider-capability-workflow-row",
            ".unified-provider-capability-selectors",
            ".unified-provider-capability-actions",
            ".unified-provider-capability-inventory",
            ".unified-provider-capability-endpoints",
            ".unified-mailbox-card",
            ".unified-mailbox-card:hover",
            ".unified-card-signals",
            ".unified-action-strip",
            ".unified-action-chip.enabled",
            ".unified-action-chip.muted",
            ".unified-card-actions",
            ".unified-mailbox-card.selected",
            ".unified-message-preview",
            ".unified-message-head",
            ".unified-message-workbench",
            ".unified-message-list",
            ".unified-message-list-scroll",
            ".unified-message-row",
            ".unified-message-row.active",
            ".unified-message-detail-pane",
            ".unified-message-detail.ready",
            ".unified-message-body",
            ".unified-message-verification",
            ".unified-message-verification-grid",
            "@media (max-width: 768px)",
        ]:
            self.assertIn(expected, css)

        reduced_motion_start = css.index("@media (prefers-reduced-motion: reduce)", css.index(".unified-message-preview"))
        reduced_motion_end = css.index("}", reduced_motion_start)
        reduced_motion_css = css[reduced_motion_start:reduced_motion_end]
        self.assertIn(".unified-card-actions .btn-inline,", reduced_motion_css)
        self.assertIn(".unified-message-row,", reduced_motion_css)
        self.assertNotIn(".unified-card-actions .btn-inline {\n  .unified-message-row", reduced_motion_css)

        mobile_start = css.index("@media (max-width: 768px)")
        mobile_css = css[mobile_start:]
        self.assertIn(".unified-workspace-view-switch", mobile_css)
        self.assertIn(".unified-workspace-view-button", mobile_css)
        self.assertIn(".unified-inbox-workflow", mobile_css)
        self.assertIn(".unified-inbox-main", mobile_css)
        self.assertIn(".unified-directory-pane", mobile_css)
        self.assertIn(".unified-diagnostics-workspace", mobile_css)
        self.assertIn(".unified-command-center", mobile_css)
        self.assertIn(".unified-command-center > *", mobile_css)
        self.assertIn("grid-column: 1 / -1;", mobile_css)
        self.assertIn(".unified-command-state", mobile_css)
        self.assertIn(".unified-command-insights", mobile_css)
        self.assertIn(".unified-command-insight", mobile_css)
        self.assertIn(".unified-command-view-rail", mobile_css)
        self.assertIn("overflow-x: auto;", mobile_css)
        self.assertIn(".unified-command-chip", mobile_css)
        self.assertIn(".unified-toolbar-field", mobile_css)
        self.assertIn(".unified-toolbar-field-search", mobile_css)
        self.assertIn(".unified-toolbar-refresh", mobile_css)
        self.assertIn(".unified-quick-views", mobile_css)
        self.assertIn(".unified-quick-view", mobile_css)
        self.assertIn(".unified-setup-guide", mobile_css)
        self.assertIn(".unified-setup-guide-head", mobile_css)
        self.assertIn(".unified-setup-guide-steps", mobile_css)
        self.assertIn(".unified-setup-step", mobile_css)
        self.assertIn(".unified-setup-step-topline", mobile_css)
        self.assertIn(".unified-setup-action", mobile_css)
        self.assertIn(".unified-setup-step-skeleton", mobile_css)
        self.assertIn(".unified-operational-lens", mobile_css)
        self.assertIn(".unified-lens-head", mobile_css)
        self.assertIn(".unified-lens-grid", mobile_css)
        self.assertIn("grid-template-columns: 1fr;", mobile_css)
        self.assertIn(".unified-lens-action", mobile_css)
        self.assertIn(".unified-action-strip", mobile_css)
        self.assertIn(".unified-card-signals", mobile_css)
        self.assertIn(".unified-provider-facets", mobile_css)
        self.assertIn(".unified-provider-capability-row", mobile_css)
        self.assertIn(".unified-provider-capability-workflows", mobile_css)
        self.assertIn(".unified-provider-capability-workflow-row", mobile_css)
        self.assertIn(".unified-provider-capability-chip", mobile_css)
        self.assertIn(".unified-provider-capability-selectors code", mobile_css)
        self.assertIn(".unified-provider-capability-actions code", mobile_css)
        self.assertIn(".unified-provider-capability-inventory code", mobile_css)
        self.assertIn(".unified-provider-capability-endpoints code", mobile_css)
        self.assertIn(".unified-message-preview", mobile_css)
        self.assertIn(".unified-message-head", mobile_css)
        self.assertIn(".unified-message-head-meta", mobile_css)
        self.assertIn(".unified-message-actions", mobile_css)
        self.assertIn(".unified-message-workbench", mobile_css)
        self.assertIn(".unified-message-list", mobile_css)
        self.assertIn(".unified-message-list-scroll", mobile_css)
        self.assertIn(".unified-message-detail-head", mobile_css)
        self.assertIn(".unified-message-body", mobile_css)
        self.assertIn("flex-wrap: wrap;", mobile_css)

    def test_unified_mailbox_i18n_covers_contract_driven_fallback_labels(self):
        client = self.app.test_client()
        i18n_js = self._get_text(client, "/static/js/i18n.js")

        for expected in [
            "'禁用': 'Disabled'",
            "'已结束': 'Finished'",
            "'池内可用': 'Available in pool'",
            "'全部读取方式': 'All read modes'",
            "'邮箱能力': 'Mailbox capability'",
            "'全部能力': 'All capabilities'",
            "'读取方式': 'Read mode'",
            "'不可用': 'Unavailable'",
            "'统一邮箱服务': 'Unified mailbox service'",
            "'统一邮箱工作台': 'Unified mailbox workspace'",
            "'集中管理 Outlook、IMAP、临时邮箱与外部 API 调用': 'Manage Outlook, IMAP, temp mailboxes, and external API access in one place'",
            "'正在读取统一邮箱服务…': 'Reading unified mailbox service...'",
            "'正在同步目录库存、来源策略和推荐视图': 'Syncing directory inventory, provider policy, and recommended views'",
            "'统一邮箱服务暂不可用': 'Unified mailbox service is temporarily unavailable'",
            "'保留当前筛选，稍后可重试刷新目录': 'Current filters are preserved; retry refreshing the directory later'",
            "'当前路由': 'Current route'",
            "'统一邮箱路由摘要': 'Unified mailbox routing summary'",
            "'当前视图': 'Current view'",
            "'推荐视图': 'Recommended views'",
            "'目录库存': 'Directory inventory'",
            "'路由模式': 'Routing mode'",
            "'外部入口': 'External entry'",
            "'目录入口': 'Directory entry'",
            "'统一邮箱工作流': 'Unified mailbox workflows'",
            "'Graph/IMAP 读信与验证码提取': 'Graph/IMAP reading and verification extraction'",
            "'按 provider 创建、读取与远端清理': 'Create, read, and clean up remotely by provider'",
            "'Provider 路由': 'Provider routing'",
            "'可用能力': 'available capabilities'",
            "'来源配置不可用': 'Provider configuration unavailable'",
            "'来源策略': 'Provider policy'",
            "'策略正常': 'Policy OK'",
            "'需要配置': 'Needs config'",
            "'配置异常': 'Config error'",
            "'配置提示': 'Config notice'",
            "'配置文件': 'Config file'",
            "'配置文件错误': 'Config file error'",
            "'发现接口': 'Discovery endpoint'",
            "'来源分布': 'Provider distribution'",
            "'暂无来源分布': 'No provider distribution yet'",
            "'Provider 能力矩阵': 'Provider capability matrix'",
            "'Provider 工作流': 'Provider workflows'",
            "'工作流支持': 'Workflow support'",
            "'暂无工作流': 'No workflows'",
            "'支持': 'Supported'",
            "'不支持': 'Unsupported'",
            "'选择字段': 'Selector fields'",
            "'暂无选择字段': 'No selector fields'",
            "'读取动作': 'Read actions'",
            "'生命周期': 'Lifecycle'",
            "'暂无动作': 'No actions'",
            "'库存': 'Inventory'",
            "'配置来源': 'Config source'",
            "'配置状态': 'Config status'",
            "'个缺失项': 'missing items'",
            "'暂无端点': 'No endpoints'",
            "'provider_health': 'Provider health'",
            "'mailbox_session_start': 'Session start'",
            "'正在读取 Provider 能力…': 'Loading provider capabilities...'",
            "'Provider 能力暂不可用': 'Provider capabilities unavailable'",
            "'暂无 Provider 能力': 'No provider capabilities yet'",
            "'动态创建': 'Dynamic create'",
            "'缺失配置': 'Missing config'",
            "'密钥字段名': 'Secret key names'",
            "'目录筛选': 'Directory filter'",
            "'Health': 'Health'",
            "'无配置文件': 'No config file'",
            "'已加载': 'Loaded'",
            "'未加载': 'Not loaded'",
            "'默认值': 'Default value'",
            "'运营态势': 'Operational posture'",
            "'当前视图状态': 'Current view status'",
            "'正在分析当前视图…': 'Analyzing current view...'",
            "'正在整理筛选、库存和 Provider 就绪度': 'Organizing filters, inventory, and provider readiness'",
            "'加载完成后显示建议动作': 'Recommended actions appear after loading'",
            "'空视图': 'Empty view'",
            "'风险提示': 'Risk notice'",
            "'当前视图可用': 'Current view is ready'",
            "'筛选条件': 'filters'",
            "'未应用筛选': 'No filters applied'",
            "'Provider 就绪': 'Provider readiness'",
            "'建议动作': 'Recommended action'",
            "'刷新目录重试': 'Refresh directory and retry'",
            "'目录读取失败，保留当前筛选': 'Directory loading failed; current filters are preserved'",
            "'清空筛选查看全量': 'Clear filters to view all'",
            "'当前筛选没有命中邮箱': 'Current filters matched no mailboxes'",
            "'检查 Provider 配置': 'Review provider configuration'",
            "'查看来源策略': 'View provider policy'",
            "'查看需处理邮箱': 'View mailboxes needing attention'",
            "'继续打开邮箱、复制验证码或刷新目录': 'Continue opening mailboxes, copying verification codes, or refreshing the directory'",
            "'Setup Path': 'Setup Path'",
            "'统一邮箱启动路径': 'Unified mailbox setup path'",
            "'正在整理账号、临时邮箱、Provider 路由和外部 API 接入状态': 'Organizing account, temp-mail, provider routing, and external API access status'",
            "'读取中': 'Loading'",
            "'待处理': 'Needs action'",
            "'需配置': 'Needs configuration'",
            "'待确认': 'Needs confirmation'",
            "'目录读取失败，保留当前配置路径': 'Directory loading failed; setup path is preserved'",
            "'重新读取统一邮箱目录和 Provider 就绪度': 'Reload unified mailbox directory and provider readiness'",
            "'按顺序完成账号库存、临时邮箱、Provider 路由和外部 API 接入': 'Complete account inventory, temp mailboxes, provider routing, and external API access in order'",
            "'普通账号已接入': 'Account mailboxes connected'",
            "'接入普通账号': 'Connect account mailboxes'",
            "'Outlook/IMAP 账号已进入统一目录': 'Outlook/IMAP accounts are in the unified directory'",
            "'导入或配置 Outlook/IMAP 账号作为稳定邮箱库存': 'Import or configure Outlook/IMAP accounts as stable mailbox inventory'",
            "'查看普通账号': 'View account mailboxes'",
            "'打开账号视图': 'Open account view'",
            "'个普通账号': 'account mailboxes'",
            "'临时邮箱已接入': 'Temp mailboxes connected'",
            "'配置临时邮箱': 'Configure temp mailboxes'",
            "'Provider 临时邮箱已进入统一目录': 'Provider temp mailboxes are in the unified directory'",
            "'创建临时邮箱或启用可动态创建的 Provider': 'Create temp mailboxes or enable a dynamically creatable provider'",
            "'查看临时邮箱': 'View temp mailboxes'",
            "'打开临时邮箱': 'Open temp mailboxes'",
            "'个临时邮箱': 'temp mailboxes'",
            "'Provider 需要配置': 'Provider needs configuration'",
            "'Provider 路由可用': 'Provider routing is available'",
            "'检查缺失配置、来源优先级和路由矩阵': 'Review missing config, source priority, and routing matrix'",
            "'外部 API 接入': 'External API access'",
            "'打开 API 安全': 'Open API Security'",
            "'聚合邮箱快速视图': 'Unified mailbox quick views'",
            "'全部邮箱': 'All mailboxes'",
            "'完整目录': 'Full directory'",
            "'Outlook/IMAP': 'Outlook/IMAP'",
            "'Provider 邮箱': 'Provider mailboxes'",
            "'可读信': 'Readable'",
            "'支持读取邮件': 'Supports message reading'",
            "'需处理': 'Needs attention'",
            "'停用或不可用': 'Inactive or unavailable'",
            "'自定义筛选': 'Custom filters'",
            "'手动组合': 'Manual mix'",
            "'统一邮箱聚合服务': 'Unified mailbox aggregation service'",
            "'统一邮箱链路': 'Unified mailbox pipeline'",
            "'日常收件箱': 'Daily inbox'",
            "'高级诊断': 'Advanced diagnostics'",
            "'目录与预览': 'Directory and preview'",
            "'配置与扩展': 'Configuration and extensibility'",
            "'验证码读取': 'Verification reading'",
            "'Inbox Preview': 'Inbox Preview'",
            "'统一收件箱预览': 'Unified inbox preview'",
            "'选择一个邮箱查看邮件': 'Select a mailbox to read messages'",
            "'最近邮件': 'Recent messages'",
            "'读取邮件': 'Read messages'",
            "'刷新邮件': 'Refresh messages'",
            "'提取验证码': 'Extract verification'",
            "'验证码结果': 'Verification result'",
            "'暂无邮件': 'No messages'",
            "'邮件读取失败': 'Failed to read messages'",
            "'邮件详情': 'Message detail'",
            "'打开原页面': 'Open original page'",
            "'预览邮件': 'Preview messages'",
            "'正文': 'Body'",
            "'HTML 正文': 'HTML body'",
            "'文本正文': 'Text body'",
            "'复制验证码': 'Copy code'",
            "'复制验证链接': 'Copy verification link'",
            "'验证链接已复制': 'Verification link copied'",
            "'正在读取邮件…': 'Reading messages...'",
            "'正在读取邮件详情…': 'Reading message detail...'",
            "'正在提取验证码…': 'Extracting verification...'",
            "'邮件详情读取失败': 'Failed to read message detail'",
            "'验证码读取失败': 'Failed to read verification'",
            "'选择一封邮件查看详情': 'Select a message to view details'",
            "'暂无正文': 'No body'",
            "'无正文预览': 'No preview'",
            "'统一读取通道': 'Unified read channel'",
            "'选中邮箱': 'Selected mailbox'",
            "'发件人': 'From'",
            "'收件人': 'To'",
            "'验证码': 'Verification code'",
            "'验证链接': 'Verification link'",
            "'置信度': 'Confidence'",
            "'未找到': 'Not found'",
            "'点击提取验证码查看结果': 'Extract verification to view result'",
            "'内容已复制到剪贴板': 'Copied to clipboard'",
            "'复制失败，请手动复制': 'Copy failed; copy manually'",
        ]:
            self.assertIn(expected, i18n_js)


if __name__ == "__main__":
    unittest.main()
