// split from overview.js → helpers.js
function ovT(text) {
    if (text === null || text === undefined || text === '') return '';
    if (typeof translateAppTextLocal === 'function') return translateAppTextLocal(text);
    if (window.translateAppText) return window.translateAppText(text);
    return String(text);
}

function ovLocale() {
    return (window.getCurrentUiLanguage && window.getCurrentUiLanguage() === 'en') ? 'en-US' : 'zh-CN';
}

