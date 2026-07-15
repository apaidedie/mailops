// split from groups.js → data.js
        function applyLoadedGroups(groupList, { refreshAccounts = true } = {}) {
            groups = Array.isArray(groupList) ? groupList : [];

            // 找到临时邮箱分组
            const tempGroup = groups.find(g => g.name === '临时邮箱');
            if (tempGroup) {
                tempEmailGroupId = tempGroup.id;
            }

            // Always warm global groups array. Mailbox sidebar/compact strip paint only
            // on the mailbox surface so export/pool soft loadGroups cannot rewrite hidden DOM.
            if (isCurrentMailboxGroupsSurface()) {
                renderGroupList(groups);
                if (typeof renderCompactGroupStrip === 'function') {
                    renderCompactGroupStrip(groups, currentGroupId);
                }
            }
            updateGroupSelects();
            // Keep pool-admin group filter aligned when groups mutate while that page is open
            // (or after soft loadGroups from other surfaces). Soft re-paint only — no force GET.
            if (typeof ensurePoolAdminGroupOptions === 'function') {
                Promise.resolve(ensurePoolAdminGroupOptions(false)).catch(() => {});
            }

            if (!refreshAccounts) {
                return;
            }

            // Account inventory refresh is mailbox-surface work; off-page soft/force loads
            // (export/pool-admin) should only warm groups + selects/filters.
            if (!isCurrentMailboxGroupsSurface()) {
                return;
            }

            // 如果之前选中了分组，保持选中状态并刷新邮箱列表
            if (currentGroupId) {
                const group = groups.find(g => g.id === currentGroupId);
                if (group) {
                    // 刷新当前分组的邮箱列表
                    if (currentGroupId === tempEmailGroupId) {
                        loadTempEmails(true);
                    } else {
                        // Fire-and-forget account refresh; callers may still await loadGroups.
                        Promise.resolve(loadAccountsByGroup(currentGroupId, true)).catch(() => {});
                    }
                }
            } else if (currentPage !== 'temp-emails') {
                // BUG-06 修复：在临时邮箱页面时，不自动选组。
                // 自动选组会调用 selectGroup()，进而清空 currentAccount，
                // 导致用户在临时邮箱页选中的邮箱被意外重置。
                // 仅在其他页面（mailbox/dashboard 等）才执行首次自动选组。
                const firstNormalGroup = groups.find(g => !isTempMailboxGroup(g));
                if (firstNormalGroup) {
                    selectGroup(firstNormalGroup.id);
                }
            }
        }

        // 加载分组列表
        async function loadGroups(forceRefresh = false) {
            const container = document.getElementById('groupList');
            const force = Boolean(forceRefresh);
            // Soft re-entry: warm groups array paints without /api/groups.
            // Mutations must pass forceRefresh=true (create/delete/import/move).
            if (!force && Array.isArray(groups) && groups.length > 0) {
                applyLoadedGroups(groups, { refreshAccounts: false });
                return groups;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so create/delete/import always start a true network GET.
            if (groupsLoadPromise) {
                if (!force || groupsLoadForce) {
                    return groupsLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                groupsLoadPromise = null;
                groupsLoadForce = false;
            }

            // Loading chrome only while mailbox sidebar is the active surface.
            // Pool-admin / export / batch-move soft-loads must not flash #groupList spinner.
            const paintSidebarChrome = isCurrentMailboxGroupsSurface();
            if (paintSidebarChrome && container) {
                container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> ${translateAppTextLocal('加载中…')}</div>`;
            }

            groupsLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/groups');
                    const data = await response.json();

                    // If force supersede abandoned this request, do not repaint stale groups.
                    if (groupsLoadPromise !== request) {
                        return groups;
                    }
                    if (data.success) {
                        // Only the network path refreshes accounts after a real reload.
                        applyLoadedGroups(data.groups, { refreshAccounts: true });
                    }
                    return groups;
                } catch (error) {
                    if (groupsLoadPromise !== request) {
                        return groups;
                    }
                    // Error chrome only on mailbox sidebar; still toast so off-page callers see failure.
                    if (isCurrentMailboxGroupsSurface() && container) {
                        container.innerHTML = `<div class="empty-state"><p>${translateAppTextLocal('加载失败')}</p></div>`;
                    }
                    showToast(translateAppTextLocal('加载分组失败'), 'error');
                    return groups;
                }
            })();

            groupsLoadPromise = request;
            try {
                return await request;
            } finally {
                if (groupsLoadPromise === request) {
                    groupsLoadPromise = null;
                    groupsLoadForce = false;
                }
            }
        }

        // 渲染分组列表
        async function loadAccountsByGroup(groupId, forceRefresh = false, page = currentAccountPage) {
            const container = document.getElementById('accountList');
            // Capture target identity at request start so rapid group/page/filter switches
            // cannot paint a stale inventory into the active #accountList.
            const targetGroupId = groupId;
            const queryKey = buildAccountListQueryKey(groupId, page);
            const isCurrentAccountListView = () => (
                Number(currentGroupId) === Number(targetGroupId)
                && buildAccountListQueryKey(currentGroupId, currentAccountPage) === queryKey
            );

            // Force-refresh means account inventory may have changed; drop unified soft directory
            // and audit soft cache (create/delete/import writes audit rows).
            if (forceRefresh) {
                if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                    window.invalidateUnifiedMailboxDirectoryCache();
                }
                if (typeof window.invalidateAuditLogPageCache === 'function') {
                    window.invalidateAuditLogPageCache();
                }
            }

            // 保存当前滚动位置（forceRefresh 时恢复）
            const savedScrollTop = forceRefresh && container ? container.scrollTop : 0;
            const cachedMeta = accountListMetaCache[groupId];

            const force = Boolean(forceRefresh);
            // Soft re-entry: always return warm cache; paint only while still on this group+query.
            if (!force && Array.isArray(accountsCache[groupId]) && cachedMeta && cachedMeta.queryKey === queryKey) {
                if (isCurrentAccountListView()) {
                    currentAccountPage = Number(cachedMeta.page || page || 1);
                    renderAccountList(accountsCache[groupId]);
                    if (typeof renderCompactAccountList === 'function') {
                        renderCompactAccountList(accountsCache[groupId]);
                    }
                }
                // 标准模式：不再在加载分组时批量启动轮询
                // 轮询仅在用户选中单个账号时启动（selectAccount 中处理）
                // 这避免了首次加载、导航切换、分组切换时的 N×4 并发 API 请求
                return accountsCache[groupId];
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so import/delete always start a true network GET.
            if (accountsByGroupLoadPromises[queryKey]) {
                if (!force || accountsByGroupLoadForce[queryKey]) {
                    return accountsByGroupLoadPromises[queryKey];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                delete accountsByGroupLoadPromises[queryKey];
                delete accountsByGroupLoadForce[queryKey];
            }

            // Loading chrome only for the currently visible group+query (force keeps old UI).
            const paintLoadingChrome = !force && isCurrentAccountListView();
            if (paintLoadingChrome && container) {
                container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> ${translateAppTextLocal('加载中…')}</div>`;
                if (typeof renderCompactLoadingState === 'function') {
                    renderCompactLoadingState(translateAppTextLocal('加载中…'));
                }
            }

            accountsByGroupLoadForce[queryKey] = force;
            const request = (async () => {
                try {
                    const response = await fetch(`/api/accounts?${queryKey}`);
                    const data = await response.json();

                    if (accountsByGroupLoadPromises[queryKey] !== request) {
                        return accountsCache[groupId];
                    }
                    if (data.success) {
                        // Always warm inventory soft cache; only sync live page cursor + paint
                        // while still on this group+query (stale responses must not rewrite UI state).
                        updateAccountListCache(groupId, data.accounts, data.pagination, queryKey, {
                            syncCurrentPage: isCurrentAccountListView()
                        });
                        if (isCurrentAccountListView()) {
                            renderAccountList(accountsCache[groupId]);
                            if (typeof renderCompactAccountList === 'function') {
                                renderCompactAccountList(accountsCache[groupId]);
                            }
                            // 恢复滚动位置
                            if (force && container) {
                                requestAnimationFrame(() => { container.scrollTop = savedScrollTop; });
                            }
                        }
                        // 标准模式：不再在加载分组时批量启动轮询
                        // 轮询仅在用户选中单个账号时启动（selectAccount 中处理）
                        // 这避免了首次加载、导航切换、分组切换时的 N×4 并发 API 请求
                    }
                    return accountsCache[groupId];
                } catch (error) {
                    if (accountsByGroupLoadPromises[queryKey] !== request) {
                        return accountsCache[groupId];
                    }
                    // Error chrome only while still on this group+query.
                    if (isCurrentAccountListView()) {
                        if (container) {
                            container.innerHTML = `<div class="empty-state"><p>${translateAppTextLocal('加载失败')}</p></div>`;
                        }
                        if (typeof renderCompactErrorState === 'function') {
                            renderCompactErrorState(translateAppTextLocal('加载失败'));
                        }
                    }
                    return accountsCache[groupId];
                } finally {
                    if (accountsByGroupLoadPromises[queryKey] === request) {
                        delete accountsByGroupLoadPromises[queryKey];
                        delete accountsByGroupLoadForce[queryKey];
                    }
                }
            })();

            accountsByGroupLoadPromises[queryKey] = request;
            return request;
        }

        // 获取 provider 展示名（账号卡片 tag）——共享 catalog helper，避免名单漂移
        function invalidateAccountsCache(groupId) {
            if (groupId === undefined || groupId === null || groupId === '') {
                for (const key of Object.keys(accountsCache)) {
                    delete accountsCache[key];
                }
                for (const key of Object.keys(accountListMetaCache)) {
                    delete accountListMetaCache[key];
                }
                for (const key of Object.keys(accountsByGroupLoadPromises)) {
                    delete accountsByGroupLoadPromises[key];
                    delete accountsByGroupLoadForce[key];
                }
                return;
            }
            const key = String(groupId);
            delete accountsCache[groupId];
            // Also drop string/number key variants that may have been used as object keys.
            delete accountsCache[key];
            delete accountListMetaCache[groupId];
            delete accountListMetaCache[key];
            const prefix = `group_id=${encodeURIComponent(key)}`;
            const prefixAlt = `group_id=${key}`;
            for (const queryKey of Object.keys(accountsByGroupLoadPromises)) {
                if (
                    queryKey.includes(prefix)
                    || queryKey.includes(prefixAlt)
                    || queryKey === key
                ) {
                    delete accountsByGroupLoadPromises[queryKey];
                    delete accountsByGroupLoadForce[queryKey];
                }
            }
        }
        window.invalidateAccountsCache = invalidateAccountsCache;

        function updateAccountListCache(groupId, accounts, pagination, queryKey, options = {}) {
            const safeAccounts = Array.isArray(accounts) ? accounts : [];
            const safePagination = pagination && typeof pagination === 'object'
                ? pagination
                : { page: currentAccountPage || 1, page_size: ACCOUNT_PAGE_SIZE, total_count: safeAccounts.length, total_pages: safeAccounts.length > 0 ? 1 : 0 };
            // Default true preserves prior callers; loadAccountsByGroup passes false for stale views.
            const syncCurrentPage = options.syncCurrentPage !== false;

            accountsCache[groupId] = safeAccounts;
            accountListMetaCache[groupId] = {
                page: Number(safePagination.page || 1),
                page_size: Number(safePagination.page_size || ACCOUNT_PAGE_SIZE),
                total_count: Number(safePagination.total_count || 0),
                total_pages: Number(safePagination.total_pages || 0),
                queryKey
            };
            if (syncCurrentPage) {
                currentAccountPage = Number(accountListMetaCache[groupId].page || 1);
            }
        }

        // 排序账号列表
        function syncAccountSummaryToAccountCache(email, accountSummary) {
            const normalizedEmail = String(email || '').trim().toLowerCase();
            if (!normalizedEmail || !accountSummary || typeof accountSummary !== 'object') {
                return false;
            }

            let updated = false;
            Object.values(accountsCache).forEach(accounts => {
                if (!Array.isArray(accounts)) {
                    return;
                }

                accounts.forEach(account => {
                    if (!account || String(account.email || '').trim().toLowerCase() !== normalizedEmail) {
                        return;
                    }

                    account.latest_email_subject = String(accountSummary.latest_email_subject || '');
                    account.latest_email_from = String(accountSummary.latest_email_from || '');
                    account.latest_email_folder = String(accountSummary.latest_email_folder || '');
                    account.latest_email_received_at = String(accountSummary.latest_email_received_at || '');
                    account.latest_verification_code = String(accountSummary.latest_verification_code || '');
                    account.latest_verification_folder = String(accountSummary.latest_verification_folder || '');
                    account.latest_verification_received_at = String(accountSummary.latest_verification_received_at || '');
                    updated = true;
                });
            });

            if (updated) {
                rerenderAccountCaches();
            }

            return updated;
        }

        function syncExtractedVerificationToAccountCache(email, verificationData, accountSummary = null) {
            if (syncAccountSummaryToAccountCache(email, accountSummary)) {
                return true;
            }

            const normalizedEmail = String(email || '').trim().toLowerCase();
            const verificationCode = String(
                verificationData?.verification_code || verificationData?.verificationCode || ''
            ).trim();

            if (!normalizedEmail || !verificationCode) {
                return false;
            }

            let updated = false;
            Object.values(accountsCache).forEach(accounts => {
                if (!Array.isArray(accounts)) {
                    return;
                }

                accounts.forEach(account => {
                    if (!account || String(account.email || '').trim().toLowerCase() !== normalizedEmail) {
                        return;
                    }

                    account.latest_verification_code = verificationCode;
                    if (verificationData?.folder) {
                        account.latest_verification_folder = String(verificationData.folder);
                    }
                    if (verificationData?.received_at) {
                        account.latest_verification_received_at = String(verificationData.received_at);
                    }
                    if (verificationData?.subject && !account.latest_email_subject) {
                        account.latest_email_subject = String(verificationData.subject);
                    }
                    updated = true;
                });
            });

            if (!updated) {
                return false;
            }
            rerenderAccountCaches();

            return true;
        }

        // 复制验证信息到剪贴板
        const verificationCopyInFlight = new Set();

