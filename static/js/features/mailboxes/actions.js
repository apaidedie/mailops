// split from mailboxes.js → actions.js
        function getUnifiedSetupGuideActionLabel(action = {}) {
            return translateUnifiedText(action.label || '执行');
        }

        function getUnifiedCommandActionCount(contract = {}, facets = {}) {
            const actionDefinitions = Array.isArray(contract.action_definitions) ? contract.action_definitions : [];
            if (actionDefinitions.length > 0) {
                return actionDefinitions.length;
            }
            return Array.isArray(facets.actions)
                ? facets.actions.filter(item => normalizeUnifiedFacetCount(item && item.count) > 0).length
                : 0;
        }

        function normalizeUnifiedProviderCapabilityActions(values = []) {
            return normalizeUnifiedProviderCapabilityKeys(values).slice(0, 8);
        }

        function getUnifiedOpenTarget(item) {
            const actionContract = item.action_contract || {};
            const internalActions = actionContract.internal || {};
            return internalActions.open_mailbox || {};
        }

        function openUnifiedMessagePreview(kind, sourceId) {
            // Soft re-open when the same mailbox messages are warm; refresh button still forces.
            return loadUnifiedMailboxMessages(kind, sourceId, { force: false });
        }

        function openUnifiedMessagePreviewFromCard(kind, sourceId) {
            return openUnifiedMessagePreview(kind, sourceId);
        }

        async function copyUnifiedPreviewValue(value, successText = '内容已复制到剪贴板') {
            const text = String(value || '').trim();
            if (!text) return false;
            try {
                if (typeof copyTextToClipboard === 'function') {
                    const ok = await copyTextToClipboard(text);
                    if (!ok) throw new Error('copy_failed');
                } else if (typeof copyToClipboard === 'function') {
                    await copyToClipboard(text);
                } else if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(text);
                } else {
                    throw new Error('copy_unavailable');
                }
                showToast(translateUnifiedText(successText), 'success');
                return true;
            } catch (error) {
                showToast(translateUnifiedText('复制失败，请手动复制'), 'error');
                return false;
            }
        }

        function bindUnifiedMailboxControls() {
            const search = document.getElementById('unifiedMailboxSearch');
            const kind = document.getElementById('unifiedMailboxKindFilter');
            const status = document.getElementById('unifiedMailboxStatusFilter');
            const readCapability = document.getElementById('unifiedMailboxReadCapabilityFilter');
            const action = document.getElementById('unifiedMailboxActionFilter');
            const provider = document.getElementById('unifiedMailboxProviderFilter');
            const sort = document.getElementById('unifiedMailboxSortFilter');
            const workspaceViewSwitch = document.getElementById('unifiedWorkspaceViewSwitch');
            const quickViews = document.getElementById('unifiedMailboxQuickViews');
            const commandCenter = document.getElementById('unifiedMailboxCommandCenter');
            const setupGuide = document.getElementById('unifiedMailboxSetupGuide');
            const providerContext = document.getElementById('unifiedMailboxProviderContext');
            const providerCapabilityMatrix = document.getElementById('unifiedProviderCapabilityMatrix');
            const operationalLens = document.getElementById('unifiedMailboxOperationalLens');
            renderUnifiedWorkspaceViewSwitch();
            if (search && !search.dataset.boundUnifiedMailbox) {
                search.dataset.boundUnifiedMailbox = '1';
                search.addEventListener('input', debounceUnifiedMailboxSearch);
            }
            [kind, status, readCapability, action, provider, sort].forEach(element => {
                if (!element || element.dataset.boundUnifiedMailbox) return;
                element.dataset.boundUnifiedMailbox = '1';
                element.addEventListener('change', () => {
                    unifiedMailboxState.page = 1;
                    syncUnifiedQuickViews();
                    loadUnifiedMailboxes(true);
                });
            });
            if (workspaceViewSwitch && !workspaceViewSwitch.dataset.boundUnifiedWorkspaceView) {
                workspaceViewSwitch.dataset.boundUnifiedWorkspaceView = '1';
                workspaceViewSwitch.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('[data-unified-workspace-view]') : null;
                    if (!button || !workspaceViewSwitch.contains(button)) return;
                    setUnifiedWorkspaceView(button.dataset.unifiedWorkspaceView || 'inbox');
                });
            }
            if (quickViews && !quickViews.dataset.boundUnifiedQuickViews) {
                quickViews.dataset.boundUnifiedQuickViews = '1';
                quickViews.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('.unified-quick-view[data-unified-quick-view]') : null;
                    if (!button || !quickViews.contains(button)) return;
                    applyUnifiedQuickView(button.dataset.unifiedQuickView || 'all');
                });
            }
            if (commandCenter && !commandCenter.dataset.boundUnifiedCommandViews) {
                commandCenter.dataset.boundUnifiedCommandViews = '1';
                commandCenter.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('.unified-command-view[data-unified-command-view]') : null;
                    if (!button || !commandCenter.contains(button)) return;
                    applyUnifiedQuickView(button.dataset.unifiedCommandView || 'all');
                });
            }
            if (setupGuide && !setupGuide.dataset.boundUnifiedSetupGuide) {
                setupGuide.dataset.boundUnifiedSetupGuide = '1';
                setupGuide.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('.unified-setup-action[data-unified-setup-action]') : null;
                    if (!button || !setupGuide.contains(button)) return;
                    const setupAction = String(button.dataset.unifiedSetupAction || '').trim();
                    if (setupAction === 'refresh') {
                        loadUnifiedMailboxes(true);
                        return;
                    }
                    if (setupAction === 'quick-view') {
                        applyUnifiedQuickView(button.dataset.unifiedSetupView || 'all');
                        return;
                    }
                    if (setupAction === 'focus-provider-context' && providerContext) {
                        providerContext.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                        return;
                    }
                    if (setupAction === 'open-account-view' && typeof switchMailboxViewMode === 'function') {
                        switchMailboxViewMode('standard');
                        return;
                    }
                    if (setupAction === 'open-temp-workspace' && typeof navigate === 'function') {
                        navigate('temp-emails');
                        return;
                    }
                    if (setupAction === 'open-api-security' && typeof navigate === 'function') {
                        navigate('settings');
                        if (typeof switchSettingsTab === 'function') {
                            switchSettingsTab('api-security');
                        }
                    }
                });
            }
            if (operationalLens && !operationalLens.dataset.boundUnifiedOperationalLens) {
                operationalLens.dataset.boundUnifiedOperationalLens = '1';
                operationalLens.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('.unified-lens-action[data-unified-lens-action]') : null;
                    if (!button || !operationalLens.contains(button)) return;
                    const lensAction = String(button.dataset.unifiedLensAction || '').trim();
                    if (lensAction === 'refresh') {
                        loadUnifiedMailboxes(true);
                        return;
                    }
                    if (lensAction === 'quick-view') {
                        applyUnifiedQuickView(button.dataset.unifiedLensView || 'all');
                        return;
                    }
                    if (lensAction === 'focus-provider-context' && providerContext) {
                        providerContext.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    }
                });
            }
            if (providerContext && !providerContext.dataset.boundUnifiedProviderFacets) {
                providerContext.dataset.boundUnifiedProviderFacets = '1';
                providerContext.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('.unified-provider-facet') : null;
                    if (!button || !providerContext.contains(button)) return;
                    setUnifiedProviderFilter(button.dataset.provider || 'all');
                });
            }
            if (providerCapabilityMatrix && !providerCapabilityMatrix.dataset.boundUnifiedProviderCapabilityMatrix) {
                providerCapabilityMatrix.dataset.boundUnifiedProviderCapabilityMatrix = '1';
                providerCapabilityMatrix.addEventListener('click', event => {
                    const target = event.target && typeof event.target.closest === 'function' ? event.target : null;
                    const button = target ? target.closest('.unified-provider-capability-filter') : null;
                    if (!button || !providerCapabilityMatrix.contains(button)) return;
                    setUnifiedProviderFilter(button.dataset.provider || 'all');
                });
            }
        }

        async function openUnifiedMailbox(sourceId, kind, email, groupId) {
            const normalizedKind = String(kind || '').toLowerCase();
            if (normalizedKind === 'temp' || normalizedKind === 'temp-emails') {
                navigate('temp-emails');
                if (typeof loadTempEmails === 'function') {
                    await loadTempEmails(true);
                }
                if (typeof selectTempEmail === 'function') {
                    selectTempEmail(email);
                }
                return;
            }

            switchMailboxViewMode('standard');
            const numericGroupId = Number(groupId || 0);
            if (numericGroupId && typeof selectGroup === 'function') {
                await selectGroup(numericGroupId);
            }
            if (typeof selectAccount === 'function') {
                selectAccount(email);
            }
        }

        async function copyUnifiedVerification(email, verificationCode, buttonElement) {
            const code = String(verificationCode || '').trim();
            if (code && typeof copyToClipboard === 'function') {
                await copyToClipboard(code);
                showToast(translateUnifiedText('验证码已复制'), 'success');
                return true;
            }
            return copyVerificationInfo(email, buttonElement);
        }

        window.addEventListener('ui-language-changed', () => {
            if (mailboxViewMode === 'unified') {
                renderUnifiedWorkspaceViewSwitch();
                // Soft re-paint warm directory/preview labels without forcing a network GET.
                if (unifiedMailboxState.directoryPayload) {
                    applyUnifiedMailboxDirectoryPayload(unifiedMailboxState.directoryPayload);
                }
                renderUnifiedMessagePreview();
            }
        });
