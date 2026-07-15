// split from mailboxes.js → quickview.js
        function normalizeUnifiedQuickViewFilterValue(value, fallback = 'all') {
            const normalized = String(value === null || value === undefined ? fallback : value).trim().toLowerCase();
            return normalized || fallback;
        }

        function normalizeUnifiedQuickViewFilters(filters = {}) {
            const source = filters && typeof filters === 'object' ? filters : {};
            return {
                kind: normalizeUnifiedQuickViewFilterValue(source.kind, UNIFIED_QUICK_VIEW_DEFAULT_FILTERS.kind),
                status: normalizeUnifiedQuickViewFilterValue(source.status, UNIFIED_QUICK_VIEW_DEFAULT_FILTERS.status),
                readCapability: normalizeUnifiedQuickViewFilterValue(source.readCapability || source.read_capability, UNIFIED_QUICK_VIEW_DEFAULT_FILTERS.readCapability),
                action: normalizeUnifiedQuickViewFilterValue(source.action, UNIFIED_QUICK_VIEW_DEFAULT_FILTERS.action),
                provider: normalizeUnifiedQuickViewFilterValue(source.provider, UNIFIED_QUICK_VIEW_DEFAULT_FILTERS.provider),
                sort: normalizeUnifiedQuickViewFilterValue(source.sort, UNIFIED_QUICK_VIEW_DEFAULT_FILTERS.sort),
                search: String(source.search || '').trim()
            };
        }

        function normalizeUnifiedQuickViewPreset(preset = {}) {
            const source = preset && typeof preset === 'object' ? preset : {};
            const key = String(source.key || '').trim().toLowerCase();
            if (!key) return null;
            return {
                key,
                label: String(source.label || source.label_en || key).trim() || key,
                detail: String(source.description || source.detail || source.description_en || '').trim(),
                filters: normalizeUnifiedQuickViewFilters(source.filters || {})
            };
        }

        function getUnifiedQuickViewPresets(contract = unifiedMailboxState.contract || {}) {
            const sourceContract = contract && typeof contract === 'object' ? contract : {};
            const contractPresets = Array.isArray(sourceContract.quick_view_presets) ? sourceContract.quick_view_presets : [];
            const sourcePresets = contractPresets.length > 0 ? contractPresets : UNIFIED_QUICK_VIEW_PRESETS;
            return sourcePresets.map(normalizeUnifiedQuickViewPreset).filter(Boolean);
        }

        function getUnifiedQuickViewPreset(key, contract = unifiedMailboxState.contract || {}) {
            const normalizedKey = String(key || '').trim().toLowerCase();
            return getUnifiedQuickViewPresets(contract).find(preset => preset.key === normalizedKey) || null;
        }

        function isUnifiedQuickViewValueAllowed(contract = {}, filterName = '', value = '') {
            const normalizedValue = String(value || '').trim().toLowerCase();
            if (!normalizedValue || normalizedValue === 'all') return true;
            const filters = contract && typeof contract === 'object' ? contract.filters || {} : {};
            const allowedValues = filters[filterName];
            if (!Array.isArray(allowedValues) || allowedValues.length === 0) return true;
            return allowedValues.map(item => String(item || '').trim().toLowerCase()).includes(normalizedValue);
        }

        function isUnifiedQuickViewPresetAvailable(preset = {}, contract = unifiedMailboxState.contract || {}) {
            const filters = normalizeUnifiedQuickViewFilters(preset.filters || {});
            return isUnifiedQuickViewValueAllowed(contract, 'kind', filters.kind)
                && isUnifiedQuickViewValueAllowed(contract, 'status', filters.status)
                && isUnifiedQuickViewValueAllowed(contract, 'read_capability', filters.readCapability)
                && isUnifiedQuickViewValueAllowed(contract, 'action', filters.action)
                && isUnifiedQuickViewValueAllowed(contract, 'sort', filters.sort);
        }

        function getUnifiedQuickViewKey(filters = unifiedMailboxState.filters, contract = unifiedMailboxState.contract || {}) {
            const normalizedFilters = normalizeUnifiedQuickViewFilters(filters);
            const preset = getUnifiedQuickViewPresets(contract).find(item => {
                const presetFilters = normalizeUnifiedQuickViewFilters(item.filters || {});
                return UNIFIED_QUICK_VIEW_FILTER_KEYS.every(key => normalizedFilters[key] === presetFilters[key]);
            });
            return preset ? preset.key : 'custom';
        }

        function setUnifiedQuickViewDomFilters(filters = {}) {
            const normalizedFilters = normalizeUnifiedQuickViewFilters(filters);
            setUnifiedFilterControlValue('unifiedMailboxKindFilter', normalizedFilters.kind);
            setUnifiedFilterControlValue('unifiedMailboxStatusFilter', normalizedFilters.status);
            setUnifiedFilterControlValue('unifiedMailboxReadCapabilityFilter', normalizedFilters.readCapability);
            setUnifiedFilterControlValue('unifiedMailboxActionFilter', normalizedFilters.action);
            setUnifiedFilterControlValue('unifiedMailboxProviderFilter', normalizedFilters.provider);
            setUnifiedFilterControlValue('unifiedMailboxSortFilter', normalizedFilters.sort);
            setUnifiedFilterControlValue('unifiedMailboxSearch', normalizedFilters.search);
        }

        function renderUnifiedQuickViews(filters = unifiedMailboxState.filters, contract = unifiedMailboxState.contract || {}) {
            const container = document.getElementById('unifiedMailboxQuickViews');
            if (!container) return;
            const availablePresets = getUnifiedQuickViewPresets(contract).filter(preset => isUnifiedQuickViewPresetAvailable(preset, contract));
            if (!availablePresets.length) {
                container.innerHTML = '';
                container.hidden = true;
                return;
            }
            container.hidden = false;
            const activeKey = getUnifiedQuickViewKey(filters, contract);
            const customActive = activeKey === 'custom';
            container.innerHTML = `
                ${availablePresets.map(preset => {
                    const active = preset.key === activeKey;
                    return `
                        <button type="button" class="unified-quick-view ${active ? 'active' : ''}" data-unified-quick-view="${escapeHtml(preset.key)}" aria-pressed="${active ? 'true' : 'false'}">
                            <span class="unified-quick-view-label">${escapeHtml(translateUnifiedText(preset.label))}</span>
                            <span class="unified-quick-view-detail">${escapeHtml(translateUnifiedText(preset.detail))}</span>
                        </button>
                    `;
                }).join('')}
                <span class="unified-quick-view custom ${customActive ? 'active' : ''}" aria-hidden="${customActive ? 'false' : 'true'}">
                    <span class="unified-quick-view-label">${escapeHtml(translateUnifiedText('自定义筛选'))}</span>
                    <span class="unified-quick-view-detail">${escapeHtml(translateUnifiedText('手动组合'))}</span>
                </span>
            `;
        }

        function syncUnifiedQuickViews() {
            syncUnifiedFiltersFromDom();
            renderUnifiedQuickViews(unifiedMailboxState.filters, unifiedMailboxState.contract || {});
        }

        function applyUnifiedQuickView(key = 'all') {
            const preset = getUnifiedQuickViewPreset(key);
            if (!preset) return;
            unifiedMailboxState.filters = normalizeUnifiedQuickViewFilters(preset.filters || {});
            setUnifiedQuickViewDomFilters(unifiedMailboxState.filters);
            unifiedMailboxState.page = 1;
            renderUnifiedQuickViews(unifiedMailboxState.filters, unifiedMailboxState.contract || {});
            loadUnifiedMailboxes(true);
        }

        function renderUnifiedCommandQuickViews(filters = unifiedMailboxState.filters, contract = unifiedMailboxState.contract || {}) {
            const presets = getUnifiedQuickViewPresets(contract).filter(preset => isUnifiedQuickViewPresetAvailable(preset, contract));
            if (!presets.length) return '';
            const activeKey = getUnifiedQuickViewKey(filters, contract);
            const customActive = activeKey === 'custom';
            return `
                <div class="unified-command-views" aria-label="${escapeHtml(translateUnifiedText('推荐视图'))}">
                    <div class="unified-command-views-head">
                        <span>${escapeHtml(translateUnifiedText('推荐视图'))}</span>
                        <strong>${escapeHtml(translateUnifiedText(customActive ? '自定义筛选' : '当前视图'))}</strong>
                    </div>
                    <div class="unified-command-view-rail">
                        ${presets.map(preset => {
                            const active = preset.key === activeKey;
                            return `
                                <button type="button" class="unified-command-view ${active ? 'active' : ''}" data-unified-command-view="${escapeHtml(preset.key)}" aria-pressed="${active ? 'true' : 'false'}">
                                    <span>${escapeHtml(translateUnifiedText(preset.label))}</span>
                                    <small>${escapeHtml(translateUnifiedText(preset.detail))}</small>
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

