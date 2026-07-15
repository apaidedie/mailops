// split from settings.js → external_api.js
        function buildExternalApiKeysEditorItems(items) {
            if (!Array.isArray(items)) return [];

            return items.map((item, index) => {
                if (!item || typeof item !== 'object' || Array.isArray(item)) {
                    throw new Error(`第 ${index + 1} 项必须是对象`);
                }

                const normalized = {
                    name: item.name || '',
                    api_key: item.api_key || item.api_key_masked || '',
                    enabled: !(item.enabled === false || item.enabled === 'false' || item.enabled === 0 || item.enabled === '0'),
                    pool_access: item.pool_access === true || item.pool_access === 'true' || item.pool_access === 1 || item.pool_access === '1',
                    allowed_emails: Array.isArray(item.allowed_emails) ? item.allowed_emails : []
                };

                if (item.id !== undefined && item.id !== null && item.id !== '') {
                    normalized.id = item.id;
                }

                return normalized;
            });
        }

        function setExternalApiKeysEditor(items) {
            const editorEl = document.getElementById('settingsExternalApiKeysJson');
            if (!editorEl) return;

            const normalized = buildExternalApiKeysEditorItems(items);
            const prettyValue = normalized.length ? JSON.stringify(normalized, null, 2) : '';
            editorEl.value = prettyValue;
            editorEl.dataset.originalCanonical = JSON.stringify(normalized);

            const hintEl = document.getElementById('externalApiKeysJsonHint');
            if (!hintEl) return;

            if (normalized.length > 0) {
                hintEl.textContent = translateAppTextLocal(
                    '当前已配置 ' + normalized.length + ' 个多 Key。保留已有脱敏 api_key 表示不修改该 Key；清空后保存表示清空全部多 Key。'
                );
            } else {
                hintEl.textContent = translateAppTextLocal(
                    '用于按调用方维护多个 Key、邮箱范围授权和启停状态。保留已有脱敏 api_key 表示不修改该 Key；清空后保存表示清空全部多 Key。'
                );
            }
        }

        // Soft re-paint settings secret/multi-key hints from warm DOM/snapshot (language change).
        function generateExternalApiKey() {
            const input = document.getElementById('settingsExternalApiKey');
            if (!input) return;

            const currentValue = input.value.trim();
            if (currentValue) {
                const confirmed = confirm(translateAppTextLocal('当前已存在 API Key，是否覆盖？'));
                if (!confirmed) return;
            }

            const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
            const bytes = new Uint8Array(64);
            window.crypto.getRandomValues(bytes);
            const key = Array.from(bytes, b => alphabet[b % alphabet.length]).join('');

            input.value = key;
            showToast(translateAppTextLocal('已生成新的 API Key（尚未保存）'), 'success');
        }

        async function copyExternalApiKey() {
            const input = document.getElementById('settingsExternalApiKey');
            if (!input) return;

            const value = input.value || '';
            const maskedValue = input.dataset.maskedValue || '';
            const isSet = input.dataset.isSet === 'true';
            let copyValue = value.trim();

            if (isSet && copyValue && maskedValue && copyValue === maskedValue) {
                try {
                    const resp = await fetch('/api/settings/external-api-key/plaintext');
                    const data = await resp.json();
                    if (!resp.ok || !data.success || !data.api_key) {
                        throw new Error((data && (data.message || data.error?.message)) || '获取真实 API Key 失败');
                    }
                    copyValue = String(data.api_key || '').trim();
                } catch (error) {
                    showToast(`${translateAppTextLocal('请求失败')}: ${error.message}`, 'error');
                    return;
                }
            }

            if (!copyValue) {
                showToast(translateAppTextLocal('当前没有可复制的 API Key'), 'warning');
                return;
            }

            try {
                const ok = await copyTextToClipboard(copyValue);
                if (!ok) throw new Error('execCommand_copy_failed');
                showToast(translateAppTextLocal('内容已复制到剪贴板'), 'success');
            } catch (error) {
                showToast(translateAppTextLocal('复制失败，请手动复制'), 'error');
            }
        }

