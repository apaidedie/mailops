// split globals from emails.js
        // ==================== 邮件相关 ====================

        // 模块内变量：存储上次获取邮件失败的错误详情
        let lastFetchErrorDetails = {};
        // Coalesce concurrent cold GET /api/emails for the same email+folder cacheKey.
        const emailsLoadPromises = Object.create(null);
        // True when the in-flight list GET for a cacheKey was started with forceRefresh.
        const emailsLoadForce = Object.create(null);
        // Soft-load message details by account|folder|method|messageId; coalesce concurrent loads.
        const emailDetailCache = new Map();
        const emailDetailLoadPromises = Object.create(null);
        // True when the in-flight detail GET for a cacheKey was started with forceRefresh.
        const emailDetailLoadForce = Object.create(null);

