// split from overview.js → misc.js
function ovLabelValue(label, value) {
    return `${ovT(label)} ${value}`;
}

function getOverviewContainer(tabId) {
    return document.getElementById(`ov-${tabId}-body`);
}

function normalizeOverviewCommandStatus(status) {
    const normalized = String(status || '').trim().toLowerCase();
    const allowed = new Set(['ready', 'needs_config', 'degraded', 'empty', 'unknown', 'restricted', 'available', 'unavailable', 'disabled', 'neutral']);
    return allowed.has(normalized) ? normalized : 'unknown';
}

function overviewCommandStatusTone(status) {
    const normalized = normalizeOverviewCommandStatus(status);
    if (normalized === 'ready' || normalized === 'available') return 'success';
    if (normalized === 'needs_config' || normalized === 'empty' || normalized === 'restricted' || normalized === 'disabled') return 'warn';
    if (normalized === 'degraded' || normalized === 'unavailable') return 'danger';
    return 'neutral';
}

function normalizeOverviewCommandPriority(priority) {
    const normalized = String(priority || '').trim().toLowerCase();
    if (normalized === 'high' || normalized === 'medium' || normalized === 'low') {
        return normalized;
    }
    return 'medium';
}

function normalizeExternalApiHealthStatus(status) {
    const normalized = String(status || '').trim().toLowerCase();
    if (normalized === 'healthy' || normalized === 'attention' || normalized === 'idle') {
        return normalized;
    }
    return 'idle';
}

function esc(value) {
    if (typeof escapeHtml === 'function') {
        return escapeHtml(String(value === null || value === undefined ? '' : value));
    }
    return String(value === null || value === undefined ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function totalValues(values) {
    return Object.keys(values || {}).reduce((sum, key) => sum + Number(values[key] || 0), 0);
}

function pickTimelineIcon(action) {
    const text = String(action || '').toLowerCase();
    if (text.includes('verification')) return 'CODE';
    if (text.includes('notification')) return 'MSG';
    if (text.includes('external')) return 'API';
    if (text.includes('pool') || text.includes('claim') || text.includes('release') || text.includes('complete')) return 'POOL';
    return 'LOG';
}

function pickToneGlyph(tone) {
    const key = String(tone || '').toLowerCase();
    if (key.includes('success')) return 'OK';
    if (key.includes('accent')) return 'DAY';
    if (key.includes('warn')) return 'WARN';
    if (key.includes('danger')) return 'RISK';
    return 'SYS';
}

