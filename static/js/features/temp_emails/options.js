// split from temp_emails.js → options.js
        function getTempEmailOptionsProviderName(providerName = null) {
            const explicitProvider = String(providerName || '').trim();
            if (explicitProvider) return explicitProvider;
            const providerSelect = document.getElementById('tempEmailProviderSelect');
            return providerSelect && providerSelect.value ? providerSelect.value.trim() : '';
        }

        function getTempEmailOptionsCacheKey(providerName) {
            return getTempEmailOptionsProviderName(providerName) || '__default__';
        }

        function getTempEmailProviderDisplayLabel(providerName, options) {
            const catalogItem = typeof getMailboxProviderCatalogItem === 'function'
                ? getMailboxProviderCatalogItem(providerName, 'temp')
                : null;
            if (typeof resolveMailboxProviderLabel === 'function') {
                const resolved = resolveMailboxProviderLabel(providerName, {
                    softLoad: false,
                    emptyLabel: '',
                    fallbackResolver: (raw) => {
                        if (catalogItem && (catalogItem.label || catalogItem.provider_label)) {
                            return String(catalogItem.label || catalogItem.provider_label).trim();
                        }
                        const select = document.getElementById('tempEmailProviderSelect');
                        if (select) {
                            const matchedOption = Array.from(select.options).find(option => option.value === raw);
                            if (matchedOption && matchedOption.textContent) {
                                return matchedOption.textContent.trim();
                            }
                        }
                        return String(
                            (options && (options.provider_label || options.provider_name))
                            || ''
                        ).trim();
                    },
                });
                if (resolved) return resolved;
            }
            if (catalogItem && (catalogItem.label || catalogItem.provider_label)) {
                return String(catalogItem.label || catalogItem.provider_label).trim();
            }
            const select = document.getElementById('tempEmailProviderSelect');
            if (select) {
                const matchedOption = Array.from(select.options).find(option => option.value === providerName);
                if (matchedOption && matchedOption.textContent) {
                    return matchedOption.textContent.trim();
                }
            }
            return String((options && (options.provider_label || options.provider_name)) || providerName || translateAppTextLocal('当前 Provider'));
        }

        function renderTempEmailProviderStatus(providerName = null) {
            // Create-temp page status chrome only. Catalog soft re-entry must not
            // rewrite hidden status badges while the user is on another page.
            if (typeof isCurrentTempEmailsPage === 'function' && !isCurrentTempEmailsPage()) {
                return;
            }
            if (typeof currentPage !== 'undefined' && currentPage !== 'temp-emails') {
                return;
            }
            const target = document.getElementById('tempEmailProviderStatus');
            if (!target) return;

            const resolvedProviderName = getTempEmailOptionsProviderName(providerName);
            const catalogItem = typeof getMailboxProviderCatalogItem === 'function'
                ? getMailboxProviderCatalogItem(resolvedProviderName, 'temp')
                : null;
            if (!catalogItem || catalogItem.configured === undefined) {
                target.innerHTML = '';
                return;
            }

            const label = getTempEmailProviderDisplayLabel(resolvedProviderName, catalogItem);
            if (catalogItem.configured) {
                target.innerHTML = `<span class="badge badge-green">${escapeHtml(translateAppTextLocal('已就绪'))}</span><span>${escapeHtml(label)}</span>`;
                return;
            }

            const missing = Array.isArray(catalogItem.missing_config) ? catalogItem.missing_config : [];
            const missingText = missing.map(key => (
                typeof getMissingConfigDisplayName === 'function' ? getMissingConfigDisplayName(key) : key
            )).join('、') || translateAppTextLocal('必要配置');
            target.innerHTML = [
                `<span class="badge badge-gold">${escapeHtml(translateAppTextLocal('缺配置'))}</span>`,
                `<span class="provider-config-missing">${escapeHtml(label)}：${escapeHtml(missingText)}</span>`
            ].join('');
        }

        function supportsManualDomainSelection(options, domains) {
            if (!domains.length) return false;
            const strategy = String((options && options.domain_strategy) || '').trim().toLowerCase();
            if (!strategy) return true;
            return strategy === 'manual' || strategy === 'manual_only' || strategy === 'auto_or_manual';
        }

        function syncTempEmailProviderSelection(providerName, { forceRefresh = false } = {}) {
            const resolvedProviderName = getTempEmailOptionsProviderName(providerName);
            renderTempEmailProviderStatus(resolvedProviderName);
            renderTempEmailOptions({ status: 'loading', providerName: resolvedProviderName });
            return loadTempEmailOptions(forceRefresh, resolvedProviderName);
        }

        function shouldPaintTempEmailOptions(providerName = null) {
            // Paint domain/status chrome only on the dedicated temp-emails page and only
            // when the live provider selection still matches the request provider.
            if (typeof isCurrentTempEmailsPage === 'function' && !isCurrentTempEmailsPage()) {
                return false;
            }
            if (typeof currentPage !== 'undefined' && currentPage !== 'temp-emails') {
                return false;
            }
            const resolved = getTempEmailOptionsProviderName(providerName);
            return getTempEmailOptionsProviderName() === resolved;
        }

        async function loadTempEmailOptions(forceRefresh = false, providerName = null) {
            const resolvedProviderName = getTempEmailOptionsProviderName(providerName);
            const cacheKey = getTempEmailOptionsCacheKey(resolvedProviderName);
            const force = Boolean(forceRefresh);

            // Soft re-entry: always return warm options; paint only on temp-emails page
            // while the same provider is still selected.
            if (!force && tempEmailOptionsCache.has(cacheKey)) {
                const cachedOptions = tempEmailOptionsCache.get(cacheKey);
                if (shouldPaintTempEmailOptions(resolvedProviderName)) {
                    renderTempEmailOptions({ status: 'loaded', options: cachedOptions, providerName: resolvedProviderName });
                }
                return cachedOptions;
            }
            // Soft joins any in-flight for the same cacheKey. Force joins only force
            // in-flight; force supersedes soft so provider switch/refresh starts a true GET.
            if (tempEmailOptionsLoadPromises[cacheKey]) {
                if (!force || tempEmailOptionsLoadForce[cacheKey]) {
                    return tempEmailOptionsLoadPromises[cacheKey];
                }
                // Abandon soft in-flight bookkeeping; request identity blocks stale apply.
                delete tempEmailOptionsLoadPromises[cacheKey];
                delete tempEmailOptionsLoadForce[cacheKey];
            }

            const requestSeq = ++tempEmailOptionsRequestSeq;
            tempEmailOptionsLoadForce[cacheKey] = force;
            const request = (async () => {
                try {
                    const url = resolvedProviderName
                        ? `/api/temp-emails/options?provider_name=${encodeURIComponent(resolvedProviderName)}`
                        : '/api/temp-emails/options';
                    const response = await fetch(url);
                    if (tempEmailOptionsLoadPromises[cacheKey] !== request) {
                        return tempEmailOptionsCache.get(cacheKey) || null;
                    }
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    const data = await response.json();
                    if (tempEmailOptionsLoadPromises[cacheKey] !== request) {
                        return tempEmailOptionsCache.get(cacheKey) || null;
                    }
                    if (data.success && data.options) {
                        // Always warm options soft cache; paint only while still current.
                        tempEmailOptionsState.set(cacheKey, 'loaded');
                        tempEmailOptionsCache.set(cacheKey, data.options);
                        if (
                            requestSeq === tempEmailOptionsRequestSeq
                            && shouldPaintTempEmailOptions(resolvedProviderName)
                        ) {
                            renderTempEmailOptions({ status: 'loaded', options: data.options, providerName: resolvedProviderName });
                        }
                        return data.options;
                    }
                    throw new Error(
                        window.resolveApiErrorMessage
                            ? window.resolveApiErrorMessage(data.error || data, '加载失败', 'Load failed')
                            : (data.error && data.error.message ? data.error.message : '加载失败')
                    );
                } catch (error) {
                    if (tempEmailOptionsLoadPromises[cacheKey] !== request) {
                        return tempEmailOptionsCache.get(cacheKey) || null;
                    }
                    tempEmailOptionsState.set(cacheKey, 'error');
                    console.error('加载临时邮箱配置失败:', error);
                    if (
                        requestSeq === tempEmailOptionsRequestSeq
                        && shouldPaintTempEmailOptions(resolvedProviderName)
                    ) {
                        renderTempEmailOptions({
                            status: 'error',
                            providerName: resolvedProviderName,
                            errorMessage: error && error.message ? error.message : translateAppTextLocal('请检查临时邮箱 options 接口')
                        });
                        showToast(translateAppTextLocal('临时邮箱配置加载失败'), 'warning');
                    }
                    return null;
                } finally {
                    if (tempEmailOptionsLoadPromises[cacheKey] === request) {
                        delete tempEmailOptionsLoadPromises[cacheKey];
                        delete tempEmailOptionsLoadForce[cacheKey];
                    }
                }
            })();

            tempEmailOptionsLoadPromises[cacheKey] = request;
            return request;
        }

        function renderTempEmailOptions(payload) {
            const domainSelect = document.getElementById('tempEmailDomainSelect');
            const hint = document.getElementById('tempEmailOptionsHint');
            const status = document.getElementById('tempEmailOptionsStatus');
            if (!domainSelect) return;

            const renderStatus = payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'status')
                ? payload.status
                : 'loaded';
            const options = renderStatus === 'loaded' && payload ? payload.options : null;
            const providerName = getTempEmailOptionsProviderName(payload && payload.providerName ? payload.providerName : null);
            const providerLabel = getTempEmailProviderDisplayLabel(providerName, options);
            const domains = Array.isArray(options?.domains) ? options.domains.filter(item => item && item.enabled !== false) : [];
            const canSelectDomainManually = supportsManualDomainSelection(options, domains);
            renderTempEmailProviderStatus(providerName);

            if (renderStatus === 'loading') {
                domainSelect.disabled = true;
                domainSelect.innerHTML = `<option value="">${escapeHtml(translateAppTextLocal('正在读取域名配置'))}</option>`;
                if (hint) {
                    hint.textContent = `${providerLabel}${translateAppTextLocal(' 正在读取域名配置。')}`;
                }
                if (status) {
                    status.textContent = '';
                    status.style.display = 'none';
                }
                return;
            }

            if (renderStatus === 'error') {
                domainSelect.disabled = true;
                domainSelect.innerHTML = `<option value="">${escapeHtml(translateAppTextLocal('域名配置加载失败'))}</option>`;
                if (hint) {
                    hint.textContent = translateAppTextLocal('无法读取当前 Provider 的域名配置。');
                }
                if (status) {
                    status.textContent = payload.errorMessage || translateAppTextLocal('请检查 /api/temp-emails/options 接口是否可用。');
                    status.style.display = 'block';
                }
                return;
            }

            const prevDomainValue = domainSelect.value;
            if (status) {
                status.textContent = '';
                status.style.display = 'none';
            }

            if (!canSelectDomainManually) {
                domainSelect.disabled = true;
                domainSelect.innerHTML = `<option value="">${escapeHtml(translateAppTextLocal('自动分配域名'))}</option>`;
                domainSelect.value = '';
                if (hint) {
                    hint.textContent = domains.length > 0
                        ? `${providerLabel}${translateAppTextLocal(' 当前由服务端自动分配域名。')}`
                        : `${providerLabel}${translateAppTextLocal(' 当前未提供可选域名，域名将由服务端自动分配。')}`;
                }
                return;
            }

            domainSelect.disabled = false;
            // BUG-07: 重建 innerHTML 前先保存当前选中值，重建后再恢复。
            // 否则每次 loadTempEmails/renderTempEmailOptions 都会把用户选好的域名重置回"自动分配"。
            domainSelect.innerHTML = [
                `<option value="">${escapeHtml(translateAppTextLocal('自动分配域名'))}</option>`,
                ...domains.map(item => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)}</option>`)
            ].join('');
            if (prevDomainValue && domains.some(d => d.name === prevDomainValue)) {
                domainSelect.value = prevDomainValue;
            }

            if (hint) {
                hint.textContent = `${translateAppTextLocal('可用域名：')}${domains.map(item => item.name).join(' / ')}`;
            }
        }

        // 复制临时邮箱页面顶栏当前邮箱地址
        function onTempEmailProviderChange(selectedProvider) {
            syncTempEmailProviderSelection(selectedProvider, { forceRefresh: false });
        }

        document.addEventListener('change', event => {
            if (event.target && event.target.id === 'tempEmailProviderSelect') {
                onTempEmailProviderChange(event.target.value);
            }
        });

