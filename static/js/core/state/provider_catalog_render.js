// split from provider_catalog.js → render.js
        function dedupeMailboxProviderDiagnosticRows(providers) {
            // Collapse dual temp bridge rows (custom_domain_temp_mail + legacy_bridge)
            // in diagnostics summary/console for operator-facing uniqueness.
            const map = new Map();
            (Array.isArray(providers) ? providers : []).forEach(item => {
                if (!item || typeof item !== 'object') return;
                const rawProvider = String(item.provider || item.name || item.key || '').trim();
                if (!rawProvider) return;
                const kind = String(item.kind || '').trim().toLowerCase();
                const canonical = kind === 'account'
                    ? rawProvider.toLowerCase()
                    : (canonicalizeMailboxProviderAllowlistValue(rawProvider) || rawProvider.toLowerCase());
                if (!canonical || canonical === 'auto') return;
                const existing = map.get(canonical);
                if (!existing) {
                    map.set(canonical, {
                        ...item,
                        provider: canonical,
                    });
                    return;
                }
                const mergedMissing = [
                    ...(Array.isArray(existing.missing_config) ? existing.missing_config : []),
                    ...(Array.isArray(item.missing_config) ? item.missing_config : []),
                ];
                const missingSeen = new Set();
                const missingConfig = mergedMissing.filter(entry => {
                    const key = String(entry || '').trim();
                    if (!key || missingSeen.has(key)) return false;
                    missingSeen.add(key);
                    return true;
                });
                map.set(canonical, {
                    ...existing,
                    ...item,
                    provider: canonical,
                    label: existing.label || item.label || item.provider_label || canonical,
                    provider_label: existing.provider_label || item.provider_label || existing.label || canonical,
                    active: existing.active === true || item.active === true,
                    configured: existing.configured === true || item.configured === true,
                    can_dynamic_create: existing.can_dynamic_create === true || item.can_dynamic_create === true,
                    status: (
                        String(existing.status || '') === 'ready'
                        || String(item.status || '') === 'ready'
                    ) ? 'ready' : (existing.status || item.status),
                    missing_config: missingConfig,
                });
            });
            return Array.from(map.values());
        }

        function renderPoolDefaultProviderDatalist() {
            const mount = document.getElementById('poolDefaultProviderOptions');
            if (!mount) return;
            const values = getPoolDefaultProviderAllowedValues();
            mount.innerHTML = values
                .map(value => `<option value="${escapeHtml(value)}"></option>`)
                .join('');
        }

        function renderActiveMailboxProviderSuggestions() {
            const mount = document.getElementById('activeMailboxProviderSuggestions');
            if (!mount) return;
            const values = getActiveMailboxProviderAllowedValues();
            if (!values.length) {
                mount.innerHTML = `<div class="form-hint">${escapeHtml(translateAppTextLocal('暂无可用来源建议'))}</div>`;
                return;
            }
            const selected = new Set(getActiveMailboxProvidersFromTextarea());
            mount.innerHTML = [
                `<div class="active-mailbox-provider-suggestions-label">${escapeHtml(translateAppTextLocal('可用来源建议'))}</div>`,
                '<div class="active-mailbox-provider-suggestion-list" role="group" aria-label="' + escapeHtml(translateAppTextLocal('启用邮箱来源建议')) + '">',
                values.map(value => {
                    const active = selected.has(value);
                    const label = typeof resolveMailboxProviderLabel === 'function'
                        ? (resolveMailboxProviderLabel(value, {
                            softLoad: false,
                            emptyLabel: '',
                            fallbackResolver: () => value,
                        }) || value)
                        : value;
                    return [
                        `<button type="button" class="active-mailbox-provider-chip${active ? ' active' : ''}" data-active-mailbox-provider="${escapeHtml(value)}" aria-pressed="${active ? 'true' : 'false'}">`,
                        escapeHtml(label),
                        '</button>',
                    ].join('');
                }).join(''),
                '</div>',
            ].join('');

            if (mount.dataset.boundActiveMailboxSuggestions !== 'true') {
                mount.addEventListener('click', event => {
                    const target = event.target;
                    if (!target || !target.closest) return;
                    const chip = target.closest('[data-active-mailbox-provider]');
                    if (!chip) return;
                    toggleActiveMailboxProviderSuggestion(chip.getAttribute('data-active-mailbox-provider') || '');
                });
                mount.dataset.boundActiveMailboxSuggestions = 'true';
            }

            const textarea = document.getElementById('activeMailboxProviders');
            if (textarea && textarea.dataset.boundActiveMailboxSuggestions !== 'true') {
                textarea.addEventListener('input', () => {
                    renderActiveMailboxProviderSuggestions();
                });
                textarea.dataset.boundActiveMailboxSuggestions = 'true';
            }
        }

        // API-security tab command-center / preflight chrome only.
        function renderExternalProviderRecipeCodeSection(label, content) {
            const value = String(content || '').trim();
            if (!value) return '';
            return [
                '<div class="external-api-recipe-code-block">',
                    `<div class="external-api-recipe-code-label">${escapeHtml(translateAppTextLocal(label))}</div>`,
                    `<pre class="external-api-command-code external-api-recipe-code"><code>${escapeHtml(value)}</code></pre>`,
                '</div>'
            ].join('');
        }

        function renderExternalProviderRecipeTab(recipe, selectedKey) {
            const active = recipe.key === selectedKey;
            const scopeLabel = getExternalProviderRecipeScopeLabel(recipe.scope);
            const kindLabel = getExternalProviderRecipeKindLabel(recipe.kind);
            return [
                `<button type="button" class="external-api-recipe-tab${active ? ' active' : ''}" data-external-provider-recipe-key="${escapeHtml(recipe.key)}" aria-pressed="${active ? 'true' : 'false'}">`,
                    `<span>${escapeHtml(recipe.label || recipe.provider)}</span>`,
                    `<small>${escapeHtml(scopeLabel)} · ${escapeHtml(kindLabel)}</small>`,
                '</button>'
            ].join('');
        }

        function renderExternalProviderRecipeDetail(recipe) {
            if (!recipe) return '';
            const configuration = recipe.configuration && typeof recipe.configuration === 'object' ? recipe.configuration : {};
            const providerConfig = configuration.provider_config && typeof configuration.provider_config === 'object' ? configuration.provider_config : {};
            const request = recipe.request && typeof recipe.request === 'object' ? recipe.request : {};
            const secretEnvKeys = getExternalProviderRecipeSecretEnvKeys(recipe);
            const envSnippet = buildExternalProviderRecipeEnvSnippet(configuration.env, secretEnvKeys);
            const providerEnvSnippet = buildExternalProviderRecipeProviderEnvSnippet(recipe);
            const settingsSnippet = formatExternalProviderRecipeJson(configuration.settings);
            const providerConfigJson = String(providerConfig.json || '').trim() || formatExternalProviderRecipeJson(providerConfig.object);
            const providerConfigToml = String(providerConfig.toml || '').trim();
            const requestBody = request.body && typeof request.body === 'object'
                ? formatExternalProviderRecipeJson(request.body)
                : (request.field ? formatExternalProviderRecipeJson({ [request.field]: request.value }) : '');
            const method = String(request.method || (recipe.endpoint ? 'POST' : '')).trim().toUpperCase();
            const endpoint = String(recipe.endpoint || '').trim();
            const priority = Array.isArray(recipe.source_priority) ? recipe.source_priority.map(item => String(item || '').trim()).filter(Boolean) : [];
            const requiredFields = Array.isArray(request.required_body_fields)
                ? request.required_body_fields.map(item => String(item || '').trim()).filter(Boolean)
                : [];
            const requestLines = [
                method || endpoint ? `${method || 'POST'} ${endpoint}`.trim() : '',
                requiredFields.length ? `required_body_fields: ${requiredFields.join(', ')}` : '',
                requestBody ? `body:\n${requestBody}` : '',
            ].filter(Boolean).join('\n');
            const chips = [
                getExternalProviderRecipeScopeLabel(recipe.scope),
                recipe.provider,
                getExternalProviderRecipeKindLabel(recipe.kind),
                recipe.active === false ? translateAppTextLocal('未启用') : translateAppTextLocal('已启用')
            ].filter(Boolean);
            return [
                '<div class="external-api-recipe-detail">',
                    '<div class="external-api-recipe-detail-head">',
                        '<div>',
                            `<div class="external-api-recipe-title">${escapeHtml(recipe.label || recipe.provider)}</div>`,
                            recipe.description ? `<div class="external-api-recipe-desc">${escapeHtml(translateAppTextLocal(recipe.description))}</div>` : '',
                        '</div>',
                        `<div class="external-api-recipe-chips">${chips.map(item => `<span>${escapeHtml(item)}</span>`).join('')}</div>`,
                    '</div>',
                    priority.length ? `<div class="external-api-command-priority external-api-recipe-priority"><span>${escapeHtml(translateAppTextLocal('来源优先级'))}</span><code>${escapeHtml(priority.join(' > '))}</code></div>` : '',
                    '<div class="external-api-recipe-code-grid">',
                        renderExternalProviderRecipeCodeSection('配置 Env', envSnippet),
                        renderExternalProviderRecipeCodeSection('Provider env hints', providerEnvSnippet),
                        renderExternalProviderRecipeCodeSection('Provider config JSON', providerConfigJson),
                        renderExternalProviderRecipeCodeSection('Provider config TOML', providerConfigToml),
                        renderExternalProviderRecipeCodeSection('Settings payload', settingsSnippet),
                        renderExternalProviderRecipeCodeSection('Request body', requestLines),
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalProviderRecipeGuide(recipes = getExternalProviderSelectionRecipes()) {
            const values = Array.isArray(recipes) ? recipes.map(normalizeExternalProviderRecipe).filter(Boolean) : [];
            if (!values.length) {
                return `<div class="external-api-recipe-guide"><div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('暂无 provider selection recipes'))}</div></div>`;
            }
            externalProviderRecipeKey = normalizeExternalProviderRecipeKey(externalProviderRecipeKey, values);
            const selectedRecipe = values.find(item => item.key === externalProviderRecipeKey) || values[0];
            return [
                '<div class="external-api-recipe-guide">',
                    '<div class="external-api-recipe-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('Provider 选择 Recipes'))}</div>`,
                            `<div class="external-api-recipe-subtitle">${escapeHtml(translateAppTextLocal('从当前 integration_manifest 读取 provider 选择示例'))}</div>`,
                        '</div>',
                        `<button type="button" class="external-api-command-copy external-api-recipe-copy" data-external-provider-recipe-copy>${escapeHtml(translateAppTextLocal('复制 Recipe'))}</button>`,
                    '</div>',
                    '<div class="external-api-recipe-body">',
                        `<div class="external-api-recipe-tabs" role="group" aria-label="${escapeHtml(translateAppTextLocal('外部 Provider Recipe'))}">${values.map(item => renderExternalProviderRecipeTab(item, selectedRecipe.key)).join('')}</div>`,
                        renderExternalProviderRecipeDetail(selectedRecipe),
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderProviderContractCounter(label, value, tone) {
            return [
                `<div class="provider-contract-counter ${escapeHtml(tone || 'unknown')}">`,
                    `<span>${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<strong>${escapeHtml(String(value))}</strong>`,
                '</div>'
            ].join('');
        }

        function renderProviderContractIssueCodes(issueCodes) {
            const codes = Array.isArray(issueCodes) ? issueCodes.filter(Boolean) : [];
            if (!codes.length) return `<span class="provider-contract-muted">${escapeHtml(translateAppTextLocal('无 issue code'))}</span>`;
            return codes.map(code => `<span class="provider-contract-chip">${escapeHtml(code)}</span>`).join('');
        }

        function renderProviderContractRow(row, pluginMap) {
            const contract = normalizeProviderContractSummary(row.contract, row.provider);
            const plugin = pluginMap.get(row.provider) || null;
            const pluginContract = plugin ? plugin.contract : null;
            const displayContract = pluginContract && pluginContract.status !== 'unknown' ? pluginContract : contract;
            const tone = getProviderContractStatusTone(displayContract);
            const summary = displayContract.summary || {};
            const pluginText = plugin
                ? `${translateAppTextLocal('插件')} ${translateAppTextLocal(plugin.status || 'installed')}`
                : translateAppTextLocal('内置或 catalog provider');
            const readiness = [
                row.active === false ? translateAppTextLocal('未启用') : '',
                row.configured === false ? translateAppTextLocal('配置缺失') : '',
                row.readiness_status ? getProviderStatusLabel(row.readiness_status) : '',
            ].filter(Boolean).join(' · ');
            const rowLabel = typeof resolveMailboxProviderLabel === 'function'
                ? (resolveMailboxProviderLabel(row.provider, {
                    softLoad: false,
                    emptyLabel: '',
                    fallbackResolver: () => String(row.label || '').trim(),
                }) || row.label || row.provider)
                : (row.label || row.provider);
            return [
                `<div class="provider-contract-row ${escapeHtml(tone)}">`,
                    '<div class="provider-contract-main">',
                        `<span class="provider-contract-label">${escapeHtml(rowLabel)}</span>`,
                        `<code>${escapeHtml(row.provider)}</code>`,
                        `<span class="provider-console-kind">${escapeHtml(getProviderKindLabel(row.kind || 'temp'))}</span>`,
                    '</div>',
                    '<div class="provider-contract-state">',
                        `<span class="badge ${escapeHtml(tone === 'valid' ? 'badge-green' : tone === 'invalid' ? 'badge-red' : tone === 'warning' ? 'badge-gold' : 'badge-gray')}">${escapeHtml(getProviderContractStatusLabel(tone))}</span>`,
                        `<span>${escapeHtml(`${summary.errors || 0} errors · ${summary.warnings || 0} warnings · ${summary.checks || 0} checks`)}</span>`,
                    '</div>',
                    `<div class="provider-contract-issues">${renderProviderContractIssueCodes(displayContract.issue_codes)}</div>`,
                    '<div class="provider-contract-plugin">',
                        `<span>${escapeHtml(pluginText)}</span>`,
                        readiness ? `<small>${escapeHtml(readiness)}</small>` : '',
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderProviderContractStatus() {
            const root = document.getElementById('providerContractStatus');
            if (!root) return;
            const summaryEl = document.getElementById('providerContractStatusSummary');
            const listEl = document.getElementById('providerContractStatusList');
            const rows = Array.isArray(providerContractState.catalog) ? providerContractState.catalog : [];
            const pluginMap = getProviderContractPluginMap();
            const mergedRows = rows.map(row => {
                const plugin = pluginMap.get(row.provider);
                return plugin && (!row.contract || row.contract.status === 'unknown')
                    ? { ...row, contract: plugin.contract, label: row.label || plugin.display_name }
                    : row;
            });
            const sortOrder = { invalid: 0, warning: 1, unknown: 2, valid: 3 };
            mergedRows.sort((a, b) => {
                const aTone = getProviderContractStatusTone(a.contract);
                const bTone = getProviderContractStatusTone(b.contract);
                return (sortOrder[aTone] ?? 9) - (sortOrder[bTone] ?? 9) || String(a.provider).localeCompare(String(b.provider));
            });
            const counts = { valid: 0, warning: 0, invalid: 0, unknown: 0 };
            mergedRows.forEach(row => {
                const tone = getProviderContractStatusTone(row.contract);
                counts[tone] = (counts[tone] || 0) + 1;
            });
            if (summaryEl) {
                summaryEl.innerHTML = [
                    renderProviderContractCounter('契约有效', counts.valid, 'valid'),
                    renderProviderContractCounter('契约告警', counts.warning, 'warning'),
                    renderProviderContractCounter('契约无效', counts.invalid, 'invalid'),
                    renderProviderContractCounter('契约未知', counts.unknown, 'unknown'),
                ].join('');
            }
            if (!mergedRows.length) {
                if (listEl) listEl.innerHTML = `<div class="provider-contract-empty">${escapeHtml(translateAppTextLocal('Provider 扩展契约暂不可用'))}</div>`;
                return;
            }
            if (listEl) listEl.innerHTML = mergedRows.map(row => renderProviderContractRow(row, pluginMap)).join('');
        }

        function renderProviderPreflightCounter(label, value, detail = '', tone = '') {
            return [
                `<div class="provider-preflight-counter ${escapeHtml(tone || 'muted')}">`,
                    `<span>${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<strong>${escapeHtml(String(value ?? 0))}</strong>`,
                    detail ? `<small>${escapeHtml(translateAppTextLocal(detail))}</small>` : '',
                '</div>'
            ].join('');
        }

        function renderProviderPreflightChips(values, emptyText) {
            const chips = Array.isArray(values)
                ? values.map(value => String(value || '').trim()).filter(Boolean)
                : [];
            if (!chips.length) {
                return `<span class="provider-preflight-muted">${escapeHtml(translateAppTextLocal(emptyText || '无'))}</span>`;
            }
            return chips.map(value => `<span class="provider-preflight-chip">${escapeHtml(value)}</span>`).join('');
        }

        function renderProviderPreflightProviderRow(row) {
            const item = row && typeof row === 'object' ? row : {};
            const providerName = String(item.provider || '').trim();
            const label = String(item.label || providerName || '').trim();
            const kind = String(item.kind || '').trim().toLowerCase();
            const localStatus = String(item.local_status || '').trim().toLowerCase();
            const statusTone = getProviderStatusBadgeClass(localStatus);
            const probe = item.probe && typeof item.probe === 'object' ? item.probe : {};
            const probeTone = getProviderPreflightProbeTone(probe);
            const probeCode = String(probe.error_code || '').trim();
            const endpoint = item.endpoints && typeof item.endpoints === 'object'
                ? String(item.endpoints.health || item.endpoints.preflight || '').trim()
                : '';
            const configText = renderProviderPreflightChips(item.missing_config, '本地配置齐全');
            const localDetail = [
                item.active === false ? translateAppTextLocal('未启用') : '',
                item.configured === false ? translateAppTextLocal('配置缺失') : '',
                item.can_dynamic_create ? translateAppTextLocal('可动态创建') : ''
            ].filter(Boolean).join(' · ');
            const probeDetail = [getProviderPreflightProbeLabel(probe), probeCode].filter(Boolean).join(' · ');

            return [
                `<div class="provider-preflight-row ${escapeHtml(getProviderPreflightStatusTone(localStatus))}">`,
                    '<div class="provider-preflight-main">',
                        `<span class="provider-preflight-label">${escapeHtml(label)}</span>`,
                        `<code>${escapeHtml(providerName)}</code>`,
                        `<span class="provider-console-kind">${escapeHtml(getProviderKindLabel(kind))}</span>`,
                    '</div>',
                    '<div class="provider-preflight-state">',
                        `<span class="badge ${escapeHtml(statusTone)}">${escapeHtml(getProviderStatusLabel(localStatus))}</span>`,
                        localDetail ? `<small>${escapeHtml(localDetail)}</small>` : '',
                    '</div>',
                    `<div class="provider-preflight-config">${configText}</div>`,
                    '<div class="provider-preflight-probe-state">',
                        `<span class="provider-preflight-probe-state-label ${escapeHtml(probeTone)}">${escapeHtml(probeDetail)}</span>`,
                        endpoint ? `<small>${escapeHtml(endpoint)}</small>` : '',
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderProviderPreflightConsole(state = providerPreflightState) {
            const root = document.getElementById('providerPreflightConsole');
            if (!root) return;
            const summaryEl = document.getElementById('providerPreflightSummary');
            const listEl = document.getElementById('providerPreflightList');
            const probeButton = root.querySelector('[data-provider-preflight-probe]');
            const currentState = state && typeof state === 'object' ? state : providerPreflightState;
            const snapshot = getProviderPreflightSnapshot();
            const isPending = currentState.status === 'loading' || currentState.status === 'probing';
            const rows = snapshot && Array.isArray(snapshot.providers)
                ? snapshot.providers.filter(item => item && typeof item === 'object')
                : [];
            const summary = snapshot && snapshot.summary && typeof snapshot.summary === 'object' ? snapshot.summary : {};
            const scope = snapshot && snapshot.scope && typeof snapshot.scope === 'object' ? snapshot.scope : {};
            const status = isPending ? currentState.status : String(snapshot?.status || currentState.status || 'idle').trim().toLowerCase();
            const tone = getProviderPreflightStatusTone(status);

            root.setAttribute('data-state', status || 'idle');
            root.setAttribute('data-tone', tone);
            if (probeButton) {
                probeButton.disabled = isPending;
                probeButton.textContent = translateAppTextLocal(currentState.status === 'probing' ? '探测中…' : '显式探测');
                probeButton.setAttribute('aria-busy', isPending ? 'true' : 'false');
            }

            if (summaryEl) {
                if (currentState.status === 'error' && !snapshot) {
                    summaryEl.innerHTML = `<div class="provider-preflight-empty error">${escapeHtml(translateAppTextLocal('Provider 预检暂不可用'))}</div>`;
                } else if (isPending && !snapshot) {
                    summaryEl.innerHTML = `<div class="provider-preflight-empty">${escapeHtml(translateAppTextLocal(currentState.status === 'probing' ? '探测中…' : '预检中…'))}</div>`;
                } else {
                    summaryEl.innerHTML = [
                        renderProviderPreflightCounter('总数', summary.total ?? rows.length, getProviderPreflightStatusLabel(status), tone),
                        renderProviderPreflightCounter('就绪', summary.ready ?? 0, '本地只读', 'ready'),
                        renderProviderPreflightCounter('缺配置', summary.needs_config ?? 0, '需要配置', summary.needs_config > 0 ? 'warning' : 'muted'),
                        renderProviderPreflightCounter('未启用', summary.inactive ?? 0, '', summary.inactive > 0 ? 'muted' : 'ready'),
                        renderProviderPreflightCounter('已探测', summary.probed ?? 0, scope.network_probe ? '显式网络探测' : '本地只读', scope.network_probe ? 'ready' : 'muted'),
                        renderProviderPreflightCounter('探测失败', summary.probe_failed ?? 0, '', summary.probe_failed > 0 ? 'error' : 'ready'),
                    ].join('');
                }
            }

            if (listEl) {
                if (currentState.status === 'error' && !snapshot) {
                    listEl.innerHTML = `<div class="provider-preflight-empty error">${escapeHtml(translateAppTextLocal('Provider 预检暂不可用'))}</div>`;
                } else if (isPending && !rows.length) {
                    listEl.innerHTML = `<div class="provider-preflight-empty">${escapeHtml(translateAppTextLocal(currentState.status === 'probing' ? '探测中…' : '预检中…'))}</div>`;
                } else if (!rows.length) {
                    listEl.innerHTML = `<div class="provider-preflight-empty">${escapeHtml(translateAppTextLocal('暂无 Provider 预检结果'))}</div>`;
                } else {
                    listEl.innerHTML = rows.map(renderProviderPreflightProviderRow).join('');
                }
            }
        }

        function renderProviderWorkbenchDiscovery(firstEndpoint, sourcePriorityText) {
            const endpoint = String(firstEndpoint || externalApiCanonicalPath('/capabilities')).trim() || externalApiCanonicalPath('/capabilities');
            const priority = String(sourcePriorityText || '').trim() || 'env > provider_config_file > settings > default';
            return [
                '<div class="provider-workbench-discovery">',
                    `<span class="provider-workbench-discovery-label">${escapeHtml(translateAppTextLocal('发现入口'))}</span>`,
                    '<div class="provider-workbench-discovery-copy">',
                        `<div>${escapeHtml(translateAppTextLocal('外部项目先读取'))} <code>${escapeHtml(endpoint)}</code></div>`,
                        `<small>${escapeHtml(translateAppTextLocal('Provider 选择按'))} <code>${escapeHtml(priority)}</code></small>`,
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderProviderWorkbenchMetric(label, value, detail = '', tone = '') {
            return [
                `<div class="provider-workbench-metric ${escapeHtml(tone)}">`,
                    `<span class="provider-workbench-metric-label">${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<strong>${escapeHtml(value)}</strong>`,
                    detail ? `<span class="provider-workbench-metric-detail">${escapeHtml(detail)}</span>` : '',
                '</div>'
            ].join('');
        }

        function renderProviderWorkbench(settings = {}, state = 'ready') {
            const root = document.getElementById('providerWorkbench');
            const summaryEl = document.getElementById('providerWorkbenchSummary');
            if (!root || !summaryEl) return;

            const safeSettings = settings && typeof settings === 'object' ? settings : {};
            const renderState = state || 'ready';
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const providers = dedupeMailboxProviderDiagnosticRows(
                Array.isArray(diagnostics.providers) ? diagnostics.providers.filter(item => item && typeof item === 'object') : []
            );
            const routeMode = getExternalApiCommandRouteMode(safeSettings);
            const providerSummary = getExternalApiCommandProviderSummary(renderState);
            const sourcePriority = getExternalApiCommandSourcePriority();
            const sourcePriorityText = sourcePriority.length ? sourcePriority.join(' > ') : 'env > provider_config_file > settings > default';
            const poolStatus = getExternalApiCommandPoolStatus(safeSettings);
            const configStatus = getProviderWorkbenchConfigFileStatus(safeSettings);
            const secretPolicyText = getProviderWorkbenchSecretPolicyText();
            const runtimeDefault = getProviderWorkbenchRuntimeDefault(safeSettings);
            const poolDefault = String(safeSettings.pool_default_provider || '').trim() || 'auto';
            const providerCountText = providerSummary.unavailable && !providers.length
                ? translateAppTextLocal('暂不可用')
                : providerSummary.value;
            const badge = document.getElementById('providerWorkbenchBadge');
            const badgeReady = !providerSummary.unavailable && configStatus.tone !== 'warning';

            root.setAttribute('data-state', renderState);
            if (badge) {
                badge.className = `badge ${badgeReady ? 'badge-green' : 'badge-gold'}`;
                badge.textContent = badgeReady ? translateAppTextLocal('可审计') : translateAppTextLocal('需检查');
            }

            if (renderState === 'loading' && !Object.keys(safeSettings).length && !providers.length) {
                summaryEl.innerHTML = `<div class="provider-workbench-empty">${escapeHtml(translateAppTextLocal('加载邮箱来源运营台…'))}</div>`;
                return;
            }

            const endpointMap = getExternalApiStarterEndpointMap();
            summaryEl.innerHTML = [
                renderProviderWorkbenchDiscovery(endpointMap.capabilities, sourcePriorityText),
                renderProviderWorkbenchMetric('运行默认', runtimeDefault.value, runtimeDefault.detail),
                renderProviderWorkbenchMetric('默认领取来源', poolDefault, poolStatus.detail),
                renderProviderWorkbenchMetric('路由模式', routeMode.value, routeMode.detail),
                renderProviderWorkbenchMetric('Provider 就绪', translateAppTextLocal(providerCountText), providerSummary.detail, providerSummary.unavailable ? 'warning' : ''),
                renderProviderWorkbenchMetric('配置文件', configStatus.label, configStatus.detail, configStatus.tone),
                renderProviderWorkbenchMetric('来源优先级', sourcePriorityText, translateAppTextLocal('Provider 选择顺序')),
                renderProviderWorkbenchMetric('密钥策略', secretPolicyText, translateAppTextLocal('只显示字段名，不显示密钥值')),
            ].join('');
        }

        function renderProviderIntegrationKeyChips(keys, emptyText = '无') {
            const values = Array.isArray(keys) ? keys.map(value => String(value || '').trim()).filter(Boolean) : [];
            if (!values.length) {
                return `<span class="provider-integration-muted">${escapeHtml(translateAppTextLocal(emptyText))}</span>`;
            }
            return values.map(value => `<span class="provider-integration-chip">${escapeHtml(value)}</span>`).join('');
        }

        function renderProviderIntegrationField(label, htmlValue) {
            return [
                '<div class="provider-integration-field">',
                    `<span class="provider-integration-field-label">${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<span class="provider-integration-field-value">${htmlValue}</span>`,
                '</div>'
            ].join('');
        }

        function renderProviderIntegrationStep(label, text) {
            const value = String(text || '').trim();
            if (!value) return '';
            return [
                '<div class="provider-integration-step">',
                    `<span class="provider-integration-step-label">${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<code>${escapeHtml(value)}</code>`,
                '</div>'
            ].join('');
        }

        function renderProviderIntegrationGuide() {
            const root = document.getElementById('providerIntegrationGuide');
            if (!root) return;
            syncProviderIntegrationFilterButtons();

            const summaryEl = document.getElementById('providerIntegrationGuideSummary');
            const listEl = document.getElementById('providerIntegrationGuideList');
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            const providers = getProviderIntegrationGuideProviders();
            if (!providers.length) {
                if (summaryEl) summaryEl.textContent = translateAppTextLocal('Provider 接入指南暂不可用');
                if (listEl) listEl.innerHTML = `<div class="provider-integration-guide-empty">${escapeHtml(translateAppTextLocal('Provider 接入指南暂不可用'))}</div>`;
                return;
            }

            const sourcePriority = Array.isArray(guide.source_priority) ? guide.source_priority.join(' > ') : '';
            const workflow = guide.workflow && typeof guide.workflow === 'object' ? guide.workflow : {};
            const discoverProviders = workflow.discover_providers && typeof workflow.discover_providers === 'object' ? workflow.discover_providers : {};
            const providerFilter = guide.provider_filter && typeof guide.provider_filter === 'object' ? guide.provider_filter : {};
            const secretPolicy = guide.secret_policy && typeof guide.secret_policy === 'object' ? guide.secret_policy : {};
            const filterText = translateAppTextLocal(providerFilter.active ? '白名单' : '全部启用');
            const secretText = secretPolicy.exposes_secret_values === false
                ? translateAppTextLocal('只显示密钥字段名')
                : translateAppTextLocal('密钥策略未知');
            const summaryParts = [
                sourcePriority ? `${translateAppTextLocal('优先级')} ${sourcePriority}` : '',
                discoverProviders.endpoint ? `${translateAppTextLocal('发现接口')} ${discoverProviders.endpoint}` : '',
                `${translateAppTextLocal('启用')} ${filterText}`,
                secretText,
            ].filter(Boolean);
            if (summaryEl) summaryEl.textContent = summaryParts.join(' · ');

            const visibleProviders = getProviderIntegrationFilteredProviders(providers);
            if (!visibleProviders.length) {
                if (listEl) listEl.innerHTML = `<div class="provider-integration-guide-empty">${escapeHtml(translateAppTextLocal('当前筛选下没有邮箱来源'))}</div>`;
                return;
            }

            const rows = visibleProviders.map(provider => {
                const providerName = String(provider.provider || '').trim();
                const label = typeof resolveMailboxProviderLabel === 'function'
                    ? String(resolveMailboxProviderLabel(providerName, {
                        softLoad: false,
                        emptyLabel: '',
                        fallbackResolver: () => String(provider.label || provider.display_name || '').trim(),
                    }) || providerName).trim()
                    : String(provider.label || providerName || '').trim();
                const kind = String(provider.kind || '').trim().toLowerCase();
                const status = String(provider.readiness_status || '').trim().toLowerCase();
                const aliasesText = getProviderIntegrationAliasesText(provider);
                const fields = [
                    renderProviderIntegrationField('必需环境变量', renderProviderIntegrationKeyChips(provider.required_env)),
                    renderProviderIntegrationField('可选环境变量', renderProviderIntegrationKeyChips(provider.optional_env)),
                    renderProviderIntegrationField('配置项', renderProviderIntegrationKeyChips(provider.settings_keys)),
                    aliasesText ? renderProviderIntegrationField('别名', `<span class="provider-integration-aliases">${escapeHtml(aliasesText)}</span>`) : '',
                ].filter(Boolean).join('');
                const steps = [
                    renderProviderIntegrationStep('激活', formatProviderIntegrationStep(provider, provider.activation)),
                    renderProviderIntegrationStep('运行默认', formatProviderIntegrationStep(provider, provider.runtime_default)),
                    renderProviderIntegrationStep('领取默认', formatProviderIntegrationStep(provider, provider.pool_claim_default)),
                    renderProviderIntegrationStep('领取请求', getProviderIntegrationRequestText(provider.pool_claim_request)),
                    renderProviderIntegrationStep('任务邮箱申请', getProviderIntegrationRequestText(provider.task_temp_apply_request)),
                ].filter(Boolean).join('');
                return [
                    '<div class="provider-integration-card">',
                        '<div class="provider-integration-card-head">',
                            '<div class="provider-integration-provider">',
                                `<span class="provider-integration-label">${escapeHtml(label)}</span>`,
                                `<code>${escapeHtml(providerName)}</code>`,
                                `<span class="provider-console-kind">${escapeHtml(getProviderKindLabel(kind))}</span>`,
                            '</div>',
                            '<div class="provider-integration-actions">',
                                `<span class="badge ${escapeHtml(getProviderStatusBadgeClass(status))}">${escapeHtml(getProviderStatusLabel(status))}</span>`,
                                `<button type="button" class="provider-integration-copy" data-provider-integration-copy data-provider-kind="${escapeHtml(kind)}" data-provider-name="${escapeHtml(providerName)}">${escapeHtml(translateAppTextLocal('复制接入片段'))}</button>`,
                            '</div>',
                        '</div>',
                        fields ? `<div class="provider-integration-fields">${fields}</div>` : '',
                        steps ? `<div class="provider-integration-steps">${steps}</div>` : '',
                    '</div>'
                ].join('');
            }).join('');

            if (listEl) listEl.innerHTML = rows;
        }

        function renderProviderHealthCell(item) {
            const kind = String(item?.kind || '').trim().toLowerCase();
            const providerName = String(item?.provider || '').trim();
            const healthColumnLabel = translateAppTextLocal('上游探测');
            const staticText = getProviderHealthStaticText(item);
            if (staticText) {
                return `<div class="provider-console-cell provider-console-health" data-column-label="${escapeHtml(healthColumnLabel)}"><span class="provider-console-mobile-label">${escapeHtml(healthColumnLabel)}</span><span class="provider-health-muted">${escapeHtml(staticText)}</span></div>`;
            }

            const healthKey = getProviderHealthKey(kind, providerName);
            const isPending = mailboxProviderHealthPending.has(healthKey);
            const state = mailboxProviderHealthState[healthKey] || null;
            const resultText = getProviderHealthResultText(state);
            const resultClass = getProviderHealthResultClass(state);
            const buttonText = isPending
                ? translateAppTextLocal('探测中…')
                : translateAppTextLocal(state ? '重新探测' : '探测');
            const resultHtml = resultText
                ? `<span class="provider-health-result ${escapeHtml(resultClass)}">${escapeHtml(resultText)}</span>`
                : '';

            return [
                `<div class="provider-console-cell provider-console-health" data-column-label="${escapeHtml(healthColumnLabel)}">`,
                    `<span class="provider-console-mobile-label">${escapeHtml(healthColumnLabel)}</span>`,
                    '<div class="provider-health-actions">',
                        `<button type="button" class="provider-health-button" data-provider-health-action data-provider-kind="${escapeHtml(kind)}" data-provider-name="${escapeHtml(providerName)}"${isPending ? ' disabled' : ''}>${escapeHtml(buttonText)}</button>`,
                        resultHtml,
                    '</div>',
                '</div>'
            ].join('');
        }

        function rerenderProviderConsoleFromCache() {
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const providers = dedupeMailboxProviderDiagnosticRows(
                Array.isArray(diagnostics.providers) ? diagnostics.providers : []
            );
            renderProviderConsole(providers);
        }

        function normalizeProviderConsoleFilter(filterName) {
            const normalized = String(filterName || 'all').trim().toLowerCase();
            return ['all', 'active', 'temp', 'account', 'needs_config'].includes(normalized) ? normalized : 'all';
        }

        function syncProviderConsoleFilterButtons() {
            mailboxProviderConsoleFilter = normalizeProviderConsoleFilter(mailboxProviderConsoleFilter);
            document.querySelectorAll('[data-provider-console-filter]').forEach(button => {
                const active = String(button.getAttribute('data-provider-console-filter') || '').trim().toLowerCase() === mailboxProviderConsoleFilter;
                button.classList.toggle('active', active);
                button.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
        }

        function renderProviderConsole(providers) {
            const root = document.getElementById('providerConsoleTable');
            if (!root) return;
            syncProviderConsoleFilterButtons();
            const safeProviders = Array.isArray(providers)
                ? providers.filter(item => item && typeof item === 'object')
                : [];
            if (!safeProviders.length) {
                root.innerHTML = `<div class="provider-console-empty">${escapeHtml(translateAppTextLocal('邮箱来源控制台暂不可用'))}</div>`;
                return;
            }

            const visibleProviders = getProviderFilteredItems(safeProviders);
            if (!visibleProviders.length) {
                root.innerHTML = `<div class="provider-console-empty">${escapeHtml(translateAppTextLocal('当前筛选下没有邮箱来源'))}</div>`;
                return;
            }

            const rows = visibleProviders.map(item => {
                const providerName = String(item.provider || '').trim();
                const label = String(item.label || providerName || '').trim();
                const status = String(item.status || '').trim().toLowerCase();
                const kind = String(item.kind || '').trim().toLowerCase();
                const providerColumnLabel = translateAppTextLocal('来源');
                const statusColumnLabel = translateAppTextLocal('状态');
                const capabilityColumnLabel = translateAppTextLocal('能力');
                const configColumnLabel = translateAppTextLocal('配置');
                const selectionColumnLabel = translateAppTextLocal('部署/调用');
                return [
                    '<div class="provider-console-row">',
                        `<div class="provider-console-main" data-column-label="${escapeHtml(providerColumnLabel)}">`,
                            '<span class="provider-console-mobile-label">' + escapeHtml(providerColumnLabel) + '</span>',
                            '<div class="provider-console-provider-text">',
                                `<span class="provider-console-label">${escapeHtml(label)}</span>`,
                                `<span class="provider-console-code">${escapeHtml(providerName)}</span>`,
                            '</div>',
                        '</div>',
                        `<div class="provider-console-meta" data-column-label="${escapeHtml(statusColumnLabel)}">`,
                            '<span class="provider-console-mobile-label">' + escapeHtml(statusColumnLabel) + '</span>',
                            `<span class="badge ${escapeHtml(getProviderStatusBadgeClass(status))}">${escapeHtml(getProviderStatusLabel(status))}</span>`,
                            `<span class="provider-console-kind">${escapeHtml(getProviderKindLabel(kind))}</span>`,
                        '</div>',
                        `<div class="provider-console-cell" data-column-label="${escapeHtml(capabilityColumnLabel)}"><span class="provider-console-mobile-label">${escapeHtml(capabilityColumnLabel)}</span>${escapeHtml(getProviderCapabilityText(item))}</div>`,
                        `<div class="provider-console-cell" data-column-label="${escapeHtml(configColumnLabel)}"><span class="provider-console-mobile-label">${escapeHtml(configColumnLabel)}</span>${escapeHtml(getProviderConfigText(item))}</div>`,
                        renderProviderHealthCell(item),
                        `<div class="provider-console-cell provider-console-deployment" data-column-label="${escapeHtml(selectionColumnLabel)}"><span class="provider-console-mobile-label">${escapeHtml(selectionColumnLabel)}</span>${escapeHtml(getProviderDeploymentText(item))}</div>`,
                    '</div>'
                ].join('');
            }).join('');

            root.innerHTML = [
                '<div class="provider-console-head">',
                    `<span>${escapeHtml(translateAppTextLocal('来源'))}</span>`,
                    `<span>${escapeHtml(translateAppTextLocal('状态'))}</span>`,
                    `<span>${escapeHtml(translateAppTextLocal('能力'))}</span>`,
                    `<span>${escapeHtml(translateAppTextLocal('配置'))}</span>`,
                    `<span>${escapeHtml(translateAppTextLocal('上游探测'))}</span>`,
                    `<span>${escapeHtml(translateAppTextLocal('部署/调用'))}</span>`,
                '</div>',
                rows
            ].join('');
        }

        function renderProviderDiagnostics() {
            const root = document.getElementById('providerDiagnosticsSummary');
            if (!root) return;

            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const summary = diagnostics.summary || {};
            const filter = diagnostics.filter || {};
            const defaults = diagnostics.defaults || {};
            const providers = dedupeMailboxProviderDiagnosticRows(
                Array.isArray(diagnostics.providers) ? diagnostics.providers : []
            );
            if (!providers.length) {
                root.innerHTML = `<div class="provider-diagnostics-empty">${escapeHtml(translateAppTextLocal('邮箱来源状态暂不可用'))}</div>`;
                renderProviderConsole([]);
                return;
            }

            const activeProviders = providers.filter(item => item && item.active);
            const needsConfig = activeProviders.filter(item => String(item.status || '') === 'needs_config');
            const unknownProviders = Array.isArray(filter.unknown_providers) ? filter.unknown_providers.filter(Boolean) : [];
            const activeLabels = activeProviders.slice(0, 6).map(item => item.label || item.provider).filter(Boolean);
            const listSeparator = getUiLanguage() === 'en' ? ', ' : '、';
            const warningSeparator = getUiLanguage() === 'en' ? '; ' : '；';
            const activeOverflow = activeProviders.length > activeLabels.length
                ? translateAppTextLocal(` 等 ${activeProviders.length} 个`)
                : '';
            const activeText = activeLabels.length ? `${activeLabels.join(listSeparator)}${activeOverflow}` : translateAppTextLocal('无');
            const filterText = translateAppTextLocal(filter.active ? '白名单' : '全部启用');
            const needsText = needsConfig.slice(0, 3).map(item => {
                const missing = Array.isArray(item.missing_config) ? item.missing_config : [];
                const missingText = missing.map(getMissingConfigDisplayName).join(listSeparator) || translateAppTextLocal('必要配置');
                return `${item.label || item.provider}: ${missingText}`;
            }).join(warningSeparator);
            const unknownText = unknownProviders.length
                ? `${translateAppTextLocal('未知来源白名单项')}: ${unknownProviders.join(listSeparator)}`
                : '';
            const invalidDefaults = Array.isArray(defaults.invalid_defaults) ? defaults.invalid_defaults.filter(Boolean) : [];
            const invalidDefaultsText = invalidDefaults.length
                ? `${translateAppTextLocal('默认来源配置无效')}: ${invalidDefaults.map(item => {
                    const key = String(item.key || item.env || item.settings_key || '').trim();
                    const provider = String(item.provider || item.raw_provider || item.unknown_provider || '').trim();
                    return [key, provider].filter(Boolean).join('=');
                }).filter(Boolean).join(listSeparator)}`
                : '';
            const inactiveDefaults = Array.isArray(defaults.inactive_defaults) ? defaults.inactive_defaults.filter(Boolean) : [];
            const inactiveDefaultsText = inactiveDefaults.length
                ? `${translateAppTextLocal('默认来源未启用')}: ${inactiveDefaults.map(item => {
                    const key = String(item.key || item.env || item.settings_key || '').trim();
                    const provider = String(item.provider || item.raw_provider || '').trim();
                    return [key, provider].filter(Boolean).join('=');
                }).filter(Boolean).join(listSeparator)}`
                : '';
            const warningText = [unknownText, invalidDefaultsText, inactiveDefaultsText, needsText].filter(Boolean).join(warningSeparator);

            root.innerHTML = [
                '<div class="provider-diagnostics-head">',
                    `<span class="provider-diagnostics-title">${escapeHtml(translateAppTextLocal('邮箱来源状态'))}</span>`,
                    `<span class="badge badge-gray">${escapeHtml(filterText)}</span>`,
                '</div>',
                '<div class="provider-diagnostics-metrics">',
                    `<span>${escapeHtml(translateAppTextLocal('启用'))} <strong>${Number(summary.active || activeProviders.length)}</strong></span>`,
                    `<span>${escapeHtml(translateAppTextLocal('就绪'))} <strong>${Number(summary.ready || summary.configured || 0)}</strong></span>`,
                    `<span>${escapeHtml(translateAppTextLocal('缺配置'))} <strong>${Number(summary.needs_config || needsConfig.length)}</strong></span>`,
                    `<span>${escapeHtml(translateAppTextLocal('可动态创建'))} <strong>${Number(summary.dynamic_create || 0)}</strong></span>`,
                '</div>',
                `<div class="provider-diagnostics-line">${escapeHtml(activeText)}</div>`,
                warningText ? `<div class="provider-diagnostics-warning">${escapeHtml(warningText)}</div>` : ''
            ].join('');
            renderProviderConsole(providers);
        }

        function setProviderConsoleFilter(filterName) {
            mailboxProviderConsoleFilter = normalizeProviderConsoleFilter(filterName);
            syncProviderConsoleFilterButtons();
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const providers = dedupeMailboxProviderDiagnosticRows(
                Array.isArray(diagnostics.providers) ? diagnostics.providers : []
            );
            renderProviderConsole(providers);
        }

        if (typeof document !== 'undefined') {
            document.addEventListener('click', event => {
                const demoActionTarget = event.target && event.target.closest ? event.target.closest('[data-demo-workspace-action]') : null;
                if (demoActionTarget) {
                    handleDemoWorkspaceAction(demoActionTarget.getAttribute('data-demo-workspace-action') || 'overview');
                    return;
                }
                const filterTarget = event.target && event.target.closest ? event.target.closest('[data-provider-console-filter]') : null;
                if (filterTarget) {
                    setProviderConsoleFilter(filterTarget.getAttribute('data-provider-console-filter') || 'all');
                    return;
                }
                const templateTarget = event.target && event.target.closest ? event.target.closest('[data-provider-template-format]') : null;
                if (templateTarget) {
                    setProviderTemplateFormat(templateTarget.getAttribute('data-provider-template-format') || 'env');
                    return;
                }
                const templateCopyTarget = event.target && event.target.closest ? event.target.closest('[data-provider-template-copy]') : null;
                if (templateCopyTarget) {
                    copyProviderConfigTemplate();
                    return;
                }
                const externalApiStarterModeTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-starter-mode]') : null;
                if (externalApiStarterModeTarget) {
                    setExternalApiStarterMode(externalApiStarterModeTarget.getAttribute('data-external-api-starter-mode') || 'curl');
                    return;
                }
                const externalApiCommandCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-command-copy]') : null;
                if (externalApiCommandCopyTarget) {
                    copyExternalApiCommandSnippet();
                    return;
                }
                const externalApiQuickstartCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-quickstart-copy]') : null;
                if (externalApiQuickstartCopyTarget) {
                    copyExternalApiQuickstart();
                    return;
                }
                const externalApiSmokeCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-smoke-copy]') : null;
                if (externalApiSmokeCopyTarget) {
                    copyExternalApiSmokeCommand();
                    return;
                }
                const externalApiContractRefreshTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-contract-refresh]') : null;
                if (externalApiContractRefreshTarget) {
                    loadExternalApiContractCheck(true);
                    return;
                }
                const externalApiBundleCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-bundle-copy]') : null;
                if (externalApiBundleCopyTarget) {
                    copyExternalApiBundleCommand();
                    return;
                }
                const externalApiHandoffCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-handoff-copy]') : null;
                if (externalApiHandoffCopyTarget) {
                    copyExternalApiHandoffKit();
                    return;
                }
                const externalApiSessionCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-session-copy]') : null;
                if (externalApiSessionCopyTarget) {
                    copyExternalApiMailboxSessionLifecycle();
                    return;
                }
                const externalProviderRecipeTarget = event.target && event.target.closest ? event.target.closest('[data-external-provider-recipe-key]') : null;
                if (externalProviderRecipeTarget) {
                    setExternalProviderRecipe(externalProviderRecipeTarget.getAttribute('data-external-provider-recipe-key') || '');
                    return;
                }
                const externalProviderRecipeCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-provider-recipe-copy]') : null;
                if (externalProviderRecipeCopyTarget) {
                    copyExternalProviderRecipe();
                    return;
                }
                const externalApiWorkflowTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-workflow-key]') : null;
                if (externalApiWorkflowTarget) {
                    setExternalApiWorkflowPlaybook(externalApiWorkflowTarget.getAttribute('data-external-api-workflow-key') || 'claim_pool_mailbox');
                    return;
                }
                const externalApiWorkflowCopyTarget = event.target && event.target.closest ? event.target.closest('[data-external-api-workflow-copy]') : null;
                if (externalApiWorkflowCopyTarget) {
                    copyExternalApiWorkflowPlaybook();
                    return;
                }
                const integrationFilterTarget = event.target && event.target.closest ? event.target.closest('[data-provider-integration-filter]') : null;
                if (integrationFilterTarget) {
                    setProviderIntegrationFilter(integrationFilterTarget.getAttribute('data-provider-integration-filter') || 'all');
                    return;
                }
                const providerPreflightProbeTarget = event.target && event.target.closest ? event.target.closest('[data-provider-preflight-probe]') : null;
                if (providerPreflightProbeTarget) {
                    loadProviderPreflightSnapshot(true, true);
                    return;
                }
                const integrationCopyTarget = event.target && event.target.closest ? event.target.closest('[data-provider-integration-copy]') : null;
                if (integrationCopyTarget) {
                    copyProviderIntegrationSnippet(
                        integrationCopyTarget.getAttribute('data-provider-name') || '',
                        integrationCopyTarget.getAttribute('data-provider-kind') || ''
                    );
                    return;
                }
                const healthTarget = event.target && event.target.closest ? event.target.closest('[data-provider-health-action]') : null;
                if (healthTarget) {
                    probeMailboxProviderHealth(
                        healthTarget.getAttribute('data-provider-kind') || '',
                        healthTarget.getAttribute('data-provider-name') || ''
                    );
                }
            });
        }

        if (typeof window !== 'undefined') {
            window.addEventListener('ui-language-changed', () => {
                renderDemoWorkspaceStrip();
                // Settings-only surfaces re-render only while Settings page/modal is open.
                if (isSettingsSurfaceActive()) {
                    refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'ready');
                    softPaintSettingsSecretHintsIfOpen();
                    if (currentSettingsTab === 'api-security') {
                        loadProviderPreflightSnapshot(false, false);
                        loadExternalApiContractCheck(false);
                        loadOperationalReadinessSnapshot(false);
                    }
                }
                // Theme toggle label is painted in JS; re-translate on language change.
                try {
                    const theme = document.documentElement.dataset.theme || localStorage.getItem('ol_theme') || 'light';
                    applyTheme(theme);
                } catch (_e) {}
            });
        }

