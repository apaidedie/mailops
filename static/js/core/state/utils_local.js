// split from state.js → utils_local.js
        function getMissingConfigDisplayName(key) {
            const rawKey = String(key || '').trim();
            const labels = {
                temp_mail_api_base_url: '临时邮箱 API Base URL',
                temp_mail_api_key: '临时邮箱 API Key',
                cf_worker_base_url: 'CF Worker 地址',
                cf_worker_admin_key: 'CF Worker Admin 密码',
                duckmail_api_base: 'DuckMail API Base URL',
                duckmail_bearer_token: 'DuckMail Bearer Token',
                tempmail_lol_api_key: 'TempMail.lol API Key',
                temp_mail_lol_api_key: 'TempMail.lol API Key',
                emailnator_api_key: 'Emailnator RapidAPI Key',
                emailnator_email_types: 'Emailnator 邮箱类型'
            };
            if (labels[rawKey]) {
                return translateAppTextLocal(labels[rawKey]);
            }

            // plugin.<provider>.<field> → catalog schema field label when available.
            const pluginMatch = rawKey.match(/^plugin\.([^.]+)\.(.+)$/i);
            if (pluginMatch) {
                const providerName = normalizeProviderCatalogName(pluginMatch[1]);
                const fieldKey = String(pluginMatch[2] || '').trim();
                const item = typeof getMailboxProviderCatalogItem === 'function'
                    ? getMailboxProviderCatalogItem(providerName, 'temp')
                    : null;
                const configuration = item && item.configuration && typeof item.configuration === 'object'
                    ? item.configuration
                    : {};
                const schema = configuration.config_schema && typeof configuration.config_schema === 'object'
                    ? configuration.config_schema
                    : {};
                const fields = Array.isArray(schema.fields) ? schema.fields : [];
                const field = fields.find(entry => String(entry?.key || '').trim() === fieldKey);
                const fieldLabel = String(field?.label || '').trim();
                if (fieldLabel) {
                    const providerLabel = typeof resolveMailboxProviderLabel === 'function'
                        ? resolveMailboxProviderLabel(providerName, {
                            softLoad: false,
                            emptyLabel: '',
                            fallbackResolver: () => String(item?.label || item?.provider_label || providerName).trim(),
                        })
                        : String(item?.label || item?.provider_label || providerName).trim();
                    const combined = providerLabel
                        ? `${providerLabel} · ${fieldLabel}`
                        : fieldLabel;
                    return translateAppTextLocal(combined);
                }
            }

            return translateAppTextLocal(rawKey || key);
        }

        function isSettingsModalVisible() {
            const modal = document.getElementById('settingsModal');
            return !!(modal && modal.classList.contains('show'));
        }

        function isSettingsPageActive() {
            // Primary Settings UX is #page-settings via navigate('settings').
            if (typeof currentPage !== 'undefined' && currentPage === 'settings') return true;
            const page = document.getElementById('page-settings');
            return !!(page && !page.classList.contains('page-hidden'));
        }

        function ensureAutomationSettingsTabReady() {
            // Automation tab: update-method radio visibility toggles. Idempotent.
            if (typeof initUpdateMethodConfigToggles === 'function') {
                initUpdateMethodConfigToggles();
            }
        }

        async function copyTextToClipboard(text) {
            const value = String(text || '');
            if (!value) return false;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(value);
                return true;
            }
            const tempInput = document.createElement('textarea');
            tempInput.value = value;
            tempInput.setAttribute('readonly', 'readonly');
            tempInput.style.position = 'fixed';
            tempInput.style.opacity = '0';
            tempInput.style.pointerEvents = 'none';
            document.body.appendChild(tempInput);
            try {
                tempInput.focus();
                tempInput.select();
                return document.execCommand('copy');
            } finally {
                if (tempInput.parentNode) {
                    tempInput.parentNode.removeChild(tempInput);
                }
            }
        }

        function getExternalIntegrationManifest() {
            return mailboxProviderIntegrationManifestCache && typeof mailboxProviderIntegrationManifestCache === 'object'
                ? mailboxProviderIntegrationManifestCache
                : {};
        }

        function getExternalIntegrationManifestAuth() {
            const manifest = getExternalIntegrationManifest();
            const auth = manifest.auth && typeof manifest.auth === 'object' ? manifest.auth : {};
            const header = String(auth.header || 'X-API-Key').trim() || 'X-API-Key';
            const placeholder = String(auth.placeholder || '<your-api-key>').trim() || '<your-api-key>';
            const fallbackCurlHeader = 'X-API-Key: <your-api-key>';
            const curlHeader = String(auth.curl_header || '').trim()
                || (header === 'X-API-Key' && placeholder === '<your-api-key>' ? fallbackCurlHeader : `${header}: ${placeholder}`);
            return { header, placeholder, curlHeader };
        }

        function getExternalIntegrationManifestDiscovery() {
            const manifest = getExternalIntegrationManifest();
            return manifest.discovery && typeof manifest.discovery === 'object' ? manifest.discovery : {};
        }

        function getExternalIntegrationManifestSourcePriority() {
            const manifest = getExternalIntegrationManifest();
            const selection = manifest.selection && typeof manifest.selection === 'object' ? manifest.selection : {};
            if (Array.isArray(selection.source_priority) && selection.source_priority.length) {
                return selection.source_priority.map(item => String(item || '').trim()).filter(Boolean);
            }
            const deployment = manifest.deployment && typeof manifest.deployment === 'object' ? manifest.deployment : {};
            if (Array.isArray(deployment.source_priority) && deployment.source_priority.length) {
                return deployment.source_priority.map(item => String(item || '').trim()).filter(Boolean);
            }
            return [];
        }

        function getExternalIntegrationQuickstart() {
            if (mailboxProviderIntegrationQuickstartCache && typeof mailboxProviderIntegrationQuickstartCache === 'object') {
                return mailboxProviderIntegrationQuickstartCache;
            }
            const manifest = getExternalIntegrationManifest();
            return manifest.quickstart && typeof manifest.quickstart === 'object' ? manifest.quickstart : {};
        }

        function getExternalQuickstartAuth() {
            const quickstart = getExternalIntegrationQuickstart();
            const auth = quickstart.auth && typeof quickstart.auth === 'object' ? quickstart.auth : {};
            const manifestAuth = getExternalIntegrationManifestAuth();
            const header = String(auth.header || manifestAuth.header || 'X-API-Key').trim() || 'X-API-Key';
            const placeholder = String(auth.placeholder || manifestAuth.placeholder || '<your-api-key>').trim() || '<your-api-key>';
            const headers = auth.headers && typeof auth.headers === 'object' ? auth.headers : { [header]: placeholder };
            return { header, placeholder, headers };
        }

        function getExternalQuickstartSequence() {
            const quickstart = getExternalIntegrationQuickstart();
            return Array.isArray(quickstart.recommended_sequence)
                ? quickstart.recommended_sequence.filter(item => item && typeof item === 'object')
                : [];
        }

        function getExternalQuickstartSelectors() {
            const quickstart = getExternalIntegrationQuickstart();
            const selectors = quickstart.provider_selector_fields && typeof quickstart.provider_selector_fields === 'object'
                ? quickstart.provider_selector_fields
                : {};
            return selectors;
        }

        function getExternalQuickstartRequests() {
            const quickstart = getExternalIntegrationQuickstart();
            const requests = quickstart.requests && typeof quickstart.requests === 'object' ? quickstart.requests : {};
            return {
                pool_claim: requests.pool_claim && typeof requests.pool_claim === 'object' ? requests.pool_claim : null,
                task_temp_apply: requests.task_temp_apply && typeof requests.task_temp_apply === 'object' ? requests.task_temp_apply : null,
                mailbox_session_start: requests.mailbox_session_start && typeof requests.mailbox_session_start === 'object' ? requests.mailbox_session_start : null,
                mailbox_session_read: requests.mailbox_session_read && typeof requests.mailbox_session_read === 'object' ? requests.mailbox_session_read : null,
                mailbox_session_close: requests.mailbox_session_close && typeof requests.mailbox_session_close === 'object' ? requests.mailbox_session_close : null,
                mailbox_directory: requests.mailbox_directory && typeof requests.mailbox_directory === 'object' ? requests.mailbox_directory : null,
            };
        }

        function getExternalQuickstartRequestLine(request) {
            const item = request && typeof request === 'object' ? request : {};
            const method = String(item.method || 'GET').trim().toUpperCase() || 'GET';
            const endpoint = String(item.endpoint || '').trim();
            return `${method} ${endpoint}`.trim();
        }

        function formatExternalQuickstartJson(value) {
            if (!value || typeof value !== 'object') return '';
            return JSON.stringify(value, null, 2);
        }

        function renderExternalQuickstartSequence(sequence) {
            const values = Array.isArray(sequence) ? sequence : [];
            if (!values.length) return `<div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('暂无 quickstart 契约'))}</div>`;
            return [
                '<ol class="external-api-quickstart-sequence">',
                values.map(item => {
                    const step = item && typeof item === 'object' ? item : {};
                    const method = String(step.method || 'GET').trim().toUpperCase() || 'GET';
                    const endpoint = appendExternalApiStarterQuery(step.endpoint, step.query);
                    const label = String(step.step || endpoint || '').trim();
                    return [
                        '<li>',
                            `<span class="external-api-command-method">${escapeHtml(method)}</span>`,
                            '<div>',
                                `<code>${escapeHtml(endpoint)}</code>`,
                                label ? `<small>${escapeHtml(translateAppTextLocal(label))}</small>` : '',
                            '</div>',
                        '</li>'
                    ].join('');
                }).join(''),
                '</ol>'
            ].join('');
        }

        function renderExternalQuickstartSelectors(selectors) {
            const source = selectors && typeof selectors === 'object' ? selectors : {};
            const rows = Object.keys(source).map(key => {
                const selector = source[key] && typeof source[key] === 'object' ? source[key] : {};
                const field = String(selector.field || selector.request_field || '').trim();
                if (!field) return '';
                const allowed = Array.isArray(selector.allowed_values) && selector.allowed_values.length
                    ? selector.allowed_values.join(', ')
                    : '';
                return [
                    '<div class="external-api-quickstart-selector">',
                        `<span>${escapeHtml(translateAppTextLocal(key))}</span>`,
                        `<code>${escapeHtml(field)}</code>`,
                        allowed ? `<small>${escapeHtml(allowed)}</small>` : '',
                    '</div>'
                ].join('');
            }).filter(Boolean);
            return rows.length ? rows.join('') : `<div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('暂无 quickstart 契约'))}</div>`;
        }

        function renderExternalQuickstartRequestCard(label, request) {
            const item = request && typeof request === 'object' ? request : null;
            if (!item) return '';
            const line = getExternalQuickstartRequestLine(item);
            const bodyText = formatExternalQuickstartJson(item.body || item.query || {});
            return [
                '<div class="external-api-quickstart-request">',
                    `<div class="external-api-quickstart-request-title">${escapeHtml(translateAppTextLocal(label))}</div>`,
                    line ? `<div class="external-api-workflow-endpoint-line"><span class="external-api-command-method">${escapeHtml(String(item.method || 'GET').trim().toUpperCase() || 'GET')}</span><code>${escapeHtml(String(item.endpoint || '').trim())}</code></div>` : '',
                    bodyText ? `<pre class="external-api-command-code external-api-quickstart-code"><code>${escapeHtml(bodyText)}</code></pre>` : '',
                '</div>'
            ].join('');
        }

        function parseIntegerSetting(value, fallback) {
            if (value === null || value === undefined) {
                return fallback;
            }
            const normalized = String(value).trim();
            if (!normalized) {
                return fallback;
            }
            const parsed = Number.parseInt(normalized, 10);
            return Number.isNaN(parsed) ? fallback : parsed;
        }

