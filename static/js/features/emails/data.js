// split from emails.js → data.js
        function getEmailDetailCacheKey(mailboxEmail, folder, method, messageId) {
            return [
                String(mailboxEmail || '').trim(),
                String(folder || 'inbox').trim().toLowerCase() || 'inbox',
                String(method || 'graph').trim().toLowerCase() || 'graph',
                String(messageId || '').trim()
            ].join('|');
        }

        function clearEmailDetailCacheForMailbox(mailboxEmail, folder = null) {
            const emailPrefix = `${String(mailboxEmail || '').trim()}|`;
            if (!emailPrefix || emailPrefix === '|') return;
            const folderPrefix = folder != null
                ? `${String(mailboxEmail || '').trim()}|${String(folder || 'inbox').trim().toLowerCase() || 'inbox'}|`
                : emailPrefix;
            for (const key of Array.from(emailDetailCache.keys())) {
                if (String(key).startsWith(folderPrefix)) {
                    emailDetailCache.delete(key);
                }
            }
            for (const key of Object.keys(emailDetailLoadPromises)) {
                if (String(key).startsWith(folderPrefix)) {
                    delete emailDetailLoadPromises[key];
                    delete emailDetailLoadForce[key];
                }
            }
        }

        /**
         * Drop soft list + detail caches for a mailbox (all folders, or one folder).
         * Account delete/import overwrite must call this so soft re-select cannot paint
         * mail for a removed mailbox or pre-overwrite credentials.
         */
        function clearEmailListCacheForMailbox(mailboxEmail, folder = null) {
            const email = String(mailboxEmail || '').trim();
            if (!email) return;
            const folderNorm = folder != null
                ? (String(folder || 'inbox').trim().toLowerCase() || 'inbox')
                : null;
            const listKeys = Object.keys(emailListCache || {});
            for (const key of listKeys) {
                if (folderNorm == null) {
                    if (key === email || key.startsWith(`${email}_`)) {
                        delete emailListCache[key];
                    }
                } else if (key === `${email}_${folderNorm}`) {
                    delete emailListCache[key];
                }
            }
            for (const key of Object.keys(emailsLoadPromises)) {
                if (folderNorm == null) {
                    if (key === email || key.startsWith(`${email}_`)) {
                        delete emailsLoadPromises[key];
                        delete emailsLoadForce[key];
                    }
                } else if (key === `${email}_${folderNorm}`) {
                    delete emailsLoadPromises[key];
                    delete emailsLoadForce[key];
                }
            }
            clearEmailDetailCacheForMailbox(email, folderNorm);
        }

        function invalidateEmailDetailCacheEntry(mailboxEmail, folder, method, messageId) {
            const key = getEmailDetailCacheKey(mailboxEmail, folder, method, messageId);
            if (!key || key.endsWith('|')) return;
            emailDetailCache.delete(key);
            delete emailDetailLoadPromises[key];
            delete emailDetailLoadForce[key];
        }

        function clearEmailListCacheForMailboxes(mailboxEmails) {
            const list = Array.isArray(mailboxEmails) ? mailboxEmails : [mailboxEmails];
            list.forEach(email => clearEmailListCacheForMailbox(email));
        }

        window.clearEmailDetailCacheForMailbox = clearEmailDetailCacheForMailbox;
        window.clearEmailListCacheForMailbox = clearEmailListCacheForMailbox;
        window.clearEmailListCacheForMailboxes = clearEmailListCacheForMailboxes;
        window.invalidateEmailDetailCacheEntry = invalidateEmailDetailCacheEntry;

        async function loadEmails(email, forceRefresh = false) {
            const container = document.getElementById('emailList');
            const targetEmail = String(email || '').trim();
            const targetFolder = String(currentFolder || 'inbox').trim().toLowerCase() || 'inbox';
            if (!targetEmail) return null;

            // 切换账号/刷新时清除选中状态
            selectedEmailIds.clear();
            updateEmailBatchActionBar();

            // 检查缓存
            const cacheKey = `${targetEmail}_${targetFolder}`;
            const force = Boolean(forceRefresh);
            const isCurrentEmailListView = () => (
                currentAccount === targetEmail
                && String(currentFolder || 'inbox').trim().toLowerCase() === targetFolder
            );
            if (!force && emailListCache[cacheKey]) {
                const cache = emailListCache[cacheKey];
                // Only paint when still on this mailbox+folder (soft re-select of other mailbox must not clobber UI).
                if (isCurrentEmailListView()) {
                    currentEmails = sortEmailsByNewestFirst(cache.emails || []);
                    hasMoreEmails = cache.has_more;
                    currentSkip = cache.skip;
                    currentMethod = cache.method || 'graph';

                    cache.emails = currentEmails;

                    // 恢复 UI
                    const methodTag = document.getElementById('methodTag');
                    methodTag.textContent = currentMethod;
                    methodTag.style.display = 'inline';
                    document.getElementById('emailCount').textContent = `(${currentEmails.length})`;

                    renderEmailList(currentEmails);
                    return currentEmails;
                }
                return sortEmailsByNewestFirst(cache.emails || []);
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so explicit refresh starts a true network GET.
            if (emailsLoadPromises[cacheKey]) {
                if (!force || emailsLoadForce[cacheKey]) {
                    return emailsLoadPromises[cacheKey];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale cache write.
                delete emailsLoadPromises[cacheKey];
                delete emailsLoadForce[cacheKey];
            }

            // Force-refresh list drops warm details for this mailbox+folder.
            if (force) {
                clearEmailDetailCacheForMailbox(targetEmail, targetFolder);
            }

            // 禁用按钮 / loading chrome only for the currently visible mailbox+folder.
            const refreshBtn = document.querySelector('.refresh-btn');
            const folderTabs = document.querySelectorAll('.email-tab');
            const paintLoadingChrome = isCurrentEmailListView();
            if (paintLoadingChrome) {
                if (refreshBtn) {
                    refreshBtn.disabled = true;
                    refreshBtn.textContent = translateAppTextLocal('获取中...');
                }
                folderTabs.forEach(tab => tab.disabled = true);
                // 重置分页状态
                currentSkip = 0;
                hasMoreEmails = true;
                if (container) {
                    container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> ${translateAppTextLocal('获取中…')}</div>`;
                }
            }

            // Capture method at request start so folder switch mid-flight does not rewrite the URL.
            const requestMethod = String(currentMethod || 'graph').trim().toLowerCase() || 'graph';
            emailsLoadForce[cacheKey] = force;
            const request = (async () => {
                try {
                    // 每次只查询20封邮件
                    const response = await fetch(
                        `/api/emails/${encodeURIComponent(targetEmail)}?method=${requestMethod}&folder=${encodeURIComponent(targetFolder)}&skip=0&top=20`
                    );
                    const data = await response.json();

                    // If force supersede abandoned this request, do not write stale list cache.
                    if (emailsLoadPromises[cacheKey] !== request) {
                        return emailListCache[cacheKey] ? emailListCache[cacheKey].emails : null;
                    }

                    if (data.success) {
                        const sortedEmails = sortEmailsByNewestFirst(data.emails || []);
                        const method = data.method === 'Graph API' ? 'graph' : 'imap';
                        if (typeof syncAccountSummaryToAccountCache === 'function' && data.account_summary) {
                            syncAccountSummaryToAccountCache(targetEmail, data.account_summary);
                        }

                        // Always warm cache for this mailbox+folder (soft re-select later).
                        emailListCache[cacheKey] = {
                            emails: sortedEmails,
                            has_more: data.has_more,
                            skip: 0,
                            method
                        };

                        // Do not paint if user already switched mailbox/folder.
                        if (!isCurrentEmailListView()) {
                            return sortedEmails;
                        }

                        currentEmails = sortedEmails;
                        currentMethod = method;
                        hasMoreEmails = data.has_more;
                        currentSkip = 0;

                        // 显示使用的方法和邮件数量
                        const methodTag = document.getElementById('methodTag');
                        if (methodTag) {
                            methodTag.textContent = data.method;
                            methodTag.style.display = 'inline';
                        }

                        const emailCountEl = document.getElementById('emailCount');
                        if (emailCountEl) {
                            emailCountEl.textContent = `(${currentEmails.length})`;
                        }

                        renderEmailList(currentEmails);
                        return currentEmails;
                    }

                    // 显示详细的多方法失败弹框（仅当前视图）
                    if (!isCurrentEmailListView()) {
                        return null;
                    }
                    if (data.details) {
                        showEmailFetchErrorModal(data.details);
                    } else {
                        handleApiError(data, '获取邮件失败');
                    }
                    if (container) {
                        container.innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">⚠️</span><p>${translateAppTextLocal('获取邮件失败，')}<a href="javascript:void(0)" id="showEmailErrorLink" style="color:#409eff;text-decoration:underline;">${translateAppTextLocal('点击查看详情')}</a></p>
                            </div>
                        `;
                    }
                    lastFetchErrorDetails = data.details || {};
                    // 绑定事件监听器
                    const errorLink = document.getElementById('showEmailErrorLink');
                    if (errorLink) {
                        errorLink.addEventListener('click', () => showEmailFetchErrorModal(lastFetchErrorDetails));
                    }
                    return null;
                } catch (error) {
                    if (emailsLoadPromises[cacheKey] !== request) {
                        return emailListCache[cacheKey] ? emailListCache[cacheKey].emails : null;
                    }
                    console.error('加载邮件列表失败:', error);
                    if (!isCurrentEmailListView()) {
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
                    // Only restore chrome we disabled for the currently visible view.
                    if (paintLoadingChrome) {
                        if (refreshBtn) {
                            refreshBtn.disabled = false;
                            refreshBtn.textContent = translateAppTextLocal('获取邮件');
                        }
                        folderTabs.forEach(tab => tab.disabled = false);
                    }
                    if (emailsLoadPromises[cacheKey] === request) {
                        delete emailsLoadPromises[cacheKey];
                        delete emailsLoadForce[cacheKey];
                    }
                }
            })();

            emailsLoadPromises[cacheKey] = request;
            return request;
        }

        // 渲染邮件列表
        // Selected email IDs
        let selectedEmailIds = new Set();
        let isBatchSelectMode = false;

        function getEmailListColdFetchPrompt(folder = currentFolder) {
            const normalized = String(folder || 'inbox').trim().toLowerCase() || 'inbox';
            return translateAppTextLocal(
                normalized === 'inbox'
                    ? '点击"获取邮件"按钮获取收件箱'
                    : '点击"获取邮件"按钮获取垃圾邮件'
            );
        }

