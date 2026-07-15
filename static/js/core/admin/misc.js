// split from admin.js → misc.js
        async function autoLoadFailedListIfNeeded() {
            try {
                const data = await fetchFailedRefreshLogs(false);
                if (data && data.success && data.logs && data.logs.length > 0) {
                    // 有失败记录，自动显示失败列表
                    showFailedListFromData(mapFailedRefreshLogRows(data.logs));
                }
            } catch (error) {
                console.error('自动加载失败列表失败:', error);
            }
        }

        // 隐藏刷新模态框
        async function retryFailedAccounts() {
            const btn = document.getElementById('retryFailedBtn');
            const progress = document.getElementById('refreshProgress');
            const progressText = document.getElementById('refreshProgressText');

            if (btn.disabled) return;

            btn.disabled = true;
            btn.textContent = translateAppTextLocal('重试中...');
            progress.style.display = 'block';
            progressText.textContent = translateAppTextLocal('正在重试失败的账号...');

            try {
                const response = await fetch('/api/accounts/refresh-failed', {
                    method: 'POST'
                });
                const data = await response.json();

                progress.style.display = 'none';
                btn.disabled = false;
                btn.textContent = translateAppTextLocal('🔁 重试失败');

                if (data.success) {
                    if (data.total === 0) {
                        showToast(translateAppTextLocal('没有需要重试的失败账号'), 'info');
                    } else {
                        showToast(
                            translateAppTextLocal(
                                '重试完成！成功: ' + data.success_count + ', 失败: ' + data.failed_count
                            ),
                            data.failed_count > 0 ? 'warning' : 'success'
                        );

                        // 刷新统计
                        loadRefreshStats(true);

                        // 失效 Token 治理
                        const retryInvalidTokenCount = Number(data.invalid_token_failed_count || 0);
                        latestInvalidTokenDetectedCount = retryInvalidTokenCount;
                        if (retryInvalidTokenCount > 0) {
                            showInvalidTokenDetectionSummary(retryInvalidTokenCount, data.invalid_token_failed_list || []);
                            loadInvalidTokenGovernanceCandidates({
                                forceRefresh: true,
                                keepVisibleWhenEmpty: true,
                                silentWhenEmpty: false
                            });
                        }

                        // 如果还有失败的，显示失败列表
                        if (data.failed_count > 0) {
                            showFailedListFromData(data.failed_list);
                        } else {
                            hideFailedList();
                        }
                        if (typeof invalidateRefreshLogPageCache === 'function') {
                            invalidateRefreshLogPageCache();
                        }
                        if (typeof invalidateAuditLogPageCache === 'function') {
                            invalidateAuditLogPageCache();
                        }
                    }
                } else {
                    const errCode = data && data.error && data.error.code;
                    if (errCode === 'REFRESH_CONFLICT') {
                        const msg = window.resolveApiErrorMessage
                            ? window.resolveApiErrorMessage(data.error, '当前已有刷新任务执行中，请等待当前任务完成后再重试', 'Another refresh task is already running. Wait for it to finish and retry.')
                            : translateAppTextLocal('当前已有刷新任务执行中，请等待当前任务完成后再重试');
                        showToast(msg, 'warning', data.error || null, true);
                    } else {
                        handleApiError(data, '重试失败');
                    }
                }
            } catch (error) {
                progress.style.display = 'none';
                btn.disabled = false;
                btn.textContent = translateAppTextLocal('🔁 重试失败');
                showToast(translateAppTextLocal('重试请求失败'), 'error');
            }
        }

        // 单个账号重试
        async function retrySingleAccount(accountId, accountEmail) {
            try {
                const response = await fetch(`/api/accounts/${accountId}/retry-refresh`, {
                    method: 'POST'
                });
                const data = await response.json();

                if (data.success) {
                    showToast(
                        translateAppTextLocal(accountEmail + ' 刷新成功'),
                        'success'
                    );
                    loadRefreshStats(true);

                    // 刷新失败列表（force network after single retry mutation）
                    loadFailedLogs(true);
                    if (typeof invalidateRefreshLogPageCache === 'function') {
                        invalidateRefreshLogPageCache();
                    }
                    if (typeof invalidateAuditLogPageCache === 'function') {
                        invalidateAuditLogPageCache();
                    }
                } else {
                    handleApiError(data, `${accountEmail} 刷新失败`);
                }
            } catch (error) {
                handleApiError({
                    success: false,
                    error: {
                        message: '刷新请求失败',
                        message_en: 'Refresh request failed',
                        details: error.message,
                        code: 'NETWORK_ERROR',
                        type: 'Frontend'
                    }
                });
            }
        }

        // 显示失败列表（从数据）
        function showFailedListFromData(failedList) {
            const container = document.getElementById('failedListContainer');
            const listEl = document.getElementById('failedList');

            // 隐藏其他列表
            hideRefreshLogs();

            // Seed soft cache from live mutation payloads (SSE complete / retry).
            const rows = Array.isArray(failedList) ? failedList : [];
            failedRefreshLogsCache = {
                success: true,
                logs: rows.map(item => ({
                    account_id: item.id ?? item.account_id,
                    account_email: item.email ?? item.account_email,
                    error_message: item.error ?? item.error_message,
                    created_at: item.created_at || null
                }))
            };

            if (!failedList || failedList.length === 0) {
                container.style.display = 'none';
                return;
            }

            let html = '';
            failedList.forEach(item => {
                html += `
                    <div style="padding: 12px; border-bottom: 1px solid #e5e5e5; display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div style="font-weight: 600; margin-bottom: 4px;">${escapeHtml(item.email)}</div>
                            <div style="font-size: 12px; color: #dc3545;">${escapeHtml(item.error || translateAppTextLocal('未知错误'))}</div>
                        </div>
                        <button class="btn btn-sm btn-primary" onclick="retrySingleAccount(${item.id}, '${escapeHtml(item.email)}')">
                            ${translateAppTextLocal('重试')}
                        </button>
                    </div>
                `;
            });

            listEl.innerHTML = html;
            container.style.display = 'block';
        }

        // 隐藏失败列表
        function hideFailedList() {
            document.getElementById('failedListContainer').style.display = 'none';
            // Empty failed set after successful bulk retry.
            failedRefreshLogsCache = { success: true, logs: [] };
        }

        function formatDateTime(dateStr) {
            return formatUiDateTime(dateStr, { fallback: '-' });
        }

        // 统一关闭所有模态框的函数 (修复 bug：防止模态框意外残留)
        function closeAllModals() {
            hideAddGroupModal();
            hideAddAccountModal();
            hideEditAccountModal();
            hideExportModal();
            hideSettingsModal();
            hideRefreshModal();
            hideRefreshErrorModal();
            hideErrorDetailModal();
            closeFullscreenEmail();
        }

        // HTML 转义
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 键盘快捷键
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                hideAddGroupModal();
                hideAddAccountModal();
                hideEditAccountModal();
                hideExportModal();
                hideSettingsModal();
                hideRefreshModal();
                hideRefreshErrorModal();
                hideErrorDetailModal();
                closeFullscreenEmail();
            }
        });
        // ==================== 标签管理 ====================

        let allTags = [];

        // 显示标签管理模态框
        async function showTagManagementModal() {
            document.getElementById('tagManagementModal').classList.add('show');
            // Soft-load when allTags is warm; create/delete force-refresh.
            await loadTags(false);
        }

        // 隐藏标签管理模态框
        function hideTagManagementModal() {
            document.getElementById('tagManagementModal').classList.remove('show');
        }

        // Coalesce concurrent soft GET /api/tags (modal + batch select race).
        let tagsLoadPromise = null;
        // True when the in-flight tags GET was started with forceRefresh.
        let tagsLoadForce = false;

        // 加载标签列表
        function isBatchTagModalOpen() {
            const modal = document.getElementById('batchTagModal');
            return !!(modal && modal.classList.contains('show'));
        }

        function paintBatchTagSelectFromWarmTags() {
            // Only rewrite batch-tag select while that modal is open.
            // Soft loadTags from tag-management modal still warms allTags without
            // touching a closed batch modal.
            if (!isBatchTagModalOpen()) return;
            const select = document.getElementById('batchTagSelect');
            if (!select || !Array.isArray(allTags)) return;
            const previous = select.value || '';
            let html = `<option value="">${translateAppTextLocal('请选择标签...')}</option>`;
            allTags.forEach(tag => {
                html += `<option value="${tag.id}">${escapeHtml(tag.name)}</option>`;
            });
            select.innerHTML = html;
            if (previous && select.querySelector(`option[value="${previous}"]`)) {
                select.value = previous;
            }
        }

        // True when any loadTags consumer surface is active and should surface errors.
        // Soft/background tag loads off these surfaces still warm allTags silently.
        function isActiveTagLoadSurface() {
            if (typeof isTagManagementModalOpen === 'function' && isTagManagementModalOpen()) {
                return true;
            }
            if (typeof isBatchTagModalOpen === 'function' && isBatchTagModalOpen()) {
                return true;
            }
            // Mailbox tag filter chrome only while on mailbox page.
            return typeof currentPage !== 'undefined' && currentPage === 'mailbox';
        }

        async function loadTags(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            // Soft re-entry: always return warm allTags; paint only active surfaces.
            // renderTagList → tag management modal; updateTagFilter → mailbox page;
            // paintBatchTagSelectFromWarmTags → batch tag modal.
            if (!force && Array.isArray(allTags) && allTags.length > 0) {
                renderTagList();
                updateTagFilter();
                paintBatchTagSelectFromWarmTags();
                return allTags;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so create/delete always start a true network GET.
            if (tagsLoadPromise) {
                if (!force || tagsLoadForce) {
                    return tagsLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                tagsLoadPromise = null;
                tagsLoadForce = false;
            }

            tagsLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/tags');
                    const data = await response.json();
                    if (tagsLoadPromise !== request) {
                        return allTags;
                    }
                    if (data.success) {
                        // Always warm soft cache; surface painters no-op when inactive.
                        allTags = Array.isArray(data.tags) ? data.tags : [];
                        renderTagList();
                        updateTagFilter();  // Update Filter Dropdown
                        paintBatchTagSelectFromWarmTags();
                    }
                    return allTags;
                } catch (error) {
                    if (tagsLoadPromise !== request) {
                        return allTags;
                    }
                    // Soft loads that finish after all tag surfaces close must not toast.
                    if (isActiveTagLoadSurface()) {
                        showToast(translateAppTextLocal('加载标签失败'), 'error');
                    }
                    return allTags;
                }
            })();

            tagsLoadPromise = request;
            try {
                return await request;
            } finally {
                if (tagsLoadPromise === request) {
                    tagsLoadPromise = null;
                    tagsLoadForce = false;
                }
            }
        }

        // 更新标签筛选下拉框
        function isTagManagementModalOpen() {
            const modal = document.getElementById('tagManagementModal');
            return !!(modal && modal.classList.contains('show'));
        }

        // 渲染标签列表
        function renderTagList() {
            // Only paint when the management modal is open. Soft loadTags from batch-tag
            // select still warms allTags / updateTagFilter without rewriting closed modal DOM.
            if (!isTagManagementModalOpen()) {
                return;
            }
            const listEl = document.getElementById('tagList');
            if (!listEl) {
                return;
            }
            if (!allTags.length) {
                listEl.innerHTML = `<div style="text-align: center; color: #999; padding: 20px;">${translateAppTextLocal('暂无标签')}</div>`;
                return;
            }

            let html = '';
            allTags.forEach(tag => {
                html += `
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px; border-bottom: 1px solid #f0f0f0;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="tag-badge" style="background-color: ${tag.color};">${escapeHtml(tag.name)}</span>
                        </div>
                        <button class="btn btn-sm btn-danger" onclick="deleteTag(${tag.id})">${translateAppTextLocal('删除')}</button>
                    </div>
                `;
            });
            listEl.innerHTML = html;
        }

        // 创建标签
        async function createTag() {
            const nameInput = document.getElementById('newTagName');
            const colorInput = document.getElementById('newTagColor');
            const name = nameInput.value.trim();
            const color = colorInput.value;

            if (!name) {
                showToast(translateAppTextLocal('请输入标签名称'), 'error');
                return;
            }

            try {
                const response = await fetch('/api/tags', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, color })
                });
                const data = await response.json();

                if (data.success) {
                    nameInput.value = '';
                    showToast(translateAppTextLocal('标签创建成功'), 'success');
                    await loadTags(true);
                    // 刷新账号列表以重新加载标签（如果是在查看列表时添加标签，可能不需要立即刷新列表，但为了保持一致性可以刷新）
                    // 但通常添加标签不影响当前列表显示，除非是给账号打标
                } else {
                    handleApiError(data, '创建失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('创建标签失败'), 'error');
            }
        }

        // 删除标签
        async function deleteTag(id) {
            if (!confirm('确定要删除这个标签吗？')) return;

            try {
                const response = await fetch(`/api/tags/${id}`, { method: 'DELETE' });
                const data = await response.json();

                if (data.success) {
                    showToast(translateAppTextLocal('标签已删除'), 'success');
                    await loadTags(true);
                    // 刷新账号列表以更新标签显示
                    if (currentGroupId) {
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(data, '删除失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('删除标签失败'), 'error');
            }
        }

        // ==================== 批量操作 ====================

        // 全局选中的账号 ID 集合（跨分组保持）
        let selectedAccountIds = new Set();
        let batchMoveGroupContext = { scopedAccountIds: null };

        function getActiveAccountCheckboxes() {
            const selector = mailboxViewMode === 'compact'
                ? '#compactAccountList .account-select-checkbox'
                : '#accountList .account-select-checkbox';
            return Array.from(document.querySelectorAll(selector));
        }

        function handleAccountSelectionChange(accountId, checked) {
            if (checked) {
                selectedAccountIds.add(accountId);
            } else {
                selectedAccountIds.delete(accountId);
            }
            updateBatchActionBar();
            updateSelectAllCheckbox();
        }

        // 更新批量操作栏状态
        function showPersistentToast(id, message) {
            // 先清除同 id 的旧 toast
            dismissPersistentToast(id);
            showToast(message, 'info', null, true);
            // 给最后一个 toast 打上 id 标记
            const toasts = document.querySelectorAll('.toast');
            if (toasts.length > 0) {
                toasts[toasts.length - 1].dataset.persistentId = id;
            }
        }

        // 更新持久 Toast 内容
        function dismissPersistentToast(id) {
            const toast = document.querySelector(`.toast[data-persistent-id="${id}"]`);
            if (toast) {
                toast.remove();
            }
        }

        // 显示批量删除确认
        function showBatchDeleteConfirm() {
            if (selectedAccountIds.size === 0) {
                showToast(translateAppTextLocal('请选择要删除的账号'), 'error');
                return;
            }

            if (!confirm(`确定要删除选中的 ${selectedAccountIds.size} 个账号吗？此操作不可恢复！`)) {
                return;
            }

            batchDeleteAccounts();
        }

        // 批量删除账号
        async function batchDeleteAccounts() {
            const accountIds = Array.from(selectedAccountIds);

            // 确保使用最新的 CSRF token
            await initCSRFToken();

            try {
                const response = await fetch('/api/accounts/batch-delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_ids: accountIds })
                });

                const data = await response.json();
                if (data.success) {
                    showToast(pickApiMessage(data, data.message, 'Accounts deleted successfully'), 'success');
                    if (typeof window.invalidateAccountDetailCacheMany === 'function') {
                        window.invalidateAccountDetailCacheMany(accountIds);
                    }
                    // Resolve emails from warm inventory before dropping group cache.
                    if (typeof window.clearEmailListCacheForMailboxes === 'function') {
                        const idSet = new Set(accountIds.map(id => String(id)));
                        const deletedEmails = [];
                        for (const group of Object.values(accountsCache || {})) {
                            if (!Array.isArray(group)) continue;
                            for (const acc of group) {
                                if (acc && idSet.has(String(acc.id)) && acc.email) {
                                    deletedEmails.push(acc.email);
                                }
                            }
                        }
                        window.clearEmailListCacheForMailboxes(deletedEmails);
                    }
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }
                    // 清空选中状态
                    selectedAccountIds.clear();
                    // 刷新分组和邮箱列表
                    loadGroups(true);
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                    // 更新批量操作栏
                    updateBatchActionBar();
                } else {
                    handleApiError(data, '删除失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('删除失败'), 'error');
            }
        }

        // ── 批量拉取邮件（Issue #55: 标准模式 latest-only）──

        function resolveSelectedAccountsForBatchFetch() {
            const result = [];
            const idSet = selectedAccountIds;
            if (!idSet || idSet.size === 0) return result;

            const seen = new Set();
            const groupArrays = Object.values(accountsCache);
            for (const group of groupArrays) {
                if (!Array.isArray(group)) continue;
                for (const acc of group) {
                    if (acc && acc.id && idSet.has(acc.id) && !seen.has(acc.id)) {
                        seen.add(acc.id);
                        result.push({
                            id: acc.id,
                            email: acc.email,
                            account_type: acc.account_type,
                            provider: acc.provider,
                        });
                    }
                }
            }
            return result;
        }

        function showBatchFetchConfirm() {
            if (selectedAccountIds.size === 0) {
                showToast(translateAppTextLocal('请选择要批量拉取邮件的账号'), 'error');
                return;
            }

            const accounts = resolveSelectedAccountsForBatchFetch();
            if (accounts.length === 0) {
                showToast(translateAppTextLocal('请选择要批量拉取邮件的账号'), 'error');
                return;
            }

            if (!confirm(`${translateAppTextLocal('批量拉取邮件')}：${translateAppTextLocal('收件箱 + 垃圾箱')} (${accounts.length} ${translateAppTextLocal('个账号')})？`)) {
                return;
            }

            batchFetchSelectedEmails(accounts);
        }

        async function batchFetchSelectedEmails(accounts) {
            const toastId = 'batch-fetch-toast-' + Date.now();
            showPersistentToast(toastId, `${translateAppTextLocal('正在批量拉取邮件')}...`);

            const ids = accounts.map(a => a.id);

            try {
                const response = await fetch('/api/emails/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_ids: ids, folders: ['inbox', 'junkemail'], skip: 0, top: 10 })
                });
                const data = await response.json();

                dismissPersistentToast(toastId);

                if (!data.success) {
                    handleApiError(data, translateAppTextLocal('批量拉取失败'));
                    return;
                }

                // 回写缓存 + 刷新当前邮箱
                let successAccounts = 0;
                const failedAccounts = [];

                for (const result of (data.results || [])) {
                    if (result.success) {
                        successAccounts++;
                        const emailAddr = result.email || '';
                        const folders = result.folders || {};
                        for (const [folder, folderData] of Object.entries(folders)) {
                            if (folderData && folderData.success) {
                                if (folderData.account_summary && typeof syncAccountSummaryToAccountCache === 'function') {
                                    syncAccountSummaryToAccountCache(emailAddr, folderData.account_summary);
                                }
                                cacheBatchFetchedFolder(emailAddr, folder, folderData);
                                refreshCurrentMailboxIfNeeded(emailAddr, folder, folderData);
                            }
                        }
                    } else {
                        failedAccounts.push(result.email || result.account_id);
                    }
                }

                const failCount = failedAccounts.length;
                let msg = `${translateAppTextLocal('批量拉取完成')}：${translateAppTextLocal('成功')} ${successAccounts}，${translateAppTextLocal('失败')} ${failCount}`;
                if (failCount > 0) {
                    msg += `（${failedAccounts.join(', ')}）`;
                }
                showToast(msg, failCount > 0 ? 'warning' : 'success');
            } catch (error) {
                dismissPersistentToast(toastId);
                showToast(translateAppTextLocal('操作失败'), 'error');
            }
        }

        async function fetchLatestFoldersForAccount(acc) {
            const folders = ['inbox', 'junkemail'];
            let accountSuccess = false;
            for (const folder of folders) {
                try {
                    const url = `/api/emails/${encodeURIComponent(acc.email)}?folder=${folder}&skip=0&top=10`;
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    const data = await response.json();
                    if (data.success) {
                        if (data.account_summary && typeof syncAccountSummaryToAccountCache === 'function') {
                            syncAccountSummaryToAccountCache(acc.email, data.account_summary);
                        }
                        cacheBatchFetchedFolder(acc.email, folder, data);
                        refreshCurrentMailboxIfNeeded(acc.email, folder, data);
                        accountSuccess = true;
                    }
                } catch (_e) {}
            }

            return { success: accountSuccess };
        }

        function cacheBatchFetchedFolder(email, folder, data) {
            const cacheKey = `${email}_${folder}`;
            emailListCache[cacheKey] = {
                emails: (typeof sortEmailsByNewestFirst === 'function')
                    ? sortEmailsByNewestFirst(data.emails || [])
                    : (data.emails || []),
                has_more: data.has_more || false,
                skip: 0,
                method: data.method || 'Graph API',
            };
        }

        async function showBatchTagModal(type, options = {}) {
            batchActionType = type;
            batchTagContext = {
                scopedAccountIds: Array.isArray(options.scopedAccountIds) && options.scopedAccountIds.length > 0
                    ? [...options.scopedAccountIds]
                    : null
            };
            document.getElementById('batchTagTitle').textContent = translateAppTextLocal(type === 'add' ? '批量添加标签' : '批量移除标签');
            document.getElementById('batchTagModal').classList.add('show');

            // 加载标签选项
            await loadTagsForSelect();
        }

        function hideBatchTagModal() {
            document.getElementById('batchTagModal').classList.remove('show');
            batchTagContext = { scopedAccountIds: null };
        }

        // 加载标签到下拉框
        async function loadTagsForSelect() {
            const select = document.getElementById('batchTagSelect');
            if (!select) return;

            try {
                // Soft warm path: paint immediately without "加载中..." flash.
                if (Array.isArray(allTags) && allTags.length > 0) {
                    paintBatchTagSelectFromWarmTags();
                    return;
                }
                // Loading/error chrome only while batch-tag modal is open.
                if (isBatchTagModalOpen()) {
                    select.innerHTML = `<option value="">${translateAppTextLocal('加载中...')}</option>`;
                }
                // Prefer shared soft loadTags; avoid a second raw GET.
                await loadTags(false);
                // loadTags success path also paints when modal open; ensure select filled after cold load.
                if (isBatchTagModalOpen() && !(select.options.length > 1)) {
                    paintBatchTagSelectFromWarmTags();
                }
            } catch (error) {
                if (isBatchTagModalOpen()) {
                    select.innerHTML = `<option value="">${translateAppTextLocal('加载失败')}</option>`;
                }
            }
        }

        // 确认批量打标
        async function confirmBatchTag() {
            const tagId = document.getElementById('batchTagSelect').value;
            if (!tagId) {
                showToast(translateAppTextLocal('请选择标签'), 'error');
                return;
            }

            const accountIds = batchTagContext.scopedAccountIds ? [...batchTagContext.scopedAccountIds] : Array.from(selectedAccountIds);

            if (accountIds.length === 0) return;

            try {
                const hasScopedAccountIds = Boolean(batchTagContext.scopedAccountIds);
                const response = await fetch('/api/accounts/tags', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account_ids: accountIds,
                        tag_id: parseInt(tagId),
                        action: batchActionType
                    })
                });

                const data = await response.json();
                if (data.success) {
                    showToast(pickApiMessage(data, data.message, 'Tag update completed'), 'success');
                    if (typeof window.invalidateAccountDetailCacheMany === 'function') {
                        window.invalidateAccountDetailCacheMany(accountIds);
                    }
                    hideBatchTagModal();
                    if (!hasScopedAccountIds) {
                        selectedAccountIds.clear();
                    }
                    // 刷新列表
                    loadGroups(true);
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                    updateBatchActionBar();
                } else {
                    handleApiError(data, '操作失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('请求失败'), 'error');
            }
        }

        // ==================== 批量移动分组 ====================

        // 显示批量移动分组模态框
        async function showBatchMoveGroupModal(options = {}) {
            batchMoveGroupContext = {
                scopedAccountIds: Array.isArray(options.scopedAccountIds) && options.scopedAccountIds.length > 0
                    ? [...options.scopedAccountIds]
                    : null
            };
            document.getElementById('batchMoveGroupModal').classList.add('show');
            await loadGroupsForBatchMove();
        }

        function hideBatchMoveGroupModal() {
            document.getElementById('batchMoveGroupModal').classList.remove('show');
            batchMoveGroupContext = { scopedAccountIds: null };
        }

        function isBatchMoveGroupModalOpen() {
            const modal = document.getElementById('batchMoveGroupModal');
            return !!(modal && modal.classList.contains('show'));
        }

        // Paint batch-move group select from warm groups (no network).
        function paintBatchMoveGroupSelectFromWarmGroups() {
            // Soft loadGroups may finish after the modal is closed — do not rewrite select.
            if (!isBatchMoveGroupModalOpen()) return;
            const select = document.getElementById('batchMoveGroupSelect');
            if (!select) return;
            const previous = select.value || '';
            const source = Array.isArray(groups) ? groups : [];
            let html = `<option value="">${translateAppTextLocal('请选择分组...')}</option>`;
            source.filter(g => !g.is_system).forEach(group => {
                const name = (typeof formatGroupDisplayName === 'function')
                    ? formatGroupDisplayName(group.name)
                    : translateAppTextLocal(String(group.name || '').trim());
                html += `<option value="${group.id}">${escapeHtml(name)}</option>`;
            });
            select.innerHTML = html;
            if (previous && select.querySelector(`option[value="${previous}"]`)) {
                select.value = previous;
            }
        }

        // Soft re-paint open batch-move modal on language change (no network).
        function softPaintBatchMoveGroupSelectIfOpen() {
            if (!isBatchMoveGroupModalOpen()) return;
            if (!(Array.isArray(groups) && groups.length > 0)) return;
            paintBatchMoveGroupSelectFromWarmGroups();
        }

        // 加载分组到下拉框
        async function loadGroupsForBatchMove() {
            const select = document.getElementById('batchMoveGroupSelect');
            if (!select) return;

            try {
                // Soft warm path: paint immediately without "加载中..." flash.
                if (Array.isArray(groups) && groups.length > 0) {
                    paintBatchMoveGroupSelectFromWarmGroups();
                    return;
                }
                if (isBatchMoveGroupModalOpen()) {
                    select.innerHTML = `<option value="">${translateAppTextLocal('加载中...')}</option>`;
                }
                // Prefer shared soft loadGroups; avoid a second raw GET /api/groups.
                if (typeof loadGroups === 'function') {
                    await loadGroups(false);
                }
                paintBatchMoveGroupSelectFromWarmGroups();
            } catch (error) {
                if (isBatchMoveGroupModalOpen()) {
                    select.innerHTML = `<option value="">${translateAppTextLocal('加载失败')}</option>`;
                }
            }
        }

        // 确认批量移动分组
        async function confirmBatchMoveGroup() {
            const groupId = document.getElementById('batchMoveGroupSelect').value;
            if (!groupId) {
                showToast(translateAppTextLocal('请选择目标分组'), 'error');
                return;
            }

            const accountIds = batchMoveGroupContext.scopedAccountIds
                ? [...batchMoveGroupContext.scopedAccountIds]
                : Array.from(selectedAccountIds);

            if (accountIds.length === 0) return;

            try {
                const hasScopedAccountIds = Boolean(batchMoveGroupContext.scopedAccountIds);
                const response = await fetch('/api/accounts/batch-update-group', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account_ids: accountIds,
                        group_id: parseInt(groupId)
                    })
                });

                const data = await response.json();
                if (data.success) {
                    showToast(pickApiMessage(data, data.message, 'Accounts moved successfully'), 'success');
                    if (typeof window.invalidateAccountDetailCacheMany === 'function') {
                        window.invalidateAccountDetailCacheMany(accountIds);
                    }
                    hideBatchMoveGroupModal();
                    if (!hasScopedAccountIds) {
                        selectedAccountIds.clear();
                    }
                    // 刷新分组列表
                    loadGroups(true);
                    // 刷新当前分组的邮箱列表
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                    updateBatchActionBar();
                } else {
                    handleApiError(data, '操作失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('请求失败'), 'error');
            }
        }

        // ==================== 版本更新检测 ====================

        function getCSRFToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return meta ? meta.getAttribute('content') : '';
        }

        // Soft-load: session-warm version-check payload; coalesce concurrent checks.
        let versionCheckCache = null;
        let versionCheckLoadPromise = null;
        // True when the in-flight version-check GET was started with forceRefresh.
        let versionCheckLoadForce = false;

