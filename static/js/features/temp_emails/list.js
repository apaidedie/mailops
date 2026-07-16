// split from temp_emails.js → list.js
        function copyTempEmailCurrent() {
            const el = document.getElementById('tempEmailCurrentName');
            if (!el || !el.textContent) return;
            const text = el.textContent.trim();
            // Compare against both source and translated placeholder so EN UI still works.
            const placeholderZh = '选择一个临时邮箱';
            const placeholderEn = (typeof translateAppTextLocal === 'function')
                ? translateAppTextLocal(placeholderZh)
                : placeholderZh;
            if (text && text !== placeholderZh && text !== placeholderEn) {
                copyEmail(text);
            }
        }

        // Dedicated temp-emails page only (inventory paints #tempEmailContainer, not mailbox).
        function isCurrentTempEmailsPage() {
            return typeof currentPage !== 'undefined' && currentPage === 'temp-emails';
        }

        // 加载临时邮箱列表
        async function loadTempEmails(forceRefresh = false) {
            // Dedicated page surface only — never touch shared mailbox #accountList.
            const pageContainer = document.getElementById('tempEmailContainer');

            // Force-refresh means temp inventory may have changed; drop unified soft directory
            // and audit soft cache (create/delete writes audit rows).
            if (forceRefresh) {
                if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                    window.invalidateUnifiedMailboxDirectoryCache();
                }
                if (typeof window.invalidateAuditLogPageCache === 'function') {
                    window.invalidateAuditLogPageCache();
                }
                // Provider credentials/domains may have changed; do not soft-paint stale options.
                invalidateTempEmailOptionsCache();
            }

            const providerSelect = document.getElementById('tempEmailProviderSelect');
            if (providerSelect) {
                syncTempEmailProviderSelection(providerSelect.value, { forceRefresh });
            }
            if (typeof loadMailboxProviderCatalog === 'function') {
                loadMailboxProviderCatalog(forceRefresh);
            }

            const force = Boolean(forceRefresh);
            // Soft re-entry: always return warm cache; paint only on the temp-emails page
            // into #tempEmailContainer (never shared mailbox #accountList).
            if (!force && accountsCache['temp']) {
                if (isCurrentTempEmailsPage()) {
                    renderTempEmailList(accountsCache['temp']);
                }
                return accountsCache['temp'];
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so generate/delete always start a true network GET.
            if (tempEmailsLoadPromise) {
                if (!force || tempEmailsLoadForce) {
                    return tempEmailsLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                tempEmailsLoadPromise = null;
                tempEmailsLoadForce = false;
            }

            // Loading chrome only on #tempEmailContainer while the dedicated page is active.
            const paintLoadingChrome = isCurrentTempEmailsPage();
            if (paintLoadingChrome && pageContainer) {
                pageContainer.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> ${translateAppTextLocal('加载中…')}</div>`;
            }

            tempEmailsLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/temp-emails');
                    const data = await response.json();

                    if (tempEmailsLoadPromise !== request) {
                        return accountsCache['temp'];
                    }
                    if (data.success) {
                        // Always warm inventory soft cache; paint only on temp-emails page.
                        accountsCache['temp'] = data.emails;
                        if (isCurrentTempEmailsPage()) {
                            renderTempEmailList(data.emails);
                        }

                        const group = groups.find(g => g.name === '临时邮箱');
                        if (group) {
                            group.account_count = data.emails.length;
                            renderGroupList(groups);
                        }
                    }
                    return accountsCache['temp'];
                } catch (error) {
                    if (tempEmailsLoadPromise !== request) {
                        return accountsCache['temp'];
                    }
                    // Error chrome only on dedicated container while still on temp-emails page.
                    if (isCurrentTempEmailsPage() && pageContainer) {
                        pageContainer.innerHTML = `<div class="empty-state"><p>${translateAppTextLocal('加载失败')}</p></div>`;
                    }
                    return accountsCache['temp'];
                } finally {
                    if (tempEmailsLoadPromise === request) {
                        tempEmailsLoadPromise = null;
                        tempEmailsLoadForce = false;
                    }
                }
            })();

            tempEmailsLoadPromise = request;
            return request;
        }

        // 渲染临时邮箱列表
        function renderTempEmailList(emails) {
            // Paint only the dedicated temp page container. Never write shared mailbox
            // #accountList — language soft-repaint / off-page loads must not clobber it.
            if (!isCurrentTempEmailsPage()) {
                return;
            }
            const pageContainer = document.getElementById('tempEmailContainer');
            if (!pageContainer) {
                return;
            }

            if (emails.length === 0) {
                pageContainer.innerHTML = `
                    <div class="ui-empty">
                        <div class="ui-empty-title">${translateAppTextLocal('还没有临时邮箱')}</div>
                        <div class="ui-empty-desc">${translateAppTextLocal('选好 Provider 与域名后，一键创建即可开始收验证码邮件。')}</div>
                        <button type="button" class="btn btn-primary" onclick="generateTempEmail()">${translateAppTextLocal('创建第一个临时邮箱')}</button>
                    </div>
                `;
                return;
            }

            const colors = ['var(--clr-accent)', 'var(--clr-jade)', 'var(--clr-primary)', '#6C5CE7', '#00B894', '#E17055'];

            const cardHTML = emails.map((email, idx) => {
                const initial = (email.email || '?')[0].toUpperCase();
                const color = colors[idx % colors.length];
                return `
                <div class="account-card ${currentAccount === email.email ? 'active' : ''}"
                     onclick="selectTempEmail('${escapeJs(email.email)}')">
                    <div class="account-card-top">
                        <div class="account-avatar" style="background:${color};">${initial}</div>
                        <div class="account-info">
                            <div class="account-email" onclick="event.stopPropagation(); copyEmail('${escapeJs(email.email)}')" title="${translateAppTextLocal('点击复制')}">${escapeHtml(email.email)}</div>
                            <div class="account-kind-label">${translateAppTextLocal('临时邮箱')}</div>
                        </div>
                    </div>
                    <div class="account-card-bottom">
                        <div class="account-actions">
                            <button class="btn btn-sm btn-accent account-code-btn" onclick="event.stopPropagation(); copyVerificationInfo('${escapeJs(email.email)}', this, { source: 'temp' })" title="${translateAppTextLocal('提取验证码')}">${translateAppTextLocal('验证码')}</button>
                            <button class="btn-icon" onclick="event.stopPropagation(); copyEmail('${escapeJs(email.email)}')" title="${translateAppTextLocal('复制')}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="12" rx="1.5"/><path d="M6 16V5.5A1.5 1.5 0 0 1 7.5 4H15"/></svg></button>
                            <button class="btn-icon" onclick="event.stopPropagation(); clearTempEmailMessages('${escapeJs(email.email)}')" title="${translateAppTextLocal('清空')}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7l.8 12h4.4L15 7M10 7V5h4v2"/></svg></button>
                            <button class="btn-icon is-danger" onclick="event.stopPropagation(); deleteTempEmail('${escapeJs(email.email)}')" title="${translateAppTextLocal('删除')}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V5h6v2M8 7l1 12h6l1-12"/></svg></button>
                        </div>
                    </div>
                </div>
            `}).join('');

            pageContainer.innerHTML = cardHTML;
        }

        // 生成临时邮箱
        async function generateTempEmail() {
            try {
                const prefixInput = document.getElementById('tempEmailPrefixInput');
                const domainSelect = document.getElementById('tempEmailDomainSelect');
                const providerSelect = document.getElementById('tempEmailProviderSelect');
                const payload = {};
                if (prefixInput && prefixInput.value.trim()) {
                    payload.prefix = prefixInput.value.trim();
                }
                if (domainSelect && domainSelect.value.trim() && !domainSelect.disabled) {
                    payload.domain = domainSelect.value.trim();
                }
                if (providerSelect && providerSelect.value.trim()) {
                    payload.provider_name = providerSelect.value.trim();
                }
                showToast(translateAppTextLocal('正在生成临时邮箱…'), 'info');
                const response = await fetch('/api/temp-emails/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (data.success) {
                    showToast(translateAppTextLocal('临时邮箱已生成: ' + data.email), 'success');
                    if (prefixInput) prefixInput.value = '';
                    invalidateAccountsCache('temp');
                    // BUG-06: 不调用 loadGroups()，因为 loadTempEmails 内部已更新分组徽章。
                    // loadGroups() 在 currentGroupId 为 null 时会触发 selectGroup()，
                    // 进而清空 currentAccount，导致当前选中临时邮箱被意外重置。
                    loadTempEmails(true);
                } else {
                    handleApiError(data, '生成临时邮箱失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('生成临时邮箱失败'), 'error');
            }
        }

        // 选择临时邮箱
        function selectTempEmail(email) {
            // BUG-05: 切换到临时邮箱前停止所有轮询，避免轮询把 currentAccount 误当作普通邮箱去拉取。
            if (typeof stopAllPolls === 'function') {
                stopAllPolls();
            }

            currentAccount = email;
            isTempEmailGroup = true;
            currentEmailDetail = null;
            isTrustedMode = false;

            // Update mailbox page bar (if visible)
            const bar = document.getElementById('currentAccountBar');
            if (bar) bar.style.display = '';
            const emailLabel = document.getElementById('currentAccountEmail');
            if (emailLabel) {
                emailLabel.textContent = email + ' (' + translateAppTextLocal('临时') + ')';
            }

            // Update active state on all account cards
            document.querySelectorAll('.account-card').forEach(item => {
                item.classList.remove('active');
                const emailEl = item.querySelector('.account-email');
                if (emailEl && emailEl.textContent.includes(email)) {
                    item.classList.add('active');
                }
            });

            // Update temp-emails independent page header
            const tempName = document.getElementById('tempEmailCurrentName');
            if (tempName) tempName.textContent = email;
            const tempRefreshBtn = document.getElementById('tempEmailRefreshBtn');
            if (tempRefreshBtn) {
                tempRefreshBtn.style.display = '';
                // Bind force-refresh here so HTML onclick can stay short / soft-safe.
                tempRefreshBtn.onclick = () => {
                    if (currentAccount && isTempEmailGroup) {
                        loadTempEmailMessages(currentAccount, true);
                    }
                };
            }

            // Hide folder tabs (temp emails don't support folders)
            const folderTabs = document.getElementById('folderTabs');
            if (folderTabs) folderTabs.style.display = 'none';

            // Show loading in message area (prefer temp-emails page container)
            const tempMsgList = document.getElementById('tempEmailMessageList');
            const emailList = document.getElementById('emailList');
            const loadingHTML = `<div class="empty-state"><span class="empty-icon">📬</span><p>${translateAppTextLocal('点击"获取邮件"按钮获取邮件')}</p></div>`;

            if (tempMsgList) tempMsgList.innerHTML = loadingHTML;
            if (emailList) {
                emailList.innerHTML = loadingHTML;
            }

            if (typeof resetEmailDetailState === 'function') {
                resetEmailDetailState({ source: 'temp' });
            }
            if (typeof setTempDetailFocus === 'function') {
                setTempDetailFocus(false);
            }
            if (typeof hideEmailDetailContainer === 'function') {
                hideEmailDetailContainer({ source: 'temp' });
            }
            const count = document.getElementById('emailCount');
            if (count) count.textContent = '';
            const tag = document.getElementById('methodTag');
            if (tag) tag.style.display = 'none';

            // Soft-load messages when warm; explicit refresh forces network.
            loadTempEmailMessages(email, false);
        }

        // 清空临时邮箱的所有邮件
        async function deleteTempEmail(email) {
            if (!confirm(`确定要删除临时邮箱 ${email} 吗？\n该邮箱的所有邮件也将被删除。`)) {
                return;
            }

            try {
                const response = await fetch(`/api/temp-emails/${encodeURIComponent(email)}`, {
                    method: 'DELETE'
                });

                const data = await response.json();

                if (data.success) {
                    showToast(translateAppTextLocal('临时邮箱已删除'), 'success');
                    invalidateAccountsCache('temp');
                    clearTempEmailMessagesCacheForMailbox(email);
                    // loadTempEmails(true) also invalidates unified directory; clear early so
                    // soft re-open cannot paint messages for the deleted mailbox.
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }

                    if (currentAccount === email) {
                        currentAccount = null;
                        currentEmails = [];
                        currentEmailDetail = null;
                        isTrustedMode = false;
                        const currentAccountBar = document.getElementById('currentAccountBar');
                        if (currentAccountBar) currentAccountBar.style.display = 'none';
                        const emptyMailboxHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📬</span><p>${translateAppTextLocal('请从左侧选择一个邮箱账号')}</p>
                            </div>
                        `;
                        const emailList = document.getElementById('emailList');
                        if (emailList) emailList.innerHTML = emptyMailboxHTML;
                        const tempMessageList = document.getElementById('tempEmailMessageList');
                        if (tempMessageList) {
                            tempMessageList.innerHTML = `
                                <div class="empty-state">
                                    <span class="empty-icon">📬</span>
                                    <p>${translateAppTextLocal('选择一个临时邮箱查看邮件')}</p>
                                </div>
                            `;
                        }
                        const tempName = document.getElementById('tempEmailCurrentName');
                        if (tempName) tempName.textContent = translateAppTextLocal('选择一个临时邮箱');
                        const tempRefreshBtn = document.getElementById('tempEmailRefreshBtn');
                        if (tempRefreshBtn) tempRefreshBtn.style.display = 'none';
                        if (typeof resetEmailDetailState === 'function') {
                            resetEmailDetailState({ source: 'temp' });
                        }
                    }

                    loadTempEmails(true);
                    // BUG-06: 同 generateTempEmail，不调用 loadGroups()，
                    // 避免 currentGroupId 为 null 时触发 selectGroup() 清空 currentAccount。
                } else {
                    handleApiError(data, '删除临时邮箱失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('删除失败'), 'error');
            }
        }

