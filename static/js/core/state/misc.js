// split from state.js → misc.js
        function itemConfigSource(providerName) {
            const item = getMailboxProviderCatalogItem(normalizeTempMailSettingsProviderName(providerName), 'temp');
            return String(item?.config_source || item?.source || '').trim().toLowerCase();
        }

        function addExternalIntegrationManifestEnvLine(lines, hint) {
            const item = hint && typeof hint === 'object' ? hint : {};
            const key = String(item.key || '').trim();
            if (!key) return;
            const secretKeys = item.secret === true ? new Set([key]) : new Set();
            const value = item.default !== undefined ? item.default : item.value;
            addProviderIntegrationEnvLine(lines, key, value, secretKeys);
        }

        function addExternalIntegrationRequestFieldLines(lines, requestFields) {
            const fields = requestFields && typeof requestFields === 'object' ? requestFields : {};
            const poolClaim = fields.pool_claim && typeof fields.pool_claim === 'object' ? fields.pool_claim : null;
            const taskTempApply = fields.task_temp_apply && typeof fields.task_temp_apply === 'object' ? fields.task_temp_apply : null;
            if (poolClaim && poolClaim.request_field) {
                lines.push(`# pool claim request: ${poolClaim.request_field}=${poolClaim.value || ''}`);
            }
            if (taskTempApply && taskTempApply.request_field) {
                lines.push(`# task temp apply request: ${taskTempApply.request_field}=${taskTempApply.value || ''}`);
            }
        }

