// Extracted from main.js lines 6328-6725 (W3 frontend split)
        // ==================== 主题 & 导航 ====================

        function applyTheme(theme) {
            document.documentElement.dataset.theme = theme;
            localStorage.setItem('ol_theme', theme);
            const btn = document.getElementById('themeToggleBtn');
            if (btn) {
                btn.textContent = theme === 'dark'
                    ? translateAppTextLocal('☀ 浅色模式')
                    : translateAppTextLocal('☾ 深色模式');
            }
        }

        function toggleTheme() {
            const current = document.documentElement.dataset.theme || 'light';
            applyTheme(current === 'dark' ? 'light' : 'dark');
        }

        function getDemoWorkspaceBootstrap() {
            const bootstrap = appBootstrapState || window.__appBootstrap || {};
            const demo = bootstrap && typeof bootstrap === 'object' ? bootstrap.demo_workspace : null;
            return demo && typeof demo === 'object' ? demo : { enabled: false };
        }

        function getDemoWorkspaceAction(actionKey) {
            const demo = getDemoWorkspaceBootstrap();
            const serverActions = Array.isArray(demo.quick_actions) ? demo.quick_actions : [];
            const merged = DEMO_WORKSPACE_ACTIONS.map(action => {
                const override = serverActions.find(item => String(item?.key || '') === action.key) || {};
                return { ...action, ...override, key: action.key };
            });
            return merged.find(action => action.key === actionKey) || null;
        }

        function renderDemoWorkspaceStrip() {
            const root = document.getElementById('demoWorkspaceStrip');
            if (!root) return;

            const demo = getDemoWorkspaceBootstrap();
            if (!demo.enabled) {
                root.hidden = true;
                root.innerHTML = '';
                return;
            }

            const databaseLabel = String(demo.database || 'output/demo/outlook-email-plus-demo.db');
            const actionButtons = DEMO_WORKSPACE_ACTIONS.map(action => {
                const label = translateAppTextLocal(action.label);
                return `<button type="button" class="demo-workspace-action" data-demo-workspace-action="${escapeHtml(action.key)}">${escapeHtml(label)}</button>`;
            }).join('');

            root.innerHTML = `
                <div class="demo-workspace-copy">
                    <span class="demo-workspace-kicker">${escapeHtml(translateAppTextLocal('Demo Workspace'))}</span>
                    <div class="demo-workspace-title">${escapeHtml(translateAppTextLocal('正在使用本地演示数据'))}</div>
                    <div class="demo-workspace-meta">${escapeHtml(translateAppTextLocal('Outlook、IMAP、临时邮箱、邮箱池和对外 API 均为可重置的合成样例'))} · <code>${escapeHtml(databaseLabel)}</code></div>
                </div>
                <div class="demo-workspace-actions" role="group" aria-label="${escapeHtml(translateAppTextLocal('Demo 快速入口'))}">
                    ${actionButtons}
                </div>
            `;
            root.hidden = false;
        }

        function handleDemoWorkspaceAction(actionKey) {
            const action = getDemoWorkspaceAction(String(actionKey || ''));
            if (!action) return;

            navigate(action.page || 'dashboard');
            if (action.page === 'dashboard' && action.tab && typeof switchOverviewTab === 'function') {
                switchOverviewTab(action.tab);
            }
            if (action.page === 'settings' && action.tab && typeof switchSettingsTab === 'function') {
                switchSettingsTab(action.tab);
            }
        }

        function applyAccountPanelDensityClasses(panel, width) {
            panel.classList.toggle('is-narrow', width < 240);
            panel.classList.toggle('is-compact', width < 170);
        }

        function navigate(page) {
            currentPage = page;
            // Hide all pages
            document.querySelectorAll('.page').forEach(p => p.classList.add('page-hidden'));
            const target = document.getElementById('page-' + page);
            if (target) {
                target.classList.remove('page-hidden');
                target.style.display = '';
            }
            // Update nav active state
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            const navBtn = document.querySelector(`.nav-item[data-page="${page}"]`);
            if (navBtn) navBtn.classList.add('active');
            // Update topbar
            updateTopbar(page);
            // Close mobile sidebar
            closeSidebar();
            // Load page data
            if (page === 'dashboard' && typeof initOverview === 'function') initOverview();
            if (page === 'mailbox') {
                if (mailboxViewMode === 'unified') {
                    if (typeof switchMailboxViewMode === 'function') {
                        switchMailboxViewMode('unified');
                    }
                } else {
                    if (groups.length === 0) {
                        loadGroups();
                    } else if (currentGroupId) {
                        loadAccountsByGroup(currentGroupId);
                    }
                    if (typeof switchMailboxViewMode === 'function') {
                        switchMailboxViewMode(mailboxViewMode);
                    }
                    syncAccountPanelDensityIfVisible();
                    scheduleAccountPanelDensitySync();
                }
            }
            // Soft-load on re-entry when page caches are warm (same pattern as overview).
            // Explicit create/delete/refresh handlers still call loaders with forceRefresh=true.
            if (page === 'temp-emails' && typeof loadTempEmails === 'function') loadTempEmails(false);
            if (page === 'settings') loadSettings();
            if (page === 'refresh-log') loadRefreshLogPage();
            if (page === 'pool-admin' && typeof loadPoolAdmin === 'function') loadPoolAdmin(false);
            if (page === 'audit') loadAuditLogPage();
        }

        function updateTopbar(page) {
            const titleEl = document.getElementById('topbarTitle');
            const subtitleEl = document.getElementById('topbarSubtitle');
            const actionsEl = document.getElementById('topbar-actions');
            const mailboxViewModeTemplate = document.getElementById('mailboxViewModeSwitcherTemplate');
            const titles = {
                'dashboard': ['数据概览', '统一邮箱服务运营看板'],
                'mailbox': ['统一邮箱工作台', '聚合账号库存、Provider 路由与外部会话入口'],
                'temp-emails': ['临时邮箱', '创建和管理临时邮箱'],
                'refresh-log': ['刷新日志', 'Token 刷新历史记录'],
                'settings': ['系统设置', '配置系统参数'],
                'pool-admin': ['号池管理', '邮箱池状态维护与调度'],
                'audit': ['审计日志', '系统操作记录']
            };
            const t = titles[page] || [page, ''];
            if (titleEl) titleEl.textContent = translateAppTextLocal(t[0]);
            if (subtitleEl) subtitleEl.textContent = translateAppTextLocal(t[1]);
            // Context actions
            if (actionsEl) {
                actionsEl.classList.remove('topbar-actions-compact');
                if (page === 'mailbox') {
                    const switcherHtml = mailboxViewModeTemplate ? mailboxViewModeTemplate.innerHTML.trim() : '';
                    const isCompactMode = mailboxViewMode === 'compact';
                    const isUnifiedMode = mailboxViewMode === 'unified';
                    actionsEl.innerHTML = (isCompactMode || isUnifiedMode) ? `
                        ${switcherHtml}
                    ` : `
                        ${switcherHtml}
                        <button class="btn-inline primary" onclick="showAddAccountModal()">＋ 添加账号</button>
                        <button class="btn-inline ghost" onclick="showExportModal()">📤 导出</button>
                        <button class="btn-inline ghost" onclick="showRefreshModal()">🔄 全量刷新 Token</button>
                    `;
                    actionsEl.classList.toggle('topbar-actions-compact', isCompactMode || isUnifiedMode);
                    if (subtitleEl) {
                        subtitleEl.textContent = translateAppTextLocal(
                            isUnifiedMode ? '统一查看账号库存、临时邮箱、Provider 路由与外部会话入口' : (isCompactMode ? '按分组查看账号摘要与验证码' : '管理账号与邮件详情')
                        );
                    }
                    const standardBtn = document.getElementById('mailboxStandardModeBtn');
                    const compactBtn = document.getElementById('mailboxCompactModeBtn');
                    const unifiedBtn = document.getElementById('mailboxUnifiedModeBtn');
                    if (standardBtn) {
                        standardBtn.classList.toggle('active', mailboxViewMode === 'standard');
                    }
                    if (compactBtn) {
                        compactBtn.classList.toggle('active', mailboxViewMode === 'compact');
                    }
                    if (unifiedBtn) {
                        unifiedBtn.classList.toggle('active', mailboxViewMode === 'unified');
                    }
                } else if (page === 'temp-emails') {
                    actionsEl.innerHTML = `
                        <button class="btn btn-sm btn-primary" onclick="generateTempEmail()">＋ 创建邮箱</button>
                    `;
                } else {
                    actionsEl.innerHTML = '';
                }
            }
        }

        function toggleSidebar() {
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                // Mobile: toggle drawer
                const sidebar = document.getElementById('sidebar');
                const backdrop = document.getElementById('sidebarBackdrop');
                sidebar.classList.toggle('mob-open');
                backdrop.classList.toggle('show');
            } else {
                // Desktop: toggle collapsed state
                const app = document.getElementById('app');
                app.classList.toggle('sidebar-collapsed');
                const collapsed = app.classList.contains('sidebar-collapsed');
                // 使用新的布局状态管理保存
                updateLayoutSidebarCollapsed(collapsed);
            }
        }

        function closeSidebar() {
            const sidebar = document.getElementById('sidebar');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (sidebar) sidebar.classList.remove('mob-open');
            if (backdrop) backdrop.classList.remove('show');
        }

        function logout() {
            if (!confirm(translateAppTextLocal('确认退出登录？'))) return;
            window.location.href = '/logout';
        }

        // ==================== 分组搜索过滤 ====================

        function filterGroups(query) {
            const items = document.querySelectorAll('#groupList .group-item');
            const q = query.toLowerCase();
            items.forEach(item => {
                const name = item.querySelector('.group-name');
                if (name && name.textContent.toLowerCase().includes(q)) {
                    item.style.display = '';
                } else {
                    item.style.display = q ? 'none' : '';
                }
            });
        }

        // ==================== 三栏拖拽调整 ====================

        function updateAccountPanelDensity() {
            const panel = document.getElementById('accountPanel');
            if (!panel) return;
            const width = panel.getBoundingClientRect().width;
            applyAccountPanelDensityClasses(panel, width);
        }

        function syncAccountPanelDensityIfVisible() {
            const page = document.getElementById('page-mailbox');
            const panel = document.getElementById('accountPanel');
            if (!page || !panel || page.classList.contains('page-hidden')) {
                return false;
            }

            const width = panel.getBoundingClientRect().width;
            if (width <= 0) {
                return false;
            }

            applyAccountPanelDensityClasses(panel, width);
            return true;
        }

        function scheduleAccountPanelDensitySync() {
            // 使用双层 rAF（以及 setTimeout fallback）刻意等待切页/拖拽后的布局回流完成，
            // 避免首次进入 mailbox 时按 0 宽或旧宽度错误计算紧凑模式。
            const runSync = () => {
                accountPanelDensitySyncHandle = null;
                syncAccountPanelDensityIfVisible();
            };

            if (accountPanelDensitySyncHandle !== null) {
                if (typeof cancelAnimationFrame === 'function') {
                    cancelAnimationFrame(accountPanelDensitySyncHandle);
                } else {
                    clearTimeout(accountPanelDensitySyncHandle);
                }
                accountPanelDensitySyncHandle = null;
            }

            if (typeof requestAnimationFrame === 'function') {
                accountPanelDensitySyncHandle = requestAnimationFrame(() => {
                    accountPanelDensitySyncHandle = requestAnimationFrame(runSync);
                });
                return;
            }

            accountPanelDensitySyncHandle = setTimeout(runSync, 0);
        }

        function initResizeHandles() {
            // 支持新的 .workspace-resizer 和旧的 .resize-handle 类名
            document.querySelectorAll('.workspace-resizer, .resize-handle').forEach(handle => {
                handle.addEventListener('mousedown', function(e) {
                    e.preventDefault();
                    const leftId = this.dataset.left;
                    const rightId = this.dataset.right;
                    const leftPanel = document.getElementById(leftId);
                    const rightPanel = document.getElementById(rightId);
                    if (!leftPanel) return;

                    this.classList.add('active');
                    document.body.style.cursor = 'col-resize';
                    document.body.style.userSelect = 'none';

                    const startX = e.clientX;
                    const startWidth = leftPanel.offsetWidth;

                    function onMouseMove(ev) {
                        const delta = ev.clientX - startX;
                        const newWidth = Math.max(120, Math.min(startWidth + delta, 500));
                        leftPanel.style.width = newWidth + 'px';
                        updateAccountPanelDensity();
                    }

                    function onMouseUp() {
                        handle.classList.remove('active');
                        document.body.style.cursor = '';
                        document.body.style.userSelect = '';
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                        // 使用新的布局状态管理保存列宽
                        updateLayoutColumnWidths();
                    }

                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                });
            });

            // 布局状态已在 initLayoutState() 中恢复，这里只需更新紧凑模式
            if (currentPage === 'mailbox') {
                syncAccountPanelDensityIfVisible();
                scheduleAccountPanelDensitySync();
            }
            window.addEventListener('resize', scheduleAccountPanelDensitySync, { passive: true });
        }

        // 平板断点 groups 栏展开/折叠 — 方案 B: 点击 ☰ 按钮后 groups 作为浮动面板覆盖在内容上方
        // 仅在平板断点(769-1024px)下有意义，按钮由 CSS .btn-toggle-groups 控制显隐
        // HTML 绑定: index.html 中 #btnToggleGroups onclick="toggleGroupsColumn()"
        function toggleGroupsColumn() {
            const groupPanel = document.getElementById('groupPanel');
            const btn = document.getElementById('btnToggleGroups');
            if (!groupPanel) return;
            const isExpanded = groupPanel.classList.toggle('groups-expanded');
            if (isExpanded) {
                groupPanel.style.display = 'flex';
                groupPanel.style.position = 'absolute';
                groupPanel.style.left = '60px';
                groupPanel.style.top = '52px';
                groupPanel.style.height = 'calc(100vh - 52px)';
                groupPanel.style.width = '220px';
                groupPanel.style.zIndex = '20';
                groupPanel.style.boxShadow = '4px 0 24px rgba(0,0,0,0.25)';
                groupPanel.style.borderRight = '1px solid var(--border)';
                groupPanel.style.background = 'var(--bg-card)';
            } else {
                groupPanel.style.cssText = '';
                handleResponsiveGroups();
            }
            if (btn) {
                btn.title = isExpanded ? translateAppTextLocal('收起分组') : translateAppTextLocal('展开分组');
            }
        }

        // resize 监听: 窗口尺寸变化时自动同步 groups 栏显隐状态
        // 与 CSS @media 断点(768/1024px) 配合，但通过 JS 内联 style 确保即时生效
        // 展开(groups-expanded)状态下不干预，避免覆盖用户操作
        function handleResponsiveGroups() {
            const groupPanel = document.getElementById('groupPanel');
            if (!groupPanel) return;
            const isExpanded = groupPanel.classList.contains('groups-expanded');
            // 展开状态下不干预
            if (isExpanded) return;
            const width = window.innerWidth;
            if (width > 768 && width <= 1024) {
                groupPanel.style.display = 'none';
            } else {
                groupPanel.style.cssText = '';
            }
        }
        window.addEventListener('resize', handleResponsiveGroups, { passive: true });

        // ==================== 邮件详情显示控制 ====================

        function showEmailDetailSection() {
            const section = document.getElementById('emailDetailSection');
            if (section) section.style.display = 'flex';
        }

        function hideEmailDetailSection() {
            const section = document.getElementById('emailDetailSection');
            if (section) section.style.display = 'none';
        }

        function stopRefresh() {
            // Placeholder for stopping a bulk refresh operation
            showToast(translateAppTextLocal('刷新已停止'), 'warn');
            const bar = document.getElementById('refreshProgressBar');
            if (bar) bar.style.display = 'none';
        }

