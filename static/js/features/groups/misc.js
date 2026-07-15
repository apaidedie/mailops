// split from groups.js → misc.js
        function isCurrentMailboxGroupsSurface() {
            return typeof currentPage !== 'undefined' && currentPage === 'mailbox';
        }

        function updateAccountPanelFooter() {
            // No-op: new layout uses topbar action buttons instead
        }

        // 加载分组下的账号
        function getProviderLabel(provider) {
            if (typeof resolveMailboxProviderLabel === 'function') {
                const label = resolveMailboxProviderLabel(provider || 'outlook', {
                    fallback: provider || 'outlook',
                    emptyLabel: '未知',
                    softLoad: true,
                });
                return translateAppTextLocal(label || '未知');
            }
            return translateAppTextLocal(String(provider || '未知').trim() || '未知');
        }

        // 渲染邮箱列表
        function goToAccountPage(page) {
            if (!currentGroupId) return;
            const totalPages = Number(getAccountListMeta().total_pages || 0);
            if (page < 1 || page > totalPages) return;
            currentAccountPage = page;
            loadAccountsByGroup(currentGroupId, false, page);
            const containers = [
                document.getElementById('accountList'),
                document.getElementById('compactAccountList')
            ].filter(Boolean);
            containers.forEach(container => {
                container.scrollTop = 0;
            });
        }

        // 排序相关变量
        let currentSortBy = 'refresh_time';
        let currentSortOrder = 'asc';

        // 账号列表分页状态
        let currentAccountPage = 1;
        const ACCOUNT_PAGE_SIZE = 50;
        let currentAccountSearchQuery = '';
        const accountListMetaCache = {};
        // Coalesce concurrent cold GET /api/accounts for the same queryKey.
        const accountsByGroupLoadPromises = Object.create(null);
        // True when the in-flight accounts GET for a queryKey was started with forceRefresh.
        const accountsByGroupLoadForce = Object.create(null);

        /**
         * Drop soft account-list rows + pagination meta for one group (or all).
         * Mutations must not leave meta.queryKey pointing at a deleted accountsCache entry.
         */
        function buildAccountListQueryKey(groupId, page = currentAccountPage) {
            const params = new URLSearchParams();
            if (groupId !== null && groupId !== undefined) {
                params.set('group_id', String(groupId));
            }
            params.set('page', String(page || 1));
            params.set('page_size', String(ACCOUNT_PAGE_SIZE));
            params.set('sort_by', currentSortBy);
            params.set('sort_order', currentSortOrder);

            const normalizedSearch = String(currentAccountSearchQuery || '').trim();
            if (normalizedSearch) {
                params.set('search', normalizedSearch);
            }

            getSelectedTagFilterIds().forEach(tagId => {
                params.append('tag_id', String(tagId));
            });

            return params.toString();
        }

        function getAccountListMeta(groupId = currentGroupId) {
            const cachedMeta = accountListMetaCache[groupId];
            if (cachedMeta) {
                return cachedMeta;
            }
            const fallbackAccounts = Array.isArray(accountsCache[groupId]) ? accountsCache[groupId] : [];
            return {
                page: currentAccountPage,
                page_size: ACCOUNT_PAGE_SIZE,
                total_count: fallbackAccounts.length,
                total_pages: fallbackAccounts.length > 0 ? 1 : 0,
                queryKey: ''
            };
        }

        function sortAccounts(sortBy) {
            // 如果点击同一个排序按钮，切换排序顺序
            if (currentSortBy === sortBy) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortBy = sortBy;
                currentSortOrder = sortBy === 'refresh_time' ? 'asc' : 'asc';
            }

            // 更新按钮状态
            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.classList.remove('active');
            });

            const activeBtn = document.querySelector(`[data-sort="${sortBy}"]`);
            if (activeBtn) {
                activeBtn.classList.add('active');
            }

            if (currentGroupId) {
                currentAccountPage = 1;  // 排序时重置到第 1 页
                loadAccountsByGroup(currentGroupId, true, 1);
            }
        }

        // 应用筛选和排序
        function applyFiltersAndSort(accounts) {
            return Array.isArray(accounts) ? [...accounts] : [];
        }

        // Tag Filter Change Handler
        function handleTagFilterChange() {
            if (currentGroupId) {
                currentAccountPage = 1;  // 标签过滤时重置到第 1 页
                loadAccountsByGroup(currentGroupId, true, 1);
            }
        }

        // 防抖函数
        function debounce(func, wait) {
            let timeout;
            return function (...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        }

        // 全局搜索函数
        async function searchAccounts(query) {
            const container = document.getElementById('accountList');
            currentAccountSearchQuery = String(query || '').trim();

            if (!currentGroupId) {
                return;
            }

            if (!currentAccountSearchQuery) {
                currentAccountPage = 1;  // 清空搜索时重置页码
                loadAccountsByGroup(currentGroupId, true, 1);
                return;
            }

            const searchingLabel = (typeof translateAppTextLocal === 'function')
                ? translateAppTextLocal('搜索中…')
                : '搜索中…';
            container.innerHTML = '<div class="loading-overlay"><span class="spinner"></span> ' + searchingLabel + '</div>';

            try {
                currentAccountPage = 1;  // 搜索结果重置到第 1 页
                await loadAccountsByGroup(currentGroupId, true, 1);
            } catch (error) {
                console.error('搜索失败:', error);
                const failLabel = (typeof translateAppTextLocal === 'function')
                    ? translateAppTextLocal('搜索失败，请重试')
                    : '搜索失败，请重试';
                container.innerHTML = '<div class="empty-state"><p>' + failLabel + '</p></div>';
            }
        }

        // 更新分组下拉选择框
        function buildVerificationExtractEndpoint(email, options = {}) {
            const normalizedSource = String(options?.source || '').trim().toLowerCase();
            if (normalizedSource === 'temp' || normalizedSource === 'temp-mail' || normalizedSource === 'temp_mail') {
                return `/api/temp-emails/${encodeURIComponent(email)}/extract-verification`;
            }
            return `/api/emails/${encodeURIComponent(email)}/extract-verification`;
        }

        async function tryFallbackVerificationExtraction(options = {}) {
            if (typeof options.fallbackExtractor !== 'function') {
                return null;
            }

            try {
                const fallbackResult = await options.fallbackExtractor();
                if (!fallbackResult || !fallbackResult.formatted) {
                    return null;
                }
                return fallbackResult;
            } catch (fallbackError) {
                console.error('本地兜底提取失败:', fallbackError);
                return null;
            }
        }

        async function copyVerificationInfo(email, buttonElement, options = {}) {
            const requestKey = String(email || '').trim().toLowerCase();
            if (!requestKey || verificationCopyInFlight.has(requestKey)) {
                return false;
            }
            verificationCopyInFlight.add(requestKey);

            // 禁用按钮并显示加载状态
            const originalContent = buttonElement.innerHTML;
            buttonElement.disabled = true;
            buttonElement.innerHTML = '⏳';
            buttonElement.style.opacity = '0.6';
            buttonElement.style.cursor = 'wait';

            try {
                const response = await fetch(buildVerificationExtractEndpoint(email, options));
                const data = await response.json();

                if (data.success && data.data && data.data.formatted) {
                    await copyToClipboard(data.data.formatted);
                    syncExtractedVerificationToAccountCache(email, data.data, data.account_summary || null);
                    if (typeof window.notifyOverviewDataChanged === 'function') {
                        window.notifyOverviewDataChanged(['summary', 'verification', 'activity'], 'verification-extracted');
                    }
                    showToast(
                        translateAppTextLocal('已复制: ' + data.data.formatted),
                        'success'
                    );
                    // 成功状态
                    buttonElement.innerHTML = '✅';
                    buttonElement.style.opacity = '1';
                    return true;
                } else {
                    const fallbackResult = await tryFallbackVerificationExtraction(options);
                    if (fallbackResult) {
                        await copyToClipboard(
                            fallbackResult.copyText || fallbackResult.verification_code || fallbackResult.verification_link || fallbackResult.formatted
                        );
                        const copiedValue = fallbackResult.displayValue || fallbackResult.verification_code || fallbackResult.verification_link || fallbackResult.formatted;
                        showToast(
                            translateAppTextLocal('已从当前邮件兜底复制: ' + copiedValue),
                            'warning'
                        );
                        buttonElement.innerHTML = '✅';
                        buttonElement.style.opacity = '1';
                        return true;
                    }

                    const errorMsg = window.resolveApiErrorMessage
                        ? window.resolveApiErrorMessage(data.error || data, '未找到验证码或链接', 'No verification code or link was found')
                        : (data.error?.message || data.error || '未找到验证码或链接');
                    showToast(errorMsg, 'error');
                    // 失败状态
                    buttonElement.innerHTML = '❌';
                    buttonElement.style.opacity = '1';
                    return false;
                }
            } catch (error) {
                console.error('提取验证码失败:', error);
                const fallbackResult = await tryFallbackVerificationExtraction(options);
                if (fallbackResult) {
                    await copyToClipboard(
                        fallbackResult.copyText || fallbackResult.verification_code || fallbackResult.verification_link || fallbackResult.formatted
                    );
                    const copiedValue = fallbackResult.displayValue || fallbackResult.verification_code || fallbackResult.verification_link || fallbackResult.formatted;
                    showToast(
                        translateAppTextLocal('已从当前邮件兜底复制: ' + copiedValue),
                        'warning'
                    );
                    buttonElement.innerHTML = '✅';
                    buttonElement.style.opacity = '1';
                    return true;
                }
                showToast(translateAppTextLocal('网络错误，请重试'), 'error');
                // 失败状态
                buttonElement.innerHTML = '❌';
                buttonElement.style.opacity = '1';
                return false;
            } finally {
                verificationCopyInFlight.delete(requestKey);
                // 延迟恢复按钮状态
                setTimeout(() => {
                    buttonElement.disabled = false;
                    buttonElement.innerHTML = originalContent;
                    buttonElement.style.cursor = 'pointer';
                }, 1500);
            }
        }

        // 复制文本到剪贴板
        async function copyToClipboard(text) {
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(text);
                } else {
                    // 降级方案：使用 textarea
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    textarea.style.position = 'fixed';
                    textarea.style.left = '-9999px';
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                }
            } catch (error) {
                console.error('复制失败:', error);
                throw error;
            }
        }

        // Fix: #accountList 在 i18n skip 列表中，MutationObserver 不会自动翻译。
        // 切换语言时必须手动重渲染账号列表，否则账号卡片文字保留旧语言（如
        // Unknown / 16 hours ago 混搭中文）。简洁模式已在 mailbox_compact.js 正确处理，
        // 此处补全标准模式。
        window.addEventListener('ui-language-changed', () => {
            // Soft re-paint warm inventory chrome without network.
            // Include empty arrays so empty-state chrome re-translates too.
            try {
                if (
                    isCurrentMailboxGroupsSurface()
                    && Array.isArray(groups)
                    && typeof renderGroupList === 'function'
                ) {
                    const groupListEl = document.getElementById('groupList');
                    if (groups.length > 0 || (groupListEl && groupListEl.querySelector('.empty-state'))) {
                        renderGroupList(groups);
                    }
                }
            } catch (e) {}
            try {
                if (typeof updateGroupSelects === 'function') {
                    updateGroupSelects();
                }
            } catch (e) {}
            try {
                if (typeof ensurePoolAdminGroupOptions === 'function') {
                    Promise.resolve(ensurePoolAdminGroupOptions(false)).catch(() => {});
                }
            } catch (e) {}
            try {
                // Only soft-paint standard mailbox inventory while on the mailbox page.
                // Never repaint shared #accountList on temp-emails/settings/etc., and skip
                // the temp group id (dedicated page owns that inventory surface).
                if (
                    typeof currentPage !== 'undefined'
                    && currentPage === 'mailbox'
                    && !isTempEmailGroup
                    && Array.isArray(accountsCache[currentGroupId])
                    && typeof renderAccountList === 'function'
                ) {
                    renderAccountList(accountsCache[currentGroupId]);
                }
            } catch (e) {}
        });

