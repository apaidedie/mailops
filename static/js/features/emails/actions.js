// split from emails.js → actions.js
        function toggleEmailSelection(emailId) {
            if (selectedEmailIds.has(emailId)) {
                selectedEmailIds.delete(emailId);
            } else {
                selectedEmailIds.add(emailId);
            }

            // Re-render to update checkbox UI (or efficiently update DOM)
            // For simplicity, we just find the checkbox and update it
            // implementation below is cheap
            renderEmailList(currentEmails, { scrollToTop: false });
        }

        function updateEmailBatchActionBar() {
            const bar = document.getElementById('emailBatchActionBar');
            if (!bar) return;
            if (selectedEmailIds.size > 0) {
                bar.style.display = 'flex';
                const countEl = document.getElementById('emailSelectedCount');
                if (countEl) {
                    countEl.textContent =
                        typeof formatSelectedItemsLabel === 'function'
                            ? formatSelectedItemsLabel(selectedEmailIds.size)
                            : translateAppTextLocal('已选 ' + selectedEmailIds.size + ' 项');
                }
            } else {
                bar.style.display = 'none';
            }
        }

        async function confirmBatchDeleteEmails() {
            if (selectedEmailIds.size === 0) return;

            if (!confirm(`确定要永久删除选中的 ${selectedEmailIds.size} 封邮件吗？此操作不可恢复！`)) {
                return;
            }

            await deleteEmails(Array.from(selectedEmailIds));
        }

        async function confirmDeleteCurrentEmail() {
            if (!currentEmailDetail || !currentEmailDetail.id) return;

            if (!confirm('确定要永久删除这封邮件吗？此操作不可恢复！')) {
                return;
            }

            if (resolveEmailDetailSource() === 'temp') {
                await deleteCurrentTempEmailMessage();
                return;
            }

            await deleteEmails([currentEmailDetail.id]);
        }

        async function deleteEmails(ids) {
            showToast(translateAppTextLocal('正在删除...'), 'info');

            try {
                const response = await fetch('/api/emails/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: currentAccount,
                        ids: ids
                    })
                });

                const result = await response.json();

                if (result.success) {
                    showToast(translateAppTextLocal('成功删除 ' + result.success_count + ' 封邮件'));

                    // Remove deleted emails from currentEmails
                    const deletedIds = new Set(ids); // Ideally result should return what was deleted
                    currentEmails = currentEmails.filter(e => !deletedIds.has(e.id));
                    selectedEmailIds.clear();
                    // Drop warm detail entries for deleted messages.
                    for (const deletedId of deletedIds) {
                        invalidateEmailDetailCacheEntry(currentAccount, currentFolder, currentMethod, deletedId);
                    }
                    // Keep soft list cache aligned so loadEmails(false) cannot repaint deleted rows.
                    if (currentAccount) {
                        const listCacheKey = `${currentAccount}_${currentFolder}`;
                        const prev = emailListCache[listCacheKey];
                        emailListCache[listCacheKey] = {
                            emails: currentEmails,
                            has_more: prev && typeof prev.has_more === 'boolean' ? prev.has_more : hasMoreEmails,
                            skip: prev && prev.skip != null ? prev.skip : currentSkip,
                            method: prev && prev.method ? prev.method : currentMethod
                        };
                    }
                    const emailCountEl = document.getElementById('emailCount');
                    if (emailCountEl) {
                        emailCountEl.textContent = `(${currentEmails.length})`;
                    }

                    renderEmailList(currentEmails, { scrollToTop: false });

                    // If current viewed email was deleted, clear view
                    if (currentEmailDetail && deletedIds.has(currentEmailDetail.id)) {
                        const refs = getEmailDetailRefs({ source: 'mailbox' });
                        refs.container.innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">🗑️</span><p>${translateAppTextLocal('邮件已删除')}</p>
                            </div>
                        `;
                        setEmailDetailToolbarVisibility(false, { source: 'mailbox' });
                    }

                    // If errors
                    if (result.failed_count > 0) {
                        console.warn('Deletion errors:', result.errors);
                        showToast(translateAppTextLocal('部分删除失败 (' + result.failed_count + ' 封)'), 'warning');
                    }
                } else {
                    const msg = window.resolveApiErrorMessage
                        ? window.resolveApiErrorMessage(result.error || result, '删除失败', 'Delete failed')
                        : (typeof result.error === 'string' ? result.error : (result.error && result.error.message) || translateAppTextLocal('未知错误'));
                    showToast(translateAppTextLocal('删除失败') + ': ' + msg, 'error', result.error && typeof result.error === 'object' ? result.error : null);
                }
            } catch (e) {
                showToast(translateAppTextLocal('网络错误'), 'error');
                console.error(e);
            }
        }

        async function deleteCurrentTempEmailMessage() {
            if (!currentEmailDetail || !currentEmailDetail.id || !currentAccount) {
                return;
            }

            showToast(translateAppTextLocal('正在删除...'), 'info');

            try {
                const response = await fetch(
                    `/api/temp-emails/${encodeURIComponent(currentAccount)}/messages/${encodeURIComponent(currentEmailDetail.id)}`,
                    { method: 'DELETE' }
                );
                const result = await response.json();

                if (!result.success) {
                    handleApiError(result, '删除失败');
                    return;
                }

                const deletedId = currentEmailDetail.id;
                currentEmails = currentEmails.filter(email => email.id !== deletedId);
                currentEmailDetail = null;
                // Drop warm temp detail for the deleted message.
                if (typeof window.invalidateTempEmailDetailCacheEntry === 'function') {
                    window.invalidateTempEmailDetailCacheEntry(currentAccount, deletedId);
                }
                // Keep temp message soft cache aligned so soft re-select cannot repaint deleted rows.
                if (typeof tempEmailMessagesCache !== 'undefined' && tempEmailMessagesCache && typeof tempEmailMessagesCache.set === 'function') {
                    tempEmailMessagesCache.set(currentAccount, {
                        emails: currentEmails,
                        count: currentEmails.length
                    });
                }
                renderEmailList(currentEmails, { scrollToTop: false });

                const tempContainer = document.getElementById('tempEmailMessageList');
                if (tempContainer && typeof renderTempEmailMessageList === 'function') {
                    renderTempEmailMessageList(tempContainer, currentEmails);
                }

                const emailCount = document.getElementById('emailCount');
                if (emailCount) {
                    emailCount.textContent = `(${currentEmails.length})`;
                }

                resetEmailDetailState({ source: 'temp' });
                showToast(translateAppTextLocal('邮件已删除'), 'success');
            } catch (error) {
                console.error('删除临时邮件失败:', error);
                showToast(translateAppTextLocal('网络错误，请重试'), 'error');
            }
        }

        // 选择邮件（soft-load warm cache; forceRefresh bypasses cache）
        async function selectEmail(messageId, index, forceRefresh = false) {
            document.querySelectorAll('.email-item').forEach((item, i) => {
                item.classList.toggle('active', i === index);
            });

            // 重置信任模式
            const refs = getEmailDetailRefs({ source: 'mailbox' });
            if (refs.trustCheckbox) {
                refs.trustCheckbox.checked = false;
            }
            isTrustedMode = false;

            // 显示工具栏
            setEmailDetailToolbarVisibility(true, { source: 'mailbox' });
            setMailboxDetailFocus(true);

            const container = refs.container;
            // Capture view identity at request start so rapid switches cannot paint stale detail.
            const mailboxEmail = String(currentAccount || '').trim();
            const normalizedMessageId = String(messageId || '').trim();
            const folder = String(currentFolder || 'inbox').trim().toLowerCase() || 'inbox';
            const method = String(currentMethod || 'graph').trim().toLowerCase() || 'graph';
            if (!mailboxEmail || !normalizedMessageId) return null;
            const cacheKey = getEmailDetailCacheKey(mailboxEmail, folder, method, normalizedMessageId);
            // Paint only while still on the same mailbox+folder+method that started this request.
            // Message-id identity is enforced by cacheKey / active row; list switches clear via loadEmails.
            const isCurrentMailboxFolderMethod = () => (
                currentAccount === mailboxEmail
                && String(currentFolder || 'inbox').trim().toLowerCase() === folder
                && String(currentMethod || 'graph').trim().toLowerCase() === method
            );

            const force = Boolean(forceRefresh);
            // Soft re-select: same account/folder/method/message already warm — re-render without network.
            if (!force && emailDetailCache.has(cacheKey)) {
                const warmEmail = emailDetailCache.get(cacheKey);
                if (isCurrentMailboxFolderMethod()) {
                    currentEmailDetail = warmEmail;
                    try {
                        renderEmailDetail(warmEmail, { source: 'mailbox' });
                    } catch (renderError) {
                        console.error('渲染邮件详情失败:', renderError);
                        if (container) {
                            container.innerHTML = `
                                <div class="empty-state">
                                    <span class="empty-icon">⚠️</span><p>${translateAppTextLocal('邮件渲染失败')}: ${escapeHtml(renderError.message || translateAppTextLocal('未知错误'))}</p>
                                </div>
                            `;
                        }
                    }
                }
                return warmEmail;
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so re-select after list refresh starts a true network GET.
            if (emailDetailLoadPromises[cacheKey]) {
                if (!force || emailDetailLoadForce[cacheKey]) {
                    return emailDetailLoadPromises[cacheKey];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                delete emailDetailLoadPromises[cacheKey];
                delete emailDetailLoadForce[cacheKey];
            }

            const paintLoadingChrome = isCurrentMailboxFolderMethod();
            if (paintLoadingChrome && container) {
                container.innerHTML = '<div class="loading-overlay"><span class="spinner"></span></div>';
            }

            emailDetailLoadForce[cacheKey] = force;
            const request = (async () => {
                try {
                    const response = await fetch(`/api/email/${encodeURIComponent(mailboxEmail)}/${encodeURIComponent(normalizedMessageId)}?method=${encodeURIComponent(method)}&folder=${encodeURIComponent(folder)}`);
                    const data = await response.json();

                    if (emailDetailLoadPromises[cacheKey] !== request) {
                        return emailDetailCache.get(cacheKey) || null;
                    }
                    if (data.success) {
                        // Always warm cache for this key (soft re-select later).
                        emailDetailCache.set(cacheKey, data.email);
                        // Do not paint if user already switched mailbox/folder/method.
                        if (!isCurrentMailboxFolderMethod()) {
                            return data.email;
                        }
                        currentEmailDetail = data.email;
                        try {
                            renderEmailDetail(data.email, { source: 'mailbox' });
                        } catch (renderError) {
                            console.error('渲染邮件详情失败:', renderError);
                            // 渲染失败时回退为纯文本显示
                            if (container) {
                                container.innerHTML = `
                                    <div class="empty-state">
                                        <span class="empty-icon">⚠️</span><p>${translateAppTextLocal('邮件渲染失败')}: ${escapeHtml(renderError.message || translateAppTextLocal('未知错误'))}</p>
                                    </div>
                                `;
                            }
                        }
                        return data.email;
                    }

                    if (!isCurrentMailboxFolderMethod()) {
                        return null;
                    }
                    handleApiError(data, '加载邮件详情失败');
                    if (container) {
                        container.innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">⚠️</span><p>${window.resolveApiErrorMessage ? window.resolveApiErrorMessage(data.error || data, '加载失败', 'Load failed') : (data.error && data.error.message ? data.error.message : translateAppTextLocal('加载失败'))}</p>
                            </div>
                        `;
                    }
                    return null;
                } catch (error) {
                    if (emailDetailLoadPromises[cacheKey] !== request) {
                        return emailDetailCache.get(cacheKey) || null;
                    }
                    console.error('加载邮件详情失败:', error);
                    if (!isCurrentMailboxFolderMethod()) {
                        return null;
                    }
                    if (container) {
                        container.innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">⚠️</span><p>${translateAppTextLocal('网络错误，请重试')}${error.message ? ' (' + escapeHtml(error.message) + ')' : ''}</p>
                            </div>
                        `;
                    }
                    return null;
                } finally {
                    if (emailDetailLoadPromises[cacheKey] === request) {
                        delete emailDetailLoadPromises[cacheKey];
                        delete emailDetailLoadForce[cacheKey];
                    }
                }
            })();

            emailDetailLoadPromises[cacheKey] = request;
            return request;
        }

        // 渲染邮件详情
