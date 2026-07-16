// split from settings.js → tests_actions.js
        async function selectCronExample(cronExpr) {
            document.getElementById('refreshCron').value = cronExpr;
            await validateCronExpression();
        }

        // 验证 Cron 表达式
        async function validateCronExpression() {
            const cronExpr = document.getElementById('refreshCron').value.trim();
            const resultEl = document.getElementById('cronValidationResult');

            if (!cronExpr) {
                resultEl.innerHTML = '';
                return;
            }

            try {
                const response = await fetch('/api/settings/validate-cron', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cron_expression: cronExpr })
                });

                const data = await response.json();

                if (data.success && data.valid) {
                    const nextRun = formatUiDateTime(data.next_run, { fallback: data.next_run, includeSeconds: false });
                    resultEl.innerHTML = `
                        <div style="color: #28a745;">
                            ✓ ${translateAppTextLocal('表达式有效')}<br>
                            ${translateAppTextLocal('下次执行:')} ${nextRun}
                        </div>
                    `;
                } else {
                    resultEl.innerHTML = `
                        <div style="color: #dc3545;">
                            ✗ ${window.resolveApiErrorMessage ? window.resolveApiErrorMessage(data.error || data, '表达式无效', 'Invalid expression') : (data.error && data.error.message ? data.error.message : (data.error || '表达式无效'))}
                        </div>
                    `;
                }
            } catch (error) {
                resultEl.innerHTML = `
                    <div style="color: #dc3545;">
                        ✗ ${translateAppTextLocal('验证失败:')} ${error.message}
                    </div>
                `;
            }
        }

        // 保存设置
        async function testTelegramPush() {
            const btn = document.getElementById('btnTestTelegram');
            if (btn) { btn.disabled = true; btn.textContent = translateAppTextLocal('⏳ 发送中…'); }
            try {
                const resp = await fetch('/api/settings/telegram-test', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const data = await resp.json();
                if (data.success) {
                    showToast(pickApiMessage(data, '测试消息已发送，请检查 Telegram', 'Test message sent successfully. Please check Telegram'), 'success');
                } else {
                    handleApiError(data, '发送失败');
                }
            } catch (e) {
                showToast(`${translateAppTextLocal('请求失败')}: ${e.message}`, 'error');
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = translateAppTextLocal('发送测试消息'); }
            }
        }

        async function testTelegramProxy() {
            const btn = document.getElementById('btnTestTelegramProxy');
            const resultEl = document.getElementById('telegramProxyTestResult');
            const proxyInput = document.getElementById('telegramProxyUrl');
            const proxyUrl = proxyInput ? proxyInput.value.trim() : '';
            if (btn) { btn.disabled = true; btn.textContent = translateAppTextLocal('⏳ 测试中…'); }
            if (resultEl) resultEl.textContent = '';
            try {
                const resp = await fetch('/api/settings/test-telegram-proxy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_url: proxyUrl })
                });
                const data = await resp.json();
                if (data.ok) {
                    if (resultEl) {
                        resultEl.textContent = translateAppTextLocal('✅ 连通');
                        resultEl.style.color = 'var(--success, green)';
                    }
                } else {
                    if (resultEl) {
                        resultEl.textContent = `❌ ${data.message || translateAppTextLocal('失败')}`;
                        resultEl.style.color = 'var(--danger, red)';
                    }
                }
            } catch (e) {
                if (resultEl) { resultEl.textContent = `❌ ${e.message}`; resultEl.style.color = 'var(--danger, red)'; }
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = translateAppTextLocal('🔗 测试连通性'); }
            }
        }

        async function testWatchtower() {
            const btn = document.getElementById('btnTestWatchtower');
            const resultEl = document.getElementById('watchtowerTestResult');
            const urlInput = document.getElementById('watchtowerUrl');
            const tokenInput = document.getElementById('watchtowerToken');
            const wtUrl = urlInput ? urlInput.value.trim() : '';
            const wtToken = tokenInput ? tokenInput.value.trim() : '';
            if (btn) { btn.disabled = true; btn.textContent = translateAppTextLocal('⏳ 测试中…'); }
            if (resultEl) resultEl.textContent = '';
            try {
                const body = {};
                if (wtUrl) body.url = wtUrl;
                if (wtToken && !wtToken.startsWith('****')) body.token = wtToken;
                const resp = await fetch('/api/system/test-watchtower', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify(body)
                });
                const data = await resp.json();
                if (data.success) {
                    if (resultEl) { resultEl.textContent = translateAppTextLocal('✅ 连通正常'); resultEl.style.color = 'var(--success, green)'; }
                } else {
                    if (resultEl) { resultEl.textContent = `❌ ${data.message || translateAppTextLocal('失败')}`; resultEl.style.color = 'var(--danger, red)'; }
                }
            } catch (e) {
                if (resultEl) { resultEl.textContent = `❌ ${e.message}`; resultEl.style.color = 'var(--danger, red)'; }
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = translateAppTextLocal('🔗 测试连通性'); }
            }
        }

        async function testEmailNotification() {
            const btn = document.getElementById('btnTestEmailNotification');
            if (btn) { btn.disabled = true; btn.textContent = translateAppTextLocal('⏳ 发送中…'); }
            try {
                const resp = await fetch('/api/settings/email-test', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const data = await resp.json();
                if (data.success) {
                    showToast(pickApiMessage(data, '测试邮件已提交，请检查收件箱', 'Test email accepted. Please check your inbox'), 'success');
                } else {
                    handleApiError(data, '测试邮件发送失败');
                }
            } catch (e) {
                showToast(`${translateAppTextLocal('请求失败')}: ${e.message}`, 'error');
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = translateAppTextLocal('发送测试邮件'); }
            }
        }

        async function testWebhookNotification() {
            const btn = document.getElementById('btnTestWebhookNotification');
            if (btn) { btn.disabled = true; btn.textContent = translateAppTextLocal('⏳ 发送中…'); }
            try {
                const resp = await fetch('/api/settings/webhook-test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await resp.json();
                if (data.success) {
                    showToast(pickApiMessage(data, 'Webhook 测试成功', 'Webhook test succeeded'), 'success');
                } else {
                    handleApiError(data, 'Webhook 测试失败');
                }
            } catch (e) {
                showToast(`${translateAppTextLocal('请求失败')}: ${e.message}`, 'error');
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = translateAppTextLocal('测试 Webhook'); }
            }
        }

        async function testVerificationAiConfig() {
            const btn = document.getElementById('btnTestVerificationAi');
            const resultEl = document.getElementById('verificationAiTestResult');
            if (btn) { btn.disabled = true; btn.textContent = translateAppTextLocal('⏳ 测试中…'); }
            if (resultEl) {
                resultEl.textContent = translateAppTextLocal('正在验证已保存的 AI 配置连通性...');
                resultEl.style.color = 'var(--text-secondary, #666)';
            }

            try {
                const resp = await fetch('/api/settings/verification-ai-test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await resp.json();

                if (!data.success) {
                    handleApiError(data, 'AI 配置测试失败');
                    if (resultEl) {
                        resultEl.textContent = '❌ ' + translateAppTextLocal('AI 配置测试失败');
                        resultEl.style.color = 'var(--danger, red)';
                    }
                    return;
                }

                const probe = data.probe || {};
                if (data.ok) {
                    const parsed = probe.parsed_output || {};
                    const code = parsed.verification_code || '-';
                    const confidence = parsed.confidence || '-';
                    const latency = probe.latency_ms || 0;
                    const connectivityOnly = data.connectivity_ok && !data.contract_ok;
                    if (resultEl) {
                        if (connectivityOnly) {
                            resultEl.textContent = translateAppTextLocal(
                                '✅ 连通正常（' + latency + 'ms，HTTP ' + (probe.http_status || 200) + '）；契约校验未通过：' + (probe.error || '-')
                            );
                            resultEl.style.color = 'var(--warning, #ff8c00)';
                        } else {
                            resultEl.textContent = translateAppTextLocal(
                                '✅ 可用（' + latency + 'ms，code=' + code + '，confidence=' + confidence + '）'
                            );
                            resultEl.style.color = 'var(--success, green)';
                        }
                    }
                    showToast(
                        translateAppTextLocal(connectivityOnly ? 'AI 连通性测试成功' : 'AI 配置测试成功'),
                        'success'
                    );
                    return;
                }

                const message = probe.message || translateAppTextLocal('AI 配置测试失败');
                const detail = probe.error ? `（${probe.error}）` : '';
                if (resultEl) {
                    resultEl.textContent = `❌ ${message}${detail}`;
                    resultEl.style.color = 'var(--danger, red)';
                }
                showToast(message, 'warning');
            } catch (e) {
                const msg = `${translateAppTextLocal('请求失败')}: ${e.message}`;
                if (resultEl) {
                    resultEl.textContent = `❌ ${msg}`;
                    resultEl.style.color = 'var(--danger, red)';
                }
                showToast(msg, 'error');
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = translateAppTextLocal('🤖 测试 AI 配置'); }
            }
        }

        async function syncCfWorkerDomains() {
            const actionBtn = document.querySelector('[data-temp-provider-action="sync_domains"]');
            if (actionBtn) {
                await runTempProviderSettingsAction(actionBtn);
                return;
            }
            // Fallback direct call if schema action button is not mounted yet.
            const fakeBtn = document.createElement('button');
            fakeBtn.setAttribute('data-temp-provider-action', 'sync_domains');
            fakeBtn.setAttribute('data-temp-provider-action-method', 'POST');
            fakeBtn.setAttribute('data-temp-provider-action-endpoint', '/api/settings/cf-worker-sync-domains');
            fakeBtn.setAttribute('data-temp-provider-action-provider', 'cloudflare_temp_mail');
            fakeBtn.textContent = translateAppTextLocal('☁ 从 CF Worker 同步域名');
            await runTempProviderSettingsAction(fakeBtn);
        }

        // 同步成功后更新 CF Worker 只读字段（schema inputs preferred）
        async function syncCfWorkerDomains() {
            const actionBtn = document.querySelector('[data-temp-provider-action="sync_domains"]');
            if (actionBtn) {
                await runTempProviderSettingsAction(actionBtn);
                return;
            }
            // Fallback direct call if schema action button is not mounted yet.
            const fakeBtn = document.createElement('button');
            fakeBtn.setAttribute('data-temp-provider-action', 'sync_domains');
            fakeBtn.setAttribute('data-temp-provider-action-method', 'POST');
            fakeBtn.setAttribute('data-temp-provider-action-endpoint', '/api/settings/cf-worker-sync-domains');
            fakeBtn.setAttribute('data-temp-provider-action-provider', 'cloudflare_temp_mail');
            fakeBtn.textContent = translateAppTextLocal('☁ 从 CF Worker 同步域名');
            await runTempProviderSettingsAction(fakeBtn);
        }

        // 同步成功后更新 CF Worker 只读字段（schema inputs preferred）
