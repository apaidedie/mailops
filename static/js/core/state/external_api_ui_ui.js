// split from external_api_ui.js → ui.js
        function renderExternalApiStarterModeButton(mode) {
            const normalizedMode = normalizeExternalApiStarterMode(externalApiStarterMode);
            const active = mode.key === normalizedMode;
            return `<button type="button" class="external-api-starter-mode${active ? ' active' : ''}" data-external-api-starter-mode="${escapeHtml(mode.key)}" aria-pressed="${active ? 'true' : 'false'}">${escapeHtml(mode.label)}</button>`;
        }

        function renderExternalApiMailboxSessionStep(step, index) {
            const item = step && typeof step === 'object' ? step : {};
            const method = String(item.method || 'POST').trim().toUpperCase() || 'POST';
            const endpoint = String(item.endpoint || '').trim();
            const label = String(item.label || item.key || `Step ${index + 1}`).trim();
            const description = String(item.description || '').trim();
            const requestHints = getExternalApiWorkflowRequestHints(item).slice(0, 3);
            return [
                '<div class="external-api-session-step">',
                    '<div class="external-api-session-step-main">',
                        `<span class="external-api-workflow-index">${index + 1}</span>`,
                        '<div class="external-api-session-step-copy">',
                            `<div class="external-api-session-step-title">${escapeHtml(translateAppTextLocal(label))}</div>`,
                            description ? `<div class="external-api-session-step-desc">${escapeHtml(translateAppTextLocal(description))}</div>` : '',
                            '<div class="external-api-workflow-endpoint-line">',
                                `<span class="external-api-command-method">${escapeHtml(method)}</span>`,
                                `<code>${escapeHtml(endpoint)}</code>`,
                            '</div>',
                            renderExternalApiWorkflowHintList(requestHints),
                        '</div>',
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalApiMailboxSessionExamples(examples) {
            const entries = [
                ['Pool claim read', examples.mailbox_session_read, { session_type: 'pool_claim', claim_token: '<claim-token>', read_action: 'verification_code' }],
                ['Task temp-mail read', examples.mailbox_session_read, { session_type: 'task_temp_mailbox', task_token: '<task-token>', read_action: 'latest_message' }],
            ];
            return entries.map(([label, request, overrides]) => {
                const body = {
                    ...((request && request.body && typeof request.body === 'object') ? request.body : {}),
                    ...overrides,
                };
                return [
                    '<div class="external-api-session-example">',
                        `<span>${escapeHtml(translateAppTextLocal(label))}</span>`,
                        `<pre class="external-api-command-code external-api-session-code"><code>${escapeHtml(formatExternalQuickstartJson(body))}</code></pre>`,
                    '</div>'
                ].join('');
            }).join('');
        }

        function renderExternalApiMailboxSessionLifecycle() {
            const workflow = getExternalApiMailboxSessionWorkflow();
            const examples = getExternalApiMailboxSessionRequestExamples();
            const readModes = getExternalApiMailboxSessionReadModes();
            const steps = workflow && Array.isArray(workflow.steps) ? workflow.steps : [];
            return [
                '<div class="external-api-session-lifecycle">',
                    '<div class="external-api-session-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('邮箱会话生命周期'))}</div>`,
                            `<div class="external-api-session-subtitle">${escapeHtml(translateAppTextLocal('一条入口完成创建、读取验证码和关闭会话'))}</div>`,
                        '</div>',
                        `<button type="button" class="external-api-command-copy external-api-session-copy" data-external-api-session-copy>${escapeHtml(translateAppTextLocal('复制会话流程'))}</button>`,
                    '</div>',
                    '<div class="external-api-session-summary">',
                        renderExternalApiCommandMetric('Start', getExternalQuickstartRequestLine(examples.mailbox_session_start), translateAppTextLocal('创建 provider-neutral mailbox session')),
                        renderExternalApiCommandMetric('Read', getExternalQuickstartRequestLine(examples.mailbox_session_read), translateAppTextLocal('使用 session_type 读取邮件或验证码')),
                        renderExternalApiCommandMetric('Close', getExternalQuickstartRequestLine(examples.mailbox_session_close), translateAppTextLocal('完成或释放生命周期')),
                    '</div>',
                    '<div class="external-api-session-body">',
                        `<div class="external-api-session-steps">${steps.map((step, index) => renderExternalApiMailboxSessionStep(step, index)).join('')}</div>`,
                        '<div class="external-api-session-examples">',
                            `<div class="external-api-session-example-title">${escapeHtml(translateAppTextLocal('读取请求模板'))}</div>`,
                            readModes.length ? `<div class="external-api-workflow-hints">${readModes.map(item => `<span>${escapeHtml(item)}</span>`).join('')}</div>` : '',
                            renderExternalApiMailboxSessionExamples(examples),
                        '</div>',
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalApiActionPlanItem(item) {
            const safeItem = item && typeof item === 'object' ? item : {};
            const priority = String(safeItem.priority || 'medium').trim().toLowerCase();
            const status = String(safeItem.status || 'optional').trim().toLowerCase();
            const meta = [priority, status, safeItem.blocking ? 'blocking' : 'non-blocking'].filter(Boolean).join(' · ');
            const target = String(safeItem.command || safeItem.endpoint || safeItem.docs || '').trim();
            return [
                `<div class="external-api-action-item" data-priority="${escapeHtml(priority)}" data-status="${escapeHtml(status)}">`,
                    '<div class="external-api-action-head">',
                        `<strong>${escapeHtml(translateAppTextLocal(safeItem.title || safeItem.key || 'Action'))}</strong>`,
                        `<span>${escapeHtml(translateAppTextLocal(meta))}</span>`,
                    '</div>',
                    safeItem.detail ? `<div class="external-api-action-detail">${escapeHtml(translateAppTextLocal(safeItem.detail))}</div>` : '',
                    target ? `<pre class="external-api-action-code"><code>${escapeHtml(target)}</code></pre>` : '',
                    safeItem.docs ? `<div class="external-api-action-meta"><span>${escapeHtml(translateAppTextLocal('Docs'))}</span><code>${escapeHtml(safeItem.docs)}</code></div>` : '',
                '</div>'
            ].join('');
        }

        function renderExternalApiActionPlan(plan) {
            const safePlan = plan && typeof plan === 'object' ? plan : {};
            const items = Array.isArray(safePlan.items) ? safePlan.items.filter(item => item && typeof item === 'object') : [];
            if (!items.length) return '';
            const summary = safePlan.summary && typeof safePlan.summary === 'object' ? safePlan.summary : {};
            return [
                '<div class="external-api-action-plan">',
                    '<div class="external-api-action-head external-api-action-plan-head">',
                        `<strong>${escapeHtml(translateAppTextLocal('Action Plan'))}</strong>`,
                        `<span>${escapeHtml(translateAppTextLocal('阻塞'))} ${escapeHtml(String(summary.blocking || 0))} · ${escapeHtml(translateAppTextLocal('总数'))} ${escapeHtml(String(summary.total || items.length))}</span>`,
                    '</div>',
                    '<div class="external-api-action-list">',
                        items.map(renderExternalApiActionPlanItem).join(''),
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalApiConsumerSummaryMetric(label, value, detail, tone = 'neutral') {
            return [
                `<div class="external-api-consumer-summary-card" data-tone="${escapeHtml(tone)}">`,
                    `<span>${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<strong>${escapeHtml(String(value))}</strong>`,
                    detail ? `<small>${escapeHtml(translateAppTextLocal(detail))}</small>` : '',
                '</div>'
            ].join('');
        }

        function renderExternalApiConsumerUsageCard(consumer) {
            const tone = getExternalApiConsumerUsageTone(consumer);
            const badgeClass = getExternalApiConsumerUsageBadgeClass(tone);
            const scopeText = getExternalApiConsumerScopeText(consumer);
            const poolText = consumer.poolAccess ? 'Pool 可用' : 'Pool 不可用';
            return [
                `<div class="external-api-consumer-card" data-tone="${escapeHtml(tone)}" role="listitem">`,
                    '<div class="external-api-consumer-card-head">',
                        '<div class="external-api-consumer-identity">',
                            `<strong>${escapeHtml(consumer.name)}</strong>`,
                            `<code>${escapeHtml(consumer.consumerKey)}</code>`,
                        '</div>',
                        `<span class="badge ${escapeHtml(badgeClass)}">${escapeHtml(translateAppTextLocal(getExternalApiConsumerUsageStatusLabel(tone)))}</span>`,
                    '</div>',
                    '<div class="external-api-consumer-chips">',
                        `<span>${escapeHtml(translateAppTextLocal('范围'))}: ${escapeHtml(scopeText)}</span>`,
                        `<span>${escapeHtml(translateAppTextLocal(poolText))}</span>`,
                    '</div>',
                    '<div class="external-api-consumer-counts">',
                        renderExternalApiConsumerSummaryMetric('今日调用', consumer.todayTotal, '总计', 'neutral'),
                        renderExternalApiConsumerSummaryMetric('成功', consumer.todaySuccess, '成功数', 'ready'),
                        renderExternalApiConsumerSummaryMetric('错误', consumer.todayError, '错误数', consumer.todayError > 0 ? 'danger' : 'neutral'),
                    '</div>',
                    '<div class="external-api-consumer-last-used">',
                        `<span>${escapeHtml(translateAppTextLocal('最近使用'))}</span>`,
                        `<strong>${escapeHtml(formatExternalApiConsumerLastUsed(consumer.lastUsedAt))}</strong>`,
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalApiConsumerUsageConsole(settings = {}) {
            const summary = getExternalApiConsumerUsageSummary(settings);
            const healthTone = summary.errorsToday > 0 ? 'danger' : (summary.usedToday > 0 ? 'ready' : 'warning');
            const badgeText = summary.total > 0
                ? `${summary.usedToday}/${summary.total} ${translateAppTextLocal('今日活跃')}`
                : translateAppTextLocal('未配置');
            const emptyState = !summary.consumers.length
                ? `<div class="external-api-consumer-empty">${escapeHtml(translateAppTextLocal('暂无多 Key 消费方；配置多 Key 后这里会显示每个调用方的今日调用、错误和授权范围。'))}</div>`
                : '';
            return [
                `<div class="external-api-consumer-console" aria-label="${escapeHtml(translateAppTextLocal('外部 API 消费方'))}">`,
                    '<div class="external-api-consumer-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('外部 API 消费方'))}</div>`,
                            `<div class="external-api-consumer-subtitle">${escapeHtml(translateAppTextLocal('按调用方查看今日用量、错误和访问范围'))}</div>`,
                        '</div>',
                        `<span class="badge ${escapeHtml(getExternalApiConsumerUsageBadgeClass(healthTone))}">${escapeHtml(badgeText)}</span>`,
                    '</div>',
                    '<div class="external-api-consumer-summary">',
                        renderExternalApiConsumerSummaryMetric('调用方', summary.total, '已配置', 'neutral'),
                        renderExternalApiConsumerSummaryMetric('启用', summary.enabled, '已启用', summary.enabled > 0 ? 'ready' : 'warning'),
                        renderExternalApiConsumerSummaryMetric('今日调用', summary.totalToday, '请求数', summary.totalToday > 0 ? 'ready' : 'warning'),
                        renderExternalApiConsumerSummaryMetric('今日错误', summary.errorsToday, '错误数', summary.errorsToday > 0 ? 'danger' : 'neutral'),
                    '</div>',
                    emptyState || `<div class="external-api-consumer-list" role="list">${summary.consumers.map(renderExternalApiConsumerUsageCard).join('')}</div>`,
                '</div>'
            ].join('');
        }

