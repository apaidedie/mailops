// split from admin.js → audit.js
        function invalidateAuditLogPageCache() {
            auditLogPageCache = null;
            auditLogPageLoadPromise = null;
            auditLogPageLoadForce = false;
        }

        // Cross-module mutations (settings/inventory/refresh) drop audit soft cache.
        window.invalidateAuditLogPageCache = invalidateAuditLogPageCache;

        function translateAuditDetailValue(value) {
            if (typeof value === 'string') {
                return translateAppTextLocal(value);
            }
            if (Array.isArray(value)) {
                return value.map(translateAuditDetailValue);
            }
            if (value && typeof value === 'object') {
                return Object.fromEntries(
                    Object.entries(value).map(([key, nestedValue]) => [key, translateAuditDetailValue(nestedValue)])
                );
            }
            return value;
        }

        function formatAuditDetailText(details) {
            if (details == null) {
                return '';
            }
            if (typeof details === 'string') {
                const trimmed = details.trim();
                if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
                    try {
                        return JSON.stringify(translateAuditDetailValue(JSON.parse(trimmed)));
                    } catch (error) {
                        return translateAppTextLocal(details);
                    }
                }
                return translateAppTextLocal(details);
            }
            if (typeof details === 'object') {
                try {
                    return JSON.stringify(translateAuditDetailValue(details));
                } catch (error) {
                    return translateAppTextLocal(String(details));
                }
            }
            return translateAppTextLocal(String(details));
        }

        function renderAuditLogPage(data) {
            const container = document.getElementById('auditLogContainer');
            if (!container) return;
            const logs = data && Array.isArray(data.logs) ? data.logs : [];
            if (logs.length > 0) {
                container.innerHTML = `
                    <div style="padding:0.6rem 1rem;font-size:0.78rem;color:var(--text-muted);border-bottom:1px solid var(--border-light);">
                        ${translateAppTextLocal(`共 ${data.total || logs.length} 条记录`)}
                    </div>
                    <div class="dashboard-list-wrap">
                        ${logs.map(log => {
                            const actionColor = log.action === 'delete' ? 'var(--clr-danger)' : (log.action === 'create' ? 'var(--clr-jade)' : 'var(--clr-primary)');
                            const actionLabel = translateAppTextLocal(log.action || '-');
                            const resourceTypeLabel = translateAppTextLocal(log.resource_type || '-');
                            const detailText = formatAuditDetailText(log.details);
                            return `
                                <div style="padding:0.75rem 1rem;border-bottom:1px solid var(--border-light);">
                                    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:4px;">
                                        <span class="badge" style="background:${actionColor};color:white;font-size:0.68rem;">${escapeHtml(actionLabel)}</span>
                                        <span style="font-size:0.78rem;color:var(--text-muted);">${escapeHtml(resourceTypeLabel)}</span>
                                        <span style="font-size:0.72rem;color:var(--text-muted);margin-left:auto;">${formatDateTime(log.created_at)}</span>
                                    </div>
                                    <div style="font-size:0.82rem;color:var(--text);">${escapeHtml(log.resource_id || '-')}</div>
                                    ${detailText ? `<div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px;word-break:break-all;">${escapeHtml(detailText).substring(0, 200)}</div>` : ''}
                                    <div style="font-size:0.68rem;color:var(--text-muted);margin-top:2px;">IP: ${escapeHtml(log.user_ip || '-')} ${log.trace_id ? '· trace: ' + escapeHtml(log.trace_id) : ''}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            } else {
                container.innerHTML = `<div class="empty-state"><span class="empty-icon">📭</span><p>${translateAppTextLocal('暂无审计记录')}</p></div>`;
            }
        }

        function isCurrentAuditLogPage() {
            return typeof currentPage !== 'undefined' && currentPage === 'audit';
        }

        async function loadAuditLogPage(forceRefresh = false) {
            const container = document.getElementById('auditLogContainer');
            if (!container) return;
            const force = Boolean(forceRefresh);

            // Soft re-entry: always return warm cache; paint only while still on audit page.
            if (!force && auditLogPageCache) {
                if (isCurrentAuditLogPage()) {
                    renderAuditLogPage(auditLogPageCache);
                }
                return auditLogPageCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so post-mutation page reload starts a true network GET.
            if (auditLogPageLoadPromise) {
                if (!force || auditLogPageLoadForce) {
                    return auditLogPageLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                auditLogPageLoadPromise = null;
                auditLogPageLoadForce = false;
            }

            // Loading chrome only while audit page is active.
            if (isCurrentAuditLogPage()) {
                container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> ${translateAppTextLocal('加载中…')}</div>`;
            }

            auditLogPageLoadForce = force;
            const request = (async () => {
                try {
                    const response = await fetch('/api/audit-logs?limit=200');
                    const data = await response.json();
                    if (auditLogPageLoadPromise !== request) {
                        return auditLogPageCache;
                    }
                    if (data && data.success) {
                        // Always warm soft cache; paint only on audit page.
                        auditLogPageCache = data;
                        if (isCurrentAuditLogPage()) {
                            renderAuditLogPage(data);
                        }
                    } else {
                        auditLogPageCache = { success: true, logs: [], total: 0 };
                        if (isCurrentAuditLogPage()) {
                            renderAuditLogPage(auditLogPageCache);
                        }
                    }
                    return auditLogPageCache;
                } catch (error) {
                    if (auditLogPageLoadPromise !== request) {
                        return auditLogPageCache;
                    }
                    if (isCurrentAuditLogPage()) {
                        container.innerHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><p>${translateAppTextLocal('加载审计日志失败')}</p></div>`;
                    }
                    return auditLogPageCache;
                }
            })();

            auditLogPageLoadPromise = request;
            try {
                return await request;
            } finally {
                if (auditLogPageLoadPromise === request) {
                    auditLogPageLoadPromise = null;
                    auditLogPageLoadForce = false;
                }
            }
        }

        // 格式化日期时间
