// split from accounts.js → render.js
        function shouldPaintEditAccountForm(accountId) {
            const key = String(accountId || '').trim();
            return !!key && editAccountPaintTargetId === key;
        }

        function paintExportGroupList(source, selectedIds = null) {
            // Soft loadGroups may finish after the export modal is closed — do not rewrite list.
            if (!isExportModalOpen()) return;
            const container = document.getElementById('exportGroupList');
            if (!container) return;

            const selected = selectedIds instanceof Set
                ? selectedIds
                : new Set(
                    Array.isArray(selectedIds)
                        ? selectedIds.map(String)
                        : Array.from(document.querySelectorAll('.export-group-checkbox:checked'))
                            .map(cb => String(cb.value))
                );

            const list = Array.isArray(source) ? source : [];
            if (list.length === 0) {
                container.innerHTML = `<div class="empty-state"><p>${translateAppTextLocal('暂无分组')}</p></div>`;
                return;
            }

            container.innerHTML = list.map(group => {
                const id = String(group.id);
                const checked = selected.has(id) ? 'checked' : '';
                const name = (typeof formatGroupDisplayName === 'function')
                    ? formatGroupDisplayName(group.name)
                    : translateAppTextLocal(String(group.name || '').trim());
                return `
                        <label style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; cursor: pointer; border-radius: var(--radius); transition: background-color 0.15s;"
                               onmouseover="this.style.backgroundColor='var(--bg-hover)'"
                               onmouseout="this.style.backgroundColor='transparent'">
                            <input type="checkbox" class="export-group-checkbox" value="${escapeHtml(id)}" ${checked}>
                            <span style="display: flex; align-items: center; gap: 8px; flex: 1;">
                                <span class="group-color-dot" style="background-color: ${escapeHtml(group.color || '#666')}"></span>
                                <span style="font-size: 0.9rem; color: var(--text);">${escapeHtml(name)}</span>
                            </span>
                            <span class="badge-count">${group.account_count || 0}</span>
                        </label>
                    `;
            }).join('');
        }

        // Soft re-paint open export modal from warm groups (language change / soft re-entry).
        function softPaintExportGroupListIfOpen() {
            if (!isExportModalOpen()) return;
            if (!(Array.isArray(groups) && groups.length > 0)) return;
            paintExportGroupList(groups);
        }

        // 加载导出分组列表
