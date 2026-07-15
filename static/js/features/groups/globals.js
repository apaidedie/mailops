// split globals from groups.js
        // ==================== 分组相关 ====================

        // Coalesce concurrent cold GET /api/groups (navigate + compact race, import + UI).
        let groupsLoadPromise = null;
        // True when the in-flight groups GET was started with forceRefresh.
        let groupsLoadForce = false;
        // Coalesce concurrent cold GET /api/groups/<id> for edit modal.
        const groupDetailLoadPromises = Object.create(null);
        // True when the in-flight group detail GET was started with forceRefresh.
        const groupDetailLoadForce = Object.create(null);
        // Active open request for group edit modal. Cleared on hide/add so a late
        // soft/network response cannot re-open the shared add/edit modal.
        let editGroupPaintTargetId = null;

        // Sidebar group list lives under the mailbox page only.
