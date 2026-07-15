// split from mailboxes.js → data.js
        function getUnifiedMailboxRequestSignature(filters = unifiedMailboxState.filters, page = unifiedMailboxState.page, pageSize = unifiedMailboxState.pageSize) {
            const normalizedFilters = normalizeUnifiedQuickViewFilters(filters);
            return JSON.stringify({
                filters: normalizedFilters,
                page: Number(page || 1),
                pageSize: Number(pageSize || 50)
            });
        }

        async function loadUnifiedMailboxMessages(kind, sourceId, options = {}) {
            const normalizedKind = normalizeUnifiedPreviewKind(kind);
            const numericSourceId = Number(sourceId || 0);
            if (!normalizedKind || !numericSourceId) return false;
            const preview = unifiedMailboxState.preview;
            const forceRefresh = Boolean(options.force);
            const selectedKey = getUnifiedMessageMailboxKey(normalizedKind, numericSourceId);
            const existingMailbox = getUnifiedPreviewMailboxItem(normalizedKind, numericSourceId) || preview.mailbox || {};
            const selectedChanged = preview.selectedKey !== selectedKey;
            const folder = String(options.folder || preview.folder || 'inbox').trim().toLowerCase() || 'inbox';
            const skip = Number(options.skip === undefined ? 0 : options.skip) || 0;
            const top = Number(options.top === undefined ? preview.top || 20 : options.top) || 20;
            const messagesSignature = `${selectedKey}|${folder}|${skip}|${top}`;

            preview.selectedKey = selectedKey;
            preview.selectedKind = normalizedKind;
            preview.selectedSourceId = numericSourceId;
            preview.mailbox = existingMailbox;
            preview.error = '';
            preview.folder = folder;
            preview.skip = skip;
            preview.top = top;

            // Soft re-open: same mailbox/folder page already loaded — re-render without network.
            // Paint only while still on the unified mailbox surface.
            if (
                !forceRefresh
                && !selectedChanged
                && preview.messagesSignature === messagesSignature
                && Array.isArray(preview.messages)
                && !preview.loading
                && !preview.error
            ) {
                if (typeof isCurrentUnifiedMailboxSurface === 'function' ? isCurrentUnifiedMailboxSurface() : true) {
                    renderUnifiedMailboxList(unifiedMailboxState.items || []);
                    renderUnifiedMessagePreview();
                }
                return true;
            }

            // Soft joins any in-flight for the same signature. Force joins only force
            // in-flight; force supersedes soft so refresh always starts a true network GET.
            if (
                preview.messagesLoadPromise
                && preview.messagesLoadSignature === messagesSignature
            ) {
                if (!forceRefresh || preview.messagesLoadForce) {
                    return preview.messagesLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; requestSeq blocks stale apply.
                preview.messagesLoadPromise = null;
                preview.messagesLoadSignature = '';
                preview.messagesLoadForce = false;
            }

            if (selectedChanged || forceRefresh) {
                preview.messages = [];
                preview.selectedMessageId = '';
                preview.message = null;
                preview.verification = null;
                preview.detailError = '';
                preview.verificationError = '';
                preview.messagesSignature = '';
                preview.detailSignature = '';
                preview.verificationSignature = '';
            }
            preview.loading = true;
            const seq = ++preview.requestSeq;
            const paintUnifiedPreview = () => (
                typeof isCurrentUnifiedMailboxSurface === 'function'
                    ? isCurrentUnifiedMailboxSurface()
                    : true
            );
            if (paintUnifiedPreview()) {
                renderUnifiedMailboxList(unifiedMailboxState.items || []);
                renderUnifiedMessagePreview();
            }
            const params = new URLSearchParams({
                folder: preview.folder,
                skip: String(preview.skip),
                top: String(preview.top)
            });

            preview.messagesLoadForce = forceRefresh;
            const request = (async () => {
                try {
                    const response = await fetch(`${getUnifiedMessageEndpoint(normalizedKind, numericSourceId, 'messages')}?${params.toString()}`);
                    const data = await response.json();
                    if (seq !== preview.requestSeq || preview.messagesLoadPromise !== request) return false;
                    if (!response.ok || !data.success) {
                        preview.loading = false;
                        preview.error = getUnifiedPreviewErrorMessage(data, '邮件读取失败');
                        preview.messagesSignature = '';
                        if (paintUnifiedPreview()) {
                            renderUnifiedMessagePreview();
                            showToast(preview.error, 'error');
                        }
                        return false;
                    }
                    // Always warm preview soft state; paint only on unified surface.
                    preview.loading = false;
                    preview.mailbox = data.mailbox || existingMailbox;
                    preview.messages = Array.isArray(data.messages) ? data.messages : [];
                    preview.messagesSignature = messagesSignature;
                    const hasCurrentMessage = preview.messages.some(message => String(message.id || '') === preview.selectedMessageId);
                    preview.selectedMessageId = hasCurrentMessage ? preview.selectedMessageId : String((preview.messages[0] || {}).id || '');
                    preview.message = null;
                    preview.detailError = '';
                    preview.detailSignature = '';
                    if (paintUnifiedPreview()) {
                        renderUnifiedMailboxList(unifiedMailboxState.items || []);
                        renderUnifiedMessagePreview();
                    }
                    if (preview.selectedMessageId) {
                        await loadUnifiedMailboxMessageDetail(normalizedKind, numericSourceId, preview.selectedMessageId, { force: true });
                    }
                    return true;
                } catch (error) {
                    if (seq !== preview.requestSeq || preview.messagesLoadPromise !== request) return false;
                    preview.loading = false;
                    preview.error = translateUnifiedText('邮件读取失败');
                    preview.messagesSignature = '';
                    if (paintUnifiedPreview()) {
                        renderUnifiedMessagePreview();
                        showToast(preview.error, 'error');
                    }
                    return false;
                } finally {
                    if (preview.messagesLoadPromise === request) {
                        preview.messagesLoadPromise = null;
                        preview.messagesLoadSignature = '';
                        preview.messagesLoadForce = false;
                    }
                }
            })();

            preview.messagesLoadPromise = request;
            preview.messagesLoadSignature = messagesSignature;
            return request;
        }

        async function loadUnifiedMailboxMessageDetail(kind, sourceId, messageId, options = {}) {
            const normalizedKind = normalizeUnifiedPreviewKind(kind);
            const numericSourceId = Number(sourceId || 0);
            const normalizedMessageId = String(messageId || '').trim();
            const preview = unifiedMailboxState.preview;
            if (!normalizedKind || !numericSourceId || !normalizedMessageId) return false;
            const forceRefresh = Boolean(options && options.force);
            const selectedKey = getUnifiedMessageMailboxKey(normalizedKind, numericSourceId);
            const folder = String(preview.folder || 'inbox').trim().toLowerCase() || 'inbox';
            const detailSignature = `${selectedKey}|${folder}|${normalizedMessageId}`;
            const messageIdUnchanged = String(preview.selectedMessageId || '') === normalizedMessageId
                && preview.selectedKey === selectedKey;

            preview.selectedKey = selectedKey;
            preview.selectedKind = normalizedKind;
            preview.selectedSourceId = numericSourceId;
            preview.selectedMessageId = normalizedMessageId;

            // Soft re-select: same mailbox/folder/message detail already warm — re-render without network.
            const paintUnifiedPreview = () => (
                typeof isCurrentUnifiedMailboxSurface === 'function'
                    ? isCurrentUnifiedMailboxSurface()
                    : true
            );
            if (
                !forceRefresh
                && messageIdUnchanged
                && preview.detailSignature === detailSignature
                && preview.message
                && !preview.detailLoading
                && !preview.detailError
            ) {
                if (paintUnifiedPreview()) {
                    renderUnifiedMessagePreview();
                }
                return true;
            }

            // Soft joins any in-flight for the same signature. Force joins only force
            // in-flight; force supersedes soft so retry always starts a true network GET.
            if (
                preview.detailLoadPromise
                && preview.detailLoadSignature === detailSignature
            ) {
                if (!forceRefresh || preview.detailLoadForce) {
                    return preview.detailLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; detailSeq blocks stale apply.
                preview.detailLoadPromise = null;
                preview.detailLoadSignature = '';
                preview.detailLoadForce = false;
            }

            preview.detailLoading = true;
            preview.detailError = '';
            preview.message = null;
            preview.verification = null;
            preview.verificationError = '';
            preview.detailSignature = '';
            preview.verificationSignature = '';
            const seq = ++preview.detailSeq;
            if (paintUnifiedPreview()) {
                renderUnifiedMessagePreview();
            }

            preview.detailLoadForce = forceRefresh;
            const request = (async () => {
                try {
                    const params = new URLSearchParams({ folder });
                    const response = await fetch(`${getUnifiedMessageDetailEndpoint(normalizedKind, numericSourceId, normalizedMessageId)}?${params.toString()}`);
                    const data = await response.json();
                    if (seq !== preview.detailSeq || preview.detailLoadPromise !== request) return false;
                    preview.detailLoading = false;
                    if (!response.ok || !data.success) {
                        preview.detailError = getUnifiedPreviewErrorMessage(data, '邮件详情读取失败');
                        preview.detailSignature = '';
                        if (paintUnifiedPreview()) {
                            renderUnifiedMessagePreview();
                            showToast(preview.detailError, 'error');
                        }
                        return false;
                    }
                    // Always warm detail soft state; paint only on unified surface.
                    preview.mailbox = data.mailbox || preview.mailbox;
                    preview.message = data.message || null;
                    preview.detailSignature = detailSignature;
                    if (paintUnifiedPreview()) {
                        renderUnifiedMessagePreview();
                    }
                    return true;
                } catch (error) {
                    if (seq !== preview.detailSeq || preview.detailLoadPromise !== request) return false;
                    preview.detailLoading = false;
                    preview.detailError = translateUnifiedText('邮件详情读取失败');
                    preview.detailSignature = '';
                    if (paintUnifiedPreview()) {
                        renderUnifiedMessagePreview();
                        showToast(preview.detailError, 'error');
                    }
                    return false;
                } finally {
                    if (preview.detailLoadPromise === request) {
                        preview.detailLoadPromise = null;
                        preview.detailLoadSignature = '';
                        preview.detailLoadForce = false;
                    }
                }
            })();

            preview.detailLoadPromise = request;
            preview.detailLoadSignature = detailSignature;
            return request;
        }

        async function loadUnifiedMailboxVerification(kind, sourceId, options = {}) {
            const normalizedKind = normalizeUnifiedPreviewKind(kind);
            const numericSourceId = Number(sourceId || 0);
            const preview = unifiedMailboxState.preview;
            if (!normalizedKind || !numericSourceId) return false;
            const forceRefresh = Boolean(options && options.force);
            const selectedKey = getUnifiedMessageMailboxKey(normalizedKind, numericSourceId);
            const folder = String(preview.folder || 'inbox').trim().toLowerCase() || 'inbox';
            const verificationSignature = `${selectedKey}|${folder}`;
            const paintUnifiedPreview = () => (
                typeof isCurrentUnifiedMailboxSurface === 'function'
                    ? isCurrentUnifiedMailboxSurface()
                    : true
            );

            // Soft re-run: same mailbox/folder verification already warm — re-render without network.
            if (
                !forceRefresh
                && preview.selectedKey === selectedKey
                && preview.verificationSignature === verificationSignature
                && preview.verification
                && !preview.verificationLoading
                && !preview.verificationError
            ) {
                if (paintUnifiedPreview()) {
                    renderUnifiedMessagePreview();
                }
                return true;
            }

            // Soft joins any in-flight for the same signature. Force joins only force
            // in-flight; force supersedes soft so extract always starts a true network GET.
            if (
                preview.verificationLoadPromise
                && preview.verificationLoadSignature === verificationSignature
            ) {
                if (!forceRefresh || preview.verificationLoadForce) {
                    return preview.verificationLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; verificationSeq blocks stale apply.
                preview.verificationLoadPromise = null;
                preview.verificationLoadSignature = '';
                preview.verificationLoadForce = false;
            }

            preview.verificationLoading = true;
            preview.verificationError = '';
            preview.verificationSignature = '';
            const seq = ++preview.verificationSeq;
            if (paintUnifiedPreview()) {
                renderUnifiedMessagePreview();
            }

            preview.verificationLoadForce = forceRefresh;
            const request = (async () => {
                try {
                    const params = new URLSearchParams({ folder });
                    const response = await fetch(`${getUnifiedMessageEndpoint(normalizedKind, numericSourceId, 'verification')}?${params.toString()}`);
                    const data = await response.json();
                    if (seq !== preview.verificationSeq || preview.verificationLoadPromise !== request) return false;
                    preview.verificationLoading = false;
                    if (!response.ok || !data.success) {
                        preview.verificationError = getUnifiedPreviewErrorMessage(data, '验证码读取失败');
                        preview.verificationSignature = '';
                        if (paintUnifiedPreview()) {
                            renderUnifiedMessagePreview();
                            showToast(preview.verificationError, 'error');
                        }
                        return false;
                    }
                    // Always warm verification soft state; paint only on unified surface.
                    preview.mailbox = data.mailbox || preview.mailbox;
                    preview.verification = data.verification || null;
                    preview.verificationSignature = verificationSignature;
                    if (paintUnifiedPreview()) {
                        renderUnifiedMessagePreview();
                    }
                    return true;
                } catch (error) {
                    if (seq !== preview.verificationSeq || preview.verificationLoadPromise !== request) return false;
                    preview.verificationLoading = false;
                    preview.verificationError = translateUnifiedText('验证码读取失败');
                    preview.verificationSignature = '';
                    if (paintUnifiedPreview()) {
                        renderUnifiedMessagePreview();
                        showToast(preview.verificationError, 'error');
                    }
                    return false;
                } finally {
                    if (preview.verificationLoadPromise === request) {
                        preview.verificationLoadPromise = null;
                        preview.verificationLoadSignature = '';
                        preview.verificationLoadForce = false;
                    }
                }
            })();

            preview.verificationLoadPromise = request;
            preview.verificationLoadSignature = verificationSignature;
            return request;
        }

        function applyUnifiedMailboxDirectoryPayload(rawData) {
            // Keep local name `data` so render call-sites match existing contract tests.
            const data = rawData && typeof rawData === 'object' ? rawData : {};
            unifiedMailboxState.loaded = true;
            unifiedMailboxState.contract = data.contract || {};
            unifiedMailboxState.providerContext = data.provider_context || {};
            unifiedMailboxState.providerFacets = (data.facets || {}).providers || [];
            renderUnifiedKindOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.kind, (data.facets || {}).kinds || []);
            renderUnifiedStatusOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.status, (data.facets || {}).statuses || []);
            renderUnifiedReadCapabilityOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.readCapability, (data.facets || {}).read_capabilities || []);
            renderUnifiedActionOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.action, (data.facets || {}).actions || []);
            renderUnifiedProviderOptions(unifiedMailboxState.providerFacets, unifiedMailboxState.filters.provider);
            renderUnifiedSortOptions(unifiedMailboxState.contract, unifiedMailboxState.filters.sort);
            renderUnifiedQuickViews(unifiedMailboxState.filters, unifiedMailboxState.contract);
            renderUnifiedCommandCenter(data, 'ready');
            renderUnifiedSetupGuide(data, 'ready');
            renderUnifiedSummary(data.summary || {}, unifiedMailboxState.contract);
            const selectedProvider = (data.filters || unifiedMailboxState.filters).provider || 'all';
            renderUnifiedOperationalLens(data, 'ready');
            renderUnifiedProviderContext(unifiedMailboxState.providerContext, 'ready', unifiedMailboxState.providerFacets, selectedProvider);
            renderUnifiedProviderCapabilityMatrix(unifiedMailboxState.providerContext, unifiedMailboxState.contract, 'ready', selectedProvider);
            renderUnifiedMailboxList(data.mailboxes || []);
            renderUnifiedResultBar({ state: 'ready', pagination: data.pagination || {}, filters: data.filters || unifiedMailboxState.filters });
            renderUnifiedPagination(data.pagination || {});
        }

        async function loadUnifiedMailboxes(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            syncUnifiedFiltersFromDom();
            const requestSignature = getUnifiedMailboxRequestSignature();
            // Paint loading/error only while still on unified mailbox surface with the
            // same live filter signature (rapid filter/mode switches must not clobber UI).
            const isCurrentUnifiedDirectoryView = () => (
                isCurrentUnifiedMailboxSurface()
                && getUnifiedMailboxRequestSignature() === requestSignature
            );

            // Soft re-entry: always keep warm payload; paint only on current unified view.
            if (
                !force
                && unifiedMailboxState.loaded
                && unifiedMailboxState.directoryPayload
                && unifiedMailboxState.directorySignature === requestSignature
            ) {
                if (isCurrentUnifiedDirectoryView()) {
                    applyUnifiedMailboxDirectoryPayload(unifiedMailboxState.directoryPayload);
                }
                return;
            }

            // Soft joins any in-flight for the same signature. Force joins only force
            // in-flight; force supersedes soft so refresh/inventory always starts a true GET
            // and abandoned soft responses do not write directoryPayload.
            if (unifiedMailboxState.loading) {
                const sameInFlight = unifiedMailboxState.directoryInFlightSignature === requestSignature;
                if (sameInFlight && (!force || unifiedMailboxState.directoryLoadForce)) {
                    return;
                }
                if (force && !unifiedMailboxState.directoryLoadForce) {
                    // Abandon soft in-flight bookkeeping; seq mismatch blocks soft apply.
                    unifiedMailboxState.directoryLoadSeq += 1;
                    // Fall through to start force network while soft is still finishing.
                } else {
                    // Different signature (filters changed) or soft while force in-flight → queue.
                    unifiedMailboxState.pendingReload = true;
                    unifiedMailboxState.pendingForceRefresh = unifiedMailboxState.pendingForceRefresh || force;
                    return;
                }
            }

            const seq = ++unifiedMailboxState.directoryLoadSeq;
            unifiedMailboxState.directoryLoadForce = force;
            unifiedMailboxState.directoryInFlightSignature = requestSignature;
            unifiedMailboxState.loading = true;
            // This invocation owns the network path for requestSignature; a later
            // different-signature call may still set pendingReload while we run.
            if (isCurrentUnifiedMailboxSurface()) {
                setUnifiedRefreshBusy(true);
            }
            if (isCurrentUnifiedDirectoryView() && (!unifiedMailboxState.loaded || force)) {
                renderUnifiedLoadingState();
            }

            const params = new URLSearchParams({
                kind: unifiedMailboxState.filters.kind,
                status: unifiedMailboxState.filters.status,
                read_capability: unifiedMailboxState.filters.readCapability,
                action: unifiedMailboxState.filters.action,
                provider: unifiedMailboxState.filters.provider,
                sort: unifiedMailboxState.filters.sort,
                search: unifiedMailboxState.filters.search,
                page: String(unifiedMailboxState.page || 1),
                page_size: String(unifiedMailboxState.pageSize || 50)
            });

            try {
                const response = await fetch(`/api/mailboxes?${params.toString()}`);
                const data = await response.json();
                if (seq !== unifiedMailboxState.directoryLoadSeq) {
                    return;
                }
                if (!response.ok || !data.success) {
                    if (requestSignature !== getUnifiedMailboxRequestSignature()) {
                        unifiedMailboxState.pendingReload = true;
                        unifiedMailboxState.pendingForceRefresh = true;
                        return;
                    }
                    handleApiError(data, '邮箱目录加载失败');
                    if (isCurrentUnifiedDirectoryView()) {
                        renderUnifiedErrorState();
                    }
                    return;
                }
                if (requestSignature !== getUnifiedMailboxRequestSignature()) {
                    unifiedMailboxState.pendingReload = true;
                    unifiedMailboxState.pendingForceRefresh = true;
                    return;
                }
                // Always warm directory soft cache; paint only while still current view.
                unifiedMailboxState.directoryPayload = data;
                unifiedMailboxState.directorySignature = requestSignature;
                if (isCurrentUnifiedDirectoryView()) {
                    applyUnifiedMailboxDirectoryPayload(data);
                } else {
                    unifiedMailboxState.loaded = true;
                }
            } catch (error) {
                if (seq !== unifiedMailboxState.directoryLoadSeq) {
                    return;
                }
                if (requestSignature !== getUnifiedMailboxRequestSignature()) {
                    unifiedMailboxState.pendingReload = true;
                    unifiedMailboxState.pendingForceRefresh = true;
                    return;
                }
                if (isCurrentUnifiedDirectoryView()) {
                    renderUnifiedErrorState();
                    showToast(translateUnifiedText('邮箱目录加载失败'), 'error');
                }
            } finally {
                if (seq !== unifiedMailboxState.directoryLoadSeq) {
                    // Superseded by a newer force/soft owner; that owner manages loading/busy.
                    return;
                }
                unifiedMailboxState.loading = false;
                unifiedMailboxState.directoryLoadForce = false;
                unifiedMailboxState.directoryInFlightSignature = '';
                if (isCurrentUnifiedMailboxSurface()) {
                    setUnifiedRefreshBusy(false);
                }
                if (unifiedMailboxState.pendingReload) {
                    const pendingForceRefresh = unifiedMailboxState.pendingForceRefresh;
                    unifiedMailboxState.pendingReload = false;
                    unifiedMailboxState.pendingForceRefresh = false;
                    loadUnifiedMailboxes(pendingForceRefresh);
                }
            }
        }

        function goToUnifiedMailboxPage(page) {
            const target = Number(page || 1);
            const totalPages = Number(unifiedMailboxState.pagination.total_pages || 0);
            if (target < 1 || (totalPages && target > totalPages)) return;
            unifiedMailboxState.page = target;
            loadUnifiedMailboxes(true);
        }

        function debounceUnifiedMailboxSearch() {
            clearTimeout(unifiedMailboxState.searchTimer);
            syncUnifiedQuickViews();
            unifiedMailboxState.searchTimer = setTimeout(() => {
                unifiedMailboxState.page = 1;
                loadUnifiedMailboxes(true);
            }, 250);
        }

