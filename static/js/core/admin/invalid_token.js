// split from admin.js → invalid_token.js
        function resetInvalidTokenGovernanceState() {
            latestInvalidTokenDetectedCount = 0;
            const container = document.getElementById('invalidTokenGovernanceContainer');
            if (container) container.style.display = 'none';
            const summary = document.getElementById('invalidTokenSummary');
            if (summary) summary.style.display = 'none';
            const listWrap = document.getElementById('invalidTokenCandidateListWrap');
            if (listWrap) listWrap.style.display = 'none';
        }

        function invalidateInvalidTokenGovernanceCache() {
            invalidTokenGovernanceCandidates = [];
            invalidTokenGovernanceCandidatesLoaded = false;
            invalidTokenGovernanceLoadPromise = null;
            invalidTokenGovernanceLoadForce = false;
        }

        /** 显示检测摘要横幅（刷新完成有 invalid token 时调用） */
        function showInvalidTokenDetectionSummary(count, failedList) {
            const summary = document.getElementById('invalidTokenSummary');
            const summaryText = document.getElementById('invalidTokenSummaryText');
            if (!summary || !summaryText) return;

            summaryText.textContent = translateAppTextLocal(
                '检测到 ' + count + ' 个疑似失效 Token 的账号，需要治理处理'
            );
            summary.style.display = 'block';

            // 同时显示治理面板容器
            const container = document.getElementById('invalidTokenGovernanceContainer');
            if (container) container.style.display = 'block';
        }

        /** 隐藏治理面板 */
        function hideInvalidTokenGovernance() {
            const container = document.getElementById('invalidTokenGovernanceContainer');
            if (container) container.style.display = 'none';
            const summary = document.getElementById('invalidTokenSummary');
            if (summary) summary.style.display = 'none';
            const listWrap = document.getElementById('invalidTokenCandidateListWrap');
            if (listWrap) listWrap.style.display = 'none';
        }

        function applyInvalidTokenGovernanceCandidates(candidates, options = {}) {
            const { keepVisibleWhenEmpty = false } = options;
            invalidTokenGovernanceCandidates = Array.isArray(candidates) ? candidates : [];
            const count = invalidTokenGovernanceCandidates.length;

            // 更新数量标签
            const countEl = document.getElementById('invalidTokenCandidateCount');
            if (countEl) {
                countEl.textContent = translateAppTextLocal(count + ' 个');
            }

            if (count === 0) {
                if (!keepVisibleWhenEmpty) {
                    hideInvalidTokenGovernance();
                }
                return;
            }

            // 渲染候选列表
            const listEl = document.getElementById('invalidTokenCandidateList');
            const listWrap = document.getElementById('invalidTokenCandidateListWrap');

            if (!listEl || !listWrap) return;

            let html = '';
            invalidTokenGovernanceCandidates.forEach(item => {
                const statusBadge = item.account_status === 'inactive'
                    ? '<span style="background-color:#fbbf24;color:#78350f;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + translateAppTextLocal('已停用') + '</span>'
                    : '<span style="background-color:#34d399;color:#064e3b;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + translateAppTextLocal('活跃') + '</span>';

                html += `
                    <div style="padding:10px 12px;border-bottom:1px solid #e5e5e5;display:flex;justify-content:space-between;align-items:start;gap:10px;">
                        <div style="flex:1;min-width:0;">
                            <div style="font-weight:600;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${escapeHtml(item.account_email)}">${escapeHtml(item.account_email)}</div>
                            <div style="font-size:12px;color:#dc3545;margin-bottom:2px;word-break:break-all;">${escapeHtml(item.error_message || translateAppTextLocal('未知错误'))}</div>
                            <div style="font-size:11px;color:#999;">${translateAppTextLocal('原因')}: ${escapeHtml(item.reason_label || item.reason_code || '-')} ｜ ${translateAppTextLocal('刷新时间')}: ${formatDateTime(item.created_at)}</div>
                        </div>
                        <div style="flex-shrink:0;display:flex;align-items:center;gap:4px;">
                            ${statusBadge}
                        </div>
                    </div>
                `;
            });

            listEl.innerHTML = html;
            listWrap.style.display = 'block';

            // 确保容器可见
            const container = document.getElementById('invalidTokenGovernanceContainer');
            if (container) container.style.display = 'block';
        }

        /** 从后端加载治理候选列表并渲染（soft-load + coalesce） */
        async function loadInvalidTokenGovernanceCandidates(options = {}) {
            const {
                forceRefresh = false,
                keepVisibleWhenEmpty = false,
                silentWhenEmpty = false
            } = options;
            const force = Boolean(forceRefresh);

            // Soft re-entry: always return warm candidates; paint only while refresh modal open.
            if (!force && invalidTokenGovernanceCandidatesLoaded) {
                if (typeof isRefreshModalOpen === 'function' ? isRefreshModalOpen() : true) {
                    applyInvalidTokenGovernanceCandidates(invalidTokenGovernanceCandidates, {
                        keepVisibleWhenEmpty
                    });
                }
                return invalidTokenGovernanceCandidates;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so post-mutation reload starts a true network GET.
            if (invalidTokenGovernanceLoadPromise) {
                if (!force || invalidTokenGovernanceLoadForce) {
                    return invalidTokenGovernanceLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                invalidTokenGovernanceLoadPromise = null;
                invalidTokenGovernanceLoadForce = false;
            }

            invalidTokenGovernanceLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/accounts/invalid-token-candidates?limit=200');
                    const data = await response.json();

                    if (invalidTokenGovernanceLoadPromise !== request) {
                        return invalidTokenGovernanceCandidates;
                    }
                    if (!data.success) {
                        if (!silentWhenEmpty && (typeof isRefreshModalOpen === 'function' ? isRefreshModalOpen() : true)) {
                            showToast(translateAppTextLocal('加载失效 Token 候选失败'), 'error');
                        }
                        return invalidTokenGovernanceCandidates;
                    }

                    // Always warm soft cache; paint only while refresh modal is open.
                    invalidTokenGovernanceCandidatesLoaded = true;
                    invalidTokenGovernanceCandidates = Array.isArray(data.candidates) ? data.candidates : [];
                    if (typeof isRefreshModalOpen === 'function' ? isRefreshModalOpen() : true) {
                        applyInvalidTokenGovernanceCandidates(invalidTokenGovernanceCandidates, {
                            keepVisibleWhenEmpty
                        });
                    }
                    return invalidTokenGovernanceCandidates;
                } catch (error) {
                    if (invalidTokenGovernanceLoadPromise !== request) {
                        return invalidTokenGovernanceCandidates;
                    }
                    console.error('加载失效 Token 候选失败:', error);
                    if (!silentWhenEmpty && (typeof isRefreshModalOpen === 'function' ? isRefreshModalOpen() : true)) {
                        showToast(translateAppTextLocal('加载失效 Token 候选失败'), 'error');
                    }
                    return invalidTokenGovernanceCandidates;
                }
            })();

            invalidTokenGovernanceLoadPromise = request;
            try {
                return await request;
            } finally {
                if (invalidTokenGovernanceLoadPromise === request) {
                    invalidTokenGovernanceLoadPromise = null;
                    invalidTokenGovernanceLoadForce = false;
                }
            }
        }

        /** 批量将失效 Token 候选账号置为停用 */
        async function batchSetInvalidTokenInactive() {
            if (invalidTokenGovernanceCandidates.length === 0) {
                showToast(translateAppTextLocal('没有需要处理的候选账号'), 'warning');
                return;
            }

            // 只取状态不是 inactive 的账号
            const targetCandidates = invalidTokenGovernanceCandidates.filter(c => c.account_status !== 'inactive');
            if (targetCandidates.length === 0) {
                showToast(translateAppTextLocal('所有候选账号已经是停用状态'), 'info');
                return;
            }

            const accountIds = targetCandidates.map(c => c.account_id);
            // Pass Chinese source; window.confirm is wrapped to translateAppText.
            const confirmed = confirm(`确定要将 ${accountIds.length} 个失效 Token 账号置为停用吗？停用后账号将不再参与刷新和使用。`);
            if (!confirmed) return;

            await initCSRFToken();

            try {
                const response = await fetch('/api/accounts/batch-update-status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_ids: accountIds, status: 'inactive' })
                });

                const data = await response.json();
                if (data.success) {
                    showToast(pickApiMessage(data, data.message, '批量停用成功'), 'success');
                    if (typeof window.invalidateAccountDetailCacheMany === 'function') {
                        window.invalidateAccountDetailCacheMany(accountIds);
                    }
                    // 刷新候选列表与统计（force after mutation）
                    await loadInvalidTokenGovernanceCandidates({
                        forceRefresh: true,
                        keepVisibleWhenEmpty: true,
                        silentWhenEmpty: true
                    });
                    await loadRefreshStats(true);
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                } else {
                    handleApiError(data, '批量停用失败');
                }
            } catch (error) {
                console.error('批量停用失败:', error);
                showToast(translateAppTextLocal('批量停用请求失败'), 'error');
            }
        }

        /** 批量删除失效 Token 候选账号（二次确认） */
        async function batchDeleteInvalidTokenCandidates() {
            if (invalidTokenGovernanceCandidates.length === 0) {
                showToast(translateAppTextLocal('没有需要处理的候选账号'), 'warning');
                return;
            }

            const accountIds = invalidTokenGovernanceCandidates.map(c => c.account_id);
            const emailPreview = invalidTokenGovernanceCandidates.slice(0, 3).map(c => c.account_email).join(', ')
                + (accountIds.length > 3 ? ` 等 ${accountIds.length} 个` : '');

            const confirmed = confirm(
                `⚠️ 危险操作：确定要删除 ${accountIds.length} 个失效 Token 账号吗？\n\n涉及账号：${emailPreview}\n\n此操作不可撤销，请确认！`
            );
            if (!confirmed) return;

            // 二次确认
            const doubleConfirmed = confirm('再次确认：删除账号将同时清除所有相关数据，是否继续？');
            if (!doubleConfirmed) return;

            await initCSRFToken();

            try {
                const response = await fetch('/api/accounts/batch-delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_ids: accountIds })
                });

                const data = await response.json();
                if (data.success) {
                    showToast(pickApiMessage(data, data.message, '批量删除成功'), 'success');
                    if (typeof window.invalidateAccountDetailCacheMany === 'function') {
                        window.invalidateAccountDetailCacheMany(accountIds);
                    }
                    // Drop soft mail list/detail for deleted mailboxes (emails known on candidates).
                    if (typeof window.clearEmailListCacheForMailboxes === 'function') {
                        window.clearEmailListCacheForMailboxes(
                            invalidTokenGovernanceCandidates.map(c => c.account_email).filter(Boolean)
                        );
                    }
                    if (typeof window.invalidateUnifiedMailboxDirectoryCache === 'function') {
                        window.invalidateUnifiedMailboxDirectoryCache();
                    }
                    hideInvalidTokenGovernance();
                    // Candidates deleted — drop soft cache so next open refetches.
                    invalidateInvalidTokenGovernanceCache();
                    await loadRefreshStats(true);
                    if (currentGroupId) {
                        invalidateAccountsCache(currentGroupId);
                        loadAccountsByGroup(currentGroupId, true);
                    }
                    loadGroups(true);
                } else {
                    handleApiError(data, '批量删除失败');
                }
            } catch (error) {
                console.error('批量删除失败:', error);
                showToast(translateAppTextLocal('批量删除请求失败'), 'error');
            }
        }

        // ==================== 刷新统计与全量刷新 ====================

        // Soft-load cache for refresh modal stats (re-open without mutations).
        let refreshStatsCache = null;
        let refreshStatsLoadPromise = null;
        // True when the in-flight refresh-stats GET was started with forceRefresh.
        let refreshStatsLoadForce = false;

