// split from mailboxes.js → workspace.js
        function translateUnifiedText(text) {
            return typeof translateAppTextLocal === 'function' ? translateAppTextLocal(text) : text;
        }

        function normalizeUnifiedWorkspaceView(view) {
            const normalized = String(view || '').trim().toLowerCase();
            return normalized === 'diagnostics' ? 'diagnostics' : 'inbox';
        }

        function setUnifiedWorkspaceView(view) {
            unifiedMailboxState.workspaceView = normalizeUnifiedWorkspaceView(view);
            renderUnifiedWorkspaceViewSwitch();
        }

        function getUnifiedDefaultGroupName(kind) {
            const normalizedKind = String(kind || '').trim().toLowerCase();
            if (normalizedKind === 'account') return translateUnifiedText('默认分组');
            return getUnifiedKindLabel(normalizedKind);
        }

        function getUnifiedSelectLabel(selectId, fallback = '') {
            const select = document.getElementById(selectId);
            if (!select) return fallback;
            const option = select.options && select.selectedIndex >= 0 ? select.options[select.selectedIndex] : null;
            return String((option && option.textContent) || fallback || '').trim();
        }

        function setUnifiedRefreshBusy(isBusy) {
            const button = document.getElementById('unifiedMailboxRefreshBtn');
            if (!button) return;
            button.disabled = Boolean(isBusy);
            if (isBusy) {
                button.setAttribute('aria-busy', 'true');
                button.textContent = translateUnifiedText('刷新中...');
                return;
            }
            button.removeAttribute('aria-busy');
            button.textContent = translateUnifiedText('刷新目录');
        }

        function getUnifiedSetupGuideEndpoint(providerContext = {}, key = '', fallback = '') {
            const readinessSummary = getUnifiedProviderReadinessSummary(providerContext);
            const readinessEndpoints = readinessSummary.endpoints && typeof readinessSummary.endpoints === 'object' ? readinessSummary.endpoints : {};
            const guide = providerContext.provider_integration_guide && typeof providerContext.provider_integration_guide === 'object'
                ? providerContext.provider_integration_guide
                : {};
            const guideEndpoints = guide.endpoints && typeof guide.endpoints === 'object' ? guide.endpoints : {};
            const discovery = providerContext.discovery && typeof providerContext.discovery === 'object' ? providerContext.discovery : {};
            const documentation = providerContext.documentation && typeof providerContext.documentation === 'object' ? providerContext.documentation : {};
            const entries = documentation.entries && typeof documentation.entries === 'object' ? documentation.entries : {};
            const docsEntry = entries.api_docs && typeof entries.api_docs === 'object' ? entries.api_docs : {};
            const openApiEntry = entries.openapi && typeof entries.openapi === 'object' ? entries.openapi : {};
            const endpointMap = {
                mailboxes: readinessEndpoints.mailboxes || guideEndpoints.mailboxes || discovery.mailboxes_endpoint || discovery.external_mailboxes_endpoint,
                providers: readinessEndpoints.providers || guideEndpoints.providers || discovery.providers_endpoint,
                provider_health: readinessEndpoints.provider_health || guideEndpoints.provider_health || discovery.provider_health_endpoint,
                docs: guideEndpoints.docs || docsEntry.endpoint,
                openapi: guideEndpoints.openapi || openApiEntry.endpoint,
                integration_bundle: guideEndpoints.integration_bundle || docsEntry.endpoint || openApiEntry.endpoint
            };
            return getUnifiedProviderContextText(endpointMap[key], fallback);
        }

        function getUnifiedSetupGuideModel(data = {}, state = 'ready') {
            const safeData = data && typeof data === 'object' ? data : {};
            const summary = safeData.summary && typeof safeData.summary === 'object' ? safeData.summary : {};
            const providerContext = safeData.provider_context && typeof safeData.provider_context === 'object' ? safeData.provider_context : {};
            const readinessSummary = getUnifiedProviderReadinessSummary(providerContext);
            const readinessTotals = readinessSummary.totals && typeof readinessSummary.totals === 'object' ? readinessSummary.totals : {};
            const providerCounts = getUnifiedOperationalProviderCounts(providerContext);
            const accountCount = Number(summary.account || readinessTotals.account_mailboxes || 0);
            const tempCount = Number(summary.temp || readinessTotals.temp_mailboxes || 0);
            const providerCount = Number(providerCounts.total || readinessTotals.providers || 0);
            const providerNeedsConfig = Number(providerCounts.needsConfig || 0);
            const providerReady = Number(providerCounts.ready || 0);
            const directoryEndpoint = getUnifiedSetupGuideEndpoint(providerContext, 'mailboxes', '/api/v1/external/mailboxes');
            const providersEndpoint = getUnifiedSetupGuideEndpoint(providerContext, 'providers', '/api/v1/external/providers');
            const integrationEndpoint = getUnifiedSetupGuideEndpoint(providerContext, 'integration_bundle', '/api/v1/external/integration-bundle');

            if (state === 'loading') {
                return {
                    state: 'loading',
                    status: 'loading',
                    detail: '正在整理账号、临时邮箱、Provider 路由和外部 API 接入状态',
                    steps: []
                };
            }
            if (state === 'error') {
                return {
                    state: 'error',
                    status: 'error',
                    detail: '目录读取失败，保留当前配置路径',
                    steps: [
                        {
                            key: 'retry',
                            status: 'error',
                            title: '刷新目录重试',
                            detail: '重新读取统一邮箱目录和 Provider 就绪度',
                            metric: translateUnifiedText('不可用'),
                            action: { action: 'refresh', label: '刷新目录' }
                        }
                    ]
                };
            }

            const steps = [
                {
                    key: 'accounts',
                    status: accountCount > 0 ? 'ready' : 'action',
                    title: accountCount > 0 ? '普通账号已接入' : '接入普通账号',
                    detail: accountCount > 0 ? 'Outlook/IMAP 账号已进入统一目录' : '导入或配置 Outlook/IMAP 账号作为稳定邮箱库存',
                    metric: formatUnifiedMailboxCount(accountCount, '个普通账号', 'account'),
                    action: accountCount > 0
                        ? { action: 'quick-view', view: 'accounts', label: '查看普通账号' }
                        : { action: 'open-account-view', label: '打开账号视图' }
                },
                {
                    key: 'temp',
                    status: tempCount > 0 ? 'ready' : 'action',
                    title: tempCount > 0 ? '临时邮箱已接入' : '配置临时邮箱',
                    detail: tempCount > 0 ? 'Provider 临时邮箱已进入统一目录' : '创建临时邮箱或启用可动态创建的 Provider',
                    metric: formatUnifiedMailboxCount(tempCount, '个临时邮箱', 'temp mailbox'),
                    action: tempCount > 0
                        ? { action: 'quick-view', view: 'temp', label: '查看临时邮箱' }
                        : { action: 'open-temp-workspace', label: '打开临时邮箱' }
                },
                {
                    key: 'providers',
                    status: providerNeedsConfig > 0 ? 'warning' : (providerReady > 0 ? 'ready' : 'unknown'),
                    title: providerNeedsConfig > 0 ? 'Provider 需要配置' : 'Provider 路由可用',
                    detail: providerNeedsConfig > 0 ? '检查缺失配置、来源优先级和路由矩阵' : providersEndpoint,
                    metric: `${providerReady}/${providerCount} ${translateUnifiedText('就绪')}`,
                    action: { action: 'focus-provider-context', label: '查看来源策略' }
                },
                {
                    key: 'external-api',
                    status: integrationEndpoint ? 'ready' : 'unknown',
                    title: '外部 API 接入',
                    detail: integrationEndpoint || directoryEndpoint,
                    metric: translateUnifiedText('发现接口'),
                    action: { action: 'open-api-security', label: '打开 API 安全' }
                }
            ];
            const status = steps.some(step => step.status === 'warning' || step.status === 'action')
                ? 'warning'
                : (steps.every(step => step.status === 'ready') ? 'ready' : 'unknown');
            return {
                state: status,
                status,
                detail: '按顺序完成账号库存、临时邮箱、Provider 路由和外部 API 接入',
                steps
            };
        }

        function getUnifiedOperationalViewLabel(filters = unifiedMailboxState.filters, contract = unifiedMailboxState.contract || {}) {
            const activeKey = getUnifiedQuickViewKey(filters, contract);
            if (activeKey === 'custom') return translateUnifiedText('自定义筛选');
            const preset = getUnifiedQuickViewPreset(activeKey, contract);
            return translateUnifiedText((preset && preset.label) || '当前视图');
        }

        function getUnifiedOperationalProviderCounts(providerContext = {}) {
            const readinessSummary = getUnifiedProviderReadinessSummary(providerContext);
            const readinessTotals = readinessSummary.totals && typeof readinessSummary.totals === 'object' ? readinessSummary.totals : {};
            const readinessIssues = readinessSummary.issues && typeof readinessSummary.issues === 'object' ? readinessSummary.issues : {};
            const providerDiagnostics = providerContext.provider_diagnostics && typeof providerContext.provider_diagnostics === 'object'
                ? providerContext.provider_diagnostics
                : {};
            const diagnostics = providerDiagnostics.summary && typeof providerDiagnostics.summary === 'object' ? providerDiagnostics.summary : {};
            return {
                status: String(readinessSummary.overall_status || '').trim().toLowerCase() || 'unknown',
                total: Number(readinessTotals.providers || diagnostics.total || 0),
                active: Number(readinessTotals.active_providers || diagnostics.active || 0),
                ready: Number(readinessTotals.ready_providers || diagnostics.ready || 0),
                needsConfig: Number(readinessTotals.needs_config_providers || readinessIssues.needs_config || diagnostics.needs_config || 0),
                inactive: Number(readinessIssues.inactive || diagnostics.inactive || 0)
            };
        }

        function getUnifiedOperationalLensState({ state = 'ready', totalCount = 0, providerCounts = {}, summary = {} } = {}) {
            if (state === 'loading' || state === 'error') return state;
            const inactiveCount = Number(summary.inactive || providerCounts.inactive || 0);
            if (Number(totalCount || 0) <= 0) return 'empty';
            if (Number(providerCounts.needsConfig || 0) > 0 || inactiveCount > 0 || ['needs_config', 'degraded', 'error'].includes(providerCounts.status)) {
                return 'warning';
            }
            return 'ready';
        }

        function getUnifiedOperationalRecommendation({ lensState = 'ready', activeFilterCount = 0, providerCounts = {}, summary = {} } = {}) {
            const inactiveCount = Number(summary.inactive || providerCounts.inactive || 0);
            if (lensState === 'loading') {
                return {
                    title: '正在分析当前视图…',
                    detail: '加载完成后显示建议动作',
                    actions: []
                };
            }
            if (lensState === 'error') {
                return {
                    title: '刷新目录重试',
                    detail: '目录读取失败，保留当前筛选',
                    actions: [{ action: 'refresh', label: '刷新目录' }]
                };
            }
            if (lensState === 'empty' && activeFilterCount > 0) {
                return {
                    title: '清空筛选查看全量',
                    detail: '当前筛选没有命中邮箱',
                    actions: [{ action: 'quick-view', view: 'all', label: '全部邮箱' }]
                };
            }
            if (Number(providerCounts.needsConfig || 0) > 0) {
                return {
                    title: '检查 Provider 配置',
                    detail: `${Number(providerCounts.needsConfig || 0)} ${translateUnifiedText('邮箱来源')} ${translateUnifiedText('需要配置')}`,
                    actions: [{ action: 'focus-provider-context', label: '查看来源策略' }]
                };
            }
            if (inactiveCount > 0) {
                return {
                    title: '查看需处理邮箱',
                    detail: `${inactiveCount} ${translateUnifiedText('邮箱')} ${translateUnifiedText('停用或不可用')}`,
                    actions: [{ action: 'quick-view', view: 'attention', label: '需处理' }]
                };
            }
            return {
                title: '当前视图可用',
                detail: '继续打开邮箱、复制验证码或刷新目录',
                actions: [{ action: 'refresh', label: '刷新目录' }]
            };
        }

        function getUnifiedCommandEndpoint(providerContext = {}) {
            const guide = providerContext.provider_integration_guide && typeof providerContext.provider_integration_guide === 'object'
                ? providerContext.provider_integration_guide
                : {};
            const guideEndpoints = guide.endpoints && typeof guide.endpoints === 'object' ? guide.endpoints : {};
            const discovery = providerContext.discovery && typeof providerContext.discovery === 'object' ? providerContext.discovery : {};
            return getUnifiedProviderContextText(guideEndpoints.mailboxes || discovery.mailboxes_endpoint || discovery.external_mailboxes_endpoint, '/api/v1/external/mailboxes');
        }

        function getUnifiedCommandProviderMode(providerContext = {}) {
            const defaults = providerContext.defaults || {};
            const providerFilter = providerContext.provider_filter || {};
            const rawActiveProviders = Array.isArray(defaults.active_mailbox_providers)
                ? defaults.active_mailbox_providers
                : (Array.isArray(providerFilter.active_providers) ? providerFilter.active_providers : []);
            const activeProviders = (typeof canonicalizeMailboxProviderAllowlistValues === 'function'
                ? canonicalizeMailboxProviderAllowlistValues(rawActiveProviders)
                : dedupeUnifiedTempProviderRows(
                    rawActiveProviders.map(item => ({ provider: item, kind: 'temp' }))
                ).map(item => item.provider)
            ).filter(value => value && value !== 'auto');
            return formatUnifiedProviderMode(providerFilter.mode, activeProviders);
        }

        function getUnifiedCommandProviderCount(providerContext = {}, facets = {}) {
            const providerDiagnostics = providerContext.provider_diagnostics || {};
            const diagnostics = providerDiagnostics.summary || {};
            const totalProviders = Number(diagnostics.total || 0);
            if (Number.isFinite(totalProviders) && totalProviders > 0) {
                return totalProviders;
            }
            return Array.isArray(facets.providers) ? facets.providers.length : 0;
        }

        function getUnifiedCommandDefaultProvider(providerContext = {}, key = 'temp_mail_provider', fallback = '-') {
            const defaults = providerContext.defaults && typeof providerContext.defaults === 'object' ? providerContext.defaults : {};
            return getUnifiedProviderContextText(defaults[key], fallback);
        }

        function getUnifiedCommandSourcePriority(providerContext = {}) {
            const selectionPolicy = providerContext.selection_policy && typeof providerContext.selection_policy === 'object'
                ? providerContext.selection_policy
                : {};
            return Array.isArray(selectionPolicy.source_priority) && selectionPolicy.source_priority.length
                ? selectionPolicy.source_priority.join(' > ')
                : translateUnifiedText('默认值');
        }

        function formatUnifiedMailboxCount(count, zhUnit, enUnit) {
            const safeCount = Number(count || 0);
            if (typeof getUiLanguage === 'function' && getUiLanguage() === 'en') {
                const pluralUnits = {
                    mailbox: 'mailboxes',
                    account: 'accounts',
                    'account mailbox': 'account mailboxes',
                    'temp mailbox': 'temp mailboxes'
                };
                const unit = safeCount === 1 ? enUnit : (pluralUnits[enUnit] || `${enUnit}s`);
                return `${safeCount} ${unit}`;
            }
            return `${safeCount} ${zhUnit}`;
        }

        function getUnifiedProviderContextText(value, fallback = '-') {
            const text = String(value === null || value === undefined ? '' : value).trim();
            return text || fallback;
        }

        function getUnifiedProviderConfigFile(selectionPolicy = {}, deploymentProfile = {}, providerFilter = {}) {
            const candidates = [
                selectionPolicy.config_file,
                deploymentProfile.config_file,
                providerFilter.config_file
            ];
            return candidates.find(item => item && typeof item === 'object') || {};
        }

        function formatUnifiedProviderSourceDetail(diagnostic = {}, fallbackKey = '') {
            if (!diagnostic || typeof diagnostic !== 'object') {
                return fallbackKey;
            }
            const sourceLabels = {
                env: '环境变量',
                settings: '配置项',
                default: '默认值',
                config_file: '配置文件',
                config_file_error: '配置文件错误'
            };
            const sourceKey = String(diagnostic.source || '').trim();
            const source = sourceKey ? translateUnifiedText(sourceLabels[sourceKey] || sourceKey) : '';
            const key = getUnifiedProviderContextText(diagnostic.env || diagnostic.config_key || diagnostic.settings_key || diagnostic.key || fallbackKey, '');
            return [source, key].filter(Boolean).join(' · ');
        }

        function formatUnifiedDefaultProviderIssue(item) {
            if (!item || typeof item !== 'object') return '';
            const key = String(item.env || item.config_key || item.settings_key || item.key || '').trim();
            const provider = String(item.provider || item.raw_provider || item.unknown_provider || '').trim();
            return [key, provider].filter(Boolean).join('=') || provider || key;
        }

        function buildUnifiedProviderNoticeMessages(providerFilter = {}, defaultsDiagnostics = {}, configFile = {}, summary = {}) {
            const messages = [];
            const listSeparator = typeof getUiLanguage === 'function' && getUiLanguage() === 'en' ? ', ' : '、';
            const configErrorCode = String(configFile.error_code || providerFilter.config_error_code || '').trim();
            const configError = String(configFile.error || providerFilter.config_error || '').trim();
            if (configErrorCode || configError) {
                messages.push(`${translateUnifiedText('配置文件错误')}: ${[configErrorCode, configError].filter(Boolean).join(' · ')}`);
            }

            const unknownProviders = Array.isArray(providerFilter.unknown_providers) ? providerFilter.unknown_providers.filter(Boolean) : [];
            if (unknownProviders.length) {
                messages.push(`${translateUnifiedText('未知来源白名单项')}: ${unknownProviders.join(listSeparator)}`);
            }

            const invalidDefaults = Array.isArray(defaultsDiagnostics.invalid_defaults) ? defaultsDiagnostics.invalid_defaults.filter(Boolean) : [];
            if (invalidDefaults.length) {
                const detail = invalidDefaults.map(formatUnifiedDefaultProviderIssue).filter(Boolean).join(listSeparator);
                messages.push(`${translateUnifiedText('默认来源配置无效')}: ${detail || Number(summary.invalid_default_entries || invalidDefaults.length)}`);
            }

            const inactiveDefaults = Array.isArray(defaultsDiagnostics.inactive_defaults) ? defaultsDiagnostics.inactive_defaults.filter(Boolean) : [];
            if (inactiveDefaults.length) {
                const detail = inactiveDefaults.map(formatUnifiedDefaultProviderIssue).filter(Boolean).join(listSeparator);
                messages.push(`${translateUnifiedText('默认来源未启用')}: ${detail || Number(summary.inactive_default_entries || inactiveDefaults.length)}`);
            }
            return messages;
        }

        function getUnifiedProviderContextState(providerFilter = {}, defaultsDiagnostics = {}, configFile = {}, summary = {}) {
            const hasConfigError = Boolean(configFile.error_code || configFile.error || providerFilter.config_error_code || providerFilter.config_error);
            const invalidDefaultCount = Number(summary.invalid_default_entries || (defaultsDiagnostics.invalid_defaults || []).length || 0);
            const inactiveDefaultCount = Number(summary.inactive_default_entries || (defaultsDiagnostics.inactive_defaults || []).length || 0);
            const unknownFilterCount = Number(summary.unknown_filter_entries || (providerFilter.unknown_providers || []).length || 0);
            const needsConfigCount = Number(summary.needs_config || 0);
            if (hasConfigError || invalidDefaultCount > 0 || unknownFilterCount > 0) {
                return 'error';
            }
            if (needsConfigCount > 0 || inactiveDefaultCount > 0) {
                return 'warning';
            }
            return 'ok';
        }

        function formatUnifiedProviderMode(mode, activeProviders = []) {
            const normalizedMode = String(mode || '').trim().toLowerCase();
            if (normalizedMode === 'all') {
                return translateUnifiedText('全部启用');
            }
            if (normalizedMode === 'allowlist') {
                return `${translateUnifiedText('白名单')} ${Number(activeProviders.length || 0)}`;
            }
            return getUnifiedProviderContextText(mode);
        }

        function getUnifiedProviderReadinessSummary(providerContext = {}) {
            const readinessSummary = providerContext.readiness_summary && typeof providerContext.readiness_summary === 'object'
                ? providerContext.readiness_summary
                : {};
            if (Number(readinessSummary.version || 0) !== 1) return {};
            return readinessSummary;
        }

        function getUnifiedProviderRoutingMatrix(readinessSummary = {}) {
            const routingMatrix = readinessSummary.routing_matrix && typeof readinessSummary.routing_matrix === 'object'
                ? readinessSummary.routing_matrix
                : {};
            if (Number(routingMatrix.version || 0) !== 1) return {};
            return routingMatrix;
        }

        function canonicalizeUnifiedTempProviderKey(providerKey) {
            const raw = String(providerKey || '').trim();
            if (!raw) return '';
            if (typeof normalizeTempMailSettingsProviderName === 'function') {
                return normalizeTempMailSettingsProviderName(raw) || raw.toLowerCase();
            }
            // Warmup-safe mirror of main.js built-in alias map when Settings helpers are unavailable.
            const staticAliases = {
                gptmail: 'legacy_bridge',
                legacy_gptmail: 'legacy_bridge',
                temp_mail: 'legacy_bridge',
                custom_domain_temp_mail: 'legacy_bridge',
            };
            const key = raw.toLowerCase();
            return staticAliases[key] || key;
        }

        function getUnifiedProviderGuideProviders(providerContext = {}) {
            const guide = providerContext.provider_integration_guide && typeof providerContext.provider_integration_guide === 'object'
                ? providerContext.provider_integration_guide
                : {};
            return Array.isArray(guide.providers)
                ? guide.providers.filter(item => item && typeof item === 'object')
                : [];
        }

        function getUnifiedProviderCapabilityMatrix(providerContext = {}) {
            const readinessSummary = providerContext.readiness_summary && typeof providerContext.readiness_summary === 'object'
                ? providerContext.readiness_summary
                : {};
            const matrix = readinessSummary.capability_matrix && typeof readinessSummary.capability_matrix === 'object'
                ? readinessSummary.capability_matrix
                : {};
            return Array.isArray(matrix.providers) ? matrix : {};
        }

        function getUnifiedProviderCapabilityMatrixProviders(providerContext = {}) {
            const matrix = getUnifiedProviderCapabilityMatrix(providerContext);
            return Array.isArray(matrix.providers)
                ? matrix.providers.filter(item => item && typeof item === 'object')
                : [];
        }

        function getUnifiedProviderCapabilityMatrixWorkflows(providerContext = {}) {
            const matrix = getUnifiedProviderCapabilityMatrix(providerContext);
            const workflows = matrix.workflows && typeof matrix.workflows === 'object' ? matrix.workflows : {};
            return Object.entries(workflows)
                .map(([key, workflow]) => ({ key, ...(workflow && typeof workflow === 'object' ? workflow : {}) }))
                .filter(item => String(item.key || item.workflow || '').trim());
        }

        function normalizeUnifiedProviderCapabilityBool(value) {
            if (typeof value === 'boolean') return value;
            if (typeof value === 'number') return value > 0;
            const text = String(value === null || value === undefined ? '' : value).trim().toLowerCase();
            return ['1', 'true', 'yes', 'enabled', 'ready', 'available'].includes(text);
        }

        function normalizeUnifiedProviderCapabilityKeys(values = []) {
            const keys = Array.isArray(values) ? values : (typeof values === 'string' ? [values] : []);
            return keys.map(item => String(item || '').trim()).filter(Boolean);
        }

        function normalizeUnifiedProviderCapabilityObject(source = {}) {
            return source && typeof source === 'object' && !Array.isArray(source) ? source : {};
        }

        function normalizeUnifiedProviderCapabilityNumber(value) {
            const numberValue = Number(value || 0);
            return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : 0;
        }

        function getUnifiedProviderReadCapability(provider = {}) {
            const capabilities = provider.capabilities && typeof provider.capabilities === 'object' ? provider.capabilities : {};
            return String(capabilities.read_capability || provider.read_capability || '').trim().toLowerCase();
        }

        function getUnifiedProviderReadCapabilityLabel(readCapability = '', contract = {}) {
            const value = String(readCapability || '').trim().toLowerCase();
            if (!value) return translateUnifiedText('未知');
            const definitions = Array.isArray(contract.read_capability_definitions) ? contract.read_capability_definitions : [];
            const definition = definitions.find(item => String(item && item.read_capability || '').trim().toLowerCase() === value) || {};
            return translateUnifiedText(definition.label || definition.label_en || value);
        }

        function getUnifiedProviderCapabilityState(provider = {}) {
            const configuration = normalizeUnifiedProviderCapabilityObject(provider.configuration);
            const active = normalizeUnifiedProviderCapabilityBool(provider.active);
            const configured = normalizeUnifiedProviderCapabilityBool(provider.configured);
            const missingConfig = normalizeUnifiedProviderCapabilityKeys(provider.missing_config || configuration.missing_config || configuration.missing_env || configuration.missing_settings);
            const missingConfigCount = normalizeUnifiedProviderCapabilityNumber(provider.missing_config_count || configuration.missing_config_count || missingConfig.length);
            const needsConfig = normalizeUnifiedProviderCapabilityBool(configuration.needs_config);
            const rawStatus = String(provider.readiness_status || '').trim().toLowerCase().replace(/_/g, '-');
            if (!active) return 'inactive';
            if (!configured || needsConfig || rawStatus === 'needs-config' || missingConfig.length > 0 || missingConfigCount > 0) return 'needs-config';
            if (rawStatus === 'ready' || rawStatus === 'ok') return 'ready';
            return rawStatus || 'unavailable';
        }

        function getUnifiedProviderCapabilityStateLabel(state) {
            const labels = {
                ready: '已就绪',
                'needs-config': '缺配置',
                inactive: '未启用',
                unavailable: '不可用',
                error: '配置异常'
            };
            return translateUnifiedText(labels[state] || state || '不可用');
        }

        function getUnifiedProviderCapabilityEndpoint(provider = {}, fieldName = '') {
            const source = provider[fieldName] && typeof provider[fieldName] === 'object' ? provider[fieldName] : {};
            const endpoint = String(source.endpoint || '').trim();
            if (!endpoint) return '';
            const query = source.query && typeof source.query === 'object' ? source.query : {};
            const queryText = Object.entries(query)
                .map(([key, value]) => [String(key || '').trim(), String(value === null || value === undefined ? '' : value).trim()])
                .filter(([key, value]) => key && value)
                .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
                .join('&');
            return queryText ? `${endpoint}?${queryText}` : endpoint;
        }

        function normalizeUnifiedProviderCapabilityEndpointMap(provider = {}) {
            const endpoints = normalizeUnifiedProviderCapabilityObject(provider.endpoints);
            const endpointEntries = Object.entries(endpoints)
                .map(([key, value]) => ({ key: String(key || '').trim(), value: String(value || '').trim() }))
                .filter(item => item.key && item.value);
            if (endpointEntries.length > 0) return endpointEntries.slice(0, 6);
            return [
                { key: 'provider_health', value: getUnifiedProviderCapabilityEndpoint(provider, 'health') },
                { key: 'mailboxes', value: getUnifiedProviderCapabilityEndpoint(provider, 'mailbox_directory_filter') }
            ].filter(item => item.value);
        }

        function getUnifiedProviderCapabilityWorkflowEntries(workflowSupport = {}, workflows = []) {
            const support = normalizeUnifiedProviderCapabilityObject(workflowSupport);
            const workflowByKey = workflows.reduce((acc, workflow) => {
                const key = String(workflow.workflow || workflow.key || '').trim();
                if (key) acc[key] = workflow;
                return acc;
            }, {});
            const keys = Object.keys(support).length > 0 ? Object.keys(support) : Object.keys(workflowByKey);
            return keys.map(key => {
                const workflow = workflowByKey[key] || {};
                return {
                    key,
                    label: String(workflow.label || key).trim(),
                    enabled: normalizeUnifiedProviderCapabilityBool(support[key])
                };
            }).filter(item => item.key).slice(0, 8);
        }

        function getUnifiedProviderCapabilitySelectorFields(selectionFields = {}) {
            const fields = normalizeUnifiedProviderCapabilityObject(selectionFields);
            return Object.entries(fields).map(([scope, value]) => {
                const entry = normalizeUnifiedProviderCapabilityObject(value);
                return {
                    scope: String(scope || '').trim(),
                    field: String(entry.field || '').trim(),
                    value: String(entry.value || '').trim()
                };
            }).filter(item => item.scope && (item.field || item.value)).slice(0, 5);
        }

        function formatUnifiedReadCapabilityLabel(readCapability = '') {
            const value = String(readCapability || '').trim().toLowerCase();
            if (!value) return translateUnifiedText('未知');
            const definitions = Array.isArray(unifiedMailboxState.contract.read_capability_definitions)
                ? unifiedMailboxState.contract.read_capability_definitions
                : [];
            const definition = definitions.find(item => String(item && item.read_capability || '').trim().toLowerCase() === value) || {};
            return translateUnifiedText(definition.label || definition.label_en || value);
        }

        function getUnifiedLatestText(item) {
            const latest = item && item.latest ? item.latest : {};
            const subject = String(latest.email_subject || '').trim();
            const from = String(latest.email_from || '').trim();
            const receivedAt = String(latest.email_received_at || '').trim();
            if (!subject && !from && !receivedAt) {
                return translateUnifiedText('暂无邮件摘要');
            }
            const meta = [from, receivedAt ? formatRelativeTime(receivedAt) : ''].filter(Boolean).join(' · ');
            return subject ? `${subject}${meta ? ' · ' + meta : ''}` : meta;
        }

        function getUnifiedVerificationText(item) {
            const latest = item && item.latest ? item.latest : {};
            return String(latest.verification_code || '').trim();
        }

        function getUnifiedMessageMailboxKey(itemOrKind, sourceId = null) {
            const kind = typeof itemOrKind === 'object'
                ? normalizeUnifiedPreviewKind(itemOrKind && itemOrKind.kind)
                : normalizeUnifiedPreviewKind(itemOrKind);
            const id = typeof itemOrKind === 'object'
                ? Number(itemOrKind && itemOrKind.source_id || 0)
                : Number(sourceId || 0);
            if (!kind || !id) return '';
            return `${kind}:${id}`;
        }

        function getUnifiedMessageEndpoint(kind, sourceId, suffix = 'messages') {
            const cleanKind = normalizeUnifiedPreviewKind(kind).replace(/[^a-z0-9_-]/g, '');
            const cleanSourceId = Number(sourceId || 0);
            const cleanSuffix = String(suffix || 'messages').replace(/^\/+/, '');
            return `/api/mailboxes/${cleanKind}/${cleanSourceId}/${cleanSuffix}`;
        }

        function getUnifiedMessageDetailEndpoint(kind, sourceId, messageId) {
            return `/api/mailboxes/${normalizeUnifiedPreviewKind(kind)}/${Number(sourceId || 0)}/messages/${encodeURIComponent(String(messageId || ''))}`;
        }

        function getUnifiedPreviewMailboxItem(kind, sourceId) {
            const key = getUnifiedMessageMailboxKey(kind, sourceId);
            return (unifiedMailboxState.items || []).find(item => getUnifiedMessageMailboxKey(item) === key) || null;
        }

        function getUnifiedMailboxProviderDisplayLabel(mailbox = {}) {
            const payload = mailbox && typeof mailbox === 'object' ? mailbox : {};
            const providerKey = String(payload.provider || payload.key || payload.name || '').trim();
            // Directory items use provider_label; readiness/capability rows use label.
            const apiLabel = String(payload.provider_label || payload.label || '').trim();
            if (typeof resolveMailboxProviderLabel === 'function') {
                const resolved = resolveMailboxProviderLabel(providerKey || apiLabel, {
                    softLoad: false,
                    emptyLabel: '',
                    fallbackResolver: () => apiLabel,
                });
                if (resolved) return resolved;
            }
            return apiLabel || providerKey || '-';
        }

        function getUnifiedPreviewMailboxLabel(mailbox = {}) {
            const provider = getUnifiedMailboxProviderDisplayLabel(mailbox);
            const capability = formatUnifiedReadCapabilityLabel(mailbox.read_capability || '');
            return [provider, capability].filter(Boolean).join(' · ');
        }

        function getUnifiedPreviewErrorMessage(data, fallback = '邮件读取失败') {
            if (!data || typeof data !== 'object') return translateUnifiedText(fallback);
            const message = data.message || (data.error && (data.error.message || data.error.message_en)) || data.message_en;
            return translateUnifiedText(String(message || fallback));
        }

        function resetUnifiedMessagePreview() {
            const preview = unifiedMailboxState.preview || {};
            // Bump seqs so abandoned in-flight preview GETs cannot repaint after reset.
            const requestSeq = Number(preview.requestSeq || 0) + 1;
            const detailSeq = Number(preview.detailSeq || 0) + 1;
            const verificationSeq = Number(preview.verificationSeq || 0) + 1;
            unifiedMailboxState.preview = {
                ...preview,
                selectedKey: '',
                selectedKind: '',
                selectedSourceId: 0,
                mailbox: null,
                messages: [],
                selectedMessageId: '',
                message: null,
                verification: null,
                loading: false,
                detailLoading: false,
                verificationLoading: false,
                error: '',
                detailError: '',
                verificationError: '',
                requestSeq,
                detailSeq,
                verificationSeq,
                messagesSignature: '',
                messagesLoadPromise: null,
                messagesLoadSignature: '',
                messagesLoadForce: false,
                detailSignature: '',
                detailLoadPromise: null,
                detailLoadSignature: '',
                detailLoadForce: false,
                verificationSignature: '',
                verificationLoadPromise: null,
                verificationLoadSignature: '',
                verificationLoadForce: false
            };
            renderUnifiedMessagePreview();
        }

        function refreshUnifiedMailboxProviderLabelsFromCatalog() {
            // After shared catalog labels arrive, repaint already-loaded unified
            // directory cards and readiness/capability labels without a network reload.
            if (!unifiedMailboxState.loaded) return;
            if (Array.isArray(unifiedMailboxState.items) && unifiedMailboxState.items.length) {
                renderUnifiedMailboxList(unifiedMailboxState.items);
            }
            const selectedProvider = String(
                (unifiedMailboxState.filters && unifiedMailboxState.filters.provider) || 'all'
            ).trim() || 'all';
            if (unifiedMailboxState.providerContext && typeof unifiedMailboxState.providerContext === 'object') {
                if (typeof renderUnifiedProviderContext === 'function') {
                    renderUnifiedProviderContext(
                        unifiedMailboxState.providerContext,
                        'ready',
                        Array.isArray(unifiedMailboxState.providerFacets) ? unifiedMailboxState.providerFacets : [],
                        selectedProvider
                    );
                }
                if (typeof renderUnifiedProviderCapabilityMatrix === 'function') {
                    renderUnifiedProviderCapabilityMatrix(
                        unifiedMailboxState.providerContext,
                        unifiedMailboxState.contract || {},
                        'ready',
                        selectedProvider
                    );
                }
            }
        }

        function invalidateUnifiedMailboxDirectoryCache() {
            unifiedMailboxState.directoryPayload = null;
            unifiedMailboxState.directorySignature = '';
            unifiedMailboxState.loaded = false;
            // Do not bump directoryLoadSeq here — in-flight loaders still use seq identity;
            // inventory mutations call this then loadUnifiedMailboxes(true) which supersedes soft.
            unifiedMailboxState.directoryLoadForce = false;
            unifiedMailboxState.directoryInFlightSignature = '';
            // Inventory mutations may remove the currently previewed mailbox; drop preview soft
            // state so deleted/overwritten mailboxes cannot keep painting warm messages/detail.
            resetUnifiedMessagePreview();
        }

        // Cross-module inventory mutations (accounts/temp force refresh) drop soft directory cache.
        window.invalidateUnifiedMailboxDirectoryCache = invalidateUnifiedMailboxDirectoryCache;

        function isCurrentUnifiedMailboxSurface() {
            return typeof mailboxViewMode !== 'undefined'
                && mailboxViewMode === 'unified'
                && (typeof currentPage === 'undefined' || currentPage === 'mailbox');
        }

