// split from state.js → i18n.js
        function getUiLanguage() {
            return window.getCurrentUiLanguage ? window.getCurrentUiLanguage() : 'zh';
        }

        function translateAppTextLocal(text) {
            return window.translateAppText ? window.translateAppText(text) : text;
        }

        function formatGroupDisplayName(name) {
            return translateAppTextLocal(String(name || '').trim());
        }

        function formatGroupDescription(description, fallback = '未填写说明') {
            const rawDescription = String(description || '').trim();
            return translateAppTextLocal(rawDescription || fallback);
        }

