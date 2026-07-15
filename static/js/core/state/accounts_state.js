// split from state.js → accounts_state.js
        function formatAccountStatusLabel(status) {
            const normalized = String(status || 'active').trim().toLowerCase();
            const zhStatusMap = {
                active: '正常',
                inactive: '停用',
                disabled: '停用',
                paused: '停用'
            };
            return translateAppTextLocal(zhStatusMap[normalized] || normalized || '正常');
        }

        function isRefreshableOutlookAccount(accountLike) {
            const accountType = String(accountLike?.account_type || 'outlook').trim().toLowerCase();
            const provider = String(accountLike?.provider || 'outlook').trim().toLowerCase();
            return accountType !== 'imap' && provider === 'outlook';
        }

        function formatSelectedItemsLabel(count) {
            return translateAppTextLocal('已选 ' + count + ' 项');
        }

        const pickApiMessage = (payload, fallbackZh, fallbackEn) => (
            window.pickApiMessage ? window.pickApiMessage(payload, fallbackZh, fallbackEn) : (fallbackZh || fallbackEn || '')
        );

        const formatUiDateTime = (dateStr, options = {}) => (
            window.formatUiDateTime ? window.formatUiDateTime(dateStr, options) : (dateStr || '')
        );

        const formatUiRelativeTime = (dateStr, fallbackZh = '从未刷新', fallbackEn = 'Never refreshed') => (
            window.formatUiRelativeTime ? window.formatUiRelativeTime(dateStr, fallbackZh, fallbackEn) : (dateStr || fallbackZh)
        );

