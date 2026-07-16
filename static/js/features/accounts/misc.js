// split from accounts.js → misc.js
        function normalizeImportAccountProviderOption(item) {
            if (!item || typeof item !== 'object') return null;
            const key = String(item.key || item.provider || '').trim();
            if (!key) return null;
            return {
                key,
                label: String(item.label || key).trim() || key,
                note: String(item.note || '').trim(),
                account_type: String(item.account_type || '').trim().toLowerCase(),
            };
        }

        function getDefaultImportAccountProviderOptions() {
            return [
                {
                    key: 'auto',
                    label: '智能识别（混合导入）',
                    note: '自动识别每行的账号类型，支持混合文件一键导入',
                    account_type: 'mixed',
                },
                {
                    key: 'outlook',
                    label: 'Outlook',
                    note: '',
                    account_type: 'outlook',
                },
            ];
        }

        function ensureAutoImportProviderOption(options) {
            const list = Array.isArray(options) ? options.filter(Boolean) : [];
            if (!list.some(item => String(item.key || '').trim().toLowerCase() === 'auto')) {
                list.unshift(getDefaultImportAccountProviderOptions()[0]);
            }
            return list;
        }

        /** Paint usable provider options if catalog never arrived (avoid stuck "加载 Provider 目录…"). */
        function ensureImportProviderSelectOptions(selectEl) {
            const select = selectEl || document.getElementById('accountProvider');
            if (!select) return false;
            if (select.querySelector('option[value="auto"]') || select.querySelector('option[value="outlook"]')) {
                return true;
            }
            const fallback = getDefaultImportAccountProviderOptions();
            providerOptions = fallback.slice();
            providersLoaded = true;
            if (typeof isAddAccountModalOpen === 'function' ? isAddAccountModalOpen() : true) {
                select.innerHTML = fallback.map(p => (
                    `<option value="${escapeHtml(p.key)}">${escapeHtml(translateAppTextLocal(p.label || p.key))}</option>`
                )).join('');
                if (typeof updateAccountProviderNote === 'function') {
                    updateAccountProviderNote(select.value);
                }
            }
            return true;
        }

        function findImportAccountProviderOption(providerName) {
            const key = String(providerName || '').trim().toLowerCase();
            return providerOptions.find(item => String(item.key || '').trim().toLowerCase() === key) || null;
        }

        function updateAccountProviderNote(providerName) {
            const noteEl = document.getElementById('accountProviderNote');
            if (!noteEl) return;
            const option = findImportAccountProviderOption(providerName);
            if (option && option.note) {
                noteEl.textContent = translateAppTextLocal(option.note);
                return;
            }
            noteEl.textContent = translateAppTextLocal('提示：按所选 Provider 使用授权码/应用专用密码或 OAuth 凭据（非网页登录密码）');
        }

        function getImportResultProviderLabel(providerKey) {
            const key = String(providerKey || '').trim();
            if (!key) return '';

            if (typeof resolveMailboxProviderLabel === 'function') {
                return resolveMailboxProviderLabel(key, {
                    softLoad: false,
                    fallbackResolver: (provider) => {
                        const importHit = findImportAccountProviderOption(provider);
                        return importHit && importHit.label ? importHit.label : '';
                    },
                }) || key;
            }

            // Fallback if shared helper is unavailable (script load order/tests).
            const importHit = findImportAccountProviderOption(key);
            if (importHit && importHit.label) return importHit.label;
            return key;
        }

        function buildImportFailureToastMessage(data) {
            const baseMessage = pickApiMessage(data, data.message || '导入失败', data.message_en || 'Import failed');
            const summary = data && typeof data.summary === 'object' ? data.summary : null;
            const errors = Array.isArray(data && data.errors) ? data.errors : [];
            const lines = [baseMessage];

            if (summary) {
                const imported = Number(summary.imported || 0);
                const failed = Number(summary.failed || 0);
                const skipped = Number(summary.skipped || 0);
                lines.push(
                    translateAppTextLocal(
                        '成功 ' + imported + '，失败 ' + failed + '，跳过 ' + skipped
                    )
                );
            }

            if (errors.length > 0) {
                const firstError = errors[0] || {};
                const row = firstError.line_number || firstError.line || firstError.index;
                // Prefer bilingual API fields via pickApiMessage when available.
                const detail = (typeof pickApiMessage === 'function')
                    ? pickApiMessage(firstError, firstError.message || firstError.error || '', firstError.message_en || firstError.message || firstError.error || '')
                    : (firstError.message || firstError.message_en || firstError.error || '');
                if (detail) {
                    lines.push(
                        row
                            ? translateAppTextLocal('第 ' + row + ' 行：' + detail)
                            : detail
                    );
                }
            }

            return lines.filter(Boolean).join('\n');
        }

        // Add-account / import modal owns #accountProvider.
        function onProviderChange(provider) {
            const p = (provider || 'outlook').toLowerCase();
            const input = document.getElementById('accountInput');
            const hint = document.getElementById('accountFormatHint');
            const customFields = document.getElementById('customImapFields');
            const duplicateGroup = document.getElementById('duplicateStrategyGroup');
            const fallbackGroup = document.getElementById('fallbackImapGroup');
            const importGroupSelect = document.getElementById('importGroupSelect');

            if (!input || !hint || !customFields) return;

            // 重置 auto 模式特有的 UI
            if (duplicateGroup) duplicateGroup.style.display = 'none';
            if (fallbackGroup) fallbackGroup.style.display = 'none';
            if (importGroupSelect) {
                importGroupSelect.disabled = false;
            }

            if (p === 'auto') {
                customFields.style.display = 'none';
                if (duplicateGroup) duplicateGroup.style.display = '';
                if (fallbackGroup) fallbackGroup.style.display = '';
                input.placeholder = translateAppTextLocal('支持混合格式，每行一个账号...\nOutlook: 邮箱----密码----client_id----refresh_token\nIMAP: 邮箱----授权码----provider\n或: 邮箱----密码（自动识别类型）\n临时邮箱: 仅邮箱地址');
                hint.textContent = translateAppTextLocal('智能识别模式：自动按每行格式和邮箱域名判断类型，自动分组');
                if (typeof getTokenBtn !== 'undefined' && getTokenBtn) getTokenBtn.style.display = 'none';
                if (importGroupSelect) {
                    importGroupSelect.disabled = true;
                    const savedHTML = importGroupSelect.innerHTML;
                    importGroupSelect.dataset.savedOptions = savedHTML;
                    importGroupSelect.innerHTML = `<option value="">${translateAppTextLocal('自动按类型分组')}</option>`;
                }
                updateAccountProviderNote(p);
                return;
            }

            // 恢复分组选择器（从 auto 切换回来时）
            if (importGroupSelect && importGroupSelect.dataset.savedOptions) {
                importGroupSelect.innerHTML = importGroupSelect.dataset.savedOptions;
                delete importGroupSelect.dataset.savedOptions;
            }

            if (p === 'outlook') {
                customFields.style.display = 'none';
                input.placeholder = translateAppTextLocal('邮箱----密码----client_id----refresh_token');
                hint.textContent = translateAppTextLocal('格式：邮箱----密码----client_id----refresh_token，支持批量导入（每行一个）');
                updateAccountProviderNote(p);
                return;
            }

            if (p === 'custom') {
                customFields.style.display = '';
                input.placeholder = translateAppTextLocal('邮箱----IMAP授权码/应用密码');
                hint.textContent = translateAppTextLocal('格式：邮箱----IMAP授权码/应用密码（每行一个）。自定义 IMAP 需填写上方服务器/端口；也支持：邮箱----授权码----imap_host----imap_port');
                updateAccountProviderNote(p);
                return;
            }

            customFields.style.display = 'none';
            input.placeholder = translateAppTextLocal('邮箱----IMAP授权码/应用密码');
            hint.textContent = translateAppTextLocal('格式：邮箱----IMAP授权码/应用密码，支持批量导入（每行一个）');
            updateAccountProviderNote(p);
        }

        // 显示添加账号模态框
        function resolveImportGroupId(rawGroupId) {
            return Number.isInteger(rawGroupId) && rawGroupId > 0 ? rawGroupId : null;
        }

        async function refreshMailboxAfterImport(provider, importedGroupId) {
            await loadGroups(true);

            if (currentPage !== 'mailbox') {
                return;
            }

            if (provider === 'auto') {
                if (!currentGroupId) {
                    const firstNormalGroup = groups.find(group => !isTempMailboxGroup(group));
                    if (firstNormalGroup) {
                        await selectGroup(firstNormalGroup.id);
                    }
                }
                return;
            }

            if (!importedGroupId) {
                if (currentGroupId) {
                    invalidateAccountsCache(currentGroupId);
                    await loadAccountsByGroup(currentGroupId, true);
                }
                return;
            }

            invalidateAccountsCache(importedGroupId);
            await selectGroup(importedGroupId);
        }

        /**
         * Best-effort parse emails from the multi-line import textarea.
         * Used after successful import (especially overwrite) to drop soft mail caches
         * so soft re-select cannot paint under pre-import credentials.
         */
        function extractImportCandidateEmails(accountString) {
            const text = String(accountString || '');
            const emails = [];
            const seen = new Set();
            for (const rawLine of text.split(/\r?\n/)) {
                const line = String(rawLine || '').trim();
                if (!line || line.startsWith('#')) continue;
                const first = line.split('----')[0] || line.split(',')[0] || line;
                const email = String(first || '').trim().toLowerCase();
                if (!email || !email.includes('@') || seen.has(email)) continue;
                seen.add(email);
                emails.push(email);
            }
            return emails;
        }

        // 添加账号
        async function updateAccountRemarkOnly() {
            const accountId = document.getElementById('editAccountId').value;
            const remark = document.getElementById('editRemark').value.trim();

            if (!accountId) {
                showToast(translateAppTextLocal('未找到账号'), 'error');
                return;
            }

            try {
                const response = await fetch(`/api/accounts/${accountId}/remark`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ remark })
                });

                const result = await response.json();
                if (!result.success) {
                    handleApiError(result, '备注更新失败');
                    return;
                }

                showToast(pickApiMessage(result, result.message, 'Remark updated successfully'), 'success');
                invalidateAccountDetailCache(accountId);

                if (currentGroupId) {
                    invalidateAccountsCache(currentGroupId);
                    loadAccountsByGroup(currentGroupId, true);
                }
            } catch (error) {
                showToast(translateAppTextLocal('备注更新失败'), 'error');
            }
        }

        // 更新账号
        async function updateAccount() {
            const accountId = document.getElementById('editAccountId').value;
            const accountType = document.getElementById('editAccountType').value || 'outlook';
            const isImap = accountType === 'imap';
            const oldGroupId = currentGroupId;
            const newGroupId = parseInt(document.getElementById('editGroupSelect').value);
            const clientIdInput = document.getElementById('editClientId');
            const refreshTokenInput = document.getElementById('editRefreshToken');
            const clientId = clientIdInput.value.trim();
            const refreshToken = refreshTokenInput.value.trim();
            const originalClientId = (clientIdInput.dataset.originalValue || '').trim();
            const hasClientIdChanged = !isImap && clientId !== originalClientId;
            const wantsToUpdateOutlookCredentials = !isImap && (hasClientIdChanged || !!refreshToken);

            const data = {
                email: document.getElementById('editEmail').value.trim(),
                password: document.getElementById('editPassword').value,
                client_id: wantsToUpdateOutlookCredentials ? clientId : '',
                refresh_token: wantsToUpdateOutlookCredentials ? refreshToken : '',
                group_id: newGroupId,
                remark: document.getElementById('editRemark').value.trim(),
                status: document.getElementById('editStatus').value
            };

            if (!data.email) {
                showToast(translateAppTextLocal('邮箱地址不能为空'), 'error');
                return;
            }

            // 仅在用户真正修改 Outlook 凭据时，才要求提交完整凭据对
            if (wantsToUpdateOutlookCredentials && (!data.client_id || !data.refresh_token)) {
                showToast(translateAppTextLocal('邮箱、Client ID 和 Refresh Token 不能为空'), 'error');
                return;
            }

            try {
                const response = await fetch(`/api/accounts/${accountId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    showToast(pickApiMessage(result, result.message, 'Account updated successfully'), 'success');
                    invalidateAccountDetailCache(accountId);
                    hideEditAccountModal();

                    // 清除相关分组的缓存
                    invalidateAccountsCache(oldGroupId);
                    if (oldGroupId !== newGroupId) {
                        invalidateAccountsCache(newGroupId);
                    }

                    // Address/credential changes invalidate soft mail list/detail for that mailbox.
                    if (typeof window.clearEmailListCacheForMailbox === 'function') {
                        const emailInput = document.getElementById('editEmail');
                        const previousEmail = String(
                            (emailInput && emailInput.dataset && emailInput.dataset.originalValue) || ''
                        ).trim();
                        const nextEmail = String(data.email || '').trim();
                        const emailChanged = previousEmail && nextEmail && previousEmail !== nextEmail;
                        const shouldClearMailSoftCache = (
                            emailChanged
                            || wantsToUpdateOutlookCredentials
                            || (isImap && !!data.password)
                        );
                        if (shouldClearMailSoftCache) {
                            if (previousEmail) {
                                window.clearEmailListCacheForMailbox(previousEmail);
                            }
                            if (nextEmail && nextEmail !== previousEmail) {
                                window.clearEmailListCacheForMailbox(nextEmail);
                            } else if (nextEmail) {
                                window.clearEmailListCacheForMailbox(nextEmail);
                            }
                        }
                    }
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }

                    // 刷新分组列表
                    loadGroups(true);

                    // 刷新当前分组的邮箱列表
                    if (currentGroupId) {
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(result, '更新失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('更新失败'), 'error');
            }
        }

        // 删除当前编辑的账号
        async function toggleAccountStatus(accountId, currentStatus) {
            const newStatus = currentStatus === 'inactive' ? 'active' : 'inactive';
            const successFallbackZh = newStatus === 'inactive' ? '停用成功' : '启用成功';
            const successFallbackEn = newStatus === 'inactive' ? 'Disabled successfully' : 'Enabled successfully';
            const failureFallbackZh = newStatus === 'inactive' ? '停用账号失败' : '启用账号失败';

            try {
                const response = await fetch(`/api/accounts/${accountId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });

                const data = await response.json();

                if (data.success) {
                    showToast(pickApiMessage(data, successFallbackZh, successFallbackEn), 'success');
                    invalidateAccountDetailCache(accountId);

                    // 清除当前分组的缓存
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(data, failureFallbackZh);
                }
            } catch (error) {
                showToast(translateAppTextLocal(failureFallbackZh), 'error');
            }
        }

        // 删除账号（快捷方式）
        async function toggleTelegramPush(accountId, enabled) {
            try {
                const response = await fetch(`/api/accounts/${accountId}/telegram-toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
                const data = await response.json();
                if (data.success) {
                    showToast(
                        pickApiMessage(
                            data,
                            data.message || (enabled ? '该邮箱通知参与已开启' : '该邮箱通知参与已关闭'),
                            enabled ? 'Mailbox notifications enabled' : 'Mailbox notifications disabled'
                        ),
                        'success'
                    );
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(data, '通知参与切换失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('操作失败'), 'error');
            }
        }

        // 显示导出邮箱模态框
