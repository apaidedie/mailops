# Journal - apaidedie (Part 4)

> Continuation from `journal-3.md` (archived at ~2000 lines)
> Started: 2026-07-13

---

## 2026-07-13 — Soft-load temp-emails and pool-admin on navigate

**Branch**: `custom`

### Summary

`navigate('temp-emails')` / `navigate('pool-admin')` no longer force-refresh on every re-entry. Warm `accountsCache['temp']` / `__poolAdminState.cache` paint immediately; create/delete/filter/refresh handlers still pass `forceRefresh=true`.

### Main Changes

- `static/js/main.js` navigate soft-load flags
- overview + pool-admin frontend contract tests
- frontend quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `b5a0c24` | perf: soft-load temp-emails and pool-admin on navigate |

### Testing

- [OK] `node --check` main.js / temp_emails.js / pool_admin.js (exit 0)
- [OK] overview soft-load + navigate soft-load + pool-admin loader tests (3 OK, exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- selection_recipes still enumerate aliases by design
- Optional: soft-load refresh-log / audit pages if caches added
## 2026-07-13 — Soft-load refresh-log and audit pages on navigate

**Branch**: `custom`

### Summary

Refresh-log and audit pages keep in-memory payload caches. Navigate re-entry paints from cache; full token refresh invalidates refresh-log cache.

### Main Changes

- `loadRefreshLogPage` / `loadAuditLogPage` forceRefresh + cache
- `invalidateRefreshLogPageCache` on refreshAllAccounts complete
- overview frontend contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `b6b7133` | perf: soft-load refresh-log and audit pages on navigate |

### Testing

- [OK] `node --check static/js/main.js` (exit 0)
- [OK] navigate soft-load contract tests (exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- selection_recipes still enumerate aliases by design
## 2026-07-13 — Invalidate refresh-log cache on all refresh paths

**Branch**: `custom`

### Summary

Soft-load refresh-log cache now invalidates after full refresh, failed-account retry, single-account retry, and selected-batch complete — not only `refreshAllAccounts`.

### Main Changes

- `retryFailedAccounts` / `retrySingleAccount` / `handleBatchRefreshSSEEvent`
- overview frontend contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `01a65d0` | fix: invalidate refresh-log soft cache on all refresh paths |

### Testing

- [OK] `node --check static/js/main.js` (exit 0)
- [OK] navigate soft-load refresh/audit contract test (exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- selection_recipes still enumerate aliases by design
## 2026-07-13 — Soft-load settings page on navigate re-entry

**Branch**: `custom`

### Summary

Settings re-entry reuses warm GET `/api/settings` via `settingsPageCache`. Manual/auto save and layout PUT invalidate; temp-mail snapshot refresh repopulates from server.

### Main Changes

- `loadSettings(forceRefresh)` + `invalidateSettingsPageCache`
- save/auto-save/layout invalidation; snapshot refresh repopulates
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `bef439a` | perf: soft-load settings page on navigate re-entry |

### Testing

- [OK] `node --check static/js/main.js` (exit 0)
- [OK] settings soft-load + related contract tests (3 OK, exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- selection_recipes still enumerate aliases by design
- Optional: invalidate audit soft cache after mutating ops if needed
## 2026-07-13 — Coalesce concurrent loadSettings fetches

**Branch**: `custom`

### Summary

Concurrent soft Settings opens share one in-flight GET via `fetchSettingsPagePayload` / `settingsPageLoadPromise`. Warm cache still short-circuits; forceRefresh starts its own request.

### Main Changes

- `fetchSettingsPagePayload` + `settingsPageLoadPromise`
- loadSettings uses shared fetch helper
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `88046b2` | perf: coalesce concurrent soft loadSettings fetches |

### Testing

- [OK] `node --check static/js/main.js` (exit 0)
- [OK] settings soft-load contract tests (exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- selection_recipes still enumerate aliases by design
## 2026-07-13 — Route remaining settings GETs through soft-load helper

**Branch**: `custom`

### Summary

`refreshTempMailSettingsSnapshotFromServer`, `initPollingSettings` fallback, and `triggerUpdate` now use `fetchSettingsPagePayload`. Invalidate bumps generation and clears soft in-flight so stale responses cannot repopulate cache.

### Main Changes

- `settingsPageCacheGeneration` + invalidate guard
- route remaining soft GETs through helper
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `e55e89c` | perf: route settings GETs through soft-load helper |

### Testing

- [OK] `node --check static/js/main.js` (exit 0)
- [OK] settings soft-load contract tests (exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- selection_recipes still enumerate aliases by design
## 2026-07-13 — Soft-load unified mailbox directory on re-entry

**Branch**: `custom`

### Summary

`loadUnifiedMailboxes(false)` reuses warm `directoryPayload` when `directorySignature` matches the current request signature. Filter/search/page/refresh still force network.

### Main Changes

- `directoryPayload` / `directorySignature` + `applyUnifiedMailboxDirectoryPayload`
- unified mailbox frontend contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `9d4950b` | perf: soft-load unified mailbox directory on re-entry |

### Testing

- [OK] `node --check static/js/features/mailboxes.js` (exit 0)
- [OK] unified mailbox frontend contract tests (2 OK, exit 0)
- [OK] `git diff --check` (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: invalidate unified directory cache after account/temp mutations
## 2026-07-13 — Invalidate unified directory cache on inventory force-refresh

**Branch**: `custom`

### Summary

`loadAccountsByGroup(..., true)` and `loadTempEmails(true)` call `window.invalidateUnifiedMailboxDirectoryCache()` so unified soft-load does not paint stale directory rows after inventory mutations.

### Main Changes

- window export of invalidate helper
- groups.js / temp_emails.js force-refresh hooks
- unified frontend contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `ff82722` | fix: invalidate unified directory soft cache on inventory force-refresh |

### Testing

- [OK] node --check mailboxes/groups/temp_emails (exit 0)
- [OK] unified contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: defer Notification.requestPermission until user gesture
## 2026-07-13 — Defer browser Notification permission until after boot

**Branch**: `custom`

### Summary

Boot no longer calls `Notification.requestPermission()` synchronously. `scheduleBrowserNotificationPermissionPrompt` waits for first pointer/key gesture, with a 30s idle fallback.

### Main Changes

- `scheduleBrowserNotificationPermissionPrompt` in main.js
- overview boot contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: defer browser Notification permission until after boot |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] boot defer notification + groups/tags tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Residual: audit soft cache invalidation hooks still light
## 2026-07-13 — Invalidate audit soft cache on settings and inventory mutations

**Branch**: `custom`

### Summary

`window.invalidateAuditLogPageCache` is exported and called after settings save/auto-save, account/temp force-refresh, and token refresh success paths so audit soft-load does not paint stale rows.

### Main Changes

- main.js settings + refresh invalidation hooks
- groups.js / temp_emails.js force-refresh hooks
- overview + unified contract tests + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `abbbbb7` | fix: invalidate audit soft cache on settings and inventory mutations |

### Testing

- [OK] node --check main/groups/temp_emails (exit 0)
- [OK] soft-load audit + inventory invalidation contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: soft-load loadGroups if groups list is large
## 2026-07-13 — Soft-load groups list when warm cache exists

**Branch**: `custom`

### Summary

`loadGroups(false)` reuses warm in-memory `groups` and re-renders without `/api/groups`. Mutation paths (create/delete/import/move) call `loadGroups(true)`.

### Main Changes

- groups.js soft-load path
- accounts.js / main.js mutation force flags
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `3b97a71` | perf: soft-load groups list when warm cache exists |

### Testing

- [OK] node --check groups/accounts/main (exit 0)
- [OK] load_groups soft + boot defer tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load tags list when warm cache exists

**Branch**: `custom`

### Summary

`loadTags(false)` reuses warm `allTags` (re-render + coalesce via `tagsLoadPromise`). Create/delete call `loadTags(true)`. `loadTagsForSelect` reuses warm tags / soft loadTags without raw GET.

### Main Changes

- `loadTags(forceRefresh)` + `tagsLoadPromise` in main.js
- `loadTagsForSelect` soft path
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load tags list when warm cache exists |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] tags soft-load + boot/groups contract tests (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: soft-load loadRefreshStats / coalesce loadGroups in-flight
## 2026-07-13 — Soft-load refresh stats when warm cache exists

**Branch**: `custom`

### Summary

`loadRefreshStats(false)` reuses `refreshStatsCache` + coalesces via `refreshStatsLoadPromise`. Modal re-open is soft; retry/single-refresh/batch-delete/governance force; full refresh complete updates cache; selected-batch complete invalidates.

### Main Changes

- refreshStatsCache / applyRefreshStats / invalidateRefreshStatsCache
- showRefreshModal soft load; mutation force flags
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load refresh stats when warm cache exists |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] refresh-stats + tags soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: soft-load failed-list / coalesce loadGroups in-flight
## 2026-07-13 — Soft-load and coalesce failed refresh list fetches

**Branch**: `custom`

### Summary

`fetchFailedRefreshLogs` owns the only raw GET for failed refresh logs. auto-load and loadFailedLogs soft-load/coalesce; showFailedListFromData/hideFailedList seed or clear cache; single retry forces reload.

### Main Changes

- failedRefreshLogsCache + fetchFailedRefreshLogs
- autoLoadFailedListIfNeeded / loadFailedLogs shared path
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load and coalesce failed refresh list fetches |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] failed-list + refresh-stats contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: coalesce loadGroups in-flight
## 2026-07-13 — Coalesce concurrent loadGroups network fetches

**Branch**: `custom`

### Summary

Cold/network `loadGroups` shares `groupsLoadPromise` so navigate/import races do not stampede `/api/groups`. Warm soft path still re-renders via `applyLoadedGroups(..., { refreshAccounts: false })`.

### Main Changes

- `groupsLoadPromise` + `applyLoadedGroups`
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: coalesce concurrent loadGroups network fetches |

### Testing

- [OK] node --check groups.js (exit 0)
- [OK] load_groups soft + boot defer tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: soft-load modal loadRefreshLogs (limit=1000) vs page cache
## 2026-07-13 — Soft-load refresh modal history list

**Branch**: `custom`

### Summary

`loadRefreshLogs(false)` soft-loads via `refreshModalHistoryCache` (limit=1000). `invalidateRefreshLogPageCache` clears both page (limit=200) and modal history caches after refresh mutations.

### Main Changes

- refreshModalHistoryCache + renderRefreshModalHistory + coalesce
- invalidateRefreshLogPageCache clears modal history too
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load refresh modal history list |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] modal history + navigate refresh/audit soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: soft-load invalid-token governance candidates
## 2026-07-13 — Soft-load invalid-token governance candidates

**Branch**: `custom`

### Summary

Invalid-token governance soft-loads warm candidates on refresh-modal re-open. `resetInvalidTokenGovernanceState` only hides UI; batch inactive/refresh complete force-refresh; batch delete invalidates cache.

### Main Changes

- `invalidTokenGovernanceCandidatesLoaded` + load promise + apply helper
- forceRefresh on mutation paths; invalidate on batch delete
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load invalid-token governance candidates |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] invalid-token governance + modal history soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Coalesce concurrent loadAccountsByGroup fetches

**Branch**: `custom`

### Summary

`loadAccountsByGroup` shares `accountsByGroupLoadPromises[queryKey]` for concurrent cold/force network loads. Warm soft path still short-circuits on matching accountsCache.

### Main Changes

- accountsByGroupLoadPromises map
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: coalesce concurrent loadAccountsByGroup fetches |

### Testing

- [OK] node --check groups.js (exit 0)
- [OK] accounts coalesce + groups soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Coalesce concurrent loadTempEmails network fetches

**Branch**: `custom`

### Summary

`loadTempEmails` shares `tempEmailsLoadPromise` for concurrent cold/force network loads. Warm `accountsCache['temp']` still short-circuits first.

### Main Changes

- tempEmailsLoadPromise in temp_emails.js
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: coalesce concurrent loadTempEmails network fetches |

### Testing

- [OK] node --check temp_emails.js (exit 0)
- [OK] temp emails coalesce + navigate soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
- Optional: coalesce loadEmails by cacheKey
## 2026-07-13 — Coalesce concurrent loadEmails fetches by cacheKey

**Branch**: `custom`

### Summary

`loadEmails` shares `emailsLoadPromises[cacheKey]` for concurrent cold/force network loads. Warm `emailListCache` still short-circuits; removed duplicate account_summary sync.

### Main Changes

- emailsLoadPromises map in emails.js
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: coalesce concurrent loadEmails fetches by cacheKey |

### Testing

- [OK] node --check emails.js (exit 0)
- [OK] load_emails + load_temp_emails coalesce tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Key pool-admin soft cache by query and coalesce loads

**Branch**: `custom`

### Summary

`loadPoolAdmin` soft-loads only when `cacheQueryKey` matches current filters/page via `getPoolAdminQueryKey()`. Concurrent loads for the same signature coalesce on `loadPromise`.

### Main Changes

- getPoolAdminQueryKey + cacheQueryKey + loadPromise
- overview + pool-admin contract tests + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: key pool-admin soft cache by query and coalesce loads |

### Testing

- [OK] node --check pool_admin.js (exit 0)
- [OK] navigate soft-load + pool admin loader tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Coalesce concurrent loadProviders for import modal

**Branch**: `custom`

### Summary

`loadProviders` shares `providersLoadPromise` for concurrent cold/force loads after the warm `providersLoaded` short-circuit, reducing import-modal open races against shared catalog.

### Main Changes

- providersLoadPromise in accounts.js
- v190 frontend contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: coalesce concurrent loadProviders for import modal |

### Testing

- [OK] node --check accounts.js (exit 0)
- [OK] test_import_account_provider_selector_is_catalog_driven (OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE; auto-turn budget exhausted)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load token-tool config and account options

**Branch**: `custom`

### Summary

Token-tool soft-loads warm OAuth config and save-dialog accounts with in-flight coalesce. Boot uses soft config load; post-save invalidates accounts cache; saveConfig updates oauthConfigCache.

### Main Changes

- oauthConfigCache / tokenToolAccountsCache + load promises
- openSaveDialog soft; confirmSaveToAccount invalidates accounts
- oauth tool frontend contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load token-tool config and account options |

### Testing

- [OK] node --check token_tool.js (exit 0)
- [OK] test_token_tool_js_soft_loads_config_and_accounts (OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load batch-move groups from warm groups cache

**Branch**: `custom`

### Summary

`loadGroupsForBatchMove` reuses warm `groups` / soft `loadGroups(false)` instead of raw GET `/api/groups`.

### Main Changes

- main.js loadGroupsForBatchMove soft path
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `b9576a4` | perf: soft-load batch-move groups from warm groups cache |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] batch-move + groups soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load export group list via loadGroups

**Branch**: `custom`

### Summary

`loadExportGroupList` soft-loads cold groups via `loadGroups(false)` then paints from warm `groups` (no empty false-negative / no raw GET).

### Main Changes

- accounts.js loadExportGroupList soft path
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `2ac256f` | perf: soft-load export group list via loadGroups |

### Testing

- [OK] node --check accounts.js (exit 0)
- [OK] export + batch-move soft-load tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load pool-admin group options via loadGroups

**Branch**: `custom`

### Summary

`ensurePoolAdminGroupOptions` reuses warm `groups` / soft `loadGroups(false|true)` and no longer raw-fetches `/api/groups`.

### Main Changes

- paintPoolAdminGroupOptions + async ensurePoolAdminGroupOptions
- overview + pool-admin contract tests + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load pool-admin group options via loadGroups |

### Testing

- [OK] node --check pool_admin.js (exit 0)
- [OK] navigate soft-load + pool admin loader tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load and coalesce temp email messages

**Branch**: `custom`

### Summary

`loadTempEmailMessages` soft-loads warm message lists by email and coalesces concurrent loads. Select is soft; explicit refresh forces; clear/delete drop cache.

### Main Changes

- tempEmailMessagesCache + tempEmailMessagesLoadPromises
- select soft / refresh force binding
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load and coalesce temp email messages |

### Testing

- [OK] node --check temp_emails.js / emails.js (exit 0)
- [OK] temp message soft-load + temp emails coalesce tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load deployment info on settings re-entry

**Branch**: `custom`

### Summary

`loadDeploymentInfo` soft-loads warm `lastDeploymentInfo` and coalesces concurrent network loads. Settings open uses soft load; language change still re-renders from cache.

### Main Changes

- deploymentInfoLoadPromise + applyDeploymentInfo
- loadSettings soft forceRefresh:false
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| (pending) | perf: soft-load deployment info on settings re-entry |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] test_load_deployment_info_soft_loads_warm_cache (OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)
## 2026-07-13 — Soft-load unified mailbox messages on re-open

**Branch**: `custom`

### Summary

Unified mailbox message preview soft-loads warm messages for the same key/folder page and coalesces concurrent loads. Refresh/retry still force network; open helper soft-opens.

### Main Changes

- preview.messagesSignature + messagesLoadPromise
- openUnifiedMessagePreview force:false
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `56d1eb1` | perf: soft-load unified mailbox messages on re-open |

### Testing

- [OK] node --check mailboxes.js (exit 0)
- [OK] unified messages soft-load + view mode tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration separate)

## 2026-07-13 — Soft-load unified mailbox message detail on re-select

**Branch**: `custom`

### Summary

Unified mailbox message detail soft-loads warm content for the same key/folder/messageId and coalesces concurrent loads. Row click soft-selects; retry and post-list auto-select force network; list refresh clears detailSignature.

### Main Changes

- preview.detailSignature + detailLoadPromise/detailLoadSignature
- loadUnifiedMailboxMessageDetail(options.force)
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `0a5cf82` | perf: soft-load unified mailbox message detail on re-select |

### Testing

- [OK] node --check mailboxes.js (exit 0)
- [OK] detail + messages soft-load contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual candidates: version-check soft cache; verification soft-load; stored DEFAULT migration research

## 2026-07-13 — Soft-load temp email message detail on re-select

**Branch**: `custom`

### Summary

Temp email message detail soft-loads warm content by mailbox|messageId and coalesces concurrent loads. Force list refresh / clear / delete mailbox clear mailbox detail cache; single-message delete invalidates via window helper.

### Main Changes

- tempEmailDetailCache + tempEmailDetailLoadPromises
- getTempEmailDetail(forceRefresh)
- window.invalidateTempEmailDetailCacheEntry
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `527110c` | perf: soft-load temp email message detail on re-select |

### Testing

- [OK] node --check temp_emails.js + emails.js (exit 0)
- [OK] detail + messages soft-load contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: version-check soft cache; mailbox selectEmail detail soft-load; verification soft-load; DEFAULT migration research

## 2026-07-13 — Soft-load mailbox selectEmail detail on re-select

**Branch**: `custom`

### Summary

Outlook/IMAP message detail soft-loads warm content by account|folder|method|messageId and coalesces concurrent loads. Force list refresh / refreshEmails clear mailbox+folder detail cache; delete invalidates matching keys.

### Main Changes

- emailDetailCache + emailDetailLoadPromises
- selectEmail(forceRefresh)
- clearEmailDetailCacheForMailbox / invalidateEmailDetailCacheEntry
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `963adaf` | perf: soft-load mailbox selectEmail detail on re-select |

### Testing

- [OK] node --check emails.js (exit 0)
- [OK] selectEmail + loadEmails + temp detail contract tests (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: version-check soft cache; unified verification soft-load; DEFAULT migration research

## 2026-07-13 — Soft-load unified mailbox verification on re-run

**Branch**: `custom`

### Summary

Unified mailbox verification soft-loads warm result for the same key|folder and coalesces concurrent loads. Extract button forces network; list/detail refresh clear verificationSignature.

### Main Changes

- preview.verificationSignature + verificationLoadPromise/verificationLoadSignature
- loadUnifiedMailboxVerification(options.force)
- extract button { force: true }
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `739c5f8` | perf: soft-load unified mailbox verification on re-run |

### Testing

- [OK] node --check mailboxes.js (exit 0)
- [OK] verification + detail + messages contract tests (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: version-check soft cache; DEFAULT migration research

## 2026-07-13 — Soft-load editGroup from warm groups cache

**Branch**: `custom`

### Summary

editGroup paints the edit modal from the warm groups array when the row is present, and coalesces concurrent cold GET /api/groups/<id>.

### Main Changes

- applyEditGroupForm helper
- editGroup(forceRefresh) soft path + groupDetailLoadPromises
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `3ce09d6` | perf: soft-load editGroup from warm groups cache |

### Testing

- [OK] node --check groups.js (exit 0)
- [OK] editGroup + loadGroups contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: version-check session cache (low value single-shot); showEditAccountModal soft from list if safe; DEFAULT migration research

## 2026-07-13 — Soft-load system version-check session cache

**Branch**: `custom`

### Summary

checkVersionUpdate soft-loads warm session version-check payload and coalesces concurrent checks. Boot delay path stays soft; applyVersionCheckPayload owns banner paint.

### Main Changes

- versionCheckCache + versionCheckLoadPromise
- applyVersionCheckPayload helper
- checkVersionUpdate(forceRefresh)
- JSContractTests + overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `8b75107` | perf: soft-load system version-check session cache |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] overview version-check soft-load test (exit 0)
- [OK] tests.test_version_update full suite (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: showEditAccountModal soft-load if list payload safe; DEFAULT migration research; poll-engine remains intentionally always-network

## 2026-07-13 — Soft-load showEditAccountModal detail cache

**Branch**: `custom`

### Summary

showEditAccountModal soft-loads warm account detail from a prior GET /api/accounts/<id> only (never list rows — client_id truncated). Concurrent loads coalesce; update/remark/delete/status invalidate cache.

### Main Changes

- accountDetailCache + accountDetailLoadPromises
- applyEditAccountForm / invalidateAccountDetailCache
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `ff724a7` | perf: soft-load showEditAccountModal detail cache |

### Testing

- [OK] node --check accounts.js (exit 0)
- [OK] edit modal + version-check contract tests (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration research; poll-engine remains always-network by design

## 2026-07-13 — Invalidate account detail cache on batch mutations

**Branch**: `custom`

### Summary

Batch delete/status paths now drop warm showEditAccountModal detail via window.invalidateAccountDetailCacheMany so re-open refetches after bulk ops.

### Main Changes

- window.invalidateAccountDetailCache / Many
- batchDeleteAccounts + invalid-token batch delete/status
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `9baa3aa` | fix: invalidate account detail cache on batch mutations |

### Testing

- [OK] node --check accounts.js + main.js (exit 0)
- [OK] show_edit_account_modal soft-load contract (1 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; poll-engine intentionally always-network

## 2026-07-13 — Invalidate account detail cache on batch move/tag

**Branch**: `custom`

### Summary

Batch move-group and batch tag success paths now drop warm showEditAccountModal detail via window.invalidateAccountDetailCacheMany so re-open refetches group_id after bulk ops.

### Main Changes

- confirmBatchMoveGroup + confirmBatchTag invalidation
- contract asserts >= 5 main.js call sites
- quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `a77c7fe` | fix: invalidate account detail cache on batch move/tag |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] show_edit_account_modal soft-load contract (1 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; poll-engine intentionally always-network

## 2026-07-13 — Upsert emailListCache on loadMoreEmails

**Branch**: `custom`

### Summary

loadMoreEmails always upserts emailListCache after a successful page append so soft re-select via loadEmails(false) keeps already-paginated rows even when the cache key was missing.

### Main Changes

- emailListCache upsert (emails/has_more/skip/method)
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `77b0906` | perf: upsert emailListCache on loadMoreEmails |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] load_more_emails_upserts_list_cache (1 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; poll-engine intentionally always-network

## 2026-07-13 — Seed emailListCache from compact account pull

**Branch**: `custom`

### Summary

refreshCompactAccount now upserts emailListCache for inbox/junkemail via cacheBatchFetchedFolder and clears emailDetailCache for those folders so standard-view soft-load reuses compact pull pages.

### Main Changes

- folderSpecs with explicit folder mapping
- cacheBatchFetchedFolder + clearEmailDetailCacheForMailbox
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `c3c14b7` | perf: seed emailListCache from compact account pull |

### Testing

- [OK] node --check mailbox_compact.js (exit 0)
- [OK] compact pull seed + batch-fetch contract suite (10 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; poll-engine intentionally always-network

## 2026-07-13 — Seed emailListCache from poll engine fetches

**Branch**: `custom`

### Summary

Poll startPoll baseline and pollSingleEmail success paths seed emailListCache for inbox/sentitems via seedPollEmailListCache (cacheBatchFetchedFolder preferred) and clear emailDetailCache for those folders.

### Main Changes

- POLL_LIST_FOLDERS + seedPollEmailListCache
- startPoll baseline + pollSingleEmail seed
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `786ca38` | perf: seed emailListCache from poll engine fetches |

### Testing

- [OK] node --check poll-engine.js (exit 0)
- [OK] poll + compact seed contracts + compact_poll suite (16 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Coalesce concurrent overview tab loads

**Branch**: `custom`

### Summary

loadOverviewTab soft-loads warm tab cache and coalesces concurrent cold/force loads via loadPromises. invalidateOverviewCache clears cache + in-flight bookkeeping.

### Main Changes

- __overviewState.loadPromises
- loadOverviewTab shared promise + mid-flight invalidate guard
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `87aa54b` | perf: coalesce concurrent overview tab loads |

### Testing

- [OK] node --check overview.js (exit 0)
- [OK] coalesce + init soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Force overview tab reload supersedes soft in-flight

**Branch**: `custom`

### Summary

Force overview loads join only force in-flight and supersede soft in-flight so Refresh / overview-data-changed always start a true network GET. Soft still joins any in-flight.

### Main Changes

- loadForce map
- force supersede soft bookkeeping
- empty invalidate clears loadPromises/loadForce/loading
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| `818ed25` | fix: force overview tab reload supersedes soft in-flight |

### Testing

- [OK] node --check overview.js (exit 0)
- [OK] coalesce + init soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; bootstrap layout soft-load low value (single boot call)

## 2026-07-13 — Force catalog reload supersedes soft in-flight

**Branch**: custom

### Summary

loadMailboxProviderCatalog force joins only force in-flight and supersedes soft so save/refresh cannot paint stale /api/providers. Soft still joins any in-flight; abandoned soft responses skip cache write via request identity.

### Main Changes

- mailboxProviderCatalogLoadForce
- force supersede soft bookkeeping + request identity guards
- settings tab contract updates for loadSettings(forceRefresh) + fetchSettingsPagePayload

### Git Commits

| Hash | Message |
|------|---------|
| a72ea5 | fix: force catalog reload supersedes soft in-flight |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] settings tab refactor suite (34 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; settings/deployment force-bypass patterns optional

## 2026-07-13 — Force settings/deployment reload supersedes soft in-flight

**Branch**: custom

### Summary

fetchSettingsPagePayload and loadDeploymentInfo now use loadForce flags: soft joins any in-flight; force joins only force and supersedes soft so abandoned soft responses cannot repaint stale settings/deployment.

### Main Changes

- settingsPageLoadForce + generation bump on force supersede
- deploymentInfoLoadForce + request identity guards
- overview contract + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| 11977c1 | fix: force settings/deployment reload supersedes soft in-flight |

### Testing

- [OK] node --check main.js (exit 0)
- [OK] deployment + settings soft-load contracts + catalog status (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; optional force-bypass for other loaders

## 2026-07-13 — Force groups/tags/preflight supersede soft in-flight

**Branch**: custom

### Summary

loadGroups, loadTags, and loadProviderPreflightSnapshot now use loadForce flags: soft joins any in-flight; force joins only force and supersedes soft so abandoned soft responses cannot repaint stale groups/tags/preflight after mutations.

### Main Changes

- groupsLoadForce + request identity
- tagsLoadForce + request identity
- providerPreflightLoadForce (+ probe treated as force)
- overview + settings preflight contracts + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| 705ba5f | fix: force groups/tags/preflight supersede soft in-flight |

### Testing

- [OK] node --check main.js + groups.js (exit 0)
- [OK] tags + groups + preflight contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; optional force-bypass for emails/temp loaders

## 2026-07-13 — Force emails/temp/accounts-by-group supersede soft in-flight

**Branch**: custom

### Summary

loadEmails, loadTempEmails, and loadAccountsByGroup now use per-key/global loadForce flags: soft joins any in-flight; force joins only force and supersedes soft so abandoned soft responses cannot repaint stale list caches after refresh/generate/import.

### Main Changes

- emailsLoadForce[cacheKey] + request identity
- tempEmailsLoadForce + request identity
- accountsByGroupLoadForce[queryKey] + request identity
- overview contracts + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| 6b564c2 | fix: force emails/temp/accounts-by-group supersede soft in-flight |

### Testing

- [OK] node --check emails.js + temp_emails.js + groups.js (exit 0)
- [OK] emails + temp + accounts-by-group coalesce contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; optional force-bypass for temp messages / token-tool loaders

## 2026-07-13 — Force temp messages and token-tool supersede soft in-flight

**Branch**: custom

### Summary

loadTempEmailMessages, loadOAuthConfig, and loadAccountOptions now use loadForce flags: soft joins any in-flight; force joins only force and supersedes soft so abandoned soft responses cannot repaint stale temp messages or token-tool config/accounts.

### Main Changes

- tempEmailMessagesLoadForce[email] + request identity (keeps requestSeq)
- oauthConfigLoadForce / tokenToolAccountsLoadForce
- invalidateTokenToolAccountsCache clears loadForce
- overview + oauth contracts + quality guidelines

### Git Commits

| Hash | Message |
|------|---------|
| 25cedaf | fix: force temp messages and token-tool supersede soft in-flight |

### Testing

- [OK] node --check temp_emails.js + token_tool.js (exit 0)
- [OK] temp messages + token-tool soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract; optional force-bypass for remaining secondary loaders

## 2026-07-13 — Force providers and refresh-log loaders supersede soft in-flight

**Branch**: `custom`

### Summary

loadProviders, refresh stats/logs/failed logs, version-check, and operational readiness now use loadForce flags: soft joins any in-flight; force joins only force and supersedes soft.

### Main Changes

- providersLoadForce
- refreshStatsLoadForce / failedRefreshLogsLoadForce / refreshModalHistoryLoadForce
- versionCheckLoadForce / operationalReadinessSnapshotLoadForce
- invalidate helpers clear loadForce

### Git Commits

| Hash | Message |
|------|---------|
| `00cfda9` | fix: force providers and refresh-log loaders supersede soft in-flight |

### Testing

- [OK] node --check main.js + accounts.js (exit 0)
- [OK] refresh/version/providers contracts green
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: detail loaders force-bypass; DEFAULT migration deferred

## 2026-07-13 — Force detail loaders and contract-check supersede soft in-flight

**Branch**: custom

### Summary

showEditAccountModal, editGroup, selectEmail, getTempEmailDetail, and loadExternalApiContractCheck now use loadForce flags: soft joins any in-flight; force joins only force and supersedes soft so abandoned soft responses cannot repaint stale details or contract reports.

### Main Changes

- accountDetailLoadForce / groupDetailLoadForce
- emailDetailLoadForce / tempEmailDetailLoadForce
- externalApiContractCheckLoadForce
- invalidate/clear helpers drop loadForce keys

### Git Commits

| Hash | Message |
|------|---------|
| 94a359 | fix: force detail loaders and contract-check supersede soft in-flight |

### Testing

- [OK] node --check accounts/emails/temp_emails/groups/main.js (exit 0)
- [OK] editGroup/account modal/temp detail/selectEmail + operational readiness contracts (5 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Force invalid-token and page-log loaders supersede soft in-flight

**Branch**: custom

### Summary

`loadInvalidTokenGovernanceCandidates`, `loadRefreshLogPage`, and `loadAuditLogPage` now use loadForce flags: soft joins any in-flight; force joins only force and supersedes soft so abandoned soft responses cannot repaint stale caches.

### Main Changes

- invalidTokenGovernanceLoadForce
- refreshLogPageLoadPromise / refreshLogPageLoadForce
- auditLogPageLoadPromise / auditLogPageLoadForce
- invalidate helpers clear promise + force

### Git Commits

| Hash | Message |
|------|---------|
| c8d922a | fix: force invalid-token and page-log loaders supersede soft in-flight |

### Testing

- [OK] node --check static/js/main.js (exit 0)
- [OK] overview contract focused + full suite (40 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: unified preview force-bypass; plugins loadForce; DEFAULT alias migration deferred

## 2026-07-13 — Force unified mailbox preview loaders supersede soft in-flight

**Branch**: custom

### Summary

Unified messages/detail/verification loaders now use preview.*LoadForce: soft joins any same-signature in-flight; force joins only force and supersedes soft so refresh/retry/extract always start a true network GET.

### Main Changes

- messagesLoadForce / detailLoadForce / verificationLoadForce
- request identity guards alongside requestSeq/detailSeq/verificationSeq
- quality-guidelines + overview contract tests updated

### Testing

- [OK] node --check static/js/features/mailboxes.js (exit 0)
- [OK] unified messages/detail/verification contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: plugins `_pluginsLoadForce`; pool-admin soft/force if any; DEFAULT alias migration deferred

## 2026-07-13 — Force PluginManager loadPlugins supersede soft in-flight

**Branch**: custom

### Summary

`PluginManager.loadPlugins` now uses `_pluginsLoadForce`: soft joins any in-flight; force joins only force and supersedes soft so refresh/install/uninstall paths always start a true network GET.

### Main Changes

- `_pluginsLoadForce`
- request identity guards on apply/side effects
- quality-guidelines + temp_mail target contract

### Testing

- [OK] node --check static/js/features/plugins.js
- [OK] test_temp_email_provider_select_is_catalog_driven (exit 0)
- [OK] git diff --check (exit 0)
- Note: unrelated test_settings_page_does_not_expose_legacy_gptmail_field_name still fails on missing copy string (pre-existing)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: pool-admin force-bypass if missing; DEFAULT alias migration deferred

## 2026-07-13 — Force loadPoolAdmin supersede soft in-flight

**Branch**: custom

### Summary

`loadPoolAdmin` now uses `__poolAdminState.loadForce`: soft joins any same-query in-flight; force joins only force and supersedes soft so filter/mutation reloads always start a true network GET.

### Main Changes

- loadForce flag on __poolAdminState
- request identity guards on apply
- quality-guidelines + pool_admin / overview contracts

### Testing

- [OK] node --check static/js/features/pool_admin.js
- [OK] PoolAdminJsModuleTests + overview pool soft-load (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: scan remaining LoadPromise without LoadForce; DEFAULT alias migration deferred

## 2026-07-13 — Restore legacy temp-mail API Key compatibility copy in settings

**Branch**: custom

### Summary

Restored the operator-facing compatibility note for the retired legacy temp-mail API Key field on the Settings temp-mail tab so the page no longer exposes `gptmail_api_key` while still documenting compatibility-only reads/migration.

### Main Changes

- templates/index.html: form-hint near hidden gptmailConfigPanel mount

### Testing

- [OK] test_settings_page_does_not_expose_legacy_gptmail_field_name (exit 0)
- [OK] git diff --check templates/index.html (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Soft/force LoadPromise scan is clean (0 remaining)
- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Force initCSRFToken supersede soft in-flight

**Branch**: custom

### Summary

`initCSRFToken` now uses `csrfTokenRefreshForce`: soft joins any in-flight CSRF pull; force joins only force and supersedes soft so CSRF_TOKEN_INVALID recovery always starts a true `/api/csrf-token` GET and abandoned soft responses do not apply a stale token.

### Main Changes

- csrfTokenRefreshForce
- request identity guards on apply
- smoke contract asserts force supersede path

### Testing

- [OK] node --check static/js/main.js
- [OK] smoke static asset + csrf recovery suite (7 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Soft/force LoadPromise + CSRF scan clean
- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Force loadTempEmailOptions supersede soft in-flight

**Branch**: custom

### Summary

`loadTempEmailOptions` now coalesces concurrent options GETs per provider cacheKey and uses `tempEmailOptionsLoadForce[cacheKey]`: soft joins any same-key in-flight; force joins only force and supersedes soft so provider switch/refresh always starts a true network GET.

### Main Changes

- tempEmailOptionsLoadPromises / tempEmailOptionsLoadForce
- request identity guards (keeps requestSeq stale paint guard)
- overview contract + quality-guidelines

### Testing

- [OK] node --check static/js/features/temp_emails.js
- [OK] options force + temp list coalesce contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Force loadUnifiedMailboxes directory supersede soft in-flight

**Branch**: custom

### Summary

`loadUnifiedMailboxes` now tracks `directoryLoadSeq` / `directoryLoadForce` / `directoryInFlightSignature`: soft joins same-signature in-flight; force supersedes soft by bumping seq so abandoned soft responses do not write `directoryPayload`. Also aligned capability-matrix contract with `dedupeUnifiedTempProviderRows`.

### Main Changes

- directoryLoadSeq / directoryLoadForce / directoryInFlightSignature
- force supersede soft path in loadUnifiedMailboxes
- unified mailbox frontend contract + quality-guidelines

### Testing

- [OK] node --check static/js/features/mailboxes.js
- [OK] unified mailbox directory + capability matrix + messages soft-load (4 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Invalidate tempEmailOptionsCache after settings/plugin mutations

**Branch**: custom

### Summary

Added `invalidateTempEmailOptionsCache()` so soft domain-options cache cannot paint stale credentials after Settings save, temp-mail auto-save, plugin config save/applyChanges, or force `loadTempEmails(true)`.

### Main Changes

- invalidateTempEmailOptionsCache + window export
- saveSettings / autoSaveSettings(temp-mail) / plugins saveConfig+applyChanges / loadTempEmails(true)
- overview contract + quality-guidelines

### Testing

- [OK] node --check temp_emails/main/plugins.js
- [OK] options invalidate + force contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Force ensurePoolAdminProviderOptions reload shared catalog

**Branch**: custom

### Summary

`ensurePoolAdminProviderOptions(true)` no longer soft-applies a warm catalog snapshot and skip network; force always calls `loadMailboxProviderCatalog(true)` (empty warm still forces) so pool type filter tracks catalog mutations.

### Main Changes

- soft: `!force && applyFromCache()` early return
- forceCatalogLoad = force || emptyWarmCache
- pool_admin contract + quality-guidelines

### Testing

- [OK] node --check static/js/features/pool_admin.js
- [OK] test_pool_admin_frontend_contract (7 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Keep accountListMetaCache in sync when dropping accountsCache

**Branch**: custom

### Summary

Added `invalidateAccountsCache(groupId?)` so inventory mutations clear account rows, pagination meta, and in-flight maps together. Replaced bare `delete accountsCache[...]` across accounts/main/temp/groups.

### Main Changes

- invalidateAccountsCache + window export in groups.js
- all mutation delete sites use helper
- overview contract + quality-guidelines

### Testing

- [OK] node --check groups/accounts/temp_emails/main.js
- [OK] loadAccountsByGroup coalesce + v190 frontend (23 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Sync email list soft cache after message delete

**Branch**: custom

### Summary

`deleteEmails` and `deleteCurrentTempEmailMessage` now upsert soft list caches from post-delete `currentEmails` so soft re-select cannot repaint deleted rows (detail invalidation alone was insufficient).

### Main Changes

- emailListCache upsert on mailbox delete
- tempEmailMessagesCache upsert on temp message delete
- overview contract + quality-guidelines

### Testing

- [OK] node --check static/js/features/emails.js
- [OK] selectEmail detail + loadEmails coalesce contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Clear email soft caches when accounts are deleted

**Branch**: custom

### Summary

Added `clearEmailListCacheForMailbox(es)` so account delete (single/batch/invalid-token governance) drops soft mail list+detail caches for removed mailboxes; soft re-select can no longer paint orphan mail after inventory delete.

### Main Changes

- clearEmailListCacheForMailbox / clearEmailListCacheForMailboxes
- deleteCurrentAccount / deleteAccount / batchDeleteAccounts / invalid-token batch delete
- refreshEmails uses shared list clearer
- overview contract + quality-guidelines

### Testing

- [OK] node --check emails/accounts/main.js
- [OK] account-delete email cache + selectEmail + loadEmails contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Clear email soft caches on account credential/address update

**Branch**: custom

### Summary

`updateAccount` now clears soft mail list+detail caches when email address or mail credentials change (Outlook client_id/refresh_token, IMAP password). Remark-only updates do not force-clear mail soft cache. Tracks original email via `editEmail.dataset.originalValue`.

### Testing

- [OK] node --check accounts/emails/main.js
- [OK] account-delete/update email cache + selectEmail + loadEmails + v190 edit contracts (4 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: DEFAULT alias migration deferred by contract

## 2026-07-13 — Clear email soft caches after account import

**Branch**: custom

### Summary

Successful `addAccount` import now parses candidate emails from the import textarea and clears soft mail list/detail caches for those addresses, preventing soft re-select from painting mail under pre-import credentials after overwrite.

### Testing

- [OK] node --check accounts.js
- [OK] test_account_delete_clears_email_list_soft_cache (includes import path, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Clear email soft caches after token-tool save

**Branch**: custom

### Summary

Token-tool `confirmSaveToAccount` now clears soft mail list/detail for the target mailbox and drops inventory + unified directory soft caches after refresh-token write or create.

### Testing

- [OK] node --check token_tool.js
- [OK] test_token_tool_js_soft_loads_config_and_accounts (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Reset unified preview when directory soft cache invalidates

**Branch**: custom

### Summary

`invalidateUnifiedMailboxDirectoryCache()` now calls `resetUnifiedMessagePreview()` and the reset clears soft signatures/loadForce flags and bumps request/detail/verification seqs so inventory delete/overwrite cannot leave a warm preview of a removed mailbox.

### Testing

- [OK] node --check mailboxes.js
- [OK] unified directory invalidate + module + messages soft-load (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Clear temp message loadForce on mailbox clear/delete

**Branch**: custom

### Summary

Temp mailbox clear/delete now use shared helpers that drop message soft cache, in-flight promises, **and loadForce**, plus detail cache. Delete also invalidates unified directory early so soft re-open cannot paint a removed mailbox.

### Testing

- [OK] node --check temp_emails.js
- [OK] temp messages + detail soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Soft re-entry repaints pool-admin group filter from warm groups

**Branch**: custom

### Summary

`ensurePoolAdminGroupOptions` soft re-entry now re-paints the group filter from warm global `groups` instead of early-returning on `groupOptionsLoaded`, so create/delete/import on other pages is visible without a forced network GET. Force still calls `loadGroups(true)`.

### Testing

- [OK] node --check pool_admin.js
- [OK] pool_admin loader + navigate soft-load contracts (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Soft pool-admin provider filter re-paints warm catalog

**Branch**: custom

### Summary

`ensurePoolAdminProviderOptions` soft path now always re-paints from warm shared catalog before any early-return, so soft catalog updates show up without forceRefresh. Network skip only when already painted and catalog still cold.

### Testing

- [OK] node --check pool_admin.js
- [OK] test_pool_admin_frontend_contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — applyLoadedGroups soft-syncs pool-admin group filter

**Branch**: custom

### Summary

`applyLoadedGroups` now soft-calls `ensurePoolAdminGroupOptions(false)` after `updateGroupSelects()` so the pool-admin group filter stays aligned when groups mutate while that page is open, without a forced network GET.

### Testing

- [OK] node --check groups.js
- [OK] navigate soft-load + load_groups warm contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Catalog soft-paints pool-admin provider filter without second GET

**Branch**: custom

### Summary

`loadMailboxProviderCatalog` warm soft re-entry and success path now call `ensurePoolAdminProviderOptions(false)` so the pool-admin type filter re-paints from the catalog just warmed/written without forcing another `/api/providers` GET.

### Testing

- [OK] node --check main.js
- [OK] test_main_js_loads_provider_catalog_for_config_status (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Soft loadProviders re-paints import select from warm catalog

**Branch**: custom

### Summary

`loadProviders` soft re-entry re-paints the import provider select from warm shared catalog instead of bare early-return; catalog success calls `loadProviders(false)` so the open import modal updates without a second `/api/providers` GET.

### Testing

- [OK] node --check accounts.js + main.js
- [OK] import provider selector + catalog config contracts (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadTags paints batch-tag select from warm allTags

**Branch**: custom

### Summary

`loadTags` warm soft path and network success now call `paintBatchTagSelectFromWarmTags()` so an open batch-tag modal select stays aligned after tag create/delete without a second `/api/tags` GET. `loadTagsForSelect` reuses the same painter.

### Testing

- [OK] node --check main.js
- [OK] test_load_tags_soft_loads_warm_cache (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — ensureLoaded soft re-paints warm plugin list

**Branch**: custom

### Summary

`PluginManager.ensureLoaded` soft re-entry now re-paints the plugin list from warm `_plugins` when the card re-opens, without a second `/api/plugins` GET.

### Testing

- [OK] node --check plugins.js
- [OK] test_temp_email_provider_select_is_catalog_driven (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Soft warm API-security loaders re-paint command center

**Branch**: custom

### Summary

`loadExternalApiContractCheck` and `loadOperationalReadinessSnapshot` soft warm paths now re-paint `renderExternalApiCommandCenter` from warm cache before return, so re-entering the api-security tab does not leave stale/empty command-center chrome while skipping network.

### Testing

- [OK] node --check main.js
- [OK] operational readiness + contract-check console contracts (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Language change re-paints warm soft-load surfaces

**Branch**: custom

### Summary

`ui-language-changed` now re-paints warm soft-load surfaces without network: tags list/filter/batch select, pool-admin group/provider filters, import provider select, open refresh-modal stats/failed/history/invalid-token panels, and visible refresh-log/audit pages (in addition to deployment warnings).

### Testing

- [OK] node --check main.js
- [OK] deployment soft-load + tags soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Unified mailbox language change soft-paints warm directory

**Branch**: custom

### Summary

Unified mailbox `ui-language-changed` now soft-paints warm `directoryPayload` via `applyUnifiedMailboxDirectoryPayload` instead of forcing `loadUnifiedMailboxes(true)`, avoiding an unnecessary network GET on language switch.

### Testing

- [OK] node --check mailboxes.js
- [OK] unified module + messages soft-load contracts (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Standard/temp mailbox language change soft-paints open lists

**Branch**: custom

### Summary

Standard mailbox and temp mailbox modules now soft-paint open email/temp lists (and open detail/messages) on `ui-language-changed` without network, completing language soft-repaint coverage beyond main.js/unified.

### Testing

- [OK] node --check emails.js + temp_emails.js
- [OK] deployment soft-load + temp messages contracts (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Groups language change soft-paints warm inventory chrome

**Branch**: custom

### Summary

Standard groups language handler now soft-paints warm group sidebar, group selects, pool-admin group filter, and account list without network (not only account cards).

### Testing

- [OK] node --check groups.js
- [OK] deployment + groups soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Pool-admin + Token-tool language soft-paint

**Branch**: custom

### Summary

- pool_admin: language change re-paints warm `__poolAdminState.cache` + group/provider filters without `loadPoolAdmin(true)`.
- token_tool: `t()` uses live `window.translateAppText`; language change re-paints scope chips + warm account select; preserves selection.

### Testing

- [OK] node --check pool_admin.js token_tool.js
- [OK] overview + pool loader + token soft-load contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Plugin manager language soft-paint

**Branch**: custom

### Summary

Plugin manager list chrome now uses live `plT()` / `translateAppText` and soft-paints warm `_plugins` on `ui-language-changed` without `loadPlugins({ force: true })`.

### Testing

- [OK] node --check plugins.js i18n.js
- [OK] temp_mail target + overview contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Export group list warm soft-paint

**Branch**: custom

### Summary

Export modal now soft-paints warm `groups` without spinner flash, preserves checkbox selection on language re-paint, and only shows loading on cold `loadGroups(false)`.

### Testing

- [OK] node --check accounts.js
- [OK] export + groups soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Batch tag/move modals warm soft-paint

**Branch**: custom

### Summary

Batch-tag and batch-move selects soft-paint warm allTags/groups without "加载中..." flash; language change soft-paints open batch-move select with selection preserved.

### Testing

- [OK] node --check main.js
- [OK] tags + batch-move + deployment contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Batch-tag modal title language soft-paint

**Branch**: custom

### Summary

Open batch-tag modal title re-translates on language change from batchActionType; batch-move select soft-paint already covered.

### Testing

- [OK] node --check main.js
- [OK] deployment + batch-move contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Version banner language soft-paint

**Branch**: custom

### Summary

Version update banner chrome now translates at paint time; language change soft-paints from warm versionCheckCache without network.

### Testing

- [OK] node --check main.js i18n.js
- [OK] version soft-load + JS contract + deployment (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Refresh modal failed/history i18n soft-paint

**Branch**: custom

### Summary

Refresh-modal failed list and history paint paths now translate empty states, retry, last-refresh, status, and history header so language soft re-paint no longer leaves Chinese chrome.

### Testing

- [OK] node --check main.js i18n.js
- [OK] refresh history + failed list + deployment contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Invalid-token governance + groups empty/search i18n

**Branch**: custom

### Summary

Invalid-token governance summary/count/status/reason chrome and groups empty-email / search loading/error chrome now translate at paint time so language soft re-paint works.

### Testing

- [OK] node --check main.js groups.js i18n.js
- [OK] invalid-token + deployment contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Plugin provider config panel language soft-paint

**Branch**: custom

### Summary

Plugin provider config panel chrome now uses plT; language change soft-paints open form from warm `_activeConfigFields` and live DOM values without network.

### Testing

- [OK] node --check plugins.js i18n.js
- [OK] temp_mail target contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Plugin lifecycle action chrome i18n

**Branch**: custom

### Summary

Plugin install/uninstall/save/test/apply/custom-install action chrome now uses plT for buttons/toasts; confirms keep Chinese source for the i18n confirm wrapper.

### Testing

- [OK] node --check plugins.js i18n.js
- [OK] temp_mail target contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Theme toggle + Settings secret/multi-key hints language soft-paint

**Branch**: custom

### Summary

Theme toggle and Settings external/verification/multi-key secret hints now translate at paint time; language change soft-paints via applyTheme + softPaintSettingsSecretHintsIfOpen while Settings is open.

### Testing

- [OK] node --check main.js i18n.js
- [OK] deployment soft-load contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — CF Worker domain sync chrome i18n

**Branch**: custom

### Summary

CF Worker domain sync success/last-synced/failure labels now use translateAppTextLocal in syncCfWorkerDomains, updateCfWorkerReadonlyFields, and temp-provider action success hints.

### Testing

- [OK] node --check main.js i18n.js
- [OK] settings temp-mail catalog frontend contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Verification AI test + Token refresh completion i18n

**Branch**: custom

### Summary

Verification AI settings validation/test result chrome and batch Token refresh completion toasts now use translateAppTextLocal + i18n patterns.

### Testing

- [OK] node --check main.js i18n.js
- [OK] verification AI probe frontend + refresh/audit soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Mailbox delete/copy + temp generate/delete toast i18n

**Branch**: custom

### Summary

Mailbox email delete/copy toasts and temp-mailbox generate/delete toasts/empty states now use translateAppTextLocal.

### Testing

- [OK] node --check emails.js temp_emails.js i18n.js
- [OK] email detail + temp messages soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Invalid-token governance + batch Token refresh toast i18n

**Branch**: custom

### Summary

Invalid-token governance load/batch action toasts and batch Token refresh progress/error toasts now use translateAppTextLocal; confirms keep Chinese source for the i18n confirm wrapper.

### Testing

- [OK] node --check main.js emails.js i18n.js
- [OK] refresh/audit + invalid-token contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Settings tab switch / auto-save / proxy test / temp-provider action i18n

**Branch**: custom

### Summary

Settings password-discard toast, auto-save failure toast, Telegram proxy connectivity result, and temp-provider action error hint now use translateAppTextLocal.

### Testing

- [OK] node --check main.js i18n.js
- [OK] settings temp-mail catalog frontend contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Temp placeholder compare + provider fallback description i18n

**Branch**: custom

### Summary

Temp mailbox current-name copy no longer hard-compares only Chinese placeholder; provider catalog fallback descriptions translate at paint time.

### Testing

- [OK] node --check temp_emails.js main.js i18n.js
- [OK] temp messages + settings catalog contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Provider fallback descriptions fully translated

**Branch**: custom

### Summary

Remaining temp-mail provider option fallbacks (plugin DOM scrape + currently-saved provider) now use translateAppTextLocal; catalog contract updated.

### Testing

- [OK] node --check main.js i18n.js
- [OK] settings catalog + temp messages contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Full refresh / retry completion toast i18n

**Branch**: custom

### Summary

Full refresh, retry-failed, and single-retry completion toasts now use translateAppTextLocal with Chinese source + patterns instead of getUiLanguage ternaries.

### Testing

- [OK] node --check main.js i18n.js
- [OK] refresh/audit soft-load contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — formatSelectedItemsLabel i18n

**Branch**: custom

### Summary

Batch selected-count label now uses translateAppTextLocal pattern instead of getUiLanguage ternary.

### Testing

- [OK] node --check main.js
- [OK] batch-fetch frontend contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Remove getUiLanguage ternaries for labels/toasts

**Branch**: custom

### Summary

Import summary, verification copy toasts, compact count labels, and temp mailbox (Temp) suffix now use translateAppTextLocal / translateCompactText patterns instead of getUiLanguage ternaries.

### Testing

- [OK] node --check accounts/groups/compact/temp/i18n
- [OK] deployment soft-load contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Confirm dialog missing i18n keys

**Branch**: custom

### Summary

Added i18n exact/pattern keys for account double-confirm delete, trust-mode warning, and invalid-token batch delete danger confirm so the confirm wrapper can translate them.

### Testing

- [OK] node --check i18n.js
- [OK] v190 key email notification translations (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Email detail render/network empty-state i18n

**Branch**: custom

### Summary

Email detail warm/network render failure empty states now use translateAppTextLocal for 邮件渲染失败 / 网络错误，请重试 / 未知错误 / 加载失败.

### Testing

- [OK] node --check emails.js i18n.js
- [OK] email detail soft-load contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Temp messages/detail network empty-state i18n

**Branch**: custom

### Summary

Temp mailbox messages and detail network empty states now use translateAppTextLocal for 网络错误，请重试 / 加载失败.

### Testing

- [OK] node --check temp_emails.js
- [OK] temp messages soft-load contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Account delete / selectAccount empty-state i18n

**Branch**: custom

### Summary

Account delete and selectAccount empty mailbox/detail chrome now use translateAppTextLocal for 请从左侧选择一个邮箱账号 / 选择一封邮件查看详情.

### Testing

- [OK] node --check accounts.js
- [OK] account delete soft-cache contract (exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Group / temp action button title i18n

**Branch**: custom

### Summary

Group edit/delete titles and temp mailbox card action titles now use translateAppTextLocal at paint time.

### Testing

- [OK] node --check groups.js temp_emails.js i18n.js
- [OK] deployment + temp messages contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Folder-aware email list empty chrome

**Branch**: custom

### Summary

Email list empty state is folder-aware: inbox / junk / other folders use distinct translated messages instead of always "收件箱为空".

### Testing

- [OK] node --check emails.js i18n.js
- [OK] v190 i18n helpers + deployment contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Email language change soft-paints empty folder + batch bar

**Branch**: custom

### Summary

Language change now re-paints empty folder email list chrome and email batch selection count labels without network; selected-count fallback uses translateAppTextLocal.

### Testing

- [OK] node --check emails.js
- [OK] deployment + v190 i18n contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Groups empty chrome language soft-paint

**Branch**: custom

### Summary

Language change now re-paints empty group list chrome and empty account-list arrays without requiring groups.length > 0 / truthy accountsCache entries.

### Testing

- [OK] node --check groups.js
- [OK] deployment + groups soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Temp empty inventory/messages language soft-paint

**Branch**: custom

### Summary

Temp mailbox language change now soft-paints empty inventory arrays and empty message lists (not only non-empty warm caches).

### Testing

- [OK] node --check temp_emails.js
- [OK] deployment + temp messages contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Tags empty chrome language soft-paint

**Branch**: custom

### Summary

Language change re-paints empty tag list chrome when tag management modal is open (not only when allTags.length > 0).

### Testing

- [OK] node --check main.js
- [OK] deployment + tags soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Cold folder fetch prompt + language soft-paint

**Branch**: custom

### Summary

Cold folder (no warm list cache) uses shared paintEmailListColdFetchPrompt; language change re-translates that prompt without rewriting it as inbox-empty.

### Testing

- [OK] node --check emails.js main.js
- [OK] deployment + v190 i18n contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadEmails current-view paint guard

**Branch**: custom

### Summary

loadEmails now captures mailbox/folder/method at request start, always warms emailListCache, and paints/errors/loading chrome only while isCurrentEmailListView() so rapid switches cannot clobber the active list.

### Testing

- [OK] node --check emails.js
- [OK] loadEmails coalesce + selectEmail detail contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — selectEmail current-view paint guard

**Branch**: custom

### Summary

selectEmail now captures mailbox/folder/method at request start, always warms emailDetailCache, and paints/errors/loading only while isCurrentMailboxFolderMethod() so rapid switches cannot clobber the active detail pane.

### Testing

- [OK] node --check emails.js
- [OK] selectEmail detail + loadEmails coalesce contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Temp messages/detail current-view paint guard

**Branch**: custom

### Summary

loadTempEmailMessages and getTempEmailDetail now always warm soft caches and paint/error/loading only while still on the same temp mailbox, matching the standard mailbox current-view guards.

### Testing

- [OK] node --check temp_emails.js
- [OK] temp messages + detail soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadTempEmails page-level paint guard

**Branch**: custom

### Summary

loadTempEmails always warms `accountsCache['temp']` but paints loading/list/error only while `isCurrentTempEmailsPage()` (`currentPage === 'temp-emails'`). `renderTempEmailList` no-ops off that page so language soft-repaint and off-page force loads cannot overwrite shared mailbox `#accountList`.

### Testing

- [OK] node --check temp_emails.js
- [OK] load_temp_emails_coalesces_inflight + navigate soft-load contracts (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadAccountsByGroup current-view paint guard

**Branch**: custom

### Summary

loadAccountsByGroup always warms accountsCache/accountListMetaCache but paints loading/list/error only while isCurrentAccountListView() (same currentGroupId + live queryKey). updateAccountListCache accepts syncCurrentPage so stale responses do not rewrite currentAccountPage.

### Testing

- [OK] node --check groups.js
- [OK] load_accounts_by_group_coalesces_inflight + load_temp_emails_coalesces_inflight (2 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadMoreEmails current-view paint guard

**Branch**: custom

### Summary

loadMoreEmails captures mailbox/folder/method/skip and a baseline email snapshot at request start, always upserts emailListCache for that key from the baseline merge, and paints loading/list/error only while still on the same mailbox+folder so mid-flight switches cannot append into the wrong live list.

### Testing

- [OK] node --check main.js
- [OK] load_more_emails_upserts_list_cache + load_emails_coalesces_inflight_by_cache_key (OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Temp inventory dedicated container only

**Branch**: custom

### Summary

loadTempEmails/renderTempEmailList paint only #tempEmailContainer (never shared #accountList). Groups language soft-repaint and catalog provider-tag refresh only touch account cards on standard mailbox page (!isTempEmailGroup).

### Testing

- [OK] node --check temp_emails.js / groups.js / main.js
- [OK] load_temp_emails_coalesces_inflight + load_deployment_info_soft_loads_warm_cache (OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadGroups mailbox sidebar chrome guard

**Branch**: custom

### Summary

loadGroups paints #groupList loading/error only while isCurrentMailboxGroupsSurface() (currentPage === mailbox). Off-page soft/force loads (pool-admin/export) still warm groups data via applyLoadedGroups without flashing the mailbox sidebar. rerenderAccountCaches also stays on standard mailbox surface.

### Testing

- [OK] node --check groups.js
- [OK] load_groups_soft_loads_warm_cache + related contracts (3 OK, exit 0)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Plugins soft-warm + tag modal paint guard

**Branch**: custom

### Summary

loadPlugins soft re-entry when _pluginsLoaded re-paints warm list without network or loading flash. renderTagList only paints #tagList while tag management modal is open (null-safe), so batch soft loadTags can warm allTags without rewriting closed modal DOM.

### Testing

- [OK] node --check plugins.js / main.js
- [OK] load_tags_soft_loads_warm_cache + temp provider catalog/plugin contract (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Log pages + overview tab paint guards

**Branch**: custom

### Summary

loadRefreshLogPage / loadAuditLogPage always warm soft caches but paint loading/list/error only while on refresh-log / audit pages. loadOverviewTab always warms tab cache but paints loading/result/error only while isCurrentOverviewTab() so rapid tab switches cannot flash the wrong pane.

### Testing

- [OK] node --check main.js / overview.js
- [OK] navigate refresh/audit soft-load + overview coalesce + init soft-load (3 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Pool-admin + refresh-modal paint guards

**Branch**: custom

### Summary

loadPoolAdmin always warms soft cache but paints loading/table/error only while isCurrentPoolAdminView() (pool-admin page + same queryKey). Language soft-repaint of the table is also gated to pool-admin. loadRefreshLogs / loadFailedLogs always warm soft caches and paint only while isRefreshModalOpen().

### Testing

- [OK] node --check pool_admin.js / main.js
- [OK] pool-admin loader + refresh modal history + failed list + navigate soft-load (4 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Invalid-token + temp options paint guards

**Branch**: custom

### Summary

loadInvalidTokenGovernanceCandidates always warms candidates soft cache but paints only while isRefreshModalOpen(). loadTempEmailOptions always warms options cache but paints domain/status chrome only while shouldPaintTempEmailOptions() (temp-emails page + matching provider).

### Testing

- [OK] node --check main.js / temp_emails.js
- [OK] invalid-token + temp options + failed list contracts (3 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Refresh-stats + unified directory paint guards

**Branch**: custom

### Summary

loadRefreshStats always warms soft cache but paints only while isRefreshModalOpen(); applyRefreshStats is null-safe. loadUnifiedMailboxes always warms directoryPayload but paints loading/directory/error only while isCurrentUnifiedDirectoryView() (unified mode + mailbox page + matching request signature).

### Testing

- [OK] node --check main.js / mailboxes.js
- [OK] load_refresh_stats + full unified_mailbox_frontend_contract (9 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Unified preview messages/detail/verification paint guards

**Branch**: custom

### Summary

loadUnifiedMailboxMessages / MessageDetail / Verification always warm preview soft state but paint loading/result/error only while isCurrentUnifiedMailboxSurface() so leaving unified mode mid-flight cannot clobber non-unified mailbox UI.

### Testing

- [OK] node --check mailboxes.js
- [OK] unified messages/detail/verification contracts + full unified suite (12 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Deployment info Settings surface paint guard

**Branch**: custom

### Summary

loadDeploymentInfo always warms lastDeploymentInfo but paints warnings/update-method radios only while isSettingsSurfaceActive() via applyDeploymentInfo(deployment, { paint }). Language change re-paints deployment warnings only on Settings surface.

### Testing

- [OK] node --check main.js
- [OK] load_deployment_info_soft_loads_warm_cache (1 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — API-security soft loaders tab paint guard

**Branch**: custom

### Summary

loadOperationalReadinessSnapshot / loadExternalApiContractCheck / loadProviderPreflightSnapshot always warm soft caches but paint command-center/preflight chrome only while isCurrentApiSecuritySurface() (Settings active + api-security tab), so mid-flight tab switches cannot repaint other Settings tabs.

### Testing

- [OK] node --check main.js
- [OK] operational readiness + contract check + preflight contracts (3 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Plugins list paint only when card expanded

**Branch**: custom

### Summary

loadPlugins / ensureLoaded always warm plugin soft state and still run catalog/radio/select side effects, but list/loading/error chrome paints only while shouldPaintPluginList() (_cardExpanded). Language soft-paint also requires the plugin manager card expanded.

### Testing

- [OK] node --check plugins.js
- [OK] temp_email_provider_select_is_catalog_driven (1 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadTags surface paint guards

**Branch**: custom

### Summary

loadTags always warms allTags. renderTagList only when tag management modal open; updateTagFilter only on mailbox page; paintBatchTagSelectFromWarmTags only when batch tag modal open so soft loads from one surface cannot clobber the others.

### Testing

- [OK] node --check main.js
- [OK] load_tags_soft_loads_warm_cache (1 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Export + batch-move modal paint guards

**Branch**: custom

### Summary

paintExportGroupList / loadExportGroupList only paint while isExportModalOpen(). paintBatchMoveGroupSelectFromWarmGroups / loadGroupsForBatchMove only paint while isBatchMoveGroupModalOpen(). Soft loadGroups finishing after close cannot rewrite closed modal DOM.

### Testing

- [OK] node --check main.js / accounts.js
- [OK] batch_move_groups + export_group_list contracts (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — loadTagsForSelect + import provider modal paint guards

**Branch**: custom

### Summary

loadTagsForSelect shows loading/error only while isBatchTagModalOpen(). loadProviders always warms providerOptions but paints #accountProvider only while isAddAccountModalOpen(), so catalog soft re-entry / language change cannot rewrite a closed import form.

### Testing

- [OK] node --check main.js / accounts.js
- [OK] load_tags_soft_loads_warm_cache + import_account_provider_selector_is_catalog_driven (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Token-tool save-dialog account select paint guard

**Branch**: custom

### Summary

loadAccountOptions always warms tokenToolAccountsCache. applyTokenToolAccountOptions and account-select error chrome paint only while isTokenToolSaveDialogOpen() so soft loads finishing after dialog close cannot rewrite closed dialog DOM. Language soft-paint still calls apply (no-ops when closed).

### Testing

- [OK] node --check token_tool.js
- [OK] token_tool_js_soft_loads_config_and_accounts + deployment soft-load (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Token-tool OAuth config soft repaint guard

**Branch**: custom

### Summary

loadOAuthConfig always warms oauthConfigCache. Soft re-entry / soft cold-load paints applyOAuthConfig only when isOAuthConfigFormUnhydrated() (clientId empty) so concurrent soft reloads cannot clobber in-progress form edits. Force always re-paints.

### Testing

- [OK] node --check token_tool.js
- [OK] token_tool_js_soft_loads_config_and_accounts (1 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Pool-admin filter options page paint guard

**Branch**: custom

### Summary

paintPoolAdminGroupOptions and applyPoolAdminProviderOptions only rewrite filter selects while isCurrentPoolAdminPage(). Soft loadGroups/catalog re-entry from settings/plugins/language change cannot clobber hidden pool-admin filters; loadPoolAdmin re-applies when the page opens.

### Testing

- [OK] node --check pool_admin.js
- [OK] pool_admin loader + navigate soft-load contracts (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — syncTempEmailProviderSelectWithCatalog page paint guard

**Branch**: custom

### Summary

syncTempEmailProviderSelectWithCatalog rewrites #tempEmailProviderSelect only while currentPage === temp-emails so catalog soft re-entry from boot/settings/plugins cannot mutate a hidden create-temp select.

### Testing

- [OK] node --check main.js
- [OK] temp_email_provider_select_is_catalog_driven (1 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Temp email provider status page paint guard

**Branch**: custom

### Summary

renderTempEmailProviderStatus paints only while isCurrentTempEmailsPage(). Catalog success also gates the status call to currentPage === temp-emails so boot/settings catalog soft loads cannot rewrite hidden create-temp status badges.

### Testing

- [OK] node --check main.js / temp_emails.js
- [OK] temp provider status + catalog-driven select contracts (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — applyLoadedGroups mailbox surface paint guard

**Branch**: custom

### Summary

applyLoadedGroups always warms the global groups array and shared selects/filters, but paints #groupList / compact strip and account-inventory refresh only while isCurrentMailboxGroupsSurface(). renderGroupList itself no-ops off mailbox. Language soft-paint of group list is also gated.

### Testing

- [OK] node --check groups.js
- [OK] load_groups + export + batch-move contracts (3 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Group selects + compact strip surface paint guards

**Branch**: custom

### Summary

updateGroupSelects rewrites importGroupSelect/editGroupSelect only while addAccountModal/editAccountModal are open. renderCompactGroupStrip paints only on mailbox compact mode; language soft-paint of compact account list uses the same surface check.

### Testing

- [OK] node --check groups.js / mailbox_compact.js
- [OK] load_groups + compact module contracts (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-13 — Account list renderer surface paint guards

**Branch**: custom

### Summary

renderAccountList no-ops unless currentPage is mailbox, not temp group, and not unified mode. renderCompactAccountList no-ops unless mailbox compact mode. Defense-in-depth for catalog/language soft re-paints.

### Testing

- [OK] node --check groups.js / mailbox_compact.js
- [OK] load_groups + compact module contracts (2 OK)
- [OK] git diff --check (exit 0)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

## 2026-07-14 — Cancel late edit-account/group modal paints

**Branch**: custom

### Summary

Late soft/network detail responses for showEditAccountModal / editGroup could re-open the edit (or shared add/edit group) modal after hide. Track paint targets (editAccountPaintTargetId / editGroupPaintTargetId) and only apply form paint while the open request still matches; cold success still warms accountDetailCache / groups list rows. hide and showAddGroupModal clear targets.

### Main Changes

- static/js/features/accounts.js paint-target cancel
- static/js/features/groups.js paint-target cancel + list row warm
- tests/test_overview_frontend_contract.py paint-cancel contracts
- .trellis/spec/frontend/quality-guidelines.md soft-load bullets

### Git Commits

| Hash | Message |
|------|---------|
| 681d3f5c | fix: cancel late edit-account/group modal paints after hide |

### Testing

- [OK] 4 focused overview frontend contracts (paint-cancel + soft-load pairs)
- [OK] node --check accounts.js / groups.js
- [OK] git diff --check (clean worktree after commit)

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration deferred by contract)
- Soft-load surface paint-guard stream: edit modal late re-open class closed; lower-risk page-local status/helpers remain
- Next high-value residual: re-scan after this unit (no unguarded soft-modal re-open of same class found)

## 2026-07-14 — Gate loadTags error toast to active tag surfaces

**Branch**: custom

### Summary

loadTags always warmed allTags and painted only via surface-gated helpers, but network errors still showToast even after all tag consumer surfaces closed. isActiveTagLoadSurface() gates the error toast to tag management modal, batch-tag modal, or mailbox page.

### Main Changes

- static/js/main.js isActiveTagLoadSurface + loadTags catch guard
- tests/test_overview_frontend_contract.py loadTags toast surface contract
- .trellis/spec/frontend/quality-guidelines.md loadTags bullet

### Testing

- [OK] test_load_tags_soft_loads_warm_cache
- [OK] node --check main.js
- [OK] git diff --check

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration deferred)
- Soft-load stream: edit modal paint-cancel + tags toast surface done; lower-risk page-local helpers remain

## 2026-07-14 — Gate loadSettings error toast to Settings surface

**Branch**: custom

### Summary

loadSettings could toast load-settings-failed after navigate away or modal close. Toast only while isSettingsSurfaceActive(); console.error still always logs.

### Main Changes

- static/js/main.js loadSettings catch surface guard
- tests/test_overview_frontend_contract.py settings soft-load toast contract
- .trellis/spec/frontend/quality-guidelines.md Settings soft-load bullet

### Testing

- [OK] test_navigate_soft_loads_settings_page
- [OK] node --check main.js
- [OK] git diff --check

### Status

[OK] **Completed unit** (continuous goal — not FINAL_CLOSE)

### Next Steps

- Residual: stored DEFAULT still custom_domain_temp_mail (migration deferred)
- Soft-load stream: toast surface guards for tags + settings done
