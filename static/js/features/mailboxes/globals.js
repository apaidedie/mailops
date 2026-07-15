// split globals from mailboxes.js
        let unifiedMailboxState = {
            page: 1,
            pageSize: 50,
            loading: false,
            loaded: false,
            searchTimer: null,
            pendingReload: false,
            pendingForceRefresh: false,
            // Soft-load: last successful directory payload + request signature.
            // Re-entry with matching signature re-renders without network.
            directoryPayload: null,
            directorySignature: '',
            // In-flight directory GET identity; force supersedes soft by bumping seq.
            directoryLoadSeq: 0,
            // True when the in-flight directory GET was started with forceRefresh.
            directoryLoadForce: false,
            // Signature of the in-flight directory GET (for same-key join).
            directoryInFlightSignature: '',
            workspaceView: 'inbox',
            filters: {
                kind: 'all',
                status: 'all',
                readCapability: 'all',
                action: 'all',
                provider: 'all',
                sort: 'updated_desc',
                search: ''
            },
            contract: {},
            providerContext: {},
            providerFacets: [],
            pagination: {
                page: 1,
                page_size: 50,
                total_count: 0,
                total_pages: 0
            },
            items: [],
            preview: {
                selectedKey: '',
                selectedKind: '',
                selectedSourceId: 0,
                mailbox: null,
                messages: [],
                selectedMessageId: '',
                message: null,
                verification: null,
                loading: false,
                detailLoading: false,
                verificationLoading: false,
                error: '',
                detailError: '',
                verificationError: '',
                requestSeq: 0,
                detailSeq: 0,
                verificationSeq: 0,
                folder: 'inbox',
                skip: 0,
                top: 20,
                // Soft-load: last successful messages list signature (key|folder|skip|top).
                messagesSignature: '',
                // In-flight promise for concurrent message list loads.
                messagesLoadPromise: null,
                messagesLoadSignature: '',
                // True when the in-flight messages GET was started with force.
                messagesLoadForce: false,
                // Soft-load: last successful message detail signature (key|folder|messageId).
                detailSignature: '',
                // In-flight promise for concurrent message detail loads.
                detailLoadPromise: null,
                detailLoadSignature: '',
                // True when the in-flight detail GET was started with force.
                detailLoadForce: false,
                // Soft-load: last successful verification signature (key|folder).
                verificationSignature: '',
                // In-flight promise for concurrent verification loads.
                verificationLoadPromise: null,
                verificationLoadSignature: '',
                // True when the in-flight verification GET was started with force.
                verificationLoadForce: false
            }
        };

        const UNIFIED_SORT_PLACEHOLDER_DEFINITIONS = [
            { sort: 'updated_desc', label: '最近更新', label_en: 'Recently updated' }
        ];

        const UNIFIED_QUICK_VIEW_FILTER_KEYS = ['kind', 'status', 'readCapability', 'action', 'provider', 'sort', 'search'];
        const UNIFIED_QUICK_VIEW_DEFAULT_FILTERS = Object.freeze({
            kind: 'all',
            status: 'all',
            readCapability: 'all',
            action: 'all',
            provider: 'all',
            sort: 'updated_desc',
            search: ''
        });
        const UNIFIED_QUICK_VIEW_PRESETS = Object.freeze([
            {
                key: 'all',
                label: '全部邮箱',
                detail: '完整目录',
                filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS }
            },
            {
                key: 'accounts',
                label: '普通账号',
                detail: 'Outlook/IMAP',
                filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, kind: 'account' }
            },
            {
                key: 'temp',
                label: '临时邮箱',
                detail: 'Provider 邮箱',
                filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, kind: 'temp' }
            },
            {
                key: 'readable',
                label: '可读信',
                detail: '支持读取邮件',
                filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, action: 'read_messages' }
            },
            {
                key: 'attention',
                label: '需处理',
                detail: '停用或不可用',
                filters: { ...UNIFIED_QUICK_VIEW_DEFAULT_FILTERS, status: 'inactive' }
            }
        ]);

