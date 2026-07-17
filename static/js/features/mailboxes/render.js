// split from mailboxes.js → render.js
        function renderUnifiedWorkspaceViewSwitch() {
            const switcher = document.getElementById('unifiedWorkspaceViewSwitch');
            const inboxWorkflow = document.getElementById('unifiedInboxWorkflow');
            const diagnosticsWorkspace = document.getElementById('unifiedDiagnosticsWorkspace');
            const activeView = normalizeUnifiedWorkspaceView(unifiedMailboxState.workspaceView);
            unifiedMailboxState.workspaceView = activeView;
            if (switcher) {
                switcher.querySelectorAll('[data-unified-workspace-view]').forEach(button => {
                    const buttonView = normalizeUnifiedWorkspaceView(button.dataset.unifiedWorkspaceView || 'inbox');
                    const isActive = buttonView === activeView;
                    button.classList.toggle('active', isActive);
                    button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
                });
                const inboxLabel = switcher.querySelector('[data-unified-view-label="inbox"]');
                const inboxDetail = switcher.querySelector('[data-unified-view-detail="inbox"]');
                const diagnosticsLabel = switcher.querySelector('[data-unified-view-label="diagnostics"]');
                const diagnosticsDetail = switcher.querySelector('[data-unified-view-detail="diagnostics"]');
                if (inboxLabel) inboxLabel.textContent = translateUnifiedText('邮箱');
                if (inboxDetail) inboxDetail.textContent = translateUnifiedText('目录与预览');
                if (diagnosticsLabel) diagnosticsLabel.textContent = translateUnifiedText('高级');
                if (diagnosticsDetail) diagnosticsDetail.textContent = translateUnifiedText('配置与扩展');
            }
            // Mutual exclusive surfaces: default inbox; diagnostics only when selected.
            if (inboxWorkflow) {
                inboxWorkflow.dataset.active = activeView === 'diagnostics' ? 'false' : 'true';
            }
            if (diagnosticsWorkspace) {
                diagnosticsWorkspace.dataset.active = activeView === 'diagnostics' ? 'true' : 'false';
            }
        }

        function renderUnifiedProviderOptions(facets = [], selectedProvider = 'all') {
            const select = document.getElementById('unifiedMailboxProviderFilter');
            if (!select) return;
            const rawSelected = String(selectedProvider || 'all').trim().toLowerCase() || 'all';
            const selected = rawSelected === 'all'
                ? 'all'
                : (canonicalizeUnifiedTempProviderKey(rawSelected) || rawSelected);
            const providers = normalizeUnifiedProviderFacets(facets);
            const hasSelected = selected === 'all' || providers.some(item => item.provider === selected);
            const options = [
                `<option value="all">${escapeHtml(translateUnifiedText('全部 Provider'))}</option>`
            ];
            if (!hasSelected) {
                options.push(`<option value="${escapeHtml(selected)}">${escapeHtml(translateUnifiedText('当前筛选'))}: ${escapeHtml(selected)}</option>`);
            }
            providers.forEach(item => {
                const provider = item.provider;
                if (!provider) return;
                const label = String(item.label || provider).trim() || provider;
                const count = normalizeUnifiedFacetCount(item.count);
                options.push(`<option value="${escapeHtml(provider)}">${escapeHtml(label)} (${count})</option>`);
            });
            select.innerHTML = options.join('');
            select.value = selected;
        }

        function renderUnifiedReadCapabilityOptions(contract = {}, selectedReadCapability = 'all', facets = []) {
            renderUnifiedDefinitionOptions({
                selectId: 'unifiedMailboxReadCapabilityFilter',
                selectedValue: selectedReadCapability,
                definitions: contract.read_capability_definitions,
                valueKey: 'read_capability',
                allLabel: '全部读取方式',
                countsByValue: buildUnifiedFacetCountMap(facets, 'read_capability')
            });
        }

        function renderUnifiedActionOptions(contract = {}, selectedAction = 'all', facets = []) {
            renderUnifiedDefinitionOptions({
                selectId: 'unifiedMailboxActionFilter',
                selectedValue: selectedAction,
                definitions: contract.action_definitions,
                valueKey: 'action',
                allLabel: '全部能力',
                countsByValue: buildUnifiedFacetCountMap(facets, 'action')
            });
        }

        function renderUnifiedSortOptions(contract = {}, selectedSort = 'updated_desc') {
            renderUnifiedDefinitionOptions({
                selectId: 'unifiedMailboxSortFilter',
                selectedValue: selectedSort,
                definitions: contract.sort_definitions,
                valueKey: 'sort',
                includeAll: false,
                fallbackDefinitions: UNIFIED_SORT_PLACEHOLDER_DEFINITIONS
            });
        }

        function renderUnifiedResultBar({ state = 'ready', pagination = {}, filters = unifiedMailboxState.filters } = {}) {
            const container = document.getElementById('unifiedMailboxResultBar');
            if (!container) return;
            const safeFilters = filters && typeof filters === 'object' ? filters : {};
            const page = Number(pagination.page || unifiedMailboxState.pagination.page || 1);
            const totalPages = Number(pagination.total_pages || unifiedMailboxState.pagination.total_pages || 0);
            const totalCount = Number(pagination.total_count || unifiedMailboxState.pagination.total_count || 0);
            const searchText = String(safeFilters.search || '').trim();
            const hasSearch = Boolean(searchText);
            const primaryText = state === 'loading'
                ? translateUnifiedText('正在刷新邮箱目录…')
                : state === 'error'
                    ? translateUnifiedText('邮箱目录暂时不可用')
                    : `${formatUnifiedMailboxCount(totalCount, '个邮箱', 'mailbox')} · ${totalPages > 0 ? `${page} / ${totalPages} ${translateUnifiedText('页')}` : translateUnifiedText('无分页')}`;
            const readCapabilityFilter = safeFilters.read_capability || safeFilters.readCapability || 'all';
            const chips = [
                { label: getUnifiedSelectLabel('unifiedMailboxKindFilter', '全部来源'), muted: String(safeFilters.kind || 'all') === 'all' },
                { label: getUnifiedSelectLabel('unifiedMailboxStatusFilter', '全部状态'), muted: String(safeFilters.status || 'all') === 'all' },
                { label: getUnifiedSelectLabel('unifiedMailboxReadCapabilityFilter', '全部读取方式'), muted: String(readCapabilityFilter) === 'all' },
                { label: getUnifiedSelectLabel('unifiedMailboxActionFilter', '全部能力'), muted: String(safeFilters.action || 'all') === 'all' },
                { label: getUnifiedSelectLabel('unifiedMailboxProviderFilter', '全部 Provider'), muted: String(safeFilters.provider || 'all') === 'all' },
                { label: getUnifiedSelectLabel('unifiedMailboxSortFilter', '最近更新'), muted: false },
            ];
            if (hasSearch) {
                chips.unshift({ label: searchText, prefix: '搜索', muted: false });
            }
            container.dataset.state = state;
            container.innerHTML = `
                <div class="unified-result-primary">${escapeHtml(primaryText)}</div>
                <div class="unified-result-chips" aria-label="${escapeHtml(translateUnifiedText('当前筛选条件'))}">
                    ${chips.map(item => {
                        const label = item.prefix ? `${translateUnifiedText(item.prefix)}: ${item.label}` : translateUnifiedText(item.label);
                        return `<span class="unified-result-chip ${item.muted ? 'muted' : ''}">${escapeHtml(label)}</span>`;
                    }).join('')}
                </div>
            `;
        }

        function renderUnifiedSetupGuideAction(action = {}) {
            const actionName = String(action.action || '').trim();
            if (!actionName) return '';
            const viewAttr = action.view ? ` data-unified-setup-view="${escapeHtml(action.view)}"` : '';
            return `<button type="button" class="unified-setup-action" data-unified-setup-action="${escapeHtml(actionName)}"${viewAttr}>${escapeHtml(getUnifiedSetupGuideActionLabel(action))}</button>`;
        }

        function renderUnifiedSetupGuideStep(step = {}, index = 0) {
            const status = String(step.status || 'unknown').trim().toLowerCase().replace(/_/g, '-');
            return `
                <article class="unified-setup-step" data-setup-step="${escapeHtml(step.key || '')}" data-setup-step-state="${escapeHtml(status)}">
                    <div class="unified-setup-step-index">${escapeHtml(String(index + 1).padStart(2, '0'))}</div>
                    <div class="unified-setup-step-body">
                        <div class="unified-setup-step-topline">
                            <span>${escapeHtml(getUnifiedSetupGuideStatusLabel(status))}</span>
                            <strong>${escapeHtml(translateUnifiedText(step.metric || ''))}</strong>
                        </div>
                        <h4>${escapeHtml(translateUnifiedText(step.title || ''))}</h4>
                        <p>${escapeHtml(translateUnifiedText(step.detail || ''))}</p>
                        ${step.action ? `<div class="unified-setup-step-actions">${renderUnifiedSetupGuideAction(step.action)}</div>` : ''}
                    </div>
                </article>
            `;
        }

        function renderUnifiedSetupGuide(data = {}, state = 'ready') {
            const container = document.getElementById('unifiedMailboxSetupGuide');
            if (!container) return;
            const model = getUnifiedSetupGuideModel(data, state);
            container.dataset.state = model.state || state;
            const isLoading = model.state === 'loading';
            const stepsHtml = isLoading
                ? '<span class="unified-setup-step-skeleton"></span><span class="unified-setup-step-skeleton"></span><span class="unified-setup-step-skeleton"></span><span class="unified-setup-step-skeleton"></span>'
                : model.steps.map((step, index) => renderUnifiedSetupGuideStep(step, index)).join('');
            container.innerHTML = `
                <div class="unified-setup-guide-head">
                    <div>
                        <span class="unified-setup-guide-kicker">${escapeHtml(translateUnifiedText('Setup Path'))}</span>
                        <h3 id="unifiedSetupGuideTitle">${escapeHtml(translateUnifiedText('统一邮箱启动路径'))}</h3>
                        <p>${escapeHtml(translateUnifiedText(model.detail || '按顺序完成账号库存、临时邮箱、Provider 路由和外部 API 接入'))}</p>
                    </div>
                    <span class="unified-setup-guide-status">${escapeHtml(getUnifiedSetupGuideStatusLabel(model.status || model.state))}</span>
                </div>
                <div class="unified-setup-guide-steps" aria-label="${escapeHtml(translateUnifiedText('统一邮箱启动路径'))}">
                    ${stepsHtml}
                </div>
            `;
        }

        function renderUnifiedLensAction(action = {}) {
            const actionName = String(action.action || '').trim();
            if (!actionName) return '';
            const viewAttr = action.view ? ` data-unified-lens-view="${escapeHtml(action.view)}"` : '';
            return `<button type="button" class="unified-lens-action" data-unified-lens-action="${escapeHtml(actionName)}"${viewAttr}>${escapeHtml(translateUnifiedText(action.label || '执行'))}</button>`;
        }

        function renderUnifiedOperationalLens(data = {}, state = 'ready') {
            const container = document.getElementById('unifiedMailboxOperationalLens');
            if (!container) return;
            const safeData = data && typeof data === 'object' ? data : {};
            const summary = safeData.summary && typeof safeData.summary === 'object' ? safeData.summary : {};
            const filters = safeData.filters || unifiedMailboxState.filters || {};
            const contract = safeData.contract || unifiedMailboxState.contract || {};
            const pagination = safeData.pagination && typeof safeData.pagination === 'object' ? safeData.pagination : {};
            const providerContext = safeData.provider_context && typeof safeData.provider_context === 'object' ? safeData.provider_context : {};
            const providerCounts = getUnifiedOperationalProviderCounts(providerContext);
            const totalCount = Number(pagination.total_count || summary.total || 0);
            const activeFilterCount = getUnifiedOperationalActiveFilterCount(filters);
            const lensState = getUnifiedOperationalLensState({ state, totalCount, providerCounts, summary });
            const currentView = getUnifiedOperationalViewLabel(filters, contract);
            const recommendation = getUnifiedOperationalRecommendation({ lensState, activeFilterCount, providerCounts, summary });
            const filterDetail = activeFilterCount > 0
                ? `${activeFilterCount} ${translateUnifiedText('筛选条件')}`
                : translateUnifiedText('未应用筛选');
            const providerDetail = `${Number(providerCounts.active || 0)} ${translateUnifiedText('启用')} · ${Number(providerCounts.ready || 0)} ${translateUnifiedText('就绪')} · ${Number(providerCounts.needsConfig || 0)} ${translateUnifiedText('缺配置')}`;
            const stateLabels = {
                loading: '正在分析当前视图…',
                error: '邮箱目录暂时不可用',
                empty: '空视图',
                warning: '风险提示',
                ready: '当前视图可用'
            };
            container.dataset.state = lensState;
            container.innerHTML = `
                <div class="unified-lens-head">
                    <div class="unified-lens-title-wrap">
                        <span class="unified-lens-kicker">${escapeHtml(translateUnifiedText('运营态势'))}</span>
                        <strong>${escapeHtml(translateUnifiedText('当前视图状态'))}</strong>
                    </div>
                    <span class="unified-lens-status">${escapeHtml(translateUnifiedText(stateLabels[lensState] || stateLabels.ready))}</span>
                </div>
                <div class="unified-lens-grid">
                    <section class="unified-lens-card" data-lens-card="view">
                        <span class="unified-lens-label">${escapeHtml(translateUnifiedText('当前视图'))}</span>
                        <strong>${escapeHtml(currentView)}</strong>
                        <span>${escapeHtml(`${formatUnifiedMailboxCount(totalCount, '个邮箱', 'mailbox')} · ${filterDetail}`)}</span>
                    </section>
                    <section class="unified-lens-card" data-lens-card="provider">
                        <span class="unified-lens-label">${escapeHtml(translateUnifiedText('Provider 就绪'))}</span>
                        <strong>${escapeHtml(getUnifiedProviderReadinessStatusLabel(providerCounts.status))}</strong>
                        <span>${escapeHtml(providerDetail)}</span>
                    </section>
                    <section class="unified-lens-card" data-lens-card="action">
                        <span class="unified-lens-label">${escapeHtml(translateUnifiedText('建议动作'))}</span>
                        <strong>${escapeHtml(translateUnifiedText(recommendation.title))}</strong>
                        <span>${escapeHtml(translateUnifiedText(recommendation.detail))}</span>
                        ${recommendation.actions.length ? `<div class="unified-lens-actions">${recommendation.actions.map(renderUnifiedLensAction).join('')}</div>` : ''}
                    </section>
                </div>
            `;
        }

        function renderUnifiedCommandInsight(label, value, detail = '') {
            return `
                <div class="unified-command-insight">
                    <span class="unified-command-insight-label">${escapeHtml(translateUnifiedText(label))}</span>
                    <strong>${escapeHtml(value)}</strong>
                    <small>${escapeHtml(detail || '')}</small>
                </div>
            `;
        }

        function renderUnifiedCommandMetric(label, value, detail = '') {
            return `
                <div class="unified-command-metric">
                    <span class="unified-command-metric-label">${escapeHtml(translateUnifiedText(label))}</span>
                    <span class="unified-command-metric-value">${escapeHtml(value)}</span>
                    <span class="unified-command-metric-detail">${escapeHtml(detail || '')}</span>
                </div>
            `;
        }

        function renderUnifiedCommandChip(label, detail) {
            return `
                <span class="unified-command-chip">
                    <span class="unified-command-chip-label">${escapeHtml(translateUnifiedText(label))}</span>
                    <span class="unified-command-chip-detail">${escapeHtml(detail)}</span>
                </span>
            `;
        }

        function renderUnifiedCommandState(state = 'loading') {
            const isError = state === 'error';
            const title = isError ? '统一邮箱服务暂不可用' : '正在读取统一邮箱服务…';
            const detail = isError ? '保留当前筛选，稍后可重试刷新目录' : '正在同步目录库存、来源策略和推荐视图';
            return `
                <div class="unified-command-state ${isError ? 'error' : 'loading'}">
                    <div class="unified-command-state-copy">
                        <span class="unified-command-kicker">${escapeHtml(translateUnifiedText('统一邮箱服务'))}</span>
                        <strong>${escapeHtml(translateUnifiedText(title))}</strong>
                        <span>${escapeHtml(translateUnifiedText(detail))}</span>
                    </div>
                    <div class="unified-command-state-grid" aria-hidden="true">
                        <span></span><span></span><span></span><span></span>
                    </div>
                    ${isError ? `<button type="button" class="btn-inline ghost" onclick="loadUnifiedMailboxes(true)">${escapeHtml(translateUnifiedText('重试'))}</button>` : ''}
                </div>
            `;
        }

        function renderUnifiedCommandCenter(data = {}, state = 'ready') {
            const container = document.getElementById('unifiedMailboxCommandCenter');
            if (!container) return;
            container.dataset.state = state;
            if (state === 'loading') {
                container.innerHTML = renderUnifiedCommandState('loading');
                return;
            }
            if (state === 'error') {
                container.innerHTML = renderUnifiedCommandState('error');
                return;
            }

            const summary = data.summary && typeof data.summary === 'object' ? data.summary : {};
            const facets = data.facets && typeof data.facets === 'object' ? data.facets : {};
            const contract = data.contract && typeof data.contract === 'object' ? data.contract : {};
            const providerContext = data.provider_context && typeof data.provider_context === 'object' ? data.provider_context : {};
            const providerDiagnostics = providerContext.provider_diagnostics || {};
            const diagnostics = providerDiagnostics.summary || {};
            const sourcePriority = getUnifiedCommandSourcePriority(providerContext);
            const providerEndpoint = getUnifiedCommandEndpoint(providerContext);
            const total = Number(summary.total || (data.pagination || {}).total_count || 0);
            const accountCount = Number(summary.account || 0);
            const tempCount = Number(summary.temp || 0);
            const readinessSummary = getUnifiedProviderReadinessSummary(providerContext);
            const readinessTotals = readinessSummary.totals || {};
            const activeProviderCount = Number(readinessTotals.active_providers || diagnostics.active || 0);
            const readyProviderCount = Number(readinessTotals.ready_providers || diagnostics.ready || 0);
            const needsConfigCount = Number(readinessTotals.needs_config_providers || diagnostics.needs_config || 0);
            const providerCount = getUnifiedCommandProviderCount(providerContext, facets);
            const actionCount = getUnifiedCommandActionCount(contract, facets);
            const routeMode = getUnifiedCommandProviderMode(providerContext);
            const routeText = [sourcePriority, routeMode, providerEndpoint].filter(Boolean).join(' · ');
            const currentFilters = data.filters || unifiedMailboxState.filters;
            const tempDefaultProvider = getUnifiedCommandDefaultProvider(providerContext, 'temp_mail_provider');
            const poolDefaultProvider = getUnifiedCommandDefaultProvider(providerContext, 'pool_claim_provider', 'auto');
            const providerReadinessText = `${activeProviderCount} ${translateUnifiedText('启用')} · ${readyProviderCount} ${translateUnifiedText('就绪')}`;

            container.innerHTML = `
                <div class="unified-command-main">
                    <div class="unified-command-copy">
                        <span class="unified-command-kicker">${escapeHtml(translateUnifiedText('统一邮箱服务'))}</span>
                        <h3>${escapeHtml(translateUnifiedText('统一邮箱工作台'))}</h3>
                        <p>${escapeHtml(translateUnifiedText('集中管理 Outlook、IMAP、临时邮箱与外部 API 调用'))}</p>
                    </div>
                    <div class="unified-command-route" title="${escapeHtml(routeText)}">
                        <span>${escapeHtml(translateUnifiedText('当前路由'))}</span>
                        <code>${escapeHtml(routeText)}</code>
                    </div>
                    <div class="unified-command-insights" aria-label="${escapeHtml(translateUnifiedText('统一邮箱路由摘要'))}">
                        ${renderUnifiedCommandInsight('运行默认', tempDefaultProvider, translateUnifiedText('临时邮箱默认'))}
                        ${renderUnifiedCommandInsight('领取默认', poolDefaultProvider, translateUnifiedText('Pool 默认'))}
                        ${renderUnifiedCommandInsight('来源优先级', sourcePriority, translateUnifiedText('Provider 选择'))}
                        ${renderUnifiedCommandInsight('目录入口', providerEndpoint, translateUnifiedText('外部调用'))}
                    </div>
                </div>
                <div class="unified-command-metrics">
                    ${renderUnifiedCommandMetric('目录库存', formatUnifiedMailboxCount(total, '个邮箱', 'mailbox'), `${accountCount} ${translateUnifiedText('普通账号')} · ${tempCount} ${translateUnifiedText('临时邮箱')}`)}
                    ${renderUnifiedCommandMetric('邮箱来源', String(providerCount), providerReadinessText)}
                    ${renderUnifiedCommandMetric('路由模式', routeMode, sourcePriority)}
                    ${renderUnifiedCommandMetric('外部入口', providerEndpoint, `${actionCount} ${translateUnifiedText('可用能力')}`)}
                </div>
                ${renderUnifiedCommandQuickViews(currentFilters, contract)}
                <div class="unified-command-workflows" aria-label="${escapeHtml(translateUnifiedText('统一邮箱工作流'))}">
                    ${renderUnifiedCommandChip('普通账号', translateUnifiedText('Graph/IMAP 读信与验证码提取'))}
                    ${renderUnifiedCommandChip('临时邮箱', translateUnifiedText('按 provider 创建、读取与远端清理'))}
                    ${renderUnifiedCommandChip('Provider 路由', `${translateUnifiedText('环境变量')} / ${translateUnifiedText('配置文件')} / ${translateUnifiedText('配置项')}`)}
                    ${renderUnifiedCommandChip('外部调用', providerEndpoint)}
                </div>
                ${needsConfigCount > 0 ? `<div class="unified-command-notice">${escapeHtml(`${translateUnifiedText('需要配置')}: ${needsConfigCount} ${translateUnifiedText('邮箱来源')}`)}</div>` : ''}
            `;
        }

        function renderUnifiedLoadingState() {
            const list = document.getElementById('unifiedMailboxList');
            const pagination = document.getElementById('unifiedMailboxPagination');
            unifiedMailboxState.items = [];
            if (list) {
                list.innerHTML = `<div class="loading-overlay unified-state-block"><span class="spinner"></span> ${escapeHtml(translateUnifiedText('加载中…'))}</div>`;
            }
            if (pagination) {
                pagination.innerHTML = '';
                pagination.style.display = 'none';
            }
            renderUnifiedResultBar({ state: 'loading' });
            renderUnifiedSetupGuide({}, 'loading');
            renderUnifiedOperationalLens({}, 'loading');
            renderUnifiedProviderContext({}, 'loading');
            renderUnifiedProviderCapabilityMatrix({}, {}, 'loading', 'all');
            renderUnifiedCommandCenter({}, 'loading');
        }

        function renderUnifiedErrorState(message = '邮箱目录加载失败') {
            const list = document.getElementById('unifiedMailboxList');
            renderUnifiedResultBar({ state: 'error' });
            renderUnifiedSetupGuide({}, 'error');
            renderUnifiedOperationalLens({}, 'error');
            renderUnifiedProviderContext({}, 'error');
            renderUnifiedProviderCapabilityMatrix({}, {}, 'error', 'all');
            renderUnifiedCommandCenter({}, 'error');
            if (!list) return;
            list.innerHTML = `
                <div class="empty-state-lite unified-state-block">
                    <p>${escapeHtml(translateUnifiedText(message))}</p>
                    <button class="btn-inline ghost" onclick="loadUnifiedMailboxes(true)">${escapeHtml(translateUnifiedText('重试'))}</button>
                </div>
            `;
        }

        function renderUnifiedSummary(summary = {}, contract = {}) {
            const container = document.getElementById('unifiedMailboxSummary');
            if (!container) return;
            const fallbackFields = [
                { key: 'total', label: '总数', label_en: 'Total' },
                { key: 'account', label: '普通账号', label_en: 'Accounts' },
                { key: 'temp', label: '临时邮箱', label_en: 'Temp mailboxes' },
                { key: 'active', label: '可用', label_en: 'Active' },
                { key: 'inactive', label: '不可用', label_en: 'Inactive' },
                { key: 'pool', label: '号池', label_en: 'Pool' }
            ];
            const fields = Array.isArray(contract.summary_fields) && contract.summary_fields.length > 0
                ? contract.summary_fields
                : fallbackFields;
            container.innerHTML = fields.map(field => {
                const key = String(field && field.key || '').trim();
                const label = String(field && (field.label || field.label_en || key) || key);
                const value = key ? summary[key] : 0;
                return `
                <div class="unified-summary-item" data-summary-key="${escapeHtml(key)}">
                    <span class="unified-summary-value">${Number(value || 0)}</span>
                    <span class="unified-summary-label">${escapeHtml(translateUnifiedText(label))}</span>
                </div>
            `;
            }).join('');
        }

        function formatUnifiedProviderList(activeProviders = []) {
            if (!Array.isArray(activeProviders) || activeProviders.length === 0) {
                return translateUnifiedText('全部 Provider');
            }
            const visible = activeProviders.slice(0, 3).map(item => String(item || '').trim()).filter(Boolean);
            const suffix = activeProviders.length > visible.length ? ` +${activeProviders.length - visible.length}` : '';
            return visible.join(', ') + suffix;
        }

        function dedupeUnifiedTempProviderRows(providers) {
            // Collapse catalog dual rows (e.g. custom_domain_temp_mail + legacy_bridge)
            // into one operator-facing readiness/capability row.
            const map = new Map();
            (Array.isArray(providers) ? providers : []).forEach(item => {
                if (!item || typeof item !== 'object') return;
                const rawProvider = String(item.provider || item.key || item.name || '').trim();
                if (!rawProvider) return;
                const kind = String(item.kind || '').trim().toLowerCase();
                const canonical = (kind === 'account')
                    ? rawProvider.toLowerCase()
                    : (canonicalizeUnifiedTempProviderKey(rawProvider) || rawProvider.toLowerCase());
                const existing = map.get(canonical);
                if (!existing) {
                    map.set(canonical, {
                        ...item,
                        provider: canonical,
                    });
                    return;
                }
                map.set(canonical, {
                    ...existing,
                    ...item,
                    provider: canonical,
                    label: existing.label || item.label || item.provider_label || canonical,
                    provider_label: existing.provider_label || item.provider_label || existing.label || canonical,
                    mailbox_count: Number(existing.mailbox_count || 0) + Number(item.mailbox_count || 0),
                    account_count: Number(existing.account_count || 0) + Number(item.account_count || 0),
                    temp_count: Number(existing.temp_count || 0) + Number(item.temp_count || 0),
                    active: existing.active === true || item.active === true,
                    configured: existing.configured === true || item.configured === true,
                    usable: existing.usable === true || item.usable === true,
                });
            });
            return Array.from(map.values());
        }

        function renderUnifiedProviderRoutingMatrix(readinessSummary = {}) {
            const routingMatrix = getUnifiedProviderRoutingMatrix(readinessSummary);
            const scopes = routingMatrix.scopes && typeof routingMatrix.scopes === 'object' ? routingMatrix.scopes : {};
            const scopeRows = Object.values(scopes).filter(scope => scope && typeof scope === 'object').slice(0, 4);
            if (!scopeRows.length) return '';
            return `
                <div class="unified-provider-routing-matrix" aria-label="${escapeHtml(translateUnifiedText('Provider 路由'))}">
                    ${scopeRows.map(scope => {
                        const counts = scope.counts && typeof scope.counts === 'object' ? scope.counts : {};
                        const providers = dedupeUnifiedTempProviderRows(
                            Array.isArray(scope.providers) ? scope.providers.filter(provider => provider && typeof provider === 'object') : []
                        );
                        const visibleProviders = providers.slice(0, 4);
                        const usableCount = Number(counts.usable || providers.filter(item => item.usable).length || 0);
                        const totalCount = Number(providers.length || counts.total || 0);
                        const endpoint = String(scope.endpoint || '').trim();
                        return `
                            <div class="unified-provider-routing-scope" data-scope="${escapeHtml(scope.scope || '')}">
                                <div class="unified-provider-routing-head">
                                    <span>${escapeHtml(translateUnifiedText(scope.label || scope.scope || 'Provider 路由'))}</span>
                                    <strong>${usableCount}/${totalCount}</strong>
                                </div>
                                <code>${escapeHtml([scope.request_field, endpoint].filter(Boolean).join(' · ') || '-')}</code>
                                ${visibleProviders.length ? `
                                    <div class="unified-provider-routing-providers">
                                        ${visibleProviders.map(provider => `
                                            <span data-usable="${provider.usable ? 'true' : 'false'}">${escapeHtml(getUnifiedMailboxProviderDisplayLabel(provider))}</span>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        function renderUnifiedProviderReadinessSummary(providerContext = {}) {
            const readinessSummary = getUnifiedProviderReadinessSummary(providerContext);
            if (!readinessSummary.version) return '';
            const totals = readinessSummary.totals && typeof readinessSummary.totals === 'object' ? readinessSummary.totals : {};
            const issues = readinessSummary.issues && typeof readinessSummary.issues === 'object' ? readinessSummary.issues : {};
            const selectorFields = readinessSummary.provider_selector_fields && typeof readinessSummary.provider_selector_fields === 'object'
                ? readinessSummary.provider_selector_fields
                : {};
            const endpoints = readinessSummary.endpoints && typeof readinessSummary.endpoints === 'object' ? readinessSummary.endpoints : {};
            const providers = dedupeUnifiedTempProviderRows(
                Array.isArray(readinessSummary.providers)
                    ? readinessSummary.providers.filter(item => item && typeof item === 'object')
                    : []
            );
            const visibleProviders = providers.slice(0, 6);
            const hiddenCount = providers.length - visibleProviders.length;
            const selectorText = [
                selectorFields.pool_claim ? `pool ${selectorFields.pool_claim}` : '',
                selectorFields.task_temp_apply ? `task ${selectorFields.task_temp_apply}` : ''
            ].filter(Boolean).join(' · ');
            const issueText = `${Number(issues.needs_config || 0)} ${translateUnifiedText('缺配置')} · ${Number(issues.inactive || 0)} ${translateUnifiedText('未启用')}`;
            return `
                <div class="unified-provider-readiness-summary" data-status="${escapeHtml(readinessSummary.overall_status || 'unknown')}">
                    <div class="unified-provider-readiness-head">
                        <div>
                            <span class="unified-provider-context-label">${escapeHtml(translateUnifiedText('目录就绪度'))}</span>
                            <strong>${escapeHtml(getUnifiedProviderReadinessStatusLabel(readinessSummary.overall_status))}</strong>
                        </div>
                        <code>${escapeHtml(endpoints.mailboxes || '/api/v1/external/mailboxes')}</code>
                    </div>
                    <div class="unified-provider-readiness-metrics">
                        <span><strong>${Number(totals.mailboxes || 0)}</strong>${escapeHtml(translateUnifiedText('邮箱'))}</span>
                        <span><strong>${Number(totals.account_mailboxes || 0)}</strong>${escapeHtml(translateUnifiedText('普通账号'))}</span>
                        <span><strong>${Number(totals.temp_mailboxes || 0)}</strong>${escapeHtml(translateUnifiedText('临时邮箱'))}</span>
                        <span><strong>${Number(totals.providers || 0)}</strong>${escapeHtml(translateUnifiedText('Provider'))}</span>
                    </div>
                    <div class="unified-provider-readiness-meta">
                        <span>${escapeHtml(selectorText || '-')}</span>
                        <span>${escapeHtml(issueText)}</span>
                    </div>
                    ${renderUnifiedProviderRoutingMatrix(readinessSummary)}
                    ${visibleProviders.length ? `
                        <div class="unified-provider-readiness-list" role="list" aria-label="${escapeHtml(translateUnifiedText('Provider 就绪度'))}">
                            ${visibleProviders.map(provider => `
                                <div class="unified-provider-readiness-row" role="listitem" data-provider="${escapeHtml(provider.provider || '')}">
                                    <span>${escapeHtml(getUnifiedMailboxProviderDisplayLabel(provider))}</span>
                                    <code>${escapeHtml([provider.kind, provider.provider].filter(Boolean).join('/'))}</code>
                                    <strong>${Number(provider.mailbox_count || 0)}</strong>
                                    <em>${escapeHtml(getUnifiedProviderReadinessStatusLabel(provider.readiness_status))}</em>
                                </div>
                            `).join('')}
                            ${hiddenCount > 0 ? `<div class="unified-provider-readiness-more">${escapeHtml(`+${hiddenCount} ${translateUnifiedText('更多 Provider')}`)}</div>` : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        function renderUnifiedProviderContext(providerContext = {}, state = 'ready', providerFacets = [], selectedProvider = 'all') {
            const container = document.getElementById('unifiedMailboxProviderContext');
            if (!container) return;
            const hasContext = providerContext && typeof providerContext === 'object' && Number(providerContext.version || 0) > 0;
            if (!hasContext) {
                const isLoading = state === 'loading';
                const fallback = isLoading ? '正在读取来源配置…' : '来源配置不可用';
                container.dataset.state = isLoading ? 'loading' : (state === 'error' ? 'error' : 'warning');
                container.innerHTML = `
                    <div class="unified-provider-context-empty">${escapeHtml(translateUnifiedText(fallback))}</div>
                    ${renderUnifiedProviderFacetChips(providerFacets, selectedProvider)}
                `;
                return;
            }

            const defaults = providerContext.defaults || {};
            const providerFilter = providerContext.provider_filter || {};
            const providerDiagnostics = providerContext.provider_diagnostics || {};
            const diagnostics = providerDiagnostics.summary || {};
            const defaultsDiagnostics = providerDiagnostics.defaults || {};
            const selectionPolicy = providerContext.selection_policy || {};
            const deploymentProfile = providerContext.deployment_profile || {};
            const discovery = providerContext.discovery || {};
            const configFile = getUnifiedProviderConfigFile(selectionPolicy, deploymentProfile, providerFilter);
            const rawActiveProviders = Array.isArray(defaults.active_mailbox_providers)
                ? defaults.active_mailbox_providers
                : (Array.isArray(providerFilter.active_providers) ? providerFilter.active_providers : []);
            const activeProviders = (typeof canonicalizeMailboxProviderAllowlistValues === 'function'
                ? canonicalizeMailboxProviderAllowlistValues(rawActiveProviders)
                : dedupeUnifiedTempProviderRows(
                    rawActiveProviders.map(item => ({ provider: item, kind: 'temp' }))
                ).map(item => item.provider)
            ).filter(value => value && value !== 'auto');
            const sourcePriority = Array.isArray(selectionPolicy.source_priority)
                ? selectionPolicy.source_priority.join(' > ')
                : '';
            const providersEndpoint = getUnifiedProviderContextText(discovery.providers_endpoint, '');
            const providerHealthEndpoint = getUnifiedProviderContextText(discovery.provider_health_endpoint, '');
            const readyCount = Number(diagnostics.ready || 0);
            const needsConfigCount = Number(diagnostics.needs_config || 0);
            const activeCount = Number(diagnostics.active || 0);
            const totalCount = Number(diagnostics.total || activeCount || 0);
            const tempDefaultDiagnostic = defaultsDiagnostics.temp_mail_provider || {};
            const poolDefaultDiagnostic = defaultsDiagnostics.pool_claim_provider || {};
            const status = getUnifiedProviderContextState(providerFilter, defaultsDiagnostics, configFile, diagnostics);
            const notices = buildUnifiedProviderNoticeMessages(providerFilter, defaultsDiagnostics, configFile, diagnostics);
            const noticeSeparator = typeof getUiLanguage === 'function' && getUiLanguage() === 'en' ? '; ' : '；';
            container.dataset.state = status;
            const items = [
                {
                    label: '运行默认',
                    value: getUnifiedProviderContextText(defaults.temp_mail_provider),
                    meta: formatUnifiedProviderSourceDetail(tempDefaultDiagnostic, defaults.temp_mail_provider_env)
                },
                {
                    label: '领取默认',
                    value: getUnifiedProviderContextText(defaults.pool_claim_provider, 'auto'),
                    meta: formatUnifiedProviderSourceDetail(poolDefaultDiagnostic, defaults.pool_claim_provider_env)
                },
                {
                    label: '来源模式',
                    value: formatUnifiedProviderMode(providerFilter.mode, activeProviders),
                    meta: formatUnifiedProviderList(activeProviders)
                },
                {
                    label: '就绪状态',
                    value: `${readyCount} ${translateUnifiedText('就绪')}`,
                    meta: `${activeCount}/${totalCount} ${translateUnifiedText('启用')} · ${needsConfigCount} ${translateUnifiedText('缺配置')}`
                },
                {
                    label: '配置文件',
                    value: formatUnifiedProviderConfigFileStatus(configFile),
                    meta: getUnifiedProviderContextText(configFile.path || configFile.resolved_path, translateUnifiedText('无配置文件'))
                },
                {
                    label: '发现接口',
                    value: getUnifiedProviderContextText(providersEndpoint),
                    meta: getUnifiedProviderContextText(providerHealthEndpoint, translateUnifiedText('无'))
                }
            ];
            const meta = [sourcePriority, providersEndpoint].filter(Boolean).join(' · ');
            container.innerHTML = `
                <div class="unified-provider-context-head">
                    <div class="unified-provider-context-title-wrap">
                        <span class="unified-provider-context-title">${escapeHtml(translateUnifiedText('来源策略'))}</span>
                        <span class="unified-provider-context-status">${escapeHtml(getUnifiedProviderContextStatusLabel(status))}</span>
                    </div>
                    <span class="unified-provider-context-meta">${escapeHtml(meta || '-')}</span>
                </div>
                ${notices.length ? `
                    <div class="unified-provider-context-alert" role="status">
                        <span class="unified-provider-context-alert-title">${escapeHtml(translateUnifiedText('配置提示'))}</span>
                        <span class="unified-provider-context-alert-text">${escapeHtml(notices.join(noticeSeparator))}</span>
                    </div>
                ` : ''}
                <div class="unified-provider-context-grid">
                    ${items.map(item => `
                        <div class="unified-provider-context-item">
                            <span class="unified-provider-context-label">${escapeHtml(translateUnifiedText(item.label))}</span>
                            <span class="unified-provider-context-value">${escapeHtml(item.value)}</span>
                            <span class="unified-provider-context-detail">${escapeHtml(item.meta || '')}</span>
                        </div>
                    `).join('')}
                </div>
                ${renderUnifiedProviderReadinessSummary(providerContext)}
                ${renderUnifiedProviderFacetChips(providerFacets, selectedProvider)}
            `;
        }

        function renderUnifiedProviderCapabilityWorkflowSummary(workflows = []) {
            if (!workflows.length) return '';
            return `
                <div class="unified-provider-capability-workflows" aria-label="${escapeHtml(translateUnifiedText('Provider 工作流'))}">
                    ${workflows.slice(0, 5).map(workflow => {
                        const label = String(workflow.label || workflow.workflow || workflow.key || '').trim();
                        const count = normalizeUnifiedProviderCapabilityNumber(workflow.provider_count);
                        return `<span><strong>${escapeHtml(translateUnifiedText(label))}</strong><code>${escapeHtml(String(count))}</code></span>`;
                    }).join('')}
                </div>
            `;
        }

        function renderUnifiedProviderCapabilityWorkflowChips(entries = []) {
            const values = Array.isArray(entries) ? entries : [];
            if (!values.length) {
                return `<span class="unified-provider-capability-chip muted">${escapeHtml(translateUnifiedText('暂无工作流'))}</span>`;
            }
            return values.map(item => {
                const stateLabel = item.enabled ? '支持' : '不支持';
                return `
                    <span class="unified-provider-capability-chip ${item.enabled ? 'enabled' : 'muted'}" aria-label="${escapeHtml(`${translateUnifiedText(item.label)}: ${translateUnifiedText(stateLabel)}`)}">
                        <span>${escapeHtml(translateUnifiedText(item.label))}</span>
                        <strong>${escapeHtml(translateUnifiedText(stateLabel))}</strong>
                    </span>
                `;
            }).join('');
        }

        function renderUnifiedProviderCapabilitySelectorFields(fields = []) {
            const values = Array.isArray(fields) ? fields : [];
            if (!values.length) {
                return `<span class="unified-provider-capability-muted">${escapeHtml(translateUnifiedText('暂无选择字段'))}</span>`;
            }
            return values.map(item => `
                <code>${escapeHtml(`${item.scope}: ${item.field || '-'}=${item.value || '-'}`)}</code>
            `).join('');
        }

        function renderUnifiedProviderCapabilityActionList(label, actions = []) {
            const values = normalizeUnifiedProviderCapabilityActions(actions);
            return `
                <div class="unified-provider-capability-actions">
                    <span>${escapeHtml(translateUnifiedText(label))}</span>
                    <div>${values.length ? values.map(action => `<code>${escapeHtml(action)}</code>`).join('') : `<span class="unified-provider-capability-muted">${escapeHtml(translateUnifiedText('暂无动作'))}</span>`}</div>
                </div>
            `;
        }

        function renderUnifiedProviderCapabilityEndpointList(endpoints = []) {
            const values = Array.isArray(endpoints) ? endpoints : [];
            if (!values.length) {
                return `<span class="unified-provider-capability-muted">${escapeHtml(translateUnifiedText('暂无端点'))}</span>`;
            }
            return values.map(item => `
                <span>${escapeHtml(translateUnifiedText(item.key))}</span>
                <code>${escapeHtml(item.value)}</code>
            `).join('');
        }

        function getUnifiedProviderCapabilityRows(providerContext = {}, contract = {}) {
            const matrixProviders = getUnifiedProviderCapabilityMatrixProviders(providerContext);
            const workflows = getUnifiedProviderCapabilityMatrixWorkflows(providerContext);
            const providers = dedupeUnifiedTempProviderRows(
                matrixProviders.length > 0 ? matrixProviders : getUnifiedProviderGuideProviders(providerContext)
            );
            return providers.map(provider => {
                const capabilities = provider.capabilities && typeof provider.capabilities === 'object' ? provider.capabilities : {};
                const configuration = normalizeUnifiedProviderCapabilityObject(provider.configuration);
                const read = normalizeUnifiedProviderCapabilityObject(provider.read);
                const inventory = normalizeUnifiedProviderCapabilityObject(provider.inventory);
                const kind = String(provider.kind || '').trim().toLowerCase();
                const providerKey = kind === 'account'
                    ? String(provider.provider || '').trim().toLowerCase()
                    : (canonicalizeUnifiedTempProviderKey(provider.provider) || String(provider.provider || '').trim().toLowerCase());
                const readCapability = String(read.capability || getUnifiedProviderReadCapability(provider)).trim().toLowerCase();
                const requiredEnv = normalizeUnifiedProviderCapabilityKeys(provider.required_env || configuration.required_env);
                const optionalEnv = normalizeUnifiedProviderCapabilityKeys(provider.optional_env || configuration.optional_env);
                const secretEnv = normalizeUnifiedProviderCapabilityKeys(provider.secret_env || configuration.secret_env);
                const secretSettings = normalizeUnifiedProviderCapabilityKeys(provider.secret_settings || configuration.secret_settings);
                const lifecycleActions = normalizeUnifiedProviderCapabilityActions(provider.lifecycle_actions);
                const endpoints = normalizeUnifiedProviderCapabilityEndpointMap(provider);
                const selectionFields = getUnifiedProviderCapabilitySelectorFields(provider.selection_fields);
                const workflowEntries = getUnifiedProviderCapabilityWorkflowEntries(provider.workflow_support, workflows);
                const missingConfig = normalizeUnifiedProviderCapabilityKeys(provider.missing_config || configuration.missing_config || configuration.missing_env || configuration.missing_settings);
                const missingConfigCount = normalizeUnifiedProviderCapabilityNumber(provider.missing_config_count || configuration.missing_config_count || missingConfig.length);
                return {
                    provider: providerKey,
                    label: getUnifiedMailboxProviderDisplayLabel({
                        provider: providerKey,
                        label: provider.label,
                        provider_label: provider.provider_label,
                    }),
                    kind,
                    kindLabel: kind ? getUnifiedKindLabel(kind, contract) : translateUnifiedText('邮箱'),
                    state: getUnifiedProviderCapabilityState(provider),
                    active: normalizeUnifiedProviderCapabilityBool(provider.active),
                    configured: normalizeUnifiedProviderCapabilityBool(provider.configured),
                    readinessStatus: String(provider.readiness_status || '').trim(),
                    readinessReason: String(provider.readiness_reason || '').trim(),
                    configSource: String(provider.config_source || configuration.source || '').trim(),
                    missingConfig,
                    missingConfigCount,
                    requiredEnv,
                    optionalEnv,
                    secretKeys: [...secretEnv, ...secretSettings],
                    readCapability,
                    readCapabilityLabel: getUnifiedProviderReadCapabilityLabel(readCapability, contract),
                    readActions: normalizeUnifiedProviderCapabilityActions(read.actions),
                    lifecycleActions,
                    workflowEntries,
                    selectionFields,
                    inventory: {
                        mailboxCount: normalizeUnifiedProviderCapabilityNumber(inventory.mailbox_count),
                        accountCount: normalizeUnifiedProviderCapabilityNumber(inventory.account_count),
                        tempCount: normalizeUnifiedProviderCapabilityNumber(inventory.temp_count)
                    },
                    canDynamicCreate: normalizeUnifiedProviderCapabilityBool(capabilities.can_dynamic_create),
                    canDeleteMailbox: normalizeUnifiedProviderCapabilityBool(capabilities.can_delete_mailbox),
                    canDeleteMessage: normalizeUnifiedProviderCapabilityBool(capabilities.can_delete_message),
                    canClearMessages: normalizeUnifiedProviderCapabilityBool(capabilities.can_clear_messages),
                    endpoints,
                    healthEndpoint: (endpoints.find(item => item.key === 'provider_health') || {}).value || getUnifiedProviderCapabilityEndpoint(provider, 'health'),
                    directoryEndpoint: (endpoints.find(item => item.key === 'mailboxes') || {}).value || getUnifiedProviderCapabilityEndpoint(provider, 'mailbox_directory_filter')
                };
            }).filter(row => row.provider || row.label);
        }

        function renderUnifiedProviderCapabilityBadge(label, enabled) {
            const className = enabled ? 'enabled' : 'muted';
            const stateLabel = enabled ? '可用' : '不可用';
            return `
                <span class="unified-provider-capability-chip ${className}" aria-label="${escapeHtml(`${translateUnifiedText(label)}: ${translateUnifiedText(stateLabel)}`)}">
                    <span>${escapeHtml(translateUnifiedText(label))}</span>
                    <strong>${escapeHtml(translateUnifiedText(stateLabel))}</strong>
                </span>
            `;
        }

        function renderUnifiedProviderCapabilityKeys(keys, emptyText) {
            const values = normalizeUnifiedProviderCapabilityKeys(keys);
            if (!values.length) {
                return `<span class="unified-provider-capability-muted">${escapeHtml(translateUnifiedText(emptyText))}</span>`;
            }
            return values.map(key => `<code>${escapeHtml(key)}</code>`).join('');
        }

        function renderUnifiedProviderCapabilityMatrix(providerContext = {}, contract = {}, state = 'ready', selectedProvider = 'all') {
            const container = document.getElementById('unifiedProviderCapabilityMatrix');
            if (!container) return;
            container.dataset.state = state;
            if (state === 'loading') {
                container.innerHTML = `<div class="unified-provider-capability-empty"><span class="spinner"></span> ${escapeHtml(translateUnifiedText('正在读取 Provider 能力…'))}</div>`;
                return;
            }
            if (state === 'error') {
                container.innerHTML = `<div class="unified-provider-capability-empty">${escapeHtml(translateUnifiedText('Provider 能力暂不可用'))}</div>`;
                return;
            }

            const rows = getUnifiedProviderCapabilityRows(providerContext, contract);
            if (!rows.length) {
                container.dataset.state = 'empty';
                container.innerHTML = `<div class="unified-provider-capability-empty">${escapeHtml(translateUnifiedText('暂无 Provider 能力'))}</div>`;
                return;
            }

            const selected = String(selectedProvider || 'all').trim().toLowerCase() || 'all';
            const workflows = getUnifiedProviderCapabilityMatrixWorkflows(providerContext);
            const readyCount = rows.filter(row => row.state === 'ready').length;
            const needsConfigCount = rows.filter(row => row.state === 'needs-config').length;
            container.innerHTML = `
                <div class="unified-provider-capability-head">
                    <div class="unified-provider-capability-title-wrap">
                        <span class="unified-provider-capability-title">${escapeHtml(translateUnifiedText('Provider 能力矩阵'))}</span>
                        <span class="unified-provider-capability-count">${escapeHtml(`${rows.length} ${translateUnifiedText('邮箱来源')}`)}</span>
                    </div>
                    <span class="unified-provider-capability-meta">${escapeHtml(`${readyCount} ${translateUnifiedText('就绪')} · ${needsConfigCount} ${translateUnifiedText('缺配置')}`)}</span>
                </div>
                ${renderUnifiedProviderCapabilityWorkflowSummary(workflows)}
                <div class="unified-provider-capability-grid" role="list" aria-label="${escapeHtml(translateUnifiedText('Provider 能力矩阵'))}">
                    ${rows.map(row => {
                        const isActive = row.provider && row.provider === selected;
                        const configDetail = row.missingConfigCount > 0
                            ? `${row.missingConfigCount} ${translateUnifiedText('个缺失项')}`
                            : translateUnifiedText(row.configSource ? '配置来源' : '配置状态');
                        const inventoryText = `${row.inventory.mailboxCount} ${translateUnifiedText('邮箱')} · ${row.inventory.accountCount} ${translateUnifiedText('账号数')} · ${row.inventory.tempCount} ${translateUnifiedText('临时邮箱')}`;
                        return `
                            <article class="unified-provider-capability-row ${isActive ? 'active' : ''}" data-provider="${escapeHtml(row.provider)}" data-state="${escapeHtml(row.state)}" role="listitem">
                                <div class="unified-provider-capability-provider">
                                    <button type="button" class="unified-provider-capability-filter" data-provider="${escapeHtml(row.provider || 'all')}" aria-pressed="${isActive ? 'true' : 'false'}">
                                        <span>${escapeHtml(row.label)}</span>
                                        <code>${escapeHtml(row.provider || '-')}</code>
                                    </button>
                                    <span class="unified-provider-capability-kind">${escapeHtml(row.kindLabel)}</span>
                                </div>
                                <div class="unified-provider-capability-state">
                                    <span class="unified-provider-capability-state-badge ${escapeHtml(row.state)}">${escapeHtml(getUnifiedProviderCapabilityStateLabel(row.state))}</span>
                                    <span>${escapeHtml(`${translateUnifiedText(row.active ? '启用' : '未启用')} · ${translateUnifiedText(row.configured ? '已配置' : '未配置')}`)}</span>
                                    <small>${escapeHtml(row.configSource ? `${translateUnifiedText('配置来源')}: ${row.configSource}` : configDetail)}</small>
                                    ${row.readinessReason ? `<small>${escapeHtml(row.readinessReason)}</small>` : ''}
                                </div>
                                <div class="unified-provider-capability-chips">
                                    <span class="unified-provider-capability-chip enabled"><span>${escapeHtml(translateUnifiedText('读取方式'))}</span><strong>${escapeHtml(row.readCapabilityLabel)}</strong></span>
                                    ${renderUnifiedProviderCapabilityBadge('动态创建', row.canDynamicCreate)}
                                    ${renderUnifiedProviderCapabilityBadge('删除远端邮箱', row.canDeleteMailbox)}
                                    ${renderUnifiedProviderCapabilityBadge('删除邮件', row.canDeleteMessage)}
                                    ${renderUnifiedProviderCapabilityBadge('清空邮件', row.canClearMessages)}
                                </div>
                                <div class="unified-provider-capability-workflow-row">
                                    <span>${escapeHtml(translateUnifiedText('工作流支持'))}</span>
                                    <div>${renderUnifiedProviderCapabilityWorkflowChips(row.workflowEntries)}</div>
                                </div>
                                <div class="unified-provider-capability-selectors">
                                    <span>${escapeHtml(translateUnifiedText('选择字段'))}</span>
                                    <div>${renderUnifiedProviderCapabilitySelectorFields(row.selectionFields)}</div>
                                </div>
                                ${renderUnifiedProviderCapabilityActionList('读取动作', row.readActions)}
                                ${renderUnifiedProviderCapabilityActionList('生命周期', row.lifecycleActions)}
                                <div class="unified-provider-capability-inventory">
                                    <span>${escapeHtml(translateUnifiedText('库存'))}</span>
                                    <code>${escapeHtml(inventoryText)}</code>
                                </div>
                                <div class="unified-provider-capability-keys">
                                    <span>${escapeHtml(translateUnifiedText('缺失配置'))}</span>
                                    <div>${renderUnifiedProviderCapabilityKeys(row.missingConfig, '无')}</div>
                                </div>
                                <div class="unified-provider-capability-keys">
                                    <span>${escapeHtml(translateUnifiedText('必需环境变量'))}</span>
                                    <div>${renderUnifiedProviderCapabilityKeys(row.requiredEnv, '无')}</div>
                                </div>
                                <div class="unified-provider-capability-keys">
                                    <span>${escapeHtml(translateUnifiedText('可选环境变量'))}</span>
                                    <div>${renderUnifiedProviderCapabilityKeys(row.optionalEnv, '无')}</div>
                                </div>
                                <div class="unified-provider-capability-keys">
                                    <span>${escapeHtml(translateUnifiedText('密钥字段名'))}</span>
                                    <div>${renderUnifiedProviderCapabilityKeys(row.secretKeys, '无')}</div>
                                </div>
                                <div class="unified-provider-capability-endpoints">
                                    ${renderUnifiedProviderCapabilityEndpointList(row.endpoints)}
                                </div>
                            </article>
                        `;
                    }).join('')}
                </div>
            `;
        }

        function renderUnifiedLabels(item) {
            const labels = Array.isArray(item && item.labels) ? item.labels.filter(Boolean) : [];
            if (labels.length === 0) {
                return `<span class="tag-chip muted">${escapeHtml(translateUnifiedText('暂无标签'))}</span>`;
            }
            return labels.slice(0, 4).map(label => `<span class="tag-chip">${escapeHtml(String(label))}</span>`).join('');
        }

        function renderUnifiedActionSummary(item) {
            const actions = item && item.actions && typeof item.actions === 'object' ? item.actions : {};
            const definitions = getUnifiedActionDefinitions(item);
            if (definitions.length === 0) {
                return `<div class="unified-action-strip" aria-label="${escapeHtml(translateUnifiedText('邮箱能力'))}"><span class="unified-action-chip muted">${escapeHtml(translateUnifiedText('暂无'))}</span></div>`;
            }
            return `
                <div class="unified-action-strip" aria-label="${escapeHtml(translateUnifiedText('邮箱能力'))}">
                    ${definitions.map(definition => {
                        const action = String(definition && definition.action || '').trim();
                        if (!action) return '';
                        const label = String(definition.label || definition.label_en || action).trim() || action;
                        const isEnabled = Boolean(actions[action]);
                        const displayLabel = translateUnifiedText(label);
                        const stateLabel = translateUnifiedText(isEnabled ? '可用' : '不可用');
                        return `<span class="unified-action-chip ${isEnabled ? 'enabled' : 'muted'}" data-action="${escapeHtml(action)}" aria-label="${escapeHtml(`${displayLabel}: ${stateLabel}`)}">${escapeHtml(displayLabel)}</span>`;
                    }).join('')}
                </div>
            `;
        }


        function renderUnifiedPreviewEmpty() {
            return `
                <div class="unified-message-empty">
                    <div>
                        <span class="unified-message-kicker">${escapeHtml(translateUnifiedText('Inbox Preview'))}</span>
                        <h3 id="unifiedMessagePreviewTitle">${escapeHtml(translateUnifiedText('统一收件箱预览'))}</h3>
                        <p>${escapeHtml(translateUnifiedText('选择一个邮箱查看邮件'))}</p>
                    </div>
                </div>
            `;
        }

        function renderUnifiedMessageRows(messages = []) {
            const preview = unifiedMailboxState.preview;
            if (!Array.isArray(messages) || messages.length === 0) {
                return `<div class="unified-message-list-empty">${escapeHtml(translateUnifiedText('暂无邮件'))}</div>`;
            }
            return messages.map(message => {
                const id = String(message && message.id || '');
                const active = id && id === preview.selectedMessageId;
                const subject = String(message && message.subject || translateUnifiedText('无主题'));
                const fromAddress = String(message && (message.from_address || message.from) || translateUnifiedText('未知'));
                const previewText = String(message && (message.body_preview || message.content_preview) || '');
                const createdAt = String(message && (message.created_at || message.date) || '');
                const timeText = createdAt && typeof formatRelativeTime === 'function' ? formatRelativeTime(createdAt) : createdAt;
                return `
                    <button type="button" class="unified-message-row ${active ? 'active' : ''}" data-message-id="${escapeHtml(id)}" onclick="loadUnifiedMailboxMessageDetail('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, '${escapeJs(id)}')" aria-pressed="${active ? 'true' : 'false'}">
                        <span class="unified-message-row-topline">
                            <strong>${escapeHtml(subject)}</strong>
                            <time>${escapeHtml(timeText)}</time>
                        </span>
                        <span class="unified-message-row-from">${escapeHtml(fromAddress)}</span>
                        <span class="unified-message-row-preview">${escapeHtml(previewText || translateUnifiedText('无正文预览'))}</span>
                    </button>
                `;
            }).join('');
        }

        function renderUnifiedMessageBody(message = {}) {
            const bodyType = String(message.body_type || (message.has_html ? 'html' : 'text')).trim().toLowerCase();
            const body = String(message.body || (bodyType === 'html' ? message.body_html : message.body_text) || '');
            if (!body) {
                return `<div class="unified-message-body empty">${escapeHtml(translateUnifiedText('暂无正文'))}</div>`;
            }
            if (bodyType === 'html') {
                const safeHtml = window.DOMPurify && typeof window.DOMPurify.sanitize === 'function'
                    ? window.DOMPurify.sanitize(body, { USE_PROFILES: { html: true } })
                    : escapeHtml(body);
                return `<div class="unified-message-body html" data-body-type="html">${safeHtml}</div>`;
            }
            return `<pre class="unified-message-body text" data-body-type="text">${escapeHtml(body)}</pre>`;
        }

        function renderUnifiedVerificationResult(verification = null) {
            const preview = unifiedMailboxState.preview;
            if (preview.verificationLoading) {
                return `<div class="unified-message-verification loading"><span class="spinner"></span>${escapeHtml(translateUnifiedText('正在提取验证码…'))}</div>`;
            }
            if (preview.verificationError) {
                return `
                    <div class="unified-message-verification error">
                        <strong>${escapeHtml(translateUnifiedText('验证码结果'))}</strong>
                        <p>${escapeHtml(preview.verificationError)}</p>
                    </div>
                `;
            }
            if (!verification || typeof verification !== 'object') {
                return `<div class="unified-message-verification empty">${escapeHtml(translateUnifiedText('点击提取验证码查看结果'))}</div>`;
            }
            const code = String(verification.verification_code || '').trim();
            const link = String(verification.verification_link || '').trim();
            const formatted = String(verification.formatted || '').trim();
            const confidence = String(verification.confidence || verification.code_confidence || verification.link_confidence || '').trim();
            return `
                <div class="unified-message-verification ready">
                    <div class="unified-message-verification-head">
                        <strong>${escapeHtml(translateUnifiedText('验证码结果'))}</strong>
                        ${confidence ? `<span>${escapeHtml(translateUnifiedText('置信度'))}: ${escapeHtml(confidence)}</span>` : ''}
                    </div>
                    <div class="unified-message-verification-grid">
                        <div>
                            <span>${escapeHtml(translateUnifiedText('验证码'))}</span>
                            <strong>${escapeHtml(code || translateUnifiedText('未找到'))}</strong>
                            ${code ? `<button type="button" class="btn-inline ghost" onclick="copyUnifiedPreviewValue('${escapeJs(code)}', '验证码已复制')">${escapeHtml(translateUnifiedText('复制验证码'))}</button>` : ''}
                        </div>
                        <div>
                            <span>${escapeHtml(translateUnifiedText('验证链接'))}</span>
                            <strong>${escapeHtml(link || translateUnifiedText('未找到'))}</strong>
                            ${link ? `<button type="button" class="btn-inline ghost" onclick="copyUnifiedPreviewValue('${escapeJs(link)}', '验证链接已复制')">${escapeHtml(translateUnifiedText('复制验证链接'))}</button>` : ''}
                        </div>
                    </div>
                    ${formatted ? `<p class="unified-message-verification-formatted">${escapeHtml(formatted)}</p>` : ''}
                </div>
            `;
        }

        function renderUnifiedMessageDetail() {
            const preview = unifiedMailboxState.preview;
            if (preview.detailLoading) {
                return `<div class="unified-message-detail loading"><span class="spinner"></span>${escapeHtml(translateUnifiedText('正在读取邮件详情…'))}</div>`;
            }
            if (preview.detailError) {
                return `
                    <div class="unified-message-detail error">
                        <strong>${escapeHtml(translateUnifiedText('邮件详情'))}</strong>
                        <p>${escapeHtml(preview.detailError)}</p>
                        ${preview.selectedMessageId ? `<button type="button" class="btn-inline ghost" onclick="loadUnifiedMailboxMessageDetail('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, '${escapeJs(preview.selectedMessageId)}', { force: true })">${escapeHtml(translateUnifiedText('重试'))}</button>` : ''}
                    </div>
                `;
            }
            const message = preview.message;
            if (!message) {
                return `<div class="unified-message-detail empty">${escapeHtml(translateUnifiedText('选择一封邮件查看详情'))}</div>`;
            }
            const subject = String(message.subject || translateUnifiedText('无主题'));
            const fromAddress = String(message.from_address || message.from || translateUnifiedText('未知'));
            const toAddress = String(message.to_address || message.to || message.email_address || '');
            const createdAt = String(message.created_at || message.date || '');
            return `
                <article class="unified-message-detail ready">
                    <div class="unified-message-detail-head">
                        <div>
                            <span class="unified-message-kicker">${escapeHtml(translateUnifiedText('邮件详情'))}</span>
                            <h4>${escapeHtml(subject)}</h4>
                        </div>
                        <time>${escapeHtml(createdAt)}</time>
                    </div>
                    <div class="unified-message-detail-meta">
                        <span><strong>${escapeHtml(translateUnifiedText('发件人'))}</strong>${escapeHtml(fromAddress)}</span>
                        ${toAddress ? `<span><strong>${escapeHtml(translateUnifiedText('收件人'))}</strong>${escapeHtml(toAddress)}</span>` : ''}
                        <span><strong>${escapeHtml(translateUnifiedText('正文'))}</strong>${escapeHtml(translateUnifiedText(message.body_type === 'html' ? 'HTML 正文' : '文本正文'))}</span>
                    </div>
                    ${renderUnifiedMessageBody(message)}
                    ${renderUnifiedVerificationResult(preview.verification)}
                </article>
            `;
        }

        function renderUnifiedMessagePreview() {
            const container = document.getElementById('unifiedMailboxMessagePreview');
            if (!container) return;
            const preview = unifiedMailboxState.preview || {};
            if (!preview.selectedKey) {
                container.dataset.state = 'empty';
                container.innerHTML = renderUnifiedPreviewEmpty();
                return;
            }
            const mailbox = preview.mailbox || getUnifiedPreviewMailboxItem(preview.selectedKind, preview.selectedSourceId) || {};
            const email = String(mailbox.email || '');
            const method = String((preview.messages[0] && preview.messages[0].method) || (preview.message && preview.message.method) || mailbox.method || '');
            const state = preview.loading ? 'loading' : (preview.error ? 'error' : 'ready');
            container.dataset.state = state;
            container.innerHTML = `
                <div class="unified-message-head">
                    <div class="unified-message-title-wrap">
                        <span class="unified-message-kicker">${escapeHtml(translateUnifiedText('统一收件箱预览'))}</span>
                        <h3 id="unifiedMessagePreviewTitle">${escapeHtml(email || translateUnifiedText('选中邮箱'))}</h3>
                        <p>${escapeHtml(getUnifiedPreviewMailboxLabel(mailbox) || translateUnifiedText('统一读取通道'))}</p>
                    </div>
                    <div class="unified-message-head-meta">
                        <span>${escapeHtml(getUnifiedKindLabel(mailbox.kind || preview.selectedKind))}</span>
                        <span>${escapeHtml(method || translateUnifiedText('读取邮件'))}</span>
                        <span>${escapeHtml((preview.folder || 'inbox').toUpperCase())}</span>
                    </div>
                    <div class="unified-message-actions">
                        <button type="button" class="btn-inline ghost" onclick="loadUnifiedMailboxMessages('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, { force: true })" ${preview.loading ? 'disabled' : ''}>${escapeHtml(translateUnifiedText('刷新邮件'))}</button>
                        <button type="button" class="btn-inline primary" onclick="loadUnifiedMailboxVerification('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, { force: true })" ${preview.verificationLoading ? 'disabled' : ''}>${escapeHtml(translateUnifiedText('提取验证码'))}</button>
                    </div>
                </div>
                ${preview.loading ? `<div class="unified-message-preview-state"><span class="spinner"></span>${escapeHtml(translateUnifiedText('正在读取邮件…'))}</div>` : ''}
                ${preview.error ? `<div class="unified-message-preview-state error"><p>${escapeHtml(preview.error)}</p><button type="button" class="btn-inline ghost" onclick="loadUnifiedMailboxMessages('${escapeJs(preview.selectedKind)}', ${Number(preview.selectedSourceId || 0)}, { force: true })">${escapeHtml(translateUnifiedText('重试'))}</button></div>` : ''}
                ${!preview.loading && !preview.error ? `
                    <div class="unified-message-workbench">
                        <aside class="unified-message-list" aria-label="${escapeHtml(translateUnifiedText('最近邮件'))}">
                            <div class="unified-message-list-head">
                                <strong>${escapeHtml(translateUnifiedText('最近邮件'))}</strong>
                                <span>${escapeHtml(String((preview.messages || []).length))}</span>
                            </div>
                            <div class="unified-message-list-scroll">
                                ${renderUnifiedMessageRows(preview.messages || [])}
                            </div>
                        </aside>
                        <section class="unified-message-detail-pane" aria-label="${escapeHtml(translateUnifiedText('邮件详情'))}">
                            ${renderUnifiedMessageDetail()}
                        </section>
                    </div>
                ` : ''}
            `;
        }

        function renderUnifiedMailboxCard(item) {
            const itemKind = String(item && item.kind || '').trim().toLowerCase();
            const kind = itemKind || 'account';
            const kindLabel = getUnifiedKindLabel(kind);
            const kindClass = getUnifiedKindClass(kind);
            const providerLabel = getUnifiedMailboxProviderDisplayLabel(item);
            const group = item.group || {};
            const groupName = group.name || getUnifiedDefaultGroupName(kind);
            const domain = String(item.domain || '').trim();
            const readCapabilityLabel = formatUnifiedReadCapabilityLabel(item.read_capability || '');
            const verificationCode = getUnifiedVerificationText(item);
            const latestText = getUnifiedLatestText(item);
            const statusClass = `status-${normalizeUnifiedStatus(item).replace(/[^a-z0-9_-]/g, '') || 'active'}`;
            const sourceId = Number(item.source_id || 0);
            const mailboxKey = getUnifiedMessageMailboxKey(kind, sourceId);
            const isSelected = mailboxKey && mailboxKey === unifiedMailboxState.preview.selectedKey;
            const groupId = group.id === null || group.id === undefined ? '' : Number(group.id || 0);
            const openTarget = getUnifiedOpenTarget(item);
            const openMode = String(openTarget.mode || kind || '').trim() || kind;
            const openSourceId = Number(openTarget.source_id || sourceId || 0);
            const openEmail = String(openTarget.email || item.email || '');
            const openGroupId = openTarget.group_id === null || openTarget.group_id === undefined
                ? groupId
                : Number(openTarget.group_id || 0);
            const copyVerifyAction = kind === 'temp'
                ? `copyVerificationInfo('${escapeJs(item.email)}', this, { source: 'temp' })`
                : `copyUnifiedVerification('${escapeJs(item.email)}', '${escapeJs(verificationCode)}', this)`;

            return `
                <article class="unified-mailbox-card ${isSelected ? 'selected' : ''}" data-kind="${escapeHtml(kind)}" data-source-id="${escapeHtml(String(sourceId))}" data-mailbox-key="${escapeHtml(mailboxKey)}" data-selected="${isSelected ? 'true' : 'false'}" data-email="${escapeHtml(item.email || '')}">
                    <div class="unified-card-main">
                        <div class="unified-card-topline">
                            <span class="unified-kind-badge ${escapeHtml(kindClass)}">${escapeHtml(kindLabel)}</span>
                            <span class="unified-status-badge ${escapeHtml(statusClass)}">${escapeHtml(formatUnifiedStatusLabel(item))}</span>
                            <span class="unified-provider-label">${escapeHtml(providerLabel)}</span>
                        </div>
                        <button class="unified-address-button" onclick="copyEmail('${escapeJs(item.email)}')" title="${escapeHtml(translateUnifiedText('复制邮箱地址'))}">
                            ${escapeHtml(item.email || '')}
                        </button>
                        <div class="unified-card-meta" aria-label="${escapeHtml(translateUnifiedText('邮箱属性'))}">
                            <span>${escapeHtml(groupName)}</span>
                            ${domain ? `<span>${escapeHtml(domain)}</span>` : ''}
                            <span>${escapeHtml(readCapabilityLabel)}</span>
                        </div>
                        <div class="unified-card-signals" aria-label="${escapeHtml(translateUnifiedText('邮箱来源摘要'))}">
                            <span><strong>${escapeHtml(translateUnifiedText('Provider'))}</strong>${escapeHtml(providerLabel)}</span>
                            <span><strong>${escapeHtml(translateUnifiedText('读取方式'))}</strong>${escapeHtml(readCapabilityLabel)}</span>
                            <span><strong>${escapeHtml(translateUnifiedText('来源'))}</strong>${escapeHtml(item.source || kind)}</span>
                        </div>
                        ${renderUnifiedActionSummary(item)}
                        <div class="unified-latest" title="${escapeHtml(latestText)}">${escapeHtml(latestText)}</div>
                        <div class="tag-list unified-labels">${renderUnifiedLabels(item)}</div>
                    </div>
                    <div class="unified-card-side">
                        <button class="code-button ${verificationCode ? '' : 'empty'}" onclick="${copyVerifyAction}" title="${escapeHtml(translateUnifiedText('复制验证码'))}">
                            ${escapeHtml(verificationCode || translateUnifiedText('暂无验证码'))}
                        </button>
                        <div class="unified-card-actions">
                            <button class="btn-inline primary" onclick="openUnifiedMessagePreviewFromCard('${escapeJs(kind)}', ${sourceId})">${escapeHtml(translateUnifiedText('预览邮件'))}</button>
                            <button class="btn-inline ghost" onclick="openUnifiedMailbox(${openSourceId}, '${escapeJs(openMode)}', '${escapeJs(openEmail)}', '${escapeJs(String(openGroupId))}')">${escapeHtml(translateUnifiedText('打开原页面'))}</button>
                            <button class="btn-inline ghost" onclick="copyEmail('${escapeJs(item.email)}')">${escapeHtml(translateUnifiedText('复制'))}</button>
                        </div>
                    </div>
                </article>
            `;
        }

        function renderUnifiedMailboxList(items) {
            const list = document.getElementById('unifiedMailboxList');
            const normalizedItems = Array.isArray(items) ? items : [];
            unifiedMailboxState.items = normalizedItems;
            if (!list) return;
            if (normalizedItems.length === 0) {
                list.innerHTML = `
                    <div class="ui-empty unified-state-block">
                        <div class="ui-empty-title">${escapeHtml(translateUnifiedText('还没有邮箱'))}</div>
                        <div class="ui-empty-desc">${escapeHtml(translateUnifiedText('导入 Outlook/IMAP 账号，或创建临时邮箱后，这里会出现统一目录。'))}</div>
                        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;">
                            <button type="button" class="btn btn-primary" onclick="showAddAccountModal()">${escapeHtml(translateUnifiedText('添加账号'))}</button>
                            <button type="button" class="btn btn-outline" onclick="navigate('temp-emails')">${escapeHtml(translateUnifiedText('创建临时邮箱'))}</button>
                        </div>
                    </div>
                `;
                resetUnifiedMessagePreview();
                return;
            }
            list.innerHTML = normalizedItems.map(renderUnifiedMailboxCard).join('');
            if (unifiedMailboxState.preview.selectedKey) {
                const stillVisible = normalizedItems.some(item => getUnifiedMessageMailboxKey(item) === unifiedMailboxState.preview.selectedKey);
                if (!stillVisible && !unifiedMailboxState.preview.loading) {
                    resetUnifiedMessagePreview();
                }
            }
        }

        function renderUnifiedPagination(pagination = {}) {
            const container = document.getElementById('unifiedMailboxPagination');
            if (!container) return;
            unifiedMailboxState.pagination = pagination;
            const page = Number(pagination.page || 1);
            const totalPages = Number(pagination.total_pages || 0);
            const totalCount = Number(pagination.total_count || 0);
            if (totalPages <= 1) {
                container.innerHTML = '';
                container.style.display = 'none';
                return;
            }
            container.style.display = 'flex';
            container.innerHTML = `
                <button class="page-btn page-btn-prev" onclick="goToUnifiedMailboxPage(${page - 1})" ${page <= 1 ? 'disabled' : ''}>‹</button>
                <span class="page-info">${page} / ${totalPages} ${escapeHtml(translateUnifiedText('页'))} · ${escapeHtml(formatUnifiedMailboxCount(totalCount, '个邮箱', 'mailbox'))}</span>
                <button class="page-btn page-btn-next" onclick="goToUnifiedMailboxPage(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>›</button>
            `;
        }

