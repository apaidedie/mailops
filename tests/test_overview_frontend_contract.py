"""Frontend contract tests for the overview command center surface."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests._import_app import import_web_app_module
from tests.frontend_js_bundle import load_feature_package_js, load_frontend_app_js, load_mailboxes_js

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_CONSOLE = "\u8fd0\u8425\u63a7\u5236\u53f0"
SERVICE_HEALTH = "\u8fd0\u884c\u72b6\u6001"
GLASS_PANEL = "\u73bb\u7483\u6001\u6982\u89c8\u9762\u677f"
REFINED_CARD_VIEW = "\u7ec6\u817b\u5361\u7247\u89c6\u56fe"
DATA_OVERVIEW = "\u6570\u636e\u6982\u89c8"
REFRESH = "\u5237\u65b0"
STRUCTURAL_EMOJI = ["\U0001f4ca", "\U0001f511", "\U0001f310", "\U0001f3b1", "\U0001f4cb"]


class OverviewFrontendContractTests(unittest.TestCase):
    """Ensure the overview remains an operational dashboard, not a decorative panel."""

    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client, password: str = "testpass123"):
        resp = client.post("/login", json={"password": password})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    def _get_index_html(self) -> str:
        client = self.app.test_client()
        self._login(client)
        resp = client.get("/")
        try:
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    def test_overview_header_uses_operational_copy(self):
        html = self._get_index_html()
        overview_block = html[html.index('id="page-dashboard"') : html.index('id="page-mailbox"')]

        self.assertIn('class="overview-tab-shell ov-command-shell"', overview_block)
        self.assertIn(f'id="ov-page-eyebrow">{OPERATIONS_CONSOLE}', overview_block)
        self.assertIn(f'id="ov-page-title">{DATA_OVERVIEW}', overview_block)
        self.assertIn(f'id="ov-page-badge">{SERVICE_HEALTH}', overview_block)
        self.assertIn(f'id="ov-refresh-btn">{REFRESH}</button>', overview_block)
        self.assertNotIn(GLASS_PANEL, overview_block)
        self.assertNotIn(REFINED_CARD_VIEW, overview_block)
        self.assertNotIn(f"{STRUCTURAL_EMOJI[0]} {DATA_OVERVIEW}", overview_block)

    def test_overview_tabs_do_not_use_structural_emoji(self):
        html = self._get_index_html()
        overview_block = html[html.index('id="page-dashboard"') : html.index('id="page-mailbox"')]
        tab_buttons = re.findall(
            r'<button[^>]*class="[^"]*ov-tab[^"]*"[^>]*>.*?</button>',
            overview_block,
        )

        self.assertEqual(len(tab_buttons), 5)
        self.assertTrue(all("ov-tab-label" in button for button in tab_buttons))
        for emoji in STRUCTURAL_EMOJI:
            self.assertNotIn(emoji, "".join(tab_buttons))

    def test_overview_js_does_not_emit_hover_explainers_or_emoji_icons(self):
        js_text = load_feature_package_js("static/js/features/overview")

        self.assertIn(f"'ov-page-eyebrow': '{OPERATIONS_CONSOLE}'", js_text)
        self.assertIn(f"'ov-page-badge': '{SERVICE_HEALTH}'", js_text)
        self.assertIn(f"titleEl.textContent = ovT('{DATA_OVERVIEW}');", js_text)
        self.assertIn(f"refreshBtn.textContent = ovT('{REFRESH}');", js_text)
        self.assertIn("function renderDataCard(options)", js_text)
        self.assertIn("ov-card-code", js_text)
        self.assertIn("return 'CODE';", js_text)
        self.assertIn("return 'POOL';", js_text)
        self.assertNotIn("renderHoverNote", js_text)
        self.assertNotIn("ov-hover-note", js_text)
        self.assertNotIn("hoverNote", js_text)
        for emoji in [*STRUCTURAL_EMOJI, "\U0001f4e3"]:
            self.assertNotIn(emoji, js_text)

    def test_external_api_overview_operations_console_contract(self):
        js_text = load_feature_package_js("static/js/features/overview")

        self.assertIn("function renderExternalApiHealthStrip(health, kpi)", js_text)
        self.assertIn("function renderExternalApiEndpointHealth(items)", js_text)
        self.assertIn("function renderExternalApiStatusBadge(status, errorCount)", js_text)
        self.assertIn("data.health || {}", js_text)
        self.assertIn("data.endpoint_health", js_text)
        self.assertIn("ov-api-health-strip", js_text)
        self.assertIn("ov-endpoint-health-list", js_text)
        self.assertIn("调用方健康", js_text)
        self.assertIn("接口健康", js_text)
        self.assertIn("错误率", js_text)

    def test_summary_command_center_render_contract(self):
        js_text = load_feature_package_js("static/js/features/overview")
        start = js_text.index("function renderOverviewSummary(data)")
        end = js_text.index("function renderVerificationStats(data)", start)
        summary_slice = js_text[start:end]

        self.assertIn("function renderOverviewCommandCenter(commandCenter)", summary_slice)
        self.assertIn("function renderOverviewCommandTile(options)", summary_slice)
        self.assertIn("function renderOverviewCommandActions(actions)", summary_slice)
        self.assertIn("normalizeOverviewCommandStatus", summary_slice)
        self.assertIn("formatOverviewCommandStatus", summary_slice)
        self.assertLess(
            summary_slice.index("renderOverviewCommandCenter(data.command_center || {})"),
            summary_slice.index('<div class="kpi-row">'),
        )
        self.assertIn("ov-command-center", summary_slice)
        self.assertIn("ov-command-grid", summary_slice)
        self.assertIn("ov-command-actions", summary_slice)
        self.assertIn("统一邮箱指挥台", summary_slice)
        self.assertIn("Provider 就绪", summary_slice)
        self.assertIn("外部 API 接入", summary_slice)
        # Next-actions tile uses a stable operator code, not a placeholder.
        self.assertIn('<span class="ov-card-code">NEXT</span>', summary_slice)
        self.assertNotIn('<span class="ov-card-code">TODO</span>', summary_slice)
        self.assertIn("下一步动作", summary_slice)

    def test_init_overview_soft_loads_warm_cache(self):
        """Returning to Dashboard must not force-reload a warm overview tab cache."""
        js_text = load_feature_package_js("static/js/features/overview")
        init_start = js_text.index("function initOverview()")
        init_end = js_text.index("function switchOverviewTab", init_start)
        init_slice = js_text[init_start:init_end]

        self.assertIn("switchOverviewTab(activeTab)", init_slice)
        # initOverview must soft-load via switchOverviewTab (cache hit or cold fetch).
        self.assertNotIn("loadOverviewTab(activeTab, true)", init_slice)
        self.assertNotIn("loadOverviewTab(activeTab, !", init_slice)

        # Explicit refresh and data-changed events still force-reload.
        self.assertIn("loadOverviewTab(__overviewState.activeTab || 'summary', true)", js_text)
        refresh_start = js_text.index("function refreshOverview()")
        refresh_end = js_text.index("function invalidateOverviewCache", refresh_start)
        refresh_slice = js_text[refresh_start:refresh_end]
        self.assertIn("loadOverviewTab(__overviewState.activeTab || 'summary', true)", refresh_slice)

    def test_load_overview_tab_coalesces_inflight_loads(self):
        """Concurrent overview tab loads share one promise; soft hits warm cache."""
        js_text = load_feature_package_js("static/js/features/overview")

        self.assertIn("loadPromises: {}", js_text)
        self.assertIn("loadForce: {}", js_text)
        self.assertIn("async function loadOverviewTab(tabId, forceReload = false)", js_text)

        load_start = js_text.index("async function loadOverviewTab(tabId, forceReload = false)")
        load_end = js_text.index("function renderOverviewTab(tabId, data)", load_start)
        load_slice = js_text[load_start:load_end]
        self.assertIn("!force && __overviewState.cache[targetTab]", load_slice)
        self.assertIn("__overviewState.loadPromises[targetTab]", load_slice)
        self.assertIn("__overviewState.loadPromises[targetTab] = request", load_slice)
        self.assertIn("__overviewState.loadForce[targetTab] = force", load_slice)
        # Soft joins any in-flight; force joins only force in-flight.
        self.assertIn("if (!force || __overviewState.loadForce[targetTab])", load_slice)
        # Force supersedes soft in-flight so Refresh starts a true network GET.
        self.assertIn("// Abandon soft in-flight bookkeeping; stale response identity check fails.", load_slice)
        # Active-tab paint guard: always warm cache; paint only while still the active tab.
        self.assertIn("const isCurrentOverviewTab = () =>", load_slice)
        self.assertIn("if (isCurrentOverviewTab())", load_slice)
        self.assertIn("// Always warm tab soft cache; paint only while still the active tab.", load_slice)
        # Must not early-return boolean loading without sharing the promise.
        self.assertNotIn("if (__overviewState.loading[tabId]) return;", load_slice)

        # Invalidate drops in-flight bookkeeping so force refresh can start clean.
        inv_start = js_text.index("function invalidateOverviewCache")
        inv_end = js_text.index("async function loadOverviewTab", inv_start)
        inv_slice = js_text[inv_start:inv_end]
        self.assertIn("delete __overviewState.loadPromises[tabId]", inv_slice)
        self.assertIn("delete __overviewState.loadForce[tabId]", inv_slice)

    def test_boot_defers_load_groups_and_tags(self):
        """Dashboard-first boot must not eagerly fetch /api/groups and /api/tags."""
        js_text = load_frontend_app_js()
        boot_start = js_text.index("document.addEventListener('DOMContentLoaded'")
        boot_end = js_text.index("setTimeout(checkVersionUpdate", boot_start)
        boot_slice = js_text[boot_start:boot_end]

        self.assertNotIn("loadGroups();", boot_slice)
        self.assertNotIn("loadTags();", boot_slice)
        # Mailbox still loads groups on demand when empty (soft-load friendly).
        self.assertIn("if (groups.length === 0)", js_text)
        self.assertIn("loadGroups();", js_text)
        # Tag modal still loads tags on open (soft by default).
        self.assertIn("async function showTagManagementModal()", js_text)
        modal_start = js_text.index("async function showTagManagementModal()")
        modal_end = js_text.index("function hideTagManagementModal()", modal_start)
        self.assertIn("await loadTags(false)", js_text[modal_start:modal_end])

    def test_invalid_token_governance_soft_loads_warm_cache(self):
        """Warm invalid-token candidates re-render without network; mutations force-refresh."""
        js_text = load_frontend_app_js()

        self.assertIn("let invalidTokenGovernanceCandidatesLoaded", js_text)
        self.assertIn("let invalidTokenGovernanceLoadPromise", js_text)
        self.assertIn("let invalidTokenGovernanceLoadForce = false", js_text)
        self.assertIn("function invalidateInvalidTokenGovernanceCache", js_text)
        self.assertIn("function applyInvalidTokenGovernanceCandidates", js_text)
        self.assertIn("async function loadInvalidTokenGovernanceCandidates(options = {})", js_text)
        # Paint-time i18n so language soft re-paint works for governance chrome.
        apply_start = js_text.index("function applyInvalidTokenGovernanceCandidates")
        apply_end = js_text.index("async function loadInvalidTokenGovernanceCandidates", apply_start)
        apply_slice = js_text[apply_start:apply_end]
        self.assertIn("translateAppTextLocal(count + ' 个')", apply_slice)
        self.assertIn("translateAppTextLocal('已停用')", apply_slice)
        self.assertIn("translateAppTextLocal('活跃')", apply_slice)
        self.assertIn("translateAppTextLocal('未知错误')", apply_slice)
        self.assertIn("translateAppTextLocal('原因')", apply_slice)
        self.assertIn("translateAppTextLocal('刷新时间')", apply_slice)
        summary_start = js_text.index("function showInvalidTokenDetectionSummary")
        summary_end = js_text.index("function hideInvalidTokenGovernance", summary_start)
        self.assertIn(
            "translateAppTextLocal(\n                '检测到 ' + count + ' 个疑似失效 Token 的账号，需要治理处理'\n            )",
            js_text[summary_start:summary_end],
        )
        self.assertIn("!force && invalidTokenGovernanceCandidatesLoaded", js_text)
        self.assertIn("if (!force || invalidTokenGovernanceLoadForce)", js_text)
        self.assertIn("invalidTokenGovernanceLoadForce = force", js_text)
        self.assertIn("invalidTokenGovernanceLoadPromise !== request", js_text)
        self.assertIn("fetch('/api/accounts/invalid-token-candidates?limit=200')", js_text)
        # Paint only while refresh modal is open; always warm candidates soft cache.
        load_gov_start = js_text.index("async function loadInvalidTokenGovernanceCandidates(options = {})")
        load_gov_end = js_text.index("async function batchSetInvalidTokenInactive", load_gov_start)
        load_gov_slice = js_text[load_gov_start:load_gov_end]
        self.assertIn("isRefreshModalOpen()", load_gov_slice)
        self.assertIn("// Always warm soft cache; paint only while refresh modal is open.", load_gov_slice)
        self.assertIn("invalidTokenGovernanceCandidates = Array.isArray(data.candidates)", load_gov_slice)

        # Modal open soft-loads; reset must not clear soft cache arrays.
        modal_start = js_text.index("async function showRefreshModal()")
        modal_end = (
            js_text.index("async function autoLoadFailedListIfNeeded", modal_start)
            if "async function autoLoadFailedListIfNeeded" in js_text[modal_start : modal_start + 800]
            else js_text.index("// Soft-load cache for failed refresh logs", modal_start)
        )
        # Prefer explicit option on modal call
        self.assertIn("forceRefresh: false", js_text[modal_start : modal_start + 600])

        reset_start = js_text.index("function resetInvalidTokenGovernanceState")
        reset_end = js_text.index("function invalidateInvalidTokenGovernanceCache", reset_start)
        reset_slice = js_text[reset_start:reset_end]
        self.assertNotIn("invalidTokenGovernanceCandidates = []", reset_slice)
        self.assertNotIn("invalidTokenGovernanceCandidatesLoaded = false", reset_slice)

        inv_start = js_text.index("function invalidateInvalidTokenGovernanceCache")
        inv_end = js_text.index("function showInvalidTokenDetectionSummary", inv_start)
        inv_slice = js_text[inv_start:inv_end]
        self.assertIn("invalidTokenGovernanceCandidates = []", inv_slice)
        self.assertIn("invalidTokenGovernanceCandidatesLoaded = false", inv_slice)
        self.assertIn("invalidTokenGovernanceLoadPromise = null", inv_slice)
        self.assertIn("invalidTokenGovernanceLoadForce = false", inv_slice)

        # Mutation paths force-refresh.
        self.assertIn("forceRefresh: true", js_text)
        batch_del = js_text.index("async function batchDeleteInvalidTokenCandidates")
        batch_del_end = js_text.index("// ==================== 刷新统计与全量刷新", batch_del)
        self.assertIn("invalidateInvalidTokenGovernanceCache()", js_text[batch_del:batch_del_end])

    def test_refresh_modal_history_soft_loads_warm_cache(self):
        """Refresh modal history (limit=1000) soft-loads; mutations clear both page and modal caches."""
        js_text = load_frontend_app_js()

        self.assertIn("async function loadRefreshLogs(forceRefresh = false)", js_text)
        self.assertIn("let refreshModalHistoryCache", js_text)
        self.assertIn("let refreshModalHistoryLoadPromise", js_text)
        self.assertIn("let refreshModalHistoryLoadForce = false", js_text)
        self.assertIn("function renderRefreshModalHistory", js_text)
        # Refresh-modal history / failed-list chrome translates at paint time for language soft re-paint.
        hist_start = js_text.index("function renderRefreshModalHistory(data)")
        hist_end = js_text.index("async function loadRefreshLogs", hist_start)
        hist_slice = js_text[hist_start:hist_end]
        self.assertIn("translateAppTextLocal('暂无全量刷新历史')", hist_slice)
        self.assertIn("translateAppTextLocal('近半年刷新历史（共 ' + logs.length + ' 条）')", hist_slice)
        self.assertIn("translateAppTextLocal(log.status === 'success' ? '成功' : '失败')", hist_slice)
        failed_start = js_text.index("async function loadFailedLogs(forceRefresh = false)")
        failed_end = (
            js_text.index("function renderRefreshModalHistory", failed_start)
            if "function renderRefreshModalHistory" in js_text[failed_start : failed_start + 50]
            else js_text.index("let refreshModalHistoryCache", failed_start)
        )
        # loadFailedLogs is before renderRefreshModalHistory in file; use safer end.
        failed_end = js_text.index("let refreshModalHistoryCache", failed_start)
        failed_slice = js_text[failed_start:failed_end]
        self.assertIn("translateAppTextLocal('暂无失败状态的邮箱')", failed_slice)
        self.assertIn("translateAppTextLocal('重试')", failed_slice)
        self.assertIn("translateAppTextLocal('最后刷新')", failed_slice)
        show_start = js_text.index("function showFailedListFromData")
        show_end = js_text.index("function hideFailedList", show_start)
        show_slice = js_text[show_start:show_end]
        self.assertIn("translateAppTextLocal('未知错误')", show_slice)
        self.assertIn("translateAppTextLocal('重试')", show_slice)
        self.assertIn("!force && refreshModalHistoryCache", js_text)
        self.assertIn("if (!force || refreshModalHistoryLoadForce)", js_text)
        self.assertIn("refreshModalHistoryLoadForce = force", js_text)
        self.assertIn("refreshModalHistoryLoadPromise !== request", js_text)
        self.assertIn("fetch('/api/accounts/refresh-logs?limit=1000')", js_text)
        # Modal surface paint guard: always warm cache; paint only while refresh modal open.
        self.assertIn("function isRefreshModalOpen()", js_text)
        load_hist_start = js_text.index("async function loadRefreshLogs(forceRefresh = false)")
        load_hist_end = js_text.index("function hideRefreshLogs", load_hist_start)
        load_hist_slice = js_text[load_hist_start:load_hist_end]
        self.assertIn("if (isRefreshModalOpen())", load_hist_slice)
        self.assertIn("// Always warm soft cache; paint only while refresh modal is open.", load_hist_slice)

        inv_start = js_text.index("function invalidateRefreshLogPageCache")
        inv_end = js_text.index("function invalidateAuditLogPageCache", inv_start)
        inv_slice = js_text[inv_start:inv_end]
        self.assertIn("refreshLogPageCache = null", inv_slice)
        self.assertIn("refreshLogPageLoadPromise = null", inv_slice)
        self.assertIn("refreshLogPageLoadForce = false", inv_slice)
        self.assertIn("refreshModalHistoryCache = null", inv_slice)
        self.assertIn("refreshModalHistoryLoadPromise = null", inv_slice)

    def test_failed_refresh_list_soft_loads_and_coalesces(self):
        """autoLoadFailedListIfNeeded and loadFailedLogs share one soft failed-list helper."""
        js_text = load_frontend_app_js()

        self.assertIn("async function fetchFailedRefreshLogs(forceRefresh = false)", js_text)
        self.assertIn("let failedRefreshLogsCache", js_text)
        self.assertIn("let failedRefreshLogsLoadPromise", js_text)
        self.assertIn("let failedRefreshLogsLoadForce = false", js_text)
        self.assertIn("function invalidateFailedRefreshLogsCache", js_text)
        self.assertIn("function mapFailedRefreshLogRows", js_text)

        fetch_start = js_text.index("async function fetchFailedRefreshLogs")
        fetch_end = js_text.index("async function autoLoadFailedListIfNeeded", fetch_start)
        fetch_slice = js_text[fetch_start:fetch_end]
        self.assertIn("!force && failedRefreshLogsCache", fetch_slice)
        self.assertIn("if (!force || failedRefreshLogsLoadForce)", fetch_slice)
        self.assertIn("failedRefreshLogsLoadForce = force", fetch_slice)
        self.assertIn("failedRefreshLogsLoadPromise !== request", fetch_slice)
        self.assertIn("fetch('/api/accounts/refresh-logs/failed')", fetch_slice)

        auto_start = js_text.index("async function autoLoadFailedListIfNeeded()")
        auto_end = js_text.index("function hideRefreshModal", auto_start)
        auto_slice = js_text[auto_start:auto_end]
        self.assertIn("fetchFailedRefreshLogs(false)", auto_slice)
        self.assertNotIn("fetch('/api/accounts/refresh-logs/failed')", auto_slice)

        self.assertIn("function isRefreshModalOpen()", js_text)
        load_start = js_text.index("async function loadFailedLogs(forceRefresh = false)")
        load_end = js_text.index("function renderRefreshModalHistory", load_start)
        load_slice = js_text[load_start:load_end]
        self.assertIn("fetchFailedRefreshLogs(forceRefresh)", load_slice)
        self.assertNotIn("fetch('/api/accounts/refresh-logs/failed')", load_slice)
        # Paint failed list chrome only while refresh modal is open.
        self.assertIn("isRefreshModalOpen()", load_slice)
        self.assertIn("if (!isRefreshModalOpen())", load_slice)

        # Only the shared helper owns the raw failed-list GET.
        raw_hits = [line for line in js_text.splitlines() if "fetch('/api/accounts/refresh-logs/failed')" in line]
        self.assertEqual(len(raw_hits), 1, raw_hits)

        # Single-account retry force-refreshes failed list.
        retry_start = js_text.index("async function retrySingleAccount")
        retry_end = js_text.index("function showFailedListFromData", retry_start)
        self.assertIn("loadFailedLogs(true)", js_text[retry_start:retry_end])

        # Live mutation payloads seed the soft cache.
        show_start = js_text.index("function showFailedListFromData")
        show_end = js_text.index("function hideFailedList", show_start)
        self.assertIn("failedRefreshLogsCache =", js_text[show_start:show_end])

    def test_load_refresh_stats_soft_loads_warm_cache(self):
        """Warm refresh-stats cache must repaint without network; mutations force-refresh."""
        js_text = load_frontend_app_js()

        self.assertIn("async function loadRefreshStats(forceRefresh = false)", js_text)
        self.assertIn("let refreshStatsCache", js_text)
        self.assertIn("let refreshStatsLoadPromise", js_text)
        self.assertIn("let refreshStatsLoadForce = false", js_text)
        self.assertIn("function invalidateRefreshStatsCache", js_text)
        self.assertIn("function applyRefreshStats", js_text)
        self.assertIn("!force && refreshStatsCache", js_text)
        self.assertIn("if (!force || refreshStatsLoadForce)", js_text)
        self.assertIn("refreshStatsLoadForce = force", js_text)
        self.assertIn("refreshStatsLoadPromise !== request", js_text)
        # Null-safe paint + modal surface guard.
        apply_start = js_text.index("function applyRefreshStats(stats)")
        apply_end = js_text.index("async function loadRefreshStats", apply_start)
        apply_slice = js_text[apply_start:apply_end]
        self.assertIn("if (!lastEl || !totalEl || !successEl || !failedEl)", apply_slice)
        load_start = js_text.index("async function loadRefreshStats(forceRefresh = false)")
        load_end = js_text.index("async function refreshAllAccounts", load_start)
        load_slice = js_text[load_start:load_end]
        self.assertIn("isRefreshModalOpen()", load_slice)
        self.assertIn("// Always warm soft cache; paint only while refresh modal is open.", load_slice)

        modal_start = js_text.index("async function showRefreshModal()")
        modal_end = js_text.index("async function autoLoadFailedListIfNeeded", modal_start)
        self.assertIn("await loadRefreshStats(false)", js_text[modal_start:modal_end])

        # Mutation / retry paths force-refresh.
        self.assertIn("await loadRefreshStats(true)", js_text)
        self.assertIn("loadRefreshStats(true)", js_text)
        # Selected-batch complete drops stats soft cache.
        batch_start = js_text.index("function handleBatchRefreshSSEEvent")
        batch_end = js_text.index("function updateAccountCardRefreshStatus", batch_start)
        self.assertIn("invalidateRefreshStatsCache", js_text[batch_start:batch_end])

    def test_load_tags_soft_loads_warm_cache(self):
        """Warm allTags must re-render without /api/tags; create/delete force-refresh."""
        js_text = load_frontend_app_js()

        self.assertIn("async function loadTags(forceRefresh = false)", js_text)
        self.assertIn("let tagsLoadForce = false", js_text)
        self.assertIn("let tagsLoadPromise", js_text)
        self.assertIn("!force && Array.isArray(allTags) && allTags.length > 0", js_text)
        self.assertIn("if (!force || tagsLoadForce)", js_text)
        self.assertIn("tagsLoadForce = force", js_text)
        self.assertIn("tagsLoadPromise !== request", js_text)

        soft_start = js_text.index("async function loadTags(forceRefresh = false)")
        soft_end = js_text.index("fetch('/api/tags')", soft_start)
        soft_slice = js_text[soft_start:soft_end]
        self.assertIn("renderTagList()", soft_slice)
        self.assertIn("updateTagFilter()", soft_slice)
        self.assertIn("paintBatchTagSelectFromWarmTags()", soft_slice)
        # Force supersedes soft in-flight.
        self.assertIn("// Abandon soft in-flight bookkeeping; identity check blocks stale apply.", soft_slice)

        # Network success also re-paints batch-tag select (when that modal is open).
        self.assertIn("function paintBatchTagSelectFromWarmTags()", js_text)
        success_slice = js_text[soft_end : js_text.index("async function createTag()", soft_end)]
        self.assertIn("paintBatchTagSelectFromWarmTags()", success_slice)
        # Surface paint guards for the three loadTags consumers.
        self.assertIn("function isTagManagementModalOpen()", js_text)
        self.assertIn("function isBatchTagModalOpen()", js_text)
        paint_batch_start = js_text.index("function paintBatchTagSelectFromWarmTags()")
        paint_batch_end = js_text.index("async function loadTags", paint_batch_start)
        paint_batch_slice = js_text[paint_batch_start:paint_batch_end]
        self.assertIn("if (!isBatchTagModalOpen()) return;", paint_batch_slice)
        update_filter_start = js_text.index("function updateTagFilter()")
        update_filter_end = js_text.index("function isTagManagementModalOpen()", update_filter_start)
        update_filter_slice = js_text[update_filter_start:update_filter_end]
        self.assertIn("currentPage !== 'mailbox'", update_filter_slice)
        render_start = js_text.index("function renderTagList()")
        render_end = js_text.index("async function createTag()", render_start)
        render_slice = js_text[render_start:render_end]
        self.assertIn("if (!isTagManagementModalOpen())", render_slice)
        self.assertIn("if (!listEl)", render_slice)

        # Mutations force-refresh.
        create_start = js_text.index("async function createTag()")
        create_end = js_text.index("async function deleteTag", create_start)
        self.assertIn("await loadTags(true)", js_text[create_start:create_end])
        delete_start = js_text.index("async function deleteTag")
        delete_end = js_text.index("// ==================== 批量操作", delete_start)
        self.assertIn("await loadTags(true)", js_text[delete_start:delete_end])

        # Batch select reuses warm allTags / soft loadTags (no raw GET).
        select_start = js_text.index("async function loadTagsForSelect()")
        select_end = js_text.index("async function confirmBatchTag()", select_start)
        select_slice = js_text[select_start:select_end]
        self.assertIn("await loadTags(false)", select_slice)
        self.assertIn("paintBatchTagSelectFromWarmTags()", select_slice)
        self.assertNotIn("fetch('/api/tags')", select_slice)
        # Loading/error chrome only while batch-tag modal is open.
        self.assertIn("isBatchTagModalOpen()", select_slice)
        # Warm path paints then returns before cold spinner assignment.
        warm_if = select_slice.index("if (Array.isArray(allTags) && allTags.length > 0)")
        warm_paint_idx = select_slice.index("paintBatchTagSelectFromWarmTags()", warm_if)
        spinner_idx = select_slice.index("translateAppTextLocal('加载中...')", warm_paint_idx)
        self.assertLess(warm_paint_idx, spinner_idx)
        self.assertIn("return;", select_slice[warm_paint_idx:spinner_idx])

        # Modal open is soft.
        modal_start = js_text.index("async function showTagManagementModal()")
        modal_end = js_text.index("function hideTagManagementModal()", modal_start)
        self.assertIn("await loadTags(false)", js_text[modal_start:modal_end])

        # Error toast only while a tag consumer surface is still active
        # (tag management / batch-tag modal / mailbox tag filter).
        self.assertIn("function isActiveTagLoadSurface()", js_text)
        active_start = js_text.index("function isActiveTagLoadSurface()")
        active_end = js_text.index("async function loadTags(forceRefresh = false)", active_start)
        active_slice = js_text[active_start:active_end]
        self.assertIn("isTagManagementModalOpen()", active_slice)
        self.assertIn("isBatchTagModalOpen()", active_slice)
        self.assertIn("currentPage === 'mailbox'", active_slice)

        load_start = js_text.index("async function loadTags(forceRefresh = false)")
        load_end = js_text.index("async function createTag()", load_start)
        load_slice = js_text[load_start:load_end]
        self.assertIn("isActiveTagLoadSurface()", load_slice)
        toast_idx = load_slice.index("translateAppTextLocal('加载标签失败')")
        toast_guard = load_slice[max(0, toast_idx - 200) : toast_idx]
        self.assertIn("isActiveTagLoadSurface()", toast_guard)

    def test_load_accounts_by_group_coalesces_inflight(self):
        """Concurrent loadAccountsByGroup for the same queryKey must share one network promise."""
        groups_js = load_feature_package_js("static/js/features/groups")
        accounts_js = load_feature_package_js("static/js/features/accounts")
        main_js = load_frontend_app_js()
        temp_js = load_feature_package_js("static/js/features/temp_emails")

        self.assertIn("const accountsByGroupLoadPromises = Object.create(null)", groups_js)
        self.assertIn("const accountsByGroupLoadForce = Object.create(null)", groups_js)
        self.assertIn("function invalidateAccountsCache(groupId)", groups_js)
        self.assertIn("window.invalidateAccountsCache = invalidateAccountsCache", groups_js)
        self.assertIn("delete accountListMetaCache[groupId]", groups_js)
        # Mutations must clear rows + pagination meta together (no bare delete accountsCache).
        self.assertNotIn("delete accountsCache[", accounts_js)
        self.assertNotIn("delete accountsCache[", main_js)
        self.assertNotIn("delete accountsCache[", temp_js)
        self.assertIn("invalidateAccountsCache(currentGroupId)", accounts_js)
        self.assertIn("invalidateAccountsCache(groupId)", groups_js)
        self.assertIn("invalidateAccountsCache('temp')", temp_js)
        self.assertIn(
            "async function loadAccountsByGroup(groupId, forceRefresh = false, page = currentAccountPage)", groups_js
        )
        load_start = groups_js.index(
            "async function loadAccountsByGroup(groupId, forceRefresh = false, page = currentAccountPage)"
        )
        load_end = (
            groups_js.index("const accountListMetaCache", load_start)
            if "const accountListMetaCache" in groups_js[load_start : load_start + 50]
            else groups_js.index("// 排序相关变量", load_start)
        )
        # Prefer end at next major section after function - use sortAccounts or accountListMetaCache near top
        # Function is before accountListMetaCache in file? Actually accountListMetaCache is after loadAccountsByGroup.
        # Use a safer end marker.
        if "function getSelectedTagFilterIds" in groups_js[load_start:]:
            load_end = groups_js.index("function getSelectedTagFilterIds", load_start)
        load_slice = groups_js[load_start:load_end]
        self.assertIn("accountsByGroupLoadPromises[queryKey]", load_slice)
        self.assertIn("accountsByGroupLoadPromises[queryKey] = request", load_slice)
        self.assertIn("fetch(`/api/accounts?${queryKey}`)", load_slice)
        # Soft joins any; force joins only force and supersedes soft.
        self.assertIn("if (!force || accountsByGroupLoadForce[queryKey])", load_slice)
        self.assertIn("accountsByGroupLoadForce[queryKey] = force", load_slice)
        self.assertIn("accountsByGroupLoadPromises[queryKey] !== request", load_slice)
        # Warm soft path still short-circuits before promise map.
        self.assertIn(
            "!force && Array.isArray(accountsCache[groupId]) && cachedMeta && cachedMeta.queryKey === queryKey", load_slice
        )
        soft_idx = load_slice.index("!force && Array.isArray(accountsCache[groupId])")
        promise_idx = load_slice.index("accountsByGroupLoadPromises[queryKey]")
        self.assertLess(soft_idx, promise_idx)
        # Current-view paint guard: always warm cache; paint only while group+query still active.
        self.assertIn("const isCurrentAccountListView = () => (", load_slice)
        self.assertIn("Number(currentGroupId) === Number(targetGroupId)", load_slice)
        self.assertIn("buildAccountListQueryKey(currentGroupId, currentAccountPage) === queryKey", load_slice)
        self.assertIn("if (isCurrentAccountListView())", load_slice)
        self.assertIn("const paintLoadingChrome = !force && isCurrentAccountListView()", load_slice)
        self.assertIn("syncCurrentPage: isCurrentAccountListView()", load_slice)
        # Stale responses must not rewrite live page cursor.
        self.assertIn("function updateAccountListCache(groupId, accounts, pagination, queryKey, options = {})", groups_js)
        self.assertIn("const syncCurrentPage = options.syncCurrentPage !== false", groups_js)
        self.assertIn("if (syncCurrentPage)", groups_js)

    def test_batch_move_groups_soft_loads_warm_groups(self):
        """Batch-move group select must reuse warm groups / soft loadGroups, not raw GET."""
        main_js = load_frontend_app_js()
        self.assertIn("function paintBatchMoveGroupSelectFromWarmGroups()", main_js)
        self.assertIn("function softPaintBatchMoveGroupSelectIfOpen()", main_js)
        self.assertIn("function isBatchMoveGroupModalOpen()", main_js)
        paint_start = main_js.index("function paintBatchMoveGroupSelectFromWarmGroups()")
        paint_end = main_js.index("function softPaintBatchMoveGroupSelectIfOpen()", paint_start)
        paint_slice = main_js[paint_start:paint_end]
        self.assertIn("if (!isBatchMoveGroupModalOpen()) return;", paint_slice)
        fn_start = main_js.index("async function loadGroupsForBatchMove()")
        fn_end = main_js.index("async function confirmBatchMoveGroup()", fn_start)
        fn_slice = main_js[fn_start:fn_end]
        self.assertIn("await loadGroups(false)", fn_slice)
        self.assertIn("Array.isArray(groups) && groups.length > 0", fn_slice)
        self.assertNotIn("fetch('/api/groups')", fn_slice)
        self.assertIn("isBatchMoveGroupModalOpen()", fn_slice)
        # Warm path paints then returns before cold spinner assignment.
        self.assertIn("paintBatchMoveGroupSelectFromWarmGroups()", fn_slice)
        warm_if = fn_slice.index("if (Array.isArray(groups) && groups.length > 0)")
        warm_paint_idx = fn_slice.index("paintBatchMoveGroupSelectFromWarmGroups()", warm_if)
        spinner_idx = fn_slice.index("translateAppTextLocal('加载中...')", warm_paint_idx)
        self.assertLess(warm_paint_idx, spinner_idx)
        self.assertIn("return;", fn_slice[warm_paint_idx:spinner_idx])
        # Language change soft-paints open batch-move modal.
        soft_lang = next(
            (
                main_js[idx : idx + 5000]
                for idx in [
                    i for i in range(len(main_js)) if main_js.startswith("window.addEventListener('ui-language-changed'", i)
                ]
                if "paintBatchTagSelectFromWarmTags" in main_js[idx : idx + 5000]
            ),
            "",
        )
        if not soft_lang:
            marker = "window.addEventListener('ui-language-changed'"
            lang_idxs = []
            start = 0
            while True:
                idx = main_js.find(marker, start)
                if idx < 0:
                    break
                lang_idxs.append(idx)
                start = idx + 1
            soft_lang = next(
                (
                    main_js[idx : idx + 5000]
                    for idx in lang_idxs
                    if "paintBatchTagSelectFromWarmTags" in main_js[idx : idx + 5000]
                ),
                "",
            )
        self.assertIn("softPaintBatchMoveGroupSelectIfOpen()", soft_lang)

    def test_export_group_list_soft_loads_via_load_groups(self):
        """Export modal group list must soft-load cold groups via loadGroups(false)."""
        accounts_js = load_feature_package_js("static/js/features/accounts")
        self.assertIn("function paintExportGroupList", accounts_js)
        self.assertIn("function softPaintExportGroupListIfOpen", accounts_js)
        self.assertIn("function isExportModalOpen()", accounts_js)
        paint_start = accounts_js.index("function paintExportGroupList(source, selectedIds = null)")
        paint_end = accounts_js.index("function softPaintExportGroupListIfOpen()", paint_start)
        paint_slice = accounts_js[paint_start:paint_end]
        self.assertIn("if (!isExportModalOpen()) return;", paint_slice)
        fn_start = accounts_js.index("async function loadExportGroupList()")
        fn_end = accounts_js.index("function toggleSelectAllGroups", fn_start)
        fn_slice = accounts_js[fn_start:fn_end]
        self.assertIn("await loadGroups(false)", fn_slice)
        self.assertIn("Array.isArray(groups) && groups.length > 0", fn_slice)
        self.assertNotIn("fetch('/api/groups')", fn_slice)
        self.assertIn("isExportModalOpen()", fn_slice)
        # Warm groups paint without spinner flash; spinner only on cold path.
        self.assertIn("paintExportGroupList(groups, new Set())", fn_slice)
        warm_paint_idx = fn_slice.index("paintExportGroupList(groups, new Set())")
        spinner_idx = fn_slice.index("loading-overlay")
        self.assertLess(warm_paint_idx, spinner_idx)
        # Language change soft-paints open export modal without network.
        self.assertIn("window.addEventListener('ui-language-changed'", accounts_js)
        lang = accounts_js[accounts_js.index("window.addEventListener('ui-language-changed'") :]
        self.assertIn("softPaintExportGroupListIfOpen()", lang)
        self.assertNotIn("loadGroups(true)", lang)

    def test_load_groups_soft_loads_warm_cache(self):
        """Warm groups array must re-render without /api/groups; mutations force-refresh."""
        groups_js = load_feature_package_js("static/js/features/groups")
        main_js = load_frontend_app_js()
        accounts_js = load_feature_package_js("static/js/features/accounts")

        self.assertIn("async function loadGroups(forceRefresh = false)", groups_js)
        self.assertIn("let groupsLoadPromise", groups_js)
        self.assertIn("let groupsLoadForce = false", groups_js)
        self.assertIn("function applyLoadedGroups", groups_js)
        self.assertIn("!force && Array.isArray(groups) && groups.length > 0", groups_js)
        self.assertIn("if (!force || groupsLoadForce)", groups_js)
        self.assertIn("groupsLoadForce = force", groups_js)
        self.assertIn("fetch('/api/groups')", groups_js)
        # Soft path re-renders without network / without refreshing accounts.
        soft_start = groups_js.index("async function loadGroups(forceRefresh = false)")
        soft_end = groups_js.index("fetch('/api/groups')", soft_start)
        soft_slice = groups_js[soft_start:soft_end]
        self.assertIn("applyLoadedGroups(groups, { refreshAccounts: false })", soft_slice)
        self.assertIn("return groupsLoadPromise", soft_slice)
        # Force supersedes soft in-flight.
        self.assertIn("// Abandon soft in-flight bookkeeping; identity check blocks stale apply.", soft_slice)
        # Network path applies with account refresh.
        self.assertIn("applyLoadedGroups(data.groups, { refreshAccounts: true })", groups_js)
        self.assertIn("groupsLoadPromise = request", groups_js)
        self.assertIn("groupsLoadPromise !== request", groups_js)
        # Sidebar loading/error chrome only on mailbox page (pool-admin/export must not flash #groupList).
        self.assertIn("function isCurrentMailboxGroupsSurface()", groups_js)
        self.assertIn("currentPage === 'mailbox'", groups_js)
        self.assertIn("const paintSidebarChrome = isCurrentMailboxGroupsSurface()", soft_slice)
        self.assertIn("if (paintSidebarChrome && container)", soft_slice)
        load_full = groups_js[soft_start : groups_js.index("function renderGroupList", soft_start)]
        self.assertIn("if (isCurrentMailboxGroupsSurface() && container)", load_full)
        # applyLoadedGroups / renderGroupList paint mailbox sidebar only on mailbox surface.
        apply_start = groups_js.index("function applyLoadedGroups")
        apply_end = groups_js.index("async function loadGroups", apply_start)
        apply_slice = groups_js[apply_start:apply_end]
        self.assertIn("if (isCurrentMailboxGroupsSurface())", apply_slice)
        self.assertIn("renderGroupList(groups)", apply_slice)
        render_start = groups_js.index("function renderGroupList")
        render_end = groups_js.index("async function selectGroup", render_start)
        render_slice = groups_js[render_start:render_end]
        self.assertIn("if (!isCurrentMailboxGroupsSurface())", render_slice)
        # Import/edit group selects only repaint while their modals are open.
        update_start = groups_js.index("function updateGroupSelects()")
        update_end = groups_js.index("function showAddGroupModal", update_start)
        update_slice = groups_js[update_start:update_end]
        self.assertIn("modalId: 'addAccountModal'", update_slice)
        self.assertIn("modalId: 'editAccountModal'", update_slice)
        self.assertIn("!modal.classList.contains('show')", update_slice)
        # Account cache re-paint helper also stays on standard mailbox surface.
        rerender_start = groups_js.index("function rerenderAccountCaches()")
        rerender_end = groups_js.index("function syncAccountSummaryToAccountCache", rerender_start)
        rerender_slice = groups_js[rerender_start:rerender_end]
        self.assertIn("currentPage !== 'mailbox'", rerender_slice)
        self.assertIn("isTempEmailGroup", rerender_slice)
        # renderAccountList itself defends shared #accountList against off-surface paints.
        render_acc_start = groups_js.index("function renderAccountList(accounts)")
        render_acc_end = groups_js.index("function goToAccountPage", render_acc_start)
        render_acc_slice = groups_js[render_acc_start:render_acc_end]
        self.assertIn("currentPage !== 'mailbox'", render_acc_slice)
        self.assertIn("isTempEmailGroup", render_acc_slice)
        self.assertIn("mailboxViewMode === 'unified'", render_acc_slice)

        # Mutations force-refresh.
        self.assertIn("loadGroups(true)", groups_js)
        self.assertIn("loadGroups(true)", accounts_js)
        self.assertIn("loadGroups(true)", main_js)
        # Navigate empty path stays soft default.
        nav_start = main_js.index("function navigate(page)")
        nav_end = main_js.index("function updateTopbar(page)", nav_start)
        self.assertIn("loadGroups();", main_js[nav_start:nav_end])
        self.assertNotIn("loadGroups(true)", main_js[nav_start:nav_end])

    def test_edit_group_soft_loads_warm_groups_cache(self):
        """editGroup paints from warm groups array; cold path coalesces GET /api/groups/<id>."""
        groups_js = load_feature_package_js("static/js/features/groups")

        self.assertIn("const groupDetailLoadPromises = Object.create(null)", groups_js)
        self.assertIn("const groupDetailLoadForce = Object.create(null)", groups_js)
        self.assertIn("function applyEditGroupForm(group)", groups_js)
        self.assertIn("async function editGroup(groupId, forceRefresh = false)", groups_js)

        load_start = groups_js.index("async function editGroup(groupId, forceRefresh = false)")
        load_end = groups_js.index("async function saveGroup", load_start)
        load_slice = groups_js[load_start:load_end]
        self.assertIn("!force && Array.isArray(groups) && groups.length > 0", load_slice)
        self.assertIn("groups.find(g => Number(g && g.id) === numericId)", load_slice)
        self.assertIn("applyEditGroupForm(warmGroup)", load_slice)
        self.assertIn("if (!force || groupDetailLoadForce[numericId])", load_slice)
        self.assertIn("groupDetailLoadForce[numericId] = force", load_slice)
        self.assertIn("groupDetailLoadPromises[numericId] !== request", load_slice)
        self.assertIn("groupDetailLoadPromises[numericId]", load_slice)
        self.assertIn("fetch(`/api/groups/${numericId}`)", load_slice)

    def test_edit_group_cancels_paint_after_modal_hide(self):
        """Late group detail responses must not re-open add/edit modal after hide or switch to add."""
        groups_js = load_feature_package_js("static/js/features/groups")

        self.assertIn("let editGroupPaintTargetId = null", groups_js)
        self.assertIn("function shouldPaintEditGroupForm(groupId)", groups_js)

        should_start = groups_js.index("function shouldPaintEditGroupForm(groupId)")
        should_end = groups_js.index("function applyEditGroupForm(group)", should_start)
        should_slice = groups_js[should_start:should_end]
        self.assertIn("editGroupPaintTargetId === numericId", should_slice)

        hide_start = groups_js.index("function hideAddGroupModal()")
        hide_end = groups_js.index("function applyEditGroupForm(group)", hide_start)
        hide_slice = groups_js[hide_start:hide_end]
        self.assertIn("editGroupPaintTargetId = null", hide_slice)

        add_start = groups_js.index("function showAddGroupModal()")
        add_end = groups_js.index("function hideAddGroupModal()", add_start)
        add_slice = groups_js[add_start:add_end]
        self.assertIn("editGroupPaintTargetId = null", add_slice)

        load_start = groups_js.index("async function editGroup(groupId, forceRefresh = false)")
        load_end = groups_js.index("async function saveGroup", load_start)
        load_slice = groups_js[load_start:load_end]
        self.assertIn("editGroupPaintTargetId = numericId", load_slice)
        self.assertIn("shouldPaintEditGroupForm(numericId)", load_slice)
        self.assertIn("shouldPaintEditGroupForm(warmGroup.id)", load_slice)
        # Cold success always warms list row when present; apply only while paint target matches.
        self.assertIn("if (shouldPaintEditGroupForm(numericId))", load_slice)
        self.assertIn("applyEditGroupForm(data.group)", load_slice)

    def test_version_check_soft_loads_session_cache(self):
        """checkVersionUpdate soft-loads warm session payload and coalesces concurrent checks."""
        main_js = load_frontend_app_js()

        self.assertIn("let versionCheckCache = null", main_js)
        self.assertIn("let versionCheckLoadPromise = null", main_js)
        self.assertIn("let versionCheckLoadForce = false", main_js)
        self.assertIn("function applyVersionCheckPayload(data)", main_js)
        self.assertIn("async function checkVersionUpdate(forceRefresh = false)", main_js)

        load_start = main_js.index("async function checkVersionUpdate(forceRefresh = false)")
        load_end = main_js.index("function dismissVersionBanner", load_start)
        load_slice = main_js[load_start:load_end]
        self.assertIn("!force && versionCheckCache", load_slice)
        self.assertIn("if (!force || versionCheckLoadForce)", load_slice)
        self.assertIn("versionCheckLoadForce = force", load_slice)
        self.assertIn("versionCheckLoadPromise !== request", load_slice)
        self.assertIn("fetch('/api/system/version-check')", load_slice)
        # Boot still soft-invokes after delay (no force).
        self.assertIn("setTimeout(checkVersionUpdate, 5000)", main_js)
        # apply helper translates chrome at paint time (language soft re-paint safe).
        apply_start = main_js.index("function applyVersionCheckPayload(data)")
        apply_end = main_js.index("async function checkVersionUpdate", apply_start)
        apply_slice = main_js[apply_start:apply_end]
        self.assertIn("translateAppTextLocal('发现新版本')", apply_slice)
        self.assertIn("translateAppTextLocal('查看更新日志')", apply_slice)
        self.assertIn("translateAppTextLocal('当前')", apply_slice)
        # Language change soft-paints warm version banner without network.
        marker = "window.addEventListener('ui-language-changed'"
        lang_idxs = []
        start = 0
        while True:
            idx = main_js.find(marker, start)
            if idx < 0:
                break
            lang_idxs.append(idx)
            start = idx + 1
        soft_lang = next(
            (main_js[idx : idx + 5000] for idx in lang_idxs if "paintBatchTagSelectFromWarmTags" in main_js[idx : idx + 5000]),
            "",
        )
        self.assertIn("if (versionCheckCache)", soft_lang)
        self.assertIn("applyVersionCheckPayload(versionCheckCache)", soft_lang)

    def test_show_edit_account_modal_soft_loads_detail_cache(self):
        """Re-opening edit modal soft-loads prior detail GET; never paints from list cache."""
        accounts_js = load_feature_package_js("static/js/features/accounts")

        self.assertIn("const accountDetailCache = new Map()", accounts_js)
        self.assertIn("const accountDetailLoadPromises = Object.create(null)", accounts_js)
        self.assertIn("const accountDetailLoadForce = Object.create(null)", accounts_js)
        self.assertIn("function invalidateAccountDetailCache(accountId)", accounts_js)
        self.assertIn("function applyEditAccountForm(acc)", accounts_js)
        self.assertIn("async function showEditAccountModal(accountId, forceRefresh = false)", accounts_js)
        # Explicit safety note: list rows truncate client_id.
        self.assertIn("never paint from accountsCache list rows", accounts_js)

        load_start = accounts_js.index("async function showEditAccountModal(accountId, forceRefresh = false)")
        load_end = accounts_js.index("function hideEditAccountModal", load_start)
        load_slice = accounts_js[load_start:load_end]
        self.assertIn("!force && accountDetailCache.has(key)", load_slice)
        self.assertIn("if (!force || accountDetailLoadForce[key])", load_slice)
        self.assertIn("accountDetailLoadForce[key] = force", load_slice)
        self.assertIn("accountDetailLoadPromises[key] !== request", load_slice)
        self.assertIn("accountDetailLoadPromises[key]", load_slice)
        self.assertIn(
            "fetch(`/api/accounts/${encodeURIComponent(key)}`)",
            load_slice,
        )
        # Mutations invalidate detail cache.
        self.assertIn("invalidateAccountDetailCache(accountId)", accounts_js)
        # Cross-feature batch paths (main.js) use window helpers.
        self.assertIn("window.invalidateAccountDetailCache = invalidateAccountDetailCache", accounts_js)
        self.assertIn("window.invalidateAccountDetailCacheMany = invalidateAccountDetailCacheMany", accounts_js)
        main_js = load_frontend_app_js()
        self.assertIn("window.invalidateAccountDetailCacheMany(accountIds)", main_js)
        # batch delete + invalid-token delete/status + batch move + batch tag
        self.assertGreaterEqual(main_js.count("window.invalidateAccountDetailCacheMany(accountIds)"), 5)
        confirm_move = main_js.index("async function confirmBatchMoveGroup()")
        confirm_tag = main_js.index("async function confirmBatchTag()")
        self.assertIn(
            "window.invalidateAccountDetailCacheMany(accountIds)",
            main_js[confirm_move : confirm_move + 1800],
        )
        self.assertIn(
            "window.invalidateAccountDetailCacheMany(accountIds)",
            main_js[confirm_tag : confirm_tag + 1800],
        )

    def test_show_edit_account_modal_cancels_paint_after_modal_hide(self):
        """Late account detail responses must not re-open edit modal after hide."""
        accounts_js = load_feature_package_js("static/js/features/accounts")

        self.assertIn("let editAccountPaintTargetId = null", accounts_js)
        self.assertIn("function shouldPaintEditAccountForm(accountId)", accounts_js)

        should_start = accounts_js.index("function shouldPaintEditAccountForm(accountId)")
        should_end = accounts_js.index("function applyEditAccountForm(acc)", should_start)
        should_slice = accounts_js[should_start:should_end]
        self.assertIn("editAccountPaintTargetId === key", should_slice)

        hide_start = accounts_js.index("function hideEditAccountModal()")
        hide_end = accounts_js.index("function focusEditRemarkField", hide_start)
        hide_slice = accounts_js[hide_start:hide_end]
        self.assertIn("editAccountPaintTargetId = null", hide_slice)

        load_start = accounts_js.index("async function showEditAccountModal(accountId, forceRefresh = false)")
        load_end = accounts_js.index("function hideEditAccountModal", load_start)
        load_slice = accounts_js[load_start:load_end]
        self.assertIn("editAccountPaintTargetId = key", load_slice)
        self.assertIn("shouldPaintEditAccountForm(key)", load_slice)
        # Always warm detail cache; apply only while paint target still matches.
        self.assertIn("accountDetailCache.set(key, data.account)", load_slice)
        self.assertIn("if (shouldPaintEditAccountForm(key))", load_slice)
        self.assertIn("applyEditAccountForm(data.account)", load_slice)
        self.assertIn("applyEditAccountForm(accountDetailCache.get(key))", load_slice)

    def test_boot_defers_notification_permission_prompt(self):
        """Critical boot must not synchronously request browser Notification permission."""
        js_text = load_frontend_app_js()
        boot_start = js_text.index("document.addEventListener('DOMContentLoaded'")
        boot_end = js_text.index("setTimeout(checkVersionUpdate", boot_start)
        boot_slice = js_text[boot_start:boot_end]

        self.assertNotIn("Notification.requestPermission()", boot_slice)
        self.assertIn("scheduleBrowserNotificationPermissionPrompt()", boot_slice)
        self.assertIn("function scheduleBrowserNotificationPermissionPrompt", js_text)
        helper_start = js_text.index("function scheduleBrowserNotificationPermissionPrompt")
        helper_end = js_text.index("document.addEventListener('DOMContentLoaded'", helper_start)
        helper_slice = js_text[helper_start:helper_end]
        self.assertIn("addEventListener('pointerdown'", helper_slice)
        self.assertIn("addEventListener('keydown'", helper_slice)
        self.assertIn("Notification.requestPermission()", helper_slice)
        self.assertIn("30000", helper_slice)

    def test_load_deployment_info_soft_loads_warm_cache(self):
        """Settings re-entry soft-loads warm deployment info without a second network GET."""
        js_text = load_frontend_app_js()

        self.assertIn("let lastDeploymentInfo = null", js_text)
        self.assertIn("let deploymentInfoLoadPromise = null", js_text)
        self.assertIn("let deploymentInfoLoadForce = false", js_text)
        self.assertIn("function applyDeploymentInfo", js_text)
        self.assertIn("async function loadDeploymentInfo({ silent = true, forceRefresh = false } = {})", js_text)

        load_start = js_text.index("async function loadDeploymentInfo({ silent = true, forceRefresh = false } = {})")
        load_end = js_text.index("function toggleRefreshStrategy", load_start)
        load_slice = js_text[load_start:load_end]
        self.assertIn("!force && lastDeploymentInfo", load_slice)
        self.assertIn("if (!force || deploymentInfoLoadForce)", load_slice)
        self.assertIn("deploymentInfoLoadForce = force", load_slice)
        self.assertIn("deploymentInfoLoadPromise !== request", load_slice)
        self.assertIn("fetch('/api/system/deployment-info', { cache: 'no-store' })", load_slice)
        self.assertIn("applyDeploymentInfo(data.deployment, { paint: paintSettingsChrome() })", load_slice)
        # Settings surface paint guard: always warm cache; paint only while Settings active.
        self.assertIn("const paintSettingsChrome = () => (", load_slice)
        self.assertIn("isSettingsSurfaceActive()", load_slice)
        self.assertIn("// Always warm soft cache; paint only while Settings surface is active.", load_slice)
        apply_start = js_text.index("function applyDeploymentInfo(deployment")
        apply_end = js_text.index("async function loadDeploymentInfo", apply_start)
        apply_slice = js_text[apply_start:apply_end]
        self.assertIn("const paint = options.paint !== false", apply_slice)
        self.assertIn("if (!paint)", apply_slice)
        # Force supersedes soft in-flight.
        self.assertIn("// Abandon soft in-flight bookkeeping; identity check blocks stale apply.", load_slice)

        # Settings load soft-loads deployment info.
        self.assertIn("loadDeploymentInfo({ silent: true, forceRefresh: false })", js_text)
        # Language change still reuses lastDeploymentInfo without network (Settings surface only).
        self.assertIn(
            "lastDeploymentInfo && (typeof isSettingsSurfaceActive === 'function' ? isSettingsSurfaceActive() : true)", js_text
        )
        self.assertIn("renderDeploymentWarnings(lastDeploymentInfo)", js_text)
        # Language change also re-paints other warm soft-load surfaces without network.
        marker = "window.addEventListener('ui-language-changed'"
        lang_idxs = []
        start = 0
        while True:
            idx = js_text.find(marker, start)
            if idx < 0:
                break
            lang_idxs.append(idx)
            start = idx + 1
        soft_lang = next(
            (js_text[idx : idx + 5000] for idx in lang_idxs if "paintBatchTagSelectFromWarmTags" in js_text[idx : idx + 5000]),
            "",
        )
        self.assertIn("paintBatchTagSelectFromWarmTags()", soft_lang)
        # Empty tags still re-paint when tag management modal is open.
        self.assertIn("Array.isArray(allTags)", soft_lang)
        self.assertIn("tagManagementModal", soft_lang)
        self.assertIn("allTags.length > 0 || tagModalOpen", soft_lang)
        self.assertIn("softPaintBatchMoveGroupSelectIfOpen()", soft_lang)
        self.assertIn("batchTagModal.classList.contains('show')", soft_lang)
        self.assertIn("batchActionType === 'add' ? '批量添加标签' : '批量移除标签'", soft_lang)
        # Settings-open secret/multi-key hints + theme toggle soft re-paint.
        settings_lang = next(
            (js_text[idx : idx + 2500] for idx in lang_idxs if "renderDemoWorkspaceStrip" in js_text[idx : idx + 2500]),
            "",
        )
        self.assertIn("softPaintSettingsSecretHintsIfOpen()", settings_lang)
        self.assertIn("applyTheme(theme)", settings_lang)
        self.assertIn("function applyTheme(theme)", js_text)
        self.assertIn("translateAppTextLocal('浅色模式')", js_text)
        self.assertIn("translateAppTextLocal('深色模式')", js_text)
        self.assertIn(".theme-toggle-label", js_text)
        self.assertIn("function softPaintSettingsSecretHintsIfOpen()", js_text)
        self.assertIn(
            "translateAppTextLocal(\n                    '当前已配置 ' + normalized.length + ' 个多 Key。保留已有脱敏 api_key 表示不修改该 Key；清空后保存表示清空全部多 Key。'\n                )",
            js_text,
        )
        self.assertIn("ensurePoolAdminGroupOptions(false)", soft_lang)
        self.assertIn("ensurePoolAdminProviderOptions(false)", soft_lang)
        self.assertIn("loadProviders(false)", soft_lang)
        self.assertIn("applyRefreshStats(refreshStatsCache)", soft_lang)
        self.assertIn("renderRefreshLogPage(refreshLogPageCache)", soft_lang)
        self.assertIn("renderAuditLogPage(auditLogPageCache)", soft_lang)

        # Standard/temp mailbox modules also soft-paint open lists on language change.
        emails_js = load_feature_package_js("static/js/features/emails")
        temp_js = load_feature_package_js("static/js/features/temp_emails")
        groups_js = load_feature_package_js("static/js/features/groups")
        self.assertIn("window.addEventListener('ui-language-changed'", emails_js)
        self.assertIn("renderEmailList(currentEmails", emails_js)
        emails_lang = emails_js[emails_js.index("window.addEventListener('ui-language-changed'") :]
        # Language change soft-paints empty folder chrome + email batch selection count.
        self.assertIn("updateEmailBatchActionBar()", emails_lang)
        self.assertIn("listEl.querySelector('.empty-state')", emails_lang)
        # Cold folder (no warm list cache) keeps "click to fetch" prompt, not inbox-empty.
        self.assertIn("paintEmailListColdFetchPrompt(currentFolder)", emails_lang)
        self.assertIn("function getEmailListColdFetchPrompt", emails_js)
        self.assertIn("function paintEmailListColdFetchPrompt", emails_js)
        self.assertIn("translateAppTextLocal('已选 ' + selectedEmailIds.size + ' 项')", emails_js)
        # switchFolder cold path uses shared paint helper.
        main_js2 = load_frontend_app_js()
        switch_start = main_js2.index("function switchFolder(folder)")
        switch_end = main_js2.index("function selectCustomColor", switch_start)
        switch_slice = main_js2[switch_start:switch_end]
        self.assertIn("paintEmailListColdFetchPrompt(folder)", switch_slice)
        self.assertIn("window.addEventListener('ui-language-changed'", temp_js)
        self.assertIn("renderTempEmailList(accountsCache['temp'])", temp_js)
        temp_lang = temp_js[temp_js.index("window.addEventListener('ui-language-changed'") :]
        # Empty temp inventory / empty message list also soft-paint on language change.
        self.assertIn("Array.isArray(accountsCache['temp'])", temp_lang)
        self.assertIn("Array.isArray(currentEmails)", temp_lang)
        self.assertIn("applyTempEmailMessagesPayload(currentAccount", temp_lang)
        # Standard group sidebar re-paints warm groups + account list on language change.
        groups_lang = groups_js[groups_js.index("window.addEventListener('ui-language-changed'") :]
        self.assertIn("renderGroupList(groups)", groups_lang)
        self.assertIn("renderAccountList(accountsCache[currentGroupId])", groups_lang)
        self.assertIn("ensurePoolAdminGroupOptions(false)", groups_lang)
        # Account inventory soft-repaint only on standard mailbox page (not temp-emails).
        self.assertIn("currentPage === 'mailbox'", groups_lang)
        self.assertIn("!isTempEmailGroup", groups_lang)
        # Empty group list chrome also re-paints (not only groups.length > 0).
        self.assertIn("groupListEl.querySelector('.empty-state')", groups_lang)
        self.assertIn("Array.isArray(accountsCache[currentGroupId])", groups_lang)
        # Group empty/search chrome translates at paint time for language soft re-paint.
        self.assertIn("translateAppTextLocal('请从左侧选择一个邮箱账号')", groups_js)
        self.assertIn("translateAppTextLocal('搜索中…')", groups_js)
        self.assertIn("translateAppTextLocal('搜索失败，请重试')", groups_js)
        # Verification copy toasts use translateAppTextLocal (not getUiLanguage ternaries).
        self.assertIn("translateAppTextLocal('已复制: ' + data.data.formatted)", groups_js)
        self.assertIn("translateAppTextLocal('已从当前邮件兜底复制: ' + copiedValue)", groups_js)
        self.assertNotIn("getUiLanguage() === 'en'", groups_js)
        # Group action button titles translate at paint time.
        self.assertIn("translateAppTextLocal('编辑')", groups_js)
        self.assertIn("translateAppTextLocal('删除')", groups_js)
        self.assertNotIn('title="编辑"', groups_js)
        self.assertNotIn('title="删除"', groups_js)

        # Import summary / compact counts / temp suffix use translate helpers.
        accounts_js = load_feature_package_js("static/js/features/accounts")
        compact_js = (ROOT / "static" / "js" / "features" / "mailbox_compact.js").read_text(encoding="utf-8")
        temp_js2 = load_feature_package_js("static/js/features/temp_emails")
        self.assertIn(
            "translateAppTextLocal(\n                        '成功 ' + imported + '，失败 ' + failed + '，跳过 ' + skipped\n                    )",
            accounts_js,
        )
        self.assertIn("translateCompactText('已选 ' + count + ' 项')", compact_js)
        self.assertIn("translateCompactText(safeCount + ' 个账号')", compact_js)
        self.assertIn("translateAppTextLocal('临时')", temp_js2)

        # Pool-admin table + filters soft-paint on language change without network.
        pool_js = (ROOT / "static" / "js" / "features" / "pool_admin.js").read_text(encoding="utf-8")
        pool_lang = pool_js[pool_js.index("window.addEventListener('ui-language-changed'") :]
        self.assertIn("renderPoolAdmin(__poolAdminState.cache)", pool_lang)
        self.assertIn("ensurePoolAdminGroupOptions(false)", pool_lang)
        self.assertIn("ensurePoolAdminProviderOptions(false)", pool_lang)
        self.assertNotIn("loadPoolAdmin(true)", pool_lang)

        # Token-tool soft-paints warm scope chips / account select on language change.
        token_js = (ROOT / "static" / "js" / "features" / "token_tool.js").read_text(encoding="utf-8")
        token_lang = token_js[token_js.index("window.addEventListener('ui-language-changed'") :]
        self.assertIn("renderScopeChips(scopeValue)", token_lang)
        self.assertIn("applyTokenToolAccountOptions(tokenToolAccountsCache)", token_lang)
        self.assertNotIn("loadOAuthConfig(true)", token_lang)
        self.assertNotIn("loadAccountOptions(true)", token_lang)
        # Account select paint only while save dialog is open.
        self.assertIn("function isTokenToolSaveDialogOpen()", token_js)
        apply_acc_start = token_js.index("function applyTokenToolAccountOptions(accounts)")
        apply_acc_end = token_js.index("function invalidateTokenToolAccountsCache", apply_acc_start)
        apply_acc_slice = token_js[apply_acc_start:apply_acc_end]
        self.assertIn("if (!isTokenToolSaveDialogOpen())", apply_acc_slice)
        load_acc_start = token_js.index("async function loadAccountOptions(forceRefresh = false)")
        load_acc_end = token_js.index("async function openSaveDialog", load_acc_start)
        load_acc_slice = token_js[load_acc_start:load_acc_end]
        self.assertIn("isTokenToolSaveDialogOpen()", load_acc_slice)
        self.assertIn("// Always warm soft cache; paint only while save dialog is open.", load_acc_slice)
        # Live translate helper (not a frozen const capture at module load).
        self.assertIn("function t(text)", token_js)
        self.assertIn("window.translateAppText(text)", token_js)

        # Plugin manager soft-paints warm list on language change without network.
        plugins_js = (ROOT / "static" / "js" / "features" / "plugins.js").read_text(encoding="utf-8")
        plugins_lang = plugins_js[plugins_js.index("window.addEventListener('ui-language-changed'") :]
        self.assertIn("softPaintOnLanguageChange()", plugins_lang)
        self.assertIn("function plT(text)", plugins_js)
        self.assertIn("plT('刷新')", plugins_js)
        self.assertNotIn("loadPlugins({ force: true })", plugins_lang)

    def test_navigate_soft_loads_temp_emails_and_pool_admin(self):
        """Re-entering temp-emails / pool-admin must reuse warm page caches."""
        js_text = load_frontend_app_js()
        nav_start = js_text.index("function navigate(page)")
        nav_end = js_text.index("function updateTopbar(page)", nav_start)
        nav_slice = js_text[nav_start:nav_end]

        self.assertIn("loadTempEmails(false)", nav_slice)
        self.assertIn("loadPoolAdmin(false)", nav_slice)
        self.assertNotIn("loadTempEmails(true)", nav_slice)
        self.assertNotIn("loadPoolAdmin(true)", nav_slice)

        # Mutation / explicit refresh paths still force-reload.
        temp_js = load_feature_package_js("static/js/features/temp_emails")
        self.assertIn("loadTempEmails(true)", temp_js)
        pool_js = (ROOT / "static" / "js" / "features" / "pool_admin.js").read_text(encoding="utf-8")
        self.assertIn("loadPoolAdmin(true)", pool_js)
        # Soft cache is keyed by query signature; soft joins any, force joins only force.
        self.assertIn("function getPoolAdminQueryKey", pool_js)
        self.assertIn("cacheQueryKey === queryKey", pool_js)
        self.assertIn("loadPromiseQueryKey === queryKey", pool_js)
        self.assertIn("loadForce: false", pool_js)
        self.assertIn("if (!force || __poolAdminState.loadForce)", pool_js)
        self.assertIn("__poolAdminState.loadForce = force", pool_js)
        self.assertIn("__poolAdminState.loadPromise !== request", pool_js)
        self.assertIn("__poolAdminState.loadPromise = request", pool_js)
        # Group filter options reuse warm groups / soft loadGroups (no raw GET).
        self.assertIn("async function ensurePoolAdminGroupOptions", pool_js)
        self.assertIn("function paintPoolAdminGroupOptions", pool_js)
        self.assertIn("await loadGroups(false)", pool_js)
        self.assertIn("await loadGroups(true)", pool_js)
        # Soft re-entry re-paints warm groups so create/delete elsewhere is visible without force GET.
        self.assertIn("if (!force && (hasWarmGroups || __poolAdminState.groupOptionsLoaded))", pool_js)
        self.assertNotIn("fetch('/api/groups')", pool_js)
        # applyLoadedGroups keeps pool-admin filter in sync without force network.
        groups_js = load_feature_package_js("static/js/features/groups")
        apply_start = groups_js.index("function applyLoadedGroups")
        apply_end = groups_js.index("async function loadGroups", apply_start)
        apply_slice = groups_js[apply_start:apply_end]
        self.assertIn("ensurePoolAdminGroupOptions(false)", apply_slice)
        self.assertIn("updateGroupSelects()", apply_slice)

    def test_load_temp_emails_coalesces_inflight(self):
        """Concurrent loadTempEmails network loads must share one promise."""
        temp_js = load_feature_package_js("static/js/features/temp_emails")

        self.assertIn("let tempEmailsLoadPromise = null", temp_js)
        self.assertIn("let tempEmailsLoadForce = false", temp_js)
        self.assertIn("async function loadTempEmails(forceRefresh = false)", temp_js)
        load_start = temp_js.index("async function loadTempEmails(forceRefresh = false)")
        load_end = temp_js.index("function renderTempEmailList", load_start)
        load_slice = temp_js[load_start:load_end]
        self.assertIn("!force && accountsCache['temp']", load_slice)
        self.assertIn("if (tempEmailsLoadPromise)", load_slice)
        self.assertIn("if (!force || tempEmailsLoadForce)", load_slice)
        self.assertIn("tempEmailsLoadForce = force", load_slice)
        self.assertIn("tempEmailsLoadPromise !== request", load_slice)
        self.assertIn("tempEmailsLoadPromise = request", load_slice)
        self.assertIn("fetch('/api/temp-emails')", load_slice)
        # Warm soft path short-circuits before promise coalesce.
        warm_idx = load_slice.index("!force && accountsCache['temp']")
        promise_idx = load_slice.index("if (tempEmailsLoadPromise)")
        self.assertLess(warm_idx, promise_idx)
        # Page-level paint guard: always warm cache; paint only on temp-emails page.
        self.assertIn("function isCurrentTempEmailsPage()", temp_js)
        self.assertIn("currentPage === 'temp-emails'", temp_js)
        self.assertIn("if (isCurrentTempEmailsPage())", load_slice)
        self.assertIn("const paintLoadingChrome = isCurrentTempEmailsPage()", load_slice)
        self.assertIn("// Always warm inventory soft cache; paint only on temp-emails page.", load_slice)
        # Dedicated container only — never dual-paint shared mailbox #accountList.
        self.assertIn("getElementById('tempEmailContainer')", load_slice)
        self.assertNotIn("getElementById('accountList')", load_slice)
        render_start = temp_js.index("function renderTempEmailList(emails)")
        render_end = temp_js.index("function onTempEmailProviderChange", render_start)
        render_slice = temp_js[render_start:render_end]
        self.assertIn("if (!isCurrentTempEmailsPage())", render_slice)
        self.assertIn("return;", render_slice)
        self.assertIn("getElementById('tempEmailContainer')", render_slice)
        self.assertNotIn("getElementById('accountList')", render_slice)
        self.assertIn("pageContainer.innerHTML = cardHTML", render_slice)
        # Catalog label refresh also skips non-mailbox / temp surfaces.
        main_js_tags = load_frontend_app_js()
        refresh_start = main_js_tags.index("function refreshAccountProviderTagsFromCatalog()")
        refresh_end = main_js_tags.index("function getMailboxProviderCatalogLabel", refresh_start)
        refresh_slice = main_js_tags[refresh_start:refresh_end]
        self.assertIn("currentPage !== 'mailbox'", refresh_slice)
        self.assertIn("isTempEmailGroup", refresh_slice)

    def test_load_temp_email_options_soft_loads_and_force_supersedes(self):
        """Temp domain options soft-load per provider; force supersedes soft in-flight."""
        temp_js = load_feature_package_js("static/js/features/temp_emails")
        main_js = load_frontend_app_js()
        plugins_js = (ROOT / "static" / "js" / "features" / "plugins.js").read_text(encoding="utf-8")

        self.assertIn("const tempEmailOptionsLoadPromises = Object.create(null)", temp_js)
        self.assertIn("const tempEmailOptionsLoadForce = Object.create(null)", temp_js)
        self.assertIn("function invalidateTempEmailOptionsCache()", temp_js)
        self.assertIn("window.invalidateTempEmailOptionsCache = invalidateTempEmailOptionsCache", temp_js)
        self.assertIn("async function loadTempEmailOptions(forceRefresh = false, providerName = null)", temp_js)

        load_start = temp_js.index("async function loadTempEmailOptions(forceRefresh = false, providerName = null)")
        load_end = temp_js.index("function renderTempEmailOptions", load_start)
        load_slice = temp_js[load_start:load_end]
        self.assertIn("!force && tempEmailOptionsCache.has(cacheKey)", load_slice)
        self.assertIn("if (tempEmailOptionsLoadPromises[cacheKey])", load_slice)
        self.assertIn("if (!force || tempEmailOptionsLoadForce[cacheKey])", load_slice)
        self.assertIn("tempEmailOptionsLoadForce[cacheKey] = force", load_slice)
        self.assertIn("tempEmailOptionsLoadPromises[cacheKey] !== request", load_slice)
        self.assertIn("'/api/temp-emails/options'", load_slice)
        # Page/provider paint guard for domain options chrome.
        self.assertIn("function shouldPaintTempEmailOptions", temp_js)
        self.assertIn("shouldPaintTempEmailOptions(resolvedProviderName)", load_slice)
        self.assertIn("// Always warm options soft cache; paint only while still current.", load_slice)

        # Settings / plugin mutations drop soft options cache so domains re-fetch.
        save_start = main_js.index("async function saveSettings()")
        save_end = main_js.index("async function testTelegramPush", save_start)
        self.assertIn("invalidateTempEmailOptionsCache()", main_js[save_start:save_end])
        auto_start = main_js.index("async function autoSaveSettings(tabName)")
        auto_end = main_js.index("function onTempMailProviderChange", auto_start)
        self.assertIn("invalidateTempEmailOptionsCache()", main_js[auto_start:auto_end])
        self.assertIn("invalidateTempEmailOptionsCache()", plugins_js)
        # Force list reload also clears options before soft-syncing provider selection.
        list_start = temp_js.index("async function loadTempEmails(forceRefresh = false)")
        list_end = temp_js.index("function renderTempEmailList", list_start)
        list_slice = temp_js[list_start:list_end]
        self.assertIn("invalidateTempEmailOptionsCache()", list_slice)
        self.assertLess(
            list_slice.index("invalidateTempEmailOptionsCache()"), list_slice.index("syncTempEmailProviderSelection")
        )

    def test_unified_mailbox_messages_soft_loads_warm_preview(self):
        """Re-opening the same unified mailbox preview soft-loads warm messages."""
        mailboxes_js = load_mailboxes_js()

        self.assertIn("messagesSignature: ''", mailboxes_js)
        self.assertIn("messagesLoadPromise: null", mailboxes_js)
        self.assertIn("messagesLoadSignature: ''", mailboxes_js)
        self.assertIn("messagesLoadForce: false", mailboxes_js)
        self.assertIn("async function loadUnifiedMailboxMessages(kind, sourceId, options = {})", mailboxes_js)

        load_start = mailboxes_js.index("async function loadUnifiedMailboxMessages(kind, sourceId, options = {})")
        load_end = mailboxes_js.index("function openUnifiedMessagePreview", load_start)
        load_slice = mailboxes_js[load_start:load_end]
        self.assertIn("const forceRefresh = Boolean(options.force)", load_slice)
        self.assertIn("preview.messagesSignature === messagesSignature", load_slice)
        self.assertIn("messagesLoadPromise", load_slice)
        self.assertIn("messagesLoadSignature === messagesSignature", load_slice)
        self.assertIn("if (!forceRefresh || preview.messagesLoadForce)", load_slice)
        self.assertIn("preview.messagesLoadForce = forceRefresh", load_slice)
        self.assertIn("preview.messagesLoadPromise !== request", load_slice)
        # Surface paint guard: warm soft state; paint only on unified mailbox surface.
        self.assertIn("isCurrentUnifiedMailboxSurface()", load_slice)
        self.assertIn("// Always warm preview soft state; paint only on unified surface.", load_slice)

        # Soft open helper; refresh buttons still pass force: true.
        open_start = mailboxes_js.index("function openUnifiedMessagePreview(kind, sourceId)")
        open_end = mailboxes_js.index("function openUnifiedMessagePreviewFromCard", open_start)
        self.assertIn("{ force: false }", mailboxes_js[open_start:open_end])
        self.assertIn("{ force: true }", mailboxes_js)

    def test_unified_mailbox_message_detail_soft_loads_warm_preview(self):
        """Re-selecting the same unified message soft-loads warm detail."""
        mailboxes_js = load_mailboxes_js()

        self.assertIn("detailSignature: ''", mailboxes_js)
        self.assertIn("detailLoadPromise: null", mailboxes_js)
        self.assertIn("detailLoadSignature: ''", mailboxes_js)
        self.assertIn("detailLoadForce: false", mailboxes_js)
        self.assertIn(
            "async function loadUnifiedMailboxMessageDetail(kind, sourceId, messageId, options = {})",
            mailboxes_js,
        )

        load_start = mailboxes_js.index(
            "async function loadUnifiedMailboxMessageDetail(kind, sourceId, messageId, options = {})"
        )
        load_end = mailboxes_js.index("async function loadUnifiedMailboxVerification", load_start)
        load_slice = mailboxes_js[load_start:load_end]
        self.assertIn("const forceRefresh = Boolean(options && options.force)", load_slice)
        self.assertIn("preview.detailSignature === detailSignature", load_slice)
        self.assertIn("detailLoadPromise", load_slice)
        self.assertIn("detailLoadSignature === detailSignature", load_slice)
        self.assertIn("if (!forceRefresh || preview.detailLoadForce)", load_slice)
        self.assertIn("preview.detailLoadForce = forceRefresh", load_slice)
        self.assertIn("preview.detailLoadPromise !== request", load_slice)
        self.assertIn("getUnifiedMessageDetailEndpoint", load_slice)
        self.assertIn("isCurrentUnifiedMailboxSurface()", load_slice)
        self.assertIn("// Always warm detail soft state; paint only on unified surface.", load_slice)

        # Row click stays soft (no force); retry and list-refresh auto-select force.
        self.assertIn(
            "onclick=\"loadUnifiedMailboxMessageDetail('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, '${escapeJs(id)}')\"",
            mailboxes_js,
        )
        self.assertIn(
            "loadUnifiedMailboxMessageDetail('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, '${escapeJs(preview.selectedMessageId)}', { force: true })",
            mailboxes_js,
        )
        self.assertIn(
            "loadUnifiedMailboxMessageDetail(normalizedKind, numericSourceId, preview.selectedMessageId, { force: true })",
            mailboxes_js,
        )

    def test_unified_mailbox_verification_soft_loads_and_coalesces(self):
        """Re-running unified verification soft-loads warm result; button force-refetches."""
        mailboxes_js = load_mailboxes_js()

        self.assertIn("verificationSignature: ''", mailboxes_js)
        self.assertIn("verificationLoadPromise: null", mailboxes_js)
        self.assertIn("verificationLoadSignature: ''", mailboxes_js)
        self.assertIn("verificationLoadForce: false", mailboxes_js)
        self.assertIn(
            "async function loadUnifiedMailboxVerification(kind, sourceId, options = {})",
            mailboxes_js,
        )

        load_start = mailboxes_js.index("async function loadUnifiedMailboxVerification(kind, sourceId, options = {})")
        load_end = mailboxes_js.index("async function copyUnifiedPreviewValue", load_start)
        load_slice = mailboxes_js[load_start:load_end]
        self.assertIn("const forceRefresh = Boolean(options && options.force)", load_slice)
        self.assertIn("preview.verificationSignature === verificationSignature", load_slice)
        self.assertIn("verificationLoadPromise", load_slice)
        self.assertIn("verificationLoadSignature === verificationSignature", load_slice)
        self.assertIn("if (!forceRefresh || preview.verificationLoadForce)", load_slice)
        self.assertIn("preview.verificationLoadForce = forceRefresh", load_slice)
        self.assertIn("preview.verificationLoadPromise !== request", load_slice)
        self.assertIn("'verification'", load_slice)
        self.assertIn("isCurrentUnifiedMailboxSurface()", load_slice)
        self.assertIn("// Always warm verification soft state; paint only on unified surface.", load_slice)

        # Explicit extract button forces network; list refresh clears verification signature.
        self.assertIn(
            "loadUnifiedMailboxVerification('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, { force: true })",
            mailboxes_js,
        )
        self.assertIn("preview.verificationSignature = ''", mailboxes_js)

    def test_load_temp_email_messages_soft_loads_and_coalesces(self):
        """Re-selecting a temp mailbox soft-loads warm messages; refresh forces network."""
        temp_js = load_feature_package_js("static/js/features/temp_emails")
        emails_js = load_feature_package_js("static/js/features/emails")

        self.assertIn("const tempEmailMessagesCache = new Map()", temp_js)
        self.assertIn("const tempEmailMessagesLoadPromises = Object.create(null)", temp_js)
        self.assertIn("const tempEmailMessagesLoadForce = Object.create(null)", temp_js)
        self.assertIn("async function loadTempEmailMessages(email, forceRefresh = false)", temp_js)
        self.assertIn("function applyTempEmailMessagesPayload", temp_js)

        load_start = temp_js.index("async function loadTempEmailMessages(email, forceRefresh = false)")
        load_end = temp_js.index("function renderTempEmailMessageList", load_start)
        load_slice = temp_js[load_start:load_end]
        self.assertIn("!force && tempEmailMessagesCache.has(targetEmail)", load_slice)
        self.assertIn("tempEmailMessagesLoadPromises[targetEmail]", load_slice)
        self.assertIn("if (!force || tempEmailMessagesLoadForce[targetEmail])", load_slice)
        self.assertIn("tempEmailMessagesLoadForce[targetEmail] = force", load_slice)
        self.assertIn("tempEmailMessagesLoadPromises[targetEmail] !== request", load_slice)
        self.assertIn("fetch(`/api/temp-emails/${encodeURIComponent(targetEmail)}/messages`)", load_slice)
        # Always warm cache; paint only while still viewing this mailbox.
        self.assertIn("Always warm cache for this mailbox", load_slice)
        self.assertIn("currentAccount !== targetEmail", load_slice)
        self.assertIn("const paintLoadingChrome = currentAccount === targetEmail", load_slice)

        # select soft; explicit refresh forces.
        self.assertIn("loadTempEmailMessages(email, false)", temp_js)
        self.assertIn("loadTempEmailMessages(currentAccount, true)", emails_js)
        self.assertIn("function refreshTempEmailMessages", temp_js)
        self.assertIn("loadTempEmailMessages(currentAccount, true)", temp_js)
        # Force-refresh is bound on the button when a temp mailbox is selected.
        self.assertIn("tempRefreshBtn.onclick", temp_js)

        # clear/delete drop message cache + loadForce bookkeeping.
        self.assertIn("function clearTempEmailMessagesCacheForMailbox(mailboxEmail)", temp_js)
        self.assertIn("function seedEmptyTempEmailMessagesCache(mailboxEmail)", temp_js)
        self.assertIn("tempEmailMessagesCache.set(key, { emails: [], count: 0 })", temp_js)
        self.assertIn("delete tempEmailMessagesLoadForce[key]", temp_js)
        self.assertIn("seedEmptyTempEmailMessagesCache(email)", temp_js)
        self.assertIn("clearTempEmailMessagesCacheForMailbox(email)", temp_js)
        self.assertIn("window.clearTempEmailMessagesCacheForMailbox = clearTempEmailMessagesCacheForMailbox", temp_js)
        # Delete also drops unified directory soft cache early.
        delete_start = temp_js.index("async function deleteTempEmail(email)")
        delete_end = temp_js.index("function applyTempEmailMessagesPayload", delete_start)
        delete_slice = temp_js[delete_start:delete_end]
        self.assertIn("invalidateUnifiedMailboxDirectoryCache()", delete_slice)
        # Generate/delete chrome translates at paint time.
        self.assertIn("translateAppTextLocal('临时邮箱已删除')", delete_slice)
        self.assertIn("translateAppTextLocal('请从左侧选择一个邮箱账号')", delete_slice)
        self.assertIn("translateAppTextLocal('选择一个临时邮箱查看邮件')", delete_slice)
        self.assertIn("translateAppTextLocal('正在生成临时邮箱…')", temp_js)
        self.assertIn("translateAppTextLocal('临时邮箱已生成: ' + data.email)", temp_js)
        self.assertIn("translateAppTextLocal('生成临时邮箱失败')", temp_js)
        # Message/detail network empty states translate at paint time.
        self.assertIn("translateAppTextLocal('网络错误，请重试')", temp_js)
        self.assertIn("translateAppTextLocal('加载失败')", temp_js)
        # Temp account card action titles translate at paint time.
        self.assertIn("translateAppTextLocal('点击复制')", temp_js)
        self.assertIn("translateAppTextLocal('提取验证码')", temp_js)
        self.assertIn("translateAppTextLocal('复制')", temp_js)
        self.assertIn("translateAppTextLocal('清空')", temp_js)
        self.assertIn("translateAppTextLocal('删除')", temp_js)
        self.assertNotIn('title="点击复制"', temp_js)
        self.assertNotIn('title="复制"', temp_js)
        # copyTempEmailCurrent must not hard-compare only Chinese placeholder (EN UI).
        copy_start = temp_js.index("function copyTempEmailCurrent()")
        copy_end = temp_js.index("async function loadTempEmails", copy_start)
        copy_slice = temp_js[copy_start:copy_end]
        self.assertIn("translateAppTextLocal(placeholderZh)", copy_slice)
        self.assertIn("text !== placeholderZh && text !== placeholderEn", copy_slice)

    def test_get_temp_email_detail_soft_loads_and_coalesces(self):
        """Re-selecting the same temp message soft-loads warm detail."""
        temp_js = load_feature_package_js("static/js/features/temp_emails")
        emails_js = load_feature_package_js("static/js/features/emails")

        self.assertIn("const tempEmailDetailCache = new Map()", temp_js)
        self.assertIn("const tempEmailDetailLoadPromises = Object.create(null)", temp_js)
        self.assertIn("const tempEmailDetailLoadForce = Object.create(null)", temp_js)
        self.assertIn("function getTempEmailDetailCacheKey(mailboxEmail, messageId)", temp_js)
        self.assertIn("function clearTempEmailDetailCacheForMailbox(mailboxEmail)", temp_js)
        self.assertIn("async function getTempEmailDetail(messageId, index, forceRefresh = false)", temp_js)

        load_start = temp_js.index("async function getTempEmailDetail(messageId, index, forceRefresh = false)")
        load_end = temp_js.index("window.addEventListener('ui-language-changed'", load_start)
        load_slice = temp_js[load_start:load_end]
        self.assertIn("!force && tempEmailDetailCache.has(cacheKey)", load_slice)
        self.assertIn("if (!force || tempEmailDetailLoadForce[cacheKey])", load_slice)
        self.assertIn("tempEmailDetailLoadForce[cacheKey] = force", load_slice)
        self.assertIn("tempEmailDetailLoadPromises[cacheKey] !== request", load_slice)
        self.assertIn("tempEmailDetailLoadPromises[cacheKey]", load_slice)
        self.assertIn(
            "fetch(`/api/temp-emails/${encodeURIComponent(mailboxEmail)}/messages/${encodeURIComponent(normalizedMessageId)}`)",
            load_slice,
        )
        # Always warm cache; paint only while still on the same temp mailbox.
        self.assertIn("const isCurrentTempMailbox = () =>", load_slice)
        self.assertIn("Always warm cache for this key", load_slice)
        self.assertIn("!isCurrentTempMailbox()", load_slice)
        self.assertIn("const paintLoadingChrome = isCurrentTempMailbox()", load_slice)

        # Row click stays soft (default forceRefresh=false).
        self.assertIn("onclick=\"getTempEmailDetail('${escapeJs(email.id || email.message_id || '')}', ${index})\"", temp_js)
        # Force list refresh / clear helpers drop mailbox detail cache.
        self.assertIn("clearTempEmailDetailCacheForMailbox(targetEmail)", temp_js)
        self.assertIn("clearTempEmailDetailCacheForMailbox(key)", temp_js)
        # Mailbox delete/clear route through message-cache helpers that clear detail too.
        self.assertIn(
            "clearTempEmailDetailCacheForMailbox(key)",
            temp_js[
                temp_js.index("function clearTempEmailMessagesCacheForMailbox") : temp_js.index(
                    "function invalidateTempEmailDetailCacheEntry"
                )
            ],
        )
        # Single-message delete drops warm detail entry via window helper.
        self.assertIn("window.invalidateTempEmailDetailCacheEntry = invalidateTempEmailDetailCacheEntry", temp_js)
        self.assertIn("window.invalidateTempEmailDetailCacheEntry(currentAccount, deletedId)", emails_js)

    def test_select_email_detail_soft_loads_and_coalesces(self):
        """Re-selecting the same Outlook/IMAP message soft-loads warm detail."""
        emails_js = load_feature_package_js("static/js/features/emails")

        self.assertIn("const emailDetailCache = new Map()", emails_js)
        self.assertIn("const emailDetailLoadPromises = Object.create(null)", emails_js)
        self.assertIn("const emailDetailLoadForce = Object.create(null)", emails_js)
        self.assertIn("function getEmailDetailCacheKey(mailboxEmail, folder, method, messageId)", emails_js)
        self.assertIn("function clearEmailDetailCacheForMailbox(mailboxEmail, folder = null)", emails_js)
        self.assertIn("async function selectEmail(messageId, index, forceRefresh = false)", emails_js)

        load_start = emails_js.index("async function selectEmail(messageId, index, forceRefresh = false)")
        load_end = emails_js.index("function normalizeEmailInlineResourceKey", load_start)
        load_slice = emails_js[load_start:load_end]
        self.assertIn("if (!force || emailDetailLoadForce[cacheKey])", load_slice)
        self.assertIn("emailDetailLoadForce[cacheKey] = force", load_slice)
        self.assertIn("emailDetailLoadPromises[cacheKey] !== request", load_slice)
        self.assertIn("emailDetailLoadPromises[cacheKey]", load_slice)
        # Capture mailbox/folder/method at request start; paint only while still current.
        self.assertIn("const isCurrentMailboxFolderMethod = () => (", load_slice)
        self.assertIn("currentAccount === mailboxEmail", load_slice)
        self.assertIn("if (!isCurrentMailboxFolderMethod())", load_slice)
        self.assertIn("Always warm cache for this key", load_slice)
        self.assertIn(
            "fetch(`/api/email/${encodeURIComponent(mailboxEmail)}/${encodeURIComponent(normalizedMessageId)}?method=${encodeURIComponent(method)}&folder=${encodeURIComponent(folder)}`)",
            load_slice,
        )

        # Force list refresh clears mailbox+folder detail cache (via list clearer or direct).
        self.assertIn("clearEmailDetailCacheForMailbox(targetEmail, targetFolder)", emails_js)
        self.assertIn("clearEmailListCacheForMailbox(currentAccount, currentFolder)", emails_js)
        self.assertIn("clearEmailDetailCacheForMailbox(email, folderNorm)", emails_js)
        # Delete path drops warm detail entries.
        self.assertIn("invalidateEmailDetailCacheEntry(currentAccount, currentFolder, currentMethod, deletedId)", emails_js)
        # Delete path must keep soft list cache aligned (not only currentEmails UI state).
        delete_start = emails_js.index("async function deleteEmails(ids)")
        delete_end = emails_js.index("async function deleteCurrentTempEmailMessage", delete_start)
        delete_slice = emails_js[delete_start:delete_end]
        self.assertIn("emailListCache[listCacheKey] = {", delete_slice)
        self.assertIn("emails: currentEmails,", delete_slice)
        # Delete/copy chrome translates at paint time.
        self.assertIn("translateAppTextLocal('正在删除...')", delete_slice)
        self.assertIn("translateAppTextLocal('成功删除 ' + result.success_count + ' 封邮件')", delete_slice)
        self.assertIn("translateAppTextLocal('邮件已删除')", delete_slice)
        self.assertIn("translateAppTextLocal('邮箱地址已复制')", emails_js)
        self.assertIn("translateAppTextLocal('复制失败，请手动复制')", emails_js)
        # Detail render/network empty states translate at paint time.
        self.assertIn("translateAppTextLocal('邮件渲染失败')", emails_js)
        self.assertIn("translateAppTextLocal('网络错误，请重试')", emails_js)
        temp_delete_start = emails_js.index("async function deleteCurrentTempEmailMessage()")
        temp_delete_end = (
            emails_js.index("// 选择邮件", temp_delete_start)
            if "// 选择邮件" in emails_js[temp_delete_start : temp_delete_start + 2000]
            else emails_js.index("async function selectEmail", temp_delete_start)
        )
        temp_delete_slice = emails_js[temp_delete_start:temp_delete_end]
        self.assertIn("tempEmailMessagesCache.set(currentAccount", temp_delete_slice)

    def test_account_delete_clears_email_list_soft_cache(self):
        """Deleting an account must drop emailListCache/detail for that mailbox."""
        emails_js = load_feature_package_js("static/js/features/emails")
        accounts_js = load_feature_package_js("static/js/features/accounts")
        main_js = load_frontend_app_js()

        self.assertIn("function clearEmailListCacheForMailbox(mailboxEmail, folder = null)", emails_js)
        self.assertIn("function clearEmailListCacheForMailboxes(mailboxEmails)", emails_js)
        self.assertIn("window.clearEmailListCacheForMailbox = clearEmailListCacheForMailbox", emails_js)
        self.assertIn("window.clearEmailListCacheForMailboxes = clearEmailListCacheForMailboxes", emails_js)
        self.assertIn("clearEmailDetailCacheForMailbox(email, folderNorm)", emails_js)
        # Explicit refresh uses the shared list+detail clearer.
        self.assertIn("clearEmailListCacheForMailbox(currentAccount, currentFolder)", emails_js)

        del_current = accounts_js[
            accounts_js.index("async function deleteCurrentAccount()") : accounts_js.index(
                "async function toggleAccountStatus"
            )
        ]
        self.assertIn("clearEmailListCacheForMailbox(email)", del_current)
        self.assertIn("invalidateUnifiedMailboxDirectoryCache()", del_current)
        # Delete clears open mailbox empty states with translated chrome.
        self.assertIn("translateAppTextLocal('请从左侧选择一个邮箱账号')", del_current)
        self.assertIn("translateAppTextLocal('选择一封邮件查看详情')", del_current)

        del_quick = accounts_js[
            accounts_js.index("async function deleteAccount(accountId, email)") : accounts_js.index(
                "async function batchNotificationToggle"
            )
        ]
        self.assertIn("clearEmailListCacheForMailbox(email)", del_quick)
        self.assertIn("translateAppTextLocal('请从左侧选择一个邮箱账号')", del_quick)
        self.assertIn("translateAppTextLocal('选择一封邮件查看详情')", del_quick)
        # selectAccount empty detail also translates.
        select_start = accounts_js.index("function selectAccount(email)")
        select_end = (
            accounts_js.index("async function showEditAccountModal", select_start)
            if "async function showEditAccountModal" in accounts_js[select_start : select_start + 5000]
            else accounts_js.index("function invalidateAccountDetailCache", select_start)
        )
        # safer: just assert globally for select path
        self.assertIn("translateAppTextLocal('选择一封邮件查看详情')", accounts_js)
        self.assertNotIn("<p>选择一封邮件查看详情</p>", accounts_js)

        update_slice = accounts_js[
            accounts_js.index("async function updateAccount()") : accounts_js.index("async function deleteCurrentAccount()")
        ]
        self.assertIn("shouldClearMailSoftCache", update_slice)
        self.assertIn("clearEmailListCacheForMailbox(previousEmail)", update_slice)
        self.assertIn("clearEmailListCacheForMailbox(nextEmail)", update_slice)
        self.assertIn("emailInput.dataset.originalValue = acc.email || ''", accounts_js)

        batch = main_js[
            main_js.index("async function batchDeleteAccounts()") : main_js.index(
                "function resolveSelectedAccountsForBatchFetch"
            )
        ]
        self.assertIn("clearEmailListCacheForMailboxes", batch)
        self.assertIn("invalidateUnifiedMailboxDirectoryCache()", batch)

        # Import (especially overwrite) must drop soft mail caches for parsed addresses.
        self.assertIn("function extractImportCandidateEmails(accountString)", accounts_js)
        add_start = accounts_js.index("async function addAccount()")
        add_end = (
            accounts_js.index("// 显示编辑", add_start)
            if "// 显示编辑" in accounts_js[add_start : add_start + 8000]
            else accounts_js.index("async function showEditAccountModal", add_start)
        )
        add_slice = accounts_js[add_start:add_end]
        self.assertIn("clearEmailListCacheForMailboxes(extractImportCandidateEmails(input))", add_slice)
        self.assertIn("invalidateUnifiedMailboxDirectoryCache()", add_slice)

    def test_load_emails_coalesces_inflight_by_cache_key(self):
        """Concurrent loadEmails for the same email+folder must share one promise."""
        emails_js = load_feature_package_js("static/js/features/emails")

        self.assertIn("const emailsLoadPromises = Object.create(null)", emails_js)
        self.assertIn("const emailsLoadForce = Object.create(null)", emails_js)
        self.assertIn("async function loadEmails(email, forceRefresh = false)", emails_js)
        load_start = emails_js.index("async function loadEmails(email, forceRefresh = false)")
        load_end = emails_js.index("function renderEmailList", load_start)
        load_slice = emails_js[load_start:load_end]
        self.assertIn("!force && emailListCache[cacheKey]", load_slice)
        self.assertIn("emailsLoadPromises[cacheKey]", load_slice)
        self.assertIn("if (!force || emailsLoadForce[cacheKey])", load_slice)
        self.assertIn("emailsLoadForce[cacheKey] = force", load_slice)
        self.assertIn("emailsLoadPromises[cacheKey] !== request", load_slice)
        self.assertIn("emailsLoadPromises[cacheKey] = request", load_slice)
        self.assertIn("/api/emails/${encodeURIComponent(targetEmail)}", load_slice)
        # Capture mailbox+folder at request start; paint only while still current.
        self.assertIn("const isCurrentEmailListView = () => (", load_slice)
        self.assertIn("currentAccount === targetEmail", load_slice)
        self.assertIn("if (!isCurrentEmailListView())", load_slice)
        self.assertIn("const requestMethod = String(currentMethod", load_slice)
        self.assertIn("folder=${encodeURIComponent(targetFolder)}", load_slice)
        # Warm soft path short-circuits before promise map.
        warm_idx = load_slice.index("!force && emailListCache[cacheKey]")
        promise_idx = load_slice.index("emailsLoadPromises[cacheKey]")
        self.assertLess(warm_idx, promise_idx)
        # Duplicate account_summary sync removed in the coalesced path.
        self.assertEqual(load_slice.count("syncAccountSummaryToAccountCache(targetEmail, data.account_summary)"), 1)

    def test_load_more_emails_upserts_list_cache(self):
        """loadMoreEmails must always upsert emailListCache so soft re-select keeps pages."""
        main_js = load_frontend_app_js()

        load_start = main_js.index("async function loadMoreEmails()")
        load_end = main_js.index("function switchFolder(folder)", load_start)
        load_slice = main_js[load_start:load_end]
        self.assertIn("// Soft-load: always upsert list cache for the requested mailbox+folder", load_slice)
        self.assertIn("emailListCache[cacheKey] = {", load_slice)
        self.assertIn("emails: mergedEmails,", load_slice)
        self.assertIn("has_more: nextHasMore,", load_slice)
        self.assertIn("skip: requestSkip,", load_slice)
        self.assertIn("method: nextMethod", load_slice)
        # Capture identity at request start; paint only while still on that mailbox+folder.
        self.assertIn("const targetEmail = String(currentAccount || '').trim()", load_slice)
        self.assertIn("const targetFolder = String(currentFolder || 'inbox').trim().toLowerCase()", load_slice)
        self.assertIn("const isCurrentEmailListView = () => (", load_slice)
        self.assertIn("if (isCurrentEmailListView())", load_slice)
        self.assertIn("const paintLoadingChrome = isCurrentEmailListView()", load_slice)
        self.assertIn("baselineEmails.concat(data.emails || [])", load_slice)
        self.assertIn(
            "`/api/emails/${encodeURIComponent(targetEmail)}?method=${encodeURIComponent(targetMethod || 'graph')}&folder=${encodeURIComponent(targetFolder)}&skip=${requestSkip}&top=20`",
            load_slice,
        )
        # Success path must always assign cache (not only mutate when key already exists).
        success_assign = load_slice.index("emailListCache[cacheKey] = {")
        # Exhausted branch may patch an existing key; that is OK and must stay after success upsert.
        if "if (emailListCache[cacheKey]) {" in load_slice:
            self.assertGreater(load_slice.index("if (emailListCache[cacheKey]) {"), success_assign)

    def test_refresh_compact_account_seeds_email_list_cache(self):
        """Compact pull seeds emailListCache so standard-view soft-load reuses pages."""
        compact_js = (ROOT / "static" / "js" / "features" / "mailbox_compact.js").read_text(encoding="utf-8")
        main_js = load_frontend_app_js()

        self.assertIn("async function refreshCompactAccount(accountId, buttonElement)", compact_js)
        self.assertIn("function cacheBatchFetchedFolder(email, folder, data)", main_js)

        load_start = compact_js.index("async function refreshCompactAccount(accountId, buttonElement)")
        load_end = compact_js.index("function renderCompactAccountList", load_start)
        load_slice = compact_js[load_start:load_end]
        self.assertIn("folder: 'inbox'", load_slice)
        self.assertIn("folder: 'junkemail'", load_slice)
        self.assertIn("cacheBatchFetchedFolder(account.email, folder, payload)", load_slice)
        self.assertIn("window.clearEmailDetailCacheForMailbox(account.email, folder)", load_slice)
        # Soft-load bridge comment remains for future agents.
        self.assertIn("Soft-load bridge: seed emailListCache", load_slice)

    def test_poll_engine_seeds_email_list_cache(self):
        """Poll baseline + tick seed emailListCache for standard-view soft-load."""
        poll_js = (ROOT / "static" / "js" / "features" / "poll-engine.js").read_text(encoding="utf-8")

        self.assertIn("var POLL_LIST_FOLDERS = ['inbox', 'sentitems']", poll_js)
        self.assertIn("function seedPollEmailListCache(email, folder, payload)", poll_js)
        self.assertIn("cacheBatchFetchedFolder(email, folder, payload)", poll_js)
        self.assertIn("window.clearEmailDetailCacheForMailbox(email, folder)", poll_js)
        self.assertIn("seedPollEmailListCache(email, POLL_LIST_FOLDERS[index] || 'inbox', data)", poll_js)
        self.assertIn("seedPollEmailListCache(email, POLL_LIST_FOLDERS[index] || 'inbox', payload)", poll_js)
        # Soft-load bridge comment remains for future agents.
        self.assertIn("Soft-load bridge: seed standard-view emailListCache", poll_js)

    def test_navigate_soft_loads_settings_page(self):
        """Re-entering Settings must reuse warm GET /api/settings payload when unchanged."""
        js_text = load_frontend_app_js()
        nav_start = js_text.index("function navigate(page)")
        nav_end = js_text.index("function updateTopbar(page)", nav_start)
        nav_slice = js_text[nav_start:nav_end]
        self.assertIn("loadSettings()", nav_slice)
        self.assertNotIn("loadSettings(true)", nav_slice)

        self.assertIn("async function loadSettings(forceRefresh = false)", js_text)
        self.assertIn("function invalidateSettingsPageCache", js_text)
        self.assertIn("async function fetchSettingsPagePayload", js_text)
        self.assertIn("let settingsPageLoadPromise", js_text)
        self.assertIn("let settingsPageLoadForce = false", js_text)
        self.assertIn("let settingsPageCacheGeneration", js_text)

        fetch_start = js_text.index("async function fetchSettingsPagePayload")
        fetch_end = js_text.index("async function refreshTempMailSettingsSnapshotFromServer()", fetch_start)
        fetch_slice = js_text[fetch_start:fetch_end]
        self.assertIn("!force && settingsPageCache", fetch_slice)
        self.assertIn("if (!force || settingsPageLoadForce)", fetch_slice)
        self.assertIn("settingsPageLoadForce = force", fetch_slice)
        self.assertIn("fetch('/api/settings')", fetch_slice)
        self.assertIn("generation === settingsPageCacheGeneration", fetch_slice)
        self.assertIn("settingsPageCache = data", fetch_slice)
        self.assertIn("settingsPageLoadPromise = request", fetch_slice)
        # Force supersedes soft in-flight (generation bump blocks stale write).
        self.assertIn("// Abandon soft in-flight bookkeeping; generation bump blocks stale cache write.", fetch_slice)

        inv_start = js_text.index("function invalidateSettingsPageCache")
        inv_end = js_text.index("async function fetchSettingsPagePayload", inv_start)
        inv_slice = js_text[inv_start:inv_end]
        self.assertIn("settingsPageCacheGeneration += 1", inv_slice)
        self.assertIn("settingsPageLoadPromise = null", inv_slice)
        self.assertIn("settingsPageLoadForce = false", inv_slice)

        load_start = js_text.index("async function loadSettings(forceRefresh = false)")
        load_end = js_text.index("console.error('loadSettings error:'", load_start)
        load_slice = js_text[load_start:load_end]
        self.assertIn("fetchSettingsPagePayload(forceRefresh)", load_slice)

        # Error toast only while Settings page/modal is still active (soft load may finish after navigate away).
        catch_start = js_text.index("console.error('loadSettings error:'", load_start)
        catch_end = js_text.index("// ==================== 部署信息检测", catch_start)
        catch_slice = js_text[catch_start:catch_end]
        self.assertIn("isSettingsSurfaceActive()", catch_slice)
        toast_idx = catch_slice.index("translateAppTextLocal('加载设置失败')")
        toast_guard = catch_slice[max(0, toast_idx - 200) : toast_idx]
        self.assertIn("isSettingsSurfaceActive()", toast_guard)

        # Successful writes drop the soft cache (or repopulate via server refresh).
        save_start = js_text.index("async function saveSettings()")
        save_end = js_text.index("async function testTelegramPush", save_start)
        self.assertIn("invalidateSettingsPageCache()", js_text[save_start:save_end])
        auto_start = js_text.index("async function autoSaveSettings(tabName)")
        auto_end = js_text.index("function onTempMailProviderChange", auto_start)
        self.assertIn("invalidateSettingsPageCache()", js_text[auto_start:auto_end])
        refresh_start = js_text.index("async function refreshTempMailSettingsSnapshotFromServer()")
        refresh_end = js_text.index("function collectApiSecuritySettingsPayload", refresh_start)
        self.assertIn("fetchSettingsPagePayload(true)", js_text[refresh_start:refresh_end])
        self.assertNotIn("fetch('/api/settings')", js_text[refresh_start:refresh_end])

        # Other soft GET consumers share the helper (no extra raw GETs).
        poll_start = js_text.index("async function initPollingSettings()")
        poll_end = js_text.index("function formatRelativeTime", poll_start)
        self.assertIn("fetchSettingsPagePayload(false)", js_text[poll_start:poll_end])
        self.assertNotIn("fetch('/api/settings')", js_text[poll_start:poll_end])
        trig_start = js_text.index("async function triggerUpdate()")
        trig_end = js_text.index("function dismissVersionBanner", 0)  # may be before; find end differently
        # triggerUpdate is near end of file — slice a bounded window.
        trig_slice = js_text[trig_start : trig_start + 1200]
        self.assertIn("fetchSettingsPagePayload(false)", trig_slice)
        self.assertNotIn("fetch('/api/settings')", trig_slice)

        # Only the soft-load helper should own the raw GET /api/settings call site for page cache.
        raw_get_hits = [line for line in js_text.splitlines() if "fetch('/api/settings')" in line and "method" not in line]
        self.assertEqual(len(raw_get_hits), 1, raw_get_hits)

    def test_navigate_soft_loads_refresh_and_audit_log_pages(self):
        """Re-entering refresh-log / audit must reuse warm payload caches."""
        js_text = load_frontend_app_js()
        nav_start = js_text.index("function navigate(page)")
        nav_end = js_text.index("function updateTopbar(page)", nav_start)
        nav_slice = js_text[nav_start:nav_end]
        # Default soft-load (no force flag on navigate).
        self.assertIn("loadRefreshLogPage()", nav_slice)
        self.assertIn("loadAuditLogPage()", nav_slice)
        self.assertNotIn("loadRefreshLogPage(true)", nav_slice)
        self.assertNotIn("loadAuditLogPage(true)", nav_slice)

        self.assertIn("async function loadRefreshLogPage(forceRefresh = false)", js_text)
        self.assertIn("async function loadAuditLogPage(forceRefresh = false)", js_text)
        self.assertIn("let refreshLogPageLoadPromise = null", js_text)
        self.assertIn("let refreshLogPageLoadForce = false", js_text)
        self.assertIn("let auditLogPageLoadPromise = null", js_text)
        self.assertIn("let auditLogPageLoadForce = false", js_text)
        self.assertIn("!force && refreshLogPageCache", js_text)
        self.assertIn("!force && auditLogPageCache", js_text)
        self.assertIn("if (!force || refreshLogPageLoadForce)", js_text)
        self.assertIn("if (!force || auditLogPageLoadForce)", js_text)
        self.assertIn("refreshLogPageLoadForce = force", js_text)
        self.assertIn("auditLogPageLoadForce = force", js_text)
        self.assertIn("refreshLogPageLoadPromise !== request", js_text)
        self.assertIn("auditLogPageLoadPromise !== request", js_text)
        self.assertIn("function invalidateRefreshLogPageCache", js_text)
        self.assertIn("function invalidateAuditLogPageCache", js_text)
        self.assertIn("window.invalidateAuditLogPageCache = invalidateAuditLogPageCache", js_text)
        # Page-surface paint guards: always warm cache; paint only on the matching page.
        self.assertIn("function isCurrentRefreshLogPage()", js_text)
        self.assertIn("function isCurrentAuditLogPage()", js_text)
        self.assertIn("currentPage === 'refresh-log'", js_text)
        self.assertIn("currentPage === 'audit'", js_text)
        refresh_start = js_text.index("async function loadRefreshLogPage(forceRefresh = false)")
        refresh_end = js_text.index("function isCurrentAuditLogPage()", refresh_start)
        refresh_slice = js_text[refresh_start:refresh_end]
        self.assertIn("if (isCurrentRefreshLogPage())", refresh_slice)
        self.assertIn("// Always warm soft cache; paint only on refresh-log page.", refresh_slice)
        audit_start = js_text.index("async function loadAuditLogPage(forceRefresh = false)")
        audit_end = js_text.index("function formatDateTime", audit_start)
        audit_slice = js_text[audit_start:audit_end]
        self.assertIn("if (isCurrentAuditLogPage())", audit_slice)
        self.assertIn("// Always warm soft cache; paint only on audit page.", audit_slice)

        audit_inv_start = js_text.index("function invalidateAuditLogPageCache")
        audit_inv_end = js_text.index("function renderRefreshLogPage", audit_inv_start)
        audit_inv_slice = js_text[audit_inv_start:audit_inv_end]
        self.assertIn("auditLogPageCache = null", audit_inv_slice)
        self.assertIn("auditLogPageLoadPromise = null", audit_inv_slice)
        self.assertIn("auditLogPageLoadForce = false", audit_inv_slice)

        # Settings writes and refresh success paths drop audit soft cache.
        save_start = js_text.index("async function saveSettings()")
        save_end = js_text.index("async function testTelegramPush", save_start)
        self.assertIn("invalidateAuditLogPageCache()", js_text[save_start:save_end])
        auto_start = js_text.index("async function autoSaveSettings(tabName)")
        auto_end = js_text.index("function onTempMailProviderChange", auto_start)
        self.assertIn("invalidateAuditLogPageCache()", js_text[auto_start:auto_end])
        refresh_all_start = js_text.index("async function refreshAllAccounts()")
        complete_idx = js_text.index("data.type === 'complete'", refresh_all_start)
        self.assertIn("invalidateAuditLogPageCache", js_text[complete_idx : complete_idx + 4000])
        # Full token refresh drops refresh-log soft cache so next visit refetches.
        refresh_start = js_text.index("async function refreshAllAccounts()")
        complete_idx = js_text.index("data.type === 'complete'", refresh_start)
        complete_slice = js_text[complete_idx : complete_idx + 4000]
        self.assertIn("invalidateRefreshLogPageCache", complete_slice)

        # Single / failed / selected-batch refresh paths also drop the soft cache.
        retry_start = js_text.index("async function retrySingleAccount")
        retry_end = js_text.index("function showFailedListFromData", retry_start)
        self.assertIn("invalidateRefreshLogPageCache", js_text[retry_start:retry_end])
        failed_start = js_text.index("async function retryFailedAccounts")
        failed_end = js_text.index("async function retrySingleAccount", failed_start)
        self.assertIn("invalidateRefreshLogPageCache", js_text[failed_start:failed_end])
        batch_start = js_text.index("function handleBatchRefreshSSEEvent")
        batch_end = js_text.index("function updateAccountCardRefreshStatus", batch_start)
        batch_slice = js_text[batch_start:batch_end]
        # Batch refresh completion toasts translate at paint time.
        self.assertIn("translateAppTextLocal('✅ Token 刷新完成：成功 ' + success_count + ' 个')", batch_slice)
        self.assertIn(
            "translateAppTextLocal(\n                            '⚠️ Token 刷新完成：成功 ' + success_count + ' 个，失败 ' + failed_count + ' 个'\n                        )",
            batch_slice,
        )
        self.assertIn("translateAppTextLocal('失败账号：')", batch_slice)
        self.assertIn("translateAppTextLocal('🔄 正在刷新 Token... 0 / ' + total)", batch_slice)
        self.assertIn("translateAppTextLocal('请选择要刷新 Token 的账号')", js_text)
        self.assertIn("translateAppTextLocal('所选账号均为 IMAP 账号，不支持 Token 刷新')", js_text)
        self.assertIn("translateAppTextLocal('刷新请求失败，请稍后重试')", js_text)
        self.assertIn("translateAppTextLocal('加载失效 Token 候选失败')", js_text)
        self.assertIn("translateAppTextLocal('没有需要处理的候选账号')", js_text)
        self.assertIn("translateAppTextLocal('批量停用请求失败')", js_text)
        self.assertIn("translateAppTextLocal('批量删除请求失败')", js_text)
        # Full refresh / retry completion toasts use translateAppTextLocal (not getUiLanguage ternaries).
        refresh_all = js_text[
            js_text.index("async function refreshAllAccounts()") : js_text.index("async function retryFailedAccounts")
        ]
        self.assertIn(
            "translateAppTextLocal(\n                                    '刷新完成！成功: ' + data.success_count + ', 失败: ' + data.failed_count\n                                )",
            refresh_all,
        )
        self.assertNotIn("getUiLanguage() === 'en'\n                                    ? `Refresh completed", refresh_all)
        retry_failed = js_text[
            js_text.index("async function retryFailedAccounts") : js_text.index("async function retrySingleAccount")
        ]
        self.assertIn(
            "translateAppTextLocal(\n                                '重试完成！成功: ' + data.success_count + ', 失败: ' + data.failed_count\n                            )",
            retry_failed,
        )
        retry_single = js_text[
            js_text.index("async function retrySingleAccount") : js_text.index("function showFailedListFromData")
        ]
        self.assertIn("translateAppTextLocal(accountEmail + ' 刷新成功')", retry_single)
        self.assertIn("data.type === 'complete'", batch_slice)
        self.assertIn("invalidateRefreshLogPageCache", batch_slice)

    def test_summary_command_center_secret_safety(self):
        js_text = load_feature_package_js("static/js/features/overview")
        start = js_text.index("function renderOverviewSummary(data)")
        end = js_text.index("function renderVerificationStats(data)", start)
        summary_slice = js_text[start:end]

        forbidden = [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "api_key",
            "bearer",
            "task_token",
            "claim_token",
            "password",
        ]
        for token in forbidden:
            self.assertNotIn(token, summary_slice)

    def test_external_api_overview_secret_safety(self):
        js_text = load_feature_package_js("static/js/features/overview")
        start = js_text.index("function renderExternalApiStats(data)")
        end = js_text.index("function renderPoolStats(data)", start)
        external_api_slice = js_text[start:end]

        forbidden = [
            "settingsExternalApiKey",
            "settingsExternalApiKeysJson",
            "settingsDuckmailBearerToken",
            "settingsEmailnatorApiKey",
            "settingsTempMailApiKey",
            "api_key_masked",
            "api_key",
            "bearer",
            "task_token",
            "claim_token",
        ]
        for token in forbidden:
            self.assertNotIn(token, external_api_slice)

    def test_overview_css_uses_restrained_token_surfaces(self):
        css_text = (ROOT / "static" / "css" / "main.css").read_text(encoding="utf-8")
        start = css_text.index("/* ==================== Overview Dashboard ==================== */")
        end = css_text.index("/* ===== Pool Admin Table Enhancement", start)
        overview_css = css_text[start:end]

        self.assertIn(".ov-command-shell", overview_css)
        self.assertIn(".ov-command-center", overview_css)
        self.assertIn(".ov-command-grid", overview_css)
        self.assertIn(".ov-command-actions", overview_css)
        self.assertIn(".ov-command-action-list", overview_css)
        self.assertIn(".ov-api-health-strip", overview_css)
        self.assertIn(".ov-endpoint-health-row", overview_css)
        self.assertIn(".ov-endpoint-health-metrics", overview_css)
        self.assertIn("background: var(--bg-card);", overview_css)
        self.assertIn("border-radius: var(--radius);", overview_css)
        self.assertIn("overflow-x: auto;", overview_css)
        self.assertIn(".ov-tab:focus-visible", overview_css)
        self.assertIn("@media (max-width: 520px)", overview_css)
        self.assertIn(".ov-command-grid {", overview_css)
        self.assertIn(".ov-api-health-strip {", overview_css)
        self.assertIn("grid-template-columns: 1fr;", overview_css)
        self.assertNotIn(".overview-tab-shell::before", overview_css)
        self.assertNotIn(".overview-tab-shell::after", overview_css)
        self.assertNotIn(".ov-hover-note", overview_css)
        self.assertNotIn("radial-gradient", overview_css)
        self.assertNotIn("backdrop-filter", overview_css)
        self.assertNotIn("translateY(-6px)", overview_css)

    def test_overview_i18n_has_current_labels(self):
        i18n_text = (ROOT / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn("'\u8fd0\u8425\u63a7\u5236\u53f0': 'Operations console'", i18n_text)
        self.assertIn("'\u8fd0\u884c\u72b6\u6001': 'Service health'", i18n_text)
        self.assertIn("'\u7edf\u4e00\u90ae\u7bb1\u6307\u6325\u53f0': 'Unified mailbox command center'", i18n_text)
        self.assertIn(
            "'\u805a\u5408\u90ae\u7bb1\u3001Provider \u4e0e\u5916\u90e8 API \u63a5\u5165\u72b6\u6001': 'Mailbox, provider, and external API readiness'",
            i18n_text,
        )
        self.assertIn("'\u90ae\u7bb1\u5e93\u5b58': 'Mailbox inventory'", i18n_text)
        self.assertIn("'\u4e0b\u4e00\u6b65\u52a8\u4f5c': 'Next actions'", i18n_text)
        self.assertIn("'\u53ef\u4f7f\u7528': 'Ready'", i18n_text)
        self.assertIn("'\u9700\u68c0\u67e5': 'Needs check'", i18n_text)
        self.assertIn("'\u63a5\u53e3\u5065\u5eb7': 'Endpoint Health'", i18n_text)
        self.assertIn("'\u8c03\u7528\u65b9\u5065\u5eb7': 'Caller Health'", i18n_text)
        self.assertIn("'\u9519\u8bef\u7387': 'Error Rate'", i18n_text)
        self.assertNotIn("'\u73bb\u7483\u6001\u6982\u89c8\u9762\u677f':", i18n_text)
        self.assertNotIn("'\u7ec6\u817b\u5361\u7247\u89c6\u56fe':", i18n_text)


if __name__ == "__main__":
    unittest.main()
