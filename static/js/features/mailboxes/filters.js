// split from mailboxes.js → filters.js
        function getUnifiedFilterValue(id, fallback) {
            const element = document.getElementById(id);
            return element && typeof element.value === 'string' ? element.value : fallback;
        }

        function setUnifiedFilterControlValue(id, value) {
            const element = document.getElementById(id);
            if (!element) return;
            element.value = value;
        }

        function normalizeUnifiedFacetCount(value) {
            const count = Number(value || 0);
            return Number.isFinite(count) && count > 0 ? count : 0;
        }

        function syncUnifiedFiltersFromDom() {
            unifiedMailboxState.filters = {
                kind: getUnifiedFilterValue('unifiedMailboxKindFilter', 'all') || 'all',
                status: getUnifiedFilterValue('unifiedMailboxStatusFilter', 'all') || 'all',
                readCapability: getUnifiedFilterValue('unifiedMailboxReadCapabilityFilter', 'all') || 'all',
                action: getUnifiedFilterValue('unifiedMailboxActionFilter', 'all') || 'all',
                provider: getUnifiedFilterValue('unifiedMailboxProviderFilter', 'all') || 'all',
                sort: getUnifiedFilterValue('unifiedMailboxSortFilter', 'updated_desc') || 'updated_desc',
                search: getUnifiedFilterValue('unifiedMailboxSearch', '').trim()
            };
        }

        function normalizeUnifiedProviderFacets(facets = []) {
            // Collapse bridge aliases (custom_domain_temp_mail / legacy_bridge) and sum counts.
            const deduped = dedupeUnifiedTempProviderRows(
                (Array.isArray(facets) ? facets : []).map(item => ({
                    ...(item && typeof item === 'object' ? item : {}),
                    provider: item && item.provider,
                    kind: item && item.kind,
                    label: item && (item.label || item.provider_label),
                    mailbox_count: item && item.count,
                    count: item && item.count,
                }))
            );
            return deduped.map(item => ({
                provider: String(item.provider || '').trim().toLowerCase(),
                kind: String(item.kind || '').trim().toLowerCase(),
                label: String(item.label || item.provider_label || item.provider || '').trim(),
                count: normalizeUnifiedFacetCount(
                    item.count !== undefined && item.count !== null
                        ? item.count
                        : item.mailbox_count
                ),
            })).filter(item => item.provider);
        }

        function getUnifiedKindDefinition(kind, contract = unifiedMailboxState.contract || {}) {
            const normalizedKind = String(kind || '').trim().toLowerCase();
            const definitions = Array.isArray(contract.kind_definitions) ? contract.kind_definitions : [];
            return definitions.find(item => String(item && item.kind || '').trim().toLowerCase() === normalizedKind) || {};
        }

        function getUnifiedKindLabel(kind, contract = unifiedMailboxState.contract || {}) {
            const normalizedKind = String(kind || '').trim().toLowerCase();
            const fallbackLabels = {
                account: '普通账号',
                temp: '临时邮箱'
            };
            const definition = getUnifiedKindDefinition(normalizedKind, contract);
            return translateUnifiedText(definition.label || definition.label_en || fallbackLabels[normalizedKind] || normalizedKind || '邮箱');
        }

        function getUnifiedKindClass(kind) {
            return String(kind || 'account').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '') || 'account';
        }

        function renderUnifiedKindOptions(contract = {}, selectedKind = 'all', facets = []) {
            const select = document.getElementById('unifiedMailboxKindFilter');
            if (!select) return;
            const filters = contract.filters || {};
            const allowedKinds = Array.isArray(filters.kind) && filters.kind.length > 0
                ? filters.kind
                : ['all'];
            const definitions = Array.isArray(contract.kind_definitions) ? contract.kind_definitions : [];
            const definitionByKind = definitions.reduce((acc, item) => {
                const kind = String(item && item.kind || '').trim().toLowerCase();
                if (kind) acc[kind] = item;
                return acc;
            }, {});
            const countsByValue = buildUnifiedFacetCountMap(facets, 'kind');
            const selected = String(selectedKind || 'all').trim().toLowerCase() || 'all';
            const options = allowedKinds.map(kindValue => {
                const kind = String(kindValue || '').trim().toLowerCase();
                const definition = definitionByKind[kind] || {};
                const label = kind === 'all'
                    ? '全部来源'
                    : (definition.label || definition.label_en || kind);
                const countValue = kind !== 'all' && countsByValue.has(kind) ? normalizeUnifiedFacetCount(countsByValue.get(kind)) : null;
                const translatedLabel = translateUnifiedText(label);
                const displayLabel = countValue === null ? translatedLabel : `${translatedLabel} (${countValue})`;
                return `<option value="${escapeHtml(kind)}">${escapeHtml(displayLabel)}</option>`;
            });
            const allowedValues = allowedKinds.map(item => String(item || '').trim().toLowerCase());
            if (!allowedValues.includes(selected)) {
                options.push(`<option value="${escapeHtml(selected)}">${escapeHtml(translateUnifiedText('当前筛选'))}: ${escapeHtml(selected)}</option>`);
            }
            select.innerHTML = options.join('');
            select.value = selected;
        }

        function renderUnifiedDefinitionOptions({ selectId, selectedValue = 'all', definitions = [], valueKey, allLabel = '', fallbackDefinitions = [], includeAll = true, countsByValue = null }) {
            const select = document.getElementById(selectId);
            if (!select) return;
            const selected = String(selectedValue || 'all').trim().toLowerCase() || 'all';
            const sourceDefinitions = Array.isArray(definitions) && definitions.length > 0 ? definitions : fallbackDefinitions;
            const options = includeAll ? [`<option value="all">${escapeHtml(translateUnifiedText(allLabel))}</option>`] : [];
            const allowedValues = includeAll ? ['all'] : [];
            sourceDefinitions.forEach(item => {
                const value = String(item && item[valueKey] || '').trim().toLowerCase();
                if (!value) return;
                allowedValues.push(value);
                const label = String(item.label || item.label_en || value).trim() || value;
                const countValue = countsByValue && countsByValue.has(value) ? normalizeUnifiedFacetCount(countsByValue.get(value)) : null;
                const translatedLabel = translateUnifiedText(label);
                const displayLabel = countValue === null ? translatedLabel : `${translatedLabel} (${countValue})`;
                options.push(`<option value="${escapeHtml(value)}">${escapeHtml(displayLabel)}</option>`);
            });
            if (!allowedValues.includes(selected)) {
                options.push(`<option value="${escapeHtml(selected)}">${escapeHtml(translateUnifiedText('当前筛选'))}: ${escapeHtml(selected)}</option>`);
            }
            select.innerHTML = options.join('');
            select.value = selected;
        }

        function renderUnifiedStatusOptions(contract = {}, selectedStatus = 'all', facets = []) {
            renderUnifiedDefinitionOptions({
                selectId: 'unifiedMailboxStatusFilter',
                selectedValue: selectedStatus,
                definitions: contract.status_definitions,
                valueKey: 'status',
                allLabel: '全部状态',
                countsByValue: buildUnifiedFacetCountMap(facets, 'status')
            });
        }

        function buildUnifiedFacetCountMap(facets = [], valueKey = '') {
            const counts = new Map();
            if (!Array.isArray(facets)) return counts;
            facets.forEach(item => {
                const value = String(item && item[valueKey] || '').trim().toLowerCase();
                if (!value) return;
                counts.set(value, normalizeUnifiedFacetCount(item.count));
            });
            return counts;
        }

        function getUnifiedSetupGuideStatusLabel(status = '') {
            const labels = {
                loading: '读取中',
                ready: '已就绪',
                warning: '待处理',
                action: '需配置',
                unknown: '待确认',
                error: '不可用'
            };
            const normalized = String(status || '').trim().toLowerCase().replace(/_/g, '-');
            return translateUnifiedText(labels[normalized] || labels.unknown);
        }

        function getUnifiedOperationalActiveFilterCount(filters = {}) {
            const normalized = normalizeUnifiedQuickViewFilters(filters || {});
            return [
                normalized.kind !== 'all',
                normalized.status !== 'all',
                normalized.readCapability !== 'all',
                normalized.action !== 'all',
                normalized.provider !== 'all',
                normalized.sort !== 'updated_desc',
                Boolean(normalized.search)
            ].filter(Boolean).length;
        }

        function getUnifiedProviderContextStatusLabel(status) {
            if (status === 'error') return translateUnifiedText('配置异常');
            if (status === 'warning') return translateUnifiedText('需要配置');
            return translateUnifiedText('策略正常');
        }

        function formatUnifiedProviderConfigFileStatus(configFile = {}) {
            if (!configFile || typeof configFile !== 'object') {
                return translateUnifiedText('无配置文件');
            }
            if (configFile.error_code || configFile.error) {
                return getUnifiedProviderContextText(configFile.error_code || configFile.error);
            }
            if (configFile.loaded) {
                return translateUnifiedText('已加载');
            }
            if (configFile.enabled) {
                return translateUnifiedText('未加载');
            }
            return translateUnifiedText('无配置文件');
        }

        function renderUnifiedProviderFacetChips(providerFacets = [], selectedProvider = 'all') {
            const facets = normalizeUnifiedProviderFacets(providerFacets);
            const rawSelected = String(selectedProvider || 'all').trim().toLowerCase() || 'all';
            const selected = rawSelected === 'all'
                ? 'all'
                : (canonicalizeUnifiedTempProviderKey(rawSelected) || rawSelected);
            if (!facets.length) {
                return `<div class="unified-provider-facets empty">${escapeHtml(translateUnifiedText('暂无来源分布'))}</div>`;
            }
            const chips = [
                {
                    provider: 'all',
                    label: translateUnifiedText('全部 Provider'),
                    kindLabel: translateUnifiedText('全部来源'),
                    count: facets.reduce((sum, item) => sum + normalizeUnifiedFacetCount(item && item.count), 0)
                },
                ...facets.map(item => {
                    const provider = item.provider;
                    const kind = String(item.kind || '').trim().toLowerCase();
                    return {
                        provider,
                        label: String(item.label || provider).trim() || provider,
                        kindLabel: kind ? getUnifiedKindLabel(kind) : translateUnifiedText('邮箱'),
                        count: normalizeUnifiedFacetCount(item.count)
                    };
                }).filter(item => item.provider)
            ];
            return `
                <div class="unified-provider-facets" aria-label="${escapeHtml(translateUnifiedText('来源分布'))}">
                    ${chips.map(item => {
                        const activeClass = item.provider === selected ? 'active' : '';
                        return `
                            <button type="button" class="unified-provider-facet ${activeClass}" data-provider="${escapeHtml(item.provider)}" aria-pressed="${item.provider === selected ? 'true' : 'false'}">
                                <span class="unified-provider-facet-label">${escapeHtml(item.label)}</span>
                                <span class="unified-provider-facet-meta">${escapeHtml(item.kindLabel)} · ${normalizeUnifiedFacetCount(item.count)}</span>
                            </button>
                        `;
                    }).join('')}
                </div>
            `;
        }

        function getUnifiedProviderReadinessStatusLabel(status = '') {
            const labels = {
                ready: '已就绪',
                needs_config: '缺配置',
                degraded: '配置异常',
                inventory_only: '仅库存',
                inactive: '未启用',
                unknown: '未知'
            };
            const normalized = String(status || '').trim().toLowerCase().replace(/-/g, '_');
            return translateUnifiedText(labels[normalized] || normalized || '未知');
        }

        function normalizeUnifiedStatus(item) {
            const poolStatus = String(item && item.pool_status || '').trim().toLowerCase();
            const status = String(item && item.status || '').trim().toLowerCase();
            return poolStatus || status || 'active';
        }

        function formatUnifiedStatusLabel(item) {
            const status = normalizeUnifiedStatus(item);
            const definitions = Array.isArray(unifiedMailboxState.contract.status_definitions)
                ? unifiedMailboxState.contract.status_definitions
                : [];
            const definition = definitions.find(item => String(item && item.status || '').trim().toLowerCase() === status) || {};
            return translateUnifiedText(definition.label || definition.label_en || status);
        }

        function getUnifiedActionDefinitions(item) {
            const contractDefinitions = Array.isArray(unifiedMailboxState.contract.action_definitions)
                ? unifiedMailboxState.contract.action_definitions
                : [];
            if (contractDefinitions.length > 0) return contractDefinitions;
            const actions = item && item.actions && typeof item.actions === 'object' ? item.actions : {};
            return Object.keys(actions).map(action => ({ action, label: action, label_en: action }));
        }

        function normalizeUnifiedPreviewKind(kind) {
            const normalized = String(kind || '').trim().toLowerCase();
            return normalized === 'temp-emails' ? 'temp' : normalized;
        }

        function setUnifiedProviderFilter(providerName = 'all') {
            const raw = String(providerName || 'all').trim().toLowerCase() || 'all';
            const provider = raw === 'all'
                ? 'all'
                : (canonicalizeUnifiedTempProviderKey(raw) || raw);
            const select = document.getElementById('unifiedMailboxProviderFilter');
            if (select) {
                select.value = provider;
            }
            unifiedMailboxState.filters.provider = provider;
            unifiedMailboxState.page = 1;
            renderUnifiedQuickViews(unifiedMailboxState.filters, unifiedMailboxState.contract || {});
            loadUnifiedMailboxes(true);
        }

