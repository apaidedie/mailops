// split from state.js → layout.js
        function getDefaultLayoutV2() {
            return {
                version: 2,
                sidebar: { collapsed: false },
                mailbox: { groupPanelWidth: 220, accountPanelWidth: 280 },
                tempEmails: { listPanelWidth: 300 }
            };
        }

        // 从后端读取布局状态
        async function loadLayoutFromServer() {
            try {
                const response = await fetch('/api/bootstrap');
                const data = await response.json();
                if (data.success && data.bootstrap) {
                    appBootstrapState = data.bootstrap;
                    window.__appBootstrap = data.bootstrap;
                    // 缓存轮询设置供 initPollingSettings 使用，避免重复请求
                    if (!window.__bootstrapPollingSettings) {
                        window.__bootstrapPollingSettings = data.bootstrap;
                    }
                    if (data.bootstrap.ui_layout_v2) {
                        const layout = data.bootstrap.ui_layout_v2;
                        if (layout.version === 2) {
                            uiLayoutV2 = layout;
                            return layout;
                        }
                    }
                }
            } catch (error) {
                console.warn('加载布局状态失败:', error);
            }
            return null;
        }

        // 迁移旧 localStorage key 到 ui_layout_v2
        function migrateOldLayoutKeys() {
            const migrated = { version: 2, sidebar: {}, mailbox: {}, tempEmails: {} };
            let needsMigration = false;

            try {
                // 迁移侧边栏折叠状态
                const oldSidebarCollapsed = localStorage.getItem('ol_sidebar_collapsed');
                if (oldSidebarCollapsed !== null) {
                    migrated.sidebar.collapsed = oldSidebarCollapsed === 'true';
                    needsMigration = true;
                } else {
                    migrated.sidebar.collapsed = false;
                }

                // 迁移列宽
                const oldColumnWidths = localStorage.getItem('ol_column_widths');
                if (oldColumnWidths) {
                    try {
                        const widths = JSON.parse(oldColumnWidths);
                        // groupPanel / accountPanel 的宽度迁移
                        if (widths.groupPanel) {
                            const w = parseInt(widths.groupPanel, 10);
                            if (!isNaN(w) && w > 0) {
                                migrated.mailbox.groupPanelWidth = w;
                                needsMigration = true;
                            }
                        }
                        if (widths.accountPanel) {
                            const w = parseInt(widths.accountPanel, 10);
                            if (!isNaN(w) && w > 0) {
                                migrated.mailbox.accountPanelWidth = w;
                                needsMigration = true;
                            }
                        }
                        // temp-emails 列宽迁移（如果有）
                        if (widths.tempEmailPanel) {
                            const w = parseInt(widths.tempEmailPanel, 10);
                            if (!isNaN(w) && w > 0) {
                                migrated.tempEmails.listPanelWidth = w;
                                needsMigration = true;
                            }
                        }
                    } catch (e) {
                        console.warn('解析旧列宽数据失败:', e);
                    }
                }

                // 设置默认值
                if (!migrated.mailbox.groupPanelWidth) migrated.mailbox.groupPanelWidth = 220;
                if (!migrated.mailbox.accountPanelWidth) migrated.mailbox.accountPanelWidth = 280;
                if (!migrated.tempEmails.listPanelWidth) migrated.tempEmails.listPanelWidth = 300;

            } catch (e) {
                console.warn('迁移布局状态失败:', e);
                return null;
            }

            return needsMigration ? migrated : null;
        }

        // 清理旧 localStorage key（可选，迁移成功后调用）
        function cleanupOldLayoutKeys() {
            try {
                localStorage.removeItem('ol_sidebar_collapsed');
                localStorage.removeItem('ol_column_widths');
            } catch (e) {}
        }

        // 保存布局状态到后端（带 debounce）
        function saveLayoutToServer() {
            if (!uiLayoutV2) return;

            if (layoutSaveDebounceTimer) {
                clearTimeout(layoutSaveDebounceTimer);
            }

            layoutSaveDebounceTimer = setTimeout(async () => {
                try {
                    await fetch('/api/settings', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ui_layout_v2: uiLayoutV2 })
                    });
                    if (typeof invalidateSettingsPageCache === 'function') {
                        invalidateSettingsPageCache();
                    }
                } catch (error) {
                    console.warn('保存布局状态失败:', error);
                }
            }, LAYOUT_SAVE_DEBOUNCE_MS);
        }

        // 初始化布局状态
        async function initLayoutState() {
            // 1. 先尝试从后端加载
            let layout = await loadLayoutFromServer();

            // 2. 如果后端没有有效布局，尝试迁移旧 key
            if (!layout) {
                const migrated = migrateOldLayoutKeys();
                if (migrated) {
                    uiLayoutV2 = migrated;
                    // 保存迁移结果到后端
                    try {
                        await fetch('/api/settings', {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ui_layout_v2: migrated })
                        });
                        // 迁移成功后清理旧 key
                        cleanupOldLayoutKeys();
                    } catch (e) {
                        console.warn('保存迁移布局失败:', e);
                    }
                } else {
                    // 使用默认布局
                    uiLayoutV2 = getDefaultLayoutV2();
                }
            } else {
                uiLayoutV2 = layout;
            }

            // 3. 应用布局状态
            applyLayoutState();
        }

        // 应用布局状态到 DOM
        function applyLayoutState() {
            if (!uiLayoutV2) return;

            // 应用侧边栏折叠状态
            const app = document.getElementById('app');
            if (app && uiLayoutV2.sidebar && uiLayoutV2.sidebar.collapsed) {
                app.classList.add('sidebar-collapsed');
            }

            // 应用 mailbox 列宽
            if (uiLayoutV2.mailbox) {
                const groupPanel = document.getElementById('groupPanel');
                const accountPanel = document.getElementById('accountPanel');
                if (groupPanel && uiLayoutV2.mailbox.groupPanelWidth) {
                    groupPanel.style.width = uiLayoutV2.mailbox.groupPanelWidth + 'px';
                }
                if (accountPanel && uiLayoutV2.mailbox.accountPanelWidth) {
                    accountPanel.style.width = uiLayoutV2.mailbox.accountPanelWidth + 'px';
                }
            }

            // 应用 temp-emails 列宽
            if (uiLayoutV2.tempEmails) {
                const tempEmailPanel = document.getElementById('tempEmailPanel');
                if (tempEmailPanel && uiLayoutV2.tempEmails.listPanelWidth) {
                    tempEmailPanel.style.width = uiLayoutV2.tempEmails.listPanelWidth + 'px';
                }
            }
        }

        // 更新布局状态中的侧边栏折叠
        function updateLayoutSidebarCollapsed(collapsed) {
            if (!uiLayoutV2) uiLayoutV2 = getDefaultLayoutV2();
            uiLayoutV2.sidebar.collapsed = collapsed;
            saveLayoutToServer();
        }

        // 更新布局状态中的列宽
        function updateLayoutColumnWidths() {
            if (!uiLayoutV2) uiLayoutV2 = getDefaultLayoutV2();

            // 读取 mailbox 列宽
            const groupPanel = document.getElementById('groupPanel');
            const accountPanel = document.getElementById('accountPanel');
            if (groupPanel && groupPanel.style.width) {
                const w = parseInt(groupPanel.style.width, 10);
                if (!isNaN(w) && w > 0) {
                    uiLayoutV2.mailbox.groupPanelWidth = w;
                }
            }
            if (accountPanel && accountPanel.style.width) {
                const w = parseInt(accountPanel.style.width, 10);
                if (!isNaN(w) && w > 0) {
                    uiLayoutV2.mailbox.accountPanelWidth = w;
                }
            }

            // 读取 temp-emails 列宽
            const tempEmailPanel = document.getElementById('tempEmailPanel');
            if (tempEmailPanel && tempEmailPanel.style.width) {
                const w = parseInt(tempEmailPanel.style.width, 10);
                if (!isNaN(w) && w > 0) {
                    uiLayoutV2.tempEmails.listPanelWidth = w;
                }
            }

            saveLayoutToServer();
        }

