// Extracted from main.js lines 6726-7534 (W3 frontend split)
        // ==================== CSRF 防护 ====================

        function isMutationRequest(method) {
            const normalizedMethod = (method || 'GET').toUpperCase();
            return !['GET', 'HEAD', 'OPTIONS'].includes(normalizedMethod);
        }

        function cloneHeaders(headers) {
            return new Headers(headers || {});
        }

        function buildFetchRequest(input, options = {}) {
            if (input instanceof Request) {
                const mergedHeaders = cloneHeaders(input.headers);
                const optionHeaders = cloneHeaders(options.headers);
                optionHeaders.forEach((value, key) => mergedHeaders.set(key, value));

                const requestOptions = {
                    ...options,
                    headers: mergedHeaders
                };

                return {
                    method: (requestOptions.method || input.method || 'GET').toUpperCase(),
                    setHeader(name, value) {
                        mergedHeaders.set(name, value);
                    },
                    execute() {
                        return originalFetch(new Request(input, requestOptions));
                    }
                };
            }

            const requestOptions = {
                ...options,
                headers: cloneHeaders(options.headers)
            };

            return {
                method: (requestOptions.method || 'GET').toUpperCase(),
                setHeader(name, value) {
                    requestOptions.headers.set(name, value);
                },
                execute() {
                    return originalFetch(input, requestOptions);
                }
            };
        }

        async function parseJsonSafely(response) {
            const contentType = response.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                return null;
            }

            try {
                return await response.clone().json();
            } catch (error) {
                return null;
            }
        }

        function isCsrfFailurePayload(payload) {
            if (!payload || typeof payload !== 'object') {
                return false;
            }

            const error = payload.error && typeof payload.error === 'object' ? payload.error : payload;
            return error.code === 'CSRF_TOKEN_INVALID';
        }

        // 初始化 CSRF Token
        async function initCSRFToken({ force = false, silent = false } = {}) {
            if (!force && csrfToken) {
                return csrfToken;
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so CSRF recovery always starts a true network GET.
            // Concurrent soft mutation attaches share one pull; CSRF_TOKEN_INVALID recovery
            // uses force:true and must not wait on a soft pull that may already be stale.
            if (csrfTokenRefreshPromise) {
                if (!force || csrfTokenRefreshForce) {
                    return csrfTokenRefreshPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                csrfTokenRefreshPromise = null;
                csrfTokenRefreshForce = false;
            }

            csrfTokenRefreshForce = Boolean(force);
            const request = (async () => {
                try {
                    const response = await originalFetch('/api/csrf-token');
                    if (!response.ok) {
                        throw new Error(`csrf_token_http_${response.status}`);
                    }

                    const data = await response.json();
                    if (csrfTokenRefreshPromise !== request) {
                        return csrfToken;
                    }
                    if (data.csrf_disabled) {
                        csrfToken = null;
                        console.warn('CSRF protection is disabled. Install flask-wtf for better security.');
                        return csrfToken;
                    }

                    if (!data.csrf_token) {
                        throw new Error('csrf_token_missing_in_response');
                    }

                    csrfToken = data.csrf_token;
                    return csrfToken;
                } catch (error) {
                    if (csrfTokenRefreshPromise !== request) {
                        return csrfToken;
                    }
                    if (!silent) {
                        showToast(translateAppTextLocal('初始化安全会话失败，请刷新页面后重试'), 'error');
                    }
                    console.error('Failed to initialize CSRF token:', error);
                    throw error;
                } finally {
                    if (csrfTokenRefreshPromise === request) {
                        csrfTokenRefreshPromise = null;
                        csrfTokenRefreshForce = false;
                    }
                }
            })();

            csrfTokenRefreshPromise = request;
            return request;
        }

        // 包装 fetch 请求，自动添加 CSRF Token
        const originalFetch = window.fetch;
        window.fetch = async function (input, options = {}) {
            const request = buildFetchRequest(input, options);
            const shouldAttachCsrf = isMutationRequest(request.method);

            if (shouldAttachCsrf && !csrfToken) {
                try {
                    await initCSRFToken({ silent: true });
                } catch (error) {
                    // 让原请求继续发出，由后端返回明确的 CSRF 错误提示
                }
            }

            if (shouldAttachCsrf && csrfToken) {
                request.setHeader('X-CSRFToken', csrfToken);
            }

            const response = await request.execute();
            if (!shouldAttachCsrf || options.__skipCsrfRetry || response.status !== 400) {
                return response;
            }

            const payload = await parseJsonSafely(response);
            if (!isCsrfFailurePayload(payload)) {
                return response;
            }

            try {
                await initCSRFToken({ force: true, silent: true });
            } catch (error) {
                return response;
            }

            if (!csrfToken) {
                return response;
            }

            const retryRequest = buildFetchRequest(input, {
                ...options,
                __skipCsrfRetry: true
            });
            retryRequest.setHeader('X-CSRFToken', csrfToken);
            return retryRequest.execute();
        };

        // Defer browser Notification permission until after boot settle.
        // Prefer a real user gesture; idle fallback only if still default.
        let browserNotificationPermissionScheduled = false;
        function scheduleBrowserNotificationPermissionPrompt() {
            if (browserNotificationPermissionScheduled) return;
            if (!('Notification' in window)) return;
            if (Notification.permission !== 'default') return;
            browserNotificationPermissionScheduled = true;

            const requestOnce = () => {
                if (!('Notification' in window) || Notification.permission !== 'default') return;
                try {
                    Notification.requestPermission();
                } catch (_error) {
                    /* permission prompt may be blocked; ignore */
                }
            };

            const onFirstGesture = () => {
                window.removeEventListener('pointerdown', onFirstGesture, true);
                window.removeEventListener('keydown', onFirstGesture, true);
                requestOnce();
            };
            window.addEventListener('pointerdown', onFirstGesture, true);
            window.addEventListener('keydown', onFirstGesture, true);

            // Late fallback if the operator never interacts (e.g. kiosk dashboard).
            // Far after boot so it does not compete with catalog/overview/sync worker.
            setTimeout(() => {
                window.removeEventListener('pointerdown', onFirstGesture, true);
                window.removeEventListener('keydown', onFirstGesture, true);
                requestOnce();
            }, 30000);
        }

        // 初始化
        document.addEventListener('DOMContentLoaded', async function () {
            // 应用保存的主题
            applyTheme(localStorage.getItem('ol_theme') || 'light');

            // 初始化 CSRF Token。失败时不阻断首屏，其它初始化继续执行，
            // 具体的写请求再走按需恢复逻辑。
            try {
                await initCSRFToken();
            } catch (error) {}

            // 初始化布局状态（从后端读取或迁移旧 localStorage）
            await initLayoutState();
            renderDemoWorkspaceStrip();

            closeAllModals();
            // Defer mailbox groups/tags until mailbox (or tag modal) needs them.
            // Dashboard-first boot must not compete for /api/groups + /api/tags
            // against overview + provider catalog on the shared sync worker.
            // navigate('mailbox') loads groups when empty; showTagManagementModal loads tags.
            initColorPicker();
            initEmailListScroll();
            initResizeHandles();
            handleResponsiveGroups();

            // 初始化轮询设置
            initPollingSettings();

            // Settings-only boot work is deferred to showSettingsModal:
            // - temp-mail provider radios (bind + render)
            // - update-method config toggles (bind + initial visibility)
            // Catalog preload still soft-loads /api/providers for labels/filters without
            // rewriting the hidden Settings mount on every page boot.

            // Preload secret-free provider catalog so account tags / import / pool
            // filters can resolve labels without waiting for Settings navigation.
            if (typeof loadMailboxProviderCatalog === 'function') {
                loadMailboxProviderCatalog(false);
            }

            // Browser notification permission is deferred until first user gesture
            // (and a late idle fallback). Do not prompt during critical boot.
            if (typeof scheduleBrowserNotificationPermissionPrompt === 'function') {
                scheduleBrowserNotificationPermissionPrompt();
            }

            // 绑定搜索框事件
            const searchInput = document.getElementById('globalSearch');
            if (searchInput) {
                const debouncedSearch = debounce((e) => {
                    searchAccounts(e.target.value);
                }, 300);
                searchInput.addEventListener('input', debouncedSearch);
            }

            // 加载数据概览
            if (typeof initOverview === 'function') initOverview();

            // 检查是否有版本更新（延迟 5 秒触发，避免首屏抢占唯一 sync worker）
            setTimeout(checkVersionUpdate, 5000);
        });

        // 初始化颜色选择器
        function initColorPicker() {
            document.querySelectorAll('.color-option').forEach(option => {
                option.addEventListener('click', function () {
                    document.querySelectorAll('.color-option').forEach(o => o.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedColor = this.dataset.color;
                    // 同步更新自定义颜色输入框
                    document.getElementById('customColorInput').value = selectedColor;
                    document.getElementById('customColorHex').value = selectedColor;
                });
            });
        }

        // 初始化邮件列表滚动监听
        function initEmailListScroll() {
            const emailList = document.getElementById('emailList');
            emailList.addEventListener('scroll', function () {
                // 检查是否滚动到底部
                if (emailList.scrollHeight - emailList.scrollTop <= emailList.clientHeight + 50) {
                    if (!isLoadingMore && hasMoreEmails && currentAccount && !isTempEmailGroup) {
                        loadMoreEmails();
                    }
                }
            });
        }

        // 加载更多邮件
        async function loadMoreEmails() {
            if (isLoadingMore || !hasMoreEmails) return;
            // Capture mailbox/folder/method/skip at request start so rapid switches cannot
            // merge a page into the wrong live list or paint stale "load more" chrome.
            const targetEmail = String(currentAccount || '').trim();
            const targetFolder = String(currentFolder || 'inbox').trim().toLowerCase() || 'inbox';
            const targetMethod = currentMethod;
            if (!targetEmail || isTempEmailGroup) return;

            const baselineEmails = Array.isArray(currentEmails) ? currentEmails.slice() : [];
            const requestSkip = (Number(currentSkip) || 0) + 20;
            const cacheKey = `${targetEmail}_${targetFolder}`;
            const isCurrentEmailListView = () => (
                String(currentAccount || '').trim() === targetEmail
                && String(currentFolder || 'inbox').trim().toLowerCase() === targetFolder
                && !isTempEmailGroup
            );

            isLoadingMore = true;
            // Advance live skip only while still on this mailbox+folder.
            if (isCurrentEmailListView()) {
                currentSkip = requestSkip;
            }

            const paintLoadingChrome = isCurrentEmailListView();
            const emailList = document.getElementById('emailList');
            // 禁用按钮
            const refreshBtn = document.querySelector('.refresh-btn');
            const folderTabs = document.querySelectorAll('.email-tab');
            if (paintLoadingChrome) {
                // 在列表底部显示加载状态
                if (emailList) {
                    const loadingDiv = document.createElement('div');
                    loadingDiv.className = 'loading-overlay';
                    loadingDiv.id = 'loadingMore';
                    loadingDiv.innerHTML = `<span class="spinner"></span> ${translateAppTextLocal('加载更多…')}`;
                    emailList.appendChild(loadingDiv);
                }
                if (refreshBtn) {
                    refreshBtn.disabled = true;
                }
                folderTabs.forEach(tab => tab.disabled = true);
            }

            try {
                const response = await fetch(
                    `/api/emails/${encodeURIComponent(targetEmail)}?method=${encodeURIComponent(targetMethod || 'graph')}&folder=${encodeURIComponent(targetFolder)}&skip=${requestSkip}&top=20`
                );
                const data = await response.json();

                if (data.success && data.emails && data.emails.length > 0) {
                    // Merge against the baseline captured for this request (not live currentEmails).
                    const mergedEmails = (typeof sortEmailsByNewestFirst === 'function')
                        ? sortEmailsByNewestFirst(baselineEmails.concat(data.emails || []))
                        : baselineEmails.concat(data.emails || []);
                    const nextHasMore = Boolean(data.has_more);
                    const nextMethod = data.method || targetMethod;

                    // Soft-load: always upsert list cache for the requested mailbox+folder
                    // so re-select keeps paginated pages even if the user navigated away.
                    emailListCache[cacheKey] = {
                        emails: mergedEmails,
                        has_more: nextHasMore,
                        skip: requestSkip,
                        method: nextMethod
                    };

                    // Paint live list only while still on this mailbox+folder.
                    if (isCurrentEmailListView()) {
                        currentEmails = mergedEmails;
                        hasMoreEmails = nextHasMore;
                        currentSkip = requestSkip;
                        if (nextMethod) currentMethod = nextMethod;

                        const loadingEl = document.getElementById('loadingMore');
                        if (loadingEl) loadingEl.remove();

                        renderEmailList(currentEmails, { scrollToTop: false });

                        const emailCountEl = document.getElementById('emailCount');
                        if (emailCountEl) {
                            emailCountEl.textContent = `(${currentEmails.length})`;
                        }
                    }
                } else {
                    // Exhausted page: warm cache has_more=false for this key when possible.
                    if (emailListCache[cacheKey]) {
                        emailListCache[cacheKey] = {
                            ...emailListCache[cacheKey],
                            has_more: false,
                            skip: requestSkip,
                            method: emailListCache[cacheKey].method || targetMethod
                        };
                    }
                    if (isCurrentEmailListView()) {
                        hasMoreEmails = false;
                        // 显示"没有更多邮件"
                        const loadingEl = document.getElementById('loadingMore');
                        if (loadingEl) {
                            loadingEl.innerHTML = `<div style="text-align:center;padding:20px;color:#999;font-size:13px;">${translateAppTextLocal('没有更多邮件了')}</div>`;
                        }
                    }
                }
            } catch (error) {
                if (isCurrentEmailListView()) {
                    const loadingEl = document.getElementById('loadingMore');
                    if (loadingEl) loadingEl.remove();
                    showToast(translateAppTextLocal('加载失败'), 'error');
                }
            } finally {
                isLoadingMore = false;
                // 启用按钮（only if we disabled them for this view）
                if (paintLoadingChrome) {
                    if (refreshBtn) {
                        refreshBtn.disabled = false;
                    }
                    folderTabs.forEach(tab => tab.disabled = false);
                }
            }
        }

        // 切换文件夹（不触发查询）
        function switchFolder(folder) {
            if (currentFolder === folder) return;

            currentFolder = folder;

            // 更新按钮状态
            document.querySelectorAll('.email-tab').forEach(tab => {
                tab.classList.toggle('active', tab.dataset.folder === folder);
            });

            const cacheKey = `${currentAccount}_${folder}`;

            // 检查是否有缓存
            if (emailListCache[cacheKey]) {
                const cache = emailListCache[cacheKey];
                currentEmails = (typeof sortEmailsByNewestFirst === 'function')
                    ? sortEmailsByNewestFirst(cache.emails || [])
                    : (cache.emails || []);
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
            } else {
                // 清空邮件列表，显示提示（cold folder: fetch prompt, not "inbox empty").
                if (typeof window.paintEmailListColdFetchPrompt === 'function') {
                    window.paintEmailListColdFetchPrompt(folder);
                } else {
                    document.getElementById('emailList').innerHTML = `
                        <div class="empty-state">
                            <span class="empty-icon">📬</span>
                            <p>${translateAppTextLocal(folder === 'inbox' ? '点击"获取邮件"按钮获取收件箱' : '点击"获取邮件"按钮获取垃圾邮件')}</p>
                        </div>
                    `;
                }
                document.getElementById('emailCount').textContent = '';
                document.getElementById('methodTag').style.display = 'none';

                // 重置分页状态
                currentEmails = [];
                currentSkip = 0;
                hasMoreEmails = true;
            }
        }

        // 选择自定义颜色（颜色选择器）
        function selectCustomColor(color) {
            selectedColor = color;
            document.getElementById('customColorHex').value = color;
            // 取消预设颜色的选中状态
            document.querySelectorAll('.color-option').forEach(o => o.classList.remove('selected'));
        }

        // 选择自定义颜色（十六进制输入）
        function selectCustomColorHex(value) {
            // 验证十六进制颜色格式
            const hexPattern = /^#[0-9A-Fa-f]{6}$/;
            if (hexPattern.test(value)) {
                selectedColor = value;
                document.getElementById('customColorInput').value = value;
                // 取消预设颜色的选中状态
                document.querySelectorAll('.color-option').forEach(o => o.classList.remove('selected'));
            } else {
                showToast(translateAppTextLocal('请输入有效的十六进制颜色（如 #FF5500）'), 'error');
            }
        }

        // 显示消息提示
        function showToast(message, type = 'info', errorDetail = null, persistent = false) {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.setAttribute('aria-live', 'polite');
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            toast.className = 'toast ' + type;

            const messageSpan = document.createElement('span');
            messageSpan.textContent = translateAppTextLocal(message);
            toast.appendChild(messageSpan);

            if (errorDetail && type === 'error') {
                const detailLink = document.createElement('a');
                detailLink.href = 'javascript:void(0)';
                detailLink.textContent = ' ' + translateAppTextLocal('[详情]');
                detailLink.style.cssText = 'color:var(--clr-danger);text-decoration:underline;margin-left:8px;';
                detailLink.onclick = function (e) {
                    e.stopPropagation();
                    showErrorDetailModal(errorDetail);
                };
                toast.appendChild(detailLink);
            }

            container.appendChild(toast);

            if (persistent) {
                // persistent 模式：追加关闭按钮，不自动消失
                const closeBtn = document.createElement('button');
                closeBtn.textContent = '×';
                closeBtn.style.cssText = 'background:none;border:none;color:inherit;cursor:pointer;margin-left:12px;font-size:1.1rem;opacity:0.8;';
                closeBtn.onclick = () => {
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 300);
                };
                toast.appendChild(closeBtn);
            } else {
                const duration = (errorDetail && type === 'error') ? 8000 : 3000;
                setTimeout(() => {
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateX(30px)';
                    setTimeout(() => toast.remove(), 300);
                }, duration);
            }
        }

        function buildRefreshErrorSuggestions({ accountType, provider, errorMessage }) {
            const language = getUiLanguage();
            const normalizedAccountType = String(accountType || 'outlook').trim().toLowerCase();
            const normalizedProvider = String(provider || 'outlook').trim().toLowerCase();
            const normalizedErrorMessage = String(errorMessage || '').trim();
            const looksLikeTokenRefreshError = /aadsts|refresh[_\s-]?token|invalid[_\s-]?grant|expired/i.test(normalizedErrorMessage);

            if (normalizedAccountType === 'imap') {
                if (normalizedProvider === 'gmail') {
                    return language === 'en'
                        ? [
                            'Confirm IMAP is enabled and use an app password instead of your normal account password.',
                            'If this looks like an old Outlook token-refresh error, switch the account to IMAP credentials and save again.',
                            'Re-check the IMAP host, port, and SSL settings before retrying.',
                        ]
                        : [
                            '请确认 Gmail 已开启 IMAP，并使用应用专用密码而不是普通登录密码。',
                            '如果这里其实是旧的 Outlook token-refresh error，请把账号切回 IMAP 凭据后重新保存。',
                            '请重新检查 IMAP 主机、端口和 SSL 配置后再重试。',
                        ];
                }

                return language === 'en'
                    ? [
                        'Check the IMAP host, port, SSL/TLS, and account password settings.',
                        'Confirm the mailbox provider allows IMAP login from third-party apps.',
                        'If this error came from a migrated Outlook account, remove the old token-refresh settings and save the IMAP credentials again.',
                    ]
                    : [
                        '请检查 IMAP 主机、端口、SSL/TLS 和账号密码配置是否正确。',
                        '请确认当前邮箱服务商允许第三方客户端通过 IMAP 登录。',
                        '如果这是从旧 Outlook 账号迁移过来的异常，请清理旧的刷新 Token 配置并重新保存 IMAP 凭据。',
                    ];
            }

            if (looksLikeTokenRefreshError) {
                return language === 'en'
                    ? [
                        'Check whether the Client ID and Refresh Token are complete and do not contain extra spaces.',
                        'Use the "Get Refresh Token" flow again to generate a fresh authorization token.',
                        'Confirm the Microsoft account or tenant permissions have not been revoked or expired.',
                    ]
                    : [
                        '请检查 Client ID 和 Refresh Token 是否填写完整且没有多余空格。',
                        '请重新使用“获取 Refresh Token”功能生成新的授权凭据。',
                        '请确认 Microsoft 账号权限未被撤销，且租户策略没有使当前 Token 失效。',
                    ];
            }

            return language === 'en'
                ? [
                    'Open the account editor and verify the saved Outlook authorization information.',
                    'Retry the refresh after confirming network, proxy, and Microsoft service availability.',
                    'If the problem persists, re-authorize the account to obtain a new Refresh Token.',
                ]
                : [
                    '请打开账号编辑弹窗，确认当前保存的 Outlook 授权信息仍然有效。',
                    '请检查网络、代理和 Microsoft 服务状态后再次尝试刷新。',
                    '如果问题持续存在，请重新授权该账号并获取新的 Refresh Token。',
                ];
        }

        // 显示刷新错误信息
        function showRefreshError(accountId, errorMessage, accountEmail, accountType = 'outlook', provider = 'outlook') {
            document.getElementById('refreshErrorModal').classList.add('show');
            document.getElementById('refreshErrorEmail').textContent = translateAppTextLocal(`账号：${accountEmail || '未知'}`);
            document.getElementById('refreshErrorMessage').textContent = translateAppTextLocal(errorMessage);
            const suggestionsEl = document.getElementById('refreshErrorSuggestions');
            const suggestions = buildRefreshErrorSuggestions({ accountType, provider, errorMessage });
            if (suggestionsEl) {
                suggestionsEl.innerHTML = suggestions.map(item => `<li>${escapeHtml(item)}</li>`).join('');
            }
            document.getElementById('editAccountFromErrorBtn').onclick = function () {
                hideRefreshErrorModal();
                showEditAccountModal(accountId);
            };
        }

        // 隐藏刷新错误模态框
        function hideRefreshErrorModal() {
            document.getElementById('refreshErrorModal').classList.remove('show');
        }

        // ==================== 统一错误处理相关 ====================

        // 显示统一错误详情模态框
        function showErrorDetailModal(error) {
            document.getElementById('errorDetailModal').classList.add('show');
            document.getElementById('errorModalUserMessage').textContent = window.resolveApiErrorMessage
                ? window.resolveApiErrorMessage(error, '发生未知错误', 'Unknown error')
                : (error.message || '发生未知错误');
            document.getElementById('errorModalCode').textContent = error.code || '-';
            document.getElementById('errorModalType').textContent = error.type || '-';
            document.getElementById('errorModalStatus').textContent = error.status || '-';
            document.getElementById('errorModalTraceId').textContent = error.trace_id || '-';

            const detailsEl = document.getElementById('errorModalDetails');
            const detailsContainer = document.getElementById('errorModalDetailsContainer');
            const toggleBtn = document.getElementById('toggleTraceBtn');

            detailsEl.textContent = error.details || translateAppTextLocal('暂无详细技术堆栈信息');

            // 重置堆栈显示状态
            detailsContainer.style.display = 'none';
            toggleBtn.textContent = translateAppTextLocal('显示堆栈/细节');
        }

        // 隐藏统一错误详情模态框
        function hideErrorDetailModal() {
            document.getElementById('errorDetailModal').classList.remove('show');
        }

        // 邮件获取失败详情弹框
        function showEmailFetchErrorModal(details) {
            if (!details) return;

            const methodNames = {
                'graph': 'Graph API',
                'imap_new': 'IMAP（新服务器）',
                'imap_old': 'IMAP（旧服务器）'
            };

            function translateError(err) {
                if (!err) return '未知错误';
                // err 可能是 string 或 object
                if (typeof err === 'string') return err;

                const code = err.code || '';
                const details = typeof err.details === 'string' ? err.details : JSON.stringify(err.details || '');
                const msg = err.message || '';

                // 翻译常见错误
                if (code === 'GRAPH_TOKEN_EXCEPTION' && details.includes('ProxyError')) {
                    return '代理连接失败：无法连接到代理服务器，请检查代理地址是否正确以及代理是否在运行';
                }
                if (code === 'GRAPH_TOKEN_FAILED' || code === 'IMAP_TOKEN_FAILED') {
                    if (details.includes('invalid_grant')) {
                        return 'Token 已失效或权限不足：请重新授权登录或更换 refresh_token';
                    }
                    if (details.includes('invalid_client')) {
                        return 'Client ID 无效：请检查 client_id 配置是否正确';
                    }
                    return `令牌获取失败：${msg}`;
                }
                if (code === 'EMAIL_FETCH_FAILED') {
                    return `获取邮件失败：${msg}`;
                }
                if (code === 'IMAP_CONNECTION_FAILED') {
                    return 'IMAP 连接失败：无法连接到邮件服务器';
                }
                return msg || details || '未知错误';
            }

            let html = '';
            const methods = ['graph', 'imap_new', 'imap_old'];
            methods.forEach(method => {
                const err = details[method];
                if (err !== undefined) {
                    const name = methodNames[method] || method;
                    const reason = translateError(err);
                    const codeText = (err && typeof err === 'object') ? (err.code || '-') : '-';
                    html += `
                        <div style="background: #fff5f5; border: 1px solid #fde2e2; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
                            <div style="font-weight: 600; color: #dc3545; margin-bottom: 6px; font-size: 14px;">${name}</div>
                            <div style="color: #333; font-size: 13px; line-height: 1.6;">${reason}</div>
                            <div style="color: #999; font-size: 12px; margin-top: 4px;">错误代码: ${codeText}</div>
                        </div>
                    `;
                }
            });

            if (!html) {
                html = '<div style="color:#666;">无详细错误信息</div>';
            }

            document.getElementById('emailFetchErrorContent').innerHTML = html;
            document.getElementById('emailFetchErrorModal').classList.add('show');
        }

        function hideEmailFetchErrorModal() {
            document.getElementById('emailFetchErrorModal').classList.remove('show');
        }

        // 切换堆栈信息的显示/隐藏
        function toggleStackTrace() {
            const container = document.getElementById('errorModalDetailsContainer');
            const btn = document.getElementById('toggleTraceBtn');

            if (container.style.display === 'none') {
                container.style.display = 'block';
                btn.textContent = translateAppTextLocal('隐藏堆栈/细节');
            } else {
                container.style.display = 'none';
                btn.textContent = translateAppTextLocal('显示堆栈/细节');
            }
        }

        // 复制错误详情到剪贴板
        function copyErrorDetails() {
            const userMessage = document.getElementById('errorModalUserMessage').textContent;
            const details = document.getElementById('errorModalDetails').textContent;
            const code = document.getElementById('errorModalCode').textContent;
            const type = document.getElementById('errorModalType').textContent;
            const status = document.getElementById('errorModalStatus').textContent;
            const traceId = document.getElementById('errorModalTraceId').textContent;
            const userMessageHeader = translateAppTextLocal('【用户错误信息】');
            const detailHeader = translateAppTextLocal('【错误详情】');
            const technicalHeader = translateAppTextLocal('【技术堆栈/细节】');

            const fullErrorText = `
${userMessageHeader}
${userMessage}

${detailHeader}
Code: ${code}
Type: ${type}
Status: ${status}
Trace ID: ${traceId}

${technicalHeader}
${details}
            `.trim();

            navigator.clipboard.writeText(fullErrorText).then(() => {
                showToast(translateAppTextLocal('错误详情已复制'), 'success');
            }).catch(() => {
                // 降级方案
                const textarea = document.createElement('textarea');
                textarea.value = fullErrorText;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showToast(translateAppTextLocal('错误详情已复制'), 'success');
            });
        }

        // 统一处理 API 响应错误
        function handleApiError(data, defaultMessage = '请求失败') {
            if (!data.success) {
                const error = data.error || data;
                const userMessage = window.resolveApiErrorMessage
                    ? window.resolveApiErrorMessage(error, defaultMessage, 'Request failed')
                    : (typeof error === 'string' ? translateAppTextLocal(error) : translateAppTextLocal(defaultMessage));
                showToast(userMessage, 'error', error && typeof error === 'object' ? error : null);
                return true;
            }
            return false;
        }

        function escapeJs(str) {
            if (!str) return '';
            return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r');
        }

