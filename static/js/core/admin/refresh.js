// split from admin.js → refresh.js
        async function showRefreshModal() {
            document.getElementById('refreshModal').classList.add('show');
            resetInvalidTokenGovernanceState();
            // Soft-load stats when warm; mutations/refresh force-refresh.
            await loadRefreshStats(false);
            // 自动加载失败列表（如果有失败记录）
            await autoLoadFailedListIfNeeded();
            // Soft-load invalid-token governance when warm; mutations force-refresh.
            await loadInvalidTokenGovernanceCandidates({
                forceRefresh: false,
                keepVisibleWhenEmpty: false,
                silentWhenEmpty: true
            });
        }

        // Soft-load cache for failed refresh logs (modal re-open + loadFailedLogs share one GET).
        let failedRefreshLogsCache = null;
        let failedRefreshLogsLoadPromise = null;
        // True when the in-flight failed-logs GET was started with forceRefresh.
        let failedRefreshLogsLoadForce = false;

        function invalidateFailedRefreshLogsCache() {
            failedRefreshLogsCache = null;
            failedRefreshLogsLoadPromise = null;
            failedRefreshLogsLoadForce = false;
        }

        function mapFailedRefreshLogRows(logs) {
            return (Array.isArray(logs) ? logs : []).map(log => ({
                id: log.account_id ?? log.id,
                email: log.account_email ?? log.email,
                error: log.error_message ?? log.error,
                created_at: log.created_at || null
            }));
        }

        async function fetchFailedRefreshLogs(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            if (!force && failedRefreshLogsCache) {
                return failedRefreshLogsCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so retry UI always starts a true network GET.
            if (failedRefreshLogsLoadPromise) {
                if (!force || failedRefreshLogsLoadForce) {
                    return failedRefreshLogsLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                failedRefreshLogsLoadPromise = null;
                failedRefreshLogsLoadForce = false;
            }

            failedRefreshLogsLoadForce = force;
            const request = (async () => {
                const response = await fetch('/api/accounts/refresh-logs/failed');
                const data = await response.json();
                if (failedRefreshLogsLoadPromise !== request) {
                    return failedRefreshLogsCache;
                }
                if (data && data.success) {
                    failedRefreshLogsCache = {
                        success: true,
                        logs: Array.isArray(data.logs) ? data.logs : []
                    };
                }
                return failedRefreshLogsCache;
            })();

            failedRefreshLogsLoadPromise = request;
            try {
                return await request;
            } finally {
                if (failedRefreshLogsLoadPromise === request) {
                    failedRefreshLogsLoadPromise = null;
                    failedRefreshLogsLoadForce = false;
                }
            }
        }

        // 自动加载失败列表（如果有失败记录）
        function hideRefreshModal() {
            const modal = document.getElementById('refreshModal');
            modal.classList.remove('show');

            // 确保所有内容都被隐藏，防止残留
            const progress = document.getElementById('refreshProgress');
            if (progress) {
                progress.style.display = 'none';
            }
            const failedList = document.getElementById('failedListContainer');
            if (failedList) {
                failedList.style.display = 'none';
            }
            const logsContainer = document.getElementById('refreshLogsContainer');
            if (logsContainer) {
                logsContainer.style.display = 'none';
            }
            resetInvalidTokenGovernanceState();

            // 重置按钮状态
            const refreshAllBtn = document.getElementById('refreshAllBtn');
            if (refreshAllBtn) {
                refreshAllBtn.disabled = false;
                refreshAllBtn.textContent = translateAppTextLocal('🔄 全量刷新');
            }

            const retryFailedBtn = document.getElementById('retryFailedBtn');
            if (retryFailedBtn) {
                retryFailedBtn.disabled = false;
                retryFailedBtn.textContent = translateAppTextLocal('🔁 重试失败');
            }
        }

        // ==================== 失效 Token 治理面板 ====================

        /** 重置治理面板 UI（模态框打开/关闭时调用）。不清 soft cache，便于 re-open soft-load。 */
        function invalidateRefreshStatsCache() {
            refreshStatsCache = null;
            refreshStatsLoadPromise = null;
            refreshStatsLoadForce = false;
        }

        function applyRefreshStats(stats) {
            const safe = stats && typeof stats === 'object' ? stats : {};
            const lastEl = document.getElementById('lastRefreshTime');
            const totalEl = document.getElementById('totalRefreshCount');
            const successEl = document.getElementById('successRefreshCount');
            const failedEl = document.getElementById('failedRefreshCount');
            // Null-safe: stats live in refresh modal; mutations may finish after close.
            if (!lastEl || !totalEl || !successEl || !failedEl) {
                return;
            }
            // 优先使用保存的本地刷新时间
            if (lastRefreshTime && lastRefreshTime instanceof Date) {
                lastEl.textContent = formatDateTime(lastRefreshTime.toISOString());
            } else if (safe.last_refresh_time) {
                lastEl.textContent = formatDateTime(safe.last_refresh_time);
            } else {
                lastEl.textContent = '-';
            }

            totalEl.textContent = safe.total ?? '-';
            successEl.textContent = safe.success_count ?? '-';
            failedEl.textContent = safe.failed_count ?? '-';
        }

        // 加载刷新统计
        async function loadRefreshStats(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            // Soft re-entry: always return warm cache; paint only while refresh modal open.
            if (!force && refreshStatsCache) {
                if (typeof isRefreshModalOpen === 'function' ? isRefreshModalOpen() : true) {
                    applyRefreshStats(refreshStatsCache);
                }
                return refreshStatsCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so post-refresh UI always starts a true network GET.
            if (refreshStatsLoadPromise) {
                if (!force || refreshStatsLoadForce) {
                    return refreshStatsLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                refreshStatsLoadPromise = null;
                refreshStatsLoadForce = false;
            }

            refreshStatsLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/accounts/refresh-stats');
                    const data = await response.json();

                    if (refreshStatsLoadPromise !== request) {
                        return refreshStatsCache;
                    }
                    if (data.success) {
                        // Always warm soft cache; paint only while refresh modal is open.
                        refreshStatsCache = data.stats || {};
                        if (typeof isRefreshModalOpen === 'function' ? isRefreshModalOpen() : true) {
                            applyRefreshStats(refreshStatsCache);
                        }
                    }
                    return refreshStatsCache;
                } catch (error) {
                    if (refreshStatsLoadPromise !== request) {
                        return refreshStatsCache;
                    }
                    console.error('加载刷新统计失败:', error);
                    return refreshStatsCache;
                }
            })();

            refreshStatsLoadPromise = request;
            try {
                return await request;
            } finally {
                if (refreshStatsLoadPromise === request) {
                    refreshStatsLoadPromise = null;
                    refreshStatsLoadForce = false;
                }
            }
        }

        // 全量刷新所有账号
        async function refreshAllAccounts() {
            const btn = document.getElementById('refreshAllBtn');
            const progress = document.getElementById('refreshProgress');
            const progressText = document.getElementById('refreshProgressText');

            if (btn.disabled) return;

            if (!confirm('确定要刷新所有账号的 Token 吗？')) {
                return;
            }

            btn.disabled = true;
            btn.textContent = translateAppTextLocal('刷新中...');
            progress.style.display = 'block';
            progressText.innerHTML = translateAppTextLocal('正在初始化...');

            try {
                const eventSource = new EventSource('/api/accounts/trigger-scheduled-refresh?force=true');
                let totalCount = 0;
                let successCount = 0;
                let failedCount = 0;

                eventSource.onmessage = function (event) {
                    try {
                        const data = JSON.parse(event.data);

                        if (data.type === 'start') {
                            totalCount = data.total;
                            const delayInfo = data.delay_seconds > 0 ? `（间隔 ${data.delay_seconds} 秒）` : '';
                            progressText.innerHTML = `${translateAppTextLocal('总共')} <strong>${totalCount}</strong> ${translateAppTextLocal('个账号')}${delayInfo}，${translateAppTextLocal('准备开始刷新...')}`;
                            // 初始化统计
                            document.getElementById('totalRefreshCount').textContent = totalCount;
                            document.getElementById('successRefreshCount').textContent = '0';
                            document.getElementById('failedRefreshCount').textContent = '0';
                        } else if (data.type === 'progress') {
                            successCount = data.success_count;
                            failedCount = data.failed_count;
                            // 实时更新统计
                            document.getElementById('successRefreshCount').textContent = successCount;
                            document.getElementById('failedRefreshCount').textContent = failedCount;
                            progressText.innerHTML = `
                                ${translateAppTextLocal('正在处理')}: <strong>${data.email}</strong><br>
                                ${translateAppTextLocal('进度')}: <strong>${data.current}/${data.total}</strong> |
                                ${translateAppTextLocal('成功')}: <strong style="color: #28a745;">${successCount}</strong> |
                                ${translateAppTextLocal('失败')}: <strong style="color: #dc3545;">${failedCount}</strong>
                            `;
                        } else if (data.type === 'delay') {
                            progressText.innerHTML += `<br><span style="color: #999;">${translateAppTextLocal('等待')} ${data.seconds} ${translateAppTextLocal('秒后继续...')}</span>`;
                        } else if (data.type === 'complete') {
                            eventSource.close();
                            progress.style.display = 'none';
                            btn.disabled = false;
                            btn.textContent = translateAppTextLocal('🔄 全量刷新');

                            const invalidTokenFailedCount = Number(data.invalid_token_failed_count || 0);
                            latestInvalidTokenDetectedCount = invalidTokenFailedCount;

                            // 直接更新统计数据，使用本地时间
                            const now = new Date();
                            lastRefreshTime = now; // 保存刷新时间
                            document.getElementById('lastRefreshTime').textContent = formatUiRelativeTime(new Date().toISOString(), '刚刚', 'Just now');
                            document.getElementById('totalRefreshCount').textContent = data.total;
                            document.getElementById('successRefreshCount').textContent = data.success_count;
                            document.getElementById('failedRefreshCount').textContent = data.failed_count;
                            // Keep soft stats cache aligned with the just-completed run.
                            refreshStatsCache = {
                                total: data.total,
                                success_count: data.success_count,
                                failed_count: data.failed_count,
                                last_refresh_time: now.toISOString()
                            };

                            showToast(
                                translateAppTextLocal(
                                    '刷新完成！成功: ' + data.success_count + ', 失败: ' + data.failed_count
                                ),
                                data.failed_count > 0 ? 'warning' : 'success'
                            );

                            if (invalidTokenFailedCount > 0) {
                                showInvalidTokenDetectionSummary(invalidTokenFailedCount, data.invalid_token_failed_list || []);
                                loadInvalidTokenGovernanceCandidates({
                                    forceRefresh: true,
                                    keepVisibleWhenEmpty: true,
                                    silentWhenEmpty: false
                                });
                            }

                            // 如果有失败的，显示失败列表（并 seed soft failed-list cache）
                            if (data.failed_count > 0) {
                                showFailedListFromData(data.failed_list);
                            } else {
                                hideFailedList();
                            }

                            // 刷新账号列表以更新刷新时间
                            if (currentGroupId) {
                                loadAccountsByGroup(currentGroupId, true);
                            }
                            // New refresh-log / audit rows may exist; drop soft-load caches.
                            if (typeof invalidateRefreshLogPageCache === 'function') {
                                invalidateRefreshLogPageCache();
                            }
                            if (typeof invalidateAuditLogPageCache === 'function') {
                                invalidateAuditLogPageCache();
                            }
                        } else if (data.type === 'error') {
                            eventSource.close();
                            progress.style.display = 'none';
                            btn.disabled = false;
                            btn.textContent = translateAppTextLocal('🔄 全量刷新');

                            const errCode = data.error && data.error.code;
                            if (errCode === 'NO_MAIL_PERMISSION') {
                                showToast(buildRefreshAllPermissionErrorSummary(data.error || {}), 'error', data.error || null, true);
                            } else {
                                const userMessage = window.resolveApiErrorMessage
                                    ? window.resolveApiErrorMessage(data.error || {}, '刷新过程中出现错误', 'Refresh failed during execution')
                                    : translateAppTextLocal('刷新过程中出现错误');

                                if (errCode === 'REFRESH_CONFLICT') {
                                    showToast(userMessage, 'warning', data.error || null, true);
                                } else {
                                    showToast(userMessage, 'error', data.error || null, true);
                                }
                            }
                        }
                    } catch (e) {
                        console.error('解析进度数据失败:', e);
                    }
                };

                eventSource.onerror = function (error) {
                    console.error('EventSource 错误:', error);
                    eventSource.close();
                    progress.style.display = 'none';
                    btn.disabled = false;
                    btn.textContent = translateAppTextLocal('🔄 全量刷新');
                    showToast(translateAppTextLocal('刷新过程中出现错误'), 'error');
                };

            } catch (error) {
                progress.style.display = 'none';
                btn.disabled = false;
                btn.textContent = translateAppTextLocal('🔄 全量刷新');
                showToast(translateAppTextLocal('刷新请求失败'), 'error');
            }
        }

        function buildRefreshAllPermissionErrorSummary(errorPayload) {
            const traceId = String(errorPayload && errorPayload.trace_id || '').trim();
            const lang = getUiLanguage();

            if (lang === 'en') {
                const lines = [
                    'This Outlook account is missing mail read permission, so full refresh cannot proceed.',
                    '[Code] NO_MAIL_PERMISSION',
                    '',
                    'Suggested actions:',
                    '1. Re-authorize the account and ensure Mail.Read or Mail.ReadWrite scope is granted.',
                    '2. Save account settings and retry full refresh.',
                    traceId
                        ? `3. If it still fails, share Trace ID: ${traceId}`
                        : '3. If it still fails, capture and share the Trace ID for backend diagnostics.',
                ];
                return lines.join('\n');
            }

            const lines = [
                '当前账号缺少邮件读取权限，导致全量刷新无法继续。',
                '[Code] NO_MAIL_PERMISSION',
                '',
                '建议处理：',
                '1. 重新授权账号，并确保授予 Mail.Read 或 Mail.ReadWrite 权限。',
                '2. 保存账号设置后再次执行“全量刷新”。',
                traceId
                    ? `3. 若仍失败，请反馈 Trace ID：${traceId}`
                    : '3. 若仍失败，请记录并反馈 Trace ID 以便后端排查。',
            ];
            return lines.join('\n');
        }

        // 重试失败的账号
        function isRefreshModalOpen() {
            const modal = document.getElementById('refreshModal');
            return !!(modal && modal.classList.contains('show'));
        }

        // 加载失败日志
        async function loadFailedLogs(forceRefresh = false) {
            const container = document.getElementById('failedListContainer');
            const listEl = document.getElementById('failedList');
            if (!container || !listEl) return;

            // Soft fetch always warms cache; paint / hide sibling panels only while
            // the refresh modal is still open (retry may complete after modal close).
            const paintFailedChrome = isRefreshModalOpen();
            if (paintFailedChrome) {
                hideRefreshLogs();
            }

            try {
                // Soft by default; retry success paths pass forceRefresh=true.
                const data = await fetchFailedRefreshLogs(forceRefresh);

                if (data && data.success) {
                    const rows = mapFailedRefreshLogRows(data.logs);
                    // Always leave soft cache warm via fetchFailedRefreshLogs side effects.
                    if (!isRefreshModalOpen()) {
                        return;
                    }
                    if (rows.length === 0) {
                        listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">' + translateAppTextLocal('暂无失败状态的邮箱') + '</div>';
                    } else {
                        let html = '';
                        rows.forEach(log => {
                            html += `
                                <div style="padding: 12px; border-bottom: 1px solid #e5e5e5; display: flex; justify-content: space-between; align-items: center;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 600; margin-bottom: 4px;">${escapeHtml(log.email || '-')}</div>
                                        <div style="font-size: 12px; color: #dc3545;">${escapeHtml(log.error || translateAppTextLocal('未知错误'))}</div>
                                        <div style="font-size: 11px; color: #999; margin-top: 4px;">${translateAppTextLocal('最后刷新')}: ${formatDateTime(log.created_at)}</div>
                                    </div>
                                    <button class="btn btn-sm btn-primary" onclick="retrySingleAccount(${log.id}, '${escapeJs(log.email || '')}')">
                                        ${translateAppTextLocal('重试')}
                                    </button>
                                </div>
                            `;
                        });
                        listEl.innerHTML = html;
                    }
                    container.style.display = 'block';
                }
            } catch (error) {
                if (isRefreshModalOpen()) {
                    showToast(translateAppTextLocal('加载失败邮箱列表失败'), 'error');
                }
            }
        }

        // Soft-load cache for refresh-modal history (limit=1000; separate from page limit=200).
        let refreshModalHistoryCache = null;
        let refreshModalHistoryLoadPromise = null;
        // True when the in-flight refresh-logs GET was started with forceRefresh.
        let refreshModalHistoryLoadForce = false;

        function renderRefreshModalHistory(data) {
            const container = document.getElementById('refreshLogsContainer');
            const listEl = document.getElementById('refreshLogsList');
            if (!container || !listEl) return;

            const logs = data && Array.isArray(data.logs) ? data.logs : [];
            if (logs.length === 0) {
                listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">' + translateAppTextLocal('暂无全量刷新历史') + '</div>';
            } else {
                listEl.innerHTML = `<div style="padding: 12px; background-color: #f8f9fa; border-bottom: 1px solid #e5e5e5; font-size: 13px; color: #666;">${translateAppTextLocal('近半年刷新历史（共 ' + logs.length + ' 条）')}</div>`;
                let html = '';
                logs.forEach(log => {
                    const statusColor = log.status === 'success' ? '#28a745' : '#dc3545';
                    const statusText = translateAppTextLocal(log.status === 'success' ? '成功' : '失败');
                    const typeText = translateAppTextLocal(log.refresh_type === 'manual' ? '手动' : '自动');
                    const typeColor = log.refresh_type === 'manual' ? '#007bff' : '#28a745';
                    const typeBgColor = log.refresh_type === 'manual' ? '#e7f3ff' : '#e8f5e9';

                    html += `
                        <div style="padding: 14px; border-bottom: 1px solid #e5e5e5; transition: background-color 0.2s;"
                             onmouseover="this.style.backgroundColor='#f8f9fa'"
                             onmouseout="this.style.backgroundColor='transparent'">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 6px;">
                                <div style="font-weight: 600; font-size: 14px;">${escapeHtml(log.account_email)}</div>
                                <div style="display: flex; gap: 8px; align-items: center;">
                                    <span style="font-size: 11px; padding: 3px 8px; background-color: ${typeBgColor}; color: ${typeColor}; border-radius: 4px; font-weight: 500;">${typeText}</span>
                                    <span style="font-size: 13px; color: ${statusColor}; font-weight: 600;">${statusText}</span>
                                </div>
                            </div>
                            <div style="font-size: 12px; color: #888;">${formatDateTime(log.created_at)}</div>
                            ${log.error_message ? `<div style="font-size: 12px; color: #dc3545; margin-top: 6px; padding: 6px; background-color: #fff5f5; border-radius: 4px;">${escapeHtml(log.error_message)}</div>` : ''}
                        </div>
                    `;
                });
                listEl.innerHTML += html;
            }
            container.style.display = 'block';
        }

        // 加载刷新历史
        async function loadRefreshLogs(forceRefresh = false) {
            const container = document.getElementById('refreshLogsContainer');
            const listEl = document.getElementById('refreshLogsList');
            if (!container || !listEl) return;
            const force = Boolean(forceRefresh);

            // Soft re-entry: always return warm cache; paint only while refresh modal is open.
            if (!force && refreshModalHistoryCache) {
                if (isRefreshModalOpen()) {
                    renderRefreshModalHistory(refreshModalHistoryCache);
                }
                return refreshModalHistoryCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so modal refresh always starts a true network GET.
            if (refreshModalHistoryLoadPromise) {
                if (!force || refreshModalHistoryLoadForce) {
                    return refreshModalHistoryLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                refreshModalHistoryLoadPromise = null;
                refreshModalHistoryLoadForce = false;
            }

            refreshModalHistoryLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/accounts/refresh-logs?limit=1000');
                    const data = await response.json();

                    if (refreshModalHistoryLoadPromise !== request) {
                        return refreshModalHistoryCache;
                    }
                    if (data && data.success) {
                        // Always warm soft cache; paint only while refresh modal is open.
                        refreshModalHistoryCache = data;
                        if (isRefreshModalOpen()) {
                            renderRefreshModalHistory(data);
                        }
                    }
                    return refreshModalHistoryCache;
                } catch (error) {
                    if (refreshModalHistoryLoadPromise !== request) {
                        return refreshModalHistoryCache;
                    }
                    if (isRefreshModalOpen()) {
                        showToast(translateAppTextLocal('加载刷新历史失败'), 'error');
                    }
                    return refreshModalHistoryCache;
                }
            })();

            refreshModalHistoryLoadPromise = request;
            try {
                return await request;
            } finally {
                if (refreshModalHistoryLoadPromise === request) {
                    refreshModalHistoryLoadPromise = null;
                    refreshModalHistoryLoadForce = false;
                }
            }
        }

        // 隐藏刷新历史
        function hideRefreshLogs() {
            document.getElementById('refreshLogsContainer').style.display = 'none';
        }

        // ==================== 页面级：刷新日志 ====================

        // Soft-load caches for log pages (navigate re-entry). Mutations invalidate.
        let refreshLogPageCache = null;
        let refreshLogPageLoadPromise = null;
        // True when the in-flight page refresh-log GET was started with forceRefresh.
        let refreshLogPageLoadForce = false;
        let auditLogPageCache = null;
        let auditLogPageLoadPromise = null;
        // True when the in-flight audit-log GET was started with forceRefresh.
        let auditLogPageLoadForce = false;

        function invalidateRefreshLogPageCache() {
            refreshLogPageCache = null;
            refreshLogPageLoadPromise = null;
            refreshLogPageLoadForce = false;
            // Modal history (limit=1000) is also stale after refresh mutations.
            refreshModalHistoryCache = null;
            refreshModalHistoryLoadPromise = null;
            refreshModalHistoryLoadForce = false;
        }

        function renderRefreshLogPage(data) {
            const container = document.getElementById('refreshLogContainer');
            if (!container) return;
            const logs = data && Array.isArray(data.logs) ? data.logs : [];
            if (logs.length > 0) {
                container.innerHTML = `
                    <div style="padding:0.6rem 1rem;font-size:0.78rem;color:var(--text-muted);border-bottom:1px solid var(--border-light);">
                        ${translateAppTextLocal(`共 ${logs.length} 条记录`)}
                    </div>
                    <div class="dashboard-list-wrap">
                        ${logs.map(log => {
                            const isSuccess = log.status === 'success';
                            const statusBadge = isSuccess
                                ? `<span class="badge" style="background:var(--clr-jade);color:white;">${translateAppTextLocal('成功')}</span>`
                                : `<span class="badge" style="background:var(--clr-danger);color:white;">${translateAppTextLocal('失败')}</span>`;
                            const typeText = translateAppTextLocal(
                                log.refresh_type === 'manual' ? '手动' : (log.refresh_type === 'scheduled' ? '定时' : (log.refresh_type || '-'))
                            );
                            return `
                                <div style="padding:0.75rem 1rem;border-bottom:1px solid var(--border-light);display:flex;align-items:center;gap:0.8rem;">
                                    <div style="flex:1;min-width:0;">
                                        <div style="font-weight:600;font-size:0.85rem;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(log.account_email || '-')}</div>
                                        <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px;">${formatDateTime(log.created_at)} · ${escapeHtml(typeText)}</div>
                                        ${log.error_message ? `<div style="font-size:0.72rem;color:var(--clr-danger);margin-top:4px;padding:4px 8px;background:rgba(185,28,28,0.06);border-radius:4px;">${escapeHtml(log.error_message)}</div>` : ''}
                                    </div>
                                    ${statusBadge}
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            } else {
                container.innerHTML = (
                    `<div class="ui-empty">`
                    + `<div class="ui-empty-title">${translateAppTextLocal('还没有刷新记录')}</div>`
                    + `<div class="ui-empty-desc">${translateAppTextLocal('执行全量刷新或单账号刷新后，Token 刷新历史会出现在这里。')}</div>`
                    + `<button type="button" class="btn btn-primary" onclick="showRefreshModal()">${translateAppTextLocal('去刷新 Token')}</button>`
                    + `</div>`
                );
            }
        }

        function isCurrentRefreshLogPage() {
            return typeof currentPage !== 'undefined' && currentPage === 'refresh-log';
        }

        async function loadRefreshLogPage(forceRefresh = false) {
            const container = document.getElementById('refreshLogContainer');
            if (!container) return;
            const force = Boolean(forceRefresh);

            // Soft re-entry: always return warm cache; paint only while still on refresh-log.
            if (!force && refreshLogPageCache) {
                if (isCurrentRefreshLogPage()) {
                    renderRefreshLogPage(refreshLogPageCache);
                }
                return refreshLogPageCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so post-mutation page reload starts a true network GET.
            if (refreshLogPageLoadPromise) {
                if (!force || refreshLogPageLoadForce) {
                    return refreshLogPageLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                refreshLogPageLoadPromise = null;
                refreshLogPageLoadForce = false;
            }

            // Loading chrome only while refresh-log page is active.
            if (isCurrentRefreshLogPage()) {
                container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> ${translateAppTextLocal('加载中…')}</div>`;
            }

            refreshLogPageLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/accounts/refresh-logs?limit=200');
                    const data = await response.json();
                    if (refreshLogPageLoadPromise !== request) {
                        return refreshLogPageCache;
                    }
                    if (data && data.success) {
                        // Always warm soft cache; paint only on refresh-log page.
                        refreshLogPageCache = data;
                        if (isCurrentRefreshLogPage()) {
                            renderRefreshLogPage(data);
                        }
                    } else {
                        refreshLogPageCache = { success: true, logs: [] };
                        if (isCurrentRefreshLogPage()) {
                            renderRefreshLogPage(refreshLogPageCache);
                        }
                    }
                    return refreshLogPageCache;
                } catch (error) {
                    if (refreshLogPageLoadPromise !== request) {
                        return refreshLogPageCache;
                    }
                    if (isCurrentRefreshLogPage()) {
                        container.innerHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><p>${translateAppTextLocal('加载刷新历史失败')}</p></div>`;
                    }
                    return refreshLogPageCache;
                }
            })();

            refreshLogPageLoadPromise = request;
            try {
                return await request;
            } finally {
                if (refreshLogPageLoadPromise === request) {
                    refreshLogPageLoadPromise = null;
                    refreshLogPageLoadForce = false;
                }
            }
        }

        // ==================== 页面级：审计日志 ====================

        async function showBatchRefreshConfirm() {
            if (selectedAccountIds.size === 0) {
                showToast(translateAppTextLocal('请选择要刷新 Token 的账号'), 'error');
                return;
            }

            const accountIds = Array.from(selectedAccountIds);

            // 检查是否有 IMAP 账号（通过 data-account-type 属性判断）
            let imapCount = 0;
            const allCheckboxes = document.querySelectorAll('.account-select-checkbox');
            allCheckboxes.forEach(cb => {
                const id = parseInt(cb.dataset.accountId || cb.value);
                if (accountIds.includes(id)) {
                    const card = cb.closest('[data-account-type]');
                    if (card && card.dataset.accountType === 'imap') {
                        imapCount++;
                    }
                }
            });

            const outlookCount = accountIds.length - imapCount;

            if (outlookCount === 0) {
                showToast(translateAppTextLocal('所选账号均为 IMAP 账号，不支持 Token 刷新'), 'warning');
                return;
            }

            let confirmMsg;
            if (imapCount > 0) {
                confirmMsg = `已选 ${accountIds.length} 个账号，其中 ${imapCount} 个 IMAP 账号不支持 Token 刷新将被跳过，确认刷新 ${outlookCount} 个 Outlook 账号？`;
            } else {
                confirmMsg = `确认刷新选中的 ${accountIds.length} 个账号的 Token？`;
            }

            if (!confirm(confirmMsg)) {
                return;
            }

            await batchRefreshSelected(accountIds);
        }

        // 执行指定账号批量刷新 Token（SSE 流式）
        async function batchRefreshSelected(accountIds) {
            await initCSRFToken();

            // 显示常驻进度 Toast
            const toastId = 'batch-refresh-toast-' + Date.now();
            showPersistentToast(
                toastId,
                translateAppTextLocal('🔄 正在刷新 Token... 0 / ' + accountIds.length)
            );

            const controller = new AbortController();
            const OVERALL_TIMEOUT_MS = 120000; // 2 分钟整体超时
            const HEARTBEAT_TIMEOUT_MS = 30000; // 30 秒心跳超时
            let overallTimeoutId = null;
            let heartbeatTimeoutId = null;
            let isAborted = false;

            function clearTimers() {
                if (overallTimeoutId) clearTimeout(overallTimeoutId);
                if (heartbeatTimeoutId) clearTimeout(heartbeatTimeoutId);
            }

            function startHeartbeatTimer() {
                if (heartbeatTimeoutId) clearTimeout(heartbeatTimeoutId);
                heartbeatTimeoutId = setTimeout(() => {
                    if (!isAborted) {
                        isAborted = true;
                        controller.abort();
                    }
                }, HEARTBEAT_TIMEOUT_MS);
            }

            overallTimeoutId = setTimeout(() => {
                if (!isAborted) {
                    isAborted = true;
                    controller.abort();
                }
            }, OVERALL_TIMEOUT_MS);

            try {
                const response = await fetch('/api/accounts/refresh/selected', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_ids: accountIds }),
                    signal: controller.signal
                });

                if (!response.ok || !response.body) {
                    clearTimers();
                    dismissPersistentToast(toastId);
                    showToast(translateAppTextLocal('刷新请求失败，请稍后重试'), 'error');
                    return;
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let totalCount = accountIds.length;
                let streamDone = false;

                startHeartbeatTimer();

                while (!streamDone) {
                    const { done, value } = await reader.read();
                    if (done) {
                        streamDone = true;
                        break;
                    }

                    startHeartbeatTimer();

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // 保留未完整的行

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        let data;
                        try {
                            data = JSON.parse(line.slice(6));
                        } catch (e) {
                            continue;
                        }

                        handleBatchRefreshSSEEvent(data, toastId, totalCount);

                        if (data.type === 'start') {
                            totalCount = data.total;
                        }
                        if (data.type === 'complete' || data.type === 'error') {
                            streamDone = true;
                            break;
                        }
                    }
                }

                clearTimers();
            } catch (error) {
                clearTimers();
                dismissPersistentToast(toastId);
                if (error.name === 'AbortError') {
                    if (isAborted) {
                        showToast(translateAppTextLocal('刷新请求超时，请检查网络或代理配置后重试'), 'warning');
                    } else {
                        showToast(translateAppTextLocal('刷新请求已取消'), 'info');
                    }
                } else {
                    showToast(translateAppTextLocal('刷新执行出现错误，请稍后重试'), 'error');
                }
                console.error('batchRefreshSelected error:', error);
            }
        }

        function buildSelectedRefreshActionGuide(errorPayload) {
            const lang = getUiLanguage();
            const code = String(errorPayload && errorPayload.code || '').trim();
            const traceId = String(errorPayload && errorPayload.trace_id || '').trim();
            const details = errorPayload && errorPayload.details;
            const detailText = typeof details === 'string'
                ? details
                : (details ? JSON.stringify(details) : '');

            if (code === 'REFRESH_CONFLICT') {
                if (lang === 'en') {
                    return [
                        'Another refresh task is running. Wait for it to finish before retrying.',
                        'Go to refresh logs and verify the current task has completed.',
                        traceId ? `If it keeps happening, share Trace ID: ${traceId}` : 'If it keeps happening, capture and share the Trace ID.',
                    ];
                }
                return [
                    '当前已有刷新任务在执行，请等待其完成后再重试。',
                    '先到刷新历史确认当前任务已结束。',
                    traceId ? `若持续出现，请反馈 Trace ID：${traceId}` : '若持续出现，请记录并反馈 Trace ID。',
                ];
            }

            if (code === 'REFRESH_SELECTED_STREAM_FAILED') {
                if (lang === 'en') {
                    return [
                        'Recheck selected accounts (status, account type, and authorization fields).',
                        'Verify network/proxy connectivity and retry selected refresh.',
                        traceId ? `If retry fails, share Trace ID: ${traceId}` : 'If retry fails, capture and share the Trace ID.',
                    ];
                }
                return [
                    '请先检查所选账号状态、账号类型与授权字段是否完整。',
                    '请检查网络/代理连通性后重新执行“Selected 刷新”。',
                    traceId ? `若重试仍失败，请反馈 Trace ID：${traceId}` : '若重试仍失败，请记录并反馈 Trace ID。',
                ];
            }

            if (/token|refresh|aadsts|invalid_grant|proxy|timeout|network/i.test(detailText)) {
                if (lang === 'en') {
                    return [
                        'Re-authorize or refresh credentials for the affected account(s).',
                        'Check network/proxy settings and retry once.',
                        traceId ? `Still failing? Share Trace ID: ${traceId}` : 'Still failing? Capture and share the Trace ID.',
                    ];
                }
                return [
                    '请重新授权或更新异常账号的凭据。',
                    '请检查网络/代理配置后重试一次。',
                    traceId ? `仍失败请反馈 Trace ID：${traceId}` : '仍失败请记录并反馈 Trace ID。',
                ];
            }

            return lang === 'en'
                ? [
                    'Retry the selected refresh once after reloading the page.',
                    'If the same error repeats, open error details and keep the Trace ID.',
                    traceId ? `Current Trace ID: ${traceId}` : 'Keep the Trace ID from error details for backend troubleshooting.',
                ]
                : [
                    '请刷新页面后重试一次“Selected 刷新”。',
                    '若同样错误再次出现，请打开详情并保留 Trace ID。',
                    traceId ? `当前 Trace ID：${traceId}` : '请保留错误详情中的 Trace ID 供后端排查。',
                ];
        }

        function buildSelectedRefreshErrorSummary(errorPayload) {
            const code = String(errorPayload && errorPayload.code || '').trim();
            const rawMessage = window.resolveApiErrorMessage
                ? window.resolveApiErrorMessage(errorPayload, '刷新执行失败', 'Refresh failed')
                : ((errorPayload && (errorPayload.message || errorPayload.message_en)) || '刷新执行失败');
            const guide = buildSelectedRefreshActionGuide(errorPayload);
            const guideText = guide.map((item, idx) => `${idx + 1}. ${item}`).join('\n');
            const codeLine = code ? `\n[Code] ${code}` : '';
            return `${rawMessage}${codeLine}\n\n建议处理：\n${guideText}`;
        }

        // 处理批量刷新 SSE 事件
        function handleBatchRefreshSSEEvent(data, toastId, totalCount) {
            if (data.type === 'start') {
                const total = data.total;
                updatePersistentToast(
                    toastId,
                    translateAppTextLocal('🔄 正在刷新 Token... 0 / ' + total)
                );

            } else if (data.type === 'progress') {
                if (data.result === 'processing') {
                    // 刚开始处理该账号
                    updatePersistentToast(
                        toastId,
                        translateAppTextLocal('🔄 正在刷新 Token... ' + (data.current - 1) + ' / ' + data.total)
                    );
                } else {
                    // 该账号刷新完成（success 或 failed）
                    updatePersistentToast(
                        toastId,
                        translateAppTextLocal('🔄 正在刷新 Token... ' + data.current + ' / ' + data.total)
                    );
                    // 更新对应账号卡片状态
                    if (data.account_id) {
                        updateAccountCardRefreshStatus(data.account_id, data.result, data.last_refresh_at, data.error_message);
                    }
                }

            } else if (data.type === 'complete') {
                const { total, success_count, failed_count, failed_list } = data;
                dismissPersistentToast(toastId);

                if (failed_count === 0) {
                    showToast(
                        translateAppTextLocal('✅ Token 刷新完成：成功 ' + success_count + ' 个'),
                        'success'
                    );
                } else {
                    let detail = null;
                    if (failed_list && failed_list.length > 0) {
                        detail = translateAppTextLocal('失败账号：') + '\n' + failed_list.map(f =>
                            `${f.email}：${f.error || translateAppTextLocal('未知错误')}`
                        ).join('\n');
                    }
                    showToast(
                        translateAppTextLocal(
                            '⚠️ Token 刷新完成：成功 ' + success_count + ' 个，失败 ' + failed_count + ' 个'
                        ),
                        'warning',
                        detail,
                        true
                    );
                }

                // 刷新账号列表以同步状态
                if (currentGroupId) {
                    loadAccountsByGroup(currentGroupId, true);
                }
                if (typeof invalidateRefreshLogPageCache === 'function') {
                    invalidateRefreshLogPageCache();
                }
                if (typeof invalidateAuditLogPageCache === 'function') {
                    invalidateAuditLogPageCache();
                }
                if (typeof invalidateRefreshStatsCache === 'function') {
                    invalidateRefreshStatsCache();
                }

            } else if (data.type === 'error') {
                dismissPersistentToast(toastId);
                const errCode = data.error && data.error.code;
                if (errCode === 'REFRESH_CONFLICT') {
                    showToast(buildSelectedRefreshErrorSummary(data.error), 'warning', data.error || null, true);
                } else {
                    showToast(buildSelectedRefreshErrorSummary(data.error || {}), 'error', data.error || null, true);
                }
            }
        }

        // 更新账号卡片的刷新状态显示
        function updateAccountCardRefreshStatus(accountId, result, lastRefreshAt, errorMessage) {
            // 标准视图：查找 data-account-id 匹配的卡片
            const cards = document.querySelectorAll(`[data-account-id="${accountId}"]`);
            cards.forEach(card => {
                // 更新刷新状态徽章（如果存在）
                const refreshBadge = card.querySelector('.refresh-status-badge, [data-refresh-status]');
                if (refreshBadge) {
                    refreshBadge.textContent = result === 'success' ? '✅' : '❌';
                    refreshBadge.title = result === 'success' ? '刷新成功' : (errorMessage || '刷新失败');
                }
                // 更新最后刷新时间（如果存在）
                if (lastRefreshAt) {
                    const timeEl = card.querySelector('[data-refresh-time], .last-refresh-at');
                    if (timeEl) {
                        timeEl.textContent = formatUiRelativeTime(lastRefreshAt, '刚刚', 'Just now');
                        timeEl.title = lastRefreshAt;
                    }
                }
            });
        }

        // 显示持久 Toast（用于进度展示）
        function refreshCurrentMailboxIfNeeded(email, folder, data) {
            if (currentAccount !== email || currentFolder !== folder) return;

            const sortedEmails = (typeof sortEmailsByNewestFirst === 'function')
                ? sortEmailsByNewestFirst(data.emails || [])
                : (data.emails || []);

            currentEmails = sortedEmails;
            const emailCountEl = document.getElementById('emailCount');
            if (emailCountEl) emailCountEl.textContent = `(${currentEmails.length})`;
            renderEmailList(currentEmails);
        }

        let batchActionType = ''; // 'add' or 'remove'
        let batchTagContext = { scopedAccountIds: null };

        // 显示批量打标模态框
