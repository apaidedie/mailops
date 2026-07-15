// split globals from overview.js
let __overviewBound = false;
const __overviewState = {
    activeTab: 'summary',
    cache: {},
    loading: {},
    // In-flight promises per tab so concurrent opens share one GET.
    loadPromises: {},
    // True when the in-flight load for a tab was started with forceReload.
    loadForce: {}
};

