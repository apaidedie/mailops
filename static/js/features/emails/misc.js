// split from emails.js → misc.js
        function resolveEmailSortTimestamp(email) {
            const rawDate = email && (email.receivedDateTime || email.date || email.created_at || email.received_at);
            const parsed = Date.parse(String(rawDate || ''));
            return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
        }

        function sortEmailsByNewestFirst(list) {
            const source = Array.isArray(list) ? list : [];
            return source
                .map((item, index) => ({ item, index, timestamp: resolveEmailSortTimestamp(item) }))
                .sort((a, b) => (b.timestamp - a.timestamp) || (a.index - b.index))
                .map(entry => entry.item);
        }

        if (typeof window !== 'undefined') {
            window.sortEmailsByNewestFirst = sortEmailsByNewestFirst;
        }

        // 加载邮件列表
        function getEmailListEmptyMessage() {
            // Folder-aware empty chrome so junk (and future folders) do not say "收件箱为空".
            const folder = String(
                (typeof currentFolder !== 'undefined' && currentFolder) ? currentFolder : 'inbox'
            ).trim().toLowerCase() || 'inbox';
            if (folder === 'junkemail' || folder === 'junk' || folder === 'spam') {
                return translateAppTextLocal('垃圾邮件为空');
            }
            if (folder !== 'inbox') {
                return translateAppTextLocal('暂无邮件');
            }
            return translateAppTextLocal('收件箱为空');
        }

        // Cold folder (no warm list cache yet): prompt user to fetch, not "inbox empty".
        function isTempEmailSource(source) {
            const normalizedSource = String(source || '').trim().toLowerCase();
            return normalizedSource === 'temp' || normalizedSource === 'temp-mail' || normalizedSource === 'temp_mail';
        }

        function resolveEmailDetailSource(options = {}) {
            if (isTempEmailSource(options?.source)) {
                return 'temp';
            }
            return isTempEmailGroup || currentPage === 'temp-emails' ? 'temp' : 'mailbox';
        }

        // detail-focus 断点阈值：低于此宽度时切换列表/详情为互斥模式
        // 注意: CSS 平板断点为 1024px，此处 900px 为功能切换阈值而非布局断点
        function isNarrowWorkspaceViewport() {
            return window.innerWidth <= 900;
        }

        // 邮箱列表/详情互斥切换 — 窄视口下点击邮件时隐藏列表、全宽展示详情
        // 被调用方: accounts.js(切换账户重置)、emails.js(点击邮件/返回列表)
        // CSS 配套: #emailListPanel.detail-focus 规则(平板+移动端)
        function setMailboxDetailFocus(active) {
            const panel = document.getElementById('emailListPanel');
            if (!panel) return;
            const shouldFocus = Boolean(active) && isNarrowWorkspaceViewport();
            panel.classList.toggle('detail-focus', shouldFocus);
            // 内联样式作为 CSS 的即时保障，避免布局闪烁
            const listEl = document.getElementById('emailList');
            const detailEl = document.getElementById('emailDetailSection');
            if (shouldFocus) {
                if (listEl) listEl.style.display = 'none';
                if (detailEl) detailEl.style.display = 'flex';
            } else if (isNarrowWorkspaceViewport()) {
                if (listEl) listEl.style.display = '';
                if (detailEl) detailEl.style.display = 'none';
            } else {
                // 桌面端：退回 CSS 控制，清除内联覆盖
                if (listEl) listEl.style.display = '';
                if (detailEl) detailEl.style.display = '';
            }
        }

        // 临时邮箱消息列表/详情互斥切换 — 与 setMailboxDetailFocus 对称设计
        // 被调用方: temp_emails.js(点击消息/刷新列表)、emails.js(切换回邮箱列表)
        // CSS 配套: .workspace.workspace-temp-emails.detail-focus 规则(平板+移动端)
        function setTempDetailFocus(active) {
            const workspace = document.querySelector('.workspace.workspace-temp-emails');
            const messagePanel = document.getElementById('tempEmailMessagePanel');
            const detailPanel = document.getElementById('tempEmailDetailSection');
            if (!workspace) return;

            const shouldFocus = Boolean(active) && isNarrowWorkspaceViewport();
            workspace.classList.toggle('detail-focus', shouldFocus);

            if (shouldFocus) {
                if (messagePanel) messagePanel.style.display = 'none';
                if (detailPanel) detailPanel.style.display = 'flex';
            } else if (isNarrowWorkspaceViewport()) {
                if (messagePanel) messagePanel.style.display = '';
                if (detailPanel) detailPanel.style.display = 'none';
            } else {
                if (messagePanel) messagePanel.style.display = '';
                if (detailPanel) detailPanel.style.display = '';
            }
        }

        function getEmailDetailRefs(options = {}) {
            const source = resolveEmailDetailSource(options);
            if (source === 'temp') {
                return {
                    source,
                    section: document.getElementById('tempEmailDetailSection'),
                    toolbar: document.getElementById('tempEmailDetailToolbar'),
                    container: document.getElementById('tempEmailDetail'),
                    trustCheckbox: document.getElementById('tempEmailTrustCheckbox'),
                    iframeId: 'tempEmailBodyFrame',
                };
            }

            return {
                source,
                section: document.getElementById('emailDetailSection'),
                toolbar: document.getElementById('emailDetailToolbar'),
                container: document.getElementById('emailDetail'),
                trustCheckbox: document.getElementById('trustEmailCheckbox'),
                iframeId: 'emailBodyFrame',
            };
        }

        function setEmailDetailToolbarVisibility(visible, options = {}) {
            const refs = getEmailDetailRefs(options);
            if (visible) {
                showEmailDetailContainer(options);
            }
            if (refs.toolbar) {
                refs.toolbar.style.display = visible ? 'flex' : 'none';
            }
        }

        function resetEmailDetailState(options = {}) {
            const refs = getEmailDetailRefs(options);
            if (refs.container) {
                refs.container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon">📄</span>
                        <p>${translateAppTextLocal('选择一封邮件查看详情')}</p>
                    </div>
                `;
            }
            if (refs.trustCheckbox) {
                refs.trustCheckbox.checked = false;
            }
            setEmailDetailToolbarVisibility(false, options);
        }

        function buildDetailVerificationOptions(options = {}) {
            return resolveEmailDetailSource(options) === 'temp'
                ? { ...options, source: 'temp' }
                : { ...options, source: 'mailbox' };
        }

        function extractVerificationFallbackFromDetail(options = {}) {
            const refs = getEmailDetailRefs(options);
            const iframe = refs.container ? refs.container.querySelector('.email-body-frame') : null;
            const textBody = refs.container ? refs.container.querySelector('.email-body-text') : null;

            let bodyText = '';
            if (iframe && iframe.contentDocument && iframe.contentDocument.body) {
                bodyText = iframe.contentDocument.body.innerText || iframe.contentDocument.body.textContent || '';
            } else if (textBody) {
                bodyText = textBody.textContent || '';
            }

            if (!bodyText.trim()) {
                return null;
            }

            const codePatterns = [
                /(?:验证码|verification code|code|码|PIN|OTP|密码)[：:\s]*([A-Za-z0-9]{4,8})/i,
                /\b(\d{4,8})\b/,
                /(?:code|码)[：:\s]*([A-Za-z0-9-]{4,12})/i,
            ];
            const urlPattern = /https?:\/\/[^\s<>"')\]]+/gi;
            const urls = bodyText.match(urlPattern) || [];
            const filteredUrls = urls.filter(u => !u.includes('unsubscribe') && !u.includes('privacy') && !u.includes('terms'));

            let code = '';
            for (const pattern of codePatterns) {
                const match = bodyText.match(pattern);
                if (match && match[1]) {
                    code = match[1];
                    break;
                }
            }

            let formatted = '';
            if (code) formatted += `验证码: ${code}`;
            if (filteredUrls.length > 0) {
                if (formatted) formatted += '\n';
                formatted += `链接: ${filteredUrls[0]}`;
            }

            if (!formatted) {
                return null;
            }

            return {
                verification_code: code,
                verification_link: filteredUrls[0] || '',
                formatted,
                copyText: code || filteredUrls[0] || formatted,
                displayValue: code || filteredUrls[0] || formatted,
            };
        }

        function normalizeEmailInlineResourceKey(value) {
            if (!value) return '';
            let normalized = String(value).trim();
            if (!normalized) return '';
            if (normalized.toLowerCase().startsWith('cid:')) {
                normalized = normalized.slice(4);
            }
            if (normalized.startsWith('<') && normalized.endsWith('>')) {
                normalized = normalized.slice(1, -1);
            }
            return normalized.trim().toLowerCase();
        }

        function resolveEmailInlineResource(resourceMap, reference) {
            if (!resourceMap || typeof resourceMap !== 'object') return '';
            const normalizedKey = normalizeEmailInlineResourceKey(reference);
            if (!normalizedKey) return '';
            return resourceMap[normalizedKey] || '';
        }

        function rewriteEmailInlineImages(html, email) {
            const sourceHtml = typeof html === 'string' ? html : '';
            const resourceMap = email && email.inline_resources && typeof email.inline_resources === 'object'
                ? email.inline_resources
                : null;

            if (!sourceHtml || !resourceMap || Object.keys(resourceMap).length === 0 || typeof DOMParser === 'undefined') {
                return sourceHtml;
            }

            try {
                const parser = new DOMParser();
                const doc = parser.parseFromString(sourceHtml, 'text/html');
                const images = doc.querySelectorAll('img[src]');

                images.forEach(img => {
                    const originalSrc = img.getAttribute('src') || '';
                    if (!/^cid:/i.test(originalSrc)) return;
                    const resolvedSrc = resolveEmailInlineResource(resourceMap, originalSrc);
                    if (resolvedSrc) {
                        img.setAttribute('src', resolvedSrc);
                    }
                });

                return doc.body ? doc.body.innerHTML : sourceHtml;
            } catch (error) {
                console.warn('重写邮件内联图片失败:', error);
                return sourceHtml;
            }
        }

        function adjustIframeHeight(iframe) {
            try {
                // 多次尝试调整高度，确保内容完全加载
                const adjustHeight = () => {
                    if (iframe.contentDocument && iframe.contentDocument.body) {
                        const body = iframe.contentDocument.body;
                        const html = iframe.contentDocument.documentElement;
                        // 获取实际内容高度（取最大值）
                        const height = Math.max(
                            body.scrollHeight,
                            body.offsetHeight,
                            html.clientHeight,
                            html.scrollHeight,
                            html.offsetHeight
                        );
                        // 设置最小高度为 600px，添加 100px 余量确保长邮件能完整显示
                        iframe.style.height = Math.max(height + 100, 600) + 'px';
                    }
                };

                // 立即调整一次
                adjustHeight();
                // 100ms 后再调整（等待图片等资源加载）
                setTimeout(adjustHeight, 100);
                // 300ms 后再调整
                setTimeout(adjustHeight, 300);
                // 500ms 后再调整（确保所有内容都已加载）
                setTimeout(adjustHeight, 500);
                // 1秒后最后调整一次
                setTimeout(adjustHeight, 1000);
                // 2秒后再次调整（处理延迟加载的内容）
                setTimeout(adjustHeight, 2000);

                // 监听 iframe 内容变化
                if (iframe.contentDocument) {
                    const observer = new MutationObserver(adjustHeight);
                    observer.observe(iframe.contentDocument.body, {
                        childList: true,
                        subtree: true,
                        attributes: true
                    });

                    // 监听图片加载完成事件
                    const images = iframe.contentDocument.querySelectorAll('img');
                    images.forEach(img => {
                        img.addEventListener('load', adjustHeight);
                        img.addEventListener('error', adjustHeight);
                    });
                }
            } catch (e) {
                // Cross-origin or sandboxed email content can block iframe measurement.
            }
        }

        // 同步邮件列表可见性（新布局简化版）
        function syncEmailListVisibility(visible) {
            // New layout doesn't use the old panel collapse system - no-op
        }

        // 切换邮件列表显示
        function toggleEmailList() {
            const toggleText = document.getElementById('toggleListText');

            isListVisible = !isListVisible;

            if (isListVisible) {
                syncEmailListVisibility(true);
                toggleText.textContent = translateAppTextLocal('隐藏列表');
            } else {
                syncEmailListVisibility(false);
                toggleText.textContent = translateAppTextLocal('显示列表');
            }
        }

        // ==================== 验证码提取（从邮件详情） ====================

        async function extractVerificationFromDetail(buttonElement) {
            if (!currentAccount || typeof copyVerificationInfo !== 'function') {
                showToast(translateAppTextLocal('请先选择一个邮箱账号'), 'error');
                return false;
            }

            const detailOptions = buildDetailVerificationOptions();
            return copyVerificationInfo(currentAccount, buttonElement, {
                ...detailOptions,
                fallbackExtractor: () => extractVerificationFallbackFromDetail(detailOptions),
            });
        }

        // 全屏查看邮件
        let currentFullscreenEmail = null;

        function toggleTrustMode(checkbox) {
            if (checkbox.checked) {
                if (confirm('⚠️ 警告：启用信任模式将直接显示邮件原始内容，不进行任何安全过滤。\n\n这可能包含恶意脚本或不安全的内容。您确定要继续吗？')) {
                    isTrustedMode = true;
                    if (currentEmailDetail) {
                        renderEmailDetail(currentEmailDetail);
                    }
                } else {
                    checkbox.checked = false;
                }
            } else {
                isTrustedMode = false;
                if (currentEmailDetail) {
                    renderEmailDetail(currentEmailDetail);
                }
            }
        }

        function adjustFullscreenIframeHeight(iframe) {
            try {
                const adjustHeight = () => {
                    if (iframe.contentDocument && iframe.contentDocument.body) {
                        const body = iframe.contentDocument.body;
                        const html = iframe.contentDocument.documentElement;
                        const height = Math.max(
                            body.scrollHeight,
                            body.offsetHeight,
                            html.clientHeight,
                            html.scrollHeight,
                            html.offsetHeight
                        );
                        // 全屏模式下设置实际高度，添加余量
                        iframe.style.height = (height + 100) + 'px';
                    }
                };

                // 多次调整高度
                adjustHeight();
                setTimeout(adjustHeight, 100);
                setTimeout(adjustHeight, 300);
                setTimeout(adjustHeight, 500);
                setTimeout(adjustHeight, 1000);

                // 监听内容变化
                if (iframe.contentDocument) {
                    const observer = new MutationObserver(adjustHeight);
                    observer.observe(iframe.contentDocument.body, {
                        childList: true,
                        subtree: true,
                        attributes: true
                    });

                    // 监听图片加载
                    const images = iframe.contentDocument.querySelectorAll('img');
                    images.forEach(img => {
                        img.addEventListener('load', adjustHeight);
                        img.addEventListener('error', adjustHeight);
                    });
                }
            } catch (e) {
                // Cross-origin or sandboxed email content can block iframe measurement.
            }
        }

        // 显示邮件列表（移动端）
        function refreshEmails() {
            if (currentAccount) {
                if (isTempEmailGroup) {
                    // Explicit refresh must force network for temp mailboxes.
                    loadTempEmailMessages(currentAccount, true);
                } else {
                    // 清除当前缓存并强制刷新
                    clearEmailListCacheForMailbox(currentAccount, currentFolder);
                    loadEmails(currentAccount, true);
                }
            } else {
                showToast(translateAppTextLocal('请先选择一个邮箱账号'), 'error');
            }
        }

        // 复制邮箱地址
        async function copyEmail(email) {
            try {
                if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
                    await navigator.clipboard.writeText(email);
                    showToast(translateAppTextLocal('邮箱地址已复制'), 'success');
                    // 派发 email-copied 事件到 window，供简洁模式轮询引擎监听
                    window.dispatchEvent(new CustomEvent('email-copied', { detail: { email } }));
                    return true;
                }

                const textarea = document.createElement('textarea');
                textarea.value = email;
                textarea.setAttribute('readonly', 'readonly');
                textarea.style.position = 'fixed';
                textarea.style.top = '-9999px';
                textarea.style.left = '-9999px';

                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();

                const copied = document.execCommand('copy');
                document.body.removeChild(textarea);

                if (!copied) {
                    throw new Error('document.execCommand(copy) returned false');
                }

                showToast(translateAppTextLocal('邮箱地址已复制'), 'success');
                // 派发 email-copied 事件到 window，供简洁模式轮询引擎监听
                window.dispatchEvent(new CustomEvent('email-copied', { detail: { email } }));
                return true;
            } catch (error) {
                console.error('复制邮箱地址失败:', error);
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
                return false;
            }
        }

        // 复制当前邮箱
        function copyCurrentEmail() {
            const emailElement = document.getElementById('currentAccountEmail');
            if (emailElement && emailElement.textContent) {
                const email = emailElement.textContent.replace(/\s+\((临时|Temp)\)$/, '').trim();
                copyEmail(email);
            }
        }

        // 退出登录
        function logout() {
            if (confirm('确定要退出登录吗？')) {
                window.location.href = '/logout';
            }
        }

        // Soft re-paint open mailbox email list/detail chrome after language change (no network).
        window.addEventListener('ui-language-changed', () => {
            try {
                // Soft re-paint open list without network.
                // Distinguish warm empty folder ("收件箱为空") from cold "click to fetch" prompt.
                if (Array.isArray(currentEmails) && typeof renderEmailList === 'function') {
                    const listEl = document.getElementById('emailList');
                    if (listEl) {
                        if (currentEmails.length > 0) {
                            renderEmailList(currentEmails, { scrollToTop: false });
                        } else if (listEl.querySelector('.empty-state')) {
                            const cacheKey = `${currentAccount}_${currentFolder}`;
                            const warm = emailListCache && emailListCache[cacheKey];
                            if (warm) {
                                renderEmailList(currentEmails, { scrollToTop: false });
                            } else if (currentAccount) {
                                paintEmailListColdFetchPrompt(currentFolder);
                            }
                        }
                    }
                }
            } catch (e) {}
            try {
                if (currentEmailDetail && typeof renderEmailDetail === 'function') {
                    renderEmailDetail(currentEmailDetail, { source: isTempEmailGroup ? 'temp' : 'mailbox' });
                }
            } catch (e) {}
            try {
                if (typeof updateEmailBatchActionBar === 'function') {
                    updateEmailBatchActionBar();
                }
            } catch (e) {}
        });
