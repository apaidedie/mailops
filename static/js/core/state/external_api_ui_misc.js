// split from external_api_ui.js → misc.js
        function normalizeExternalApiStarterMode(mode) {
            const normalized = String(mode || 'curl').trim().toLowerCase();
            return EXTERNAL_API_STARTER_MODES.some(item => item.key === normalized) ? normalized : 'curl';
        }

        function getExternalApiStarterDiscoverySteps(endpointMap) {
            const discovery = getExternalIntegrationManifestDiscovery();
            const manifestSteps = Array.isArray(discovery.recommended_sequence)
                ? discovery.recommended_sequence.filter(item => item && typeof item === 'object')
                : [];
            if (manifestSteps.length) {
                return manifestSteps.map(item => {
                    const step = String(item.step || '').trim();
                    const fallbackEndpoint = step === 'pool_claim_random'
                        ? endpointMap.poolClaimRandom
                        : (step === 'temp_mail_apply' ? endpointMap.tempMailApply : endpointMap[step]);
                    return {
                        step,
                        method: String(item.method || 'GET').trim().toUpperCase() || 'GET',
                        endpoint: String(item.endpoint || fallbackEndpoint || '').trim(),
                        query: item.query && typeof item.query === 'object' ? item.query : null
                    };
                }).filter(item => item.step && item.endpoint);
            }
            return [
                { step: 'capabilities', method: 'GET', endpoint: endpointMap.capabilities, query: null },
                { step: 'providers', method: 'GET', endpoint: endpointMap.providers, query: null },
                { step: 'mailboxes', method: 'GET', endpoint: endpointMap.mailboxes, query: { kind: 'all', provider: 'all' } }
            ];
        }

        function appendExternalApiStarterQuery(path, query) {
            const value = String(path || '').trim();
            const queryObject = query && typeof query === 'object' ? query : {};
            const params = [];
            Object.keys(queryObject).forEach(key => {
                const queryKey = String(key || '').trim();
                const queryValue = queryObject[key];
                if (!queryKey || queryValue === undefined || queryValue === null) return;
                params.push(`${encodeURIComponent(queryKey)}=${encodeURIComponent(String(queryValue))}`);
            });
            if (!params.length) return value;
            return `${value}${value.includes('?') ? '&' : '?'}${params.join('&')}`;
        }

        function formatExternalApiStarterStringLiteral(value) {
            return JSON.stringify(String(value === undefined || value === null ? '' : value));
        }

        function normalizeExternalApiStarterStepIdentifier(value) {
            const normalized = String(value || '').trim().replace(/[^A-Za-z0-9_]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
            if (!normalized) return 'step';
            return /^[A-Za-z_]/.test(normalized) ? normalized : `step_${normalized}`;
        }

        function escapeExternalApiStarterDoubleQuoted(value) {
            return String(value === undefined || value === null ? '' : value)
                .replace(/\\/g, '\\\\')
                .replace(/"/g, '\\"');
        }

        function getExternalApiStarterEndpointMap() {
            const discovery = getExternalIntegrationManifestDiscovery();
            const manifestEndpoints = discovery.endpoints && typeof discovery.endpoints === 'object' ? discovery.endpoints : {};
            const endpoints = getExternalApiCommandEndpointMap();
            return {
                capabilities: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'capabilities', endpoints.capabilities || externalApiCanonicalPath('/capabilities')),
                integrationBundle: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'integration_bundle', endpoints.integration_bundle || externalApiCanonicalPath('/integration-bundle')),
                providers: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'providers', endpoints.providers || externalApiCanonicalPath('/providers')),
                mailboxes: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'mailboxes', endpoints.mailboxes || externalApiCanonicalPath('/mailboxes')),
                openapi: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'openapi', endpoints.openapi || externalApiCanonicalPath('/openapi.json')),
                poolClaimRandom: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'pool_claim_random', endpoints.pool_claim_random || externalApiCanonicalPath('/pool/claim-random')),
                poolClaimRelease: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'pool_claim_release', endpoints.pool_claim_release || externalApiCanonicalPath('/pool/claim-release')),
                poolClaimComplete: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'pool_claim_complete', endpoints.pool_claim_complete || externalApiCanonicalPath('/pool/claim-complete')),
                messages: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'messages', endpoints.messages || externalApiCanonicalPath('/messages')),
                verificationCode: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'verification_code', endpoints.verification_code || externalApiCanonicalPath('/verification-code')),
                mailboxSessionStart: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'mailbox_session_start', endpoints.mailbox_session_start || externalApiCanonicalPath('/mailbox-sessions/start')),
                mailboxSessionRead: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'mailbox_session_read', endpoints.mailbox_session_read || externalApiCanonicalPath('/mailbox-sessions/read')),
                mailboxSessionClose: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'mailbox_session_close', endpoints.mailbox_session_close || externalApiCanonicalPath('/mailbox-sessions/close')),
                tempMailApply: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'temp_mail_apply', endpoints.temp_mail_apply || externalApiCanonicalPath('/temp-emails/apply')),
                tempMailFinish: getExternalApiStarterManifestEndpoint(manifestEndpoints, 'temp_mail_finish', endpoints.temp_mail_finish || externalApiCanonicalPath('/temp-emails/{task_token}/finish'))
            };
        }

        function syncExternalApiStarterModeButtons() {
            externalApiStarterMode = normalizeExternalApiStarterMode(externalApiStarterMode);
            document.querySelectorAll('[data-external-api-starter-mode]').forEach(button => {
                const active = normalizeExternalApiStarterMode(button.getAttribute('data-external-api-starter-mode')) === externalApiStarterMode;
                button.classList.toggle('active', active);
                button.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
        }

        function setExternalApiStarterMode(mode) {
            externalApiStarterMode = normalizeExternalApiStarterMode(mode);
            const root = document.getElementById('externalApiCommandCenter');
            const currentState = root ? String(root.getAttribute('data-state') || 'ready') : 'ready';
            renderExternalApiCommandCenter(externalApiSettingsSnapshot, currentState === 'loading' ? 'ready' : currentState);
        }

        function getExternalApiMailboxSessionRequestExamples() {
            const requests = getExternalQuickstartRequests();
            const endpointMap = getExternalApiStarterEndpointMap();
            const fallback = {
                mailbox_session_start: {
                    method: 'POST',
                    endpoint: endpointMap.mailboxSessionStart,
                    body: {
                        caller_id: '<caller-id>',
                        task_id: '<task-id>',
                        source_strategy: 'pool_first',
                        provider: '<provider-or-auto>',
                        provider_name: '<provider-name>'
                    }
                },
                mailbox_session_read: {
                    method: 'POST',
                    endpoint: endpointMap.mailboxSessionRead,
                    body: {
                        session_type: '<session-type-from-start-response>',
                        read_action: 'verification_code',
                        caller_id: '<caller-id>',
                        task_id: '<task-id>',
                        email: '<email>',
                        claim_token: '<claim-token>',
                        task_token: '<task-token>',
                        since_minutes: 10
                    }
                },
                mailbox_session_close: {
                    method: 'POST',
                    endpoint: endpointMap.mailboxSessionClose,
                    body: {
                        session_type: '<session-type-from-start-response>',
                        account_id: '<account-id>',
                        claim_token: '<claim-token>',
                        task_token: '<task-token>',
                        caller_id: '<caller-id>',
                        task_id: '<task-id>',
                        result: 'success',
                        detail: ''
                    }
                }
            };
            return {
                mailbox_session_start: requests.mailbox_session_start || fallback.mailbox_session_start,
                mailbox_session_read: requests.mailbox_session_read || fallback.mailbox_session_read,
                mailbox_session_close: requests.mailbox_session_close || fallback.mailbox_session_close,
            };
        }

        function getExternalApiMailboxSessionReadModes() {
            const workflow = getExternalApiMailboxSessionWorkflow();
            const readStep = workflow && Array.isArray(workflow.steps)
                ? workflow.steps.find(step => step && (step.key === 'read_session' || String(step.endpoint || '').includes('/mailbox-sessions/read')))
                : null;
            const request = readStep && readStep.request && typeof readStep.request === 'object' ? readStep.request : {};
            const values = Array.isArray(request.read_action_values) ? request.read_action_values : [];
            return values.map(item => String(item || '').trim()).filter(Boolean).slice(0, 7);
        }

        function getExternalApiMailboxSessionLifecycleText() {
            const auth = getExternalIntegrationManifestAuth();
            const examples = getExternalApiMailboxSessionRequestExamples();
            const readModes = getExternalApiMailboxSessionReadModes();
            const lines = [
                '# Mailbox session lifecycle',
                `# Auth: ${auth.header}: ${auth.placeholder}`,
                '',
                `[start] ${getExternalQuickstartRequestLine(examples.mailbox_session_start)}`,
                formatExternalQuickstartJson((examples.mailbox_session_start || {}).body || {}),
                '',
                `[read] ${getExternalQuickstartRequestLine(examples.mailbox_session_read)}`,
                '# pool_claim session read',
                formatExternalQuickstartJson({
                    session_type: 'pool_claim',
                    read_action: 'verification_code',
                    caller_id: '<caller-id>',
                    task_id: '<task-id>',
                    email: '<email>',
                    claim_token: '<claim-token>',
                    since_minutes: 10,
                }),
                '',
                '# task_temp_mailbox session read',
                formatExternalQuickstartJson({
                    session_type: 'task_temp_mailbox',
                    read_action: 'latest_message',
                    caller_id: '<caller-id>',
                    task_id: '<task-id>',
                    email: '<email>',
                    task_token: '<task-token>',
                    since_minutes: 10,
                }),
                readModes.length ? `# read_action values: ${readModes.join(', ')}` : '',
                '',
                `[close] ${getExternalQuickstartRequestLine(examples.mailbox_session_close)}`,
                formatExternalQuickstartJson((examples.mailbox_session_close || {}).body || {}),
            ].filter(line => line !== '');
            return `${lines.join('\n')}\n`;
        }

        function getExternalApiOnboardingSteps(settings, renderState, providerSummary, poolStatus, endpointMap) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const safeProviderSummary = providerSummary && typeof providerSummary === 'object'
                ? providerSummary
                : getExternalApiCommandProviderSummary(renderState || 'ready');
            const safePoolStatus = poolStatus && typeof poolStatus === 'object'
                ? poolStatus
                : getExternalApiCommandPoolStatus(safeSettings);
            const safeEndpointMap = endpointMap && typeof endpointMap === 'object'
                ? endpointMap
                : getExternalApiCommandEndpointMap();
            const multiKeyCount = getExternalApiCommandMultiKeyCount(safeSettings);
            const hasAnyApiKey = safeSettings.external_api_key_set === true || multiKeyCount > 0;
            const poolEnabled = safeSettings.pool_external_enabled === true;
            const poolPartial = poolEnabled && [
                safeSettings.external_api_disable_pool_claim_random,
                safeSettings.external_api_disable_pool_claim_release,
                safeSettings.external_api_disable_pool_claim_complete,
                safeSettings.external_api_disable_pool_stats
            ].some(value => value === true);
            const discoveryEndpoint = String(safeEndpointMap.capabilities || safeEndpointMap.openapi || externalApiCanonicalPath('/capabilities')).trim();

            return [
                {
                    label: 'API Key',
                    status: hasAnyApiKey ? '已完成' : '待处理',
                    detail: hasAnyApiKey ? '已可使用 X-API-Key 调用' : '生成 API Key 后保存设置',
                    tone: hasAnyApiKey ? 'done' : 'warning'
                },
                {
                    label: '多 Key',
                    status: multiKeyCount > 0 ? '已配置' : '可选',
                    detail: multiKeyCount > 0 ? `${multiKeyCount} ${translateAppTextLocal('个调用方 Key 可用')}` : '可选：配置多调用方 Key',
                    tone: multiKeyCount > 0 ? 'done' : 'neutral'
                },
                {
                    label: 'External Pool',
                    status: poolEnabled ? (poolPartial ? '部分启用' : '已启用') : '按需启用',
                    detail: poolEnabled ? safePoolStatus.detail : 'Pool 端点未启用，不影响目录和临时邮箱创建',
                    tone: poolEnabled ? (poolPartial ? 'partial' : 'done') : 'neutral'
                },
                {
                    label: 'Provider catalog',
                    status: safeProviderSummary.unavailable ? '需检查' : '已加载',
                    detail: safeProviderSummary.unavailable ? 'Provider catalog 需要检查' : 'Provider catalog 已加载',
                    tone: safeProviderSummary.unavailable ? 'warning' : 'done'
                },
                {
                    label: 'Discovery 入口',
                    status: discoveryEndpoint ? '可发现' : '需检查',
                    detail: discoveryEndpoint ? '外部服务先读取能力发现或 OpenAPI' : '就绪入口需要检查',
                    tone: discoveryEndpoint ? 'done' : 'warning'
                }
            ];
        }

        function getExternalApiSmokeCoverageItems() {
            return [
                { key: 'integration_bundle', label: 'Bundle', endpoint: externalApiCanonicalPath('/integration-bundle') },
                { key: 'health', label: 'Health', endpoint: externalApiCanonicalPath('/health') },
                { key: 'capabilities', label: 'Capabilities', endpoint: externalApiCanonicalPath('/capabilities') },
                { key: 'providers', label: 'Providers', endpoint: externalApiCanonicalPath('/providers') },
                { key: 'mailboxes', label: 'Mailboxes', endpoint: `${externalApiCanonicalPath('/mailboxes')}?page_size=1` },
                { key: 'openapi', label: 'OpenAPI', endpoint: externalApiCanonicalPath('/openapi.json') }
            ];
        }

        function getExternalApiActionPlan(settings = {}, state = 'ready', providerSummary = null) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const renderState = String(state || 'ready').trim() || 'ready';
            const endpointMap = getExternalApiStarterEndpointMap();
            const safeProviderSummary = providerSummary && typeof providerSummary === 'object'
                ? providerSummary
                : getExternalApiCommandProviderSummary(renderState);
            const poolStatus = getExternalApiCommandPoolStatus(safeSettings);
            const mailboxSnapshot = getOperationalReadinessMailboxSnapshot();
            const items = [];
            const hasProviderConfigGap = safeProviderSummary.unavailable || Number(safeProviderSummary.needsConfig || 0) > 0;
            const poolDisabled = safeSettings.pool_external_enabled !== true;
            const mailboxNeedsProbe = ['loading', 'error'].includes(String(mailboxSnapshot.status || '')) || Number(mailboxSnapshot.totals.mailboxes || mailboxSnapshot.summary.total || 0) <= 0;
            const isReady = !hasProviderConfigGap && !poolDisabled && !mailboxNeedsProbe && !String(poolStatus.value || '').includes(translateAppTextLocal('部分启用'));

            if (hasProviderConfigGap) {
                items.push({
                    key: 'configure_providers',
                    priority: 'high',
                    status: 'action_required',
                    blocking: true,
                    title: '配置缺失 Provider',
                    detail: safeProviderSummary.detail || translateAppTextLocal('Provider catalog 需要检查'),
                    endpoint: endpointMap.providers || externalApiCanonicalPath('/providers'),
                    docs: 'docs/provider-onboarding.md'
                });
            }
            if (poolDisabled) {
                items.push({
                    key: 'enable_external_pool',
                    priority: 'medium',
                    status: 'optional',
                    blocking: false,
                    title: '按需启用 External Pool',
                    detail: poolStatus.detail || translateAppTextLocal('Pool 端点关闭'),
                    endpoint: endpointMap.poolClaimRandom || externalApiCanonicalPath('/pool/claim-random'),
                    docs: 'docs/external-integration-quickstart.md'
                });
            }
            if (mailboxNeedsProbe) {
                items.push({
                    key: 'probe_mailbox_directory',
                    priority: 'medium',
                    status: mailboxSnapshot.status === 'error' ? 'action_required' : 'optional',
                    blocking: mailboxSnapshot.status === 'error',
                    title: '探测统一邮箱目录',
                    detail: translateAppTextLocal('确认当前 API Key 可见的 Outlook、IMAP、Pool 与临时邮箱库存'),
                    endpoint: endpointMap.mailboxes || externalApiCanonicalPath('/mailboxes'),
                    docs: 'docs/external-integration-quickstart.md'
                });
            }
            items.push({
                key: 'run_smoke_check',
                priority: 'high',
                status: 'ready',
                blocking: false,
                title: '运行只读 Smoke Check',
                detail: translateAppTextLocal('部署前验证 discovery、OpenAPI、Provider 与密钥安全'),
                endpoint: endpointMap.integrationBundle || externalApiCanonicalPath('/integration-bundle'),
                command: getExternalApiSmokeCommand(),
                docs: 'docs/external-integration-quickstart.md'
            });
            items.push({
                key: 'generate_client',
                priority: 'medium',
                status: 'ready',
                blocking: false,
                title: '生成或刷新客户端',
                detail: translateAppTextLocal('使用 canonical OpenAPI 生成外部服务 SDK'),
                endpoint: endpointMap.openapi || externalApiCanonicalPath('/openapi.json'),
                docs: 'docs/external-integration-quickstart.md'
            });
            items.push({
                key: 'start_mailbox_session',
                priority: 'high',
                status: isReady ? 'ready' : 'blocked',
                blocking: false,
                title: '启动统一邮箱会话',
                detail: translateAppTextLocal('用 mailbox session 屏蔽 Pool 与临时邮箱 Provider 差异'),
                endpoint: endpointMap.mailboxSessionStart || externalApiCanonicalPath('/mailbox-sessions/start'),
                docs: 'docs/external-integration-quickstart.md'
            });
            const deduped = [];
            const seen = new Set();
            items.forEach(item => {
                const key = String(item.key || '').trim();
                if (!key || seen.has(key)) return;
                seen.add(key);
                deduped.push(item);
            });
            return {
                version: 1,
                status: isReady ? 'ready' : (hasProviderConfigGap || mailboxSnapshot.status === 'error' ? 'needs_config' : 'degraded'),
                summary: {
                    total: deduped.length,
                    blocking: deduped.filter(item => item.blocking === true).length,
                    high: deduped.filter(item => item.priority === 'high').length,
                    medium: deduped.filter(item => item.priority === 'medium').length,
                    low: deduped.filter(item => item.priority === 'low').length
                },
                items: deduped
            };
        }

        function normalizeExternalApiConsumerUsageCount(value) {
            const numeric = Number(value);
            return Number.isFinite(numeric) && numeric > 0 ? Math.floor(numeric) : 0;
        }

        function normalizeExternalApiConsumerUsageBool(value, defaultValue = false) {
            if (value === true || value === 'true' || value === 1 || value === '1') return true;
            if (value === false || value === 'false' || value === 0 || value === '0') return false;
            return defaultValue;
        }

        function getExternalApiConsumerUsageItems(settings = {}) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const keys = Array.isArray(safeSettings.external_api_keys) ? safeSettings.external_api_keys : [];
            return keys.map((item, index) => {
                const source = item && typeof item === 'object' ? item : {};
                const allowedEmails = Array.isArray(source.allowed_emails)
                    ? source.allowed_emails.map(value => String(value || '').trim()).filter(Boolean)
                    : [];
                const enabled = normalizeExternalApiConsumerUsageBool(source.enabled, true);
                const poolAccess = normalizeExternalApiConsumerUsageBool(source.pool_access, false);
                const todayTotal = normalizeExternalApiConsumerUsageCount(source.today_total_count);
                const todaySuccess = normalizeExternalApiConsumerUsageCount(source.today_success_count);
                const todayError = normalizeExternalApiConsumerUsageCount(source.today_error_count);
                const consumerKey = String(source.consumer_key || (source.id ? `key:${source.id}` : '')).trim();
                const name = String(source.name || '').trim();
                const lastUsedAt = String(source.today_last_used_at || source.last_used_at || '').trim();
                return {
                    index,
                    name: name || consumerKey || `Consumer ${index + 1}`,
                    consumerKey: consumerKey || `consumer:${index + 1}`,
                    enabled,
                    poolAccess,
                    allowedEmails,
                    todayTotal,
                    todaySuccess,
                    todayError,
                    lastUsedAt,
                };
            });
        }

        function getExternalApiConsumerUsageTone(consumer) {
            const safeConsumer = consumer && typeof consumer === 'object' ? consumer : {};
            if (safeConsumer.enabled === false) return 'disabled';
            if (Number(safeConsumer.todayError || 0) > 0) return 'danger';
            if (Number(safeConsumer.todayTotal || 0) <= 0) return 'warning';
            return 'ready';
        }

        function getExternalApiConsumerUsageStatusLabel(tone) {
            const normalized = String(tone || 'warning').trim().toLowerCase();
            if (normalized === 'ready') return '今日正常';
            if (normalized === 'danger') return '今日有错误';
            if (normalized === 'disabled') return '已禁用';
            return '今日未调用';
        }

        function getExternalApiConsumerUsageBadgeClass(tone) {
            const normalized = String(tone || 'warning').trim().toLowerCase();
            if (normalized === 'ready') return 'badge-green';
            if (normalized === 'danger') return 'badge-red';
            if (normalized === 'disabled') return 'badge-gray';
            return 'badge-gold';
        }

        function getExternalApiConsumerScopeText(consumer) {
            const allowedEmails = Array.isArray(consumer && consumer.allowedEmails) ? consumer.allowedEmails : [];
            if (!allowedEmails.length) return translateAppTextLocal('全部邮箱');
            if (allowedEmails.length === 1) return allowedEmails[0];
            return `${allowedEmails.length} ${translateAppTextLocal('个邮箱')}`;
        }

        function formatExternalApiConsumerLastUsed(value) {
            const lastUsedAt = String(value || '').trim();
            if (!lastUsedAt) return translateAppTextLocal('今天未调用');
            return formatUiDateTime(lastUsedAt, { fallback: lastUsedAt, includeSeconds: false });
        }

        function getExternalApiConsumerUsageSummary(settings = {}) {
            const consumers = getExternalApiConsumerUsageItems(settings);
            const enabled = consumers.filter(item => item.enabled !== false).length;
            const usedToday = consumers.filter(item => Number(item.todayTotal || 0) > 0).length;
            const errorsToday = consumers.filter(item => Number(item.todayError || 0) > 0).length;
            return {
                consumers,
                total: consumers.length,
                enabled,
                usedToday,
                errorsToday,
                successToday: consumers.reduce((sum, item) => sum + Number(item.todaySuccess || 0), 0),
                totalToday: consumers.reduce((sum, item) => sum + Number(item.todayTotal || 0), 0),
            };
        }

