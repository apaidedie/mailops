// split from external_api_ui.js → commands.js
        function getExternalApiCommandEndpointMap() {
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            const guideEndpoints = guide.endpoints && typeof guide.endpoints === 'object' ? guide.endpoints : {};
            return EXTERNAL_API_COMMAND_ENDPOINTS.reduce((acc, item) => {
                acc[item.key] = String(guideEndpoints[item.key] || item.path || '').trim();
                return acc;
            }, {});
        }

        function getExternalApiCommandMultiKeyCount(settings) {
            const directCount = Number(settings && settings.external_api_keys_count);
            if (!isNaN(directCount) && directCount > 0) return directCount;
            const keys = Array.isArray(settings && settings.external_api_keys) ? settings.external_api_keys : [];
            return keys.length;
        }

        function getExternalApiCommandAccessStatus(settings) {
            const multiKeyCount = getExternalApiCommandMultiKeyCount(settings);
            const hasLegacyKey = settings && settings.external_api_key_set === true;
            if (hasLegacyKey || multiKeyCount > 0) {
                return {
                    label: '可接入',
                    detail: hasLegacyKey ? '已配置 API Key' : '仅多 Key',
                    badgeClass: 'badge-green'
                };
            }
            return {
                label: '未配置 API Key',
                detail: '外部调用会被拒绝',
                badgeClass: 'badge-gold'
            };
        }

        function getExternalApiCommandRouteMode(settings) {
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const guideFilter = guide.provider_filter && typeof guide.provider_filter === 'object' ? guide.provider_filter : null;
            const diagnosticFilter = diagnostics.filter && typeof diagnostics.filter === 'object' ? diagnostics.filter : null;
            const filter = guideFilter || diagnosticFilter || {};
            const activeProviders = canonicalizeMailboxProviderAllowlistValues(
                Array.isArray(filter.active_providers)
                    ? filter.active_providers
                    : (Array.isArray(settings && settings.active_mailbox_providers) ? settings.active_mailbox_providers : [])
            ).filter(value => value !== 'auto');
            const isAllowlist = filter.active === true || String(filter.mode || '').trim().toLowerCase() === 'allowlist' || activeProviders.length > 0;
            const poolDefault = canonicalizeMailboxProviderAllowlistValue(
                String((settings && settings.pool_default_provider) || '').trim() || 'auto'
            ) || 'auto';
            const listSeparator = getUiLanguage() === 'en' ? ', ' : '、';
            const providerText = isAllowlist
                ? (activeProviders.slice(0, 4).join(listSeparator) || translateAppTextLocal('白名单'))
                : translateAppTextLocal('全部启用');
            return {
                value: translateAppTextLocal(isAllowlist ? '白名单' : '全部启用'),
                detail: `${translateAppTextLocal('领取默认')} ${poolDefault} · ${providerText}`
            };
        }

        function getExternalApiCommandSourcePriority() {
            const manifestPriority = getExternalIntegrationManifestSourcePriority();
            if (manifestPriority.length) return manifestPriority;
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            if (Array.isArray(guide.source_priority) && guide.source_priority.length) {
                return guide.source_priority.map(item => String(item || '').trim()).filter(Boolean);
            }
            const descriptor = getProviderTemplateDescriptor(mailboxProviderTemplateFormat);
            if (Array.isArray(descriptor.priority) && descriptor.priority.length) return descriptor.priority;
            return ['env', 'provider_config_file', 'settings', 'default'];
        }

        function getExternalApiCommandPoolStatus(settings) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            if (safeSettings.pool_external_enabled !== true) {
                return {
                    value: translateAppTextLocal('未启用'),
                    detail: translateAppTextLocal('Pool 端点关闭')
                };
            }
            const disabledEndpoints = [
                safeSettings.external_api_disable_pool_claim_random === true ? 'claim-random' : '',
                safeSettings.external_api_disable_pool_claim_release === true ? 'claim-release' : '',
                safeSettings.external_api_disable_pool_claim_complete === true ? 'claim-complete' : '',
                safeSettings.external_api_disable_pool_stats === true ? 'stats' : ''
            ].filter(Boolean);
            if (!disabledEndpoints.length) {
                return {
                    value: translateAppTextLocal('已启用'),
                    detail: translateAppTextLocal('全部端点可用')
                };
            }
            return {
                value: translateAppTextLocal('部分启用'),
                detail: `${translateAppTextLocal('已禁用')} ${disabledEndpoints.join(', ')}`
            };
        }

        function buildExternalApiStarterJavaScriptSnippet(endpointMap) {
            const endpoints = endpointMap || getExternalApiStarterEndpointMap();
            const auth = getExternalIntegrationManifestAuth();
            const steps = getExternalApiStarterDiscoverySteps(endpoints);
            const stepLines = steps.map(item => {
                const endpoint = appendExternalApiStarterQuery(item.endpoint, item.query);
                const method = String(item.method || 'GET').toUpperCase();
                const options = method && method !== 'GET' ? `, { method: ${formatExternalApiStarterStringLiteral(method)} }` : '';
                return `const ${normalizeExternalApiStarterStepIdentifier(item.step)} = await callExternal(${formatExternalApiStarterStringLiteral(endpoint)}${options});`;
            });
            return [
                `const baseUrl = ${formatExternalApiStarterStringLiteral(getExternalApiStarterBaseUrl())};`,
                `const apiKey = ${formatExternalApiStarterStringLiteral(auth.placeholder)};`,
                'const endpoints = {',
                `  capabilities: ${formatExternalApiStarterStringLiteral(endpoints.capabilities)},`,
                `  providers: ${formatExternalApiStarterStringLiteral(endpoints.providers)},`,
                `  mailboxes: ${formatExternalApiStarterStringLiteral(`${endpoints.mailboxes}?kind=all&provider=all`)}`,
                '};',
                '',
                'async function callExternal(path, options = {}) {',
                '  const url = /^https?:\\/\\//i.test(path) ? path : `${baseUrl}${path}`;',
                '  const response = await fetch(url, {',
                '    ...options,',
                '    headers: {',
                `      ${formatExternalApiStarterStringLiteral(auth.header)}: apiKey,`,
                '      "Content-Type": "application/json",',
                '      ...(options.headers || {})',
                '    }',
                '  });',
                '  if (!response.ok) throw new Error(`HTTP ${response.status}`);',
                '  return response.json();',
                '}',
                '',
                ...(stepLines.length ? stepLines : [
                    'const capabilities = await callExternal(endpoints.capabilities);',
                    'const providers = await callExternal(endpoints.providers);',
                    'const mailboxes = await callExternal(endpoints.mailboxes);'
                ])
            ].join('\n');
        }

        function buildExternalApiStarterPythonSnippet(endpointMap) {
            const endpoints = endpointMap || getExternalApiStarterEndpointMap();
            const auth = getExternalIntegrationManifestAuth();
            const steps = getExternalApiStarterDiscoverySteps(endpoints);
            const stepLines = steps.map(item => {
                const endpoint = appendExternalApiStarterQuery(item.endpoint, item.query);
                const method = String(item.method || 'GET').toUpperCase();
                const options = method && method !== 'GET' ? `, method=${formatExternalApiStarterStringLiteral(method)}` : '';
                return `${normalizeExternalApiStarterStepIdentifier(item.step)} = call_external(${formatExternalApiStarterStringLiteral(endpoint)}${options})`;
            });
            return [
                'import requests',
                '',
                `BASE_URL = ${formatExternalApiStarterStringLiteral(getExternalApiStarterBaseUrl())}`,
                `API_KEY = ${formatExternalApiStarterStringLiteral(auth.placeholder)}`,
                `AUTH_HEADER = ${formatExternalApiStarterStringLiteral(auth.header)}`,
                'ENDPOINTS = {',
                `    "capabilities": ${formatExternalApiStarterStringLiteral(endpoints.capabilities)},`,
                `    "providers": ${formatExternalApiStarterStringLiteral(endpoints.providers)},`,
                `    "mailboxes": ${formatExternalApiStarterStringLiteral(`${endpoints.mailboxes}?kind=all&provider=all`)},`,
                '}',
                '',
                'def external_url(path):',
                '    if path.startswith(("http://", "https://")):',
                '        return path',
                '    return f"{BASE_URL}{path}"',
                '',
                'def call_external(path, **kwargs):',
                '    response = requests.request(',
                '        kwargs.pop("method", "GET"),',
                '        external_url(path),',
                '        headers={AUTH_HEADER: API_KEY, **kwargs.pop("headers", {})},',
                '        timeout=30,',
                '        **kwargs,',
                '    )',
                '    response.raise_for_status()',
                '    return response.json()',
                '',
                ...(stepLines.length ? stepLines : [
                    'capabilities = call_external(ENDPOINTS["capabilities"])',
                    'providers = call_external(ENDPOINTS["providers"])',
                    'mailboxes = call_external(ENDPOINTS["mailboxes"])'
                ])
            ].join('\n');
        }

        function buildExternalApiStarterEnvSnippet(settings = {}) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const endpoints = getExternalApiStarterEndpointMap();
            const auth = getExternalIntegrationManifestAuth();
            const sourcePriority = getExternalApiCommandSourcePriority();
            const routeMode = getExternalApiCommandRouteMode(safeSettings);
            const poolDefault = canonicalizeMailboxProviderAllowlistValue(
                String(safeSettings.pool_default_provider || '').trim() || 'auto'
            ) || 'auto';
            const tempMailDefault = (typeof normalizeTempMailSettingsProviderName === 'function'
                ? normalizeTempMailSettingsProviderName(safeSettings.temp_mail_provider)
                : String(safeSettings.temp_mail_provider || '').trim()) || String(safeSettings.temp_mail_provider || '').trim();
            const activeProviders = canonicalizeMailboxProviderAllowlistValues(
                Array.isArray(safeSettings.active_mailbox_providers) ? safeSettings.active_mailbox_providers : []
            ).filter(value => value !== 'auto');
            const lines = [
                '# External API client',
                `OUTLOOK_EMAIL_EXTERNAL_API_BASE=${getExternalApiStarterBaseUrl()}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_KEY=${auth.placeholder}`,
                '',
                `# Provider selection priority: ${sourcePriority.join(' > ') || 'env > provider_config_file > settings > default'}`,
                `# Route mode: ${routeMode.value} / ${routeMode.detail}`,
                `TEMP_MAIL_PROVIDER=${tempMailDefault}`,
                `EXTERNAL_POOL_DEFAULT_PROVIDER=${poolDefault}`,
                `ACTIVE_MAILBOX_PROVIDERS=${activeProviders.join(',')}`,
                '',
                '# Discovery endpoints',
                `OUTLOOK_EMAIL_EXTERNAL_API_INTEGRATION_BUNDLE=${endpoints.integrationBundle}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_CAPABILITIES=${endpoints.capabilities}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_PROVIDERS=${endpoints.providers}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_MAILBOXES=${endpoints.mailboxes}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_OPENAPI=${endpoints.openapi}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_MAILBOX_SESSION_START=${endpoints.mailboxSessionStart}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_MAILBOX_SESSION_READ=${endpoints.mailboxSessionRead}`,
                `OUTLOOK_EMAIL_EXTERNAL_API_MAILBOX_SESSION_CLOSE=${endpoints.mailboxSessionClose}`,
            ];
            const manifestProviders = getExternalIntegrationManifestProviders();
            if (manifestProviders.length) {
                const manifestLines = [];
                manifestLines.push('', '# Provider env keys from current integration manifest');
                let manifestProviderHintCount = 0;
                manifestProviders.forEach(provider => {
                    const item = provider && typeof provider === 'object' ? provider : {};
                    const providerName = String(item.provider || '').trim();
                    const providerLabel = String(item.label || providerName || '').trim();
                    const envHints = Array.isArray(item.env) ? item.env.filter(envItem => envItem && typeof envItem === 'object') : [];
                    const hasRequestFields = item.request_fields && typeof item.request_fields === 'object' && Object.keys(item.request_fields).length;
                    if (!envHints.length && !hasRequestFields) return;
                    manifestProviderHintCount += 1;
                    manifestLines.push('', `# ${providerLabel}${providerName && providerName !== providerLabel ? ` (${providerName})` : ''}`);
                    envHints.forEach(hint => addExternalIntegrationManifestEnvLine(manifestLines, hint));
                    addExternalIntegrationRequestFieldLines(manifestLines, item.request_fields);
                });
                if (manifestProviderHintCount > 0) {
                    lines.push(...manifestLines);
                    return `${lines.join('\n')}\n`;
                }
            }
            const providers = getProviderIntegrationGuideProviders();
            if (!providers.length) return `${lines.join('\n')}\n`;

            lines.push('', '# Provider env keys from current catalog');
            providers.forEach(provider => {
                const item = provider && typeof provider === 'object' ? provider : {};
                const providerName = String(item.provider || '').trim();
                const providerLabel = String(item.label || providerName || '').trim();
                const configuration = item.configuration && typeof item.configuration === 'object' ? item.configuration : {};
                const envDefaults = configuration.env_defaults && typeof configuration.env_defaults === 'object' ? configuration.env_defaults : {};
                const envKeys = [
                    ...(Array.isArray(item.required_env) ? item.required_env : []),
                    ...(Array.isArray(item.optional_env) ? item.optional_env : []),
                    ...Object.keys(envDefaults),
                ].map(key => String(key || '').trim()).filter(Boolean);
                const hasRequestFields = (item.pool_claim_request && item.pool_claim_request.field)
                    || (item.task_temp_apply_request && item.task_temp_apply_request.field);
                if (!envKeys.length && !hasRequestFields) return;
                const secretKeys = getProviderIntegrationSecretKeySets(item).env;
                lines.push('', `# ${providerLabel}${providerName && providerName !== providerLabel ? ` (${providerName})` : ''}`);
                envKeys.forEach(key => addProviderIntegrationEnvLine(lines, key, envDefaults[key], secretKeys));
                if (item.pool_claim_request && item.pool_claim_request.field) {
                    lines.push(`# pool claim request: ${item.pool_claim_request.field}=${item.pool_claim_request.value || providerName}`);
                }
                if (item.task_temp_apply_request && item.task_temp_apply_request.field) {
                    lines.push(`# task temp apply request: ${item.task_temp_apply_request.field}=${item.task_temp_apply_request.value || providerName}`);
                }
            });
            return `${lines.join('\n')}\n`;
        }

        function getExternalApiStarterSnippet(mode = externalApiStarterMode, settings = externalApiSettingsSnapshot) {
            const normalizedMode = normalizeExternalApiStarterMode(mode);
            const endpointMap = getExternalApiStarterEndpointMap();
            if (normalizedMode === 'javascript') return buildExternalApiStarterJavaScriptSnippet(endpointMap);
            if (normalizedMode === 'python') return buildExternalApiStarterPythonSnippet(endpointMap);
            if (normalizedMode === 'env') return buildExternalApiStarterEnvSnippet(settings);
            return buildExternalApiStarterCurlSnippet(endpointMap);
        }

        function getExternalApiCommandStarterCommand() {
            return getExternalApiStarterSnippet('curl', externalApiSettingsSnapshot);
        }

        async function copyExternalApiWorkflowPlaybook() {
            const playbook = getExternalApiWorkflowPlaybookText(externalApiWorkflowKey);
            try {
                const ok = await copyTextToClipboard(playbook);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('工作流已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        async function copyExternalApiMailboxSessionLifecycle() {
            const lifecycle = getExternalApiMailboxSessionLifecycleText();
            try {
                const ok = await copyTextToClipboard(lifecycle);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('会话流程已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        function renderExternalApiCommandMetric(label, value, detail, tone = '') {
            return [
                `<div class="external-api-command-metric ${escapeHtml(tone)}">`,
                    `<span class="external-api-command-metric-label">${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<strong>${escapeHtml(value)}</strong>`,
                    detail ? `<span class="external-api-command-metric-detail">${escapeHtml(detail)}</span>` : '',
                '</div>'
            ].join('');
        }

        function renderExternalApiCommandEndpoint(item, endpointMap) {
            const path = endpointMap[item.key] || item.path;
            return [
                '<div class="external-api-command-endpoint">',
                    '<div class="external-api-command-endpoint-main">',
                        `<span class="external-api-command-method">${escapeHtml(item.method)}</span>`,
                        `<code>${escapeHtml(path)}</code>`,
                    '</div>',
                    `<div class="external-api-command-endpoint-meta"><span>${escapeHtml(translateAppTextLocal(item.label))}</span><small>${escapeHtml(translateAppTextLocal(item.detail))}</small></div>`,
                '</div>'
            ].join('');
        }

        function getExternalApiSmokeCommand() {
            return `OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url ${getExternalApiStarterBaseUrl() || '<your-base-url>'}`;
        }

        function getExternalApiBundleEndpointDescriptor(endpointMap = getExternalApiStarterEndpointMap()) {
            const source = endpointMap && typeof endpointMap === 'object' ? endpointMap : {};
            return {
                canonical: String(source.integrationBundle || source.integration_bundle || externalApiCanonicalPath('/integration-bundle')).trim() || externalApiCanonicalPath('/integration-bundle'),
                legacy: externalApiLegacyPath('/integration-bundle')
            };
        }

        function getExternalApiBundleCopyCommand() {
            const endpoints = getExternalApiBundleEndpointDescriptor();
            const auth = getExternalIntegrationManifestAuth();
            const authHeader = escapeExternalApiStarterDoubleQuoted(auth.curlHeader);
            const url = escapeExternalApiStarterDoubleQuoted(getExternalApiCommandUrl(endpoints.canonical));
            return `curl -s -H "${authHeader}" "${url}"`;
        }

        function getExternalApiBundleSummaryCards(settings = {}, state = 'ready', providerSummary = null) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const accessStatus = getExternalApiCommandAccessStatus(safeSettings);
            const multiKeyCount = getExternalApiCommandMultiKeyCount(safeSettings);
            const hasApiAccess = safeSettings.external_api_key_set === true || multiKeyCount > 0;
            const auth = getExternalIntegrationManifestAuth();
            const safeProviderSummary = providerSummary && typeof providerSummary === 'object'
                ? providerSummary
                : getExternalApiCommandProviderSummary(state);
            const mailboxSnapshot = getOperationalReadinessMailboxSnapshot();
            const totals = mailboxSnapshot.totals;
            const summary = mailboxSnapshot.summary;
            const accountCount = Number(totals.account_mailboxes || summary.account || 0);
            const tempCount = Number(totals.temp_mailboxes || summary.temp || 0);
            const totalMailboxes = Number(totals.mailboxes || summary.total || accountCount + tempCount || 0);
            const inventoryReady = mailboxSnapshot.status === 'ready';
            return [
                {
                    key: 'auth',
                    label: '认证占位',
                    value: translateAppTextLocal(accessStatus.label),
                    detail: `${auth.header}: ${auth.placeholder}`,
                    tone: hasApiAccess ? 'ready' : 'degraded'
                },
                {
                    key: 'bundle',
                    label: 'Discovery Bundle',
                    value: 'v1',
                    detail: translateAppTextLocal('一站式读取 endpoints、readiness、workflow 和 smoke checks'),
                    tone: 'ready'
                },
                {
                    key: 'providers',
                    label: 'Provider 就绪',
                    value: translateAppTextLocal(safeProviderSummary.value || '暂不可用'),
                    detail: safeProviderSummary.detail || translateAppTextLocal('Provider catalog 未加载'),
                    tone: safeProviderSummary.unavailable || safeProviderSummary.needsConfig > 0 ? 'degraded' : 'ready'
                },
                {
                    key: 'inventory',
                    label: '邮箱库存',
                    value: inventoryReady ? String(totalMailboxes) : translateAppTextLocal('待加载'),
                    detail: inventoryReady
                        ? `${translateAppTextLocal('账号')} ${accountCount} · ${translateAppTextLocal('临时邮箱')} ${tempCount}`
                        : translateAppTextLocal('正在读取邮箱目录快照…'),
                    tone: inventoryReady ? 'ready' : 'neutral'
                }
            ];
        }

        function renderExternalApiBundleSummaryCard(card) {
            const safeCard = card && typeof card === 'object' ? card : {};
            return [
                `<div class="external-api-bundle-card" data-tone="${escapeHtml(safeCard.tone || 'neutral')}" data-bundle-key="${escapeHtml(safeCard.key || '')}">`,
                    `<span>${escapeHtml(translateAppTextLocal(safeCard.label || ''))}</span>`,
                    `<strong>${escapeHtml(String(safeCard.value || ''))}</strong>`,
                    safeCard.detail ? `<small>${escapeHtml(safeCard.detail)}</small>` : '',
                '</div>'
            ].join('');
        }

        function renderExternalApiBundleEndpointRow(label, endpoint) {
            return [
                '<div class="external-api-bundle-route">',
                    '<div class="external-api-bundle-route-main">',
                        '<span class="external-api-command-method">GET</span>',
                        `<code>${escapeHtml(endpoint)}</code>`,
                    '</div>',
                    `<span>${escapeHtml(translateAppTextLocal(label))}</span>`,
                '</div>'
            ].join('');
        }

        function renderExternalApiBundleLaunchpad(settings = {}, state = 'ready', providerSummary = null) {
            const endpoints = getExternalApiBundleEndpointDescriptor();
            const command = getExternalApiBundleCopyCommand();
            const cards = getExternalApiBundleSummaryCards(settings, state, providerSummary);
            const actionPlan = getExternalApiActionPlan(settings, state, providerSummary);
            return [
                '<div class="external-api-bundle-launchpad">',
                    '<div class="external-api-bundle-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('Integration Readiness Bundle'))}</div>`,
                            `<div class="external-api-bundle-subtitle">${escapeHtml(translateAppTextLocal('外部服务优先读取这个一站式 payload'))}</div>`,
                        '</div>',
                        `<span class="badge badge-green">${escapeHtml(translateAppTextLocal('推荐入口'))}</span>`,
                    '</div>',
                    `<div class="external-api-bundle-summary">${cards.map(renderExternalApiBundleSummaryCard).join('')}</div>`,
                    renderExternalApiActionPlan(actionPlan),
                    '<div class="external-api-bundle-routes">',
                        renderExternalApiBundleEndpointRow('Canonical v1', endpoints.canonical),
                        renderExternalApiBundleEndpointRow('Legacy alias', endpoints.legacy),
                    '</div>',
                    '<div class="external-api-bundle-command-wrap">',
                        `<div class="external-api-smoke-label">${escapeHtml(translateAppTextLocal('只读 Bundle 命令'))}</div>`,
                        `<pre class="external-api-command-code external-api-bundle-command"><code>${escapeHtml(command)}</code></pre>`,
                        '<div class="external-api-command-actions">',
                            `<button type="button" class="external-api-command-copy external-api-bundle-copy" data-external-api-bundle-copy>${escapeHtml(translateAppTextLocal('复制 Bundle 命令'))}</button>`,
                        '</div>',
                    '</div>',
                '</div>'
            ].join('');
        }

        function formatExternalApiHandoffValue(value) {
            if (Array.isArray(value)) return value.map(formatExternalApiHandoffValue).filter(Boolean).join(', ');
            if (value && typeof value === 'object') {
                return Object.keys(value)
                    .map(key => `${key}=${formatExternalApiHandoffValue(value[key])}`)
                    .filter(item => item.trim() !== '=')
                    .join(', ');
            }
            return String(value === undefined || value === null ? '' : value).trim();
        }

        function getExternalApiHandoffDocs() {
            const manifest = getExternalIntegrationManifest();
            const manifestDocs = manifest.documentation && typeof manifest.documentation === 'object' ? manifest.documentation : {};
            const entries = manifestDocs.entries && typeof manifestDocs.entries === 'object' ? manifestDocs.entries : {};
            const docs = [];
            Object.keys(entries).forEach(key => {
                const item = entries[key] && typeof entries[key] === 'object' ? entries[key] : {};
                const label = String(item.label || key).trim();
                const target = String(item.endpoint || item.path || item.legacy_endpoint || '').trim();
                if (label && target) docs.push(`${label}: ${target}`);
            });
            if (!docs.some(line => line.includes(externalApiCanonicalPath('/docs')))) {
                docs.push(`External API docs: ${externalApiCanonicalPath('/docs')}`);
            }
            if (!docs.some(line => line.includes('docs/external-integration-quickstart.md'))) {
                docs.push('Quickstart docs: docs/external-integration-quickstart.md');
            }
            if (!docs.some(line => line.includes('docs/provider-onboarding.md'))) {
                docs.push('Provider onboarding: docs/provider-onboarding.md');
            }
            return docs;
        }

        function getExternalApiHandoffSections(settings = {}, state = 'ready', providerSummary = null) {
            const auth = getExternalIntegrationManifestAuth();
            const quickstart = getExternalIntegrationQuickstart();
            const endpointMap = getExternalApiStarterEndpointMap();
            const bundle = getExternalApiBundleEndpointDescriptor(endpointMap);
            const sequence = getExternalQuickstartSequence();
            const selectors = getExternalQuickstartSelectors();
            const sessionExamples = getExternalApiMailboxSessionRequestExamples();
            const actionPlan = getExternalApiActionPlan(settings, state, providerSummary);
            const quickstartRequests = getExternalQuickstartRequests();
            const discoverySteps = (sequence.length ? sequence : getExternalApiStarterDiscoverySteps(endpointMap)).map(item => {
                const method = String(item.method || 'GET').trim().toUpperCase() || 'GET';
                const endpoint = appendExternalApiStarterQuery(item.endpoint, item.query);
                return `${method} ${endpoint}`.trim();
            }).filter(Boolean);
            const selectorLines = Object.keys(selectors).map(key => {
                const selector = selectors[key] && typeof selectors[key] === 'object' ? selectors[key] : {};
                const field = String(selector.field || selector.request_field || '').trim();
                const allowed = Array.isArray(selector.allowed_values) && selector.allowed_values.length
                    ? ` (${selector.allowed_values.map(formatExternalApiHandoffValue).filter(Boolean).join(', ')})`
                    : '';
                return field ? `${key}: ${field}${allowed}` : '';
            }).filter(Boolean);
            if (!selectorLines.length) {
                selectorLines.push('pool_claim: provider');
                selectorLines.push('task_temp_apply: provider_name');
            }
            const requestLines = Object.keys(quickstartRequests).map(key => {
                const request = quickstartRequests[key];
                return request ? `${key}: ${getExternalQuickstartRequestLine(request)}` : '';
            }).filter(Boolean);
            return {
                baseUrl: getExternalApiStarterBaseUrl() || '<your-base-url>',
                auth: `${auth.header}: ${auth.placeholder}`,
                bundle,
                smokeCommand: getExternalApiSmokeCommand(),
                discoverySteps,
                selectorLines,
                sessionExamples,
                actionPlan,
                requestLines,
                docs: getExternalApiHandoffDocs(),
                quickstartAvailable: quickstart && Object.keys(quickstart).length > 0,
            };
        }

        function getExternalApiHandoffActionPlanLines(plan) {
            const safePlan = plan && typeof plan === 'object' ? plan : {};
            const items = Array.isArray(safePlan.items) ? safePlan.items.filter(item => item && typeof item === 'object') : [];
            if (!items.length) return ['- No local action items available.'];
            return items.map(item => {
                const priority = String(item.priority || 'medium').trim();
                const status = String(item.status || 'optional').trim();
                const title = String(item.title || item.key || 'Action').trim();
                const target = String(item.command || item.endpoint || item.docs || '').trim();
                return `- [${priority}/${status}] ${title}${target ? ` -> ${target}` : ''}`;
            });
        }

        function getExternalApiHandoffKitText(settings = externalApiSettingsSnapshot, state = 'ready', providerSummary = null) {
            const sections = getExternalApiHandoffSections(settings, state, providerSummary);
            const lines = [
                '# OutlookEmail Plus External Integration Handoff',
                '',
                '## Base URL',
                sections.baseUrl,
                '',
                '## Auth',
                `Header: ${sections.auth}`,
                'Value source: give the external service its own API key; do not paste admin UI secrets here.',
                '',
                '## Start Here',
                `Integration Bundle: GET ${getExternalApiCommandUrl(sections.bundle.canonical)}`,
                `Canonical path: ${sections.bundle.canonical}`,
                `Legacy alias: ${sections.bundle.legacy}`,
                `Smoke Check: ${sections.smokeCommand}`,
                '',
                '## Discovery Sequence',
                ...(sections.discoverySteps.length ? sections.discoverySteps.map((line, index) => `${index + 1}. ${line}`) : [
                    `1. GET ${externalApiCanonicalPath('/capabilities')}`,
                    `2. GET ${externalApiCanonicalPath('/providers')}`,
                    `3. GET ${externalApiCanonicalPath('/mailboxes')}?kind=all&provider=all`,
                ]),
                '',
                '## Provider Selectors',
                ...sections.selectorLines.map(line => `- ${line}`),
                '',
                '## Request Index',
                ...(sections.requestLines.length ? sections.requestLines.map(line => `- ${line}`) : [
                    `- mailbox_session_start: POST ${externalApiCanonicalPath('/mailbox-sessions/start')}`,
                    `- mailbox_session_read: POST ${externalApiCanonicalPath('/mailbox-sessions/read')}`,
                    `- mailbox_session_close: POST ${externalApiCanonicalPath('/mailbox-sessions/close')}`,
                ]),
                '',
                '## Mailbox Session',
                `[mailbox_session_start] ${getExternalQuickstartRequestLine(sections.sessionExamples.mailbox_session_start)}`,
                formatExternalQuickstartJson((sections.sessionExamples.mailbox_session_start || {}).body || {}),
                '',
                `[mailbox_session_read] ${getExternalQuickstartRequestLine(sections.sessionExamples.mailbox_session_read)}`,
                formatExternalQuickstartJson((sections.sessionExamples.mailbox_session_read || {}).body || {}),
                '',
                `[mailbox_session_close] ${getExternalQuickstartRequestLine(sections.sessionExamples.mailbox_session_close)}`,
                formatExternalQuickstartJson((sections.sessionExamples.mailbox_session_close || {}).body || {}),
                '',
                '## Local Action Plan',
                ...getExternalApiHandoffActionPlanLines(sections.actionPlan),
                '',
                '## Docs',
                ...sections.docs.map(line => `- ${line}`),
            ].filter(line => line !== undefined && line !== null);
            return `${lines.join('\n')}\n`;
        }

        function renderExternalApiHandoffKit(settings = {}, state = 'ready', providerSummary = null) {
            const sections = getExternalApiHandoffSections(settings, state, providerSummary);
            const preview = getExternalApiHandoffKitText(settings, state, providerSummary);
            const chips = [
                `${translateAppTextLocal('Bundle')} ${sections.bundle.canonical}`,
                sections.quickstartAvailable ? translateAppTextLocal('Quickstart') : translateAppTextLocal('Fallback quickstart'),
                `${translateAppTextLocal('Action Plan')} ${String((sections.actionPlan.summary || {}).total || (sections.actionPlan.items || []).length || 0)}`,
                'X-API-Key: <your-api-key>',
            ];
            return [
                '<div class="external-api-handoff-kit">',
                    '<div class="external-api-handoff-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('External Integration Handoff Kit'))}</div>`,
                            `<div class="external-api-handoff-subtitle">${escapeHtml(translateAppTextLocal('一键交给外部开发者的安全接入说明'))}</div>`,
                        '</div>',
                        `<button type="button" class="external-api-command-copy external-api-handoff-copy" data-external-api-handoff-copy>${escapeHtml(translateAppTextLocal('复制交接包'))}</button>`,
                    '</div>',
                    `<div class="external-api-handoff-chips">${chips.map(item => `<span class="external-api-handoff-chip">${escapeHtml(item)}</span>`).join('')}</div>`,
                    `<pre class="external-api-command-code external-api-handoff-preview"><code>${escapeHtml(preview)}</code></pre>`,
                '</div>'
            ].join('');
        }

        function renderExternalApiCommandCenter(settings = {}, state = 'ready') {
            const root = document.getElementById('externalApiCommandCenter');
            if (!root) return;
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            externalApiSettingsSnapshot = safeSettings;
            const renderState = state || 'ready';
            externalApiCommandRenderState = renderState;
            root.setAttribute('data-state', renderState);

            if (renderState === 'loading' && !Object.keys(safeSettings).length) {
                root.innerHTML = `<div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('正在读取外部 API 服务…'))}</div>`;
                return;
            }

            const accessStatus = getExternalApiCommandAccessStatus(safeSettings);
            const multiKeyCount = getExternalApiCommandMultiKeyCount(safeSettings);
            const providerSummary = getExternalApiCommandProviderSummary(renderState);
            const routeMode = getExternalApiCommandRouteMode(safeSettings);
            const sourcePriority = getExternalApiCommandSourcePriority();
            const endpointMap = getExternalApiCommandEndpointMap();
            externalApiStarterMode = normalizeExternalApiStarterMode(externalApiStarterMode);
            const starterSnippet = getExternalApiStarterSnippet(externalApiStarterMode, safeSettings);
            const poolStatus = getExternalApiCommandPoolStatus(safeSettings);
            const publicMode = safeSettings.external_api_public_mode === true;
            const sourcePriorityText = sourcePriority.length ? sourcePriority.join(' > ') : 'env > provider_config_file > settings > default';
            const providerRecipes = getExternalProviderSelectionRecipes();
            externalProviderRecipeKey = normalizeExternalProviderRecipeKey(externalProviderRecipeKey, providerRecipes);
            const workflowPlaybooks = getExternalApiWorkflowPlaybooks();
            externalApiWorkflowKey = normalizeExternalApiWorkflowKey(externalApiWorkflowKey, workflowPlaybooks);
            const providerNotice = providerSummary.unavailable
                ? `<div class="external-api-command-notice">${escapeHtml(translateAppTextLocal('Provider catalog 暂不可用，已保留外部 API 基础入口。'))}</div>`
                : '';
            const onboardingSteps = getExternalApiOnboardingSteps(safeSettings, renderState, providerSummary, poolStatus, endpointMap);

            root.innerHTML = [
                '<div class="external-api-command-head">',
                    '<div>',
                        `<div class="external-api-command-title">${escapeHtml(translateAppTextLocal('外部接入指挥台'))}</div>`,
                        `<div class="external-api-command-subtitle">${escapeHtml(translateAppTextLocal('统一暴露邮箱目录、Provider 路由、OpenAPI 与验证码读取入口'))}</div>`,
                    '</div>',
                    `<span class="badge ${escapeHtml(accessStatus.badgeClass)}">${escapeHtml(translateAppTextLocal(accessStatus.label))}</span>`,
                '</div>',
                renderExternalApiOnboardingChecklist(onboardingSteps),
                renderExternalApiSmokeCheckPanel(),
                renderExternalApiContractCheckPanel(),
                renderExternalApiBundleLaunchpad(safeSettings, renderState, providerSummary),
                renderExternalApiHandoffKit(safeSettings, renderState, providerSummary),
                renderExternalApiConsumerUsageConsole(safeSettings),
                '<div class="external-api-command-metrics">',
                    renderExternalApiCommandMetric('接入状态', translateAppTextLocal(accessStatus.label), translateAppTextLocal(accessStatus.detail), accessStatus.badgeClass),
                    renderExternalApiCommandMetric('多 Key', String(multiKeyCount), multiKeyCount > 0 ? translateAppTextLocal('已配置') : translateAppTextLocal('未配置')),
                    renderExternalApiCommandMetric('公网模式', translateAppTextLocal(publicMode ? '已启用' : '未启用'), publicMode ? translateAppTextLocal('启用额外公网策略') : translateAppTextLocal('仅 API Key 鉴权')),
                    renderExternalApiCommandMetric('External Pool', poolStatus.value, poolStatus.detail),
                    renderExternalApiCommandMetric('Provider 就绪', translateAppTextLocal(providerSummary.value), providerSummary.detail, providerSummary.unavailable ? 'badge-gold' : ''),
                    renderExternalApiCommandMetric('路由模式', routeMode.value, routeMode.detail),
                '</div>',
                renderOperationalReadinessConsole(safeSettings, renderState),
                renderExternalApiQuickstartCockpit(),
                renderExternalApiMailboxSessionLifecycle(),
                '<div class="external-api-command-body">',
                    '<div class="external-api-command-endpoints">',
                        `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('调用入口'))}</div>`,
                        EXTERNAL_API_COMMAND_ENDPOINTS.map(item => renderExternalApiCommandEndpoint(item, endpointMap)).join(''),
                    '</div>',
                    '<div class="external-api-command-snippet">',
                        `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('接入启动包'))}</div>`,
                        `<div class="external-api-command-priority"><span>${escapeHtml(translateAppTextLocal('来源优先级'))}</span><code>${escapeHtml(sourcePriorityText)}</code></div>`,
                        `<div class="external-api-starter-modes" role="group" aria-label="${escapeHtml(translateAppTextLocal('接入片段格式'))}">${EXTERNAL_API_STARTER_MODES.map(renderExternalApiStarterModeButton).join('')}</div>`,
                        `<pre class="external-api-command-code external-api-starter-code"><code>${escapeHtml(starterSnippet)}</code></pre>`,
                        '<div class="external-api-command-actions">',
                            `<button type="button" class="external-api-command-copy" data-external-api-command-copy>${escapeHtml(translateAppTextLocal('复制接入片段'))}</button>`,
                        '</div>',
                    '</div>',
                '</div>',
                renderExternalProviderRecipeGuide(providerRecipes),
                renderExternalApiWorkflowPlaybooks(workflowPlaybooks),
                providerNotice
            ].join('');
            syncExternalApiStarterModeButtons();
        }

        async function copyExternalApiQuickstart() {
            const quickstartText = getExternalApiQuickstartText();
            try {
                const ok = await copyTextToClipboard(quickstartText);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('Quickstart 已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        async function copyExternalApiSmokeCommand() {
            const smokeCommand = getExternalApiSmokeCommand();
            try {
                const ok = await copyTextToClipboard(smokeCommand);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('自检命令已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        async function copyExternalApiBundleCommand() {
            const command = getExternalApiBundleCopyCommand();
            try {
                const ok = await copyTextToClipboard(command);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('Bundle 命令已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        async function copyExternalApiHandoffKit() {
            const currentState = String(externalApiCommandRenderState || 'ready');
            const handoff = getExternalApiHandoffKitText(externalApiSettingsSnapshot, currentState === 'loading' ? 'ready' : currentState);
            try {
                const ok = await copyTextToClipboard(handoff);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('交接包已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        async function copyExternalApiCommandSnippet() {
            const command = getExternalApiStarterSnippet(externalApiStarterMode, externalApiSettingsSnapshot);
            try {
                const ok = await copyTextToClipboard(command);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('接入片段已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

