// split from accounts.js → data.js
        function invalidateAccountDetailCache(accountId) {
            const key = String(accountId || '').trim();
            if (!key) return;
            accountDetailCache.delete(key);
            delete accountDetailLoadPromises[key];
            delete accountDetailLoadForce[key];
        }

        function invalidateAccountDetailCacheMany(accountIds) {
            const list = Array.isArray(accountIds) ? accountIds : [];
            list.forEach(id => invalidateAccountDetailCache(id));
        }

        // Cross-feature invalidation (batch delete/status in main.js).
        window.invalidateAccountDetailCache = invalidateAccountDetailCache;
        window.invalidateAccountDetailCacheMany = invalidateAccountDetailCacheMany;

        function getImportAccountProviderOptionsFromPayload(data) {
            const payload = data && typeof data === 'object' ? data : {};
            const catalog = Array.isArray(payload.mailbox_providers) ? payload.mailbox_providers : [];
            const catalogAccountOptions = catalog
                .filter(item => String(item?.kind || '').trim().toLowerCase() === 'account')
                .map(normalizeImportAccountProviderOption)
                .filter(Boolean);
            if (catalogAccountOptions.length) {
                return ensureAutoImportProviderOption(catalogAccountOptions);
            }

            const legacy = Array.isArray(payload.providers) ? payload.providers : [];
            const legacyOptions = legacy.map(normalizeImportAccountProviderOption).filter(Boolean);
            return ensureAutoImportProviderOption(legacyOptions);
        }

        async function loadProviders(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            const select = document.getElementById('accountProvider');
            if (!select) return providerOptions;

            const applyImportProviderOptions = (options) => {
                const normalized = ensureAutoImportProviderOption(options);
                if (!Array.isArray(normalized) || !normalized.length) throw new Error('providers_empty');

                // Keep auto first when present for operator ergonomics.
                const autoOptions = normalized.filter(item => item.key === 'auto');
                const otherOptions = normalized.filter(item => item.key !== 'auto');
                providerOptions = [...autoOptions, ...otherOptions];
                providersLoaded = true;

                // Always warm soft options; paint #accountProvider only while import modal open.
                // Catalog soft re-entry / language change must not rewrite a closed import form.
                if (!isAddAccountModalOpen()) {
                    return;
                }

                const previous = select.value || '';
                select.innerHTML = providerOptions.map(p => (
                    `<option value="${escapeHtml(p.key)}">${escapeHtml(translateAppTextLocal(p.label || p.key))}</option>`
                )).join('');

                const preferred = [previous, 'auto', 'outlook']
                    .map(item => String(item || '').trim())
                    .find(item => item && select.querySelector(`option[value="${item}"]`));
                if (preferred) select.value = preferred;
                updateAccountProviderNote(select.value);
            };

            const optionsFromSharedCatalogCache = () => {
                if (
                    typeof mailboxProviderCatalogCache === 'undefined'
                    || !Array.isArray(mailboxProviderCatalogCache)
                    || !mailboxProviderCatalogCache.length
                ) {
                    return null;
                }
                const options = getImportAccountProviderOptionsFromPayload({
                    mailbox_providers: mailboxProviderCatalogCache,
                });
                return options.length ? options : null;
            };

            // Soft re-entry: re-paint from warm shared catalog without a second network GET.
            // Do not early-return before re-paint once providersLoaded is true.
            if (providersLoaded && !force) {
                try {
                    const cachedOptions = optionsFromSharedCatalogCache();
                    if (cachedOptions) {
                        applyImportProviderOptions(cachedOptions);
                    }
                } catch (_err) {
                    /* keep previously painted options */
                }
                return providerOptions;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so catalog refresh always starts a true load path.
            if (providersLoadPromise) {
                if (!force || providersLoadForce) {
                    return providersLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                providersLoadPromise = null;
                providersLoadForce = false;
            }

            providersLoadForce = force;
            const request = (async () => {
                try {
                    // Prefer warm shared cache (boot preload / settings / plugin lifecycle).
                    if (!force) {
                        const cachedOptions = optionsFromSharedCatalogCache();
                        if (cachedOptions) {
                            if (providersLoadPromise !== request) return providerOptions;
                            applyImportProviderOptions(cachedOptions);
                            return providerOptions;
                        }
                    }

                    // Prefer shared loader so import does not race a second /api/providers fetch.
                    // Empty array cache needs force=true because loadMailboxProviderCatalog treats any array as warm.
                    if (typeof loadMailboxProviderCatalog === 'function') {
                        const forceCatalogLoad = force || (
                            typeof mailboxProviderCatalogCache !== 'undefined'
                            && Array.isArray(mailboxProviderCatalogCache)
                            && mailboxProviderCatalogCache.length === 0
                        );
                        await loadMailboxProviderCatalog(forceCatalogLoad);
                        if (providersLoadPromise !== request) return providerOptions;
                        const cachedOptions = optionsFromSharedCatalogCache();
                        if (cachedOptions) {
                            applyImportProviderOptions(cachedOptions);
                            return providerOptions;
                        }
                    }

                    // Last-resort fallback when shared loader/cache is unavailable.
                    const resp = await fetch('/api/providers');
                    const data = await resp.json();
                    if (providersLoadPromise !== request) return providerOptions;
                    if (!data || data.success === false) throw new Error('providers_payload_failed');
                    applyImportProviderOptions(getImportAccountProviderOptionsFromPayload(data));
                } catch (e) {
                    if (providersLoadPromise !== request) return providerOptions;
                    // Keep a minimal fallback so import remains usable offline.
                    // Paint fallback options only while the add-account modal is open.
                    // Always recover from stuck "加载 Provider 目录…" placeholder.
                    ensureImportProviderSelectOptions(select);
                    if (!providerOptions.length) {
                        providerOptions = getDefaultImportAccountProviderOptions();
                        providersLoaded = true;
                    }
                }
                return providerOptions;
            })();

            providersLoadPromise = request;
            try {
                return await request;
            } finally {
                if (providersLoadPromise === request) {
                    providersLoadPromise = null;
                    providersLoadForce = false;
                }
            }
        }

        // Provider 切换：更新 placeholder / hint / custom IMAP 配置区显示
        async function loadExportGroupList() {
            const container = document.getElementById('exportGroupList');
            if (!container) return;

            try {
                // Soft warm path: paint immediately without loading spinner flash.
                if (Array.isArray(groups) && groups.length > 0) {
                    paintExportGroupList(groups, new Set());
                } else {
                    if (isExportModalOpen()) {
                        container.innerHTML = '<div class="loading-overlay"><span class="spinner"></span></div>';
                    }
                    // Prefer shared soft loadGroups; avoid empty false-negative when cold.
                    if (typeof loadGroups === 'function') {
                        await loadGroups(false);
                    }
                    paintExportGroupList(Array.isArray(groups) ? groups : [], new Set());
                }
            } catch (error) {
                if (isExportModalOpen()) {
                    container.innerHTML = `<div class="empty-state"><p style="color:var(--clr-danger)">${translateAppTextLocal('加载失败')}</p></div>`;
                }
            }

            if (isExportModalOpen()) {
                const selectAll = document.getElementById('selectAllGroups');
                if (selectAll) selectAll.checked = false;
            }
        }

        // Language change soft-paints open export modal without network.
        window.addEventListener('ui-language-changed', () => {
            try {
                softPaintExportGroupListIfOpen();
            } catch (_e) {}
        });

        // 全选/取消全选分组
