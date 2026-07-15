// Extracted from main.js lines 6283-6327 (W3 frontend split)
        // ==================== 标准模式轮询指示器 ====================
        // 在标准模式下，在账号卡片邮箱地址旁显示/隐藏轮询绿点。
        // 由统一轮询引擎通过 UI 回调调用（mailbox_compact.js 中根据 mailboxViewMode 分发）。

        function showStandardPollDot(email) {
            if (!email) return;
            var allCards = document.querySelectorAll('#accountList .account-card');
            allCards.forEach(function(card) {
                var emailEl = card.querySelector('.account-email');
                if (emailEl && emailEl.textContent.trim() === email) {
                    // 在 .account-info 容器中添加状态行（避免 .account-email 的 overflow:hidden 裁剪）
                    var infoEl = card.querySelector('.account-info');
                    if (infoEl && !infoEl.querySelector('.standard-poll-status')) {
                        var statusEl = document.createElement('div');
                        statusEl.className = 'standard-poll-status';
                        statusEl.innerHTML = '<span class="standard-poll-dot"></span>' + translateAppTextLocal('轮询监听中…');
                        infoEl.appendChild(statusEl);
                    }
                    // 给卡片加上边框高亮
                    card.classList.add('standard-poll-active');
                }
            });
        }

        function hideStandardPollDot(email) {
            if (email) {
                var allCards = document.querySelectorAll('#accountList .account-card');
                allCards.forEach(function(card) {
                    var emailEl = card.querySelector('.account-email');
                    if (emailEl && emailEl.textContent.trim() === email) {
                        var infoEl = card.querySelector('.account-info');
                        if (infoEl) {
                            var statusEl = infoEl.querySelector('.standard-poll-status');
                            if (statusEl) statusEl.remove();
                        }
                        card.classList.remove('standard-poll-active');
                    }
                });
            } else {
                // 无参数时清除所有
                document.querySelectorAll('.standard-poll-status').forEach(function(el) { el.remove(); });
                document.querySelectorAll('.standard-poll-active').forEach(function(el) { el.classList.remove('standard-poll-active'); });
            }
        }

