// split from state.js → temp_settings.js
        function isTempMailboxGroup(groupOrName) {
            const rawName = typeof groupOrName === 'string'
                ? String(groupOrName || '').trim()
                : String(groupOrName?.name || '').trim();
            return rawName === '临时邮箱' || rawName === 'Temp Mailboxes' || rawName === 'Temp Mailbox';
        }

        async function ensureTempMailSettingsTabReady() {
            // Temp-mail tab controls: radios + plugins. Idempotent.
            if (typeof initTempMailProviderOptions === 'function') {
                initTempMailProviderOptions();
            }
            await ensureTempMailPluginsReady();
        }

        function applyTempMailSettingsSelection(mappedProvider) {
            const provider = normalizeTempMailSettingsProviderName(mappedProvider)
                || getOperatorDefaultTempMailProvider();
            const providerGroup = getTempMailSettingsProviderMount();
            // Only paint radios/config when the temp-mail mount is bound (tab opened).
            // Do not write pendingProvider while unbound — passive Basic Settings load
            // must not leave a canonicalized pending that other paths can misread.
            if (!isTempMailSettingsProviderMountBound(providerGroup)) {
                if (providerGroup) {
                    providerGroup.dataset.pendingProvider = '';
                }
                return provider;
            }
            if (providerGroup) {
                providerGroup.dataset.pendingProvider = provider;
            }
            renderTempMailProviderOptions(provider);
            const radioBtn = findTempMailSettingsProviderRadio(provider);
            if (radioBtn) {
                radioBtn.checked = true;
                if (providerGroup) {
                    providerGroup.dataset.pendingProvider = '';
                }
            }
            if (typeof onTempMailProviderChange === 'function') {
                onTempMailProviderChange(provider);
            }
            return provider;
        }

        function rehydrateTempMailSettingsFromCatalog() {
            // Settings selection/config panel only after radios are bound (Settings opened).
            if (!isTempMailSettingsProviderMountBound()) return;
            const selection = getCurrentTempMailSettingsProviderSelection(getTempMailSettingsProviderMount());
            if (typeof onTempMailProviderChange === 'function') {
                onTempMailProviderChange(selection);
            } else {
                renderTempMailProviderConfigPanel(selection);
            }
        }

