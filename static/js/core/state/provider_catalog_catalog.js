// split from provider_catalog.js → catalog.js
        function normalizeProviderCatalogName(value) {
            return String(value || '').trim().toLowerCase();
        }

        function getMailboxProviderCatalogItem(providerName, kind = 'temp') {
            const normalizedProvider = normalizeProviderCatalogName(providerName);
            const normalizedKind = String(kind || '').trim().toLowerCase();
            const catalog = Array.isArray(mailboxProviderCatalogCache) ? mailboxProviderCatalogCache : [];
            const catalogItem = catalog.find(item => (
                String(item?.kind || '').trim().toLowerCase() === normalizedKind
                && normalizeProviderCatalogName(item?.provider) === normalizedProvider
            ));
            if (catalogItem) return catalogItem;

            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const diagnosticProviders = Array.isArray(diagnostics.providers) ? diagnostics.providers : [];
            return diagnosticProviders.find(item => (
                String(item?.kind || '').trim().toLowerCase() === normalizedKind
                && normalizeProviderCatalogName(item?.provider) === normalizedProvider
            )) || null;
        }

        async function loadMailboxProviderCatalog(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            if (!force && Array.isArray(mailboxProviderCatalogCache)) {
                syncTempEmailProviderSelectWithCatalog();
                refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'ready');
                // Soft re-entry: re-paint pool-admin type filter from warm catalog (no second GET).
                if (typeof ensurePoolAdminProviderOptions === 'function') {
                    ensurePoolAdminProviderOptions(false);
                }
                return mailboxProviderCatalogCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes a soft in-flight so save/refresh always start a true network GET.
            if (mailboxProviderCatalogPromise) {
                if (!force || mailboxProviderCatalogLoadForce) {
                    return mailboxProviderCatalogPromise;
                }
                // Abandon soft in-flight bookkeeping; stale response identity check fails.
                mailboxProviderCatalogPromise = null;
                mailboxProviderCatalogLoadForce = false;
            }

            mailboxProviderCatalogLoadForce = force;
            const request = fetch('/api/providers')
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    // If force supersede abandoned this request, do not write stale catalog.
                    if (mailboxProviderCatalogPromise !== request) {
                        return mailboxProviderCatalogCache;
                    }
                    mailboxProviderCatalogCache = Array.isArray(data.mailbox_providers) ? data.mailbox_providers : [];
                    mailboxProviderDiagnosticsCache = data.provider_diagnostics && typeof data.provider_diagnostics === 'object'
                        ? data.provider_diagnostics
                        : null;
                    mailboxProviderDeploymentProfileCache = data.deployment_profile && typeof data.deployment_profile === 'object'
                        ? data.deployment_profile
                        : null;
                    mailboxProviderIntegrationGuideCache = data.provider_integration_guide && typeof data.provider_integration_guide === 'object'
                        ? data.provider_integration_guide
                        : null;
                    mailboxProviderIntegrationManifestCache = data.integration_manifest && typeof data.integration_manifest === 'object'
                        ? data.integration_manifest
                        : null;
                    mailboxProviderIntegrationQuickstartCache = data.quickstart && typeof data.quickstart === 'object' ? data.quickstart : null;
                    mailboxProviderSelectionPolicyCache = data.selection_policy && typeof data.selection_policy === 'object'
                        ? data.selection_policy
                        : null;
                    mailboxProviderDefaultTempMailProvider = normalizeTempMailSettingsProviderName(
                        data.default_temp_mail_provider
                    ) || '';
                    if (force) {
                        mailboxProviderHealthState = {};
                        mailboxProviderHealthPending = new Set();
                    }
                    syncTempEmailProviderSelectWithCatalog();
                    updateProviderContractStateFromCatalog(data);
                    refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'ready');
                    // Status badge lives on temp-emails page; skip when off that surface.
                    if (
                        typeof currentPage !== 'undefined'
                        && currentPage === 'temp-emails'
                        && typeof renderTempEmailProviderStatus === 'function'
                    ) {
                        renderTempEmailProviderStatus();
                    }
                    refreshAccountProviderTagsFromCatalog();
                    // Catalog just wrote warm cache — soft-paint pool filter (do not force another GET).
                    if (typeof ensurePoolAdminProviderOptions === 'function') {
                        ensurePoolAdminProviderOptions(false);
                    }
                    // Soft-paint import provider select if modal already opened (no second GET).
                    if (typeof loadProviders === 'function') {
                        loadProviders(false);
                    }
                    if (typeof refreshUnifiedMailboxProviderLabelsFromCatalog === 'function') {
                        refreshUnifiedMailboxProviderLabelsFromCatalog();
                    }
                    return mailboxProviderCatalogCache;
                })
                .catch(error => {
                    if (mailboxProviderCatalogPromise !== request) {
                        return mailboxProviderCatalogCache;
                    }
                    console.warn('加载 provider catalog 失败:', error);
                    mailboxProviderCatalogCache = [];
                    mailboxProviderDiagnosticsCache = null;
                    mailboxProviderDeploymentProfileCache = null;
                    mailboxProviderIntegrationGuideCache = null;
                    mailboxProviderIntegrationManifestCache = null;
                    mailboxProviderIntegrationQuickstartCache = null;
                    mailboxProviderSelectionPolicyCache = null;
                    mailboxProviderDefaultTempMailProvider = '';
                    updateProviderContractStateFromCatalog({ mailbox_providers: [] });
                    refreshSettingsProviderSurfaces(externalApiSettingsSnapshot, 'provider_error');
                    return mailboxProviderCatalogCache;
                })
                .finally(() => {
                    if (mailboxProviderCatalogPromise === request) {
                        mailboxProviderCatalogPromise = null;
                        mailboxProviderCatalogLoadForce = false;
                    }
                });
            mailboxProviderCatalogPromise = request;
            return request;
        }

        function canonicalizeMailboxProviderAllowlistValue(value) {
            const raw = String(value || '').trim();
            if (!raw) return '';
            if (raw.toLowerCase() === 'auto') return 'auto';
            // Collapse bridge aliases (custom_domain_temp_mail / gptmail / ...) to canonical keys.
            if (typeof normalizeTempMailSettingsProviderName === 'function') {
                return normalizeTempMailSettingsProviderName(raw) || raw;
            }
            return raw;
        }

        function canonicalizeMailboxProviderAllowlistValues(values) {
            const seen = new Set();
            const next = [];
            (Array.isArray(values) ? values : []).forEach(item => {
                const value = canonicalizeMailboxProviderAllowlistValue(item);
                if (!value || seen.has(value)) return;
                seen.add(value);
                next.push(value);
            });
            return next;
        }

        function getPoolDefaultProviderAllowedValues() {
            const policy = mailboxProviderSelectionPolicyCache && typeof mailboxProviderSelectionPolicyCache === 'object'
                ? mailboxProviderSelectionPolicyCache
                : {};
            const scopes = policy.scopes && typeof policy.scopes === 'object' ? policy.scopes : {};
            const preferred = scopes.pool_claim_default && typeof scopes.pool_claim_default === 'object'
                ? scopes.pool_claim_default
                : {};
            const fallback = scopes.explicit_pool_claim && typeof scopes.explicit_pool_claim === 'object'
                ? scopes.explicit_pool_claim
                : {};
            const source = Array.isArray(preferred.allowed_values) && preferred.allowed_values.length
                ? preferred.allowed_values
                : (Array.isArray(fallback.allowed_values) ? fallback.allowed_values : []);
            const seen = new Set();
            const values = [];
            source.forEach(item => {
                const value = canonicalizeMailboxProviderAllowlistValue(item);
                if (!value || seen.has(value)) return;
                seen.add(value);
                values.push(value);
            });
            if (!seen.has('auto')) {
                values.unshift('auto');
            } else {
                // Keep auto first for operator ergonomics.
                const withoutAuto = values.filter(value => value !== 'auto');
                return ['auto', ...withoutAuto];
            }
            return values;
        }

        function refreshAccountProviderTagsFromCatalog() {
            // After catalog labels arrive, repaint cached account cards so tags
            // no longer stick on raw provider keys from the first paint.
            // Only while standard mailbox inventory is the active surface.
            if (typeof currentPage !== 'undefined' && currentPage !== 'mailbox') return;
            if (typeof isTempEmailGroup !== 'undefined' && isTempEmailGroup) return;
            if (typeof currentGroupId === 'undefined' || !currentGroupId) return;
            if (typeof accountsCache === 'undefined' || !accountsCache) return;
            const accounts = accountsCache[currentGroupId];
            if (!Array.isArray(accounts) || !accounts.length) return;
            if (typeof renderAccountList === 'function') {
                renderAccountList(accounts);
            }
            if (typeof renderCompactAccountList === 'function') {
                renderCompactAccountList(accounts);
            }
        }

        function getMailboxProviderCatalogLabel(providerKey) {
            const key = String(providerKey || '').trim().toLowerCase();
            if (!key) return '';
            const catalog = (typeof mailboxProviderCatalogCache !== 'undefined' && Array.isArray(mailboxProviderCatalogCache))
                ? mailboxProviderCatalogCache
                : [];
            if (!catalog.length) return '';
            const candidates = [key];
            // Also try canonical temp alias (custom_domain_temp_mail → legacy_bridge).
            if (typeof canonicalizeMailboxProviderAllowlistValue === 'function') {
                const canonical = String(canonicalizeMailboxProviderAllowlistValue(key) || '').trim().toLowerCase();
                if (canonical && canonical !== key && canonical !== 'auto') {
                    candidates.push(canonical);
                }
            }
            for (const candidate of candidates) {
                const hit = catalog.find(item => (
                    String(item?.provider || item?.key || '').trim().toLowerCase() === candidate
                ));
                const label = String(hit?.label || hit?.provider_label || '').trim();
                if (label) return label;
            }
            return '';
        }

        function resolveMailboxProviderLabel(providerKey, options = {}) {
            const opts = options && typeof options === 'object' ? options : {};
            const raw = String(providerKey || opts.fallback || '').trim();
            const key = raw.toLowerCase();
            if (!key) return String(opts.emptyLabel || '').trim();

            const catalogLabel = getMailboxProviderCatalogLabel(key);
            if (catalogLabel) return catalogLabel;

            if (opts.softLoad !== false && typeof loadMailboxProviderCatalog === 'function') {
                const catalog = (typeof mailboxProviderCatalogCache !== 'undefined' && Array.isArray(mailboxProviderCatalogCache))
                    ? mailboxProviderCatalogCache
                    : [];
                if (!catalog.length) {
                    try { loadMailboxProviderCatalog(false); } catch (_e) { /* ignore soft-load failures */ }
                }
            }

            if (typeof opts.fallbackResolver === 'function') {
                const resolved = String(opts.fallbackResolver(raw) || '').trim();
                if (resolved) return resolved;
            }

            return raw || String(opts.emptyLabel || '').trim();
        }

        function getActiveMailboxProviderAllowedValues() {
            const policy = mailboxProviderSelectionPolicyCache && typeof mailboxProviderSelectionPolicyCache === 'object'
                ? mailboxProviderSelectionPolicyCache
                : {};
            const scopes = policy.scopes && typeof policy.scopes === 'object' ? policy.scopes : {};
            const activeScope = scopes.active_allowlist && typeof scopes.active_allowlist === 'object'
                ? scopes.active_allowlist
                : {};
            const source = Array.isArray(activeScope.allowed_values) ? activeScope.allowed_values : [];
            const seen = new Set();
            const values = [];
            source.forEach(item => {
                const value = canonicalizeMailboxProviderAllowlistValue(item);
                if (!value || value === 'auto' || seen.has(value)) return;
                seen.add(value);
                values.push(value);
            });
            // Fall back to catalog providers when selection policy is unavailable.
            if (!values.length && Array.isArray(mailboxProviderCatalogCache)) {
                mailboxProviderCatalogCache.forEach(item => {
                    const value = canonicalizeMailboxProviderAllowlistValue(item?.provider);
                    if (!value || value === 'auto' || seen.has(value)) return;
                    seen.add(value);
                    values.push(value);
                });
            }
            return values;
        }

        function getActiveMailboxProvidersFromTextarea() {
            const el = document.getElementById('activeMailboxProviders');
            if (!el) return [];
            const seen = new Set();
            return String(el.value || '')
                .split(/\r?\n|,/)
                .map(item => canonicalizeMailboxProviderAllowlistValue(item))
                .filter(item => {
                    if (!item || item === 'auto' || seen.has(item)) return false;
                    seen.add(item);
                    return true;
                });
        }

        function setActiveMailboxProvidersTextarea(values) {
            const el = document.getElementById('activeMailboxProviders');
            if (!el) return;
            const seen = new Set();
            const canonicalValues = [];
            (Array.isArray(values) ? values : []).forEach(item => {
                const value = canonicalizeMailboxProviderAllowlistValue(item);
                if (!value || value === 'auto' || seen.has(value)) return;
                seen.add(value);
                canonicalValues.push(value);
            });
            el.value = canonicalValues.join('\n');
        }

        function toggleActiveMailboxProviderSuggestion(providerName) {
            const provider = canonicalizeMailboxProviderAllowlistValue(providerName);
            if (!provider || provider === 'auto') return;
            const current = getActiveMailboxProvidersFromTextarea();
            const next = current.includes(provider)
                ? current.filter(item => item !== provider)
                : [...current, provider];
            setActiveMailboxProvidersTextarea(next);
            renderActiveMailboxProviderSuggestions();
        }

        function getProviderStatusLabel(status) {
            const normalized = String(status || '').trim().toLowerCase();
            if (normalized === 'ready') return translateAppTextLocal('已就绪');
            if (normalized === 'needs_config') return translateAppTextLocal('缺配置');
            if (normalized === 'inactive') return translateAppTextLocal('未启用');
            return normalized || translateAppTextLocal('未知');
        }

        function getProviderStatusBadgeClass(status) {
            const normalized = String(status || '').trim().toLowerCase();
            if (normalized === 'ready') return 'badge-green';
            if (normalized === 'needs_config') return 'badge-gold';
            if (normalized === 'inactive') return 'badge-gray';
            return 'badge-gray';
        }

        function getProviderKindLabel(kind) {
            const normalized = String(kind || '').trim().toLowerCase();
            if (normalized === 'account') return translateAppTextLocal('账号池');
            if (normalized === 'temp') return translateAppTextLocal('临时邮箱');
            return normalized || translateAppTextLocal('未知');
        }

        function getProviderSelectionFallbackText(item) {
            const selection = item && typeof item.selection === 'object' ? item.selection : {};
            const runtimeEnv = selection.runtime_env && typeof selection.runtime_env === 'object' ? selection.runtime_env : {};
            const parts = [];
            const poolClaimProvider = String(selection.pool_claim_provider || '').trim();
            const tempApplyProvider = String(selection.temp_apply_provider_name || '').trim();
            const runtimeProvider = String(runtimeEnv.TEMP_MAIL_PROVIDER || '').trim();
            const matchedProviders = Array.isArray(selection.pool_claim_temp_provider_names) ? selection.pool_claim_temp_provider_names : [];
            const fallbackProviders = Array.isArray(selection.pool_claim_temp_fallback_provider_names) ? selection.pool_claim_temp_fallback_provider_names : [];
            if (poolClaimProvider) parts.push(`claim=${poolClaimProvider}`);
            if (tempApplyProvider) parts.push(`apply=${tempApplyProvider}`);
            if (runtimeProvider) parts.push(`env=${runtimeProvider}`);
            if (matchedProviders.length) parts.push(`matches=${matchedProviders.join('|')}`);
            if (fallbackProviders.length) parts.push(`fallback=${fallbackProviders.join('|')}`);
            return parts.join(' · ') || translateAppTextLocal('池内库存');
        }

        function getProviderDeploymentAssignment(target) {
            if (!target || typeof target !== 'object') return '';
            const key = String(target.env || target.field || '').trim();
            const value = String(target.value || target.settings_value || '').trim();
            if (!key || !value) return '';
            return `${key}=${value}`;
        }

        function getProviderDeploymentConfigNames(target) {
            if (!target || typeof target !== 'object') return [];
            const keys = Array.isArray(target.keys) ? target.keys : [];
            const required = Array.isArray(target.required) ? target.required : [];
            const optional = Array.isArray(target.optional) ? target.optional : [];
            return Array.from(new Set([...keys, ...required, ...optional].map(value => String(value || '').trim()).filter(Boolean)));
        }

        function getProviderDeploymentText(item) {
            const deployment = item && typeof item.deployment === 'object' ? item.deployment : {};
            const parts = [];
            const activate = getProviderDeploymentAssignment(deployment.activate);
            const poolDefault = getProviderDeploymentAssignment(deployment.pool_claim_default);
            const runtimeDefault = getProviderDeploymentAssignment(deployment.runtime_default);
            const poolRequest = getProviderDeploymentAssignment(deployment.pool_claim_request);
            const tempApplyRequest = getProviderDeploymentAssignment(deployment.task_temp_apply_request);
            const envConfigNames = getProviderDeploymentConfigNames(deployment.config_env);
            const settingConfigNames = getProviderDeploymentConfigNames(deployment.config_settings);

            if (activate) parts.push(`${translateAppTextLocal('激活')} ${activate}`);
            if (poolDefault) parts.push(`${translateAppTextLocal('领取默认')} ${poolDefault}`);
            if (runtimeDefault) parts.push(`${translateAppTextLocal('运行默认')} ${runtimeDefault}`);
            if (poolRequest) parts.push(`${translateAppTextLocal('领取')} ${poolRequest}`);
            if (tempApplyRequest) parts.push(`${translateAppTextLocal('申请')} ${tempApplyRequest}`);
            if (envConfigNames.length) parts.push(`${translateAppTextLocal('配置环境变量')} ${envConfigNames.join(', ')}`);
            if (settingConfigNames.length) parts.push(`${translateAppTextLocal('配置项')} ${settingConfigNames.join(', ')}`);

            return parts.join(' · ') || getProviderSelectionFallbackText(item);
        }

        function getProviderConfigText(item) {
            const missing = Array.isArray(item?.missing_config) ? item.missing_config : [];
            if (item?.active === false) return translateAppTextLocal('被白名单排除');
            if (missing.length) return missing.map(getMissingConfigDisplayName).join(getUiLanguage() === 'en' ? ', ' : '、');
            return translateAppTextLocal('本地配置齐全');
        }

        function getProviderCapabilityText(item) {
            const parts = [];
            if (item?.can_dynamic_create) parts.push(translateAppTextLocal('可动态创建'));
            if (item?.requires_pool_inventory) parts.push(translateAppTextLocal('需要池内库存'));
            if (item?.read_capability) parts.push(String(item.read_capability));
            return parts.join(' · ') || translateAppTextLocal('标准读信');
        }

        function getExternalIntegrationManifestProviders() {
            const manifest = getExternalIntegrationManifest();
            return Array.isArray(manifest.providers) ? manifest.providers.filter(item => item && typeof item === 'object') : [];
        }

        function normalizeExternalProviderRecipe(recipe) {
            const item = recipe && typeof recipe === 'object' ? recipe : {};
            const key = String(item.key || '').trim();
            const provider = String(item.provider || '').trim();
            const scope = String(item.scope || '').trim();
            if (!key || !provider || !scope) return null;
            return { ...item, key, provider, scope };
        }

        function getExternalProviderSelectionRecipes() {
            const manifest = getExternalIntegrationManifest();
            const selection = manifest.selection && typeof manifest.selection === 'object' ? manifest.selection : {};
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            const profile = mailboxProviderDeploymentProfileCache && typeof mailboxProviderDeploymentProfileCache === 'object'
                ? mailboxProviderDeploymentProfileCache
                : {};
            const recipeLists = [
                manifest.selection_recipes,
                selection.recipes,
                guide.selection_recipes,
                profile.selection_recipes,
            ];
            for (const list of recipeLists) {
                const recipes = Array.isArray(list) ? list.map(normalizeExternalProviderRecipe).filter(Boolean) : [];
                if (recipes.length) return recipes;
            }
            const recipeIndexes = [
                manifest.selection_recipe_index,
                selection.recipe_index,
                guide.selection_recipe_index,
                profile.selection_recipe_index,
            ];
            for (const index of recipeIndexes) {
                if (!index || typeof index !== 'object') continue;
                const recipes = Object.keys(index).map(key => normalizeExternalProviderRecipe(index[key])).filter(Boolean);
                if (recipes.length) return recipes;
            }
            return [];
        }

        function getExternalProviderRecipeScopeLabel(scope) {
            const labels = {
                active_allowlist: '启用来源',
                temp_runtime_default: '临时邮箱默认',
                pool_claim_default: 'Pool 默认',
                explicit_pool_claim: 'Pool 请求',
                task_temp_apply: '任务临时邮箱请求'
            };
            const normalized = String(scope || '').trim();
            return translateAppTextLocal(labels[normalized] || normalized || 'Provider 选择');
        }

        function getExternalProviderRecipeKindLabel(kind) {
            const normalized = String(kind || '').trim();
            if (normalized === 'temp') return translateAppTextLocal('临时邮箱');
            if (normalized === 'account') return translateAppTextLocal('账号池');
            return normalized || translateAppTextLocal('Provider');
        }

        function normalizeExternalProviderRecipeKey(key, recipes = getExternalProviderSelectionRecipes()) {
            const normalized = String(key || '').trim();
            const values = Array.isArray(recipes) ? recipes : [];
            if (values.some(item => item.key === normalized)) return normalized;
            const preferredScopes = ['explicit_pool_claim', 'task_temp_apply', 'temp_runtime_default', 'pool_claim_default', 'active_allowlist'];
            for (const scope of preferredScopes) {
                const match = values.find(item => item.scope === scope);
                if (match) return match.key;
            }
            return values.length ? values[0].key : '';
        }

        function formatExternalProviderRecipeValue(value) {
            if (value === undefined || value === null) return '';
            if (Array.isArray(value) || typeof value === 'object') return JSON.stringify(value, null, 2);
            if (typeof value === 'boolean') return value ? 'true' : 'false';
            return String(value);
        }

        function getExternalProviderRecipeSecretEnvKeys(recipe) {
            const hints = Array.isArray(recipe && recipe.provider_env) ? recipe.provider_env : [];
            return new Set(hints
                .filter(item => item && typeof item === 'object' && item.secret === true)
                .map(item => String(item.key || '').trim())
                .filter(Boolean));
        }

        function buildExternalProviderRecipeEnvSnippet(envValues, secretKeys = new Set()) {
            const values = envValues && typeof envValues === 'object' ? envValues : {};
            return Object.keys(values)
                .map(key => {
                    const envKey = String(key || '').trim();
                    if (!envKey) return '';
                    const envValue = secretKeys.has(envKey) ? '' : formatExternalProviderRecipeValue(values[key]);
                    return `${envKey}=${envValue}`;
                })
                .filter(Boolean)
                .join('\n');
        }

        function buildExternalProviderRecipeProviderEnvSnippet(recipe) {
            const hints = Array.isArray(recipe && recipe.provider_env) ? recipe.provider_env : [];
            return hints
                .map(hint => {
                    const item = hint && typeof hint === 'object' ? hint : {};
                    const key = String(item.key || '').trim();
                    if (!key) return '';
                    const value = item.secret === true ? '' : formatExternalProviderRecipeValue(item.default !== undefined ? item.default : item.value);
                    return `${key}=${value}`;
                })
                .filter(Boolean)
                .join('\n');
        }

        function formatExternalProviderRecipeJson(value) {
            if (!value || typeof value !== 'object') return '';
            return JSON.stringify(value, null, 2);
        }

        function getExternalProviderRecipeText(recipeKey = externalProviderRecipeKey) {
            const recipes = getExternalProviderSelectionRecipes();
            const selectedKey = normalizeExternalProviderRecipeKey(recipeKey, recipes);
            const recipe = recipes.find(item => item.key === selectedKey) || recipes[0];
            if (!recipe) return '';
            const auth = getExternalIntegrationManifestAuth();
            const configuration = recipe.configuration && typeof recipe.configuration === 'object' ? recipe.configuration : {};
            const providerConfig = configuration.provider_config && typeof configuration.provider_config === 'object' ? configuration.provider_config : {};
            const request = recipe.request && typeof recipe.request === 'object' ? recipe.request : {};
            const secretEnvKeys = getExternalProviderRecipeSecretEnvKeys(recipe);
            const sections = [];
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
            const requiredFields = Array.isArray(request.required_body_fields)
                ? request.required_body_fields.map(item => String(item || '').trim()).filter(Boolean)
                : [];
            const pushSection = (label, content) => {
                const value = String(content || '').trim();
                if (value) sections.push(`[${label}]\n${value}`);
            };
            pushSection('env', envSnippet);
            pushSection('provider_env', providerEnvSnippet);
            pushSection('provider_config.json', providerConfigJson);
            pushSection('provider_config.toml', providerConfigToml);
            pushSection('settings.json', settingsSnippet);
            pushSection('request', [
                method || endpoint ? `${method || 'POST'} ${endpoint}`.trim() : '',
                requiredFields.length ? `required_body_fields: ${requiredFields.join(', ')}` : '',
                requestBody ? `body:\n${requestBody}` : '',
            ].filter(Boolean).join('\n'));
            const headerLines = [
                `# Provider selection recipe: ${recipe.label || recipe.provider}`,
                recipe.description ? `# ${recipe.description}` : '',
                `# key: ${recipe.key}`,
                `# scope: ${recipe.scope}`,
                `# provider: ${recipe.provider}`,
                `# auth: ${auth.header}: ${auth.placeholder}`,
                Array.isArray(recipe.source_priority) && recipe.source_priority.length ? `# source_priority: ${recipe.source_priority.join(' > ')}` : '',
            ].filter(Boolean);
            return `${headerLines.join('\n')}\n\n${sections.join('\n\n')}\n`;
        }

        function setExternalProviderRecipe(key) {
            externalProviderRecipeKey = normalizeExternalProviderRecipeKey(key);
            const root = document.getElementById('externalApiCommandCenter');
            const currentState = root ? String(root.getAttribute('data-state') || 'ready') : 'ready';
            renderExternalApiCommandCenter(externalApiSettingsSnapshot, currentState === 'loading' ? 'ready' : currentState);
        }

        async function copyExternalProviderRecipe() {
            const recipe = getExternalProviderRecipeText(externalProviderRecipeKey);
            try {
                const ok = await copyTextToClipboard(recipe);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('Recipe 已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        function getExternalApiCommandProviderSummary(state) {
            const diagnostics = mailboxProviderDiagnosticsCache || {};
            const summary = diagnostics.summary && typeof diagnostics.summary === 'object' ? diagnostics.summary : {};
            const providers = dedupeMailboxProviderDiagnosticRows(
                Array.isArray(diagnostics.providers) ? diagnostics.providers.filter(item => item && typeof item === 'object') : []
            );
            const activeProviders = providers.filter(item => item.active);
            const readyProviders = providers.filter(item => String(item.status || '').trim().toLowerCase() === 'ready');
            const needsConfigProviders = providers.filter(item => String(item.status || '').trim().toLowerCase() === 'needs_config');
            const total = Number(summary.total || providers.length || 0);
            const active = Number(summary.active || activeProviders.length || 0);
            const ready = Number(summary.ready || summary.configured || readyProviders.length || 0);
            const needsConfig = Number(summary.needs_config || needsConfigProviders.length || 0);
            if (state === 'provider_error' || (!total && !providers.length)) {
                return {
                    unavailable: true,
                    value: '暂不可用',
                    detail: translateAppTextLocal('Provider catalog 未加载'),
                    ready,
                    active,
                    total,
                    needsConfig
                };
            }
            return {
                unavailable: false,
                value: `${ready}/${total}`,
                detail: `${translateAppTextLocal('启用')} ${active} · ${translateAppTextLocal('缺配置')} ${needsConfig}`,
                ready,
                active,
                total,
                needsConfig
            };
        }

        function normalizeProviderContractSummary(validation, fallbackProvider = '') {
            const source = validation && typeof validation === 'object' ? validation : {};
            const summary = source.summary && typeof source.summary === 'object' ? source.summary : {};
            const status = String(source.status || 'unknown').trim().toLowerCase() || 'unknown';
            return {
                provider: String(source.provider || fallbackProvider || '').trim(),
                status: ['valid', 'warning', 'invalid'].includes(status) ? status : 'unknown',
                valid: source.valid === true,
                summary: {
                    errors: Number(summary.errors) || 0,
                    warnings: Number(summary.warnings) || 0,
                    checks: Number(summary.checks) || 0,
                },
                issue_codes: Array.isArray(source.issue_codes)
                    ? source.issue_codes.map(code => String(code || '').trim()).filter(Boolean).slice(0, 6)
                    : [],
            };
        }

        function getProviderContractCatalogRows(payload) {
            const data = payload && typeof payload === 'object' ? payload : {};
            const catalogProviders = Array.isArray(data.mailbox_providers) ? data.mailbox_providers : [];
            const guide = data.provider_integration_guide && typeof data.provider_integration_guide === 'object'
                ? data.provider_integration_guide
                : {};
            const guideProviders = Array.isArray(guide.providers) ? guide.providers : [];
            const rowsByKey = new Map();

            const addProvider = (provider) => {
                if (!provider || typeof provider !== 'object') return;
                const kind = String(provider.kind || '').trim().toLowerCase();
                if (kind && kind !== 'temp') return;
                const rawProviderName = normalizeProviderCatalogName(provider.provider || provider.name);
                if (!rawProviderName) return;
                // Collapse bridge aliases so contract status does not list dual rows.
                const providerName = canonicalizeMailboxProviderAllowlistValue(rawProviderName) || rawProviderName;
                if (!providerName || providerName === 'auto') return;
                const contract = normalizeProviderContractSummary(provider.contract_validation, providerName);
                const key = `${kind || 'temp'}:${providerName}`;
                const existing = rowsByKey.get(key) || {};
                rowsByKey.set(key, {
                    ...existing,
                    provider: providerName,
                    label: String(provider.label || provider.display_name || existing.label || providerName).trim(),
                    kind: kind || existing.kind || 'temp',
                    active: provider.active !== undefined ? provider.active === true : existing.active,
                    configured: provider.configured !== undefined ? provider.configured === true : existing.configured,
                    readiness_status: String(provider.readiness_status || provider.status || existing.readiness_status || '').trim().toLowerCase(),
                    contract,
                });
            };

            catalogProviders.forEach(addProvider);
            guideProviders.forEach(addProvider);
            return Array.from(rowsByKey.values());
        }

        function updateProviderContractStateFromCatalog(payload) {
            providerContractState.catalog = getProviderContractCatalogRows(payload);
            providerContractState.lastUpdated = new Date().toLocaleString();
        }

        function updateProviderContractStateFromPlugins(plugins) {
            providerContractState.plugins = Array.isArray(plugins)
                ? plugins
                    .filter(plugin => plugin && typeof plugin === 'object')
                    .map(plugin => ({
                        name: normalizeProviderCatalogName(plugin.name),
                        display_name: String(plugin.display_name || plugin.name || '').trim(),
                        status: String(plugin.status || '').trim().toLowerCase(),
                        contract: normalizeProviderContractSummary(plugin.contract_validation, plugin.name),
                    }))
                    .filter(plugin => plugin.name)
                : [];
            providerContractState.lastUpdated = new Date().toLocaleString();
            renderProviderContractStatus();
        }

        function getProviderContractPluginMap() {
            const map = new Map();
            providerContractState.plugins.forEach(plugin => {
                if (plugin.name) map.set(plugin.name, plugin);
            });
            return map;
        }

        function getProviderContractStatusTone(contract) {
            const status = String(contract?.status || 'unknown').trim().toLowerCase();
            if (status === 'invalid') return 'invalid';
            if (status === 'warning') return 'warning';
            if (status === 'valid') return 'valid';
            return status === 'invalid' || status === 'warning' || status === 'valid' ? status : 'unknown';
        }

        function getProviderContractStatusLabel(status) {
            const normalized = String(status || 'unknown').trim().toLowerCase();
            if (normalized === 'valid') return translateAppTextLocal('契约有效');
            if (normalized === 'warning') return translateAppTextLocal('契约告警');
            if (normalized === 'invalid') return translateAppTextLocal('契约无效');
            return translateAppTextLocal('契约未知');
        }

        function getProviderWorkbenchConfigFileStatus(settings) {
            const profile = mailboxProviderDeploymentProfileCache && typeof mailboxProviderDeploymentProfileCache === 'object'
                ? mailboxProviderDeploymentProfileCache
                : {};
            const profileConfig = profile.config_file && typeof profile.config_file === 'object' ? profile.config_file : null;
            const settingsConfig = settings && settings.provider_config_file && typeof settings.provider_config_file === 'object'
                ? settings.provider_config_file
                : null;
            const configFile = profileConfig || settingsConfig || {};
            if (configFile.enabled !== true) {
                return {
                    label: translateAppTextLocal('未启用'),
                    detail: 'OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE',
                    tone: 'muted'
                };
            }

            const displayPath = String(configFile.path || configFile.resolved_path || '').trim();
            if (configFile.loaded === true) {
                const sections = Array.isArray(configFile.sections) ? configFile.sections.filter(Boolean).join(', ') : '';
                return {
                    label: translateAppTextLocal('已加载'),
                    detail: [displayPath, sections ? `${translateAppTextLocal('配置项')} ${sections}` : ''].filter(Boolean).join(' · '),
                    tone: 'ready'
                };
            }

            const errorCode = String(configFile.error_code || '').trim();
            return {
                label: translateAppTextLocal(errorCode ? '配置文件错误' : '未加载'),
                detail: [displayPath, errorCode].filter(Boolean).join(' · ') || translateAppTextLocal('Provider catalog 未加载'),
                tone: errorCode ? 'warning' : 'muted'
            };
        }

        function getProviderWorkbenchSecretPolicyText() {
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            const secretPolicy = guide.secret_policy && typeof guide.secret_policy === 'object' ? guide.secret_policy : {};
            if (secretPolicy.exposes_secret_values === false) return translateAppTextLocal('只显示密钥字段名');
            return translateAppTextLocal('密钥策略未知');
        }

        function getProviderWorkbenchRuntimeDefault(settings) {
            const provider = String((settings && settings.temp_mail_provider) || '').trim();
            const label = String((settings && settings.temp_mail_provider_label) || '').trim();
            return {
                value: provider || translateAppTextLocal('暂不可用'),
                detail: label && label !== provider ? label : 'TEMP_MAIL_PROVIDER'
            };
        }

        function normalizeProviderIntegrationFilter(filterName) {
            const normalized = String(filterName || 'all').trim().toLowerCase();
            return ['all', 'temp'].includes(normalized) ? normalized : 'all';
        }

        function syncProviderIntegrationFilterButtons() {
            mailboxProviderIntegrationFilter = normalizeProviderIntegrationFilter(mailboxProviderIntegrationFilter);
            document.querySelectorAll('[data-provider-integration-filter]').forEach(button => {
                const active = normalizeProviderIntegrationFilter(button.getAttribute('data-provider-integration-filter')) === mailboxProviderIntegrationFilter;
                button.classList.toggle('active', active);
                button.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
        }

        function getProviderIntegrationGuideProviders() {
            const guide = mailboxProviderIntegrationGuideCache && typeof mailboxProviderIntegrationGuideCache === 'object'
                ? mailboxProviderIntegrationGuideCache
                : {};
            const providers = Array.isArray(guide.providers)
                ? guide.providers.filter(item => item && typeof item === 'object')
                : [];
            // Reuse diagnostics de-dupe so guide cards collapse bridge aliases.
            return dedupeMailboxProviderDiagnosticRows(providers);
        }

        function getProviderIntegrationProvider(providerName, kind = '') {
            const normalizedProvider = normalizeProviderCatalogName(providerName);
            const normalizedKind = String(kind || '').trim().toLowerCase();
            return getProviderIntegrationGuideProviders().find(item => {
                const sameProvider = normalizeProviderCatalogName(item.provider) === normalizedProvider;
                if (!sameProvider) return false;
                return !normalizedKind || String(item.kind || '').trim().toLowerCase() === normalizedKind;
            }) || null;
        }

        function getProviderIntegrationFilteredProviders(providers) {
            const filter = normalizeProviderIntegrationFilter(mailboxProviderIntegrationFilter);
            if (filter === 'temp') {
                return providers.filter(item => String(item.kind || '').trim().toLowerCase() === 'temp');
            }
            return providers;
        }

        function getProviderIntegrationSecretKeySets(provider) {
            const item = provider && typeof provider === 'object' ? provider : {};
            const configuration = item.configuration && typeof item.configuration === 'object' ? item.configuration : {};
            const normalizeKeys = (values) => Array.isArray(values)
                ? values.map(value => String(value || '').trim()).filter(Boolean)
                : [];
            return {
                env: new Set([
                    ...normalizeKeys(item.secret_env),
                    ...normalizeKeys(configuration.secret_env),
                ]),
                settings: new Set([
                    ...normalizeKeys(item.secret_settings),
                    ...normalizeKeys(configuration.secret_settings),
                ]),
            };
        }

        function formatProviderIntegrationStep(provider, step, fallback = '') {
            if (!step || typeof step !== 'object') return fallback;
            const secretKeys = getProviderIntegrationSecretKeySets(provider);
            const env = step.env && typeof step.env === 'object' ? step.env : null;
            const settings = step.settings && typeof step.settings === 'object' ? step.settings : null;
            const providerConfig = step.provider_config && typeof step.provider_config === 'object' ? step.provider_config : null;
            const field = String(step.field || '').trim();
            const value = step.value !== undefined && step.value !== null ? String(step.value).trim() : '';
            const parts = [];
            if (env && env.key) {
                const envKey = String(env.key || '').trim();
                const envValue = secretKeys.env.has(envKey) ? '' : (env.value !== undefined && env.value !== null ? env.value : '');
                if (envKey) parts.push(`${envKey}=${envValue}`);
            }
            if (settings && settings.key) {
                const settingsKey = String(settings.key || '').trim();
                const settingsValue = secretKeys.settings.has(settingsKey) ? '' : (settings.value !== undefined && settings.value !== null ? settings.value : '');
                if (settingsKey) parts.push(`${settingsKey}=${settingsValue}`);
            }
            if (providerConfig && providerConfig.key) {
                const configValue = Array.isArray(providerConfig.value) ? providerConfig.value.join(',') : providerConfig.value;
                parts.push(`providers.${providerConfig.key}=${configValue !== undefined && configValue !== null ? configValue : ''}`);
            }
            if (field) parts.push(`${field}=${value}`);
            return parts.filter(Boolean).join(' · ') || fallback;
        }

        function getProviderIntegrationRequestText(step) {
            if (!step || typeof step !== 'object') return '';
            const method = String(step.method || '').trim();
            const endpoint = String(step.endpoint || '').trim();
            const field = String(step.field || '').trim();
            const value = step.value !== undefined && step.value !== null ? String(step.value).trim() : '';
            const request = field ? `${field}=${value}` : '';
            return [method, endpoint, request].filter(Boolean).join(' ');
        }

        function getProviderIntegrationAliasesText(provider) {
            const aliases = provider && provider.aliases && typeof provider.aliases === 'object' ? provider.aliases : {};
            const values = [];
            Object.keys(aliases).forEach(key => {
                const aliasValues = Array.isArray(aliases[key]) ? aliases[key].map(value => String(value || '').trim()).filter(Boolean) : [];
                if (aliasValues.length) values.push(`${key}: ${aliasValues.join(', ')}`);
            });
            return values.join(' · ');
        }

        function addProviderIntegrationEnvLine(lines, key, value, secretKeys) {
            const envKey = String(key || '').trim();
            if (!envKey) return;
            const secretSet = secretKeys instanceof Set ? secretKeys : new Set();
            const existingPrefix = `${envKey}=`;
            const nextValue = secretSet.has(envKey) ? '' : String(value === undefined || value === null ? '' : value);
            const nextLine = `${envKey}=${nextValue}`;
            const existingIndex = lines.findIndex(line => line.startsWith(existingPrefix));
            if (existingIndex >= 0) {
                if (!secretSet.has(envKey) && !lines[existingIndex].slice(existingPrefix.length) && nextValue) {
                    lines[existingIndex] = nextLine;
                }
                return;
            }
            lines.push(nextLine);
        }

        function buildProviderIntegrationEnvSnippet(provider) {
            const item = provider && typeof provider === 'object' ? provider : {};
            const providerName = String(item.provider || '').trim();
            const kind = String(item.kind || '').trim().toLowerCase();
            const configuration = item.configuration && typeof item.configuration === 'object' ? item.configuration : {};
            const envDefaults = configuration.env_defaults && typeof configuration.env_defaults === 'object' ? configuration.env_defaults : {};
            const secretKeys = getProviderIntegrationSecretKeySets(item).env;
            const lines = [
                `# ${providerName} provider integration`,
            ];

            if (item.activation && item.activation.env) {
                addProviderIntegrationEnvLine(lines, item.activation.env.key, item.activation.env.value, secretKeys);
            }
            if (item.runtime_default && item.runtime_default.env) {
                addProviderIntegrationEnvLine(lines, item.runtime_default.env.key, item.runtime_default.env.value, secretKeys);
            }
            if (item.pool_claim_default && item.pool_claim_default.env) {
                addProviderIntegrationEnvLine(lines, item.pool_claim_default.env.key, item.pool_claim_default.env.value, secretKeys);
            }

            const configEnvKeys = [
                ...(Array.isArray(item.required_env) ? item.required_env : []),
                ...(Array.isArray(item.optional_env) ? item.optional_env : []),
                ...Object.keys(envDefaults),
            ];
            configEnvKeys.forEach(key => addProviderIntegrationEnvLine(lines, key, envDefaults[key], secretKeys));

            const requestLines = [];
            if (item.pool_claim_request && item.pool_claim_request.field) {
                requestLines.push(`# pool claim request: ${item.pool_claim_request.field}=${item.pool_claim_request.value || providerName}`);
            }
            if (kind === 'temp' && item.task_temp_apply_request && item.task_temp_apply_request.field) {
                requestLines.push(`# task temp apply request: ${item.task_temp_apply_request.field}=${item.task_temp_apply_request.value || providerName}`);
            }
            return [...lines, ...requestLines].join('\n') + '\n';
        }

        async function copyProviderIntegrationSnippet(providerName, kind) {
            const provider = getProviderIntegrationProvider(providerName, kind);
            if (!provider) {
                showToast(translateAppTextLocal('Provider 接入指南暂不可用'), 'warning');
                return;
            }
            const snippet = buildProviderIntegrationEnvSnippet(provider);
            try {
                const ok = await copyTextToClipboard(snippet);
                if (!ok) throw new Error('copy_failed');
                showToast(translateAppTextLocal('Provider 接入片段已复制'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

        function setProviderIntegrationFilter(filterName) {
            mailboxProviderIntegrationFilter = normalizeProviderIntegrationFilter(filterName);
            renderProviderIntegrationGuide();
        }

        function getProviderFilteredItems(providers) {
            const filter = normalizeProviderConsoleFilter(mailboxProviderConsoleFilter);
            if (filter === 'temp' || filter === 'account') {
                return providers.filter(item => String(item.kind || '').trim().toLowerCase() === filter);
            }
            if (filter === 'needs_config') {
                return providers.filter(item => String(item.status || '').trim().toLowerCase() === 'needs_config');
            }
            if (filter === 'active') {
                return providers.filter(item => item.active);
            }
            return providers;
        }

