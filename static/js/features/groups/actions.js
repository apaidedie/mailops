// split from groups.js → actions.js
        async function selectGroup(groupId) {
            currentGroupId = groupId;
            currentAccountPage = 1;  // 切换分组时重置到第 1 页
            currentAccountSearchQuery = '';

            // 切换分组时停止所有正在运行的轮询（避免跨分组轮询堆积）
            if (typeof stopAllPolls === 'function') {
                stopAllPolls();
            }

            // 清空搜索框
            const searchInput = document.getElementById('globalSearch');
            if (searchInput) {
                searchInput.value = '';
            }

            // 重置右侧邮件列 UI（清除上一个分组的残留状态）
            currentAccount = null;
            const accountBar = document.getElementById('currentAccountBar');
            if (accountBar) accountBar.style.display = 'none';
            const emailListEl = document.getElementById('emailList');
            if (emailListEl) {
                emailListEl.innerHTML = '<div class="empty-state"><span class="empty-icon">📬</span><p>' +
                    (typeof translateAppTextLocal === 'function'
                        ? translateAppTextLocal('请从左侧选择一个邮箱账号')
                        : '请从左侧选择一个邮箱账号') +
                    '</p></div>';
            }
            const detailSection = document.getElementById('emailDetailSection');
            if (detailSection) detailSection.style.display = 'none';
            const folderTabs = document.getElementById('folderTabs');
            if (folderTabs) folderTabs.style.display = 'none';
            const emailCount = document.getElementById('emailCount');
            if (emailCount) emailCount.textContent = '';
            const methodTag = document.getElementById('methodTag');
            if (methodTag) methodTag.style.display = 'none';

            // 检查是否是临时邮箱分组
            const group = groups.find(g => g.id === groupId);
            isTempEmailGroup = Boolean(group && isTempMailboxGroup(group));

            // 更新分组列表 UI
            document.querySelectorAll('.group-item').forEach(item => {
                item.classList.toggle('active', parseInt(item.dataset.groupId) === groupId);
            });
            if (typeof renderCompactGroupStrip === 'function') {
                renderCompactGroupStrip(groups, groupId);
            }

            // 更新邮箱面板标题
            if (group) {
                document.getElementById('currentGroupName').textContent = formatGroupDisplayName(group.name);
                document.getElementById('currentGroupColor').style.backgroundColor = group.color || '#666';

                // 更新导入邮箱时的默认分组
                const importSelect = document.getElementById('importGroupSelect');
                if (importSelect) {
                    importSelect.value = groupId;
                }
            }

            // 更新底部按钮
            updateAccountPanelFooter();

            // 加载该分组的邮箱
            if (isTempEmailGroup) {
                // 临时邮箱已有独立页面，跳转到专属页面管理
                navigate('temp-emails');
                return;
            } else {
                // 切换分组：加载账号列表（不启动批量轮询）
                await loadAccountsByGroup(groupId);
            }
        }

        // 更新账号面板底部按钮（新布局无独立footer，通过topbar按钮实现）
        function getSelectedTagFilterIds() {
            return Array.from(document.querySelectorAll('.tag-filter-checkbox:checked'))
                .map(cb => parseInt(cb.value, 10))
                .filter(tagId => Number.isInteger(tagId) && tagId > 0);
        }

        function updateGroupSelects() {
            // Soft loadGroups may run while import/edit modals are closed — only rewrite
            // open modal selects so hidden forms keep their previous option HTML stable.
            const selectSpecs = [
                { selectId: 'importGroupSelect', modalId: 'addAccountModal' },
                { selectId: 'editGroupSelect', modalId: 'editAccountModal' },
            ];
            selectSpecs.forEach(({ selectId, modalId }) => {
                const modal = document.getElementById(modalId);
                if (!modal || !modal.classList.contains('show')) {
                    return;
                }
                const select = document.getElementById(selectId);
                if (!select) {
                    return;
                }
                const currentValue = select.value;
                // 过滤掉临时邮箱分组（导入邮箱时不能选择临时邮箱分组）
                const filteredGroups = selectId === 'importGroupSelect'
                    ? groups.filter(g => g.name !== '临时邮箱')
                    : groups;

                select.innerHTML = filteredGroups.map(g =>
                    `<option value="${g.id}">${escapeHtml(g.name)}</option>`
                ).join('');
                // 恢复之前的选择
                if (currentValue && filteredGroups.find(g => g.id === parseInt(currentValue))) {
                    select.value = currentValue;
                } else if (currentGroupId && filteredGroups.find(g => g.id === currentGroupId)) {
                    select.value = currentGroupId;
                }
            });
        }

        // 显示添加分组模态框
        function showAddGroupModal() {
            // Cancel any pending edit paint so a late detail GET cannot clobber add form.
            editGroupPaintTargetId = null;
            editingGroupId = null;
            document.getElementById('groupModalTitle').textContent = translateAppTextLocal('添加分组');
            document.getElementById('groupName').value = '';
            document.getElementById('groupDescription').value = '';
            selectedColor = '#B85C38';
            document.querySelectorAll('.color-option').forEach(o => {
                o.classList.toggle('selected', o.dataset.color === selectedColor);
            });
            document.getElementById('customColorInput').value = selectedColor;
            document.getElementById('customColorHex').value = selectedColor;
            document.getElementById('groupProxyUrl').value = '';
            document.getElementById('groupVerificationCodeLength').value = '6-6';
            document.getElementById('groupVerificationCodeRegex').value = '';
            document.getElementById('addGroupModal').classList.add('show');
        }

        // 隐藏添加分组模态框
        function hideAddGroupModal() {
            editGroupPaintTargetId = null;
            document.getElementById('addGroupModal').classList.remove('show');
        }

        function applyEditGroupForm(group) {
            if (!group || typeof group !== 'object') return false;
            const numericId = Number(group.id || 0);
            if (!numericId) return false;

            editingGroupId = numericId;
            document.getElementById('groupModalTitle').textContent = translateAppTextLocal('编辑分组');
            document.getElementById('groupName').value = group.name || '';
            document.getElementById('groupDescription').value = group.description || '';
            selectedColor = group.color || '#B85C38';

            // 检查是否是预设颜色
            document.querySelectorAll('.color-option').forEach(o => {
                o.classList.toggle('selected', o.dataset.color === selectedColor);
            });

            // 更新自定义颜色输入框
            document.getElementById('customColorInput').value = selectedColor;
            document.getElementById('customColorHex').value = selectedColor;

            // 填充代理设置
            document.getElementById('groupProxyUrl').value = group.proxy_url || '';

            // 回填验证码提取策略
            document.getElementById('groupVerificationCodeLength').value = group.verification_code_length || '6-6';
            document.getElementById('groupVerificationCodeRegex').value = group.verification_code_regex || '';

            document.getElementById('addGroupModal').classList.add('show');
            return true;
        }

        // 编辑分组（soft-load warm groups cache; forceRefresh bypasses cache）
        async function editGroup(groupId, forceRefresh = false) {
            const numericId = Number(groupId || 0);
            if (!numericId) return false;
            const force = Boolean(forceRefresh);

            // Mark this group as the intended open target before any soft/network paint.
            editGroupPaintTargetId = numericId;

            // Soft open: warm list row already has full group fields from /api/groups.
            if (!force && Array.isArray(groups) && groups.length > 0) {
                const warmGroup = groups.find(g => Number(g && g.id) === numericId);
                if (
                    warmGroup
                    && shouldPaintEditGroupForm(warmGroup.id)
                    && applyEditGroupForm(warmGroup)
                ) {
                    return true;
                }
            }

            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so re-edit after save starts a true network GET.
            if (groupDetailLoadPromises[numericId]) {
                if (!force || groupDetailLoadForce[numericId]) {
                    return groupDetailLoadPromises[numericId];
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                delete groupDetailLoadPromises[numericId];
                delete groupDetailLoadForce[numericId];
            }

            groupDetailLoadForce[numericId] = force;
            const request = (async () => {
                try {
                    const response = await fetch(`/api/groups/${numericId}`);
                    const data = await response.json();

                    if (groupDetailLoadPromises[numericId] !== request) {
                        return false;
                    }
                    if (data.success && data.group) {
                        // Always warm list row when possible; apply only while paint target matches.
                        if (Array.isArray(groups) && data.group && data.group.id != null) {
                            const idx = groups.findIndex(g => Number(g && g.id) === numericId);
                            if (idx >= 0) {
                                groups[idx] = { ...groups[idx], ...data.group };
                            }
                        }
                        if (shouldPaintEditGroupForm(numericId)) {
                            applyEditGroupForm(data.group);
                        }
                        return true;
                    }
                    if (shouldPaintEditGroupForm(numericId)) {
                        showToast(translateAppTextLocal('加载分组信息失败'), 'error');
                    }
                    return false;
                } catch (error) {
                    if (groupDetailLoadPromises[numericId] !== request) {
                        return false;
                    }
                    if (shouldPaintEditGroupForm(numericId)) {
                        showToast(translateAppTextLocal('加载分组信息失败'), 'error');
                    }
                    return false;
                } finally {
                    if (groupDetailLoadPromises[numericId] === request) {
                        delete groupDetailLoadPromises[numericId];
                        delete groupDetailLoadForce[numericId];
                    }
                }
            })();

            groupDetailLoadPromises[numericId] = request;
            return request;
        }

        // 保存分组
        async function saveGroup() {
            const name = document.getElementById('groupName').value.trim();
            const description = document.getElementById('groupDescription').value.trim();
            const verificationCodeLength = document.getElementById('groupVerificationCodeLength')?.value?.trim() || '6-6';
            const verificationCodeRegex = document.getElementById('groupVerificationCodeRegex')?.value?.trim() || '';

            if (!name) {
                showToast(translateAppTextLocal('请输入分组名称'), 'error');
                return;
            }

            try {
                const url = editingGroupId ? `/api/groups/${editingGroupId}` : '/api/groups';
                const method = editingGroupId ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name,
                        description,
                        color: selectedColor,
                        proxy_url: document.getElementById('groupProxyUrl').value.trim(),
                        verification_code_length: verificationCodeLength,
                        verification_code_regex: verificationCodeRegex
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showToast(pickApiMessage(data, data.message, 'Group saved successfully'), 'success');
                    hideAddGroupModal();
                    loadGroups(true);
                } else {
                    handleApiError(data, '保存分组失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('保存失败'), 'error');
            }
        }

        // 删除分组
        async function deleteGroup(groupId) {
            if (!confirm('确定要删除该分组吗？分组下的邮箱将移至默认分组。')) {
                return;
            }

            try {
                const response = await fetch(`/api/groups/${groupId}`, { method: 'DELETE' });
                const data = await response.json();

                if (data.success) {
                    showToast(pickApiMessage(data, data.message, 'Group deleted successfully'), 'success');
                    // 清除缓存（含分页 meta，避免 soft-load 命中陈旧 queryKey）
                    invalidateAccountsCache(groupId);
                    // 如果删除的是当前选中的分组，切换到默认分组
                    if (currentGroupId === groupId) {
                        currentGroupId = 1;
                    }
                    loadGroups(true);
                } else {
                    handleApiError(data, '删除分组失败');
                }
            } catch (error) {
                showToast(translateAppTextLocal('删除失败'), 'error');
            }
        }

        // ==================== 全选功能 ====================

        // 全选/取消全选账号（当前分组）
        function toggleSelectAll() {
            const selectAllCheckbox = mailboxViewMode === 'compact'
                ? document.getElementById('compactSelectAllCheckbox')
                : document.getElementById('selectAllCheckbox');

            if (selectAllCheckbox.checked) {
                selectAllAccounts();
            } else {
                unselectAllAccounts();
            }
        }

        // 全选当前分组所有账号
        function selectAllAccounts() {
            const checkboxes = getActiveAccountCheckboxes();
            checkboxes.forEach(cb => {
                cb.checked = true;
                selectedAccountIds.add(parseInt(cb.value));
            });
            updateBatchActionBar();
            updateSelectAllCheckbox();
        }

        // 取消全选当前分组
        function unselectAllAccounts() {
            const checkboxes = getActiveAccountCheckboxes();
            checkboxes.forEach(cb => {
                cb.checked = false;
                selectedAccountIds.delete(parseInt(cb.value));
            });
            updateBatchActionBar();
            updateSelectAllCheckbox();
        }

        // 更新全选复选框状态（基于当前分组）
        function updateSelectAllCheckbox() {
            const checkboxes = getActiveAccountCheckboxes();
            const checkedCount = checkboxes.filter(cb => cb.checked).length;
            const selectAllCheckboxes = [
                document.getElementById('selectAllCheckbox'),
                document.getElementById('compactSelectAllCheckbox')
            ].filter(Boolean);

            selectAllCheckboxes.forEach(selectAllCheckbox => {
                if (checkboxes.length === 0) {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = selectedAccountIds.size > 0;
                } else if (checkedCount === 0) {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = selectedAccountIds.size > 0;
                } else if (checkedCount === checkboxes.length) {
                    selectAllCheckbox.checked = true;
                    selectAllCheckbox.indeterminate = false;
                } else {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = true;
                }
            });
        }

        // ==================== 验证码复制功能 ====================

