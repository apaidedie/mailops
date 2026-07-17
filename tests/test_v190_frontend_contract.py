from __future__ import annotations

import re
import unittest

from tests._import_app import import_web_app_module
from tests.frontend_js_bundle import load_feature_package_js, load_frontend_app_js


class V190FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def _login(self, client):
        resp = client.post("/login", json={"password": "testpass123"})
        self.assertEqual(resp.status_code, 200)

    def _get_text(self, client, path):
        resp = client.get(path)
        try:
            return resp.data.decode("utf-8")
        finally:
            resp.close()

    def test_i18n_runtime_exposes_date_and_error_helpers(self):
        client = self.app.test_client()
        js = self._get_text(client, "/static/js/i18n.js")
        self.assertIn("window.formatUiDateTime", js)
        self.assertIn("window.formatUiRelativeTime", js)
        self.assertIn("window.resolveApiErrorMessage", js)
        self.assertIn("switcher-docked", js)
        self.assertIn("document.querySelector('.sidebar-bottom')", js)
        self.assertIn(
            "root.querySelectorAll('[placeholder],[title],[aria-label],input[type=\"button\"][value]')",
            js,
        )
        self.assertIn("const core = text.trim()", js)

    def test_i18n_skips_dynamic_business_scopes(self):
        client = self.app.test_client()
        js = self._get_text(client, "/static/js/i18n.js")

        self.assertIn("const I18N_SKIP_SELECTORS", js)
        self.assertIn("data-i18n-skip", js)
        for selector in [
            "#emailList",
            "#emailDetail",
            "#accountList",
            "#compactAccountList",
            "#refreshLogContainer",
            "#auditLogContainer",
            "#tempEmailContainer",
        ]:
            self.assertIn(selector, js)

    def test_main_js_does_not_override_i18n_runtime_helpers(self):
        client = self.app.test_client()
        main_js = load_frontend_app_js()
        self.assertIn("const pickApiMessage = (payload, fallbackZh, fallbackEn) =>", main_js)
        self.assertIn("const formatUiDateTime = (dateStr, options = {}) =>", main_js)
        self.assertIn(
            "const formatUiRelativeTime = (dateStr, fallbackZh = '从未刷新', fallbackEn = 'Never refreshed') =>",
            main_js,
        )
        self.assertNotIn("function pickApiMessage(payload, fallbackZh, fallbackEn)", main_js)
        self.assertNotIn("function formatUiDateTime(dateStr, options = {})", main_js)
        self.assertNotIn(
            "function formatUiRelativeTime(dateStr, fallbackZh = '从未刷新', fallbackEn = 'Never refreshed')",
            main_js,
        )

    def test_frontend_no_longer_uses_raw_error_object_toasts_on_key_paths(self):
        client = self.app.test_client()
        main_js = load_frontend_app_js()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        self.assertNotIn("showToast(data.error || '创建失败'", main_js)
        self.assertNotIn("showToast(data.error || '删除失败'", main_js)
        self.assertNotIn("showToast(data.error || '操作失败'", main_js)
        self.assertNotIn("showToast(result.error, 'error')", accounts_js)

    def test_settings_and_login_pages_load_i18n_script(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")
        login_html = self._get_text(client, "/login")
        self.assertIn("/static/js/i18n.js", index_html)
        self.assertIn("/static/js/i18n.js", login_html)
        self.assertIn('id="telegramPollInterval" min="10" max="86400"', index_html)
        self.assertIn('id="webhookNotificationEnabled"', index_html)
        self.assertIn('id="webhookNotificationUrl"', index_html)
        self.assertIn('id="webhookNotificationToken"', index_html)
        self.assertIn('id="btnTestWebhookNotification"', index_html)

    def test_key_email_notification_translations_exist(self):
        client = self.app.test_client()
        js = self._get_text(client, "/static/js/i18n.js")
        for text in [
            "邮件通知",
            "启用邮件通知",
            "启用 Email 通知",
            "Email 通知",
            "Telegram 通知",
            "接收通知邮箱",
            "发送测试邮件",
            "📤 导出",
            "导出",
            "🔄 全量刷新 Token",
            "全量刷新 Token",
            "＋ 添加账号",
            "添加账号",
            "＋ 创建邮箱",
            "创建邮箱",
            "🔑 验证码",
            "验证码",
            "审计日志",
            "📋 审计日志",
            "暂无审计记录",
            "加载审计日志失败",
            "手动",
            "定时",
            "✉️ 邮件通知",
            "✉️ Email 通知",
            "Email 通知",
            "📬 Telegram 通知",
            "Telegram 通知",
            "📬 Telegram 推送",
            "这里只配置 Email 通知通道。普通邮箱需在账号列表开启通知后才会通过 Email 发送；临时邮箱按当前通知规则处理。启用后仅从新到达的邮件开始通知。",
            "这里只配置 Email 渠道的接收邮箱，不会让所有普通邮箱自动发送。",
            "这里只配置 Telegram 通知通道。普通邮箱需在账号列表开启通知后才会通过 Telegram 发送；临时邮箱按当前通知规则处理。",
            "验证当前 Telegram 通知通道是否配置正确",
            "通知",
            "该邮箱通知参与",
            "开启该邮箱通知参与",
            "该邮箱通知参与（已开启）",
            "该邮箱通知参与已开启",
            "该邮箱通知参与已关闭",
            "点击关闭该邮箱通知参与",
            "关闭时（默认）仅做 API Key 鉴权；开启后额外启用 IP 白名单、限流、高风险端点禁用等安全策略。",
            "建议设置为 30 天，防止 Token 因 90 天不使用而过期",
            "默认分组",
            "请从左侧选择一个邮箱账号",
            "选择一个临时邮箱查看邮件",
            "表达式有效",
            "下次执行:",
            "验证失败:",
            "自动按类型分组",
            "请选择标签...",
            "请选择分组...",
            "轮询中",
            "输入新密码（留空则不修改）",
            "用于 /api/v1/external/* 的 X-API-Key；兼容 /api/v1/external/*",
            "每行一个 IP 或 CIDR，如 192.168.1.0/24",
            "输入 Bot Token",
            "输入 Chat ID",
            "http://host:port 或 socks5://user:pass@host:port",
            "授权成功后，浏览器会跳转到一个空白页，请复制地址栏中的完整 URL 并粘贴到这里",
            "确定要刷新所有账号的 Token 吗？",
            "确定要删除这个标签吗？",
            "再次确认：删除账号将同时清除所有相关数据，是否继续？",
            "⚠️ 警告：启用信任模式将直接显示邮件原始内容，不进行任何安全过滤。",
            "Cron 表达式",
            "📨 收件箱",
            "收件箱",
            "⚠️ 垃圾邮件",
            "垃圾邮件",
            "🔔 推送",
            "QQ邮箱",
            "163邮箱",
            "126邮箱",
            "阿里云邮箱",
            "自定义IMAP",
            "该分组暂无邮箱",
            "收件箱为空",
            "暂无邮件",
            "未知发件人",
            "勾选后，新导入的 Outlook/IMAP 账号会以 `available` 状态进入邮箱池；不勾选则保持池外。",
            "（每个邮箱刷新之间的等待时间）",
            "访问 GitHub 仓库",
            "Webhook 通知",
            "启用 Webhook 通知",
            "Webhook URL",
            "Webhook Token（可选）",
            "测试 Webhook",
            "Webhook 测试成功",
            "Webhook 测试失败",
            "随机生成",
            "当前已存在 API Key，是否覆盖？",
        ]:
            self.assertIn(text, js)

    def test_frontend_success_toasts_use_pick_api_message_on_key_paths(self):
        client = self.app.test_client()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        groups_js = load_feature_package_js("static/js/features/groups")
        main_js = load_frontend_app_js()
        self.assertIn("pickApiMessage(result, result.message", accounts_js)
        self.assertIn("pickApiMessage(data, data.message", groups_js)
        self.assertIn("pickApiMessage(data, data.message", main_js)

    def test_frontend_dynamic_options_and_placeholders_use_i18n_helpers(self):
        client = self.app.test_client()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        main_js = load_frontend_app_js()
        groups_js = load_feature_package_js("static/js/features/groups")
        emails_js = load_feature_package_js("static/js/features/emails")
        temp_emails_js = load_feature_package_js("static/js/features/temp_emails")
        self.assertIn("translateAppTextLocal('自动按类型分组')", accounts_js)
        self.assertIn("translateAppTextLocal('支持混合格式，每行一个账号", accounts_js)
        self.assertIn("translateAppTextLocal('请选择标签...')", main_js)
        self.assertIn("translateAppTextLocal('请选择分组...')", main_js)
        self.assertIn("translateAppTextLocal('通知')", groups_js)
        self.assertIn("translateAppTextLocal('点击关闭该邮箱通知参与')", groups_js)
        self.assertIn(
            "translateAppTextLocal(notificationEnabled ? '该邮箱通知参与（已开启）' : '开启该邮箱通知参与')",
            groups_js,
        )
        self.assertIn("function getEmailListEmptyMessage()", emails_js)
        self.assertIn("translateAppTextLocal('收件箱为空')", emails_js)
        self.assertIn("translateAppTextLocal('垃圾邮件为空')", emails_js)
        self.assertIn("getEmailListEmptyMessage()", emails_js)
        # Empty message must be folder-aware (junk must not always say inbox empty).
        empty_fn = emails_js[
            emails_js.index("function getEmailListEmptyMessage()") : emails_js.index("function renderEmailList")
        ]
        self.assertIn("junkemail", empty_fn)
        self.assertIn("translateAppTextLocal('暂无邮件')", empty_fn)
        self.assertIn("translateAppTextLocal('暂无邮件')", temp_emails_js)

    def test_frontend_email_list_sorting_fallback_is_present_on_all_key_paths(self):
        client = self.app.test_client()
        emails_js = load_feature_package_js("static/js/features/emails")
        main_js = load_frontend_app_js()

        # helper contract: timestamp fallback chain + stable newest-first sort
        self.assertIn("function resolveEmailSortTimestamp(email)", emails_js)
        self.assertIn(
            "const rawDate = email && (email.receivedDateTime || email.date || email.created_at || email.received_at);",
            emails_js,
        )
        self.assertIn("return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;", emails_js)
        self.assertIn("function sortEmailsByNewestFirst(list)", emails_js)
        self.assertIn(".sort((a, b) => (b.timestamp - a.timestamp) || (a.index - b.index))", emails_js)
        self.assertIn("window.sortEmailsByNewestFirst = sortEmailsByNewestFirst;", emails_js)

        # loadEmails(): fetch path + cache recovery path
        self.assertIn("const sortedEmails = sortEmailsByNewestFirst(data.emails || []);", emails_js)
        self.assertIn("currentEmails = sortEmailsByNewestFirst(cache.emails || []);", emails_js)

        # loadMoreEmails(): merged pagination fallback in core/http.js
        self.assertIn("const mergedEmails = (typeof sortEmailsByNewestFirst === 'function')", main_js)
        self.assertIn(
            "? sortEmailsByNewestFirst(baselineEmails.concat(data.emails || []))",
            main_js,
        )

        # switchFolder(): cache recovery fallback in core/http.js
        self.assertIn("? sortEmailsByNewestFirst(cache.emails || [])", main_js)

        # selectAccount() in accounts.js: cache recovery must also sort
        accounts_js = load_feature_package_js("static/js/features/accounts")
        self.assertIn("? sortEmailsByNewestFirst(cache.emails || [])", accounts_js)

    def test_notification_copy_matches_channel_vs_account_model(self):
        client = self.app.test_client()
        self._login(client)
        index_html = self._get_text(client, "/")
        groups_js = load_feature_package_js("static/js/features/groups")

        # Structural chrome uses plain titles (vector icons elsewhere); keep channel copy precise.
        self.assertIn("Email 通知", index_html)
        self.assertIn("Telegram 通知", index_html)
        self.assertNotIn("✉️ Email 通知", index_html)
        self.assertNotIn("📬 Telegram 通知", index_html)
        self.assertIn(
            "这里只配置 Email 通知通道。普通邮箱需在账号列表开启通知后才会通过 Email 发送；临时邮箱按当前通知规则处理。启用后仅从新到达的邮件开始通知。",
            index_html,
        )
        self.assertIn("这里只配置 Email 渠道的接收邮箱，不会让所有普通邮箱自动发送。", index_html)
        self.assertIn(
            "这里只配置 Telegram 通知通道。普通邮箱需在账号列表开启通知后才会通过 Telegram 发送；临时邮箱按当前通知规则处理。",
            index_html,
        )
        self.assertNotIn(
            "全局生效，覆盖普通邮箱和临时邮箱；仅从启用后新到达的邮件开始通知。",
            index_html,
        )
        self.assertNotIn(
            "只需填写接收邮箱，不暴露复杂邮件网关配置。关闭通知后可保留该邮箱。",
            index_html,
        )
        self.assertIn("acc.notification_enabled !== undefined", groups_js)
        self.assertIn(
            "currentAccountSearchQuery = String(query || '').trim();",
            groups_js,
        )
        self.assertIn(
            "await loadAccountsByGroup(currentGroupId, true, 1);",
            groups_js,
        )

    def test_frontend_import_and_export_error_contract_helpers_are_consumed(self):
        client = self.app.test_client()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        main_js = load_frontend_app_js()
        self.assertIn("buildImportFailureToastMessage", accounts_js)
        self.assertIn("data.summary || Array.isArray(data.errors)", accounts_js)
        self.assertIn("if (verifyData.need_verify)", accounts_js)
        self.assertIn("if (data.need_verify)", accounts_js)
        self.assertIn("translateAppTextLocal('【用户错误信息】')", main_js)
        self.assertIn("translateAppTextLocal('【错误详情】')", main_js)
        self.assertIn("translateAppTextLocal('【技术堆栈/细节】')", main_js)

    def test_frontend_polling_settings_preserve_zero_value(self):
        client = self.app.test_client()
        self._login(client)
        main_js = load_frontend_app_js()
        index_html = self._get_text(client, "/")

        self.assertIn("function parseIntegerSetting(value, fallback)", main_js)
        self.assertIn("let autoPollingEnabled = false;", main_js)
        self.assertIn("function applyPollingSettings(settings, { restart = false", main_js)
        # [Phase 3 兼容] 使用两个字段的或运算
        self.assertIn(
            "autoPollingEnabled = isAutoPollingEnabledSetting(settings.enable_auto_polling)",
            main_js,
        )
        self.assertIn(
            "|| isAutoPollingEnabledSetting(settings.enable_compact_auto_poll);",
            main_js,
        )
        self.assertIn("String(parseIntegerSetting(data.settings.polling_count, 5))", main_js)
        self.assertIn("maxPollingCount = parseIntegerSetting(settings.polling_count, 5);", main_js)
        self.assertIn("applyPollingSettings(settings, { restart: true });", main_js)
        self.assertNotIn("data.settings.polling_count || '5'", main_js)
        self.assertNotIn("parseInt(data.settings.polling_count) || 5", main_js)
        self.assertIn('id="pollingCount" min="0" max="100" value="5"', index_html)
        self.assertIn("范围：0-100 次，设置为 0 表示持续轮询", index_html)

    def test_frontend_auto_polling_uses_shared_runtime_state_for_account_selection_and_email_load(
        self,
    ):
        """Phase 2: 轮询触发从'选中账号自动启动'改为'复制邮箱启动'，由统一引擎处理"""
        client = self.app.test_client()
        main_js = load_frontend_app_js()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        emails_js = load_feature_package_js("static/js/features/emails")
        poll_engine_js = self._get_text(client, "/static/js/features/poll-engine.js")
        compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")

        # 统一引擎包含核心轮询逻辑
        self.assertIn("function startPoll(email, opts)", poll_engine_js)
        self.assertIn("function stopPoll(email, toastMsg, toastType)", poll_engine_js)
        self.assertIn("function stopAllPolls()", poll_engine_js)
        # email-copied 事件监听在 compact 适配层（现支持标准和简洁两种模式）
        self.assertIn("email-copied", compact_js)
        # 标准模式选中账号不再自动启动轮询（已删除 syncPollingForCurrentAccount）
        self.assertNotIn("syncPollingForCurrentAccount", accounts_js)
        self.assertNotIn("syncPollingForCurrentAccount", emails_js)
        # 临时邮箱切换使用统一引擎停止
        self.assertNotIn("fetch('/api/settings')", emails_js)

    def test_account_panel_density_sync_runs_on_init_and_mailbox_navigation(self):
        client = self.app.test_client()
        main_js = load_frontend_app_js()

        self.assertIn("let accountPanelDensitySyncHandle = null;", main_js)
        self.assertIn("function syncAccountPanelDensityIfVisible()", main_js)
        self.assertIn("function scheduleAccountPanelDensitySync()", main_js)
        self.assertIn("syncAccountPanelDensityIfVisible();", main_js)
        self.assertIn("scheduleAccountPanelDensitySync();", main_js)
        self.assertIn(
            "window.addEventListener('resize', scheduleAccountPanelDensitySync, { passive: true });",
            main_js,
        )
        self.assertIn("if (page === 'mailbox') {", main_js)

    def test_external_pool_settings_are_exposed_in_settings_page_and_saved_by_frontend(
        self,
    ):
        client = self.app.test_client()
        self._login(client)
        main_js = load_frontend_app_js()
        index_html = self._get_text(client, "/")

        self.assertIn(
            "const poolExternalEnabledEl = document.getElementById('poolExternalEnabled');",
            main_js,
        )
        self.assertIn("data.settings.pool_external_enabled === true", main_js)
        self.assertIn("settings.pool_external_enabled = poolExternalEnabledEl.checked", main_js)
        self.assertIn(
            "settings.external_api_disable_pool_claim_random = disablePoolClaimRandomEl.checked",
            main_js,
        )
        self.assertIn(
            "settings.external_api_disable_pool_claim_release = disablePoolClaimReleaseEl.checked",
            main_js,
        )
        self.assertIn(
            "settings.external_api_disable_pool_claim_complete = disablePoolClaimCompleteEl.checked",
            main_js,
        )
        self.assertIn(
            "settings.external_api_disable_pool_stats = disablePoolStatsEl.checked",
            main_js,
        )
        self.assertIn('id="poolExternalEnabled"', index_html)
        self.assertIn('id="externalApiDisablePoolClaimRandom"', index_html)
        self.assertIn('id="externalApiDisablePoolClaimRelease"', index_html)
        self.assertIn('id="externalApiDisablePoolClaimComplete"', index_html)
        self.assertIn('id="externalApiDisablePoolStats"', index_html)
        self.assertIn("启用 external pool 端点", index_html)
        # Workflow-B: long form essays removed; keep control IDs + save path as contract.
        self.assertIn("function generateExternalApiKey()", main_js)
        self.assertIn("function copyExternalApiKey()", main_js)
        self.assertIn("window.crypto.getRandomValues", main_js)
        self.assertIn("const bytes = new Uint8Array(64)", main_js)
        self.assertIn("async function testWebhookNotification()", main_js)
        self.assertIn("/api/settings/webhook-test", main_js)

    def test_account_edit_uses_conditional_outlook_credential_validation(self):
        client = self.app.test_client()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        self.assertIn("clientIdInput.dataset.originalValue = acc.client_id || '';", accounts_js)
        self.assertIn(
            "const wantsToUpdateOutlookCredentials = !isImap && (hasClientIdChanged || !!refreshToken);",
            accounts_js,
        )
        self.assertIn(
            "if (wantsToUpdateOutlookCredentials && (!data.client_id || !data.refresh_token))",
            accounts_js,
        )
        self.assertNotIn("if (!isImap && (!data.client_id || !data.refresh_token))", accounts_js)

    def test_import_account_provider_selector_is_catalog_driven(self):
        """导入账号邮箱类型应来自 /api/providers account catalog，而非模板硬编码列表。"""
        client = self.app.test_client()
        self._login(client)
        html = self._get_text(client, "/")
        accounts_js = load_feature_package_js("static/js/features/accounts")

        self.assertIn('id="accountProvider"', html)
        self.assertIn('id="accountProviderNote"', html)
        select_start = html.index('id="accountProvider"')
        select_end = html.index("</select>", select_start)
        select_html = html[select_start:select_end]
        self.assertIn("加载 Provider 目录", select_html)
        self.assertNotIn('value="outlook"', select_html)
        self.assertNotIn('value="gmail"', select_html)
        self.assertNotIn('value="custom"', select_html)

        self.assertIn("function loadProviders", accounts_js)
        self.assertIn("function getImportAccountProviderOptionsFromPayload", accounts_js)
        self.assertIn("function ensureImportProviderSelectOptions", accounts_js)
        self.assertIn("function ensureAutoImportProviderOption", accounts_js)
        self.assertIn("function updateAccountProviderNote", accounts_js)
        self.assertIn("mailbox_providers", accounts_js)
        self.assertIn("toLowerCase() === 'account'", accounts_js)
        self.assertIn("['auto', 'outlook']", accounts_js)
        self.assertIn("accountProviderNote", accounts_js)
        # Prefer shared catalog cache/loader; direct /api/providers is last-resort only.
        self.assertIn("mailboxProviderCatalogCache", accounts_js)
        self.assertIn("loadMailboxProviderCatalog", accounts_js)
        self.assertIn("optionsFromSharedCatalogCache", accounts_js)
        self.assertIn("Last-resort fallback when shared loader/cache is unavailable", accounts_js)
        self.assertIn("fetch('/api/providers')", accounts_js)
        # Concurrent import-modal opens share one in-flight loadProviders promise.
        self.assertIn("let providersLoadPromise = null", accounts_js)
        self.assertIn("let providersLoadForce = false", accounts_js)
        load_start = accounts_js.index("async function loadProviders(forceRefresh = false)")
        load_end = accounts_js.index("function onProviderChange", load_start)
        load_slice = accounts_js[load_start:load_end]
        # Soft re-entry re-paints from warm catalog before return (no bare early-return).
        self.assertIn("if (providersLoaded && !force)", load_slice)
        self.assertIn("optionsFromSharedCatalogCache()", load_slice)
        self.assertIn("applyImportProviderOptions(cachedOptions)", load_slice)
        self.assertIn("if (!force || providersLoadForce)", load_slice)
        self.assertIn("providersLoadForce = force", load_slice)
        self.assertIn("providersLoadPromise !== request", load_slice)
        self.assertIn("providersLoadPromise = request", load_slice)
        # Paint #accountProvider only while add-account/import modal is open.
        self.assertIn("function isAddAccountModalOpen()", accounts_js)
        self.assertIn("if (!isAddAccountModalOpen())", load_slice)
        warm_idx = load_slice.index("if (providersLoaded && !force)")
        promise_idx = load_slice.index("if (providersLoadPromise)")
        self.assertLess(warm_idx, promise_idx)
        self.assertLess(
            load_slice.index("optionsFromSharedCatalogCache()"),
            promise_idx,
        )

    def test_import_result_provider_labels_are_catalog_driven(self):
        """Auto 导入结果统计的 provider 名称应来自 catalog，而非硬编码 map。"""
        client = self.app.test_client()
        accounts_js = load_feature_package_js("static/js/features/accounts")
        main_js = load_frontend_app_js()

        self.assertIn("function getImportResultProviderLabel", accounts_js)
        self.assertIn("resolveMailboxProviderLabel", accounts_js)
        self.assertIn("function resolveMailboxProviderLabel", main_js)
        self.assertIn("findImportAccountProviderOption", accounts_js)
        self.assertIn("getImportResultProviderLabel(prov)", accounts_js)
        self.assertNotIn(
            "const provNames = {outlook:'Outlook',gmail:'Gmail'",
            accounts_js,
        )
        self.assertNotIn("provNames[prov]", accounts_js)

    def test_collapsed_sidebar_hides_github_label_to_avoid_overlap(self):
        client = self.app.test_client()
        css = self._get_text(client, "/static/css/main.css")
        i18n_js = self._get_text(client, "/static/js/i18n.js")
        self.assertIn(".sidebar-collapsed .btn-github span { display: none; }", css)
        self.assertIn(".sidebar-collapsed .btn-github {", css)
        self.assertIn(".sidebar-collapsed #globalLanguageSwitcher.switcher-docked", i18n_js)
        mobile_switcher = i18n_js[i18n_js.index("@media (max-width: 768px)") :]
        self.assertIn("position: static;", mobile_switcher)
        self.assertIn("width: 100%;", mobile_switcher)
        self.assertNotIn("position: fixed;", mobile_switcher)

    def test_scroll_is_not_globally_locked_on_html_body(self):
        client = self.app.test_client()
        css = self._get_text(client, "/static/css/main.css")
        normalized = css.replace("\r\n", "\n")
        self.assertNotRegex(
            normalized,
            re.compile(r"html\\s*\\{[^}]*overflow:\\s*hidden;", re.MULTILINE),
        )
        self.assertNotRegex(
            normalized,
            re.compile(r"body\\s*\\{[^}]*overflow:\\s*hidden;", re.MULTILINE),
        )

    def test_watchtower_i18n_keys_present(self):
        """验证 Watchtower/Docker API 更新相关新增的 i18n 翻译键存在"""
        client = self.app.test_client()
        i18n_js = self._get_text(client, "/static/js/i18n.js")
        main_js = load_frontend_app_js()

        # i18n.js 中应包含新增的翻译条目
        self.assertIn(
            "'Watchtower 检查完毕，当前已是最新版本': 'Watchtower check complete, already up to date'",
            i18n_js,
        )
        self.assertIn("'✅ 连通正常': '✅ Connection OK'", i18n_js)
        self.assertIn("'⏳ 测试中…': '⏳ Testing...'", i18n_js)
        self.assertIn("'基础': 'Basic'", i18n_js)
        self.assertIn("'临时邮箱': 'Temp Mailboxes'", i18n_js)
        self.assertIn("'API 安全': 'API Security'", i18n_js)
        self.assertIn("'自动化': 'Automation'", i18n_js)

        # main.js 中应使用 translateAppTextLocal 翻译 Watchtower 结果
        self.assertIn("translateAppTextLocal('✅ 连通正常')", main_js)
        self.assertIn("translateAppTextLocal('⏳ 测试中…')", main_js)
