// split from state.js → readiness.js
        async function loadOperationalReadinessSnapshot(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            // Soft re-entry: always return warm cache; paint only on api-security tab.
            if (!force && operationalReadinessSnapshotCache) {
                if (isCurrentApiSecuritySurface()) {
                    renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready');
                }
                return operationalReadinessSnapshotCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so command-center refresh starts a true network GET.
            if (operationalReadinessSnapshotPromise) {
                if (!force || operationalReadinessSnapshotLoadForce) {
                    return operationalReadinessSnapshotPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                operationalReadinessSnapshotPromise = null;
                operationalReadinessSnapshotLoadForce = false;
            }

            const params = new URLSearchParams({
                kind: 'all',
                status: 'all',
                read_capability: 'all',
                action: 'all',
                provider: 'all',
                sort: 'updated_desc',
                page: '1',
                page_size: '1'
            });

            operationalReadinessSnapshotLoadForce = force;
            const request = fetch(`/api/mailboxes?${params.toString()}`)
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (operationalReadinessSnapshotPromise !== request) {
                        return operationalReadinessSnapshotCache;
                    }
                    if (!data || data.success === false) throw new Error('mailbox_snapshot_failed');
                    // Always warm soft cache; paint only while still on api-security.
                    operationalReadinessSnapshotCache = {
                        summary: data.summary && typeof data.summary === 'object' ? data.summary : {},
                        provider_context: data.provider_context && typeof data.provider_context === 'object' ? data.provider_context : {},
                        contract: data.contract && typeof data.contract === 'object' ? data.contract : {},
                        facets: data.facets && typeof data.facets === 'object' ? data.facets : {},
                        status: 'ready'
                    };
                    if (isCurrentApiSecuritySurface()) {
                        renderExternalApiCommandCenter(externalApiSettingsSnapshot, 'ready');
                    }
                    return operationalReadinessSnapshotCache;
                })
                .catch(error => {
                    if (operationalReadinessSnapshotPromise !== request) {
                        return operationalReadinessSnapshotCache;
                    }
                    console.warn('加载运行就绪快照失败:', error);
                    operationalReadinessSnapshotCache = {
                        summary: {},
                        provider_context: {},
                        contract: {},
                        facets: {},
                        status: 'error'
                    };
                    if (isCurrentApiSecuritySurface()) {
                        renderExternalApiCommandCenter(externalApiSettingsSnapshot, 'mailbox_error');
                    }
                    return operationalReadinessSnapshotCache;
                })
                .finally(() => {
                    if (operationalReadinessSnapshotPromise === request) {
                        operationalReadinessSnapshotPromise = null;
                        operationalReadinessSnapshotLoadForce = false;
                    }
                });
            operationalReadinessSnapshotPromise = request;
            return request;
        }

        function getOperationalReadinessMailboxSnapshot() {
            const snapshot = operationalReadinessSnapshotCache && typeof operationalReadinessSnapshotCache === 'object'
                ? operationalReadinessSnapshotCache
                : {};
            const providerContext = snapshot.provider_context && typeof snapshot.provider_context === 'object'
                ? snapshot.provider_context
                : {};
            const readiness = providerContext.readiness_summary && typeof providerContext.readiness_summary === 'object'
                ? providerContext.readiness_summary
                : {};
            return {
                status: String(snapshot.status || (Object.keys(snapshot).length ? 'ready' : 'loading')),
                summary: snapshot.summary && typeof snapshot.summary === 'object' ? snapshot.summary : {},
                providerContext,
                readiness,
                totals: readiness.totals && typeof readiness.totals === 'object' ? readiness.totals : {},
                issues: readiness.issues && typeof readiness.issues === 'object' ? readiness.issues : {}
            };
        }

        function getOperationalReadinessTaskTempStatus() {
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const providers = dedupeMailboxProviderDiagnosticRows(
                Array.isArray(diagnostics.providers) ? diagnostics.providers.filter(item => item && typeof item === 'object') : []
            );
            const activeDynamicProviders = providers.filter(item => item.active !== false && item.can_dynamic_create === true);
            const readyDynamicProviders = activeDynamicProviders.filter(item => String(item.status || item.readiness_status || '').trim().toLowerCase() === 'ready');
            if (!providers.length) {
                return {
                    tone: 'degraded',
                    value: translateAppTextLocal('待加载'),
                    detail: translateAppTextLocal('Provider catalog 未加载')
                };
            }
            if (readyDynamicProviders.length > 0) {
                return {
                    tone: 'ready',
                    value: `${readyDynamicProviders.length}/${activeDynamicProviders.length || readyDynamicProviders.length}`,
                    detail: translateAppTextLocal('任务临时邮箱可创建')
                };
            }
            if (activeDynamicProviders.length > 0) {
                return {
                    tone: 'degraded',
                    value: `0/${activeDynamicProviders.length}`,
                    detail: translateAppTextLocal('任务临时邮箱需补齐 Provider 配置')
                };
            }
            return {
                tone: 'neutral',
                value: '0',
                detail: translateAppTextLocal('暂无可动态创建的 Provider')
            };
        }

        function getOperationalReadinessTone(ready, neutral = false) {
            if (ready) return 'ready';
            return neutral ? 'neutral' : 'degraded';
        }

        function getOperationalReadinessCards(settings, renderState) {
            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const mailboxSnapshot = getOperationalReadinessMailboxSnapshot();
            const totals = mailboxSnapshot.totals;
            const summary = mailboxSnapshot.summary;
            const accessStatus = getExternalApiCommandAccessStatus(safeSettings);
            const multiKeyCount = getExternalApiCommandMultiKeyCount(safeSettings);
            const hasApiAccess = safeSettings.external_api_key_set === true || multiKeyCount > 0;
            const providerSummary = getExternalApiCommandProviderSummary(renderState);
            const poolStatus = getExternalApiCommandPoolStatus(safeSettings);
            const endpointMap = getExternalApiCommandEndpointMap();
            const accountCount = Number(totals.account_mailboxes || summary.account || 0);
            const tempCount = Number(totals.temp_mailboxes || summary.temp || 0);
            const totalMailboxes = Number(totals.mailboxes || summary.total || accountCount + tempCount || 0);
            const mailboxReady = mailboxSnapshot.status === 'ready';
            const taskTempStatus = getOperationalReadinessTaskTempStatus();
            const discoveryReady = Boolean(String(endpointMap.capabilities || '').trim() && String(endpointMap.openapi || '').trim());
            const poolEnabled = safeSettings.pool_external_enabled === true;
            const poolPartial = poolEnabled && [
                safeSettings.external_api_disable_pool_claim_random,
                safeSettings.external_api_disable_pool_claim_release,
                safeSettings.external_api_disable_pool_claim_complete,
                safeSettings.external_api_disable_pool_stats
            ].some(value => value === true);

            return [
                {
                    key: 'external_api',
                    label: 'External API',
                    value: translateAppTextLocal(accessStatus.label),
                    detail: translateAppTextLocal(accessStatus.detail),
                    tone: hasApiAccess ? 'ready' : 'degraded'
                },
                {
                    key: 'provider_catalog',
                    label: 'Provider catalog',
                    value: providerSummary.unavailable ? translateAppTextLocal('需检查') : `${providerSummary.ready}/${providerSummary.total}`,
                    detail: providerSummary.unavailable ? translateAppTextLocal('Provider catalog 需要检查') : providerSummary.detail,
                    tone: providerSummary.unavailable || providerSummary.needsConfig > 0 ? 'degraded' : 'ready'
                },
                {
                    key: 'mailbox_directory',
                    label: '邮箱目录快照',
                    value: mailboxReady ? String(totalMailboxes) : translateAppTextLocal('需检查'),
                    detail: mailboxReady ? translateAppTextLocal('Outlook / IMAP / Temp Mail 聚合目录可读取') : translateAppTextLocal('Mailbox directory snapshot unavailable'),
                    tone: mailboxReady ? 'ready' : 'degraded'
                },
                {
                    key: 'account_inventory',
                    label: 'Outlook / IMAP',
                    value: String(accountCount),
                    detail: accountCount > 0 ? translateAppTextLocal('账号邮箱已进入统一目录') : translateAppTextLocal('暂无账号邮箱库存'),
                    tone: getOperationalReadinessTone(accountCount > 0, true)
                },
                {
                    key: 'temp_inventory',
                    label: '临时邮箱库存',
                    value: String(tempCount),
                    detail: tempCount > 0 ? translateAppTextLocal('临时邮箱已进入统一目录') : translateAppTextLocal('可通过 Provider 动态创建临时邮箱'),
                    tone: getOperationalReadinessTone(tempCount > 0 || taskTempStatus.tone === 'ready', true)
                },
                {
                    key: 'external_pool',
                    label: 'External Pool',
                    value: poolStatus.value,
                    detail: poolStatus.detail,
                    tone: poolEnabled ? (poolPartial ? 'partial' : 'ready') : 'neutral'
                },
                {
                    key: 'task_temp',
                    label: '任务临时邮箱',
                    value: taskTempStatus.value,
                    detail: taskTempStatus.detail,
                    tone: taskTempStatus.tone
                },
                {
                    key: 'discovery_openapi',
                    label: 'Discovery / OpenAPI',
                    value: discoveryReady ? translateAppTextLocal('可发现') : translateAppTextLocal('需检查'),
                    detail: discoveryReady ? `${externalApiCanonicalPath('/capabilities')} · ${externalApiCanonicalPath('/openapi.json')}` : translateAppTextLocal('就绪入口需要检查'),
                    tone: discoveryReady ? 'ready' : 'degraded'
                }
            ];
        }

        function renderOperationalReadinessCard(card) {
            const safeCard = card && typeof card === 'object' ? card : {};
            return [
                `<div class="operational-readiness-card" data-tone="${escapeHtml(safeCard.tone || 'neutral')}" data-readiness-key="${escapeHtml(safeCard.key || '')}">`,
                    '<div class="operational-readiness-card-head">',
                        `<span>${escapeHtml(translateAppTextLocal(safeCard.label || ''))}</span>`,
                        `<strong>${escapeHtml(String(safeCard.value || ''))}</strong>`,
                    '</div>',
                    safeCard.detail ? `<div class="operational-readiness-status">${escapeHtml(safeCard.detail)}</div>` : '',
                '</div>'
            ].join('');
        }

        function renderOperationalReadinessConsole(settings = {}, state = 'ready') {
            const cards = getOperationalReadinessCards(settings, state);
            const snapshot = getOperationalReadinessMailboxSnapshot();
            const degraded = cards.some(item => item.tone === 'degraded');
            const subtitle = snapshot.status === 'loading'
                ? '正在读取邮箱目录快照…'
                : '聚合 API 鉴权、Provider、目录库存、Pool 与任务临时邮箱状态';
            return [
                `<div class="operational-readiness-console" data-state="${escapeHtml(snapshot.status)}" data-health="${degraded ? 'degraded' : 'ready'}">`,
                    '<div class="operational-readiness-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('运行就绪检查台'))}</div>`,
                            `<div class="operational-readiness-subtitle">${escapeHtml(translateAppTextLocal(subtitle))}</div>`,
                        '</div>',
                        `<span class="badge ${degraded ? 'badge-gold' : 'badge-green'}">${escapeHtml(translateAppTextLocal(degraded ? '需检查' : '可接入'))}</span>`,
                    '</div>',
                    `<div class="operational-readiness-grid">${cards.map(renderOperationalReadinessCard).join('')}</div>`,
                '</div>'
            ].join('');
        }

