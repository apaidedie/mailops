// split from overview.js → ui.js
function initOverview() {
    const page = document.getElementById('page-dashboard');
    if (!page) return;
    syncOverviewStaticText();

    if (!__overviewBound) {
        document.querySelectorAll('.ov-tab').forEach((button) => {
            button.addEventListener('click', () => switchOverviewTab(button.dataset.tab || 'summary'));
        });

        const refreshBtn = document.getElementById('ov-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshOverview);
        }

        window.addEventListener('ui-language-changed', () => {
            syncOverviewStaticText();
            updateOverviewRefreshTime();
            if (__overviewState.cache[__overviewState.activeTab]) {
                renderOverviewTab(__overviewState.activeTab, __overviewState.cache[__overviewState.activeTab]);
            }
        });

        window.addEventListener('overview-data-changed', (event) => {
            const detail = event && event.detail ? event.detail : {};
            invalidateOverviewCache(detail.tabs);

            const pageIsActive = !page.classList.contains('page-hidden');
            if (pageIsActive) {
                loadOverviewTab(__overviewState.activeTab || 'summary', true);
            }
        });
        __overviewBound = true;
    }

    const activeTab = __overviewState.activeTab || 'summary';
    // Soft-load path: switchOverviewTab reuses warm cache or starts a cold fetch.
    // Do not force-reload here — returning to Dashboard would re-hit /api/overview/*
    // even when the tab payload is already cached. Hard refresh remains on:
    // Refresh button, overview-data-changed (when page is active), and cold cache.
    switchOverviewTab(activeTab);
    updateOverviewRefreshTime();
}

function switchOverviewTab(tabId) {
    const targetTab = tabId || 'summary';
    __overviewState.activeTab = targetTab;

    document.querySelectorAll('.ov-tab').forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === targetTab);
    });
    document.querySelectorAll('.ov-tab-pane').forEach((pane) => {
        pane.classList.toggle('active', pane.dataset.tab === targetTab);
    });

    if (__overviewState.cache[targetTab]) {
        renderOverviewTab(targetTab, __overviewState.cache[targetTab]);
        return;
    }
    loadOverviewTab(targetTab);
}

function syncOverviewStaticText() {
    const textMap = {
        'ov-refresh-label': '最近刷新：'
    };
    Object.keys(textMap).forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = ovT(textMap[id]);
        }
    });

    const titleEl = document.getElementById('ov-page-title');
    if (titleEl) {
        titleEl.textContent = ovT('数据概览');
    }

    const refreshBtn = document.getElementById('ov-refresh-btn');
    if (refreshBtn) {
        refreshBtn.textContent = ovT('刷新');
    }

    const tabLabels = {
        summary: '总览',
        verification: '验证码提取',
        'external-api': '对外 API',
        pool: '邮箱池',
        activity: '系统活动'
    };
    document.querySelectorAll('.ov-tab').forEach((button) => {
        const labelEl = button.querySelector('.ov-tab-label');
        const tabId = button.dataset.tab || '';
        if (labelEl && tabLabels[tabId]) {
            labelEl.textContent = ovT(tabLabels[tabId]);
        }
    });
}

