// split from admin.js → version_update.js
        function updateTagFilter() {
            // Mailbox sidebar tag filter only — soft loadTags from modals must not
            // rewrite hidden mailbox chrome while the user is on another page.
            if (typeof currentPage !== 'undefined' && currentPage !== 'mailbox') {
                return;
            }
            const container = document.getElementById('tagFilterContainer');
            if (!container) return;

            if (allTags.length === 0) {
                container.style.display = 'none';
                return;
            }

            container.style.display = 'flex';

            let html = '';
            allTags.forEach(tag => {
                html += `
                    <label style="display: inline-flex; align-items: center; gap: 4px; font-size: 11px; cursor: pointer; padding: 2px 6px; border: 1px solid #e5e5e5; border-radius: 12px; background: white; user-select: none;">
                        <input type="checkbox" class="tag-filter-checkbox" value="${tag.id}" onchange="handleTagFilterChange()" style="margin: 0;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: ${tag.color}; display: inline-block;"></span>
                        ${escapeHtml(tag.name)}
                    </label>
                `;
            });
            container.innerHTML = html;
            /* Old dropdown code removed */


        }

        // Tag manager modal list only — batch-tag soft loadTags must not require open modal.
        function updateBatchActionBar() {
            const barConfigs = [
                { barId: 'batchActionBar', countId: 'selectedCount', active: mailboxViewMode === 'standard' },
                { barId: 'compactBatchActionBar', countId: 'compactSelectedCount', active: mailboxViewMode === 'compact' }
            ];

            barConfigs.forEach(config => {
                const bar = document.getElementById(config.barId);
                const countSpan = document.getElementById(config.countId);
                if (!bar || !countSpan) return;

                if (selectedAccountIds.size > 0 && config.active) {
                    bar.style.display = 'flex';
                    countSpan.textContent = formatSelectedItemsLabel(selectedAccountIds.size);
                } else {
                    bar.style.display = 'none';
                }
            });
        }

        window.addEventListener('ui-language-changed', () => {
            updateTopbar(currentPage);
            updateBatchActionBar();

            // 语言切换后，重渲染部署警告文案（后端同时返回中英文）
            // Only while Settings surface is active so non-settings pages do not flash chrome.
            if (lastDeploymentInfo && (typeof isSettingsSurfaceActive === 'function' ? isSettingsSurfaceActive() : true)) {
                try {
                    renderDeploymentWarnings(lastDeploymentInfo);
                } catch (e) {}
            }

            // Version banner soft re-paint from warm session cache (no network).
            try {
                if (versionCheckCache) {
                    applyVersionCheckPayload(versionCheckCache);
                }
            } catch (e) {}

            // Soft-load surfaces: re-paint warm caches with new language without network.
            try {
                // Include empty allTags so tag empty chrome re-translates when modal is open.
                if (Array.isArray(allTags)) {
                    const tagModal = document.getElementById('tagManagementModal');
                    const tagModalOpen = !!(tagModal && tagModal.classList.contains('show'));
                    if (allTags.length > 0 || tagModalOpen) {
                        renderTagList();
                        updateTagFilter();
                        paintBatchTagSelectFromWarmTags();
                    }
                }
            } catch (e) {}
            try {
                // Open batch-tag modal: re-translate title (select painted above when warm).
                const batchTagModal = document.getElementById('batchTagModal');
                if (batchTagModal && batchTagModal.classList.contains('show')) {
                    const titleEl = document.getElementById('batchTagTitle');
                    if (titleEl) {
                        titleEl.textContent = translateAppTextLocal(
                            batchActionType === 'add' ? '批量添加标签' : '批量移除标签'
                        );
                    }
                }
            } catch (e) {}
            try {
                softPaintBatchMoveGroupSelectIfOpen();
            } catch (e) {}
            try {
                if (Array.isArray(groups) && groups.length > 0) {
                    if (typeof ensurePoolAdminGroupOptions === 'function') {
                        Promise.resolve(ensurePoolAdminGroupOptions(false)).catch(() => {});
                    }
                }
            } catch (e) {}
            try {
                if (typeof ensurePoolAdminProviderOptions === 'function') {
                    ensurePoolAdminProviderOptions(false);
                }
            } catch (e) {}
            try {
                if (typeof loadProviders === 'function') {
                    loadProviders(false);
                }
            } catch (e) {}

            // Refresh modal open: re-paint stats / failed list / history / invalid-token from warm caches.
            const refreshModal = document.getElementById('refreshModal');
            if (refreshModal && refreshModal.classList.contains('show')) {
                try {
                    if (refreshStatsCache) applyRefreshStats(refreshStatsCache);
                } catch (e) {}
                try {
                    if (failedRefreshLogsCache && failedRefreshLogsCache.success) {
                        const failedContainer = document.getElementById('failedListContainer');
                        if (failedContainer && failedContainer.style.display !== 'none') {
                            showFailedListFromData(mapFailedRefreshLogRows(failedRefreshLogsCache.logs));
                        }
                    }
                } catch (e) {}
                try {
                    const historyContainer = document.getElementById('refreshLogsContainer');
                    if (historyContainer && historyContainer.style.display !== 'none' && refreshModalHistoryCache) {
                        renderRefreshModalHistory(refreshModalHistoryCache);
                    }
                } catch (e) {}
                try {
                    if (invalidTokenGovernanceCandidatesLoaded) {
                        applyInvalidTokenGovernanceCandidates(invalidTokenGovernanceCandidates, {
                            keepVisibleWhenEmpty: true
                        });
                    }
                } catch (e) {}
            }

            // Page-level soft log pages currently visible.
            try {
                if (currentPage === 'refresh-log' && refreshLogPageCache) {
                    renderRefreshLogPage(refreshLogPageCache);
                }
            } catch (e) {}
            try {
                if (currentPage === 'audit' && auditLogPageCache) {
                    renderAuditLogPage(auditLogPageCache);
                }
            } catch (e) {}
        });

        // 显示批量刷新 Token 确认框
        function updatePersistentToast(id, message) {
            const toast = document.querySelector(`.toast[data-persistent-id="${id}"]`);
            if (toast) {
                const msgEl = toast.querySelector('span') || toast;
                msgEl.textContent = message;
            } else {
                // 如果 toast 已被用户关闭，重新显示
                showPersistentToast(id, message);
            }
        }

        // 关闭持久 Toast
        function applyVersionCheckPayload(data) {
            if (!data || typeof data !== 'object') return;
            // 版本检查被管理员关闭时，不再提示也不再重试
            if (data.disabled) return;
            if (!data.has_update) return;
            const banner = document.getElementById('versionUpdateBanner');
            const msg = document.getElementById('versionUpdateMsg');
            if (!banner || !msg) return;
            const latest = escapeHtml(String(data.latest_version || ''));
            const current = escapeHtml(String(data.current_version || ''));
            const releaseUrl = escapeHtml(String(data.release_url || '#'));
            // Translate chrome labels at paint time so language change can soft re-paint.
            msg.innerHTML = `${translateAppTextLocal('发现新版本')} <strong>v${latest}</strong>（${translateAppTextLocal('当前')} v${current}）
                        <a href="${releaseUrl}" target="_blank" class="ms-1">${translateAppTextLocal('查看更新日志')}</a>`;
            banner.classList.remove('d-none');
            const appEl = document.getElementById('app');
            if (appEl) {
                appEl.style.paddingTop = banner.offsetHeight + 'px';
            }
        }

        /**
         * 页面加载时调用一次，检查是否有可用更新。
         * Soft-load warm session result; forceRefresh bypasses cache.
         */
        async function checkVersionUpdate(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            // Soft re-run: reuse warm session payload without network.
            if (!force && versionCheckCache) {
                applyVersionCheckPayload(versionCheckCache);
                return versionCheckCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so explicit recheck starts a true network GET.
            if (versionCheckLoadPromise) {
                if (!force || versionCheckLoadForce) {
                    return versionCheckLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                versionCheckLoadPromise = null;
                versionCheckLoadForce = false;
            }

            versionCheckLoadForce = force;
            const request = (async () => {
                try {
                    const res = await fetch('/api/system/version-check');
                    if (!res.ok) return null;
                    const data = await res.json();
                    if (versionCheckLoadPromise !== request) {
                        return versionCheckCache;
                    }
                    versionCheckCache = data;
                    applyVersionCheckPayload(data);
                    return data;
                } catch (e) {
                    // 静默失败
                    return null;
                } finally {
                    if (versionCheckLoadPromise === request) {
                        versionCheckLoadPromise = null;
                        versionCheckLoadForce = false;
                    }
                }
            })();

            versionCheckLoadPromise = request;
            return request;
        }

        function dismissVersionBanner() {
            document.getElementById('versionUpdateBanner').classList.add('d-none');
            document.getElementById('app').style.paddingTop = '';
        }

        /**
         * 用户点击"立即更新"时触发
         */
        async function triggerUpdate() {
            const btn = document.getElementById('btnTriggerUpdate');
            btn.disabled = true;
            btn.textContent = translateAppTextLocal('正在触发更新...');

            // 获取更新方式（从设置中读取或默认为 watchtower）
            let updateMethod = 'watchtower';
            try {
                const settingsData = await fetchSettingsPagePayload(false);
                if (settingsData && settingsData.success && settingsData.settings) {
                    updateMethod = settingsData.settings.update_method || 'watchtower';
                }
            } catch (e) {
                console.warn('Failed to load update method, using default (watchtower):', e);
            }

            try {
                // 根据更新方式决定 timeout 和 URL
                const timeout = updateMethod === 'docker_api' ? 120000 : 60000;  // Docker API 模式 120s, Watchtower 模式 60s
                const url = `/api/system/trigger-update?method=${updateMethod}`;
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);
                
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRFToken() },
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                
                const data = await res.json();
                if (data.success) {
                    // 镜像已是最新，无需等待重启
                    if (data.already_latest) {
                        showToast(translateAppTextLocal('当前已是最新版本，无需更新'), 'info', 5000);
                        btn.disabled = false;
                        btn.textContent = translateAppTextLocal('立即更新');
                        return;
                    }

                    // 记录本次更新方式，供 waitForRestart 调整等待时长
                    try {
                        window.__lastUpdateMethod = updateMethod;
                    } catch (e) {}

                    // Docker API 与 Watchtower 都可能触发容器重启：统一走“等待恢复”逻辑
                    btn.textContent = translateAppTextLocal('等待容器重启...');
                    if (updateMethod === 'docker_api') {
                        showToast(translateAppTextLocal('Docker API 更新已启动，等待容器重启...'), 'info', 5000);
                    }
                    await waitForRestart();
                } else {
                    const msg = data.message || '未知错误';
                    // 区分常见错误场景，给出友好提示
                    if (updateMethod === 'docker_api') {
                        if (msg.includes('未启用') || msg.includes('DOCKER_SELF_UPDATE_ALLOW')) {
                            showToast(translateAppTextLocal('Docker API 自更新功能未启用。请在 .env 中设置 DOCKER_SELF_UPDATE_ALLOW=true，并在 docker-compose.yml 中挂载 docker.sock'), 'warning', 10000);
                        } else if (msg.includes('docker.sock') || msg.includes('无法连接')) {
                            showToast(translateAppTextLocal('无法访问 Docker API。请确认已在 docker-compose.yml 中挂载 /var/run/docker.sock'), 'warning', 8000);
                        } else {
                            showToast(translateAppTextLocal('Docker API 更新失败：') + msg, 'error', 8000);
                        }
                    } else {
                        if (msg.includes('WATCHTOWER_HTTP_API_TOKEN') || (msg.includes('未配置') && res.status === 500)) {
                            showToast(translateAppTextLocal('一键更新需要配置 Watchtower 服务（仅 Docker 部署支持）。请在 .env 中设置 WATCHTOWER_HTTP_API_TOKEN，并使用含 Watchtower 的 docker-compose 部署方式'), 'warning', 10000);
                        } else if (msg.includes('无法连接') || msg.includes('Watchtower')) {
                            showToast(translateAppTextLocal('无法连接 Watchtower 服务，请确认已使用 docker-compose 方式部署，且 watchtower 容器正常运行'), 'warning', 8000);
                        } else {
                            showToast(translateAppTextLocal('更新失败：') + msg, 'error');
                        }
                    }
                    btn.disabled = false;
                    btn.textContent = translateAppTextLocal('立即更新');
                }
            } catch (e) {
                if (e.name === 'AbortError') {
                    showToast(translateAppTextLocal('更新请求超时，请检查配置和网络连接'), 'error', 8000);
                } else {
                    showToast(translateAppTextLocal('更新请求失败，请检查网络连接'), 'error');
                }
                btn.disabled = false;
                btn.textContent = translateAppTextLocal('立即更新');
            }
        }

        /**
         * 轮询 /healthz 等待容器重启后恢复
         * - 立即开始轮询，每 3 秒一次
         * - 最长等待 90 秒，超时提示用户手动检查
         * - 检测到服务恢复后刷新页面
         */
        async function waitForRestart() {
            // 默认 90 秒（Watchtower 通常更快）；Docker API 更新可能涉及 pull 镜像，适当放宽
            const WATCHTOWER_MAX_WAIT_MS = 90000;  // 90 秒
            const DOCKER_API_MAX_WAIT_MS = 180000;  // 180 秒
            const POLL_INTERVAL_MS = 3000;  // 每 3 秒

            let MAX_WAIT_MS = WATCHTOWER_MAX_WAIT_MS;
            try {
                const method = (window.__lastUpdateMethod || 'watchtower');
                if (method === 'docker_api') {
                    MAX_WAIT_MS = DOCKER_API_MAX_WAIT_MS;
                }
            } catch (e) {
                MAX_WAIT_MS = WATCHTOWER_MAX_WAIT_MS;
            }
            const startAt = Date.now();
            let seenDown = false;
            let initialBootId = null;

            // 先读取一次 boot_id，用于判断是否发生“新进程启动”
            try {
                const firstRes = await fetch('/healthz', { cache: 'no-store' });
                if (firstRes.ok) {
                    const firstData = await firstRes.json();
                    if (firstData && firstData.boot_id) {
                        initialBootId = String(firstData.boot_id);
                    }
                }
            } catch (e) {
                // ignore
            }

            while (Date.now() - startAt < MAX_WAIT_MS) {
                await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
                try {
                    const res = await fetch('/healthz', { cache: 'no-store' });
                    if (res.ok) {
                        let bootIdChanged = false;
                        try {
                            const d = await res.json();
                            const bootId = d && d.boot_id ? String(d.boot_id) : null;
                            if (bootId && initialBootId && bootId !== initialBootId) {
                                bootIdChanged = true;
                            }
                        } catch (e) {
                            // ignore json parse
                        }

                        // 以“boot_id 变化”作为更可靠的重启完成信号
                        if (bootIdChanged || seenDown) {
                            showToast(translateAppTextLocal('更新完成，正在刷新页面...'), 'success');
                            setTimeout(() => location.reload(), 1500);
                            return;
                        }
                        // 还没看到重启迹象：可能仍在 pull/重建中，继续等
                    } else {
                        seenDown = true;
                    }
                } catch (e) {
                    // 请求失败通常意味着容器正在重启/网络暂不可用
                    seenDown = true;
                }
            }

            // 超时处理
            try {
                const method = (window.__lastUpdateMethod || 'watchtower');
                if (method === 'docker_api') {
                    if (!seenDown) {
                        showToast(translateAppTextLocal('等待超时：容器未发生重启，可能已是最新版本或更新仍在后台进行'), 'warning', 9000);
                    } else {
                        showToast(translateAppTextLocal('等待超时：容器尚未恢复，请检查容器状态/日志'), 'warning', 9000);
                    }
                } else {
                    if (!seenDown) {
                        showToast(translateAppTextLocal('等待超时：容器未发生重启，请检查 Watchtower 配置/日志'), 'warning', 9000);
                    } else {
                        showToast(translateAppTextLocal('更新超时，请手动检查容器状态'), 'warning', 8000);
                    }
                }
            } catch (e) {
                showToast(translateAppTextLocal('更新超时，请手动检查容器状态'), 'warning', 8000);
            }
            const btn = document.getElementById('btnTriggerUpdate');
            if (btn) {
                btn.disabled = false;
                btn.textContent = translateAppTextLocal('立即更新');
            }
        }

        /**
         * 设置面板中的"手动触发更新"按钮回调
         * 与 triggerUpdate() 类似，但 UI 反馈在设置面板内
         */
        async function manualTriggerUpdate() {
            const btn = document.getElementById('btnManualTriggerUpdate');
            const resultDiv = document.getElementById('manualUpdateResult');
            if (!btn) return;

            btn.disabled = true;
            btn.textContent = translateAppTextLocal('正在触发更新...');
            if (resultDiv) {
                resultDiv.style.display = 'none';
                resultDiv.innerHTML = '';
            }

            // 读取当前选择的更新方式
            const selectedRadio = document.querySelector('input[name="updateMethod"]:checked');
            const updateMethod = selectedRadio ? selectedRadio.value : 'watchtower';

            try {
                const timeout = updateMethod === 'docker_api' ? 120000 : 60000;
                const url = `/api/system/trigger-update?method=${updateMethod}`;

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRFToken() },
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                const data = await res.json();
                if (data.success) {
                    if (resultDiv) {
                        resultDiv.style.display = 'block';
                        const msg = pickApiMessage(data, '更新已触发', 'Update triggered');
                        resultDiv.innerHTML = `<span style="color: var(--clr-success, #28a745);">✅ ${escapeHtml(msg)}</span>`;
                    }
                    // 镜像已是最新，无需等待重启
                    if (data.already_latest) {
                        showToast(pickApiMessage(data, '当前已是最新版本', 'Already up to date'), 'info', 5000);
                        btn.disabled = false;
                        btn.textContent = translateAppTextLocal('立即更新');
                        return;
                    }
                    window.__lastUpdateMethod = updateMethod;
                    btn.textContent = translateAppTextLocal('等待容器重启...');
                    await waitForRestart();
                } else {
                    const msg = data.message || '未知错误';
                    const detail = data.detail ? `\n详情: ${data.detail}` : '';
                    if (resultDiv) {
                        resultDiv.style.display = 'block';
                        resultDiv.innerHTML = `<span style="color: var(--clr-danger, #dc3545);">❌ ${escapeHtml(msg)}</span>${detail ? '<br><small style="color: var(--text-muted);">' + escapeHtml(detail.trim()) + '</small>' : ''}`;
                    }
                    showToast(translateAppTextLocal('更新失败：') + msg, 'error', 8000);
                    btn.disabled = false;
                    btn.textContent = translateAppTextLocal('立即更新');
                }
            } catch (e) {
                const errMsg = e.name === 'AbortError' ? translateAppTextLocal('请求超时') : (e.message || translateAppTextLocal('网络错误'));
                if (resultDiv) {
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = `<span style="color: var(--clr-danger, #dc3545);">❌ ${escapeHtml(errMsg)}</span>`;
                }
                showToast(translateAppTextLocal('更新请求失败：') + errMsg, 'error', 8000);
                btn.disabled = false;
                btn.textContent = translateAppTextLocal('立即更新');
            }
        }
