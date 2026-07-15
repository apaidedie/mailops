// split from provider_catalog.js → health.js
        async function loadProviderPreflightSnapshot(forceRefresh = false, probeNetwork = false) {
            const explicitProbe = probeNetwork === true;
            const force = Boolean(forceRefresh) || explicitProbe;
            // Soft re-entry: always return warm cache; paint only on api-security tab.
            if (!force && providerPreflightCache) {
                if (isCurrentApiSecuritySurface()) {
                    renderProviderPreflightConsole();
                }
                return providerPreflightCache;
            }
            // Soft joins any in-flight. Force/probe joins only force in-flight;
            // force supersedes soft so API-security refresh starts a true network GET.
            if (providerPreflightPromise) {
                if (!force || providerPreflightLoadForce) {
                    return providerPreflightPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                providerPreflightPromise = null;
                providerPreflightLoadForce = false;
            }

            providerPreflightLoadForce = force;
            providerPreflightState = {
                status: explicitProbe ? 'probing' : 'loading',
                probeNetwork: explicitProbe,
                error: null
            };
            if (isCurrentApiSecuritySurface()) {
                renderProviderPreflightConsole();
            }

            const endpoint = explicitProbe
                ? '/api/providers/preflight?probe_network=true'
                : '/api/providers/preflight';
            const request = fetch(endpoint, { cache: 'no-store' })
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (providerPreflightPromise !== request) {
                        return providerPreflightCache;
                    }
                    if (!data || data.success === false) throw new Error('provider_preflight_failed');
                    // Always warm soft cache; paint only while still on api-security.
                    providerPreflightCache = data.provider_preflight && typeof data.provider_preflight === 'object'
                        ? data.provider_preflight
                        : {};
                    providerPreflightState = {
                        status: 'ready',
                        probeNetwork: explicitProbe,
                        error: null
                    };
                    if (isCurrentApiSecuritySurface()) {
                        renderProviderPreflightConsole();
                    }
                    return providerPreflightCache;
                })
                .catch(error => {
                    if (providerPreflightPromise !== request) {
                        return providerPreflightCache;
                    }
                    console.warn('加载 provider preflight 失败:', error);
                    providerPreflightState = {
                        status: 'error',
                        probeNetwork: explicitProbe,
                        error
                    };
                    if (isCurrentApiSecuritySurface()) {
                        renderProviderPreflightConsole();
                    }
                    return providerPreflightCache;
                })
                .finally(() => {
                    if (providerPreflightPromise === request) {
                        providerPreflightPromise = null;
                        providerPreflightLoadForce = false;
                    }
                });
            providerPreflightPromise = request;
            return request;
        }

        function getProviderPreflightSnapshot() {
            return providerPreflightCache && typeof providerPreflightCache === 'object' ? providerPreflightCache : null;
        }

        function getProviderPreflightStatusLabel(status) {
            const normalized = String(status || '').trim().toLowerCase();
            if (normalized === 'ready') return translateAppTextLocal('预检通过');
            if (normalized === 'needs_config') return translateAppTextLocal('需要配置');
            if (normalized === 'degraded') return translateAppTextLocal('预检降级');
            if (normalized === 'probing') return translateAppTextLocal('探测中…');
            if (normalized === 'loading') return translateAppTextLocal('预检中…');
            if (normalized === 'error') return translateAppTextLocal('预检失败');
            return translateAppTextLocal('预检未知');
        }

        function getProviderPreflightStatusTone(status) {
            const normalized = String(status || '').trim().toLowerCase();
            if (normalized === 'ready') return 'ready';
            if (normalized === 'needs_config') return 'warning';
            if (normalized === 'degraded' || normalized === 'error') return 'error';
            if (normalized === 'loading' || normalized === 'probing') return 'muted';
            return 'muted';
        }

        function getProviderPreflightProbeLabel(probe) {
            const safeProbe = probe && typeof probe === 'object' ? probe : {};
            const status = String(safeProbe.status || '').trim().toLowerCase();
            if (safeProbe.requested !== true || status === 'not_requested') return translateAppTextLocal('未探测');
            if (status === 'ok' || safeProbe.ok === true) {
                return safeProbe.network_probe === false
                    ? translateAppTextLocal('本地检查通过')
                    : translateAppTextLocal('上游正常');
            }
            if (status === 'skipped') return translateAppTextLocal('探测已跳过');
            if (status === 'error' || safeProbe.ok === false) return translateAppTextLocal('探测失败');
            return translateAppTextLocal('探测未知');
        }

        function getProviderPreflightProbeTone(probe) {
            const safeProbe = probe && typeof probe === 'object' ? probe : {};
            const status = String(safeProbe.status || '').trim().toLowerCase();
            if (status === 'ok' || safeProbe.ok === true) return 'ready';
            if (status === 'error' || safeProbe.ok === false) return 'error';
            if (status === 'skipped') return 'warning';
            return 'muted';
        }

        function getProviderHealthKey(kind, providerName) {
            return `${String(kind || '').trim().toLowerCase()}:${normalizeProviderCatalogName(providerName)}`;
        }

        function getProviderHealthDetailsText(details) {
            if (!details || typeof details !== 'object') return '';
            const parts = [];
            if (details.domain_count !== undefined && details.domain_count !== null) {
                parts.push(`${translateAppTextLocal('域名')} ${Number(details.domain_count) || 0}`);
            }
            if (details.enabled_domain_count !== undefined && details.enabled_domain_count !== null) {
                parts.push(`${translateAppTextLocal('可用域名')} ${Number(details.enabled_domain_count) || 0}`);
            }
            if (details.configured !== undefined) {
                parts.push(translateAppTextLocal(details.configured ? '配置 OK' : '配置缺失'));
            }
            return parts.join(' · ');
        }

        function getProviderHealthResultText(state) {
            if (!state || state.status === 'loading') return '';
            if (state.status === 'error') {
                const error = state.error && typeof state.error === 'object' ? state.error : {};
                const code = String(error.code || error.error_code || '').trim();
                return [translateAppTextLocal('探测异常'), code].filter(Boolean).join(' · ');
            }

            const health = state.health && typeof state.health === 'object' ? state.health : {};
            const probe = health.probe && typeof health.probe === 'object' ? health.probe : {};
            const status = String(probe.status || '').trim().toLowerCase();
            if (status === 'ok' || probe.ok === true) {
                const detailsText = getProviderHealthDetailsText(probe.details || {});
                const statusText = probe.network_probe === false
                    ? translateAppTextLocal('本地检查通过')
                    : translateAppTextLocal('上游正常');
                return [statusText, detailsText].filter(Boolean).join(' · ');
            }
            if (status === 'skipped') {
                const code = String(probe.error_code || '').trim();
                if (code === 'TEMP_MAIL_PROVIDER_NOT_CONFIGURED') return translateAppTextLocal('本地未就绪');
                if (code === 'MAILBOX_PROVIDER_NOT_ACTIVE') return translateAppTextLocal('未启用');
                return translateAppTextLocal('探测已跳过');
            }
            if (status === 'error' || probe.ok === false) {
                const code = String(probe.error_code || '').trim();
                return [translateAppTextLocal('探测失败'), code].filter(Boolean).join(' · ');
            }
            return '';
        }

        function getProviderHealthResultClass(state) {
            if (!state || state.status === 'loading') return '';
            if (state.status === 'error') return 'error';
            const probe = state.health && state.health.probe && typeof state.health.probe === 'object' ? state.health.probe : {};
            const status = String(probe.status || '').trim().toLowerCase();
            if (status === 'ok' || probe.ok === true) return 'ok';
            if (status === 'skipped') return 'skipped';
            if (status === 'error' || probe.ok === false) return 'error';
            return '';
        }

        function getProviderHealthStaticText(item) {
            const kind = String(item?.kind || '').trim().toLowerCase();
            const status = String(item?.status || '').trim().toLowerCase();
            if (kind !== 'temp') return translateAppTextLocal('账号池不用探测');
            if (item?.active === false) return translateAppTextLocal('未启用');
            if (status !== 'ready') return translateAppTextLocal('先补齐配置');
            return '';
        }

        async function probeMailboxProviderHealth(kind, providerName) {
            const normalizedKind = String(kind || '').trim().toLowerCase();
            const normalizedProvider = normalizeProviderCatalogName(providerName);
            if (!normalizedKind || !normalizedProvider) return;

            const healthKey = getProviderHealthKey(normalizedKind, normalizedProvider);
            if (mailboxProviderHealthPending.has(healthKey)) return;
            mailboxProviderHealthPending.add(healthKey);
            mailboxProviderHealthState[healthKey] = { status: 'loading' };
            rerenderProviderConsoleFromCache();

            try {
                const endpoint = `/api/providers/${encodeURIComponent(normalizedKind)}/${encodeURIComponent(normalizedProvider)}/health?probe_network=true`;
                const response = await fetch(endpoint, { cache: 'no-store' });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || !data.success) {
                    const errorPayload = data.error || data || { code: `HTTP_${response.status}` };
                    const error = new Error(errorPayload.message || `HTTP ${response.status}`);
                    error.payload = errorPayload;
                    throw error;
                }

                const health = data.provider_health && typeof data.provider_health === 'object' ? data.provider_health : {};
                mailboxProviderHealthState[healthKey] = { status: 'ready', health };
                const probe = health.probe && typeof health.probe === 'object' ? health.probe : {};
                if (probe.status === 'ok' || probe.ok === true) {
                    const successMessage = probe.network_probe === false
                        ? 'Provider 本地检查通过'
                        : 'Provider 上游探测通过';
                    showToast(translateAppTextLocal(successMessage), 'success');
                } else if (probe.status === 'skipped') {
                    showToast(translateAppTextLocal('Provider 探测已跳过'), 'warning');
                } else {
                    showToast(translateAppTextLocal('Provider 上游探测失败'), 'warning');
                }
            } catch (error) {
                mailboxProviderHealthState[healthKey] = { status: 'error', error: error.payload || error };
                showToast(translateAppTextLocal('Provider 上游探测失败'), 'error', error.payload || null);
            } finally {
                mailboxProviderHealthPending.delete(healthKey);
                rerenderProviderConsoleFromCache();
            }
        }

