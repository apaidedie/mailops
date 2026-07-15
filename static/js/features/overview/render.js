// split from overview.js → render.js
function renderOverviewTab(tabId, data) {
    const renderers = {
        summary: renderOverviewSummary,
        verification: renderVerificationStats,
        'external-api': renderExternalApiStats,
        pool: renderPoolStats,
        activity: renderActivityStats
    };
    const renderer = renderers[tabId];
    if (renderer) renderer(data || {});
}

function renderOverviewLoading(tabId) {
    const container = getOverviewContainer(tabId);
    if (!container) return;
    container.innerHTML = `<div class="ov-empty">${esc(ovT('加载中…'))}</div>`;
}

function renderOverviewError(tabId) {
    const container = getOverviewContainer(tabId);
    if (!container) return;
    container.innerHTML = `<div class="ov-empty">${esc(ovT('加载失败'))}</div>`;
}

function renderOverviewSummary(data) {
    const container = getOverviewContainer('summary');
    if (!container) return;

    const accountStatus = data.account_status || {};
    const pool = data.pool_snapshot || {};
    const refresh = data.refresh_health || {};
    const kpi = data.kpi || {};

    container.innerHTML = `
        ${renderOverviewCommandCenter(data.command_center || {})}
        <div class="kpi-row">
            ${renderKpiCard('总账号数', formatNumber(accountStatus.total || 0), ovLabelValue('活跃', formatNumber(accountStatus.active || 0)), 'kpi-primary')}
            ${renderKpiCard('邮箱池可用', formatNumber(pool.available || 0), ovLabelValue('占用', formatNumber(pool.in_use || 0)), 'kpi-success')}
            ${renderKpiCard('今日验证码提取', formatNumber(kpi.verification_extracted || 0), ovLabelValue('临时邮箱', formatNumber(kpi.temp_emails_active || 0)), 'kpi-accent')}
            ${renderKpiCard('最近刷新成功率', formatPercent(refresh.success_rate_7d || 0), ovLabelValue('失败', formatNumber(refresh.last_fail_count || 0)), 'kpi-warn')}
        </div>
        <div class="two-col">
            ${renderDataCard({
                title: '账号状态分布',
                code: '账号',
                badge: '实时',
                body: renderProgressBlock([
                    { label: '活跃', value: accountStatus.active || 0, total: accountStatus.total || 0, tone: 'jade' },
                    { label: '过期', value: accountStatus.expired || 0, total: accountStatus.total || 0, tone: 'danger' },
                    { label: '待刷新', value: accountStatus.pending_refresh || 0, total: accountStatus.total || 0, tone: 'warn' },
                    { label: '异常', value: accountStatus.error || 0, total: accountStatus.total || 0, tone: 'primary' }
                ])
            })}
            ${renderDataCard({
                title: '邮箱池快照',
                code: '池',
                badge: '供给',
                body: renderProgressBlock([
                    { label: '可用', value: pool.available || 0, total: pool.total || 0, tone: 'jade' },
                    { label: '占用中', value: pool.in_use || 0, total: pool.total || 0, tone: 'primary' },
                    { label: '冷却中', value: pool.cooldown || 0, total: pool.total || 0, tone: 'warn' },
                    { label: '已使用', value: pool.used || 0, total: pool.total || 0, tone: 'accent' }
                ])
            })}
            ${renderDataCard({
                title: '刷新健康',
                code: '刷新',
                badge: '任务',
                body: `
                    <div class="ov-kv"><span>${esc(ovT('最近启动'))}</span><strong>${formatTime(refresh.last_run_at)}</strong></div>
                    <div class="ov-kv"><span>${esc(ovT('最近成功数'))}</span><strong>${formatNumber(refresh.last_success_count || 0)}</strong></div>
                    <div class="ov-kv"><span>${esc(ovT('最近失败数'))}</span><strong>${formatNumber(refresh.last_fail_count || 0)}</strong></div>
                    <div class="ov-kv"><span>${esc(ovT('最近耗时'))}</span><strong>${formatDurationSeconds(refresh.last_duration_s || 0)}</strong></div>
                `
            })}
            ${renderDataCard({
                title: '今日快捷数字',
                code: '今日',
                badge: '当天',
                body: `
                    <div class="ov-kv"><span>${esc(ovT('今日收件'))}</span><strong>${formatNumber(kpi.emails_received || 0)}</strong></div>
                    <div class="ov-kv"><span>${esc(ovT('验证码提取'))}</span><strong>${formatNumber(kpi.verification_extracted || 0)}</strong></div>
                    <div class="ov-kv"><span>${esc(ovT('活跃临时邮箱'))}</span><strong>${formatNumber(kpi.temp_emails_active || 0)}</strong></div>
                `
            })}
        </div>
    `;
}

function renderOverviewCommandCenter(commandCenter) {
    const data = commandCenter || {};
    const inventory = data.mailbox_inventory || {};
    const provider = data.provider_readiness || {};
    const external = data.external_api || {};
    const actions = Array.isArray(data.actions) ? data.actions : [];
    const overallStatus = normalizeOverviewCommandStatus(data.overall_status);
    const overallTone = overviewCommandStatusTone(overallStatus);

    return `
        <section class="ov-command-center" aria-live="polite" aria-label="${esc(ovT('统一邮箱指挥台'))}">
            <div class="ov-command-center-head">
                <div class="ov-command-center-title">
                    <span class="ov-card-code">MAIL</span>
                    <div>
                        <h3>${esc(ovT('统一邮箱指挥台'))}</h3>
                        <p>${esc(ovT('聚合邮箱、Provider 与外部 API 接入状态'))}</p>
                    </div>
                </div>
                <span class="ov-command-status" data-tone="${esc(overallTone)}">${esc(formatOverviewCommandStatus(overallStatus))}</span>
            </div>
            <div class="ov-command-grid">
                ${renderOverviewCommandTile({
                    title: '邮箱库存',
                    status: inventory.status,
                    code: 'INV',
                    rows: [
                        ['全部邮箱', formatNumber(inventory.total || 0)],
                        ['账号邮箱', formatNumber(inventory.account || 0)],
                        ['临时邮箱', formatNumber(inventory.temp || 0)],
                        ['Provider', formatNumber(inventory.providers || 0)]
                    ]
                })}
                ${renderOverviewCommandTile({
                    title: 'Provider 就绪',
                    status: provider.status,
                    code: 'PROV',
                    rows: [
                        ['已就绪', formatNumber(provider.ready || 0)],
                        ['活跃', formatNumber(provider.active || 0)],
                        ['需配置', formatNumber(provider.needs_config || 0)],
                        ['动态创建', formatNumber(provider.dynamic_create || 0)]
                    ]
                })}
                ${renderOverviewCommandTile({
                    title: '外部 API 接入',
                    status: external.status,
                    code: 'API',
                    rows: [
                        ['发现入口', formatOverviewCommandStatus(external.discovery_status)],
                        ['统一邮箱目录', formatOverviewCommandStatus(external.mailbox_directory_status)],
                        ['任务临时邮箱', formatOverviewCommandStatus(external.task_temp_mailbox_status)],
                        ['邮箱池', formatOverviewCommandStatus(external.pool_status)]
                    ]
                })}
                <div class="ov-command-actions" data-status="${esc(overallStatus)}">
                    <div class="ov-command-actions-head">
                        <span class="ov-card-code">NEXT</span>
                        <strong>${esc(ovT('下一步动作'))}</strong>
                    </div>
                    ${renderOverviewCommandActions(actions)}
                </div>
            </div>
        </section>
    `;
}

function renderOverviewCommandTile(options) {
    const config = options || {};
    const status = normalizeOverviewCommandStatus(config.status);
    const tone = overviewCommandStatusTone(status);
    const rows = Array.isArray(config.rows) ? config.rows : [];
    return `
        <div class="ov-command-tile" data-tone="${esc(tone)}">
            <div class="ov-command-tile-head">
                <span class="ov-card-code">${esc(config.code || 'SYS')}</span>
                <strong>${esc(ovT(config.title || ''))}</strong>
                <span class="ov-command-status" data-tone="${esc(tone)}">${esc(formatOverviewCommandStatus(status))}</span>
            </div>
            <div class="ov-command-metrics">
                ${rows.map((row) => `
                    <div class="ov-command-metric">
                        <span>${esc(ovT(row[0] || '--'))}</span>
                        <strong>${esc(row[1] || '--')}</strong>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function renderOverviewCommandActions(actions) {
    const safeActions = Array.isArray(actions) ? actions.filter(Boolean).slice(0, 4) : [];
    if (!safeActions.length) {
        return `<div class="ov-empty">${esc(ovT('暂无动作'))}</div>`;
    }
    return `
        <div class="ov-command-action-list">
            ${safeActions.map((action) => {
                const status = normalizeOverviewCommandStatus(action.status);
                const priority = normalizeOverviewCommandPriority(action.priority);
                return `
                    <div class="ov-command-action" data-status="${esc(status)}" data-priority="${esc(priority)}">
                        <div class="ov-command-action-main">
                            <strong>${esc(ovT(action.label || action.key || '--'))}</strong>
                            <span>${esc(ovT(action.detail || ''))}</span>
                            ${action.target ? `<code>${esc(action.target)}</code>` : ''}
                        </div>
                        <span class="ov-command-action-priority">${esc(ovT(formatOverviewCommandPriority(priority)))}</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function formatOverviewCommandStatus(status) {
    const mapped = {
        ready: '可使用',
        needs_config: '需配置',
        degraded: '需检查',
        empty: '目录为空',
        unknown: '未知',
        restricted: '受限',
        available: '可用',
        unavailable: '不可用',
        disabled: '禁用',
        neutral: '待确认'
    };
    return ovT(mapped[normalizeOverviewCommandStatus(status)] || '未知');
}

function formatOverviewCommandPriority(priority) {
    const mapped = {
        high: '高优先级',
        medium: '中优先级',
        low: '低优先级'
    };
    return mapped[normalizeOverviewCommandPriority(priority)] || '中优先级';
}

function renderVerificationStats(data) {
    const container = getOverviewContainer('verification');
    if (!container) return;

    const kpi = data.kpi || {};
    const channelStats = Array.isArray(data.channel_stats) ? data.channel_stats : [];
    const recent = Array.isArray(data.recent) ? data.recent : [];

    container.innerHTML = `
        <div class="kpi-row">
            ${renderKpiCard('近 7 天提取次数', formatNumber(kpi.total_count || 0), ovLabelValue('成功', formatNumber(kpi.success_count || 0)), 'kpi-primary')}
            ${renderKpiCard('总体成功率', formatPercent(kpi.success_rate || 0), ovLabelValue('失败', formatNumber(kpi.fail_count || 0)), 'kpi-success')}
            ${renderKpiCard('AI 兜底次数', formatNumber(kpi.ai_used_count || 0), ovLabelValue('AI 成功率', formatPercent(kpi.ai_success_rate || 0)), 'kpi-warn')}
            ${renderKpiCard('平均耗时', formatDurationMs(kpi.avg_duration_ms || 0), `P95 ${formatDurationMs(kpi.p95_duration_ms || 0)}`, 'kpi-accent')}
        </div>
        <div class="two-col">
            ${renderDataCard({
                title: '各通道成功率',
                code: '通道',
                badge: '效率',
                body: renderProgressBlock(channelStats.map((item) => ({
                    label: formatChannelLabel(item.label || item.channel || 'unknown'),
                    value: item.success_count || 0,
                    total: item.count || 0,
                    tone: 'jade',
                    suffix: `${formatPercent(item.success_rate || 0)} · ${formatNumber(item.count || 0)} ${ovT('次')}`
                })))
            })}
            ${renderDataCard({
                title: '各通道平均耗时',
                code: '耗时',
                badge: '性能',
                body: renderProgressBlock(channelStats.map((item) => ({
                    label: formatChannelLabel(item.label || item.channel || 'unknown'),
                    value: item.avg_duration_ms || 0,
                    total: Math.max(...channelStats.map((row) => Number(row.avg_duration_ms || 0)), 1),
                    tone: 'accent',
                    suffix: formatDurationMs(item.avg_duration_ms || 0)
                })))
            })}
        </div>
        ${renderDataCard({
            title: '最近提取记录',
            code: '明细',
            badge: '明细',
            className: 'ov-mt',
            body: renderTable(
                ['时间', '账号', '通道', '结果', '耗时', '状态'],
                recent.map((item) => [
                    formatTime(item.started_at),
                    esc(item.account_email || '--'),
                    esc(formatChannelLabel(item.channel_label || item.channel || '--')),
                    esc(item.code_found || '--'),
                    formatDurationMs(item.duration_ms || 0),
                    renderResultBadge(item.result_type, item.error_code)
                ]),
                6
            )
        })}
    `;
}

function renderExternalApiStats(data) {
    const container = getOverviewContainer('external-api');
    if (!container) return;

    const kpi = data.kpi || {};
    const health = data.health || {};
    const dailySeries = Array.isArray(data.daily_series) ? data.daily_series : [];
    const callerRank = Array.isArray(data.caller_rank) ? data.caller_rank : [];
    const byEndpoint = Array.isArray(data.by_endpoint) ? data.by_endpoint : [];
    const endpointHealth = Array.isArray(data.endpoint_health) ? data.endpoint_health : byEndpoint;
    const hasUsage = Number(kpi.week_calls || 0) > 0 || callerRank.length > 0 || endpointHealth.length > 0;

    container.innerHTML = `
        <div class="kpi-row">
            ${renderKpiCard('今日调用量', formatNumber(kpi.today_calls || 0), ovLabelValue('7 日', formatNumber(kpi.week_calls || 0)), 'kpi-primary')}
            ${renderKpiCard('调用波动', formatPercent(kpi.today_vs_yesterday_rate || 0), '对比昨日', 'kpi-accent')}
            ${renderKpiCard('7 日成功率', formatPercent(kpi.success_rate || 0), ovLabelValue('错误率', formatPercent(kpi.error_rate || 0)), 'kpi-success')}
            ${renderKpiCard('活跃调用方', formatNumber(kpi.active_callers || 0), '近 7 日有调用', 'kpi-warn')}
        </div>
        ${renderExternalApiHealthStrip(health, kpi)}
        ${hasUsage ? '' : `<div class="ov-empty ov-mb">${esc(ovT('近 7 日暂无外部 API 调用'))}</div>`}
        <div class="two-col">
            ${renderDataCard({
                title: '7 日调用趋势',
                code: '趋势',
                badge: '趋势',
                body: `<div id="ov-external-chart"></div>`
            })}
            ${renderDataCard({
                title: '接口占比',
                code: '接口',
                badge: '分布',
                body: renderProgressBlock(byEndpoint.map((item) => ({
                    label: item.endpoint || '--',
                    value: item.count || 0,
                    total: kpi.week_calls || 0,
                    tone: Number(item.error_count || 0) > 0 ? 'warn' : 'primary',
                    suffix: `${formatNumber(item.count || 0)} · ${formatPercent(item.rate || 0)} · ${ovT('错误')} ${formatNumber(item.error_count || 0)}`
                })))
            })}
        </div>
        ${renderDataCard({
            title: '接口健康',
            code: '接口',
            badge: '错误率',
            className: 'ov-mt',
            body: renderExternalApiEndpointHealth(endpointHealth)
        })}
            ${renderDataCard({
                title: '调用方健康',
                code: '调用方',
                badge: '近 7 日',
                className: 'ov-mt',
                body: renderTable(
                ['调用方', '今日', '7 日', '成功率', '错误率', '接口数', '状态', '最近调用'],
                callerRank.map((item) => [
                    esc(item.key_name || item.caller_id || '--'),
                    formatNumber(item.today_calls || 0),
                    formatNumber(item.week_calls || 0),
                    formatPercent(item.success_rate || 0),
                    formatPercent(item.error_rate || 0),
                    formatNumber(item.endpoint_count || 0),
                    renderExternalApiStatusBadge(item.last_status || '', item.error_count || 0),
                    esc(item.last_used_at || '--')
                ]),
                8
            )
        })}
    `;
    renderBarChart(document.getElementById('ov-external-chart'), dailySeries);
}

function renderExternalApiHealthStrip(health, kpi) {
    const healthData = health || {};
    const kpiData = kpi || {};
    const status = normalizeExternalApiHealthStatus(healthData.status);
    return `
        <div class="ov-api-health-strip" data-status="${esc(status)}" aria-live="polite">
            <div class="ov-api-health-item ov-api-health-state">
                <span>${esc(ovT('运行状态'))}</span>
                <strong>${esc(formatExternalApiHealthStatus(status))}</strong>
            </div>
            <div class="ov-api-health-item">
                <span>${esc(ovT('7 日错误'))}</span>
                <strong>${formatNumber(kpiData.error_count || 0)}</strong>
            </div>
            <div class="ov-api-health-item">
                <span>${esc(ovT('最高错误接口'))}</span>
                <strong>${esc(healthData.top_error_endpoint || '--')}</strong>
            </div>
            <div class="ov-api-health-item">
                <span>${esc(ovT('最高错误调用方'))}</span>
                <strong>${esc(healthData.top_error_caller || '--')}</strong>
            </div>
            <div class="ov-api-health-item">
                <span>${esc(ovT('风险调用方'))}</span>
                <strong>${formatNumber(healthData.risk_count || 0)}</strong>
            </div>
        </div>
    `;
}

function renderExternalApiEndpointHealth(items) {
    const safeItems = Array.isArray(items) ? items : [];
    if (!safeItems.length) {
        return `<div class="ov-empty">${esc(ovT('暂无数据'))}</div>`;
    }
    return `
        <div class="ov-endpoint-health-list">
            ${safeItems.map((item) => {
                const count = Number(item.count || 0);
                const errorCount = Number(item.error_count || 0);
                const tone = errorCount > 0 ? 'warn' : 'success';
                return `
                    <div class="ov-endpoint-health-row" data-tone="${tone}">
                        <div class="ov-endpoint-health-main">
                            <strong>${esc(item.endpoint || '--')}</strong>
                            <span>${esc(ovT('最近调用'))} ${esc(item.last_used_at || '--')}</span>
                        </div>
                        <div class="ov-endpoint-health-metrics">
                            <span>${esc(ovT('调用'))} <strong>${formatNumber(count)}</strong></span>
                            <span>${esc(ovT('成功率'))} <strong>${formatPercent(item.success_rate || 0)}</strong></span>
                            <span>${esc(ovT('错误率'))} <strong>${formatPercent(item.error_rate || 0)}</strong></span>
                            ${renderExternalApiStatusBadge(item.last_status || '', errorCount)}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function formatExternalApiHealthStatus(status) {
    const mapped = {
        healthy: '健康',
        attention: '需关注',
        idle: '暂无调用'
    };
    return ovT(mapped[normalizeExternalApiHealthStatus(status)] || '暂无调用');
}

function renderExternalApiStatusBadge(status, errorCount) {
    const normalized = String(status || '').trim().toLowerCase();
    if (normalized === 'ok' && Number(errorCount || 0) <= 0) {
        return `<span class="badge-pill badge-success">${esc(ovT('调用正常'))}</span>`;
    }
    if (normalized || Number(errorCount || 0) > 0) {
        return `<span class="badge-pill badge-warn">${esc(formatExternalApiLastStatus(normalized || 'error'))}</span>`;
    }
    return `<span class="badge-pill">${esc(ovT('暂无状态'))}</span>`;
}

function formatExternalApiLastStatus(status) {
    const normalized = String(status || '').trim().toLowerCase();
    const mapped = {
        ok: '正常',
        error: '调用异常',
        failed: '失败',
        fail: '失败',
        timeout: '超时',
        denied: '拒绝'
    };
    return ovT(mapped[normalized] || status || '异常');
}

function renderPoolStats(data) {
    const container = getOverviewContainer('pool');
    if (!container) return;

    const kpi = data.kpi || {};
    const dist = data.operation_distribution || {};
    const recent = Array.isArray(data.recent_operations) ? data.recent_operations : [];
    const topProjects = Array.isArray(data.project_top5) ? data.project_top5 : [];

    container.innerHTML = `
        <div class="kpi-row">
            ${renderKpiCard('可用账号', formatNumber(kpi.available || 0), ovLabelValue('占用', formatNumber(kpi.in_use || 0)), 'kpi-primary')}
            ${renderKpiCard('冷却中', formatNumber(kpi.cooldown || 0), ovLabelValue('已使用', formatNumber(kpi.used || 0)), 'kpi-warn')}
            ${renderKpiCard('近 7 天领取', formatNumber(kpi.claim_count_7d || 0), ovLabelValue('完成率', formatPercent(kpi.complete_success_rate || 0)), 'kpi-success')}
            ${renderKpiCard('最长占用', formatDurationSeconds(kpi.max_claimed_duration_s || 0), '当前占用中', 'kpi-accent')}
        </div>
        <div class="two-col">
            ${renderDataCard({
                title: '操作分布',
                code: '操作',
                badge: '池子',
                body: renderProgressBlock([
                    { label: '领取', value: dist.claim || 0, total: totalValues(dist), tone: 'primary' },
                    { label: '完成', value: dist.complete || 0, total: totalValues(dist), tone: 'jade' },
                    { label: '释放', value: dist.release || 0, total: totalValues(dist), tone: 'accent' },
                    { label: '过期回收', value: dist.expire || 0, total: totalValues(dist), tone: 'danger' }
                ])
            })}
            ${renderDataCard({
                title: '项目 Top 5',
                code: '项目',
                badge: '项目',
                body: renderTable(
                    ['项目', '账号数', '成功数', '复用率'],
                    topProjects.map((item) => [
                        esc(item.project_key || '--'),
                        formatNumber(item.account_count || 0),
                        formatNumber(item.success_count || 0),
                        formatPercent(item.reuse_rate || 0)
                    ]),
                    4
                )
            })}
        </div>
        ${renderDataCard({
            title: '最近邮箱池操作',
            code: '流转',
            badge: '流转',
            className: 'ov-mt',
            body: renderTable(
                ['时间', '账号', '动作', '调用方', '项目', '结果'],
                recent.map((item) => [
                    esc(item.time || '--'),
                    esc(item.account_email || '--'),
                    esc(formatPoolActionLabel(item.action || '--')),
                    esc(item.caller_id || '--'),
                    esc(item.project_key || '--'),
                    esc(formatTimelineStatus(item.result || '--'))
                ]),
                6
            )
        })}
    `;
}

function renderActivityStats(data) {
    const container = getOverviewContainer('activity');
    if (!container) return;

    const kpi = data.kpi || {};
    const notificationStats = data.notification_stats || {};
    const timeline = Array.isArray(data.timeline) ? data.timeline : [];

    container.innerHTML = `
        <div class="kpi-row">
            ${renderKpiCard('24h 审计操作', formatNumber(kpi.audit_ops_24h || 0), '系统活动', 'kpi-primary')}
            ${renderKpiCard('24h 通知投递', formatNumber(kpi.notification_total_24h || 0), '全部通道', 'kpi-success')}
            ${renderKpiCard('24h 提取事件', formatNumber(kpi.verification_events_24h || 0), '验证码链路', 'kpi-accent')}
        </div>
        <div class="two-col">
            ${renderDataCard({
                title: '通知健康',
                code: '通知',
                badge: '通道',
                body: renderProgressBlock(Object.keys(notificationStats).map((channel) => ({
                    label: formatChannelLabel(channel),
                    value: notificationStats[channel].success_count || 0,
                    total: notificationStats[channel].count || 0,
                    tone: 'jade',
                    suffix: `${formatNumber(notificationStats[channel].count || 0)} · ${formatPercent(notificationStats[channel].success_rate || 0)}`
                })))
            })}
            ${renderDataCard({
                title: '最近系统活动',
                code: '活动',
                badge: '时间线',
                body: `<div id="ov-activity-timeline"></div>`
            })}
        </div>
    `;
    renderTimeline(document.getElementById('ov-activity-timeline'), timeline);
}

function renderKpiCard(label, value, note, tone) {
    return `
        <div class="kpi-card ${tone || ''}">
            <div class="kpi-head">
                <span class="kpi-icon">${esc(pickToneGlyph(tone))}</span>
                <div class="kpi-label">${esc(ovT(label))}</div>
            </div>
            <div class="kpi-value">${esc(value)}</div>
            <div class="kpi-note">${esc(ovT(note))}</div>
        </div>
    `;
}

function renderDataCard(options) {
    const config = options || {};
    const code = config.code || 'SYS';
    return `
        <div class="data-card ${esc(config.className || '')}">
            <div class="data-card-header">
                <div class="ov-card-header-main">
                    <span class="ov-card-code">${esc(ovT(code))}</span>
                    <span class="ov-card-title">${esc(ovT(config.title || ''))}</span>
                </div>
                ${config.badge ? `<span class="ov-card-badge">${esc(ovT(config.badge))}</span>` : ''}
            </div>
            <div class="data-card-body">${config.body || ''}</div>
        </div>
    `;
}

function renderProgressBlock(items) {
    const safeItems = Array.isArray(items) ? items.filter(Boolean) : [];
    if (!safeItems.length) {
        return `<div class="ov-empty">${esc(ovT('暂无数据'))}</div>`;
    }
    return safeItems.map((item) => {
        const total = Number(item.total || 0);
        const value = Number(item.value || 0);
        const percent = total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0;
        const suffix = item.suffix || `${formatNumber(value)} / ${formatNumber(total)}`;
        return `
            <div class="prog-row">
                <div class="prog-label">
                    <span class="prog-name">${esc(ovT(item.label || '--'))}</span>
                    <span class="prog-val">${esc(suffix)}</span>
                </div>
                <div class="prog-track"><div class="prog-fill ${esc(item.tone || 'primary')}" style="width:${percent}%"></div></div>
            </div>
        `;
    }).join('');
}

function renderTable(headers, rows, colCount) {
    if (!rows || !rows.length) {
        return `<div class="ov-empty">${esc(ovT('暂无数据'))}</div>`;
    }
    return `
        <div class="data-table-shell">
            <table class="data-table">
                <thead><tr>${headers.map((header) => `<th>${esc(ovT(header))}</th>`).join('')}</tr></thead>
                <tbody>
                    ${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderBarChart(container, data) {
    if (!container) return;
    const series = Array.isArray(data) ? data : [];
    if (!series.length) {
        container.innerHTML = `<div class="ov-empty">${esc(ovT('暂无数据'))}</div>`;
        return;
    }
    const maxValue = Math.max(...series.map((item) => Number(item.count || 0)), 1);
    container.innerHTML = `
        <div class="bar-chart">
            ${series.map((item) => {
                const count = Number(item.count || 0);
                const height = Math.max((count / maxValue) * 100, count > 0 ? 6 : 2);
                return `
                    <div class="bar-item">
                        <div class="bar-popover">${esc(item.date || '--')} · ${formatNumber(count)} ${esc(ovT('次'))}</div>
                        <div class="bar-col" style="height:${height}%"></div>
                        <div class="bar-value">${formatNumber(count)}</div>
                        <div class="bar-label">${esc((item.date || '').slice(5) || '--')}</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function renderTimeline(container, events) {
    if (!container) return;
    const items = Array.isArray(events) ? events : [];
    if (!items.length) {
        container.innerHTML = `<div class="ov-empty">${esc(ovT('暂无数据'))}</div>`;
        return;
    }
    container.innerHTML = `
        <div class="timeline">
            ${items.map((item) => `
                <div class="tl-item">
                    <div class="tl-icon">${pickTimelineIcon(item.action)}</div>
                    <div class="tl-content">
                        <div class="tl-title">${esc(formatTimelineAction(item.action || '--'))}</div>
                        <div class="tl-meta">${esc(item.time || '--')} · ${esc(formatTimelineStatus(item.status || '--'))}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderResultBadge(resultType, errorCode) {
    if (resultType === 'code' || resultType === 'link') {
        return `<span class="badge-pill badge-success">${esc(ovT('成功'))}</span>`;
    }
    return `<span class="badge-pill badge-danger">${esc(errorCode || ovT('失败'))}</span>`;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString(ovLocale());
}

function formatPercent(value) {
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatDurationMs(value) {
    const ms = Number(value || 0);
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms}ms`;
}

function formatDurationSeconds(value) {
    const seconds = Number(value || 0);
    if (seconds >= 3600) return `${(seconds / 3600).toFixed(1)}h`;
    if (seconds >= 60) return `${(seconds / 60).toFixed(1)}m`;
    return `${seconds}s`;
}

function formatTime(value) {
    if (value === null || value === undefined || value === '') return '--';
    if (typeof value === 'number') {
        try {
            return new Date(value * 1000).toLocaleString(ovLocale(), { hour12: false });
        } catch (error) {
            return String(value);
        }
    }
    return String(value);
}

function formatChannelLabel(value) {
    const raw = String(value || '').trim();
    const normalized = raw.toLowerCase();
    const mapped = {
        unknown: '未知通道',
        'graph inbox': 'Graph 收件箱',
        'graph junk': 'Graph 垃圾箱',
        'imap new': 'IMAP 新链路',
        'imap old': 'IMAP 旧链路',
        'temp mail': '临时邮箱通道',
        'ai fallback': 'AI 兜底通道',
        graph: 'Graph 通道',
        imap: 'IMAP 通道',
        telegram: 'Telegram',
        email: 'Email',
        webhook: 'Webhook',
        graph_inbox: 'Graph 收件箱',
        graph_junk: 'Graph 垃圾箱',
        imap_new: 'IMAP 新链路',
        imap_old: 'IMAP 旧链路',
        temp_mail: '临时邮箱通道',
        ai_fallback: 'AI 兜底通道',
        graph_delta: 'Graph 通道',
        imap_ssl: 'IMAP 通道'
    };
    return ovT(mapped[normalized] || raw || '--');
}

function formatTimelineAction(value) {
    const raw = String(value || '').trim();
    const normalized = raw.toLowerCase();
    if (normalized === 'verification_extract') {
        return ovT('验证码提取事件');
    }
    if (normalized.startsWith('notification:')) {
        const channel = raw.includes(':') ? raw.slice(raw.indexOf(':') + 1) : '';
        return ovT(`通知：${formatChannelLabel(channel)}`);
    }
    return ovT(raw || '--');
}

function formatTimelineStatus(value) {
    const raw = String(value || '').trim();
    const normalized = raw.toLowerCase();
    const mapped = {
        success: '成功',
        successful: '成功',
        sent: '已发送',
        ok: '正常',
        failed: '失败',
        error: '失败',
        fail: '失败'
    };
    return ovT(mapped[normalized] || raw || '--');
}

function formatPoolActionLabel(value) {
    const raw = String(value || '').trim();
    const normalized = raw.toLowerCase();
    const mapped = {
        claim: '领取',
        complete: '完成',
        release: '释放',
        expire: '过期回收'
    };
    return ovT(mapped[normalized] || raw || '--');
}

