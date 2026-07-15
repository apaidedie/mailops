// split from temp_emails.js → cache.js
        function invalidateTempEmailOptionsCache() {
            tempEmailOptionsCache.clear();
            tempEmailOptionsState.clear();
            for (const key of Object.keys(tempEmailOptionsLoadPromises)) {
                delete tempEmailOptionsLoadPromises[key];
                delete tempEmailOptionsLoadForce[key];
            }
            // Bump seq so abandoned in-flight responses do not repaint domain selects.
            tempEmailOptionsRequestSeq += 1;
        }
        window.invalidateTempEmailOptionsCache = invalidateTempEmailOptionsCache;
        // Coalesce concurrent cold GET /api/temp-emails (navigate + generate race).
        let tempEmailsLoadPromise = null;
        // True when the in-flight temp list GET was started with forceRefresh.
        let tempEmailsLoadForce = false;

        // BUG-05: 快速切换临时邮箱/从普通邮箱切换到临时邮箱时，旧请求与轮询可能污染当前 UI。
        // - tempEmailMessagesRequestSeq / tempEmailDetailRequestSeq 用于丢弃过期请求的响应（stale guard）。
        // - selectTempEmail 主动 stopAllPolls，避免轮询继续跑 /api/emails 导致报错与串号。
        let tempEmailMessagesRequestSeq = 0;
        let tempEmailDetailRequestSeq = 0;
        // Soft-load message lists by mailbox email; coalesce concurrent loads.
        const tempEmailMessagesCache = new Map();
        const tempEmailMessagesLoadPromises = Object.create(null);
        // True when the in-flight messages GET for a mailbox was started with forceRefresh.
        const tempEmailMessagesLoadForce = Object.create(null);
        // Soft-load message details by mailbox|messageId; coalesce concurrent loads.
        const tempEmailDetailCache = new Map();
        const tempEmailDetailLoadPromises = Object.create(null);
        // True when the in-flight detail GET for a cacheKey was started with forceRefresh.
        const tempEmailDetailLoadForce = Object.create(null);

        function getTempEmailDetailCacheKey(mailboxEmail, messageId) {
            return `${String(mailboxEmail || '').trim()}|${String(messageId || '').trim()}`;
        }

        function clearTempEmailDetailCacheForMailbox(mailboxEmail) {
            const prefix = `${String(mailboxEmail || '').trim()}|`;
            if (!prefix || prefix === '|') return;
            for (const key of Array.from(tempEmailDetailCache.keys())) {
                if (String(key).startsWith(prefix)) {
                    tempEmailDetailCache.delete(key);
                }
            }
            for (const key of Object.keys(tempEmailDetailLoadPromises)) {
                if (String(key).startsWith(prefix)) {
                    delete tempEmailDetailLoadPromises[key];
                    delete tempEmailDetailLoadForce[key];
                }
            }
        }

        /**
         * Drop soft message-list + detail caches for one temp mailbox.
         * Always clears loadForce so a later force cannot join a dead promise map entry.
         */
        function clearTempEmailMessagesCacheForMailbox(mailboxEmail) {
            const key = String(mailboxEmail || '').trim();
            if (!key) return;
            tempEmailMessagesCache.delete(key);
            delete tempEmailMessagesLoadPromises[key];
            delete tempEmailMessagesLoadForce[key];
            clearTempEmailDetailCacheForMailbox(key);
        }

        function seedEmptyTempEmailMessagesCache(mailboxEmail) {
            const key = String(mailboxEmail || '').trim();
            if (!key) return;
            tempEmailMessagesCache.set(key, { emails: [], count: 0 });
            delete tempEmailMessagesLoadPromises[key];
            delete tempEmailMessagesLoadForce[key];
            clearTempEmailDetailCacheForMailbox(key);
        }

        function invalidateTempEmailDetailCacheEntry(mailboxEmail, messageId) {
            const key = getTempEmailDetailCacheKey(mailboxEmail, messageId);
            if (!key || key === '|') return;
            tempEmailDetailCache.delete(key);
            delete tempEmailDetailLoadPromises[key];
            delete tempEmailDetailLoadForce[key];
        }

        // Cross-feature invalidation (emails.js delete path).
        window.invalidateTempEmailDetailCacheEntry = invalidateTempEmailDetailCacheEntry;
        window.clearTempEmailDetailCacheForMailbox = clearTempEmailDetailCacheForMailbox;
        window.clearTempEmailMessagesCacheForMailbox = clearTempEmailMessagesCacheForMailbox;

        // Explicit refresh button entry (force network).
