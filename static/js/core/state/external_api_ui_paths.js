// split from external_api_ui.js → paths.js
        function externalApiCanonicalPath(path = '') {
            const suffix = String(path || '').trim();
            if (!suffix) return EXTERNAL_API_CANONICAL_PREFIX;
            return `${EXTERNAL_API_CANONICAL_PREFIX}${suffix.startsWith('/') ? suffix : `/${suffix}`}`;
        }

        function externalApiLegacyPath(path = '') {
            const suffix = String(path || '').trim();
            if (!suffix) return EXTERNAL_API_LEGACY_PREFIX;
            return `${EXTERNAL_API_LEGACY_PREFIX}${suffix.startsWith('/') ? suffix : `/${suffix}`}`;
        }

        const EXTERNAL_API_COMMAND_ENDPOINTS = [
            { key: 'integration_bundle', label: 'Integration Readiness Bundle', method: 'GET', path: externalApiCanonicalPath('/integration-bundle'), detail: '一站式读取接入就绪状态' },
            { key: 'capabilities', label: '能力发现', method: 'GET', path: externalApiCanonicalPath('/capabilities'), detail: '读取运行时能力与 endpoint map' },
            { key: 'openapi', label: 'OpenAPI', method: 'GET', path: externalApiCanonicalPath('/openapi.json'), detail: '生成客户端和校验外部契约' },
            { key: 'mailboxes', label: '统一邮箱目录', method: 'GET', path: externalApiCanonicalPath('/mailboxes'), detail: '列出 Outlook、IMAP 与临时邮箱' },
            { key: 'providers', label: 'Provider 目录', method: 'GET', path: externalApiCanonicalPath('/providers'), detail: '发现 provider、路由与部署模板' },
            { key: 'mailbox_session_start', label: '启动邮箱会话', method: 'POST', path: externalApiCanonicalPath('/mailbox-sessions/start'), detail: '统一创建可读邮箱会话' },
            { key: 'mailbox_session_read', label: '读取邮箱会话', method: 'POST', path: externalApiCanonicalPath('/mailbox-sessions/read'), detail: '按会话读取邮件、验证码或原文' },
            { key: 'mailbox_session_close', label: '关闭邮箱会话', method: 'POST', path: externalApiCanonicalPath('/mailbox-sessions/close'), detail: '完成或释放会话生命周期' },
            { key: 'pool_claim_random', label: '随机领取', method: 'POST', path: externalApiCanonicalPath('/pool/claim-random'), detail: '从邮箱池领取可用邮箱' },
            { key: 'temp_mail_apply', label: '任务临时邮箱', method: 'POST', path: externalApiCanonicalPath('/temp-emails/apply'), detail: '为外部任务申请临时邮箱' }
        ];

        const EXTERNAL_API_STARTER_MODES = [
            { key: 'curl', label: 'curl' },
            { key: 'javascript', label: 'JavaScript' },
            { key: 'python', label: 'Python' },
            { key: 'env', label: '.env' }
        ];

        const DEMO_WORKSPACE_ACTIONS = [
            { key: 'overview', label: '总览', page: 'dashboard', tab: 'summary' },
            { key: 'unified_mailbox', label: '统一邮箱', page: 'mailbox' },
            { key: 'temp_mailboxes', label: '临时邮箱', page: 'temp-emails' },
            { key: 'external_api', label: '对外 API', page: 'dashboard', tab: 'external-api' },
            { key: 'providers', label: 'Provider 设置', page: 'settings', tab: 'api-security' }
        ];

        // 缓存与信任模式
        let emailListCache = {};
        let currentEmailDetail = null;
        let isTrustedMode = false;

        // 轮询相关（Phase 2: 变量保留用于设置读写，实际轮询由统一引擎处理）
        let maxPollingCount = 5;
        let pollingInterval = 10;
        let autoPollingEnabled = false;
        // [Phase 3] compact 独立变量已废弃，统一使用上方标准字段

        // 导航状态
        let currentPage = 'dashboard';
        let accountPanelDensitySyncHandle = null;

        // ==================== 布局状态管理 (ui_layout_v2) ====================
        // 布局状态缓存
        let uiLayoutV2 = null;
        let layoutSaveDebounceTimer = null;
        const LAYOUT_SAVE_DEBOUNCE_MS = 2000;

        // 默认布局状态
        function getExternalApiCommandUrl(path) {
            const value = String(path || '').trim();
            if (!value) return '';
            if (/^https?:\/\//i.test(value)) return value;
            const origin = (typeof window !== 'undefined' && window.location && window.location.origin)
                ? window.location.origin
                : 'http://localhost:5000';
            return `${origin}${value.startsWith('/') ? value : `/${value}`}`;
        }

        function getExternalApiStarterBaseUrl() {
            if (typeof window !== 'undefined' && window.location && window.location.origin) {
                return window.location.origin;
            }
            return 'http://localhost:5000';
        }

        function buildExternalApiStarterCurlSnippet(endpointMap) {
            const endpoints = endpointMap || getExternalApiStarterEndpointMap();
            const auth = getExternalIntegrationManifestAuth();
            const authHeader = escapeExternalApiStarterDoubleQuoted(auth.curlHeader);
            const steps = getExternalApiStarterDiscoverySteps(endpoints);
            if (steps.length) {
                return steps.map(item => {
                    const url = escapeExternalApiStarterDoubleQuoted(getExternalApiCommandUrl(appendExternalApiStarterQuery(item.endpoint, item.query)));
                    const method = String(item.method || 'GET').toUpperCase();
                    const methodArg = method && method !== 'GET' ? ` -X ${method}` : '';
                    return `curl -s${methodArg} -H "${authHeader}" "${url}"`;
                }).join('\n');
            }
            return [
                `curl -s -H "${authHeader}" "${escapeExternalApiStarterDoubleQuoted(getExternalApiCommandUrl(endpoints.capabilities))}"`,
                `curl -s -H "${authHeader}" "${escapeExternalApiStarterDoubleQuoted(getExternalApiCommandUrl(endpoints.providers))}"`,
                `curl -s -H "${authHeader}" "${escapeExternalApiStarterDoubleQuoted(`${getExternalApiCommandUrl(endpoints.mailboxes)}?kind=all&provider=all`)}"`
            ].join('\n');
        }

