// Extracted from main.js lines 7535-7549 (W3 frontend split)
        // ==================== 工具函数 ====================

        // HTML 转义
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 格式化日期
        function formatDate(dateStr) {
            return formatUiDateTime(dateStr, { fallback: dateStr || '' });
        }

