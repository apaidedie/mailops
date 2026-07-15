// split globals from state.js
// Extracted from main.js lines 1-6282 (W3 frontend split)
// 全局状态
        let csrfToken = null;
        let csrfTokenRefreshPromise = null;
        // True when the in-flight CSRF token GET was started with force.
        let csrfTokenRefreshForce = false;
        let currentAccount = null;
        let currentGroupId = null;
        let currentEmails = [];
        let currentMethod = 'graph';
        let currentFolder = 'inbox';
        let isListVisible = true;
        let groups = [];
        let accountsCache = {};
        let editingGroupId = null;
        let selectedColor = '#B85C38';
        let isTempEmailGroup = false;
        let tempEmailGroupId = null;
        let isLoadingMore = false;
        let hasMoreEmails = true;
        let currentSkip = 0;
        let lastRefreshTime = null;
        let mailboxViewMode = ['standard', 'compact', 'unified'].includes(localStorage.getItem('ol_mailbox_view_mode'))
            ? localStorage.getItem('ol_mailbox_view_mode')
            : 'unified';
        let latestInvalidTokenDetectedCount = 0;
        let invalidTokenGovernanceCandidates = [];
        // Soft-load: true after a successful GET; reset/hide only clear UI, not this flag.
        let invalidTokenGovernanceCandidatesLoaded = false;
        let invalidTokenGovernanceLoadPromise = null;
        // True when the in-flight invalid-token candidates GET was started with forceRefresh.
        let invalidTokenGovernanceLoadForce = false;
        let selectedInvalidTokenCandidateIds = new Set();
        let mailboxProviderCatalogCache = null;
        let mailboxProviderDiagnosticsCache = null;
        let mailboxProviderDeploymentProfileCache = null;
        let mailboxProviderIntegrationGuideCache = null;
        let mailboxProviderIntegrationManifestCache = null;
        let mailboxProviderIntegrationQuickstartCache = null;
        let mailboxProviderSelectionPolicyCache = null;
        // Operator-facing default temp provider from /api/providers (bridge-canonical).
        let mailboxProviderDefaultTempMailProvider = '';
        let mailboxProviderCatalogPromise = null;
        // True when the in-flight catalog load was started with forceRefresh.
        let mailboxProviderCatalogLoadForce = false;
        let mailboxProviderConsoleFilter = 'all';
        let mailboxProviderIntegrationFilter = 'all';
        let mailboxProviderTemplateFormat = 'env';
        let mailboxProviderHealthState = {};
        let mailboxProviderHealthPending = new Set();
        let providerContractState = { catalog: [], plugins: [], lastUpdated: null };
        let externalApiSettingsSnapshot = {};
        let externalApiCommandRenderState = 'ready';
        let externalApiStarterMode = 'curl';
        let externalApiWorkflowKey = 'claim_pool_mailbox';
        let externalProviderRecipeKey = '';
        let externalApiContractCheckCache = null;
        let externalApiContractCheckPromise = null;
        // True when the in-flight contract-check GET was started with forceRefresh.
        let externalApiContractCheckLoadForce = false;
        let externalApiContractCheckState = { status: 'idle', error: null };
        let operationalReadinessSnapshotCache = null;
        let operationalReadinessSnapshotPromise = null;
        // True when the in-flight operational readiness GET was started with forceRefresh.
        let operationalReadinessSnapshotLoadForce = false;
        let providerPreflightCache = null;
        let providerPreflightPromise = null;
        // True when the in-flight preflight GET was started with force/probe.
        let providerPreflightLoadForce = false;
        let providerPreflightState = { status: 'idle', probeNetwork: false, error: null };
        let tempMailSettingsSnapshot = {};
        let tempMailSettingsDirtyKeys = new Set();
        let appBootstrapState = null;

        const EXTERNAL_API_CANONICAL_PREFIX = '/api/v1/external';
        const EXTERNAL_API_LEGACY_PREFIX = '/api/external';

