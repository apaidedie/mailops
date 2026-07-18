// split from provider_catalog.js → temp_settings.js
        function getTempProviderConfiguration(providerName) {
            const item = getMailboxProviderCatalogItem(providerName, 'temp');
            const configuration = item && item.configuration && typeof item.configuration === 'object'
                ? item.configuration
                : {};
            return { item, configuration };
        }

        function getBuiltinTempSettingsSchemaFallbackProviders() {
            // Startup / offline classification before /api/providers settles.
            // Keep in sync with built-in temp providers that own schema fields.
            return [
                'legacy_bridge',
                'cloudflare_temp_mail',
                'mail_tm',
                'duckmail',
                'tempmail_lol',
                'emailnator',
            ];
        }

        function providerUsesTempSettingsSchemaPanel(providerName) {
            const normalizedProvider = normalizeTempMailSettingsProviderName(providerName) || getOperatorDefaultTempMailProvider();
            const item = getMailboxProviderCatalogItem(normalizedProvider, 'temp');
            if (item) {
                const panel = String(item?.settings_ui?.panel || 'schema').trim().toLowerCase();
                const configSource = String(item.config_source || item.source || '').trim().toLowerCase();
                // Catalog-ready plugins with schema metadata use the same Settings panel
                // and /api/settings plugin.* keys as built-ins. PluginManager remains the
                // warmup/fallback path when catalog is missing (handled below).
                if (configSource === 'plugin') {
                    // Catalog-ready plugins with panel=schema share Settings schema UI +
                    // /api/settings plugin.* keys. No fields still renders the empty/
                    // "无需配置" schema body rather than a second PluginManager form.
                    return panel === 'schema';
                }
                return panel === 'schema';
            }

            // Catalog not ready: never misroute installed plugins into an empty schema body.
            const builtinFallback = new Set(getBuiltinTempSettingsSchemaFallbackProviders());
            if (builtinFallback.has(normalizedProvider)) return true;

            const pluginManager = typeof window !== 'undefined' && window.PluginManager ? window.PluginManager : null;
            if (pluginManager && typeof pluginManager.hasInstalledProvider === 'function') {
                if (pluginManager.hasInstalledProvider(normalizedProvider)) return false;
            }
            // Unknown provider without catalog → prefer plugin path when manager exists,
            // otherwise keep schema empty state rather than inventing dedicated panels.
            if (pluginManager) return false;
            return true;
        }

        function getTempProviderSchemaFields(providerName) {
            const { configuration } = getTempProviderConfiguration(providerName);
            const schema = configuration.config_schema && typeof configuration.config_schema === 'object'
                ? configuration.config_schema
                : {};
            const schemaFields = Array.isArray(schema.fields) ? schema.fields : [];
            const settingsKeys = (configuration.settings_keys || []).map(key => String(key || '').trim()).filter(Boolean);
            const required = new Set((configuration.required_settings || []).map(key => String(key || '').trim()).filter(Boolean));
            const secret = new Set((configuration.secret_settings || []).map(key => String(key || '').trim()).filter(Boolean));
            const defaults = configuration.settings_defaults && typeof configuration.settings_defaults === 'object'
                ? configuration.settings_defaults
                : {};

            const resolveSettingKey = key => {
                const normalizedKey = String(key || '').trim();
                if (!normalizedKey) return '';
                if (settingsKeys.includes(normalizedKey)) return normalizedKey;
                return settingsKeys.find(item => item.endsWith(`.${normalizedKey}`)) || normalizedKey;
            };

            const getDefaultValue = (key, settingKey) => {
                if (Object.prototype.hasOwnProperty.call(defaults, settingKey)) return defaults[settingKey];
                if (Object.prototype.hasOwnProperty.call(defaults, key)) return defaults[key];
                return undefined;
            };

            if (schemaFields.length) {
                return schemaFields.map(field => {
                    const key = String(field?.key || '').trim();
                    if (!key) return null;
                    const settingKey = resolveSettingKey(key);
                    const fieldType = String(field?.type || '').trim().toLowerCase();
                    const isSecret = secret.has(settingKey) || secret.has(key) || fieldType === 'password' || /(?:key|token|secret|password|bearer)/i.test(settingKey || key);
                    const defaultValue = getDefaultValue(key, settingKey);
                    return {
                        key,
                        settingKey,
                        label: String(field?.label || '').trim() || getMissingConfigDisplayName(settingKey),
                        type: isSecret ? 'password' : (fieldType || (Array.isArray(defaultValue) || typeof defaultValue === 'object' ? 'json' : 'text')),
                        required: field?.required === true || required.has(settingKey) || required.has(key),
                        secret: isSecret,
                        readonly: field?.readonly === true || field?.read_only === true,
                        placeholder: String(field?.placeholder || '').trim(),
                        defaultValue: defaultValue !== undefined ? defaultValue : field?.default,
                    };
                }).filter(Boolean);
            }

            return (configuration.settings_keys || []).map(rawKey => {
                const key = String(rawKey || '').trim();
                if (!key) return null;
                const defaultValue = defaults[key];
                return {
                    key,
                    label: getMissingConfigDisplayName(key),
                    type: secret.has(key) ? 'password' : (Array.isArray(defaultValue) || typeof defaultValue === 'object' ? 'json' : 'text'),
                    required: required.has(key),
                    secret: secret.has(key),
                    placeholder: '',
                    defaultValue,
                };
            }).filter(Boolean);
        }

        function tempProviderSettingDomId(settingKey) {
            return `tempProviderSetting_${String(settingKey || '').replace(/[^a-zA-Z0-9_-]/g, '_')}`;
        }

        function formatTempProviderSettingValue(value) {
            if (value === undefined || value === null) return '';
            if (Array.isArray(value) || typeof value === 'object') {
                try {
                    return JSON.stringify(value, null, 2);
                } catch (error) {
                    return '';
                }
            }
            return String(value);
        }

        function getTempProviderSettingSnapshotValue(field) {
            const settingKey = field?.settingKey || field?.key;
            if (!field || !settingKey) return '';
            if (field.secret) return '';
            if (Object.prototype.hasOwnProperty.call(tempMailSettingsSnapshot, settingKey)) {
                return formatTempProviderSettingValue(tempMailSettingsSnapshot[settingKey]);
            }
            return formatTempProviderSettingValue(field.defaultValue);
        }

        function getTempProviderSecretState(field) {
            const settingKey = field?.settingKey || field?.key;
            if (!field || !settingKey) return { isSet: false, maskedValue: '' };
            const setKey = `${settingKey}_set`;
            const maskedKey = `${settingKey}_masked`;
            return {
                isSet: tempMailSettingsSnapshot[setKey] === true,
                maskedValue: String(tempMailSettingsSnapshot[maskedKey] || ''),
            };
        }

        function renderTempProviderField(field) {
            const settingKey = field.settingKey || field.key;
            const id = tempProviderSettingDomId(settingKey);
            const requiredBadge = field.required
                ? `<span class="temp-provider-field-required">${escapeHtml(translateAppTextLocal('必填'))}</span>`
                : '';
            const type = field.type === 'url' ? 'url' : (field.secret ? 'password' : 'text');
            const value = getTempProviderSettingSnapshotValue(field);
            const placeholder = field.placeholder || formatTempProviderSettingValue(field.defaultValue);
            const commonAttrs = [
                `id="${escapeHtml(id)}"`,
                'class="form-input temp-provider-config-input"',
                `data-temp-provider-setting="${escapeHtml(settingKey)}"`,
                `data-temp-provider-field="${escapeHtml(field.key)}"`,
                `data-temp-provider-secret="${field.secret ? 'true' : 'false'}"`,
                `data-temp-provider-type="${escapeHtml(field.type || 'text')}"`,
                `data-temp-provider-readonly="${field.readonly ? 'true' : 'false'}"`,
                `data-loaded-value="${escapeHtml(value)}"`,
            ];
            if (field.readonly) {
                commonAttrs.push('readonly');
                commonAttrs.push('class="form-input temp-provider-config-input readonly-field"');
            }
            const secretState = getTempProviderSecretState(field);
            if (field.secret) {
                commonAttrs.push(`data-is-set="${secretState.isSet ? 'true' : 'false'}"`);
                commonAttrs.push(`data-masked-value="${escapeHtml(secretState.maskedValue)}"`);
                commonAttrs.push('autocomplete="off"');
            }

            // Rebuild attrs without duplicate class if readonly already set class.
            const attrList = field.readonly
                ? commonAttrs.filter((item, index, arr) => !(item.startsWith('class=') && arr.findIndex(x => x.startsWith('class=')) !== index))
                : commonAttrs;

            const control = field.type === 'json'
                ? `<textarea ${attrList.join(' ')} rows="4" placeholder="${escapeHtml(placeholder || '[]')}">${escapeHtml(value)}</textarea>`
                : `<input ${attrList.join(' ')} type="${escapeHtml(type)}" value="${escapeHtml(field.secret ? '' : value)}" placeholder="${escapeHtml(field.secret ? translateAppTextLocal('输入新值；留空则保留已保存配置') : placeholder)}">`;
            const secretHint = field.secret
                ? `<div class="form-hint temp-provider-secret-hint">${escapeHtml(secretState.isSet ? `${translateAppTextLocal('已设置')}：${secretState.maskedValue}` : translateAppTextLocal('未设置'))}</div>`
                : '';
            const readonlyHint = field.readonly
                ? `<div class="form-hint">${escapeHtml(translateAppTextLocal('只读字段，可通过操作按钮更新'))}</div>`
                : '';
            // Keep technical setting keys out of the operator UI (cleaner GPTMail form).
            return [
                '<div class="form-group temp-provider-config-field">',
                    '<div class="temp-provider-field-head">',
                        `<label class="form-label" for="${escapeHtml(id)}">${escapeHtml(translateAppTextLocal(field.label || settingKey))}</label>`,
                        requiredBadge,
                    '</div>',
                    control,
                    secretHint,
                    readonlyHint,
                '</div>'
            ].join('');
        }

        function formatGptmailUsageNumber(value) {
            const num = Number(value);
            if (!Number.isFinite(num)) return '—';
            try {
                return num.toLocaleString();
            } catch (_error) {
                return String(num);
            }
        }

        function renderGptmailUsagePanel(usage, options = {}) {
            const safeUsage = usage && typeof usage === 'object' ? usage : null;
            const opts = options && typeof options === 'object' ? options : {};
            const status = String(opts.status || '').trim().toLowerCase();
            const message = String(opts.message || '').trim();
            if (!safeUsage && !message) {
                return [
                    '<div class="temp-provider-usage-panel" id="tempProviderUsagePanel" hidden>',
                    '</div>',
                ].join('');
            }
            const rows = [
                ['used_today', '今日已用'],
                ['daily_limit', '今日限额'],
                ['remaining_today', '今日剩余'],
                ['total_usage', '累计用量'],
                ['total_limit', '累计限额'],
                ['remaining_total', '累计剩余'],
            ];
            const grid = safeUsage
                ? [
                    '<div class="temp-provider-usage-grid">',
                    ...rows.map(([key, labelZh]) => {
                        if (!(key in safeUsage)) return '';
                        return [
                            '<div class="temp-provider-usage-item">',
                                `<div class="temp-provider-usage-label">${escapeHtml(translateAppTextLocal(labelZh))}</div>`,
                                `<div class="temp-provider-usage-value">${escapeHtml(formatGptmailUsageNumber(safeUsage[key]))}</div>`,
                            '</div>',
                        ].join('');
                    }).filter(Boolean),
                    '</div>',
                ].join('')
                : '';
            const toneClass = status === 'error'
                ? ' is-error'
                : (status === 'ok' ? ' is-ok' : '');
            const messageHtml = message
                ? `<div class="temp-provider-usage-message${toneClass}">${escapeHtml(message)}</div>`
                : '';
            return [
                `<div class="temp-provider-usage-panel${toneClass}" id="tempProviderUsagePanel">`,
                    `<div class="temp-provider-usage-title">${escapeHtml(translateAppTextLocal('GPTMail 用量'))}</div>`,
                    messageHtml,
                    grid,
                '</div>',
            ].join('');
        }

        function updateGptmailUsagePanel(usage, options = {}) {
            const panel = document.getElementById('tempProviderUsagePanel');
            const html = renderGptmailUsagePanel(usage, options);
            if (!panel) {
                const body = document.getElementById('tempMailProviderConfigBody');
                if (!body) return;
                const actions = body.querySelector('.temp-provider-config-actions');
                if (actions) {
                    actions.insertAdjacentHTML('afterend', html);
                } else {
                    body.insertAdjacentHTML('afterbegin', html);
                }
                return;
            }
            const wrap = document.createElement('div');
            wrap.innerHTML = html;
            const next = wrap.firstElementChild;
            if (next) panel.replaceWith(next);
        }

        function getTempProviderSettingsActions(providerName) {
            const item = getMailboxProviderCatalogItem(normalizeTempMailSettingsProviderName(providerName), 'temp');
            const actions = item?.settings_ui?.actions;
            return Array.isArray(actions) ? actions.filter(action => action && typeof action === 'object') : [];
        }

        function getPluginSchemaTestConnectionAction(providerName) {
            const normalizedProvider = normalizeTempMailSettingsProviderName(providerName);
            if (!normalizedProvider) return null;
            const item = getMailboxProviderCatalogItem(normalizedProvider, 'temp');
            const configSource = String(item?.config_source || item?.source || '').trim().toLowerCase();
            if (configSource !== 'plugin') return null;
            // Reuse the existing plugin test-connection API from the schema panel.
            return {
                key: 'test_connection',
                label: 'Test connection',
                label_zh: '测试连接',
                method: 'POST',
                endpoint: `/api/plugins/${encodeURIComponent(normalizedProvider)}/test-connection`,
            };
        }

        function renderTempProviderSettingsActions(providerName) {
            const catalogActions = getTempProviderSettingsActions(providerName);
            const pluginTestAction = getPluginSchemaTestConnectionAction(providerName);
            const actions = pluginTestAction
                ? [...catalogActions.filter(action => String(action?.key || '').trim() !== 'test_connection'), pluginTestAction]
                : catalogActions;
            if (!actions.length) return '';
            return [
                '<div class="temp-provider-config-actions">',
                    actions.map(action => {
                        const key = String(action.key || '').trim();
                        if (!key) return '';
                        const label = getUiLanguage() === 'en'
                            ? String(action.label || key)
                            : String(action.label_zh || action.label || key);
                        const method = String(action.method || 'POST').trim().toUpperCase() || 'POST';
                        const endpoint = String(action.endpoint || '').trim();
                        return [
                            `<button type="button" class="btn btn-secondary temp-provider-action-btn" data-temp-provider-action="${escapeHtml(key)}" data-temp-provider-action-method="${escapeHtml(method)}" data-temp-provider-action-endpoint="${escapeHtml(endpoint)}" data-temp-provider-action-provider="${escapeHtml(normalizeTempMailSettingsProviderName(providerName))}">`,
                                escapeHtml(translateAppTextLocal(label)),
                            '</button>',
                        ].join('');
                    }).filter(Boolean).join(''),
                    '<div class="form-hint" id="tempProviderActionHint" aria-live="polite"></div>',
                '</div>'
            ].join('');
        }

        async function runTempProviderSettingsAction(buttonEl) {
            if (!buttonEl) return;
            const method = String(buttonEl.getAttribute('data-temp-provider-action-method') || 'POST').toUpperCase();
            const endpoint = String(buttonEl.getAttribute('data-temp-provider-action-endpoint') || '').trim();
            const provider = String(buttonEl.getAttribute('data-temp-provider-action-provider') || '').trim();
            const actionKey = String(buttonEl.getAttribute('data-temp-provider-action') || '').trim();
            const hintEl = document.getElementById('tempProviderActionHint');
            if (!endpoint) {
                showToast(translateAppTextLocal('操作端点不可用'), 'error');
                return;
            }
            const originalText = buttonEl.textContent;
            buttonEl.disabled = true;
            buttonEl.textContent = translateAppTextLocal('处理中…');
            try {
                const resp = await fetch(endpoint, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: method === 'GET' || method === 'HEAD' ? undefined : JSON.stringify({}),
                });
                const data = await resp.json();
                if (!data.success) {
                    handleApiError(data, '操作失败');
                    if (hintEl) {
                        hintEl.textContent = `❌ ${(data.error && data.error.message) || translateAppTextLocal('操作失败')}`;
                    }
                    return;
                }

                const item = getMailboxProviderCatalogItem(provider, 'temp');
                const actions = Array.isArray(item?.settings_ui?.actions) ? item.settings_ui.actions : [];
                const action = actions.find(entry => String(entry?.key || '').trim() === actionKey) || {};
                const resultMap = action.result_map && typeof action.result_map === 'object' ? action.result_map : {};

                Object.keys(resultMap).forEach(responseKey => {
                    const settingKey = String(resultMap[responseKey] || '').trim();
                    if (!settingKey || !(responseKey in data)) return;
                    let nextValue = data[responseKey];
                    if (settingKey === 'cf_worker_domains' && Array.isArray(nextValue)) {
                        nextValue = nextValue.map(name => (
                            typeof name === 'string' ? { name, enabled: true } : name
                        ));
                    }
                    tempMailSettingsSnapshot[settingKey] = nextValue;
                    tempMailSettingsDirtyKeys.add(settingKey);
                    const inputEl = document.querySelector(`[data-temp-provider-setting="${settingKey}"]`);
                    if (inputEl) {
                        const formatted = formatTempProviderSettingValue(nextValue);
                        inputEl.value = formatted;
                        inputEl.dataset.loadedValue = formatted;
                    }
                });

                // Compatibility for existing CF sync response shape.
                if (actionKey === 'sync_domains' || endpoint.includes('cf-worker-sync-domains')) {
                    if (Array.isArray(data.domains)) {
                        const domains = data.domains.map(name => (
                            typeof name === 'string' ? { name, enabled: true } : name
                        ));
                        tempMailSettingsSnapshot.cf_worker_domains = domains;
                        tempMailSettingsDirtyKeys.add('cf_worker_domains');
                        const domainsEl = document.querySelector('[data-temp-provider-setting="cf_worker_domains"]');
                        if (domainsEl) {
                            const formatted = formatTempProviderSettingValue(domains);
                            domainsEl.value = formatted;
                            domainsEl.dataset.loadedValue = formatted;
                        }
                    }
                    if (data.default_domain) {
                        tempMailSettingsSnapshot.cf_worker_default_domain = data.default_domain;
                        tempMailSettingsDirtyKeys.add('cf_worker_default_domain');
                        const defaultEl = document.querySelector('[data-temp-provider-setting="cf_worker_default_domain"]');
                        if (defaultEl) {
                            defaultEl.value = String(data.default_domain);
                            defaultEl.dataset.loadedValue = String(data.default_domain);
                        }
                    }
                }

                // GPTMail usage probe: /api/providers/temp/.../health?probe_network=true
                if (actionKey === 'check_usage' || endpoint.includes('/health')) {
                    const health = data.provider_health && typeof data.provider_health === 'object'
                        ? data.provider_health
                        : (data.data && data.data.provider_health) || data;
                    const probe = health && health.probe && typeof health.probe === 'object' ? health.probe : {};
                    const details = probe.details && typeof probe.details === 'object' ? probe.details : {};
                    const usage = details.usage && typeof details.usage === 'object' ? details.usage : null;
                    const probeOk = probe.ok === true || probe.status === 'ok' || health.local_ready === true;
                    if (usage) {
                        updateGptmailUsagePanel(usage, {
                            status: probeOk ? 'ok' : 'error',
                            message: probeOk
                                ? translateAppTextLocal('已从 GPTMail /api/stats 刷新用量')
                                : (probe.error || translateAppTextLocal('探测完成，但上游返回异常')),
                        });
                        showToast(translateAppTextLocal('用量已更新'), probeOk ? 'success' : 'warning');
                        if (hintEl) {
                            const remain = usage.remaining_today != null
                                ? `${translateAppTextLocal('今日剩余')} ${formatGptmailUsageNumber(usage.remaining_today)}`
                                : '';
                            hintEl.textContent = probeOk
                                ? `✅ ${translateAppTextLocal('用量已更新')}${remain ? ` · ${remain}` : ''}`
                                : `⚠️ ${probe.error || translateAppTextLocal('探测异常')}`;
                        }
                        return;
                    }
                    updateGptmailUsagePanel(null, {
                        status: 'error',
                        message: probe.error || translateAppTextLocal('上游未返回 usage 字段'),
                    });
                    showToast(probe.error || translateAppTextLocal('未获取到用量'), 'warning');
                    if (hintEl) hintEl.textContent = `⚠️ ${probe.error || translateAppTextLocal('未获取到用量')}`;
                    return;
                }

                showToast(pickApiMessage(data, data.message || '操作成功', data.message || 'Action completed'), 'success');
                if (hintEl) {
                    const versionInfo = data.version ? ` (${data.version})` : '';
                    const titleInfo = data.title ? `「${data.title}」` : '';
                    const domainText = Array.isArray(data.domains) ? data.domains.join(', ') : '';
                    hintEl.textContent = domainText
                        ? `✅ ${translateAppTextLocal('同步成功')} ${titleInfo}${versionInfo}：${domainText}`
                        : `✅ ${data.message || translateAppTextLocal('操作成功')}`;
                }
            } catch (error) {
                showToast(`${translateAppTextLocal('请求失败')}: ${error.message}`, 'error');
                if (hintEl) hintEl.textContent = `❌ ${error.message}`;
            } finally {
                buttonEl.disabled = false;
                buttonEl.textContent = originalText;
            }
        }

        function renderTempProviderEnvHints(configuration) {
            const envKeys = [
                ...(configuration.required_env || []),
                ...(configuration.optional_env || []),
            ].map(key => String(key || '').trim()).filter(Boolean);
            if (!envKeys.length) return '';
            const secretEnv = new Set((configuration.secret_env || []).map(key => String(key || '').trim()).filter(Boolean));
            const defaults = configuration.env_defaults && typeof configuration.env_defaults === 'object'
                ? configuration.env_defaults
                : {};
            return [
                '<div class="temp-provider-config-hints">',
                    `<div class="temp-provider-config-hints-title">${escapeHtml(translateAppTextLocal('部署环境变量'))}</div>`,
                    envKeys.map(key => {
                        const value = secretEnv.has(key) ? '' : String(defaults[key] || '');
                        return `<code>${escapeHtml(`${key}=${value}`)}</code>`;
                    }).join(''),
                '</div>'
            ].join('');
        }

        function renderTempMailProviderConfigPanel(providerName, options = {}) {
            const opts = options && typeof options === 'object' ? options : {};
            const normalizedProvider = normalizeTempMailSettingsProviderName(providerName) || getOperatorDefaultTempMailProvider();
            const panel = document.getElementById('tempMailProviderConfigPanel');
            const body = document.getElementById('tempMailProviderConfigBody');
            const subtitle = document.getElementById('tempMailProviderConfigSubtitle');
            if (!panel || !body) return;

            // Preserve edits from the previously rendered provider before re-render.
            // Skip when the snapshot was just reloaded from the server (stale empty secret
            // inputs must not overwrite *_set/*_masked state).
            if (!opts.skipSnapshotSync && !syncTempProviderSchemaInputsToSnapshot()) return;

            // Built-in and schema-capable providers render through catalog fields.
            if (!providerUsesTempSettingsSchemaPanel(normalizedProvider)) {
                panel.style.display = 'none';
                body.innerHTML = '';
                return;
            }

            const { item, configuration } = getTempProviderConfiguration(normalizedProvider);
            const fields = getTempProviderSchemaFields(normalizedProvider);
            const label = typeof resolveMailboxProviderLabel === 'function'
                ? (resolveMailboxProviderLabel(normalizedProvider, {
                    softLoad: false,
                    emptyLabel: '',
                    fallbackResolver: () => String(item?.label || item?.provider_label || item?.provider || '').trim(),
                }) || normalizedProvider)
                : (item?.label || item?.provider_label || item?.provider || normalizedProvider);
            if (subtitle) {
                subtitle.textContent = translateAppTextLocal('根据 Provider 目录渲染配置字段');
            }
            panel.style.display = 'block';

            if (!item && !fields.length) {
                body.innerHTML = `<div class="provider-radio-empty">${escapeHtml(translateAppTextLocal('Provider 配置目录暂不可用'))}</div>`;
                return;
            }

            const statusBadge = item?.configured
                ? `<span class="badge badge-green">${escapeHtml(translateAppTextLocal('已就绪'))}</span>`
                : `<span class="badge badge-gold">${escapeHtml(translateAppTextLocal('需配置'))}</span>`;
            const missing = Array.isArray(item?.missing_config) ? item.missing_config : [];
            const missingText = missing.length ? missing.map(getMissingConfigDisplayName).join(getUiLanguage() === 'en' ? ', ' : '、') : translateAppTextLocal('无缺失项');
            const fieldHtml = fields.length
                ? `<div class="temp-provider-config-grid">${fields.map(renderTempProviderField).join('')}</div>`
                : `<div class="provider-radio-empty">${escapeHtml(translateAppTextLocal('该 Provider 无需本地配置'))}</div>`;

            const isGptmail = ['legacy_bridge', 'custom_domain_temp_mail', 'gptmail', 'legacy_gptmail', 'temp_mail']
                .includes(normalizedProvider);
            const description = getUiLanguage() === 'en'
                ? String(item?.settings_ui?.description || item?.description || '').trim()
                : String(item?.settings_ui?.description_zh || item?.settings_ui?.description || item?.description_zh || item?.description || '').trim();
            body.innerHTML = [
                '<div class="temp-provider-config-summary">',
                    '<div>',
                        `<div class="temp-provider-config-title">${escapeHtml(translateAppTextLocal(label))}</div>`,
                        description
                            ? `<div class="temp-provider-config-detail">${escapeHtml(translateAppTextLocal(description))}</div>`
                            : '',
                        `<div class="temp-provider-config-detail">${escapeHtml(translateAppTextLocal('缺失项'))}: ${escapeHtml(missingText)}</div>`,
                    '</div>',
                    statusBadge,
                '</div>',
                isGptmail
                    ? renderGptmailUsagePanel(null, {
                        message: item?.configured
                            ? translateAppTextLocal('点击「刷新用量」从 GPTMail /api/stats 拉取限额')
                            : translateAppTextLocal('配置 GPTMail API Key 后可查看用量'),
                    })
                    : '',
                renderTempProviderSettingsActions(normalizedProvider),
                fieldHtml,
                renderTempProviderEnvHints(configuration),
            ].join('');
            hydrateTempProviderSchemaInputs();
            if (body.dataset.boundTempProviderActions !== 'true') {
                body.addEventListener('click', event => {
                    const target = event.target;
                    if (!target || !target.closest) return;
                    const actionBtn = target.closest('[data-temp-provider-action]');
                    if (!actionBtn) return;
                    runTempProviderSettingsAction(actionBtn);
                });
                body.dataset.boundTempProviderActions = 'true';
            }
            // Soft auto-refresh usage once when GPTMail is already configured.
            if (isGptmail && item?.configured && body.dataset.gptmailUsageAutoloaded !== normalizedProvider) {
                body.dataset.gptmailUsageAutoloaded = normalizedProvider;
                const usageBtn = body.querySelector('[data-temp-provider-action="check_usage"]');
                if (usageBtn) {
                    setTimeout(() => {
                        if (document.body.contains(usageBtn)) {
                            runTempProviderSettingsAction(usageBtn);
                        }
                    }, 80);
                }
            }
        }

        function hydrateTempProviderSchemaInputs() {
            const panel = document.getElementById('tempMailProviderConfigPanel');
            if (!panel || panel.style.display === 'none') return;
            Array.from(panel.querySelectorAll('[data-temp-provider-setting]')).forEach(inputEl => {
                const settingKey = String(inputEl.getAttribute('data-temp-provider-setting') || '').trim();
                if (!settingKey) return;
                const isSecret = inputEl.getAttribute('data-temp-provider-secret') === 'true';
                if (isSecret) {
                    const maskedValue = String(tempMailSettingsSnapshot[`${settingKey}_masked`] || '');
                    inputEl.value = '';
                    inputEl.dataset.maskedValue = maskedValue;
                    inputEl.dataset.isSet = tempMailSettingsSnapshot[`${settingKey}_set`] === true ? 'true' : 'false';
                    return;
                }
                const value = Object.prototype.hasOwnProperty.call(tempMailSettingsSnapshot, settingKey)
                    ? tempMailSettingsSnapshot[settingKey]
                    : undefined;
                if (value === undefined) return;
                const formatted = formatTempProviderSettingValue(value);
                inputEl.value = formatted;
                inputEl.dataset.loadedValue = formatted;
            });
        }

        function getBuiltinTempSettingsProviderAliasMap() {
            // Warmup-safe alias map when /api/providers has not settled yet.
            // Keep in sync with backend legacy_bridge settings_ui.aliases.
            return {
                gptmail: 'legacy_bridge',
                legacy_gptmail: 'legacy_bridge',
                temp_mail: 'legacy_bridge',
                custom_domain_temp_mail: 'legacy_bridge',
            };
        }

        function normalizeTempMailSettingsProviderName(value) {
            const provider = normalizeProviderCatalogName(value);
            if (!provider) return '';
            const catalog = Array.isArray(mailboxProviderCatalogCache) ? mailboxProviderCatalogCache : [];
            const canonical = catalog.find(item => (
                String(item?.kind || '').trim().toLowerCase() === 'temp'
                && Array.isArray(item?.settings_ui?.aliases)
                && item.settings_ui.aliases.map(normalizeProviderCatalogName).includes(provider)
            ));
            if (canonical) {
                return normalizeProviderCatalogName(canonical.provider) || provider;
            }
            // Catalog missing/empty: still canonicalize known built-in aliases so
            // warmup routing does not send gptmail/custom_domain_temp_mail to PluginManager.
            const staticAliases = getBuiltinTempSettingsProviderAliasMap();
            return normalizeProviderCatalogName(staticAliases[provider]) || provider;
        }

        function getTempMailSettingsProviderMount() {
            return document.getElementById('tempMailProviderOptions') || document.querySelector('.provider-radio-group');
        }

        function getTempMailSettingsProviderOrder(providerName) {
            const item = getMailboxProviderCatalogItem(normalizeTempMailSettingsProviderName(providerName), 'temp');
            const order = Number(item?.settings_ui?.sort_order);
            return Number.isFinite(order) ? order : 1000;
        }

        function normalizeTempMailSettingsProviderOption(item, source = 'catalog') {
            const rawProvider = normalizeProviderCatalogName(item?.provider || item?.name || item?.key);
            const provider = normalizeTempMailSettingsProviderName(rawProvider);
            if (!provider || provider === 'auto') return null;

            const configSource = String(item?.config_source || item?.source || '').trim().toLowerCase();
            const dynamicCreate = item?.can_dynamic_create !== undefined ? !!item.can_dynamic_create : true;
            const catalogItem = getMailboxProviderCatalogItem(provider, 'temp') || item;
            const ui = (catalogItem?.settings_ui && typeof catalogItem.settings_ui === 'object')
                ? catalogItem.settings_ui
                : (item?.settings_ui && typeof item.settings_ui === 'object' ? item.settings_ui : {});
            const localizedDescription = getUiLanguage() === 'en' ? ui.description : ui.description_zh;
            const explicitDescription = String(item?.description || item?.provider_description || '').trim();
            const fallbackDescription = String(localizedDescription || '').trim()
                || explicitDescription
                || (configSource === 'plugin'
                    ? translateAppTextLocal('第三方插件 Provider')
                    : (dynamicCreate
                        ? translateAppTextLocal('支持动态创建临时邮箱')
                        : translateAppTextLocal('临时邮箱 Provider')));

            return {
                provider,
                label: String(item?.label || item?.provider_label || item?.display_name || catalogItem?.label || rawProvider || provider).trim() || provider,
                description: fallbackDescription,
                active: item?.active !== false,
                configured: item?.configured,
                missingConfig: Array.isArray(item?.missing_config) ? item.missing_config : [],
                configSource,
                source,
                sortOrder: getTempMailSettingsProviderOrder(provider),
            };
        }

        function mergeTempMailSettingsProviderOption(optionMap, option) {
            if (!optionMap || !option || !option.provider) return;
            const existing = optionMap.get(option.provider);
            if (!existing) {
                optionMap.set(option.provider, option);
                return;
            }
            const preferIncoming = (option.source === 'catalog' && existing.source !== 'catalog')
                || (option.source === existing.source);
            optionMap.set(option.provider, {
                ...existing,
                ...option,
                label: preferIncoming ? (option.label || existing.label) : (existing.label || option.label),
                description: preferIncoming ? (option.description || existing.description) : (existing.description || option.description),
                sortOrder: Math.min(existing.sortOrder ?? 1000, option.sortOrder ?? 1000),
                source: option.source === 'catalog' || existing.source === 'catalog' ? 'catalog' : (option.source || existing.source),
            });
        }

        function getExistingPluginTempMailProviderOptions(mount) {
            if (!mount) return [];
            return Array.from(mount.querySelectorAll('.provider-radio[data-plugin]')).map(label => {
                const input = label.querySelector('input[name="tempMailProvider"]');
                if (!input) return null;
                return normalizeTempMailSettingsProviderOption({
                    provider: input.value,
                    label: label.querySelector('.provider-name')?.textContent || input.value,
                    description: label.querySelector('.provider-desc')?.textContent
                        || translateAppTextLocal('第三方插件 Provider'),
                    config_source: 'plugin',
                }, 'plugin');
            }).filter(Boolean);
        }

        function getTempMailSettingsProviderOptions(selectedProvider = '', mount = null) {
            const optionMap = new Map();
            const catalog = Array.isArray(mailboxProviderCatalogCache) ? mailboxProviderCatalogCache : [];
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const diagnosticProviders = Array.isArray(diagnostics.providers) ? diagnostics.providers : [];
            const catalogOptions = catalog
                .map(item => String(item?.kind || '').trim().toLowerCase() === 'temp'
                    ? normalizeTempMailSettingsProviderOption(item, 'catalog')
                    : null)
                .filter(Boolean);
            const diagnosticOptions = diagnosticProviders
                .map(item => String(item?.kind || '').trim().toLowerCase() === 'temp'
                    ? normalizeTempMailSettingsProviderOption(item, 'diagnostics')
                    : null)
                .filter(Boolean);

            catalogOptions.forEach(option => mergeTempMailSettingsProviderOption(optionMap, option));
            diagnosticOptions.forEach(option => mergeTempMailSettingsProviderOption(optionMap, option));

            getExistingPluginTempMailProviderOptions(mount).forEach(option => {
                if (!optionMap.has(option.provider)) {
                    mergeTempMailSettingsProviderOption(optionMap, option);
                }
            });

            const selected = normalizeTempMailSettingsProviderName(selectedProvider);
            if (selected && !optionMap.has(selected)) {
                mergeTempMailSettingsProviderOption(optionMap, normalizeTempMailSettingsProviderOption({
                    provider: selected,
                    label: selected,
                    description: translateAppTextLocal('当前已保存的临时邮箱 Provider'),
                }, 'saved'));
            }

            return Array.from(optionMap.values()).sort((a, b) => {
                const orderDelta = (a.sortOrder ?? 1000) - (b.sortOrder ?? 1000);
                if (orderDelta !== 0) return orderDelta;
                return String(a.label || a.provider).localeCompare(String(b.label || b.provider));
            });
        }

        function renderTempMailSettingsProviderOption(option, selectedProvider) {
            const provider = normalizeTempMailSettingsProviderName(option.provider);
            const checked = provider === selectedProvider ? ' checked' : '';
            const sourceBadge = option.configSource === 'plugin'
                ? `<span class="provider-source-badge">${escapeHtml(translateAppTextLocal('插件'))}</span>`
                : '';
            return [
                `<label class="provider-radio" data-provider-option="${escapeHtml(provider)}" data-provider-source="${escapeHtml(option.source || 'catalog')}">`,
                    `<input type="radio" name="tempMailProvider" value="${escapeHtml(provider)}"${checked}>`,
                    '<span class="provider-radio-label">',
                        '<span class="provider-name-line">',
                            `<span class="provider-name">${escapeHtml(translateAppTextLocal(option.label || provider))}</span>`,
                            sourceBadge,
                        '</span>',
                        `<span class="provider-desc">${escapeHtml(translateAppTextLocal(option.description || '临时邮箱 Provider'))}</span>`,
                        `<span class="provider-config-status" data-provider-status="${escapeHtml(provider)}"></span>`,
                    '</span>',
                '</label>'
            ].join('');
        }

        function findTempMailSettingsProviderRadio(providerName) {
            const provider = normalizeTempMailSettingsProviderName(providerName);
            if (!provider) return null;
            return Array.from(document.querySelectorAll('input[name="tempMailProvider"]'))
                .find(input => normalizeTempMailSettingsProviderName(input.value) === provider) || null;
        }

        function getOperatorDefaultTempMailProvider() {
            // Prefer discovery default from /api/providers; fall back to operator-canonical bridge key.
            const cached = normalizeTempMailSettingsProviderName(mailboxProviderDefaultTempMailProvider);
            return cached || 'legacy_bridge';
        }

        function getCurrentTempMailSettingsProviderSelection(mount) {
            const target = mount || getTempMailSettingsProviderMount();
            const checked = document.querySelector('input[name="tempMailProvider"]:checked');
            if (checked && checked.value) {
                return normalizeTempMailSettingsProviderName(checked.value) || getOperatorDefaultTempMailProvider();
            }
            // Pending is only meaningful after the temp-mail tab bound radios.
            if (isTempMailSettingsProviderMountBound(target)) {
                const pending = target ? String(target.dataset.pendingProvider || '').trim() : '';
                if (pending) {
                    return normalizeTempMailSettingsProviderName(pending) || getOperatorDefaultTempMailProvider();
                }
            }
            const snapshotProvider = tempMailSettingsSnapshot
                && Object.prototype.hasOwnProperty.call(tempMailSettingsSnapshot, 'temp_mail_provider')
                ? String(tempMailSettingsSnapshot.temp_mail_provider || '').trim()
                : '';
            if (snapshotProvider) {
                return normalizeTempMailSettingsProviderName(snapshotProvider) || snapshotProvider;
            }
            return getOperatorDefaultTempMailProvider();
        }

        function isTempMailSettingsProviderMountBound(mount = null) {
            const target = mount || getTempMailSettingsProviderMount();
            return !!(target && target.dataset && target.dataset.boundTempMailProviderOptions === 'true');
        }

        async function ensureTempMailPluginsReady() {
            // Plugin list is only needed for temp-mail routing / plugin card / dual-path UI.
            if (typeof window !== 'undefined' && window.PluginManager && typeof window.PluginManager.ensureLoaded === 'function') {
                try {
                    await window.PluginManager.ensureLoaded();
                } catch (_error) { /* plugin list soft-fail must not block Settings */ }
            } else if (typeof window !== 'undefined' && window.PluginManager && typeof window.PluginManager.loadPlugins === 'function') {
                try {
                    await window.PluginManager.loadPlugins();
                } catch (_error) { /* ignore */ }
            }
        }

        function refreshSettingsProviderSurfaces(settingsSnapshot = externalApiSettingsSnapshot, workbenchState = 'ready') {
            // Settings-only provider surfaces live on #page-settings / Settings modal.
            // Catalog preload must not rewrite them while Settings is closed.
            if (!isSettingsSurfaceActive()) return;
            // Temp-mail radios/config can update whenever Settings is open (cheap, tab may switch next).
            renderTempMailProviderOptions();
            updateTempMailProviderStatusBadges();
            rehydrateTempMailSettingsFromCatalog();
            // API security / workbench panels are expensive and only visible on that tab.
            if (currentSettingsTab !== 'api-security') return;
            paintApiSecuritySurfacesFromSnapshot(settingsSnapshot, workbenchState);
        }

        function renderTempMailProviderOptions(preferredProvider = '') {
            const mount = getTempMailSettingsProviderMount();
            if (!mount) return '';
            // Settings radios are deferred until initTempMailProviderOptions() (Settings open).
            // Skip rewriting the hidden mount when the user has never opened Settings.
            if (!isTempMailSettingsProviderMountBound(mount)) return '';
            const selectedProvider = normalizeTempMailSettingsProviderName(preferredProvider)
                || getCurrentTempMailSettingsProviderSelection(mount);
            const options = getTempMailSettingsProviderOptions(selectedProvider, mount);
            if (!options.length) {
                mount.innerHTML = `<div class="provider-radio-empty">${escapeHtml(translateAppTextLocal('暂无可用临时邮箱 Provider'))}</div>`;
                return '';
            }

            const selectedExists = options.some(option => option.provider === selectedProvider);
            const nextSelectedProvider = selectedExists ? selectedProvider : options[0].provider;
            mount.innerHTML = options.map(option => renderTempMailSettingsProviderOption(option, nextSelectedProvider)).join('');

            const selectedRadio = findTempMailSettingsProviderRadio(nextSelectedProvider);
            if (selectedRadio) {
                selectedRadio.checked = true;
                mount.dataset.pendingProvider = '';
            } else {
                mount.dataset.pendingProvider = nextSelectedProvider;
            }
            updateTempMailProviderStatusBadges();
            return nextSelectedProvider;
        }

        function initTempMailProviderOptions() {
            const mount = getTempMailSettingsProviderMount();
            if (!mount) return;
            if (mount.dataset.boundTempMailProviderOptions !== 'true') {
                mount.addEventListener('change', event => {
                    const target = event.target;
                    if (!target || !target.matches || !target.matches('input[name="tempMailProvider"]')) return;
                    mount.dataset.pendingProvider = '';
                    if (typeof onTempMailProviderChange === 'function') {
                        onTempMailProviderChange(target.value);
                    }
                });
                mount.dataset.boundTempMailProviderOptions = 'true';
            }
            renderTempMailProviderOptions();
        }

        function getTempEmailProviderCatalogOptions() {
            const catalog = Array.isArray(mailboxProviderCatalogCache) ? mailboxProviderCatalogCache : [];
            const seen = new Set();
            const options = [];
            catalog.forEach(item => {
                const kind = String(item?.kind || '').trim().toLowerCase();
                // Canonicalize aliases (e.g. custom_domain_temp_mail -> legacy_bridge) so selectors stay unique.
                const provider = normalizeTempMailSettingsProviderName(item?.provider || item?.name || item?.key);
                if (kind !== 'temp' || !provider || provider === 'auto' || seen.has(provider)) return;
                seen.add(provider);
                options.push({
                    provider,
                    label: String(item?.label || item?.provider_label || item?.provider || provider).trim() || provider,
                    active: item?.active !== false
                });
            });
            return options;
        }

        function findTempEmailProviderOption(select, providerName) {
            const provider = normalizeTempMailSettingsProviderName(providerName) || normalizeProviderCatalogName(providerName);
            if (!select || !provider) return null;
            return Array.from(select.options).find(option => {
                const optionProvider = normalizeTempMailSettingsProviderName(option.value) || normalizeProviderCatalogName(option.value);
                return optionProvider === provider;
            }) || null;
        }

        function removeDuplicateTempEmailProviderOptions(select, preferredValue = '') {
            if (!select) return;
            const preferredProvider = normalizeTempMailSettingsProviderName(preferredValue) || normalizeProviderCatalogName(preferredValue);
            const byProvider = new Map();
            Array.from(select.options).forEach(option => {
                const provider = normalizeTempMailSettingsProviderName(option.value) || normalizeProviderCatalogName(option.value);
                if (!provider) {
                    option.remove();
                    return;
                }
                const existing = byProvider.get(provider);
                if (!existing) {
                    byProvider.set(provider, option);
                    return;
                }
                if (provider === preferredProvider && option.selected && !existing.selected) {
                    existing.remove();
                    byProvider.set(provider, option);
                    return;
                }
                option.remove();
            });
        }

        function syncTempEmailProviderSelectWithCatalog() {
            // Create-temp page owns #tempEmailProviderSelect. Catalog soft re-entry from
            // boot/settings/plugins must not rewrite a hidden select off that page.
            if (typeof currentPage !== 'undefined' && currentPage !== 'temp-emails') {
                return '';
            }
            const select = document.getElementById('tempEmailProviderSelect');
            if (!select) return '';
            const previousValue = normalizeTempMailSettingsProviderName(select.value) || normalizeProviderCatalogName(select.value);
            const catalogOptions = getTempEmailProviderCatalogOptions();
            const catalogProviders = new Set(catalogOptions.map(item => item.provider));

            // Drop loading placeholders and options no longer present in catalog.
            if (catalogOptions.length) {
                Array.from(select.options).forEach(option => {
                    const value = normalizeTempMailSettingsProviderName(option.value) || normalizeProviderCatalogName(option.value);
                    if (!value || !catalogProviders.has(value)) {
                        option.remove();
                    }
                });
            }

            catalogOptions.forEach(item => {
                let option = findTempEmailProviderOption(select, item.provider);
                if (!option) {
                    option = document.createElement('option');
                    option.value = item.provider;
                    select.appendChild(option);
                } else if (option.value !== item.provider) {
                    option.value = item.provider;
                }
                option.textContent = item.label;
                option.dataset.providerCatalog = '1';
                option.dataset.providerActive = item.active ? 'true' : 'false';
            });

            removeDuplicateTempEmailProviderOptions(select, previousValue);
            if (previousValue && findTempEmailProviderOption(select, previousValue)) {
                select.value = previousValue;
            } else if (catalogOptions.length && !findTempEmailProviderOption(select, select.value)) {
                select.value = catalogOptions[0].provider;
            }
            return select.value;
        }

        function updateTempMailProviderStatusBadges() {
            document.querySelectorAll('[data-provider-status]').forEach(target => {
                const providerName = target.getAttribute('data-provider-status') || '';
                const item = getMailboxProviderCatalogItem(providerName, 'temp');
                if (!item || item.configured === undefined) {
                    target.innerHTML = '';
                    return;
                }

                const missing = Array.isArray(item.missing_config) ? item.missing_config : [];
                if (item.active === false) {
                    target.innerHTML = `<span class="badge badge-gray">${escapeHtml(translateAppTextLocal('未启用'))}</span>`;
                    return;
                }

                if (item.configured) {
                    target.innerHTML = `<span class="badge badge-green">${escapeHtml(translateAppTextLocal('已就绪'))}</span>`;
                    return;
                }

                const missingText = missing.map(getMissingConfigDisplayName).join('、') || translateAppTextLocal('必要配置');
                target.innerHTML = [
                    `<span class="badge badge-gold">${escapeHtml(translateAppTextLocal('缺配置'))}</span>`,
                    `<span class="provider-config-missing">${escapeHtml(missingText)}</span>`
                ].join('');
            });
        }

        function normalizeProviderTemplateFormat(formatName) {
            const normalized = String(formatName || 'env').trim().toLowerCase();
            return ['env', 'json', 'toml'].includes(normalized) ? normalized : 'env';
        }

        function getProviderTemplateDescriptor(formatName) {
            const format = normalizeProviderTemplateFormat(formatName);
            const profile = mailboxProviderDeploymentProfileCache && typeof mailboxProviderDeploymentProfileCache === 'object'
                ? mailboxProviderDeploymentProfileCache
                : {};
            const templates = profile.templates && typeof profile.templates === 'object' ? profile.templates : {};
            const keyByFormat = {
                env: 'env',
                json: 'provider_config_json',
                toml: 'provider_config_toml'
            };
            const key = keyByFormat[format] || 'env';
            const template = templates[key] && typeof templates[key] === 'object' ? templates[key] : {};
            return {
                format,
                key,
                content: String(template.content || ''),
                sourceFormat: String(template.format || format),
                priority: Array.isArray(templates.priority) ? templates.priority.map(item => String(item || '').trim()).filter(Boolean) : []
            };
        }

        function getProviderTemplateUsageText(formatName) {
            const format = normalizeProviderTemplateFormat(formatName);
            if (format === 'json') return translateAppTextLocal('适合 provider JSON 配置文件');
            if (format === 'toml') return translateAppTextLocal('适合 provider TOML 配置文件');
            return translateAppTextLocal('适合 .env 环境变量');
        }

        function getProviderTemplateLabel(formatName) {
            const format = normalizeProviderTemplateFormat(formatName);
            if (format === 'json') return 'JSON';
            if (format === 'toml') return 'TOML';
            return '.env';
        }

        function syncProviderTemplateTabs() {
            mailboxProviderTemplateFormat = normalizeProviderTemplateFormat(mailboxProviderTemplateFormat);
            document.querySelectorAll('[data-provider-template-format]').forEach(button => {
                const active = normalizeProviderTemplateFormat(button.getAttribute('data-provider-template-format')) === mailboxProviderTemplateFormat;
                button.classList.toggle('active', active);
                button.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
        }

        function renderProviderConfigTemplates() {
            const root = document.getElementById('providerConfigTemplates');
            if (!root) return;
            syncProviderTemplateTabs();

            const metaEl = document.getElementById('providerConfigTemplateMeta');
            const codeEl = document.getElementById('providerConfigTemplateCode');
            const copyButton = root.querySelector('[data-provider-template-copy]');
            const descriptor = getProviderTemplateDescriptor(mailboxProviderTemplateFormat);
            const hasContent = Boolean(descriptor.content.trim());
            const priorityText = descriptor.priority.length
                ? `${translateAppTextLocal('优先级')} ${descriptor.priority.join(' > ')}`
                : '';
            const metaText = hasContent
                ? [getProviderTemplateLabel(descriptor.format), getProviderTemplateUsageText(descriptor.format), priorityText].filter(Boolean).join(' · ')
                : translateAppTextLocal('配置模板暂不可用');

            if (metaEl) metaEl.textContent = metaText;
            if (codeEl) codeEl.textContent = hasContent ? descriptor.content : translateAppTextLocal('暂无配置模板');
            if (copyButton) copyButton.disabled = !hasContent;
        }

        function setProviderTemplateFormat(formatName) {
            mailboxProviderTemplateFormat = normalizeProviderTemplateFormat(formatName);
            renderProviderConfigTemplates();
            renderProviderWorkbench(externalApiSettingsSnapshot, 'ready');
        }

        async function copyProviderConfigTemplate() {
            const descriptor = getProviderTemplateDescriptor(mailboxProviderTemplateFormat);
            if (!descriptor.content.trim()) {
                showToast(translateAppTextLocal('暂无配置模板'), 'warning');
                return;
            }
            try {
                const ok = await copyTextToClipboard(descriptor.content);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('配置模板已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

