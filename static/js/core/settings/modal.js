// split from settings.js → modal.js
        function toggleUpdateMethodConfig() {
            const watchtowerConfigArea = document.getElementById('watchtowerConfigArea');
            const dockerApiWarning = document.getElementById('dockerApiWarning');
            if (!watchtowerConfigArea || !dockerApiWarning) return;

            const selectedMethod = document.querySelector('input[name="updateMethod"]:checked')?.value;
            if (selectedMethod === 'docker_api') {
                watchtowerConfigArea.style.display = 'none';
                dockerApiWarning.style.display = 'block';
            } else {
                watchtowerConfigArea.style.display = 'block';
                dockerApiWarning.style.display = 'none';
            }
        }

        function initUpdateMethodConfigToggles() {
            try {
                const updateMethodRadios = document.getElementsByName('updateMethod');
                if (!updateMethodRadios || updateMethodRadios.length === 0) {
                    return;
                }

                updateMethodRadios.forEach((radio) => {
                    if (!radio) return;
                    // 防止重复绑定（某些情况下可能多次初始化）
                    if (radio.dataset && radio.dataset.boundUpdateMethodToggle === 'true') {
                        return;
                    }
                    radio.addEventListener('change', toggleUpdateMethodConfig);
                    if (radio.dataset) {
                        radio.dataset.boundUpdateMethodToggle = 'true';
                    }
                });

                // 初始化时调用一次，确保初始显隐正确
                toggleUpdateMethodConfig();
            } catch (e) {
                // 静默失败：不影响其它功能
            }
        }

        // 显示设置模态框
        async function showSettingsModal() {
            document.getElementById('settingsModal').classList.add('show');
            // Compatibility modal path; primary nav uses navigate('settings') → loadSettings.
            await loadSettings();
        }

        // 隐藏设置模态框
        function hideSettingsModal() {
            document.getElementById('settingsModal').classList.remove('show');
            // 清空密码输入框
            document.getElementById('settingsPassword').value = '';
        }

        function softPaintSettingsSecretHintsIfOpen() {
            if (!isSettingsSurfaceActive()) return;

            const externalHintEl = document.getElementById('externalApiKeyHint');
            const externalApiKeyEl = document.getElementById('settingsExternalApiKey');
            if (externalHintEl && externalApiKeyEl) {
                if (externalApiKeyEl.dataset.isSet === 'true') {
                    externalHintEl.textContent = translateAppTextLocal(
                        '已设置：' + (externalApiKeyEl.dataset.maskedValue || '')
                    );
                } else {
                    externalHintEl.textContent = translateAppTextLocal(
                        '未设置（设置后可通过 /api/v1/external/* 对外开放接口读取邮件与验证码；/api/v1/external/* 保持 legacy 兼容）'
                    );
                }
            }

            const verificationHintEl = document.getElementById('verificationAiApiKeyHint');
            const verificationKeyEl = document.getElementById('settingsVerificationAiApiKey');
            if (verificationHintEl && verificationKeyEl) {
                if (verificationKeyEl.dataset.isSet === 'true') {
                    verificationHintEl.textContent = translateAppTextLocal(
                        '已设置：' + (verificationKeyEl.dataset.maskedValue || '')
                    );
                } else {
                    verificationHintEl.textContent = translateAppTextLocal('未设置');
                }
            }

            // Multi-key JSON hint: re-apply from warm snapshot or editor original canonical.
            try {
                const snap = externalApiSettingsSnapshot && typeof externalApiSettingsSnapshot === 'object'
                    ? externalApiSettingsSnapshot
                    : null;
                if (snap && Object.prototype.hasOwnProperty.call(snap, 'external_api_keys')) {
                    setExternalApiKeysEditor(snap.external_api_keys || []);
                } else {
                    const editorEl = document.getElementById('settingsExternalApiKeysJson');
                    if (editorEl && editorEl.dataset.originalCanonical) {
                        const parsed = JSON.parse(editorEl.dataset.originalCanonical || '[]');
                        setExternalApiKeysEditor(parsed);
                    }
                }
            } catch (_e) {}
        }

        function parseSettingsJsonInput(inputEl, errorMessage, emptyValue) {
            if (!inputEl) return { ok: true, exists: false };
            const rawValue = inputEl.value.trim();
            if (!rawValue) {
                return { ok: true, exists: true, value: emptyValue };
            }
            try {
                return { ok: true, exists: true, value: JSON.parse(rawValue) };
            } catch (error) {
                showToast(translateAppTextLocal(errorMessage), 'error');
                return { ok: false, exists: true };
            }
        }

        function invalidateSettingsPageCache() {
            settingsPageCache = null;
            settingsPageCacheGeneration += 1;
            // Drop soft coalesce handle; an in-flight soft request still completes but
            // will not write cache when its captured generation no longer matches.
            settingsPageLoadPromise = null;
            settingsPageLoadForce = false;
        }

        async function fetchSettingsPagePayload(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            if (!force && settingsPageCache && settingsPageCache.success) {
                return settingsPageCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so save/refresh always start a true network GET.
            if (settingsPageLoadPromise) {
                if (!force || settingsPageLoadForce) {
                    return settingsPageLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; generation bump blocks stale cache write.
                settingsPageLoadPromise = null;
                settingsPageLoadForce = false;
                settingsPageCacheGeneration += 1;
            }
            const generation = settingsPageCacheGeneration;
            settingsPageLoadForce = force;
            const request = (async () => {
                const response = await fetch('/api/settings');
                const data = await response.json();
                // Only soft/force writes that still match the current generation may cache.
                if (data && data.success && generation === settingsPageCacheGeneration) {
                    settingsPageCache = data;
                }
                return data;
            })();
            settingsPageLoadPromise = request;
            try {
                return await request;
            } finally {
                if (settingsPageLoadPromise === request) {
                    settingsPageLoadPromise = null;
                    settingsPageLoadForce = false;
                }
            }
        }

        function collectApiSecuritySettingsPayload() {
            const settings = {};
            const externalApiKeyEl = document.getElementById('settingsExternalApiKey');
            const externalApiKeysJsonEl = document.getElementById('settingsExternalApiKeysJson');
            const externalApiKeysRaw = externalApiKeysJsonEl ? externalApiKeysJsonEl.value.trim() : '';
            const originalExternalApiKeysCanonical = externalApiKeysJsonEl
                ? (externalApiKeysJsonEl.dataset.originalCanonical || '[]')
                : '[]';

            assignSecretSettingFromInput(settings, 'external_api_key', externalApiKeyEl);

            if (externalApiKeysJsonEl) {
                if (externalApiKeysRaw) {
                    let parsedExternalApiKeys;
                    try {
                        parsedExternalApiKeys = JSON.parse(externalApiKeysRaw);
                    } catch (error) {
                        showToast(translateAppTextLocal('多 Key 配置必须是合法 JSON'), 'error');
                        return null;
                    }

                    if (!Array.isArray(parsedExternalApiKeys)) {
                        showToast(translateAppTextLocal('多 Key 配置必须是 JSON 数组'), 'error');
                        return null;
                    }

                    let normalizedExternalApiKeys;
                    try {
                        normalizedExternalApiKeys = buildExternalApiKeysEditorItems(parsedExternalApiKeys);
                    } catch (error) {
                        showToast(error.message || translateAppTextLocal('多 Key 配置格式无效'), 'error');
                        return null;
                    }

                    const nextCanonical = JSON.stringify(normalizedExternalApiKeys);
                    if (nextCanonical !== originalExternalApiKeysCanonical) {
                        settings.external_api_keys = normalizedExternalApiKeys;
                    }
                } else if (originalExternalApiKeysCanonical !== '[]') {
                    settings.external_api_keys = [];
                }
            }

            const publicModeEl = document.getElementById('externalApiPublicMode');
            if (publicModeEl) settings.external_api_public_mode = publicModeEl.checked;

            const ipWhitelistEl = document.getElementById('externalApiIpWhitelist');
            if (ipWhitelistEl) {
                settings.external_api_ip_whitelist = ipWhitelistEl.value.trim().split('\n').map(line => line.trim()).filter(Boolean);
            }

            const rateLimitEl = document.getElementById('externalApiRateLimit');
            if (rateLimitEl) {
                const rateLimit = parseInt(rateLimitEl.value);
                if (!isNaN(rateLimit)) settings.external_api_rate_limit_per_minute = rateLimit;
            }

            const disableRawEl = document.getElementById('externalApiDisableRaw');
            if (disableRawEl) settings.external_api_disable_raw_content = disableRawEl.checked;

            const disableWaitEl = document.getElementById('externalApiDisableWait');
            if (disableWaitEl) settings.external_api_disable_wait_message = disableWaitEl.checked;

            const poolExternalEnabledEl = document.getElementById('poolExternalEnabled');
            if (poolExternalEnabledEl) settings.pool_external_enabled = poolExternalEnabledEl.checked;

            const poolDefaultProviderEl = document.getElementById('poolDefaultProvider');
            if (poolDefaultProviderEl) {
                settings.pool_default_provider = canonicalizeMailboxProviderAllowlistValue(
                    poolDefaultProviderEl.value.trim() || 'auto'
                ) || 'auto';
            }

            const activeMailboxProvidersEl = document.getElementById('activeMailboxProviders');
            if (activeMailboxProvidersEl) {
                // Always submit canonical keys so bridge aliases do not fork allowlists.
                settings.active_mailbox_providers = getActiveMailboxProvidersFromTextarea();
            }

            const disablePoolClaimRandomEl = document.getElementById('externalApiDisablePoolClaimRandom');
            if (disablePoolClaimRandomEl) settings.external_api_disable_pool_claim_random = disablePoolClaimRandomEl.checked;

            const disablePoolClaimReleaseEl = document.getElementById('externalApiDisablePoolClaimRelease');
            if (disablePoolClaimReleaseEl) settings.external_api_disable_pool_claim_release = disablePoolClaimReleaseEl.checked;

            const disablePoolClaimCompleteEl = document.getElementById('externalApiDisablePoolClaimComplete');
            if (disablePoolClaimCompleteEl) settings.external_api_disable_pool_claim_complete = disablePoolClaimCompleteEl.checked;

            const disablePoolStatsEl = document.getElementById('externalApiDisablePoolStats');
            if (disablePoolStatsEl) settings.external_api_disable_pool_stats = disablePoolStatsEl.checked;

            return settings;
        }

        // 加载设置
        async function loadSettings(forceRefresh = false) {
            try {
                // Page path (navigate('settings')) and modal path both land here.
                // Tab-specific control init only for the already-active tab.
                if (currentSettingsTab === 'temp-mail') {
                    await ensureTempMailSettingsTabReady();
                } else if (currentSettingsTab === 'automation') {
                    ensureAutomationSettingsTabReady();
                }

                const data = await fetchSettingsPagePayload(forceRefresh);

                if (data && data.success) {
                    externalApiSettingsSnapshot = data.settings || {};
                    tempMailSettingsSnapshot = data.settings || {};
                    tempMailSettingsDirtyKeys = new Set();

                    // 密码不回显
                    document.getElementById('settingsPassword').value = '';

                    const verificationAiEnabledEl = document.getElementById('settingsVerificationAiEnabled');
                    if (verificationAiEnabledEl) {
                        verificationAiEnabledEl.checked = !!data.settings.verification_ai_enabled;
                    }

                    const verificationAiBaseUrlEl = document.getElementById('settingsVerificationAiBaseUrl');
                    if (verificationAiBaseUrlEl) {
                        verificationAiBaseUrlEl.value = data.settings.verification_ai_base_url || '';
                    }

                    const verificationAiModelEl = document.getElementById('settingsVerificationAiModel');
                    if (verificationAiModelEl) {
                        verificationAiModelEl.value = data.settings.verification_ai_model || '';
                    }

                    const verificationAiApiKeyEl = document.getElementById('settingsVerificationAiApiKey');
                    if (verificationAiApiKeyEl) {
                        const maskedValue = data.settings.verification_ai_api_key_masked || '';
                        verificationAiApiKeyEl.value = maskedValue;
                        verificationAiApiKeyEl.dataset.maskedValue = maskedValue;
                        verificationAiApiKeyEl.dataset.isSet = data.settings.verification_ai_api_key_set ? 'true' : 'false';
                    }

                    const verificationAiApiKeyHintEl = document.getElementById('verificationAiApiKeyHint');
                    if (verificationAiApiKeyHintEl) {
                        if (data.settings.verification_ai_api_key_set) {
                            verificationAiApiKeyHintEl.textContent = translateAppTextLocal(
                                `已设置：${data.settings.verification_ai_api_key_masked || ''}`
                            );
                        } else {
                            verificationAiApiKeyHintEl.textContent = translateAppTextLocal('未设置');
                        }
                    }

                    const verificationAiTestResultEl = document.getElementById('verificationAiTestResult');
                    if (verificationAiTestResultEl) {
                        verificationAiTestResultEl.textContent = translateAppTextLocal('建议先保存配置再测试。');
                        verificationAiTestResultEl.style.color = 'var(--text-secondary, #666)';
                    }

                    // v0.3: Provider 选择器改为单选按钮（仅 temp-mail tab 已绑定时绘制）
                    const rawProvider = data.settings.temp_mail_provider || getOperatorDefaultTempMailProvider();
                    const mappedProvider = normalizeTempMailSettingsProviderName(rawProvider) || getOperatorDefaultTempMailProvider();
                    applyTempMailSettingsSelection(mappedProvider);
                    // Boot already soft-preloads /api/providers. Opening Settings should
                    // reuse a warm non-empty cache; only force when cache is missing/empty.
                    const forceCatalogLoad = !(
                        Array.isArray(mailboxProviderCatalogCache)
                        && mailboxProviderCatalogCache.length
                    );
                    loadMailboxProviderCatalog(forceCatalogLoad);
                    // Schema panel hydrates only when temp-mail radios/config are bound.
                    if (isTempMailSettingsProviderMountBound()) {
                        renderTempMailProviderConfigPanel(mappedProvider);
                    }

                    const externalApiKeyEl = document.getElementById('settingsExternalApiKey');
                    if (externalApiKeyEl) {
                        const maskedValue = data.settings.external_api_key_masked || '';
                        externalApiKeyEl.value = maskedValue;
                        externalApiKeyEl.dataset.maskedValue = maskedValue;
                        externalApiKeyEl.dataset.isSet = data.settings.external_api_key_set ? 'true' : 'false';
                    }

                    const externalHintEl = document.getElementById('externalApiKeyHint');
                    if (externalHintEl) {
                        if (data.settings.external_api_key_set) {
                            externalHintEl.textContent = translateAppTextLocal(
                                `已设置：${data.settings.external_api_key_masked || ''}`
                            );
                        } else {
                            externalHintEl.textContent = translateAppTextLocal(
                                '未设置（设置后可通过 /api/v1/external/* 对外开放接口读取邮件与验证码；/api/v1/external/* 保持 legacy 兼容）'
                            );
                        }
                    }

                    setExternalApiKeysEditor(data.settings.external_api_keys || []);

                    // P1：公网安全配置
                    const publicModeEl = document.getElementById('externalApiPublicMode');
                    if (publicModeEl) publicModeEl.checked = data.settings.external_api_public_mode === true;

                    const ipWhitelistEl = document.getElementById('externalApiIpWhitelist');
                    if (ipWhitelistEl) {
                        const wl = data.settings.external_api_ip_whitelist;
                        ipWhitelistEl.value = Array.isArray(wl) ? wl.join('\n') : '';
                    }

                    const rateLimitEl = document.getElementById('externalApiRateLimit');
                    if (rateLimitEl) rateLimitEl.value = data.settings.external_api_rate_limit_per_minute || 60;

                    const disableRawEl = document.getElementById('externalApiDisableRaw');
                    if (disableRawEl) disableRawEl.checked = data.settings.external_api_disable_raw_content === true;

                    const disableWaitEl = document.getElementById('externalApiDisableWait');
                    if (disableWaitEl) disableWaitEl.checked = data.settings.external_api_disable_wait_message === true;

                    const poolExternalEnabledEl = document.getElementById('poolExternalEnabled');
                    if (poolExternalEnabledEl) poolExternalEnabledEl.checked = data.settings.pool_external_enabled === true;

                    const poolDefaultProviderEl = document.getElementById('poolDefaultProvider');
                    if (poolDefaultProviderEl) {
                        poolDefaultProviderEl.value = canonicalizeMailboxProviderAllowlistValue(
                            data.settings.pool_default_provider || 'auto'
                        ) || 'auto';
                    }

                    const activeMailboxProvidersEl = document.getElementById('activeMailboxProviders');
                    if (activeMailboxProvidersEl) {
                        const activeProviders = Array.isArray(data.settings.active_mailbox_providers) ? data.settings.active_mailbox_providers : [];
                        setActiveMailboxProvidersTextarea(activeProviders);
                        renderActiveMailboxProviderSuggestions();
                    }

                    const disablePoolClaimRandomEl = document.getElementById('externalApiDisablePoolClaimRandom');
                    if (disablePoolClaimRandomEl) disablePoolClaimRandomEl.checked = data.settings.external_api_disable_pool_claim_random === true;

                    const disablePoolClaimReleaseEl = document.getElementById('externalApiDisablePoolClaimRelease');
                    if (disablePoolClaimReleaseEl) disablePoolClaimReleaseEl.checked = data.settings.external_api_disable_pool_claim_release === true;

                    const disablePoolClaimCompleteEl = document.getElementById('externalApiDisablePoolClaimComplete');
                    if (disablePoolClaimCompleteEl) disablePoolClaimCompleteEl.checked = data.settings.external_api_disable_pool_claim_complete === true;

                    const disablePoolStatsEl = document.getElementById('externalApiDisablePoolStats');
                    if (disablePoolStatsEl) disablePoolStatsEl.checked = data.settings.external_api_disable_pool_stats === true;

                    // API security surfaces: only when that tab is already active.
                    // Form field hydration above still runs so switching tabs has values ready.
                    // switchSettingsTab('api-security') paints + soft-loads on first visit.
                    if (currentSettingsTab === 'api-security') {
                        paintApiSecuritySurfacesFromSnapshot(data.settings || {}, 'ready');
                        loadProviderPreflightSnapshot(false, false);
                        loadExternalApiContractCheck(false);
                        loadOperationalReadinessSnapshot(false);
                    }

                    // 加载刷新配置
                    document.getElementById('refreshIntervalDays').value = data.settings.refresh_interval_days || '30';
                    document.getElementById('refreshDelaySeconds').value = data.settings.refresh_delay_seconds || '5';
                    document.getElementById('refreshCron').value = data.settings.refresh_cron || '0 2 * * *';

                    // 设置定时刷新开关
                    const enableScheduled = data.settings.enable_scheduled_refresh !== 'false';
                    document.getElementById('enableScheduledRefresh').checked = enableScheduled;

                    // 设置刷新策略单选框
                    const useCron = data.settings.use_cron_schedule === 'true';
                    document.querySelector('input[name="refreshStrategy"][value="' + (useCron ? 'cron' : 'days') + '"]').checked = true;
                    toggleRefreshStrategy();

                    // 加载轮询设置（后端返回 boolean，兼容处理）
                    // [Phase 3 兼容] 任一开关开启，设置面板复选框就显示为勾选状态
                    const enablePolling = isAutoPollingEnabledSetting(data.settings.enable_auto_polling)
                        || isAutoPollingEnabledSetting(data.settings.enable_compact_auto_poll);
                    document.getElementById('enableAutoPolling').checked = enablePolling;
                    document.getElementById('pollingInterval').value = String(parseIntegerSetting(data.settings.polling_interval, 10));
                    document.getElementById('pollingCount').value = String(parseIntegerSetting(data.settings.polling_count, 5));

                    // [Phase 3] 简洁模式独立面板已合并，使用统一引擎配置
                    applyPollingSettings(data.settings);

                    // 加载 Telegram 推送设置
                    const tgToken = document.getElementById('telegramBotToken');
                    const tgChat = document.getElementById('telegramChatId');
                    const tgPoll = document.getElementById('telegramPollInterval');
                    const tgProxy = document.getElementById('telegramProxyUrl');
                    const emailEnabled = document.getElementById('emailNotificationEnabled');
                    const emailRecipient = document.getElementById('emailNotificationRecipient');
                    const webhookEnabledEl = document.getElementById('webhookNotificationEnabled');
                    const webhookUrlEl = document.getElementById('webhookNotificationUrl');
                    const webhookTokenEl = document.getElementById('webhookNotificationToken');
                    if (tgToken) tgToken.value = data.telegram_bot_token || '';
                    if (tgChat) tgChat.value = data.telegram_chat_id || '';
                    if (tgPoll) tgPoll.value = String(parseIntegerSetting(data.telegram_poll_interval, 600));
                    if (tgProxy) tgProxy.value = (data.settings && data.settings.telegram_proxy_url) || '';
                    if (emailEnabled) emailEnabled.checked = !!data.settings.email_notification_enabled;
                    if (emailRecipient) emailRecipient.value = data.settings.email_notification_recipient || '';
                    if (webhookEnabledEl) webhookEnabledEl.checked = data.settings.webhook_notification_enabled === true;
                    if (webhookUrlEl) webhookUrlEl.value = (data.settings && data.settings.webhook_notification_url) || '';
                    if (webhookTokenEl) {
                        const webhookMasked = (data.settings && data.settings.webhook_notification_token) || '';
                        webhookTokenEl.value = webhookMasked;
                        webhookTokenEl.dataset.maskedValue = webhookMasked;
                        webhookTokenEl.dataset.isSet = webhookMasked ? 'true' : 'false';
                    }

                    // 加载 Watchtower 一键更新设置
                    const wtUrl = document.getElementById('watchtowerUrl');
                    const wtToken = document.getElementById('watchtowerToken');
                    if (wtUrl) wtUrl.value = (data.settings && data.settings.watchtower_url) || '';
                    if (wtToken) wtToken.value = (data.settings && data.settings.watchtower_token) || '';
                    
                    // 加载更新方式设置
                    const updateMethod = (data.settings && data.settings.update_method) || 'watchtower';
                    const updateMethodRadios = document.getElementsByName('updateMethod');
                    updateMethodRadios.forEach(radio => {
                        radio.checked = (radio.value === updateMethod);
                    });

                    // 触发更新方式切换逻辑（index.html 内联脚本绑定了 change 事件）
                    // 注意：直接设置 radio.checked 不会触发 change，需手动派发事件以更新显隐。
                    try {
                        const selectedUpdateMethodRadio = document.querySelector('input[name="updateMethod"]:checked');
                        if (selectedUpdateMethodRadio) {
                            selectedUpdateMethodRadio.dispatchEvent(new Event('change'));
                        }
                    } catch (e) {
                        // 静默失败
                    }

                    // Soft-load deployment warnings; force only when cache cold.
                    loadDeploymentInfo({ silent: true, forceRefresh: false });
                }
            } catch (error) {
                console.error('loadSettings error:', error);
                // Soft load may finish after navigate away / modal close — toast only on Settings surface.
                if (typeof isSettingsSurfaceActive === 'function' ? isSettingsSurfaceActive() : true) {
                    showToast(translateAppTextLocal('加载设置失败'), 'error');
                }
            }
        }

        // ==================== 部署信息检测（用于一键更新提示） ====================

        // 缓存最近一次部署信息，用于语言切换时重渲染 / Settings re-entry soft-load
        let lastDeploymentInfo = null;
        let deploymentInfoLoadPromise = null;
        // True when the in-flight deployment-info GET was started with forceRefresh.
        let deploymentInfoLoadForce = false;

        function toggleRefreshStrategy() {
            const strategy = document.querySelector('input[name="refreshStrategy"]:checked').value;
            document.getElementById('daysStrategyContainer').style.display = strategy === 'days' ? 'block' : 'none';
            document.getElementById('cronStrategyContainer').style.display = strategy === 'cron' ? 'block' : 'none';
        }

        // 选择 Cron 样例
        async function saveSettings() {
            const password = document.getElementById('settingsPassword').value;

            const verificationAiEnabledEl = document.getElementById('settingsVerificationAiEnabled');
            const verificationAiBaseUrlEl = document.getElementById('settingsVerificationAiBaseUrl');
            const verificationAiApiKeyEl = document.getElementById('settingsVerificationAiApiKey');
            const verificationAiModelEl = document.getElementById('settingsVerificationAiModel');

            const verificationAiEnabled = verificationAiEnabledEl ? verificationAiEnabledEl.checked : false;
            const verificationAiBaseUrl = verificationAiBaseUrlEl ? verificationAiBaseUrlEl.value.trim() : '';
            const verificationAiModel = verificationAiModelEl ? verificationAiModelEl.value.trim() : '';
            const verificationAiApiKey = verificationAiApiKeyEl ? verificationAiApiKeyEl.value.trim() : '';
            const verificationAiApiKeyMasked = verificationAiApiKeyEl ? (verificationAiApiKeyEl.dataset.maskedValue || '') : '';
            const verificationAiApiKeyIsSet = verificationAiApiKeyEl ? verificationAiApiKeyEl.dataset.isSet === 'true' : false;

            const refreshDays = document.getElementById('refreshIntervalDays').value;
            const refreshDelay = document.getElementById('refreshDelaySeconds').value;
            const refreshCron = document.getElementById('refreshCron').value.trim();
            const strategy = document.querySelector('input[name="refreshStrategy"]:checked').value;
            const enableScheduled = document.getElementById('enableScheduledRefresh').checked;

            // 轮询设置
            const enablePolling = document.getElementById('enableAutoPolling').checked;
            const pollingInterval = document.getElementById('pollingInterval').value;
            const pollingCount = document.getElementById('pollingCount').value;
            const emailNotificationEnabled = document.getElementById('emailNotificationEnabled').checked;
            const emailNotificationRecipient = document.getElementById('emailNotificationRecipient').value.trim();

            const settings = {};

            // 只有输入了密码才更新密码
            if (password) {
                settings.login_password = password;
            }

            settings.verification_ai_enabled = verificationAiEnabled;
            settings.verification_ai_base_url = verificationAiBaseUrl;
            settings.verification_ai_model = verificationAiModel;

            if (!(verificationAiApiKeyIsSet && verificationAiApiKey && verificationAiApiKey === verificationAiApiKeyMasked)) {
                settings.verification_ai_api_key = verificationAiApiKey;
            }

            if (verificationAiEnabled) {
                if (!verificationAiBaseUrl) {
                    showToast(translateAppTextLocal('请填写 AI Base URL'), 'error');
                    return;
                }
                if (!verificationAiModel) {
                    showToast(translateAppTextLocal('请填写 AI 模型 ID'), 'error');
                    return;
                }
                const hasApiKey = !!verificationAiApiKey || (verificationAiApiKeyIsSet && verificationAiApiKey === verificationAiApiKeyMasked);
                if (!hasApiKey) {
                    showToast(translateAppTextLocal('请填写 AI API Key'), 'error');
                    return;
                }
            }

            const tempMailSettings = collectTempMailSettingsPayload();
            if (!tempMailSettings) return;
            Object.assign(settings, tempMailSettings);

            const apiSecuritySettings = collectApiSecuritySettingsPayload();
            if (!apiSecuritySettings) return;
            Object.assign(settings, apiSecuritySettings);

            // 刷新配置
            const days = parseInt(refreshDays);
            const delay = parseInt(refreshDelay);

            if (isNaN(days) || days < 1 || days > 90) {
                showToast(translateAppTextLocal('刷新周期必须在 1-90 天之间'), 'error');
                return;
            }

            if (isNaN(delay) || delay < 0 || delay > 60) {
                showToast(translateAppTextLocal('刷新间隔必须在 0-60 秒之间'), 'error');
                return;
            }

            settings.refresh_interval_days = days;
            settings.refresh_delay_seconds = delay;
            settings.use_cron_schedule = strategy === 'cron';
            settings.enable_scheduled_refresh = enableScheduled;

            if (strategy === 'cron') {
                if (!refreshCron) {
                    showToast(translateAppTextLocal('请输入 Cron 表达式'), 'error');
                    return;
                }
                settings.refresh_cron = refreshCron;
            }

            // 轮询配置验证
            const pInterval = parseInt(pollingInterval);
            const pCount = parseInt(pollingCount);

            if (isNaN(pInterval) || pInterval < 3 || pInterval > 300) {
                showToast(translateAppTextLocal('轮询间隔必须在 3-300 秒之间'), 'error');
                return;
            }

            // 0 表示持续轮询，1-100 表示有限次数
            if (isNaN(pCount) || pCount < 0 || pCount > 100) {
                showToast(translateAppTextLocal('轮询次数必须在 0-100 次之间（0 表示持续轮询）'), 'error');
                return;
            }

            settings.enable_auto_polling = enablePolling;
            settings.polling_interval = pInterval;
            settings.polling_count = pCount;
            settings.email_notification_enabled = emailNotificationEnabled;
            settings.email_notification_recipient = emailNotificationRecipient;

            // [Phase 3] 简洁模式独立配置已合并，统一通过标准字段传递
            // 向后端同步 compact 字段（deprecated 兼容），镜像标准字段值
            settings.enable_compact_auto_poll   = enablePolling;
            settings.compact_poll_interval      = pInterval;
            settings.compact_poll_max_count     = pCount;

            // Telegram 推送配置
            const tgBotTokenEl = document.getElementById('telegramBotToken');
            const tgChatIdEl = document.getElementById('telegramChatId');
            const tgPollIntervalEl = document.getElementById('telegramPollInterval');
            const tgProxyUrlEl = document.getElementById('telegramProxyUrl');
            const tgBotToken = tgBotTokenEl ? tgBotTokenEl.value.trim() : '';
            const tgChatId = tgChatIdEl ? tgChatIdEl.value.trim() : '';
            const tgPollInterval = tgPollIntervalEl ? parseInt(tgPollIntervalEl.value) : NaN;
            const tgProxyUrl = tgProxyUrlEl ? tgProxyUrlEl.value.trim() : '';

            if (tgBotToken) {
                settings.telegram_bot_token = tgBotToken;
            }
            if (tgChatId !== undefined) {
                settings.telegram_chat_id = tgChatId;
            }
            if (!isNaN(tgPollInterval)) {
                if (tgPollInterval < 10 || tgPollInterval > 86400) {
                    showToast(translateAppTextLocal('Telegram 轮询间隔必须在 10-86400 秒之间'), 'error');
                    return;
                }
                settings.telegram_poll_interval = tgPollInterval;
            }
            settings.telegram_proxy_url = tgProxyUrl;

            // Webhook 通知配置
            const webhookEnabledEl = document.getElementById('webhookNotificationEnabled');
            const webhookUrlEl = document.getElementById('webhookNotificationUrl');
            const webhookTokenEl = document.getElementById('webhookNotificationToken');
            const webhookEnabled = webhookEnabledEl ? webhookEnabledEl.checked : false;
            const webhookUrl = webhookUrlEl ? webhookUrlEl.value.trim() : '';
            const webhookToken = webhookTokenEl ? webhookTokenEl.value.trim() : '';
            const webhookTokenMasked = webhookTokenEl ? (webhookTokenEl.dataset.maskedValue || '') : '';
            const webhookTokenIsSet = webhookTokenEl ? webhookTokenEl.dataset.isSet === 'true' : false;

            if (webhookEnabled && !webhookUrl) {
                showToast(translateAppTextLocal('启用 Webhook 通知时必须填写 Webhook URL'), 'error');
                return;
            }
            if (webhookUrl && !(webhookUrl.startsWith('http://') || webhookUrl.startsWith('https://'))) {
                showToast(translateAppTextLocal('Webhook URL 必须以 http:// 或 https:// 开头'), 'error');
                return;
            }
            settings.webhook_notification_enabled = webhookEnabled;
            settings.webhook_notification_url = webhookUrl;
            if (!(webhookTokenIsSet && webhookToken && webhookToken === webhookTokenMasked)) {
                settings.webhook_notification_token = webhookToken;
            }

            // Watchtower 一键更新配置
            const wtUrlEl = document.getElementById('watchtowerUrl');
            const wtTokenEl = document.getElementById('watchtowerToken');
            const wtUrl = wtUrlEl ? wtUrlEl.value.trim() : '';
            const wtToken = wtTokenEl ? wtTokenEl.value.trim() : '';
            settings.watchtower_url = wtUrl;
            if (wtToken) {
                settings.watchtower_token = wtToken;
            }
            
            // 更新方式配置
            const updateMethodRadio = document.querySelector('input[name="updateMethod"]:checked');
            if (updateMethodRadio) {
                settings.update_method = updateMethodRadio.value;
            }

            try {
                const response = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });

                const data = await response.json();

                if (data.success) {
                    applyPollingSettings(settings, { restart: true });
                    // [Phase 3] applyPollingSettings 已内含引擎同步，无需额外调用
                    // Drop soft Settings cache before refresh; refresh repopulates from server.
                    invalidateSettingsPageCache();
                    if (typeof invalidateAuditLogPageCache === 'function') {
                        invalidateAuditLogPageCache();
                    }
                    await refreshTempMailSettingsSnapshotFromServer();
                    await loadMailboxProviderCatalog(true);
                    // Temp domain options depend on saved provider credentials; drop soft cache.
                    if (typeof window.invalidateTempEmailOptionsCache === 'function') {
                        window.invalidateTempEmailOptionsCache();
                    }
                    // Settings modal is about to close: invalidate api-security panel caches
                    // so the next open soft-loads fresh data without a forced network burst now.
                    providerPreflightCache = null;
                    providerPreflightPromise = null;
                    providerPreflightState = { status: 'idle', probeNetwork: false, error: null };
                    operationalReadinessSnapshotCache = null;
                    operationalReadinessSnapshotPromise = null;
                    externalApiContractCheckCache = null;
                    externalApiContractCheckPromise = null;
                    externalApiContractCheckState = { status: 'idle', error: null };
                    showToast(pickApiMessage(data, '设置已保存，重启应用后生效', 'Settings saved successfully'), 'success');
                    hideSettingsModal();
                } else {
                    handleApiError(data, '保存设置失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('保存设置失败'), 'error');
            }
        }

        function switchSettingsTab(tabName) {
            const prevTab = currentSettingsTab;
            if (prevTab === tabName) return; // 同一 Tab 无操作
            currentSettingsTab = tabName;

            // 1. 基础 Tab 切走时，密码框有内容则清空 + Toast 提示
            if (prevTab === 'basic') {
                const pwdEl = document.getElementById('settingsPassword');
                if (pwdEl && pwdEl.value.trim()) {
                    pwdEl.value = '';
                    showToast(
                        translateAppTextLocal('密码修改未保存，如需修改请在「基础」Tab 重新输入后点击保存'),
                        'warning'
                    );
                }
            }

            // 2. 立即更新 Tab 按钮视觉状态
            document.querySelectorAll('.settings-tab').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tabName);
            });

            // 3. 立即更新 Tab 内容区显隐
            document.querySelectorAll('.settings-tab-pane').forEach(pane => {
                pane.classList.toggle('active', pane.id === `settings-tab-${tabName}`);
            });

            if (tabName === 'api-security') {
                // Snapshot-first paint of the full api-security surface set, then soft-load network panels.
                paintApiSecuritySurfacesFromSnapshot(externalApiSettingsSnapshot, 'ready');
                loadProviderPreflightSnapshot(false, false);
                loadExternalApiContractCheck(false);
                loadOperationalReadinessSnapshot(false);
            }
            if (tabName === 'temp-mail') {
                ensureTempMailSettingsTabReady()
                    .then(() => {
                        const pending = normalizeTempMailSettingsProviderName(
                            tempMailSettingsSnapshot?.temp_mail_provider
                            || getOperatorDefaultTempMailProvider()
                        );
                        applyTempMailSettingsSelection(pending);
                        if (isTempMailSettingsProviderMountBound()) {
                            renderTempMailProviderConfigPanel(pending);
                        }
                    })
                    .catch(() => {});
            }
            if (tabName === 'automation') {
                ensureAutomationSettingsTabReady();
            }

            // 4. 后台异步触发自动保存（基础 Tab 除外）
            if (prevTab !== 'basic') {
                autoSaveSettings(prevTab);
            }
        }

        // 自动保存逻辑（密码除外）
        async function autoSaveSettings(tabName) {
            if (tabName === 'basic') return;

            const settings = {};

            if (tabName === 'temp-mail') {
                const tempMailSettings = collectTempMailSettingsPayload();
                if (!tempMailSettings) return;
                Object.assign(settings, tempMailSettings);
            } else if (tabName === 'api-security') {
                const apiSecuritySettings = collectApiSecuritySettingsPayload();
                if (!apiSecuritySettings) return;
                Object.assign(settings, apiSecuritySettings);
            } else if (tabName === 'automation') {
                const enableScheduled = document.getElementById('enableScheduledRefresh')?.checked;
                if (enableScheduled !== undefined) settings.enable_scheduled_refresh = enableScheduled;

                const strategy = document.querySelector('input[name="refreshStrategy"]:checked')?.value;
                if (strategy) settings.use_cron_schedule = strategy === 'cron';

                const refreshDays = parseInt(document.getElementById('refreshIntervalDays')?.value);
                if (!isNaN(refreshDays) && refreshDays >= 1 && refreshDays <= 90) settings.refresh_interval_days = refreshDays;

                const refreshDelay = parseInt(document.getElementById('refreshDelaySeconds')?.value);
                if (!isNaN(refreshDelay) && refreshDelay >= 0 && refreshDelay <= 60) settings.refresh_delay_seconds = refreshDelay;

                const refreshCron = document.getElementById('refreshCron')?.value?.trim();
                if (refreshCron && strategy === 'cron') settings.refresh_cron = refreshCron;

                const enablePolling = document.getElementById('enableAutoPolling')?.checked;
                if (enablePolling !== undefined) {
                    settings.enable_auto_polling = enablePolling;
                    settings.enable_compact_auto_poll = enablePolling;
                }

                const pInterval = parseInt(document.getElementById('pollingInterval')?.value);
                if (!isNaN(pInterval) && pInterval >= 3 && pInterval <= 300) {
                    settings.polling_interval = pInterval;
                    settings.compact_poll_interval = pInterval;
                }

                const pCount = parseInt(document.getElementById('pollingCount')?.value);
                if (!isNaN(pCount) && pCount >= 0 && pCount <= 100) {
                    settings.polling_count = pCount;
                    settings.compact_poll_max_count = pCount;
                }

                const emailNotifEnabled = document.getElementById('emailNotificationEnabled')?.checked;
                if (emailNotifEnabled !== undefined) settings.email_notification_enabled = emailNotifEnabled;

                const emailRecipient = document.getElementById('emailNotificationRecipient')?.value?.trim();
                if (emailRecipient !== undefined) settings.email_notification_recipient = emailRecipient;

                const tgToken = document.getElementById('telegramBotToken')?.value?.trim();
                if (tgToken) settings.telegram_bot_token = tgToken;

                const tgChatId = document.getElementById('telegramChatId')?.value?.trim();
                if (tgChatId !== undefined) settings.telegram_chat_id = tgChatId;

                const tgPoll = parseInt(document.getElementById('telegramPollInterval')?.value);
                if (!isNaN(tgPoll) && tgPoll >= 10 && tgPoll <= 86400) settings.telegram_poll_interval = tgPoll;

                const tgProxyUrlQuick = document.getElementById('telegramProxyUrl')?.value?.trim();
                if (tgProxyUrlQuick !== undefined) settings.telegram_proxy_url = tgProxyUrlQuick;

                const webhookEnabledQuick = document.getElementById('webhookNotificationEnabled')?.checked;
                if (webhookEnabledQuick !== undefined) settings.webhook_notification_enabled = webhookEnabledQuick;

                const webhookUrlQuick = document.getElementById('webhookNotificationUrl')?.value?.trim();
                if (webhookUrlQuick !== undefined) settings.webhook_notification_url = webhookUrlQuick;

                const webhookTokenEl = document.getElementById('webhookNotificationToken');
                if (webhookTokenEl) {
                    const val = webhookTokenEl.value.trim();
                    const masked = webhookTokenEl.dataset.maskedValue || '';
                    const isSet = webhookTokenEl.dataset.isSet === 'true';
                    if (!(isSet && val && val === masked)) {
                        settings.webhook_notification_token = val;
                    }
                }
            }

            if (Object.keys(settings).length === 0) return;

            // 显示保存中圆点
            const prevTabBtn = document.querySelector(`.settings-tab[data-tab="${tabName}"]`);
            let dotEl = null;
            if (prevTabBtn) {
                dotEl = document.createElement('span');
                dotEl.className = 'tab-save-dot';
                prevTabBtn.appendChild(dotEl);
                prevTabBtn.classList.add('saving');
            }

            try {
                const resp = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                // 保存成功：移除圆点
                if (prevTabBtn) {
                    prevTabBtn.classList.remove('saving');
                    if (dotEl) dotEl.remove();
                }
                // Settings soft-load cache must not paint pre-save values on re-entry.
                invalidateSettingsPageCache();
                if (typeof invalidateAuditLogPageCache === 'function') {
                    invalidateAuditLogPageCache();
                }
                if (tabName === 'api-security') {
                    externalApiSettingsSnapshot = { ...externalApiSettingsSnapshot, ...settings };
                    renderProviderWorkbench(externalApiSettingsSnapshot, 'ready');
                    loadProviderPreflightSnapshot(true, false);
                    renderExternalApiCommandCenter(externalApiSettingsSnapshot, 'ready');
                    loadExternalApiContractCheck(true);
                    loadOperationalReadinessSnapshot(true);
                }
                if (tabName === 'temp-mail') {
                    await refreshTempMailSettingsSnapshotFromServer();
                    loadMailboxProviderCatalog(true);
                    if (typeof window.invalidateTempEmailOptionsCache === 'function') {
                        window.invalidateTempEmailOptionsCache();
                    }
                    // Preflight UI is api-security scoped; invalidate only so next visit soft-loads.
                    providerPreflightCache = null;
                    providerPreflightPromise = null;
                    providerPreflightState = { status: 'idle', probeNetwork: false, error: null };
                }
                if (tabName === 'automation') {
                    // Partial auto-save does not refetch full GET; force next loadSettings network.
                    // invalidateSettingsPageCache already ran above.
                }
            } catch (e) {
                // 保存失败：圆点变红保留 + 持久 Toast
                if (prevTabBtn) {
                    prevTabBtn.classList.remove('saving');
                    prevTabBtn.classList.add('save-error');
                }
                showToast(
                    translateAppTextLocal('保存失败，[' + tabName + '] Tab 的修改尚未保存，请手动重试'),
                    'error',
                    null,
                    true
                );
            }
        }

        // Provider 切换面板显隐
        function updateCfWorkerReadonlyFields(data) {
            if (Array.isArray(data.domains)) {
                const domains = data.domains.map(d => (typeof d === 'string' ? { name: d, enabled: true } : d));
                tempMailSettingsSnapshot.cf_worker_domains = domains;
                const domainsEl = document.querySelector('[data-temp-provider-setting="cf_worker_domains"]')
                    || document.getElementById('settingsCfWorkerDomains');
                if (domainsEl) {
                    domainsEl.value = formatTempProviderSettingValue(domains);
                    domainsEl.classList.add('readonly-field');
                    domainsEl.readOnly = true;
                }
            }
            if (data.default_domain) {
                tempMailSettingsSnapshot.cf_worker_default_domain = data.default_domain;
                const defaultDomainEl = document.querySelector('[data-temp-provider-setting="cf_worker_default_domain"]')
                    || document.getElementById('settingsCfWorkerDefaultDomain');
                if (defaultDomainEl) {
                    defaultDomainEl.value = data.default_domain;
                    defaultDomainEl.classList.add('readonly-field');
                    defaultDomainEl.readOnly = true;
                }
            }
            const syncTimeEl = document.getElementById('tempProviderActionHint') || document.getElementById('cfWorkerSyncTime');
            if (syncTimeEl) {
                syncTimeEl.textContent = `${translateAppTextLocal('上次同步')}：${new Date().toLocaleString()}`;
                syncTimeEl.style.display = 'block';
            }
        }

        // ==================== 自动轮询功能 ====================

        // 初始化轮询设置
        async function initPollingSettings() {
            try {
                // 优先使用 bootstrap 已缓存的轮询设置，避免首页阶段重复请求 /api/settings
                const cached = window.__bootstrapPollingSettings;
                if (cached) {
                    applyPollingSettings(cached);
                    delete window.__bootstrapPollingSettings;
                    return;
                }
                // 降级：走 Settings soft helper，与 loadSettings 共享 cache / in-flight。
                const data = await fetchSettingsPagePayload(false);
                if (data && data.success) {
                    applyPollingSettings(data.settings);
                }
            } catch (error) {
                console.error('初始化轮询设置失败:', error);
            }
        }

        // ==================== 工具函数 ====================

        // 相对时间格式化
