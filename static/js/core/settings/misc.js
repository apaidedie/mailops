// split from settings.js → misc.js
        function assignSecretSettingFromInput(settings, settingKey, inputEl) {
            if (!settings || !settingKey || !inputEl) return;
            const value = inputEl.value.trim();
            const maskedValue = inputEl.dataset.maskedValue || '';
            const isSet = inputEl.dataset.isSet === 'true';
            if (!(isSet && value && value === maskedValue)) {
                settings[settingKey] = value;
            }
        }

        function pickDeploymentWarningText(warning, keyZh, keyEn) {
            if (!warning || typeof warning !== 'object') return '';
            const zh = String(warning[keyZh] || '').trim();
            const en = String(warning[keyEn] || '').trim();
            return getUiLanguage() === 'en' ? (en || zh) : (zh || en);
        }

        function normalizeDeploymentWarningSeverity(severityRaw) {
            const normalized = String(severityRaw || 'info').trim().toLowerCase();
            if (normalized === 'error' || normalized === 'warning' || normalized === 'info') return normalized;
            // 兼容后端可能返回的其它值
            return 'info';
        }

        function buildDeploymentWarningStyle(severity) {
            // 统一用 CSS 变量，兼容浅色/深色主题
            if (severity === 'error') {
                return {
                    color: 'var(--clr-danger)',
                    background: 'rgba(192,57,43,0.08)',
                    icon: '⛔'
                };
            }
            if (severity === 'warning') {
                return {
                    color: 'var(--clr-warn)',
                    background: 'rgba(230,126,34,0.08)',
                    icon: '⚠️'
                };
            }
            return {
                color: 'var(--clr-accent)',
                background: 'rgba(200,150,62,0.08)',
                icon: 'ℹ️'
            };
        }

        function renderDeploymentWarnings(deployment) {
            const container = document.getElementById('deploymentWarnings');
            if (!container) return;

            const warnings = Array.isArray(deployment && deployment.warnings) ? deployment.warnings : [];
            if (warnings.length === 0) {
                container.innerHTML = '';
                return;
            }

            const html = warnings.map((warning) => {
                const severity = normalizeDeploymentWarningSeverity(warning && warning.severity);
                const style = buildDeploymentWarningStyle(severity);

                const title = pickDeploymentWarningText(warning, 'message', 'message_en');
                const suggestion = pickDeploymentWarningText(warning, 'suggestion', 'suggestion_en');

                const suggestionHtml = suggestion
                    ? `<div style="margin-top:6px;font-size:0.78rem;color:var(--text-muted);">
                            <strong>${escapeHtml(translateAppTextLocal('处理建议'))}：</strong>${escapeHtml(suggestion)}
                       </div>`
                    : '';

                return `
                    <div class="form-hint" style="background:${style.background}; padding: 12px; border-radius: 6px; border-left: 3px solid ${style.color}; margin-bottom: 10px;">
                        <div style="display:flex; gap: 10px; align-items:flex-start;">
                            <div style="font-size: 1rem; line-height: 1.2;">${style.icon}</div>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: var(--text);">${escapeHtml(title)}</div>
                                ${suggestionHtml}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = html;
        }

        function applyDeploymentInfo(deployment, options = {}) {
            if (!deployment || typeof deployment !== 'object') return;
            // Always warm soft cache; paint Settings chrome only when requested/active.
            lastDeploymentInfo = deployment;
            const paint = options.paint !== false;
            if (!paint) {
                return;
            }
            renderDeploymentWarnings(lastDeploymentInfo);

            // 根据后端推荐的更新方式自动选择 radio
            const recommended = deployment.recommended_method;
            if (recommended) {
                const radios = document.getElementsByName('updateMethod');
                radios.forEach(radio => {
                    if (radio.value === recommended) {
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change'));
                    }
                });
            }
        }

        async function loadDeploymentInfo({ silent = true, forceRefresh = false } = {}) {
            const container = document.getElementById('deploymentWarnings');
            if (!container) return null;
            const force = Boolean(forceRefresh);
            // Paint warnings/update-method radios only while Settings surface is active
            // so a mid-flight navigate away cannot rewrite Settings form state.
            const paintSettingsChrome = () => (
                typeof isSettingsSurfaceActive === 'function' ? isSettingsSurfaceActive() : true
            );

            // Soft re-entry: always return warm cache; paint only on Settings surface.
            if (!force && lastDeploymentInfo) {
                if (paintSettingsChrome()) {
                    applyDeploymentInfo(lastDeploymentInfo);
                }
                return lastDeploymentInfo;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so explicit refresh starts a true network GET.
            if (deploymentInfoLoadPromise) {
                if (!force || deploymentInfoLoadForce) {
                    return deploymentInfoLoadPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                deploymentInfoLoadPromise = null;
                deploymentInfoLoadForce = false;
            }

            deploymentInfoLoadForce = force;
            const request = (async () => {
                try {
                    // Network path still bypasses browser HTTP cache for freshness.
                    const res = await fetch('/api/system/deployment-info', { cache: 'no-store' });
                    if (!res.ok) return null;
                    const data = await res.json();
                    // If force supersede abandoned this request, do not apply stale deployment.
                    if (deploymentInfoLoadPromise !== request) {
                        return lastDeploymentInfo;
                    }
                    if (!data || !data.success || !data.deployment) {
                        if (!silent && paintSettingsChrome()) {
                            handleApiError(data || { success: false, error: '请求失败' }, '请求失败');
                        }
                        return null;
                    }

                    // Always warm soft cache; paint only while Settings surface is active.
                    applyDeploymentInfo(data.deployment, { paint: paintSettingsChrome() });
                    return lastDeploymentInfo;
                } catch (e) {
                    if (deploymentInfoLoadPromise !== request) {
                        return lastDeploymentInfo;
                    }
                    if (!silent && paintSettingsChrome()) {
                        showToast(`${translateAppTextLocal('请求失败')}: ${e.message}`, 'error');
                    }
                    return null;
                }
            })();

            deploymentInfoLoadPromise = request;
            try {
                return await request;
            } finally {
                if (deploymentInfoLoadPromise === request) {
                    deploymentInfoLoadPromise = null;
                    deploymentInfoLoadForce = false;
                }
            }
        }

        // 切换刷新策略
        function formatRelativeTime(timestamp) {
            return formatUiRelativeTime(timestamp, '从未刷新', 'Never refreshed');
        }

