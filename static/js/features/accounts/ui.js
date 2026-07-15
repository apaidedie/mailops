// split from accounts.js → ui.js
        async function showExportModal() {
            document.getElementById('exportModal').classList.add('show');
            await loadExportGroupList();
        }

        // 隐藏导出邮箱模态框
        function hideExportModal() {
            document.getElementById('exportModal').classList.remove('show');
        }

        // Paint export modal group checkboxes from a groups array (no network).
        function isExportModalOpen() {
            const modal = document.getElementById('exportModal');
            return !!(modal && modal.classList.contains('show'));
        }

        // selectedIds: optional Set/array of string ids to restore after re-paint.
        function showExportVerifyModal() {
            document.getElementById('exportVerifyModal').classList.add('show');
            document.getElementById('exportVerifyPassword').value = '';
            document.getElementById('exportVerifyPassword').focus();
        }

        // 隐藏导出密码确认对话框
        function hideExportVerifyModal() {
            document.getElementById('exportVerifyModal').classList.remove('show');
            document.getElementById('exportVerifyPassword').value = '';
        }

        // 确认导出验证
