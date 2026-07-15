// split from state.js → surface.js
        function isSettingsSurfaceActive() {
            // Active when either the full Settings page or the compatibility modal is open.
            return isSettingsPageActive() || isSettingsModalVisible();
        }

        function paintApiSecuritySurfacesFromSnapshot(settingsSnapshot = externalApiSettingsSnapshot, workbenchState = 'ready') {
            // Full api-security tab paint from local caches/snapshot (no network).
            renderPoolDefaultProviderDatalist();
            renderActiveMailboxProviderSuggestions();
            renderProviderDiagnostics();
            renderProviderConfigTemplates();
            renderProviderIntegrationGuide();
            renderProviderContractStatus();
            renderProviderWorkbench(settingsSnapshot, workbenchState);
            renderExternalApiCommandCenter(settingsSnapshot, workbenchState);
        }

        function isCurrentApiSecuritySurface() {
            return (typeof isSettingsSurfaceActive === 'function' ? isSettingsSurfaceActive() : true)
                && typeof currentSettingsTab !== 'undefined'
                && currentSettingsTab === 'api-security';
        }

