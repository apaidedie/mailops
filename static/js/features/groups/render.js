// split from groups.js → render.js
        function renderGroupList(groups) {
            // #groupList is mailbox-sidebar chrome only.
            if (!isCurrentMailboxGroupsSurface()) {
                return;
            }
            const container = document.getElementById('groupList');
            if (!container) {
                return;
            }

            // 过滤掉临时邮箱分组（已有独立页面管理）
            const filteredGroups = groups.filter(g => !isTempMailboxGroup(g));

            if (filteredGroups.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon">📁</span>
                        <p class="ui-empty-title">${translateAppTextLocal('暂无分组')}</p>
                        <button type="button" class="btn btn-primary btn-sm" onclick="showAddGroupModal()">${translateAppTextLocal('添加分组')}</button>
                    </div>
                `;
                return;
            }

            container.innerHTML = filteredGroups.map(group => {
                const isSystem = group.is_system === 1;
                const isDefault = group.id === 1;

                return `
                    <div class="group-item ${currentGroupId === group.id ? 'active' : ''}"
                         data-group-id="${group.id}"
                         onclick="selectGroup(${group.id})">
                        <span class="group-color-dot" style="background-color: ${group.color || '#666'}"></span>
                        <span class="group-name">${escapeHtml(group.name)}</span>
                        <span class="badge-count">${group.account_count || 0}</span>
                        <div class="group-actions">
                            ${!isSystem ? `<button class="btn-icon" onclick="event.stopPropagation(); editGroup(${group.id})" title="${translateAppTextLocal('编辑')}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/></svg></button>` : ''}
                            ${!isDefault && !isSystem ? `<button class="btn-icon is-danger" onclick="event.stopPropagation(); deleteGroup(${group.id})" title="${translateAppTextLocal('删除')}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V5h6v2M8 7l1 12h6l1-12"/></svg></button>` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }

        // 选择分组
        function renderAccountList(accounts) {
            // Shared #accountList is standard-mailbox inventory chrome only.
            // Soft/catalog re-paints must not rewrite it off the mailbox surface.
            if (typeof currentPage !== 'undefined' && currentPage !== 'mailbox') {
                return;
            }
            if (typeof isTempEmailGroup !== 'undefined' && isTempEmailGroup) {
                return;
            }
            if (typeof mailboxViewMode !== 'undefined' && mailboxViewMode === 'unified') {
                return;
            }
            const container = document.getElementById('accountList');
            if (!container) {
                return;
            }

            if (accounts.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon" aria-hidden="true"></span>
                        <p class="ui-empty-title">${translateAppTextLocal('该分组暂无邮箱')}</p>
                        <button type="button" class="btn btn-primary btn-sm" onclick="showAddAccountModal()">${translateAppTextLocal('导入账号')}</button>
                    </div>
                `;
                const selectAllCheckbox = document.getElementById('selectAllCheckbox');
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = false;
                    selectAllCheckbox.indeterminate = selectedAccountIds.size > 0;
                }
                updateBatchActionBar();
                return;
            }

            const pagination = getAccountListMeta();
            const totalAccounts = Number(pagination.total_count || 0);
            const totalPages = Number(pagination.total_pages || 0);
            currentAccountPage = Number(pagination.page || 1);
            const pageAccounts = Array.isArray(accounts) ? accounts : [];
            const avatarGradients = [
                ['#2563EB', '#60A5FA'],  // tech blue
                ['#3A7D44', '#5BAF6A'],  // 翠绿→嫩绿
                ['#2E6B8A', '#4BA3CC'],  // 海蓝→天蓝
                ['#8B5E3C', '#C8963E'],  // 棕→琥珀金
                ['#7B4F9B', '#B77FD8'],  // 紫罗兰→薰衣草
                ['#C75050', '#E88080'],  // 朱红→浅红
                ['#2C7A7B', '#4DC9C9'],  // 青绿→薄荷
                ['#9B6B3E', '#D4A65A'],  // 赭石→沙金
            ];

            container.innerHTML = pageAccounts.map((acc, index) => {
                const isChecked = selectedAccountIds.has(acc.id);
                const initial = (acc.email || '?')[0].toUpperCase();
                const supportsTokenRefresh = isRefreshableOutlookAccount(acc);
                const isFailed = supportsTokenRefresh && acc.last_refresh_status === 'failed';
                const defaultMethodLabel = supportsTokenRefresh ? 'Graph' : 'IMAP';
                const gradient = avatarGradients[index % avatarGradients.length];
                const providerLabel = getProviderLabel(acc.provider || acc.account_type || 'outlook');
                const providerTagHtml = `<span class="account-provider-tag">${escapeHtml(providerLabel)}</span>`;
                const notificationEnabled = acc.notification_enabled !== undefined
                    ? !!acc.notification_enabled
                    : !!acc.telegram_push_enabled;
                const isCfPoolAccount = String(acc.provider || '').toLowerCase() === 'cloudflare_temp_mail';

                let tokenBadge = `<span class="badge badge-gray">IMAP</span>`;
                if (supportsTokenRefresh) {
                    tokenBadge = `<span class="badge badge-gray">– ${translateAppTextLocal('未知')}</span>`;
                    if (acc.token_status === 'valid') {
                        tokenBadge = `<span class="badge badge-green">✓ ${translateAppTextLocal('有效')}</span>`;
                    } else if (acc.token_status === 'invalid' || acc.token_status === 'expired') {
                        tokenBadge = `<span class="badge badge-red">✗ ${translateAppTextLocal('过期')}</span>`;
                    } else if (acc.token_status === 'expiring') {
                        tokenBadge = `<span class="badge badge-gold">⚠ ${translateAppTextLocal('即将过期')}</span>`;
                    }
                }

                return `
                <div class="account-card ${currentAccount === acc.email ? 'active' : ''}"
                     onclick="selectAccount('${escapeJs(acc.email)}')">
                    <div class="account-token-badge">${tokenBadge}</div>
                    <div class="account-card-top">
                        <input type="checkbox" class="account-select-checkbox" value="${acc.id}"
                               ${isChecked ? 'checked' : ''}
                               onclick="event.stopPropagation()"
                               onchange="event.stopPropagation(); handleAccountSelectionChange(${acc.id}, this.checked)">
                        <div class="account-avatar" style="background: linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})">${initial}</div>
                        <div class="account-info">
                            <div class="account-email ${isFailed ? 'is-failed' : ''}"
                                 onclick="event.stopPropagation(); copyEmail('${escapeJs(acc.email)}')"
                                 title="${escapeHtml(translateAppTextLocal('点击复制邮箱地址'))}">
                                ${escapeHtml(acc.email)}
                            </div>
                            ${acc.remark && acc.remark.trim() ? `<div class="account-remark">${escapeHtml(translateAppTextLocal('备注'))}: ${escapeHtml(acc.remark)}</div>` : ''}
                            <div class="account-tag-row">
                                ${providerTagHtml}
                                ${(acc.tags || []).map(tag => `<span class="tag" style="background-color:${tag.color};color:white;">${escapeHtml(tag.name)}</span>`).join('')}
                                ${notificationEnabled ? `<span class="tag tg-push-tag" onclick="event.stopPropagation(); toggleTelegramPush(${acc.id}, false)" title="${escapeHtml(translateAppTextLocal('点击关闭该邮箱通知参与'))}">${escapeHtml(translateAppTextLocal('通知'))}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="account-card-bottom">
                        <div class="account-meta">
                            <span class="account-api-tag">${acc.method || defaultMethodLabel}</span>
                            <span class="account-refresh-time">${formatRelativeTime(acc.last_refresh_at)}</span>
                            ${isFailed ? `<button class="btn btn-sm btn-danger account-error-btn" onclick="event.stopPropagation(); showRefreshError(${acc.id}, '${escapeJs(acc.last_refresh_error || '未知错误')}', '${escapeJs(acc.email)}', '${escapeJs(acc.account_type || 'outlook')}', '${escapeJs(acc.provider || 'outlook')}')">${escapeHtml(translateAppTextLocal('查看错误'))}</button>` : ''}
                        </div>
                        <div class="account-actions">
                            <button class="btn-icon ${notificationEnabled ? 'tg-push-active' : ''}" onclick="event.stopPropagation(); toggleTelegramPush(${acc.id}, ${!notificationEnabled})" title="${escapeHtml(translateAppTextLocal(notificationEnabled ? '该邮箱通知参与（已开启）' : '开启该邮箱通知参与'))}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9a6 6 0 0 1 12 0c0 7 3 7 3 7H3s3 0 3-7"/><path d="M10 19a2 2 0 0 0 4 0"/></svg></button>
                            <button class="btn btn-sm btn-accent account-code-btn" onclick="event.stopPropagation(); copyVerificationInfo('${escapeJs(acc.email)}', this)" title="${escapeHtml(translateAppTextLocal('验证码'))}">${escapeHtml(translateAppTextLocal('验证码'))}</button>
                            <button class="btn-icon" onclick="event.stopPropagation(); copyEmail('${escapeJs(acc.email)}')" title="${escapeHtml(translateAppTextLocal('复制'))}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="12" rx="1.5"/><path d="M6 16V5.5A1.5 1.5 0 0 1 7.5 4H15"/></svg></button>
                            ${isCfPoolAccount
                                ? `<button class="btn-icon is-disabled" disabled title="${escapeHtml(translateAppTextLocal('邮箱池管理的账号不支持编辑'))}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/></svg></button>`
                                : `<button class="btn-icon" onclick="event.stopPropagation(); showEditAccountModal(${acc.id})" title="${escapeHtml(translateAppTextLocal('编辑'))}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/></svg></button>`
                            }
                            ${isCfPoolAccount
                                ? `<button class="btn-icon is-disabled is-danger" disabled title="${escapeHtml(translateAppTextLocal('邮箱池管理的账号不支持手动删除'))}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V5h6v2M8 7l1 12h6l1-12"/></svg></button>`
                                : `<button class="btn-icon is-danger" onclick="event.stopPropagation(); deleteAccount(${acc.id}, '${escapeJs(acc.email)}')" title="${escapeHtml(translateAppTextLocal('删除'))}"><svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V5h6v2M8 7l1 12h6l1-12"/></svg></button>`
                            }
                        </div>
                    </div>
                </div>
            `}).join('');

            // ===== 分页控件：总账号数超过一页时显示 =====
            if (totalPages > 1) {
                const paginationEl = document.createElement('div');
                paginationEl.className = 'account-pagination';
                paginationEl.innerHTML = `
                    <button class="page-btn page-btn-prev"
                            onclick="goToAccountPage(${currentAccountPage - 1})"
                            ${currentAccountPage <= 1 ? 'disabled' : ''}>
                        ◀
                    </button>
                    <span class="page-info">
                        ${currentAccountPage} / ${totalPages} ${translateAppTextLocal('页')} &nbsp;·&nbsp; ${translateAppTextLocal('共')} ${totalAccounts} ${translateAppTextLocal('个账号')}
                    </span>
                    <button class="page-btn page-btn-next"
                            onclick="goToAccountPage(${currentAccountPage + 1})"
                            ${currentAccountPage >= totalPages ? 'disabled' : ''}>
                        ▶
                    </button>
                `;
                container.appendChild(paginationEl);
            }

            updateSelectAllCheckbox();
            updateBatchActionBar();
            // 如果有正在运行的轮询，重新显示轮询指示器（账号列表重渲染后会丢失绿点）
            if (typeof reapplyAllPollUI === 'function') {
                reapplyAllPollUI();
            }
        }

        // 跳转到指定账号分页
        function shouldPaintEditGroupForm(groupId) {
            const numericId = Number(groupId || 0);
            return !!numericId && editGroupPaintTargetId === numericId;
        }

        function rerenderAccountCaches() {
            if (!Array.isArray(accountsCache[currentGroupId])) {
                return;
            }
            // Only repaint shared mailbox inventory while on standard mailbox surface.
            if (typeof currentPage !== 'undefined' && currentPage !== 'mailbox') {
                return;
            }
            if (isTempEmailGroup) {
                return;
            }

            renderAccountList(accountsCache[currentGroupId]);
            if (typeof renderCompactAccountList === 'function') {
                renderCompactAccountList(accountsCache[currentGroupId]);
            }
            if (typeof renderCompactGroupStrip === 'function') {
                renderCompactGroupStrip(groups, currentGroupId);
            }
            updateSelectAllCheckbox();
            updateBatchActionBar();
        }

