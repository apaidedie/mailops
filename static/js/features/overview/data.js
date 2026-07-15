// split from overview.js → data.js
function refreshOverview() {
    invalidateOverviewCache();
    loadOverviewTab(__overviewState.activeTab || 'summary', true);
    updateOverviewRefreshTime();
}

function invalidateOverviewCache(tabIds) {
    const targets = Array.isArray(tabIds) && tabIds.length
        ? tabIds.map((item) => String(item || '').trim()).filter(Boolean)
        : Object.keys(__overviewState.cache);

    if (!targets.length) {
        __overviewState.cache = {};
        __overviewState.loadPromises = {};
        __overviewState.loadForce = {};
        __overviewState.loading = {};
        return;
    }

    targets.forEach((tabId) => {
        delete __overviewState.cache[tabId];
        delete __overviewState.loadPromises[tabId];
        delete __overviewState.loadForce[tabId];
        __overviewState.loading[tabId] = false;
    });
}

async function loadOverviewTab(tabId, forceReload = false) {
    const targetTab = tabId || 'summary';
    const force = Boolean(forceReload);
    // Paint loading/result only while this tab is still the active overview surface
    // (rapid tab switches must not flash loading into a different pane).
    const isCurrentOverviewTab = () => (__overviewState.activeTab || 'summary') === targetTab;

    // Soft re-entry: always return warm cache; paint only for the active tab.
    if (!force && __overviewState.cache[targetTab]) {
        if (isCurrentOverviewTab()) {
            renderOverviewTab(targetTab, __overviewState.cache[targetTab]);
        }
        return __overviewState.cache[targetTab];
    }

    // Soft joins soft (or force) in-flight. Force joins only force in-flight;
    // force supersedes a soft in-flight so Refresh always starts a true network GET.
    if (__overviewState.loadPromises[targetTab]) {
        if (!force || __overviewState.loadForce[targetTab]) {
            return __overviewState.loadPromises[targetTab];
        }
        // Abandon soft in-flight bookkeeping; stale response identity check fails.
        delete __overviewState.loadPromises[targetTab];
        delete __overviewState.loadForce[targetTab];
        delete __overviewState.cache[targetTab];
    }

    const endpointMap = {
        summary: '/api/overview/summary',
        verification: '/api/overview/verification',
        'external-api': '/api/overview/external-api',
        pool: '/api/overview/pool',
        activity: '/api/overview/activity'
    };
    const endpoint = endpointMap[targetTab];
    if (!endpoint) return null;

    __overviewState.loading[targetTab] = true;
    __overviewState.loadForce[targetTab] = force;
    if (isCurrentOverviewTab()) {
        renderOverviewLoading(targetTab);
    }

    const request = (async () => {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            // If invalidateOverviewCache / force supersede cleared this tab mid-flight, do not repaint stale.
            if (__overviewState.loadPromises[targetTab] !== request) {
                return null;
            }
            // Always warm tab soft cache; paint only while still the active tab.
            __overviewState.cache[targetTab] = data || {};
            if (isCurrentOverviewTab()) {
                renderOverviewTab(targetTab, data || {});
                updateOverviewRefreshTime();
            }
            return __overviewState.cache[targetTab];
        } catch (error) {
            if (__overviewState.loadPromises[targetTab] !== request) {
                return null;
            }
            if (isCurrentOverviewTab()) {
                renderOverviewError(targetTab, error);
            }
            return null;
        } finally {
            if (__overviewState.loadPromises[targetTab] === request) {
                delete __overviewState.loadPromises[targetTab];
                delete __overviewState.loadForce[targetTab];
            }
            __overviewState.loading[targetTab] = false;
        }
    })();

    __overviewState.loadPromises[targetTab] = request;
    return request;
}

function updateOverviewRefreshTime() {
    const el = document.getElementById('ov-last-refresh');
    if (el) {
        el.textContent = new Date().toLocaleString(ovLocale(), { hour12: false });
    }
}

window.notifyOverviewDataChanged = function notifyOverviewDataChanged(tabIds, reason) {
    window.dispatchEvent(new CustomEvent('overview-data-changed', {
        detail: {
            tabs: Array.isArray(tabIds) ? tabIds : [],
            reason: reason || ''
        }
    }));
};
