# Pool-admin filter options page paint guard

## Goal
Soft catalog/groups re-entry from other pages must not rewrite pool-admin filter selects while the user is elsewhere.

## Done
- [x] paintPoolAdminGroupOptions gated to isCurrentPoolAdminPage
- [x] applyPoolAdminProviderOptions gated to isCurrentPoolAdminPage
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
