// split from settings.js → temp_mail.js
        function syncTempProviderSchemaInputsToSnapshot() {
            const panel = document.getElementById('tempMailProviderConfigPanel');
            if (!panel || panel.style.display === 'none') return true;
            const inputs = Array.from(panel.querySelectorAll('[data-temp-provider-setting]'));
            for (const inputEl of inputs) {
                const settingKey = String(inputEl.getAttribute('data-temp-provider-setting') || '').trim();
                if (!settingKey) continue;
                const isSecret = inputEl.getAttribute('data-temp-provider-secret') === 'true';
                const isReadonly = inputEl.getAttribute('data-temp-provider-readonly') === 'true' || inputEl.readOnly;
                const fieldType = String(inputEl.getAttribute('data-temp-provider-type') || '').trim().toLowerCase();
                const rawValue = String(inputEl.value || '').trim();
                const loadedValue = String(inputEl.dataset.loadedValue || '').trim();
                if (isSecret) {
                    const maskedValue = String(inputEl.dataset.maskedValue || '');
                    const isSet = inputEl.dataset.isSet === 'true';
                    if (rawValue && !(isSet && rawValue === maskedValue)) {
                        tempMailSettingsSnapshot[settingKey] = rawValue;
                        tempMailSettingsDirtyKeys.add(settingKey);
                    }
                    continue;
                }
                if (isReadonly) {
                    // Readonly fields are action-managed; still keep snapshot values.
                    if (Object.prototype.hasOwnProperty.call(tempMailSettingsSnapshot, settingKey)) {
                        continue;
                    }
                }
                if (rawValue === loadedValue) continue;
                if (fieldType === 'json') {
                    if (!rawValue) {
                        tempMailSettingsSnapshot[settingKey] = [];
                        tempMailSettingsDirtyKeys.add(settingKey);
                        continue;
                    }
                    try {
                        tempMailSettingsSnapshot[settingKey] = JSON.parse(rawValue);
                        tempMailSettingsDirtyKeys.add(settingKey);
                    } catch (error) {
                        showToast(translateAppTextLocal(`${settingKey} 必须是合法 JSON`), 'error');
                        return false;
                    }
                    continue;
                }
                tempMailSettingsSnapshot[settingKey] = rawValue;
                tempMailSettingsDirtyKeys.add(settingKey);
            }
            return true;
        }

        function collectTempProviderSchemaSettings(settings) {
            if (!settings) return true;
            if (!syncTempProviderSchemaInputsToSnapshot()) return false;
            // Only emit keys the user actually edited (or action-updated) in this session.
            tempMailSettingsDirtyKeys.forEach(key => {
                if (!key) return;
                if (Object.prototype.hasOwnProperty.call(tempMailSettingsSnapshot, key)) {
                    settings[key] = tempMailSettingsSnapshot[key];
                }
            });
            return true;
        }

        function collectTempMailSettingsPayload() {
            const settings = {};
            // Prefer live radio selection when the temp-mail tab has been opened.
            // If radios are unbound, prefer the server snapshot over a pending
            // canonicalized value written by applyTempMailSettingsSelection during
            // loadSettings, so global save from Basic does not rewrite the stored
            // provider (e.g. custom_domain_temp_mail → legacy_bridge).
            const mount = getTempMailSettingsProviderMount();
            const bound = isTempMailSettingsProviderMountBound(mount);
            const checked = document.querySelector('input[name="tempMailProvider"]:checked');
            const pending = mount ? String(mount.dataset.pendingProvider || '').trim() : '';
            const snapshotProvider = tempMailSettingsSnapshot
                && Object.prototype.hasOwnProperty.call(tempMailSettingsSnapshot, 'temp_mail_provider')
                ? String(tempMailSettingsSnapshot.temp_mail_provider || '').trim()
                : '';
            if (bound) {
                const rawProvider = (checked && checked.value)
                    || pending
                    || snapshotProvider
                    || getOperatorDefaultTempMailProvider();
                settings.temp_mail_provider = normalizeTempMailSettingsProviderName(rawProvider)
                    || getOperatorDefaultTempMailProvider();
            } else if (snapshotProvider) {
                // Preserve the server-stored value exactly when the user never opened
                // temp-mail (do not canonicalize custom_domain_temp_mail → legacy_bridge).
                settings.temp_mail_provider = snapshotProvider;
            } else {
                settings.temp_mail_provider = getOperatorDefaultTempMailProvider();
            }

            // Collect currently rendered schema fields (selected provider). Catalog may
            // also expose other providers' keys; only visible inputs are submitted here.
            // When unbound, dirty keys are empty so no phantom schema keys are emitted.
            if (!collectTempProviderSchemaSettings(settings)) return null;

            return settings;
        }

        // Soft-load cache for Settings page re-entry (navigate / modal).
        // Any successful settings write must invalidate so the next open refetches
        // (or refreshTempMailSettingsSnapshotFromServer repopulates from server).
        let settingsPageCache = null;
        // Coalesce concurrent soft GET /api/settings (navigate + modal race, double-click).
        let settingsPageLoadPromise = null;
        // True when the in-flight settings GET was started with forceRefresh.
        let settingsPageLoadForce = false;
        // Bumped on invalidate so in-flight soft responses cannot repopulate stale cache.
        let settingsPageCacheGeneration = 0;

        async function refreshTempMailSettingsSnapshotFromServer() {
            // After temp-mail save, reload masked secret state + configured flags so the
            // schema panel (including plugin.* keys) matches server truth.
            try {
                const data = await fetchSettingsPagePayload(true);
                if (!data || data.success === false) return false;
                externalApiSettingsSnapshot = data.settings || {};
                tempMailSettingsSnapshot = data.settings || {};
                tempMailSettingsDirtyKeys = new Set();
                const selectedProvider = typeof getCurrentTempMailSettingsProviderSelection === 'function'
                    ? getCurrentTempMailSettingsProviderSelection(getTempMailSettingsProviderMount())
                    : '';
                if (selectedProvider && typeof renderTempMailProviderConfigPanel === 'function') {
                    renderTempMailProviderConfigPanel(selectedProvider, { skipSnapshotSync: true });
                } else if (typeof hydrateTempProviderSchemaInputs === 'function') {
                    hydrateTempProviderSchemaInputs();
                }
                if (typeof updateTempMailProviderStatusBadges === 'function') {
                    updateTempMailProviderStatusBadges();
                }
                return true;
            } catch (_error) {
                return false;
            }
        }

        function onTempMailProviderChange(provider) {
            const normalizedProvider = normalizeTempMailSettingsProviderName(provider) || getOperatorDefaultTempMailProvider();
            const pluginPanel = document.getElementById('pluginProviderConfigPanel');
            const pluginManager = typeof window !== 'undefined' && window.PluginManager ? window.PluginManager : null;
            const usesSchemaPanel = providerUsesTempSettingsSchemaPanel(normalizedProvider);

            // Hide legacy specialized mounts if they still exist in DOM.
            ['gptmailConfigPanel', 'cfWorkerConfigPanel'].forEach(id => {
                const panel = document.getElementById(id);
                if (panel) panel.style.display = 'none';
            });

            updateTempMailProviderStatusBadges();
            renderTempMailProviderConfigPanel(normalizedProvider);

            if (usesSchemaPanel) {
                if (pluginManager && typeof pluginManager.hideProviderConfig === 'function') {
                    pluginManager.hideProviderConfig();
                }
                if (pluginPanel) {
                    pluginPanel.style.display = 'none';
                }
            } else {
                if (pluginPanel) pluginPanel.style.display = 'block';
                if (pluginManager && typeof pluginManager.showProviderConfig === 'function') {
                    pluginManager.showProviderConfig(normalizedProvider);
                }
            }
        }

        // Compatibility wrapper kept for older callers/tests.
