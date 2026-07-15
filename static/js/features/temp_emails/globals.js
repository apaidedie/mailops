// split globals from temp_emails.js
        // ==================== 临时邮箱相关 ====================

        let tempEmailOptionsCache = new Map();
        let tempEmailOptionsState = new Map();
        let tempEmailOptionsRequestSeq = 0;
        // Coalesce concurrent options GETs per provider cacheKey.
        const tempEmailOptionsLoadPromises = Object.create(null);
        // True when the in-flight options GET for a cacheKey was started with forceRefresh.
        const tempEmailOptionsLoadForce = Object.create(null);

        /** Drop warm domain-options soft cache after settings/plugin mutations. */
