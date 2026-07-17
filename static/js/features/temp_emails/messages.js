// split from temp_emails.js → messages.js
        function refreshTempEmailMessages() {
            if (currentAccount && isTempEmailGroup) {
                loadTempEmailMessages(currentAccount, true);
            }
        }

        async function clearTempEmailMessages(email) {
            if (!confirm(`确定要清空临时邮箱 ${email} 的所有邮件吗？`)) {
                return;
            }

            try {
                const response = await fetch(`/api/temp-emails/${encodeURIComponent(email)}/clear`, {
                    method: 'DELETE'
                });

                const data = await response.json();

                if (data.success) {
                    showToast(translateAppTextLocal('邮件已清空'), 'success');
                    seedEmptyTempEmailMessagesCache(email);

                    // 如果当前选中的就是这个邮箱，清空邮件列表
                    if (currentAccount === email) {
                        currentEmails = [];
                        currentEmailDetail = null;
                        const emailCount = document.getElementById('emailCount');
                        if (emailCount) {
                            emailCount.textContent = '(0)';
                        }
                        const emptyStateHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📭</span><p>${translateAppTextLocal('收件箱为空')}</p>
                            </div>
                        `;
                        const emailList = document.getElementById('emailList');
                        const tempMessageList = document.getElementById('tempEmailMessageList');
                        if (emailList) emailList.innerHTML = emptyStateHTML;
                        if (tempMessageList) tempMessageList.innerHTML = emptyStateHTML;
                        if (typeof resetEmailDetailState === 'function') {
                            resetEmailDetailState({ source: 'temp' });
                        }
                    }
                } else {
                    handleApiError(data, '清空临时邮箱失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('清空失败'), 'error');
            }
        }

        // 删除临时邮箱
        function applyTempEmailMessagesPayload(targetEmail, payload) {
            const emails = Array.isArray(payload?.emails) ? payload.emails : [];
            const count = payload && payload.count != null ? payload.count : emails.length;
            currentEmails = emails;

            const methodTag = document.getElementById('methodTag');
            if (methodTag) {
                methodTag.textContent = 'Temp Mail';
                methodTag.style.display = 'inline';
                methodTag.style.backgroundColor = '#00bcf2';
                methodTag.style.color = 'white';
            }

            const emailCount = document.getElementById('emailCount');
            if (emailCount) emailCount.textContent = `(${count})`;

            // Render to mailbox emailList
            renderEmailList(emails);

            // Also render to temp-emails page container
            const tempContainer = document.getElementById('tempEmailMessageList');
            if (tempContainer) {
                renderTempEmailMessageList(tempContainer, emails);
            }
        }

        // 加载临时邮箱的邮件
        async function loadTempEmailMessages(email, forceRefresh = false) {
            const container = document.getElementById('emailList');
            const tempContainer = document.getElementById('tempEmailMessageList');
            const loadingHTML = '<div class="loading-overlay"><span class="spinner"></span></div>';

            // BUG-05: stale request guard
            const requestSeq = ++tempEmailMessagesRequestSeq;
            const targetEmail = String(email || '').trim();
            if (!targetEmail) return null;

            currentEmailDetail = null;
            if (typeof resetEmailDetailState === 'function') {
                resetEmailDetailState({ source: 'temp' });
            }

            const force = Boolean(forceRefresh);
            // Soft re-select: paint warm cache without network (only if still viewing this mailbox).
            if (!force && tempEmailMessagesCache.has(targetEmail)) {
                const warm = tempEmailMessagesCache.get(targetEmail);
                if (currentAccount === targetEmail) {
                    applyTempEmailMessagesPayload(targetEmail, warm);
                }
                return warm;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so explicit refresh starts a true network GET.
            if (tempEmailMessagesLoadPromises[targetEmail]) {
                if (!force || tempEmailMessagesLoadForce[targetEmail]) {
                    return tempEmailMessagesLoadPromises[targetEmail];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                delete tempEmailMessagesLoadPromises[targetEmail];
                delete tempEmailMessagesLoadForce[targetEmail];
            }

            // Force-refresh message list drops warm details for this mailbox.
            if (force) {
                clearTempEmailDetailCacheForMailbox(targetEmail);
            }

            // Loading chrome only for the currently visible temp mailbox.
            const paintLoadingChrome = currentAccount === targetEmail;
            if (paintLoadingChrome) {
                if (container) container.innerHTML = loadingHTML;
                if (tempContainer) tempContainer.innerHTML = loadingHTML;
            }

            // 禁用按钮
            const refreshBtn = document.getElementById('tempEmailRefreshBtn');
            if (paintLoadingChrome && refreshBtn) {
                refreshBtn.disabled = true;
                refreshBtn.textContent = translateAppTextLocal('获取中...');
            }

            tempEmailMessagesLoadForce[targetEmail] = force;
            const request = (async () => {
                try {
                    const response = await fetch(`/api/temp-emails/${encodeURIComponent(targetEmail)}/messages`);
                    const data = await response.json();

                    // Force-supersede abandoned this request: do not write/paint.
                    if (tempEmailMessagesLoadPromises[targetEmail] !== request) {
                        return tempEmailMessagesCache.get(targetEmail) || null;
                    }

                    if (data.success) {
                        const payload = {
                            emails: Array.isArray(data.emails) ? data.emails : [],
                            count: data.count != null ? data.count : (data.emails || []).length,
                        };
                        // Always warm cache for this mailbox (soft re-select later).
                        tempEmailMessagesCache.set(targetEmail, payload);
                        // Do not paint if user already switched mailbox or a newer request started.
                        if (requestSeq !== tempEmailMessagesRequestSeq || currentAccount !== targetEmail) {
                            return payload;
                        }
                        applyTempEmailMessagesPayload(targetEmail, payload);
                        return payload;
                    }

                    if (requestSeq !== tempEmailMessagesRequestSeq || currentAccount !== targetEmail) {
                        return null;
                    }
                    handleApiError(data, '加载临时邮件失败');
                    const errHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><p>${window.resolveApiErrorMessage ? window.resolveApiErrorMessage(data.error || data, '加载失败', 'Load failed') : (data.error && data.error.message ? data.error.message : translateAppTextLocal('加载失败'))}</p></div>`;
                    if (container) container.innerHTML = errHTML;
                    if (tempContainer) tempContainer.innerHTML = errHTML;
                    return null;
                } catch (error) {
                    if (tempEmailMessagesLoadPromises[targetEmail] !== request) {
                        return tempEmailMessagesCache.get(targetEmail) || null;
                    }
                    if (requestSeq !== tempEmailMessagesRequestSeq || currentAccount !== targetEmail) {
                        return null;
                    }
                    const errHTML = '<div class="empty-state"><span class="empty-icon">⚠️</span><p>' + translateAppTextLocal('网络错误，请重试') + '</p></div>';
                    if (container) container.innerHTML = errHTML;
                    if (tempContainer) tempContainer.innerHTML = errHTML;
                    return null;
                } finally {
                    if (tempEmailMessagesLoadPromises[targetEmail] === request) {
                        delete tempEmailMessagesLoadPromises[targetEmail];
                        delete tempEmailMessagesLoadForce[targetEmail];
                    }
                    if (refreshBtn) {
                        // 仅当前最新请求结束时才恢复按钮状态，避免旧请求提前解锁。
                        if (requestSeq === tempEmailMessagesRequestSeq) {
                            refreshBtn.disabled = false;
                            refreshBtn.innerHTML = `<svg class="ui-icon ui-icon--sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 0 0-14.8-4.2L4 9h5V4L7.1 5.9M4 13a8 8 0 0 0 14.8 4.2L20 15h-5v5l1.9-1.9"/></svg>${translateAppTextLocal('获取邮件')}`;
                        }
                    }
                }
            })();

            tempEmailMessagesLoadPromises[targetEmail] = request;
            return request;
        }

        // 渲染临时邮箱邮件列表到独立页面
        function renderTempEmailMessageList(container, emails) {
            if (!emails || emails.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon" aria-hidden="true"></span>
                        <p class="ui-empty-title">${translateAppTextLocal('暂无邮件')}</p>
                        <button type="button" class="btn btn-primary btn-sm" onclick="if(currentAccount) loadTempEmailMessages(currentAccount, true)">${translateAppTextLocal('获取邮件')}</button>
                    </div>
                `;
                return;
            }
            container.innerHTML = emails.map((email, index) => {
                const subject = email.subject || translateAppTextLocal('无主题');
                const from = email.from || translateAppTextLocal('未知发件人');
                const date = email.date || '';
                const preview = (email.body_preview || '').substring(0, 80);
                return `
                    <div class="email-item ${index === 0 ? '' : ''}" onclick="getTempEmailDetail('${escapeJs(email.id || email.message_id || '')}', ${index})">
                        <div class="email-subject">${escapeHtml(subject)}</div>
                        <div class="email-from">${escapeHtml(from)}</div>
                        <div class="email-preview">${escapeHtml(preview)}</div>
                        <div class="email-date">${escapeHtml(date)}</div>
                    </div>
                `;
            }).join('');
        }

        // 获取临时邮件详情（soft-load warm cache; forceRefresh bypasses cache）
        async function getTempEmailDetail(messageId, index, forceRefresh = false) {
            document.querySelectorAll('#tempEmailMessageList .email-item').forEach((item, i) => {
                item.classList.toggle('active', i === index);
            });

            if (typeof showEmailDetailContainer === 'function') {
                showEmailDetailContainer({ source: 'temp' });
            }
            if (typeof setTempDetailFocus === 'function') {
                setTempDetailFocus(true);
            }
            if (typeof setEmailDetailToolbarVisibility === 'function') {
                setEmailDetailToolbarVisibility(true, { source: 'temp' });
            }

            const refs = typeof getEmailDetailRefs === 'function'
                ? getEmailDetailRefs({ source: 'temp' })
                : {
                    container: document.getElementById('tempEmailDetail'),
                    toolbar: document.getElementById('tempEmailDetailToolbar')
                };
            const container = refs.container;
            // Capture mailbox identity at request start so rapid switches cannot paint stale detail.
            const mailboxEmail = String(currentAccount || '').trim();
            const normalizedMessageId = String(messageId || '').trim();
            if (!mailboxEmail || !normalizedMessageId) return null;
            const cacheKey = getTempEmailDetailCacheKey(mailboxEmail, normalizedMessageId);
            const isCurrentTempMailbox = () => String(currentAccount || '').trim() === mailboxEmail;

            const force = Boolean(forceRefresh);
            // Soft re-select: same mailbox/message detail already warm — re-render without network.
            if (!force && tempEmailDetailCache.has(cacheKey)) {
                const warmEmail = tempEmailDetailCache.get(cacheKey);
                if (isCurrentTempMailbox()) {
                    currentEmailDetail = warmEmail;
                    if (typeof renderEmailDetail === 'function') {
                        renderEmailDetail(warmEmail, { source: 'temp' });
                    }
                }
                return warmEmail;
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so re-select after list refresh starts a true network GET.
            if (tempEmailDetailLoadPromises[cacheKey]) {
                if (!force || tempEmailDetailLoadForce[cacheKey]) {
                    return tempEmailDetailLoadPromises[cacheKey];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                delete tempEmailDetailLoadPromises[cacheKey];
                delete tempEmailDetailLoadForce[cacheKey];
            }

            const paintLoadingChrome = isCurrentTempMailbox();
            if (paintLoadingChrome && container) {
                container.innerHTML = '<div class="loading-overlay"><span class="spinner"></span></div>';
            }

            // BUG-05: stale request guard
            const requestSeq = ++tempEmailDetailRequestSeq;
            tempEmailDetailLoadForce[cacheKey] = force;

            const request = (async () => {
                try {
                    const response = await fetch(`/api/temp-emails/${encodeURIComponent(mailboxEmail)}/messages/${encodeURIComponent(normalizedMessageId)}`);
                    const data = await response.json();

                    // Force-supersede abandoned this request: do not write/paint.
                    if (tempEmailDetailLoadPromises[cacheKey] !== request) {
                        return tempEmailDetailCache.get(cacheKey) || null;
                    }

                    if (data.success) {
                        // Always warm cache for this key (soft re-select later).
                        tempEmailDetailCache.set(cacheKey, data.email);
                        // Do not paint if user already switched mailbox or a newer detail request started.
                        if (requestSeq !== tempEmailDetailRequestSeq || !isCurrentTempMailbox()) {
                            return data.email;
                        }
                        currentEmailDetail = data.email;
                        renderEmailDetail(data.email, { source: 'temp' });
                        return data.email;
                    }

                    if (requestSeq !== tempEmailDetailRequestSeq || !isCurrentTempMailbox()) {
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
                    if (tempEmailDetailLoadPromises[cacheKey] !== request) {
                        return tempEmailDetailCache.get(cacheKey) || null;
                    }
                    if (requestSeq !== tempEmailDetailRequestSeq || !isCurrentTempMailbox()) {
                        return null;
                    }
                    if (container) {
                        container.innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">⚠️</span><p>${translateAppTextLocal('网络错误，请重试')}</p>
                            </div>
                        `;
                    }
                    return null;
                } finally {
                    if (tempEmailDetailLoadPromises[cacheKey] === request) {
                        delete tempEmailDetailLoadPromises[cacheKey];
                        delete tempEmailDetailLoadForce[cacheKey];
                    }
                }
            })();

            tempEmailDetailLoadPromises[cacheKey] = request;
            return request;
        }

        // Soft re-paint open temp inventory/messages after language change (no network).
        window.addEventListener('ui-language-changed', () => {
            try {
                // Soft re-paint warm temp inventory (including empty arrays) without network.
                // renderTempEmailList itself no-ops off the temp-emails page.
                if (accountsCache && Array.isArray(accountsCache['temp']) && typeof renderTempEmailList === 'function') {
                    renderTempEmailList(accountsCache['temp']);
                }
            } catch (e) {}
            try {
                // Include empty message lists so empty chrome re-translates.
                if (
                    Array.isArray(currentEmails)
                    && isTempEmailGroup
                    && typeof applyTempEmailMessagesPayload === 'function'
                    && currentAccount
                ) {
                    applyTempEmailMessagesPayload(currentAccount, {
                        emails: currentEmails,
                        count: currentEmails.length
                    });
                }
            } catch (e) {}
        });
