// split from accounts.js → actions.js
        function selectAccount(email) {
            currentAccount = email;
            isTempEmailGroup = false;
            currentFolder = 'inbox';
            currentMethod = 'graph';

            document.getElementById('currentAccountBar').style.display = '';
            document.getElementById('currentAccountEmail').textContent = email;

            // Update active state on account cards
            document.querySelectorAll('.account-card').forEach(item => {
                item.classList.remove('active');
                const emailEl = item.querySelector('.account-email');
                if (emailEl && emailEl.textContent.includes(email)) {
                    item.classList.add('active');
                }
            });

            // 窄屏下：回到列表态（避免上一次详情态残留）
            if (typeof setMailboxDetailFocus === 'function') {
                setMailboxDetailFocus(false);
            }

            const folderTabs = document.getElementById('folderTabs');
            if (folderTabs) {
                folderTabs.style.display = 'flex';
                document.querySelectorAll('.email-tab').forEach(tab => {
                    tab.classList.toggle('active', tab.dataset.folder === 'inbox');
                });
            }

            const cacheKey = `${email}_inbox`;

            if (emailListCache[cacheKey]) {
                const cache = emailListCache[cacheKey];
                currentEmails = (typeof sortEmailsByNewestFirst === 'function')
                    ? sortEmailsByNewestFirst(cache.emails || [])
                    : (cache.emails || []);
                hasMoreEmails = cache.has_more;
                currentSkip = cache.skip;
                currentMethod = cache.method || 'graph';

                cache.emails = currentEmails;

                const methodTag = document.getElementById('methodTag');
                methodTag.textContent = currentMethod;
                methodTag.style.display = 'inline';
                document.getElementById('emailCount').textContent = `(${currentEmails.length})`;

                renderEmailList(currentEmails);
            } else {
                document.getElementById('emailList').innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon" aria-hidden="true"></span>
                        <p class="ui-empty-title">${translateAppTextLocal('尚未加载邮件')}</p>
                        <p class="ui-empty-desc">${translateAppTextLocal('点击右上角获取邮件开始拉取')}</p>
                    </div>
                `;
                document.getElementById('emailCount').textContent = '';
                document.getElementById('methodTag').style.display = 'none';
                currentEmails = [];
            }

            document.getElementById('emailDetail').innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon" aria-hidden="true"></span>
                    <p class="ui-empty-title">${translateAppTextLocal('邮件详情')}</p>
                    <p class="ui-empty-desc">${translateAppTextLocal('选择一封邮件以查看正文与验证码')}</p>
                </div>
            `;
            document.getElementById('emailDetailToolbar').style.display = 'none';

            // 自动加载邮件列表（优先使用缓存，无缓存时自动 fetch）
            if (typeof loadEmails === 'function') {
                loadEmails(email);
            }

            // 标准模式：选中账号后自动启动轮询（如果轮询已启用且该账号尚未在轮询中）
            var view = typeof mailboxViewMode !== 'undefined' ? mailboxViewMode : 'standard';
            if (view !== 'compact' && typeof pollEnabled !== 'undefined' && pollEnabled && typeof startPoll === 'function') {
                // 如果该账号已在轮询中则跳过，避免重复启动和多余 Toast
                var alreadyPolling = typeof pollMap !== 'undefined' && pollMap.has(email);
                if (!alreadyPolling) {
                    startPoll(email);
                }
            }
        }

        // Provider 下拉缓存（来自 /api/providers 的 account catalog / providers 列表）
        let providersLoaded = false;
        let providerOptions = [];
        // Coalesce concurrent cold loadProviders (import modal open race).
        let providersLoadPromise = null;
        // True when the in-flight providers load was started with forceRefresh.
        let providersLoadForce = false;
        // Soft-load edit-modal detail from prior GET /api/accounts/<id> only
        // (list payload truncates client_id — never paint from accountsCache list rows).
        const accountDetailCache = new Map();
        const accountDetailLoadPromises = Object.create(null);
        // True when the in-flight detail GET for an account was started with forceRefresh.
        const accountDetailLoadForce = Object.create(null);
        // Active open request for edit-account modal. Cleared on hide so a late
        // soft/network response cannot re-add .show after the user cancelled.
        let editAccountPaintTargetId = null;

        function applyEditAccountForm(acc) {
            if (!acc || typeof acc !== 'object') return false;
            const isImap = (acc.account_type || 'outlook') === 'imap';
            const clientIdInput = document.getElementById('editClientId');
            const refreshTokenInput = document.getElementById('editRefreshToken');
            if (!clientIdInput || !refreshTokenInput) return false;

            document.getElementById('editAccountId').value = acc.id;
            document.getElementById('editAccountType').value = acc.account_type || 'outlook';
            const emailInput = document.getElementById('editEmail');
            if (emailInput) {
                emailInput.value = acc.email || '';
                emailInput.dataset.originalValue = acc.email || '';
            }
            document.getElementById('editPassword').value = acc.password || '';
            clientIdInput.value = acc.client_id || '';
            clientIdInput.dataset.originalValue = acc.client_id || '';
            refreshTokenInput.value = acc.refresh_token || '';
            document.getElementById('editGroupSelect').value = acc.group_id || 1;
            document.getElementById('editRemark').value = acc.remark || '';
            document.getElementById('editStatus').value = acc.status || 'active';

            // IMAP 账号：隐藏 Client ID / Refresh Token，调整密码标签
            const clientIdGroup = document.getElementById('editClientIdGroup');
            const refreshTokenGroup = document.getElementById('editRefreshTokenGroup');
            const passwordLabel = document.getElementById('editPasswordLabel');

            if (isImap) {
                if (clientIdGroup) clientIdGroup.style.display = 'none';
                if (refreshTokenGroup) refreshTokenGroup.style.display = 'none';
                if (passwordLabel) passwordLabel.textContent = translateAppTextLocal('授权码 / 应用密码');
                document.getElementById('editPassword').placeholder = translateAppTextLocal('留空则不修改');
                refreshTokenInput.placeholder = '';
            } else {
                if (clientIdGroup) clientIdGroup.style.display = '';
                if (refreshTokenGroup) refreshTokenGroup.style.display = '';
                if (passwordLabel) passwordLabel.textContent = translateAppTextLocal('密码');
                document.getElementById('editPassword').placeholder = translateAppTextLocal('可选，留空则不修改');
                refreshTokenInput.placeholder = translateAppTextLocal('留空则不修改');
            }

            document.getElementById('editAccountModal').classList.add('show');
            return true;
        }

        function isAddAccountModalOpen() {
            const modal = document.getElementById('addAccountModal');
            return !!(modal && modal.classList.contains('show'));
        }

        // 加载邮箱 providers（用于导入下拉）
        function showAddAccountModal() {
            document.getElementById('accountInput').value = '';
            const addToPoolCheckbox = document.getElementById('addToPoolCheckbox');
            if (addToPoolCheckbox) {
                addToPoolCheckbox.checked = false;
            }
            // 设置默认分组为当前选中的分组
            if (currentGroupId) {
                document.getElementById('importGroupSelect').value = currentGroupId;
            }
            // 加载 providers 并初始化默认状态
            loadProviders().finally(() => {
                const sel = document.getElementById('accountProvider');
                if (sel) {
                    // Catalog may hang/fail; never leave the loading placeholder as the only option.
                    ensureImportProviderSelectOptions(sel);
                    const preferred = ['auto', 'outlook']
                        .find(item => sel.querySelector(`option[value="${item}"]`));
                    if (preferred) sel.value = preferred;
                    // Keep select.value and onProviderChange() in sync (empty value must not imply auto UI).
                    onProviderChange(sel.value || preferred || 'auto');
                } else {
                    onProviderChange('auto');
                }

                const hostEl = document.getElementById('imapHost');
                const portEl = document.getElementById('imapPort');
                if (hostEl) hostEl.value = '';
                if (portEl) portEl.value = '993';

                // 重置 auto 模式的字段
                const fbHostEl = document.getElementById('fallbackImapHost');
                const fbPortEl = document.getElementById('fallbackImapPort');
                if (fbHostEl) fbHostEl.value = '';
                if (fbPortEl) fbPortEl.value = '993';
                const skipRadio = document.querySelector('input[name="duplicateStrategy"][value="skip"]');
                if (skipRadio) skipRadio.checked = true;
            });
            document.getElementById('addAccountModal').classList.add('show');
        }

        // 隐藏添加账号模态框
        function hideAddAccountModal() {
            document.getElementById('addAccountModal').classList.remove('show');
        }

        async function addAccount() {
            const input = document.getElementById('accountInput').value.trim();
            const importGroupSelect = document.getElementById('importGroupSelect');
            const providerEl = document.getElementById('accountProvider');
            // Recover if catalog paint never replaced the loading placeholder.
            ensureImportProviderSelectOptions(providerEl);

            let provider = providerEl ? String(providerEl.value || '').trim() : '';
            // UI may already be in auto-group mode while select is still empty after failed paint.
            if (!provider && importGroupSelect && importGroupSelect.disabled) {
                provider = 'auto';
                if (providerEl && providerEl.querySelector('option[value="auto"]')) {
                    providerEl.value = 'auto';
                }
            }
            if (!provider) provider = 'outlook';

            const rawGroupValue = importGroupSelect ? String(importGroupSelect.value || '').trim() : '';
            const parsedGroupId = rawGroupValue === '' ? NaN : parseInt(rawGroupValue, 10);
            const groupId = Number.isFinite(parsedGroupId) ? parsedGroupId : NaN;
            const addToPool = Boolean(document.getElementById('addToPoolCheckbox')?.checked);
            const importedGroupId = resolveImportGroupId(groupId);

            if (!input) {
                showToast(translateAppTextLocal('请输入账号信息'), 'error');
                return;
            }

            try {
                const payload = { account_string: input, add_to_pool: addToPool };

                if (provider === 'auto') {
                    payload.provider = 'auto';
                    payload.group_id = null;
                    const strategyEl = document.querySelector('input[name="duplicateStrategy"]:checked');
                    payload.duplicate_strategy = strategyEl ? strategyEl.value : 'skip';
                    const fbHost = (document.getElementById('fallbackImapHost')?.value || '').trim();
                    const fbPort = parseInt(document.getElementById('fallbackImapPort')?.value || '993', 10);
                    if (fbHost) {
                        payload.imap_host = fbHost;
                        payload.imap_port = fbPort || 993;
                    }
                } else {
                    // outlook / explicit IMAP providers require a real group id
                    if (!importedGroupId) {
                        showToast(translateAppTextLocal('请选择有效分组，或切换到智能识别自动分组'), 'error');
                        return;
                    }
                    payload.group_id = importedGroupId;
                    if (provider && provider !== 'outlook') {
                        payload.provider = provider;
                    }
                    if (provider === 'custom') {
                        const host = (document.getElementById('imapHost')?.value || '').trim();
                        const portRaw = (document.getElementById('imapPort')?.value || '').trim();
                        const port = parseInt(portRaw || '993', 10) || 993;

                        if (!host) {
                            // 允许每行内嵌 host/port：email----授权码----imap_host----imap_port（或导出格式 5 段）
                            const lines = input.split('\n').map(l => (l || '').trim()).filter(l => l && !l.startsWith('#'));
                            const hasInlineHost = lines.some(l => (l.split('----').length >= 4));
                            if (!hasInlineHost) {
                                showToast(translateAppTextLocal('请填写 IMAP 服务器地址（或在文本中每行包含 host/port）'), 'error');
                                return;
                            }
                        } else {
                            payload.imap_host = host;
                            payload.imap_port = port;
                        }
                    }
                }

                const response = await fetch('/api/accounts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (data.success) {
                    // Auto 模式增强结果展示
                    if (data.summary && data.summary.mode === 'auto') {
                        let msg = pickApiMessage(data, data.message, data.message_en || 'Import completed');
                        const s = data.summary;
                        if (s.by_provider && Object.keys(s.by_provider).length > 0) {
                            msg += `\n\n--- ${translateAppTextLocal('按类型统计')} ---`;
                            for (const [prov, stats] of Object.entries(s.by_provider)) {
                                const name = getImportResultProviderLabel(prov);
                                msg += `\n${translateAppTextLocal(name)}: ${translateAppTextLocal('成功')} ${stats.imported || 0}`;
                                if (stats.skipped) msg += `, ${translateAppTextLocal('跳过')} ${stats.skipped}`;
                                if (stats.failed) msg += `, ${translateAppTextLocal('失败')} ${stats.failed}`;
                            }
                        }
                        if (s.groups_created && s.groups_created.length > 0) {
                            msg += `\n\n✨ ${translateAppTextLocal('自动创建分组')}：${s.groups_created.join('、')}`;
                        }
                        showToast(msg, 'success');
                    } else {
                        showToast(pickApiMessage(data, data.message, 'Import completed'), 'success');
                    }
                    hideAddAccountModal();

                    // 清除缓存并刷新分组列表（可能有新分组）
                    if (typeof accountsCache !== 'undefined') {
                        if (provider === 'auto') {
                            // auto 模式可能影响多个分组，清除所有缓存
                            invalidateAccountsCache();
                        } else if (importedGroupId) {
                            invalidateAccountsCache(importedGroupId);
                        }
                    }
                    // Import may overwrite credentials for existing addresses; drop soft mail caches.
                    if (typeof window.clearEmailListCacheForMailboxes === 'function') {
                        window.clearEmailListCacheForMailboxes(extractImportCandidateEmails(input));
                    }
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }

                    await refreshMailboxAfterImport(provider, importedGroupId);
                } else if (data.summary || Array.isArray(data.errors)) {
                    showToast(buildImportFailureToastMessage(data), 'error', data.error || data);
                } else {
                    handleApiError(data, '导入邮箱失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('添加失败'), 'error');
            }
        }

        // 显示编辑账号模态框（soft-load prior detail GET; never list-cache — client_id truncated）
        async function showEditAccountModal(accountId, forceRefresh = false) {
            const key = String(accountId || '').trim();
            if (!key) return false;
            const force = Boolean(forceRefresh);

            // Mark this account as the intended open target before any soft/network paint.
            editAccountPaintTargetId = key;

            // Soft re-open: same account detail already warm from a prior detail GET.
            if (!force && accountDetailCache.has(key)) {
                if (shouldPaintEditAccountForm(key)
                    && applyEditAccountForm(accountDetailCache.get(key))) {
                    return true;
                }
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so re-open after mutation starts a true network GET.
            if (accountDetailLoadPromises[key]) {
                if (!force || accountDetailLoadForce[key]) {
                    return accountDetailLoadPromises[key];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                delete accountDetailLoadPromises[key];
                delete accountDetailLoadForce[key];
            }

            accountDetailLoadForce[key] = force;
            const request = (async () => {
                try {
                    const response = await fetch(`/api/accounts/${encodeURIComponent(key)}`);
                    const data = await response.json();

                    if (accountDetailLoadPromises[key] !== request) {
                        return accountDetailCache.has(key);
                    }
                    if (data.success && data.account) {
                        // Always warm detail cache; paint only while open target still matches.
                        accountDetailCache.set(key, data.account);
                        if (shouldPaintEditAccountForm(key)) {
                            applyEditAccountForm(data.account);
                        }
                        return true;
                    }
                    if (shouldPaintEditAccountForm(key)) {
                        showToast(translateAppTextLocal('加载账号信息失败'), 'error');
                    }
                    return false;
                } catch (error) {
                    if (accountDetailLoadPromises[key] !== request) {
                        return accountDetailCache.has(key);
                    }
                    if (shouldPaintEditAccountForm(key)) {
                        showToast(translateAppTextLocal('加载账号信息失败'), 'error');
                    }
                    return false;
                } finally {
                    if (accountDetailLoadPromises[key] === request) {
                        delete accountDetailLoadPromises[key];
                        delete accountDetailLoadForce[key];
                    }
                }
            })();

            accountDetailLoadPromises[key] = request;
            return request;
        }

        // 隐藏编辑账号模态框
        function hideEditAccountModal() {
            editAccountPaintTargetId = null;
            document.getElementById('editAccountModal').classList.remove('show');
        }

        function focusEditRemarkField() {
            const remarkField = document.getElementById('editRemark');
            if (!remarkField) {
                return;
            }
            remarkField.focus();
            remarkField.setSelectionRange(remarkField.value.length, remarkField.value.length);
        }

        async function showEditRemarkOnly(accountId) {
            await showEditAccountModal(accountId);
            focusEditRemarkField();
        }

        async function deleteCurrentAccount() {
            const accountId = document.getElementById('editAccountId').value;
            const email = document.getElementById('editEmail').value;
            const groupId = parseInt(document.getElementById('editGroupSelect').value);

            if (!confirm(`确定要删除账号 ${email} 吗？`)) {
                return;
            }

            try {
                const response = await fetch(`/api/accounts/${accountId}`, { method: 'DELETE' });
                const data = await response.json();

                if (data.success) {
                    showToast(pickApiMessage(data, '删除成功', 'Deleted successfully'), 'success');
                    invalidateAccountDetailCache(accountId);
                    hideEditAccountModal();

                    // 清除缓存
                    invalidateAccountsCache(groupId);
                    // Drop soft mail list/detail for the deleted mailbox.
                    if (typeof window.clearEmailListCacheForMailbox === 'function') {
                        window.clearEmailListCacheForMailbox(email);
                    }
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }

                    if (currentAccount === email) {
                        currentAccount = null;
                        document.getElementById('currentAccountBar').style.display = 'none';
                        document.getElementById('emailList').innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📬</span><p>${translateAppTextLocal('请从左侧选择一个邮箱账号')}</p>
                            </div>
                        `;
                        document.getElementById('emailDetail').innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📄</span><p>${translateAppTextLocal('选择一封邮件查看详情')}</p>
                            </div>
                        `;
                    }

                    // 刷新分组列表
                    loadGroups(true);

                    // 刷新当前分组的邮箱列表
                    if (currentGroupId) {
                        loadAccountsByGroup(currentGroupId, true);
                    }
                }
            } catch (error) {
                showToast(translateAppTextLocal('删除失败'), 'error');
            }
        }

        // 切换账号状态（启用/停用）
        async function deleteAccount(accountId, email) {
            if (!confirm(`确定要删除账号 ${email} 吗？`)) {
                return;
            }

            try {
                const response = await fetch(`/api/accounts/${accountId}`, { method: 'DELETE' });
                const data = await response.json();

                if (data.success) {
                    showToast(pickApiMessage(data, '删除成功', 'Deleted successfully'), 'success');
                    invalidateAccountDetailCache(accountId);

                    // 清除当前分组的缓存
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                    }
                    // Drop soft mail list/detail for the deleted mailbox.
                    if (typeof window.clearEmailListCacheForMailbox === 'function') {
                        window.clearEmailListCacheForMailbox(email);
                    }
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }

                    if (currentAccount === email) {
                        currentAccount = null;
                        document.getElementById('currentAccountBar').style.display = 'none';
                        document.getElementById('emailList').innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📬</span><p>${translateAppTextLocal('请从左侧选择一个邮箱账号')}</p>
                            </div>
                        `;
                        document.getElementById('emailDetail').innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📄</span><p>${translateAppTextLocal('选择一封邮件查看详情')}</p>
                            </div>
                        `;
                    }

                    // 刷新分组列表
                    loadGroups(true);

                    // 刷新当前分组的邮箱列表
                    if (currentGroupId) {
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(data, '删除账号失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('删除失败'), 'error');
            }
        }

        // 批量切换账号通知参与开关（Issue #64）
        async function batchNotificationToggle(enabled) {
            if (selectedAccountIds.size === 0) {
                showToast(translateAppTextLocal('请选择要批量操作通知的账号'), 'error');
                return;
            }
            const ids = Array.from(selectedAccountIds);
            try {
                const response = await fetch('/api/accounts/batch-notification-toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_ids: ids, enabled })
                });
                const data = await response.json();
                if (data.success) {
                    showToast(
                        data.message || (enabled ? translateAppTextLocal('批量开启通知完成') : translateAppTextLocal('批量关闭通知完成')),
                        'success'
                    );
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(data, translateAppTextLocal('批量操作失败'));
                }
            } catch (error) {
                showToast(translateAppTextLocal('操作失败'), 'error');
            }
        }

        // 切换账号通知参与开关（沿用旧 Telegram 接口）
        function toggleSelectAllGroups() {
            const selectAll = document.getElementById('selectAllGroups').checked;
            document.querySelectorAll('.export-group-checkbox').forEach(cb => {
                cb.checked = selectAll;
            });
        }

        // 存储待导出的分组ID
        let pendingExportGroupIds = [];

        // 导出选中的分组
        async function exportSelectedGroups() {
            const checkboxes = document.querySelectorAll('.export-group-checkbox:checked');
            const groupIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

            if (groupIds.length === 0) {
                showToast(translateAppTextLocal('请选择要导出的分组'), 'error');
                return;
            }

            // 保存待导出的分组ID
            pendingExportGroupIds = groupIds;

            // 显示密码确认对话框
            hideExportModal();
            showExportVerifyModal();
        }

        // 显示导出密码确认对话框
        async function confirmExportVerify() {
            const password = document.getElementById('exportVerifyPassword').value;

            if (!password) {
                showToast(translateAppTextLocal('请输入密码'), 'error');
                return;
            }

            try {
                // 获取验证token
                const verifyResponse = await fetch('/api/export/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password })
                });

                const verifyData = await verifyResponse.json();

                if (!verifyData.success) {
                    handleApiError(verifyData, '密码错误');
                    if (verifyData.need_verify) {
                        document.getElementById('exportVerifyPassword').focus();
                    }
                    return;
                }

                const verifyToken = verifyData.verify_token;

                // 执行导出（使用请求头传递 token，避免 URL/日志泄露）
                const response = await fetch('/api/accounts/export-selected', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Export-Token': verifyToken
                    },
                    body: JSON.stringify({
                        group_ids: pendingExportGroupIds
                    })
                });

                if (response.ok) {
                    // 获取文件名
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'accounts.txt';
                    if (contentDisposition) {
                        const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?([^;\n]+)/i);
                        if (match) {
                            filename = decodeURIComponent(match[1]);
                        }
                    }

                    // 下载文件
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);

                    showToast(translateAppTextLocal('导出成功'), 'success');
                    hideExportVerifyModal();
                } else {
                    const data = await response.json();
                    handleApiError(data, '导出失败');
                    if (data.need_verify) {
                        document.getElementById('exportVerifyPassword').focus();
                    }
                }
            } catch (error) {
                showToast(translateAppTextLocal('导出失败'), 'error');
            }
        }

