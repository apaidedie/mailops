// ==================== 插件管理 ====================

const PluginManager = (() => {
    let _plugins = [];
    let _pluginsLoaded = false;
    let _pluginsLoadPromise = null;
    // True when the in-flight plugins GET was started with force/forceCatalogRefresh.
    let _pluginsLoadForce = false;
    let _cardExpanded = false;
    let _activeConfig = null;
    // Warm schema/config for open provider panel soft re-paint (language change).
    let _activeConfigFields = null;
    let _activeConfigValues = null;

    // Live i18n helper so language switches re-translate plugin chrome.
    function plT(text) {
        if (text === null || text === undefined || text === '') return '';
        if (typeof window.translateAppText === 'function') {
            return window.translateAppText(text);
        }
        return String(text);
    }

    // ── 公共 fetch 包装（Content-Type；CSRF 由 main.js 的 fetch 覆写层自动注入）──

    async function _post(url, body) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return { ok: resp.ok, status: resp.status, data: await resp.json() };
    }

    async function _get(url) {
        const resp = await fetch(url);
        return { ok: resp.ok, status: resp.status, data: await resp.json() };
    }

    function _getCheckedProviderRadio(group) {
        return Array.from(group.querySelectorAll('input[name="tempMailProvider"]')).find(el => el.checked) || null;
    }

    function _findProviderRadio(group, value) {
        return Array.from(group.querySelectorAll('input[name="tempMailProvider"]')).find(el => el.value === value) || null;
    }

    function _getPluginByName(name) {
        return _plugins.find(item => item && item.name === name) || null;
    }

    function _getInstalledPluginByName(name) {
        return _plugins.find(item => item && item.name === name && item.status === 'installed') || null;
    }

    function _getProviderConfigElements() {
        return {
            panel: document.getElementById('pluginProviderConfigPanel'),
            title: document.getElementById('pluginProviderConfigTitle'),
            body: document.getElementById('pluginProviderConfigBody'),
        };
    }

    function _resetProviderConfigPanel() {
        const { panel, title, body } = _getProviderConfigElements();
        if (panel) panel.style.display = 'none';
        if (title) title.textContent = plT('插件 Provider 配置');
        if (body) {
            body.innerHTML = '<div class="form-hint">' + plT('请选择一个已安装插件 Provider。') + '</div>';
        }
        _activeConfig = null;
        _activeConfigFields = null;
        _activeConfigValues = null;
    }

    function _scrollToProviderConfigPanel() {
        const { panel } = _getProviderConfigElements();
        if (panel && typeof panel.scrollIntoView === 'function') {
            panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // ── 折叠卡片 ─────────────────────────────────────────────────────────────

    function toggleCard() {
        _cardExpanded = !_cardExpanded;
        const body = document.getElementById('pluginManagerBody');
        const icon = document.getElementById('pluginManagerToggleIcon');
        if (body) body.style.display = _cardExpanded ? 'block' : 'none';
        if (icon) icon.classList.toggle('open', _cardExpanded);
        if (_cardExpanded) {
            // Use ensureLoaded so a successful empty install does not refetch forever.
            ensureLoaded().catch(() => {});
        }
    }

    // ── 加载插件列表 ──────────────────────────────────────────────────────────

    async function _refreshMailboxProviderCatalogFromPlugins(forceRefresh = false) {
        // Soft-load by default so boot soft-preload is reused. Force only after
        // install/uninstall/applyChanges when the provider registry may have changed.
        // Await settles the rewrite, then dual DOM injection can re-apply fallbacks
        // for installed-but-not-loaded plugins without being overwritten later.
        if (typeof loadMailboxProviderCatalog !== 'function') return;
        try {
            // Empty-array cache is "warm but empty"; force refill in that case too.
            const emptyWarmCache = (
                typeof mailboxProviderCatalogCache !== 'undefined'
                && Array.isArray(mailboxProviderCatalogCache)
                && mailboxProviderCatalogCache.length === 0
            );
            await loadMailboxProviderCatalog(Boolean(forceRefresh || emptyWarmCache));
        } catch (_err) {
            /* catalog soft-refresh must not break plugin manager UI */
        }
    }

    // Plugin manager list chrome only when the collapsible card body is expanded.
    // Temp-mail Settings soft-preload may call ensureLoaded/loadPlugins while collapsed.
    function shouldPaintPluginList() {
        return _cardExpanded === true;
    }

    async function loadPlugins(options = {}) {
        const opts = options && typeof options === 'object' ? options : {};
        const forceCatalogRefresh = opts.forceCatalogRefresh === true;
        const forceReload = opts.force === true || forceCatalogRefresh === true;
        // Soft re-entry: successful prior load returns warm list without /api/plugins
        // and without a loading flash. Paint list chrome only when card is expanded.
        if (!forceReload && _pluginsLoaded) {
            if (shouldPaintPluginList()) {
                const installedCount = _plugins.filter(p => p && p.status === 'installed').length;
                _renderPluginList(installedCount);
            }
            return _plugins;
        }
        // Soft joins any in-flight. Force joins only force in-flight;
        // force supersedes soft so refresh/install always starts a true network GET.
        if (_pluginsLoadPromise) {
            if (!forceReload || _pluginsLoadForce) {
                return _pluginsLoadPromise;
            }
            // Abandon soft in-flight bookkeeping; request identity blocks stale apply.
            _pluginsLoadPromise = null;
            _pluginsLoadForce = false;
        }

        const content = document.getElementById('pluginManagerContent');
        // Loading chrome only for a true network path while the manager card is open.
        if (content && shouldPaintPluginList()) {
            content.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-muted);font-size:0.85rem;">' + plT('加载中…') + '</div>';
        }

        _pluginsLoadForce = forceReload;
        const request = (async () => {
            try {
                const { ok, data } = await _get('/api/plugins');
                if (_pluginsLoadPromise !== request) {
                    return _plugins;
                }
                if (!ok || !data.success) throw new Error((data.error && data.error.message) || '加载失败');
                // Always warm plugin soft state + catalog side effects.
                _plugins = (data.data && data.data.plugins) || [];
                _pluginsLoaded = true;
                if (typeof updateProviderContractStateFromPlugins === 'function') {
                    updateProviderContractStateFromPlugins(_plugins);
                }
                if (shouldPaintPluginList()) {
                    _renderPluginList(data.data && data.data.installed_count != null ? data.data.installed_count : 0);
                }
                await _refreshMailboxProviderCatalogFromPlugins(forceCatalogRefresh);
                // Re-inject after catalog settles so plugin-only options survive catalog rewrite.
                _refreshProviderRadios();
                _refreshProviderSelect();
                return _plugins;
            } catch (err) {
                if (_pluginsLoadPromise !== request) {
                    return _plugins;
                }
                _pluginsLoaded = false;
                if (typeof updateProviderContractStateFromPlugins === 'function') {
                    updateProviderContractStateFromPlugins([]);
                }
                if (content && shouldPaintPluginList()) {
                    content.innerHTML = `<div class="plugin-load-error">${escapeHtml(plT('加载插件列表失败'))}：${escapeHtml(String(err.message || err))}</div>`;
                }
                throw err;
            } finally {
                if (_pluginsLoadPromise === request) {
                    _pluginsLoadPromise = null;
                    _pluginsLoadForce = false;
                }
            }
        })();

        _pluginsLoadPromise = request;
        try {
            return await request;
        } catch (_err) {
            return _plugins;
        }
    }

    // ── 渲染插件列表 ──────────────────────────────────────────────────────────

    function _renderPluginList(installedCount) {
        const content = document.getElementById('pluginManagerContent');
        if (!content) return;

        const badge = document.getElementById('pluginManagerBadge');
        if (badge) {
            badge.textContent = installedCount > 0 ? plT('已安装 ' + installedCount + ' 个') : plT('无插件');
            badge.className = installedCount > 0 ? 'badge badge-info' : 'badge';
            badge.style.display = 'inline-flex';
        }

        const installed = _plugins.filter(p => p.status === 'installed');
        const failed    = _plugins.filter(p => p.status === 'load_failed');
        const available = _plugins.filter(p => p.status === 'available');

        let html = `
            <div class="plugin-toolbar">
                <button class="btn btn-sm btn-secondary" onclick="PluginManager.loadPlugins({ force: true })">${plT('刷新')}</button>
                <button class="btn btn-sm btn-secondary" onclick="PluginManager.openCustomInstallModal()">${plT('自定义安装')}</button>
            </div>`;

        if (_plugins.length === 0) {
            html += '<div class="plugin-empty">' + plT('暂无可用插件') + '</div>';
        } else {
            html += '<div class="plugin-list">';
            [...installed, ...failed, ...available].forEach(p => { html += _renderPluginItem(p); });
            html += '</div>';
        }

        html += `
            <div class="plugin-apply-bar">
                <span class="plugin-apply-hint">${plT('安装、卸载或更新插件文件后，点击应用使插件生效')}</span>
                <button class="btn btn-sm btn-primary" onclick="PluginManager.applyChanges()">${plT('应用变更')}</button>
            </div>`;

        content.innerHTML = html;
    }

    function _renderPluginItem(p) {
        const name        = escapeHtml(p.name || '');
        const displayName = escapeHtml(p.display_name || p.name || '');
        const desc        = escapeHtml(p.description || '');
        const author      = escapeHtml(p.author || '');
        const version     = escapeHtml(p.version || '');
        const minVer      = escapeHtml(p.min_app_version || '');
        const status      = p.status;

        let badge = '';
        let actions = '';
        let statusClass = '';

        if (status === 'installed') {
            badge   = '<span class="plugin-status plugin-status--ok">' + plT('已安装') + '</span>';
            actions = `<button class="btn btn-sm btn-secondary" onclick="PluginManager.toggleConfig('${name}')">${plT('打开设置')}</button>
                       <button class="btn btn-sm btn-outline-danger" onclick="PluginManager.confirmUninstall('${name}','${displayName}')">${plT('卸载')}</button>`;
        } else if (status === 'load_failed') {
            badge       = '<span class="plugin-status plugin-status--fail">' + plT('加载失败') + '</span>';
            statusClass = 'plugin-item--fail';
            actions     = `<button class="btn btn-sm btn-outline-danger" onclick="PluginManager.confirmUninstall('${name}','${displayName}')">${plT('卸载')}</button>`;
        } else {
            badge   = '<span class="plugin-status plugin-status--avail">' + plT('可安装') + '</span>';
            actions = `<button class="btn btn-sm btn-primary" onclick="PluginManager.install('${name}')">${plT('安装')}</button>`;
        }

        const errorBlock = (status === 'load_failed' && p.error)
            ? `<div class="plugin-item-error">
                   ${escapeHtml(plT('加载失败'))}：${escapeHtml(String(p.error))}
               </div>` : '';

        return `
            <div class="plugin-item ${statusClass}" id="plugin-item-${name}">
                <div class="plugin-item-main">
                    <div class="plugin-item-body">
                        <div class="plugin-item-title">
                            ${displayName} ${badge}
                        </div>
                        ${desc ? `<div class="plugin-item-desc">${desc}</div>` : ''}
                        <div class="plugin-item-meta">
                            ${author  ? `<span>${author}</span>`  : ''}
                            ${version ? `<span>v${version}</span>` : ''}
                            ${minVer  ? `<span>${minVer}+</span>` : ''}
                        </div>
                    </div>
                    <div class="plugin-item-actions">${actions}</div>
                </div>
                ${errorBlock}
            </div>`;
    }

    // ── 配置面板 ──────────────────────────────────────────────────────────────

    function toggleConfig(name) {
        const group = document.querySelector('.provider-radio-group');
        const radio = group ? _findProviderRadio(group, name) : null;
        if (radio) {
            radio.checked = true;
        }

        if (typeof onTempMailProviderChange === 'function') {
            onTempMailProviderChange(name);
        } else {
            showProviderConfig(name);
        }
        _scrollToProviderConfigPanel();
    }

    async function showProviderConfig(name) {
        const { panel, title, body } = _getProviderConfigElements();
        if (!panel || !title || !body) return;
        const plugin = _getInstalledPluginByName(name);

        panel.style.display = 'block';
        if (!plugin) {
            title.textContent = plT('插件 Provider 配置');
            body.innerHTML = `<div class="form-hint">${escapeHtml(plT('未找到已安装的插件 Provider'))}：${escapeHtml(String(name || ''))}</div>`;
            _activeConfig = null;
            _activeConfigFields = null;
            _activeConfigValues = null;
            return;
        }

        _activeConfig = name;
        title.textContent = (plugin.display_name || plugin.name) + ' ' + plT('配置');
        body.innerHTML = '<div class="plugin-config-loading">' + plT('加载配置…') + '</div>';

        try {
            const [schemaRes, configRes] = await Promise.all([
                _get(`/api/plugins/${encodeURIComponent(name)}/config/schema`),
                _get(`/api/plugins/${encodeURIComponent(name)}/config`),
            ]);
            if (!schemaRes.ok) throw new Error((schemaRes.data.error && schemaRes.data.error.message) || plT('加载 schema 失败'));
            if (!configRes.ok) throw new Error((configRes.data.error && configRes.data.error.message) || plT('加载配置失败'));

            const fields = (schemaRes.data.data && schemaRes.data.data.config_schema && schemaRes.data.data.config_schema.fields) || [];
            const config = (configRes.data.data && configRes.data.data.config) || {};
            if (_activeConfig !== name) return;
            _activeConfigFields = fields;
            _activeConfigValues = config;
            body.innerHTML = _renderConfigForm(name, fields, config);
        } catch (err) {
            if (_activeConfig !== name) return;
            _activeConfigFields = null;
            _activeConfigValues = null;
            body.innerHTML = `<div class="plugin-load-error">${escapeHtml(plT('加载失败'))}：${escapeHtml(String(err.message || err))}</div>`;
        }
    }

    function _renderConfigForm(name, fields, currentConfig) {
        let fieldsHtml = '';
        for (const field of fields) {
            const key         = field.key || '';
            const label       = escapeHtml(field.label || key);
            const type        = field.type || 'text';
            const required    = field.required ? '<span class="form-req">*</span>' : '';
            const hint        = escapeHtml(field.hint || field.description || '');
            const placeholder = escapeHtml(field.placeholder || '');
            const rawVal      = currentConfig[key] !== undefined ? currentConfig[key] : (field.default !== undefined ? field.default : '');
            const currentVal  = escapeHtml(String(rawVal));
            const inputId     = `plugin-field-${escapeHtml(name)}-${escapeHtml(key)}`;

            let inputHtml = '';
            if (type === 'textarea') {
                inputHtml = `<textarea class="form-input plugin-config-textarea" id="${inputId}" placeholder="${placeholder}">${currentVal}</textarea>`;
            } else if (type === 'select' && Array.isArray(field.options)) {
                const opts = field.options.map(opt => {
                    const v = typeof opt === 'object' ? opt.value : opt;
                    const l = typeof opt === 'object' ? opt.label : opt;
                    return `<option value="${escapeHtml(String(v))}" ${String(v) === String(rawVal) ? 'selected' : ''}>${escapeHtml(String(l))}</option>`;
                }).join('');
                inputHtml = `<select class="form-input" id="${inputId}">${opts}</select>`;
            } else if (type === 'toggle') {
                const checked = (String(rawVal) === 'true' || String(rawVal) === '1') ? 'checked' : '';
                inputHtml = `<label class="form-check-row"><input type="checkbox" id="${inputId}" ${checked}><span>${label}</span></label>`;
            } else {
                const inputType = type === 'password' ? 'password' : type === 'number' ? 'number' : type === 'url' ? 'url' : 'text';
                inputHtml = `<input type="${inputType}" class="form-input" id="${inputId}" placeholder="${placeholder}" value="${currentVal}" autocomplete="off">`;
            }

            if (type !== 'toggle') {
                fieldsHtml += `
                    <div class="form-group plugin-config-field">
                        <label class="form-label" for="${inputId}">${label}${required}</label>
                        ${inputHtml}
                        ${hint ? `<div class="form-hint">${hint}</div>` : ''}
                    </div>`;
            } else {
                fieldsHtml += `
                    <div class="form-group plugin-config-field">
                        ${inputHtml}
                        ${hint ? `<div class="form-hint">${hint}</div>` : ''}
                    </div>`;
            }
        }

        const testId = `plugin-test-${escapeHtml(name)}`;
        return `
            <div class="plugin-config-form">
            ${fieldsHtml || '<div class="plugin-config-empty">' + plT('该插件无可配置项。') + '</div>'}
            <div id="${testId}" class="plugin-test-result" style="display:none;"></div>
            <div class="plugin-config-actions">
                <button class="btn btn-sm btn-secondary" onclick="PluginManager.testConnection('${escapeHtml(name)}','${testId}')">${plT('测试连接')}</button>
                <div class="plugin-config-actions-spacer"></div>
                <button class="btn btn-sm btn-primary" onclick="PluginManager.saveConfig('${escapeHtml(name)}')">${plT('保存')}</button>
            </div>
            </div>`;
    }

    // ── 安装 ──────────────────────────────────────────────────────────────────

    async function install(name, url) {
        const btn = document.querySelector(`#plugin-item-${name} .btn-primary`);
        if (btn) { btn.disabled = true; btn.textContent = plT('安装中…'); }

        try {
            const body = { name };
            if (url) body.url = url;
            const { ok, data } = await _post('/api/plugins/install', body);
            if (!ok || !data.success) {
                showToast((data.error && data.error.message) || plT('安装失败'), 'error');
                if (btn) { btn.disabled = false; btn.textContent = plT('安装'); }
                return;
            }
            showToast(data.message || plT('安装成功，请点击「应用变更」'), 'success');
            // Installed-but-not-loaded plugins still need DOM fallback inject; soft catalog is enough.
            await loadPlugins({ forceCatalogRefresh: false });
        } catch (err) {
            showToast(String(err.message || plT('安装失败')), 'error');
            if (btn) { btn.disabled = false; btn.textContent = plT('安装'); }
        }
    }

    // ── 卸载 ──────────────────────────────────────────────────────────────────

    function confirmUninstall(name, displayName) {
        // Pass Chinese source; window.confirm is wrapped to translateAppText.
        if (!confirm('确认卸载插件「' + displayName + '」？\n\n卸载后插件文件将被删除，关联邮箱记录保留。')) return;
        uninstall(name);
    }

    async function uninstall(name) {
        try {
            const { ok, data } = await _post(`/api/plugins/${encodeURIComponent(name)}/uninstall`, { clean_config: false });
            if (!ok || !data.success) {
                showToast((data.error && data.error.message) || plT('卸载失败'), 'error');
                return;
            }
            showToast(data.message || plT('插件已卸载'), 'success');
            if (_activeConfig === name) {
                _resetProviderConfigPanel();
            }
            // Registry may still list the plugin until applyChanges; force catalog after unload-on-disk.
            await loadPlugins({ forceCatalogRefresh: true });
        } catch (err) {
            showToast(String(err.message || plT('卸载失败')), 'error');
        }
    }

    // ── 保存配置 ──────────────────────────────────────────────────────────────

    async function saveConfig(name) {
        const config = {};
        const prefix = `plugin-field-${name}-`;
        document.querySelectorAll(`[id^="${prefix}"]`).forEach(el => {
            const key = el.id.slice(prefix.length);
            config[key] = el.type === 'checkbox' ? (el.checked ? 'true' : 'false') : el.value;
        });

        try {
            const { ok, data } = await _post(`/api/plugins/${encodeURIComponent(name)}/config`, { config });
            if (!ok || !data.success) {
                showToast((data.error && data.error.message) || plT('保存失败'), 'error');
                return;
            }
            showToast(plT('配置已保存'), 'success');
            // Plugin credentials may change domain options; drop soft options cache.
            if (typeof window.invalidateTempEmailOptionsCache === 'function') {
                window.invalidateTempEmailOptionsCache();
            }
            await showProviderConfig(name);
        } catch (err) {
            showToast(String(err.message || plT('保存失败')), 'error');
        }
    }

    // ── 测试连接 ──────────────────────────────────────────────────────────────

    async function testConnection(name, resultId) {
        const el = document.getElementById(resultId);
        if (el) {
            el.style.cssText = 'display:block;border-radius:6px;padding:0.5rem 0.75rem;font-size:0.78rem;margin-top:0.5rem;background:var(--bg-secondary);color:var(--text-muted);border:1px solid var(--border-light);';
            el.textContent = plT('⏳ 测试中…');
        }
        try {
            const { ok, data } = await _post(`/api/plugins/${encodeURIComponent(name)}/test-connection`, {});
            if (el) {
                if (ok && data.success) {
                    const latencyMs = data.data && data.data.latency_ms;
                    const latency = latencyMs
                        ? ' · ' + plT('延迟') + ' ' + latencyMs + 'ms'
                        : '';
                    el.innerHTML = '✅ ' + escapeHtml(plT('连接成功')) + escapeHtml(latency);
                    el.style.background = 'rgba(58,125,68,0.08)';
                    el.style.color = 'var(--clr-jade)';
                    el.style.border = '1px solid rgba(58,125,68,0.2)';
                } else {
                    const msg = (data.error && data.error.message) || plT('连接失败');
                    el.innerHTML = `❌ ${escapeHtml(msg)}`;
                    el.style.background = 'rgba(192,57,43,0.06)';
                    el.style.color = 'var(--clr-danger)';
                    el.style.border = '1px solid rgba(192,57,43,0.15)';
                }
            }
        } catch (err) {
            if (el) {
                el.innerHTML = `❌ ${escapeHtml(String(err.message || plT('请求失败')))}`;
                el.style.background = 'rgba(192,57,43,0.06)';
                el.style.color = 'var(--clr-danger)';
                el.style.border = '1px solid rgba(192,57,43,0.15)';
            }
        }
    }

    // ── 应用变更（热刷新）────────────────────────────────────────────────────

    async function applyChanges() {
        try {
            const { ok, data } = await _post('/api/system/reload-plugins', {});
            if (!ok || !data.success) {
                showToast((data.error && data.error.message) || plT('应用失败'), 'error');
                return;
            }
            const loaded = (data.data && data.data.loaded) || 0;
            const failedArr = (data.data && data.data.failed) || [];
            showToast(
                failedArr.length > 0
                    ? plT('已加载 ' + loaded + ' 个插件，' + failedArr.length + ' 个失败')
                    : plT('已应用，成功加载 ' + loaded + ' 个插件'),
                failedArr.length > 0 ? 'warning' : 'success'
            );
            // Runtime registry changed: force catalog refresh then re-apply plugin DOM fallbacks.
            await loadPlugins({ forceCatalogRefresh: true });
            if (typeof window.invalidateTempEmailOptionsCache === 'function') {
                window.invalidateTempEmailOptionsCache();
            }
        } catch (err) {
            showToast(String(err.message || plT('应用失败')), 'error');
        }
    }

    // ── 自定义安装模态框 ──────────────────────────────────────────────────────

    function openCustomInstallModal() {
        const modal = document.getElementById('pluginCustomInstallModal');
        if (modal) {
            modal.classList.add('show');
            modal.style.display = 'flex';
        }
        const nameEl = document.getElementById('customPluginName');
        const urlEl  = document.getElementById('customPluginUrl');
        if (nameEl) nameEl.value = '';
        if (urlEl)  urlEl.value  = '';
    }

    function closeCustomInstallModal() {
        const modal = document.getElementById('pluginCustomInstallModal');
        if (modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
    }

    async function customInstall() {
        const nameEl = document.getElementById('customPluginName');
        const urlEl  = document.getElementById('customPluginUrl');
        const name   = nameEl ? nameEl.value.trim() : '';
        const url    = urlEl  ? urlEl.value.trim()  : '';
        if (!name) { showToast(plT('请输入插件名称'), 'warning'); return; }
        if (!url)  { showToast(plT('请输入下载地址'), 'warning'); return; }
        // Pass Chinese source; window.confirm is wrapped to translateAppText.
        if (!confirm('⚠️ 安全提示\n\n您正在从第三方 URL 安装插件，代码将在服务器上执行。\n请仅安装来自可信来源的插件。\n\n继续安装「' + name + '」？')) return;
        closeCustomInstallModal();
        await install(name, url);
    }

    // ── Provider 集成 ────────────────────────────────────────────────────────

    function _refreshProviderRadios() {
        const group = document.querySelector('.provider-radio-group');
        if (!group) return;
        const previousValue = _getCheckedProviderRadio(group)?.value || '';
        const pendingValue = String(group.dataset.pendingProvider || '').trim();
        let injectedNewPluginRadio = false;
        // 移除已有插件 radio
        group.querySelectorAll('.provider-radio[data-plugin-radio="true"]').forEach(el => el.remove());
        _plugins.filter(p => p.status === 'installed').forEach(p => {
            const existingRadio = _findProviderRadio(group, p.name);
            const existingLabel = existingRadio ? existingRadio.closest('.provider-radio') : null;
            if (existingLabel) {
                // Catalog already rendered this provider; only tag source, do not overwrite labels.
                existingLabel.setAttribute('data-plugin', p.name);
                return;
            }
            const label = document.createElement('label');
            label.className = 'provider-radio';
            label.setAttribute('data-plugin', p.name);
            label.setAttribute('data-plugin-radio', 'true');
            label.innerHTML = `
                <input type="radio" name="tempMailProvider" value="${escapeHtml(p.name)}">
                <span class="provider-radio-label">
                    <span class="provider-name">${escapeHtml(p.display_name || p.name)}</span>
                    <span class="provider-desc">第三方插件 Provider</span>
                 </span>`;
            group.appendChild(label);
            injectedNewPluginRadio = true;
        });

        const fallbackRadio = _findProviderRadio(group, previousValue)
            || _findProviderRadio(group, pendingValue)
            || _getCheckedProviderRadio(group)
            || _findProviderRadio(group, 'legacy_bridge')
            || group.querySelector('input[name="tempMailProvider"]');
        if (fallbackRadio) {
            const nextValue = fallbackRadio.value || '';
            const selectionChanged = nextValue !== previousValue;
            fallbackRadio.checked = true;
            group.dataset.pendingProvider = '';
            // Avoid re-rendering schema panel (and wiping mid-edit dirty state) on every plugin list load.
            if ((selectionChanged || injectedNewPluginRadio) && typeof onTempMailProviderChange === 'function') {
                onTempMailProviderChange(nextValue);
            }
        }
    }

    function _refreshProviderSelect() {
        const sel = document.getElementById('tempEmailProviderSelect');
        if (!sel) return;
        const previousValue = sel.value;
        sel.querySelectorAll('option[data-plugin]').forEach(el => el.remove());
        _plugins.filter(p => p.status === 'installed').forEach(p => {
            const existing = Array.from(sel.options).find(opt => opt.value === p.name);
            if (existing) {
                // Catalog option text is authoritative when already present.
                existing.setAttribute('data-plugin', p.name);
                return;
            }
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.setAttribute('data-plugin', p.name);
            opt.textContent = `${p.display_name || p.name}`;
            sel.appendChild(opt);
        });

        const hasPrevious = Array.from(sel.options).some(opt => opt.value === previousValue);
        const nextValue = hasPrevious ? previousValue : (sel.options[0] ? sel.options[0].value : '');
        const selectionChanged = nextValue !== previousValue;
        sel.value = nextValue;
        // Only notify when selection actually changes; avoid thrashing create-temp UI.
        if (selectionChanged && typeof onTempEmailProviderChange === 'function') {
            onTempEmailProviderChange(sel.value);
        }
    }

    function init() {
        // Intentionally do not fetch /api/plugins on every page boot.
        // Load on temp-mail Settings tab, plugin-card expand, or explicit refresh/lifecycle actions.
    }

    async function ensureLoaded(options = {}) {
        const opts = options && typeof options === 'object' ? options : {};
        // Successful empty list is still loaded; only refetch on force or prior failure.
        if (_pluginsLoaded && opts.force !== true && opts.forceCatalogRefresh !== true) {
            // Soft re-entry: re-paint warm list only when plugin card is expanded.
            if (shouldPaintPluginList()) {
                const installedCount = _plugins.filter(p => p && p.status === 'installed').length;
                _renderPluginList(installedCount);
            }
            return _plugins;
        }
        await loadPlugins(opts);
        return _plugins;
    }

    // Soft-paint warm plugin list + open provider config chrome on language change (no network).
    function softPaintOnLanguageChange() {
        if (!_pluginsLoaded) return;
        const content = document.getElementById('pluginManagerContent');
        // Only re-paint when the manager card is expanded (list chrome is visible).
        if (!content || !shouldPaintPluginList()) return;
        const installedCount = _plugins.filter(p => p && p.status === 'installed').length;
        _renderPluginList(installedCount);

        const { panel, title, body } = _getProviderConfigElements();
        if (!panel || panel.style.display === 'none' || !title || !body) return;
        if (_activeConfig && Array.isArray(_activeConfigFields)) {
            const plugin = _getInstalledPluginByName(_activeConfig);
            title.textContent = ((plugin && (plugin.display_name || plugin.name)) || _activeConfig) + ' ' + plT('配置');
            // Preserve in-progress field edits by reading current DOM values when possible.
            const liveConfig = { ...(_activeConfigValues || {}) };
            (_activeConfigFields || []).forEach(field => {
                const key = field && field.key;
                if (!key) return;
                const inputId = `plugin-field-${_activeConfig}-${key}`;
                const el = document.getElementById(inputId);
                if (!el) return;
                if (el.type === 'checkbox') {
                    liveConfig[key] = el.checked ? 'true' : 'false';
                } else {
                    liveConfig[key] = el.value;
                }
            });
            _activeConfigValues = liveConfig;
            body.innerHTML = _renderConfigForm(_activeConfig, _activeConfigFields, liveConfig);
        } else if (!_activeConfig) {
            title.textContent = plT('插件 Provider 配置');
            body.innerHTML = '<div class="form-hint">' + plT('请选择一个已安装插件 Provider。') + '</div>';
        }
    }

    // ── Public API ────────────────────────────────────────────────────────────

    return {
        init,
        ensureLoaded,
        softPaintOnLanguageChange,
        toggleCard,
        loadPlugins,
        install,
        confirmUninstall,
        uninstall,
        toggleConfig,
        showProviderConfig,
        hideProviderConfig: _resetProviderConfigPanel,
        saveConfig,
        testConnection,
        applyChanges,
        openCustomInstallModal,
        closeCustomInstallModal,
        customInstall,
        hasInstalledProvider: name => !!_getInstalledPluginByName(name),
        getPluginByName: name => _getPluginByName(name),
    };
})();

window.PluginManager = PluginManager;
PluginManager.init();

// Language change soft-paints warm plugin list without network.
window.addEventListener('ui-language-changed', () => {
    try {
        if (window.PluginManager && typeof window.PluginManager.softPaintOnLanguageChange === 'function') {
            window.PluginManager.softPaintOnLanguageChange();
        }
    } catch (_e) {}
});
