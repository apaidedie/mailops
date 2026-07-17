# Quality Guidelines



> Code quality standards for frontend development.



---



## Overview

Frontend quality is contract-driven. The app is a dense operational workspace, so visual changes must preserve scanability, responsive integrity, accessibility hooks, and backend-owned discovery contracts. Static HTML/CSS/JS text tests are normal in this repository and should be updated alongside UI changes.


---



## Forbidden Patterns



<!-- Patterns that should never be used and why -->



### Production Debug Console Output



Production static scripts must not leave `console.log(...)` or `console.debug(...)` calls. They make browser consoles noisy and can accidentally expose operational state while users are debugging real failures.



Keep `console.warn(...)` and `console.error(...)` only for actionable failure paths. Silent browser compatibility fallbacks should use a short code comment instead of logging expected noise.



Frontend contract tests should assert production scripts stay free of `console.log(` and `console.debug(` when cleanup touches shared UI files.



#### Wrong



```javascript

console.log('刷新统计数据:', data);

console.debug('[poll-engine] startPoll called for:', email);

```



#### Correct



```javascript

if (!response.ok) {

  console.error('加载刷新统计失败:', error);

}

```



---



## Required Patterns

## Scenario: Local Demo Workspace First-Run Strip

### 1. Scope / Trigger

Trigger: frontend changes that render, move, relabel, or add actions to the local demo workspace first-run strip that consumes `/api/bootstrap.demo_workspace`.

### 2. Signatures

- `templates/index.html -> #demoWorkspaceStrip`
- `static/js/main.js -> window.__appBootstrap`
- `static/js/main.js -> renderDemoWorkspaceStrip()`
- `static/js/main.js -> handleDemoWorkspaceAction(actionKey)`
- `static/css/main.css -> .demo-workspace-*`
- `GET /api/bootstrap -> bootstrap.demo_workspace`

### 3. Contracts

The demo strip is a page-shell display adapter over `bootstrap.demo_workspace`. It must render only when `demo_workspace.enabled === true`, and it must hide/clear itself for ordinary deployments. It may show the safe relative demo database label and synthetic-data posture, but it must not show absolute paths, environment values, provider bearer tokens, API keys, task tokens, claim tokens, mailbox passwords, or message content.

Quick actions must use existing navigation primitives such as `navigate(page)`, `switchOverviewTab(tab)`, and `switchSettingsTab(tab)`. Do not add a second router, call external API endpoints from the browser, or duplicate provider-selection/readiness logic in the strip. Dynamic labels and backend-provided fields must be escaped before entering `innerHTML`.

The strip is a restrained operational affordance, not a landing hero. It should sit near the topbar, use existing CSS tokens, keep dimensions stable, and collapse into a mobile-safe grid without page-level or strip-level horizontal overflow.

### 4. Validation & Error Matrix

- Bootstrap succeeds with enabled demo -> strip appears and quick actions route to Overview, Unified mailbox, Temp mailboxes, External API tab, and Provider settings tab.
- Bootstrap disabled or missing field -> strip remains hidden without throwing.
- Language changes -> strip rerenders labels without reading form inputs.
- Mobile viewport -> action buttons wrap within the strip; page overflow and strip overflow stay zero.
- Backend adds an unknown action -> ignore or fall back to known action descriptors; do not create provider-specific branches.

### 5. Good/Base/Bad Cases

- Good: `renderDemoWorkspaceStrip()` reads `window.__appBootstrap.demo_workspace`, escapes labels, and delegates action clicks to existing navigation functions.
- Base: if `switchOverviewTab` is unavailable during early startup, the strip still renders and ordinary page navigation works.
- Bad: reading `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey` to build copy or quick actions.
- Bad: putting the demo experience in a marketing-style hero that pushes the operational dashboard out of the first viewport.

### 6. Tests Required

- Frontend contract tests must assert the DOM mount point, JS helper names, bootstrap cache assignment, click data attribute, CSS hooks, mobile selectors, and secret-safety slices.
- Backend/bootstrap tests must cover enabled and disabled `demo_workspace` payloads.
- Browser QA is required for visual changes and must inspect desktop/mobile page overflow plus strip overflow, then verify quick-action routing.

### 7. Wrong vs Correct

#### Wrong
```javascript
const key = document.getElementById('settingsDuckmailBearerToken').value;
root.innerHTML = `<div>${key}</div>`;
```

#### Correct
```javascript
const demo = window.__appBootstrap?.demo_workspace || { enabled: false };
if (demo.enabled) renderDemoWorkspaceStrip();
```

## Scenario: Overview External API Operations Console

### 1. Scope / Trigger

Trigger: frontend changes that render Dashboard -> External API operational usage, caller health, endpoint health, external API trend panels, or any UI consuming `/api/overview/external-api`.

### 2. Signatures

- `templates/index.html -> #ov-external-api-body`
- `static/js/features/overview.js -> renderExternalApiStats(data)`
- `static/js/features/overview.js -> renderExternalApiHealthStrip(health, kpi)`
- `static/js/features/overview.js -> renderExternalApiEndpointHealth(items)`
- `static/css/main.css -> .ov-api-health-*`
- `static/css/main.css -> .ov-endpoint-health-*`

### 3. Contracts

The Overview external API tab is an operations display adapter over authenticated admin data from `/api/overview/external-api`. It may render `kpi`, `health`, `daily_series`, `by_endpoint`, `endpoint_health`, and `caller_rank` fields returned by the overview repository. It must not call `/api/external/*` from the browser, must not read Settings credential inputs, and must not reconstruct usage or provider selection rules in JavaScript.

Dynamic endpoint names, caller labels, consumer identifiers, status values, and timestamps must be escaped before insertion into `innerHTML`. JavaScript may provide display-only fallbacks for missing fields, but repository/API projections own count aggregation, health status, error rates, top error caller, and top error endpoint.

The surface must remain a dense operational dashboard: KPI row first, followed by health/risk signals, trend/distribution panels, endpoint health, and caller health. It must use existing Overview cards/tables/tokens and avoid structural emoji, hover-only explainers, nested decorative cards, one-off palettes, or marketing hero treatment.

### 4. Validation & Error Matrix

- Empty `week_calls` and empty lists -> show zero KPI values, `idle`/no-call health state, and explicit empty states without throwing.
- Erroring endpoint rows -> show endpoint error count/rate and warning tone without changing layout bounds.
- Missing `endpoint_health` in an older payload -> fall back to `by_endpoint` for compatibility.
- Long endpoint paths or caller names -> wrap inside cards or scroll only inside `.data-table-shell`; page and `#ov-external-api-body` must not gain horizontal overflow.
- Browser or language change re-render -> labels translate at render time and do not read secret inputs.
- Payload contains unexpected status text -> render escaped text or a safe mapped label, never raw HTML.

### 5. Good/Base/Bad Cases

- Good: `renderExternalApiStats()` reads `data.health || {}` and `data.endpoint_health` and delegates to dedicated render helpers.
- Good: endpoint/caller strings are passed through `esc(...)` before becoming markup.
- Base: mobile caller tables may scroll within `.data-table-shell` while page-level and overview-body overflow remain zero.
- Bad: reading `settingsExternalApiKey`, `settingsExternalApiKeysJson`, provider bearer-token inputs, task tokens, or claim tokens to build this console.
- Bad: using the Overview tab to call API-key-protected `/api/v1/external/*` endpoints from the admin browser.

### 6. Tests Required

- Frontend contract tests must assert renderer helper names, CSS hooks, i18n labels, and secret-safety slices.
- API/repository tests must cover populated and empty overview payloads when the frontend consumes new fields.
- Browser QA is required for material layout changes and must inspect desktop and mobile page-level overflow, `#ov-external-api-body` overflow, `.overview-tab-shell` overflow, and deliberate table-shell overflow separately.

### 7. Wrong vs Correct

#### Wrong

```javascript
const key = document.getElementById('settingsExternalApiKey').value;
const health = await fetch('/api/v1/external/health', { headers: { 'X-API-Key': key } });
```

#### Correct

```javascript
const health = data.health || {};
const endpointHealth = Array.isArray(data.endpoint_health) ? data.endpoint_health : byEndpoint;
return renderExternalApiHealthStrip(health, kpi);
```

## Scenario: Overview Unified Mailbox Command Center UI

### 1. Scope / Trigger

Trigger: frontend changes that render Dashboard -> Summary unified mailbox readiness, provider readiness, external API readiness, or next actions from `/api/overview/summary.command_center`.

### 2. Signatures

- `static/js/features/overview.js -> renderOverviewSummary(data)`
- `static/js/features/overview.js -> renderOverviewCommandCenter(commandCenter)`
- `static/js/features/overview.js -> renderOverviewCommandTile(options)`
- `static/js/features/overview.js -> renderOverviewCommandActions(actions)`
- `static/css/main.css -> .ov-command-center*`
- `GET /api/overview/summary -> command_center`

### 3. Contracts

The summary command center is a display adapter over authenticated admin data from `/api/overview/summary.command_center`. It must render before the existing KPI row so the first viewport answers whether unified mailbox aggregation is usable.

The frontend may render `overall_status`, `mailbox_inventory`, `provider_readiness`, `external_api`, and bounded `actions`. It must not call `/api/external/*`, `/api/mailboxes`, or provider endpoints to recompute readiness from the browser. It must not read Settings credential inputs or rebuild provider selection logic in JavaScript.

Dynamic labels, status text, action details, and action targets must be escaped before insertion into `innerHTML`. User-visible strings must pass through `ovT(...)`/`i18n.js`. The UI must stay operational and data-dense: token surfaces, stable tiles, responsive collapse, no structural emoji, no decorative gradients, no nested cards inside existing `renderDataCard` cards.

### 4. Validation & Error Matrix



- Missing `command_center` on older payload -> render an unknown/degraded command-center shell without throwing.

- Empty mailbox inventory -> show zero counts and a directory-empty/needs-action status without page overflow.

- Provider needs config -> show warning tone and bounded next actions from the API payload.

- Long endpoint/action target -> wrap inside `.ov-command-action-main code` without page-level, shell-level, summary-body, or command-center horizontal overflow.

- Language change -> rerender labels from i18n without reading Settings inputs.

- Dashboard re-entry with warm tab cache -> `initOverview()` soft-loads via `switchOverviewTab` and must not force `/api/overview/*`.

- `loadOverviewTab(tabId, forceReload=false)` soft-loads warm `__overviewState.cache[tabId]`; concurrent soft loads coalesce via `__overviewState.loadPromises[tabId]`; force joins only force in-flight (`loadForce`) and supersedes a soft in-flight so Refresh / `overview-data-changed` always start a true network GET; always warm tab soft cache and paint/loading/error only while `isCurrentOverviewTab()` (`activeTab === targetTab`); `invalidateOverviewCache` clears cache + in-flight bookkeeping for targeted tabs.

- `checkVersionUpdate(forceRefresh=false)` soft-loads warm session `versionCheckCache` and coalesces concurrent checks via `versionCheckLoadPromise`; boot `setTimeout(checkVersionUpdate, 5000)` stays soft; `applyVersionCheckPayload` owns banner paint.

- `navigate('temp-emails')` / `navigate('pool-admin')` soft-load via `loadTempEmails(false)` / `loadPoolAdmin(false)` so warm `accountsCache['temp']` / `__poolAdminState.cache` paint without a forced network burst; create/delete/filter/refresh handlers still pass `forceRefresh=true`.

- `loadPoolAdmin` soft-loads only when `cacheQueryKey` matches `getPoolAdminQueryKey()` (filters/page); soft joins any in-flight for the same query signature and force joins only force (`__poolAdminState.loadForce`) and supersedes soft so abandoned soft responses do not repaint; always warm soft cache and paint/loading/error only while `isCurrentPoolAdminView()` (`currentPage === 'pool-admin'` and live queryKey still matches the request); language soft-repaint of the table requires `isCurrentPoolAdminPage()`; mutations/filter/page pass `forceRefresh=true`.

- `ensurePoolAdminProviderOptions(forceRefresh)` soft re-paints warm `mailboxProviderCatalogCache` only while `isCurrentPoolAdminPage()` (via `applyPoolAdminProviderOptions`); force always calls `loadMailboxProviderCatalog(true)` (or force when warm-empty). Soft may skip network only when already painted and catalog is still cold.

- `loadMailboxProviderCatalog` success and warm soft re-entry must call `ensurePoolAdminProviderOptions(false)` (not `true`) so pool-admin type filter re-paints from the catalog just written/warmed without a second `/api/providers` GET.

- `loadProviders(forceRefresh)` soft re-entry (`providersLoaded && !force`) must warm import options from `mailboxProviderCatalogCache` before return and paint `#accountProvider` only while `isAddAccountModalOpen()`; catalog success calls `loadProviders(false)` (not `true`) to avoid a second `/api/providers` GET.

- `syncTempEmailProviderSelectWithCatalog()` rewrites `#tempEmailProviderSelect` only while `currentPage === 'temp-emails'` so catalog soft re-entry from boot/settings/plugins cannot mutate a hidden create-temp select.

- `renderTempEmailProviderStatus` paints `#tempEmailProviderStatus` only while `isCurrentTempEmailsPage()` / `currentPage === 'temp-emails'`; catalog success must not call it off that page.

- `ensurePoolAdminGroupOptions(forceRefresh)` soft re-entry re-paints from warm global `groups` without network only while `isCurrentPoolAdminPage()` (via `paintPoolAdminGroupOptions`); force calls `loadGroups(true)`. Soft must not early-return without re-paint once `groupOptionsLoaded` is true **and** the user is on pool-admin, or create/delete on other pages leaves a stale group filter when returning.

- `applyLoadedGroups` must soft-call `ensurePoolAdminGroupOptions(false)` after `updateGroupSelects()` so pool-admin group filter stays aligned when groups mutate while that page is open (no force GET).

- `ensurePoolAdminGroupOptions` must reuse warm `groups` / soft `loadGroups(false|true)` and must not raw-fetch `/api/groups`.

- `loadTempEmails` soft-loads warm `accountsCache['temp']`; soft joins any in-flight and force joins only force (`tempEmailsLoadForce`) and supersedes soft so generate/delete always start a true network GET. Always warm inventory cache; paint/loading/error only while `isCurrentTempEmailsPage()` (`currentPage === 'temp-emails'`), and **only** into `#tempEmailContainer` — never dual-paint shared mailbox `#accountList`.

- `loadTempEmailOptions(forceRefresh, providerName)` soft-loads warm `tempEmailOptionsCache` per provider cacheKey; soft joins any in-flight for the same cacheKey and force joins only force (`tempEmailOptionsLoadForce[cacheKey]`) and supersedes soft so provider switch/refresh starts a true GET `/api/temp-emails/options`. Always warm options soft cache; paint domain/status chrome only while `shouldPaintTempEmailOptions()` (temp-emails page + live provider still matches request).

- `invalidateTempEmailOptionsCache()` clears options soft cache + in-flight bookkeeping and bumps `tempEmailOptionsRequestSeq`; call after Settings save / temp-mail auto-save, plugin config save / applyChanges, and `loadTempEmails(true)` so domain options never soft-paint stale credentials.

- `loadTempEmailMessages(email, forceRefresh=false)` soft-loads warm `tempEmailMessagesCache` by mailbox email; soft joins any in-flight and force joins only force (`tempEmailMessagesLoadForce[email]`) and supersedes soft (keeps requestSeq stale guard); select uses soft load; explicit refresh passes `forceRefresh=true`.

- Temp mailbox clear/delete must use `seedEmptyTempEmailMessagesCache` / `clearTempEmailMessagesCacheForMailbox` so message cache, loadPromises, **and loadForce** drop together with detail cache; delete also invalidates unified directory soft cache.

- `getTempEmailDetail(messageId, index, forceRefresh=false)` soft-loads warm `tempEmailDetailCache` by `mailbox|messageId` and coalesces concurrent loads via `tempEmailDetailLoadPromises`; row click soft-selects; force message-list refresh / clear / delete mailbox call `clearTempEmailDetailCacheForMailbox`; single-message delete drops that detail cache key.

- `loadEmails(email, forceRefresh)` soft-loads warm `emailListCache[email_folder]`; soft joins any in-flight and force joins only force (`emailsLoadForce[cacheKey]`) and supersedes soft for the same cacheKey.

- `deleteEmails` / temp message delete must upsert soft list caches (`emailListCache[account_folder]` / `tempEmailMessagesCache`) from the post-delete `currentEmails` so `loadEmails(false)` / soft temp re-select cannot repaint deleted rows; detail cache invalidation alone is not enough.

- Account inventory delete (single / batch / invalid-token governance) must call `clearEmailListCacheForMailbox(es)` so soft mail list+detail for removed mailboxes cannot be re-selected after the account is gone; also drop unified directory soft cache.

- Account update that changes email address or mail credentials (Outlook client_id/refresh_token, or IMAP password) must clear soft mail caches for previous/next address via `clearEmailListCacheForMailbox`; remark-only updates must not force-clear mail list soft cache.

- Account import success (`addAccount`) must call `clearEmailListCacheForMailboxes(extractImportCandidateEmails(input))` so overwrite/import of existing addresses cannot soft-paint pre-import credentials; also drop unified directory soft cache.

- Token tool `confirmSaveToAccount` success must clear soft mail caches for the target mailbox (`clearEmailListCacheForMailbox`) and drop inventory/unified directory soft caches after refresh-token write or create.

- `loadMoreEmails` captures `targetEmail`/`targetFolder`/`targetMethod`/`requestSkip` at request start, merges against a baseline snapshot (not live `currentEmails`), always upserts `emailListCache[targetEmail_targetFolder]` (`emails` / `has_more` / `skip` / `method`) so soft re-select via `loadEmails(false)` keeps already-paginated rows even when the user navigated away, and paints loading/list/error only while `isCurrentEmailListView()` so rapid mailbox/folder switches cannot append a page into the wrong live list.

- Compact pull `refreshCompactAccount` seeds `emailListCache` for inbox/junkemail via `cacheBatchFetchedFolder` (fallback upsert) and clears `emailDetailCache` for those folders so standard-view soft-load reuses compact pull pages without stale detail.

- Poll engine `startPoll` baseline + `pollSingleEmail` success paths seed `emailListCache` for inbox/sentitems via `seedPollEmailListCache` (`cacheBatchFetchedFolder` preferred) and clear matching `emailDetailCache` so opening the mailbox soft-loads warm poll pages.

- `selectEmail(messageId, index, forceRefresh=false)` soft-loads warm `emailDetailCache` by `account|folder|method|messageId` and coalesces concurrent loads via `emailDetailLoadPromises`; row click soft-selects; force list refresh / `refreshEmails` call `clearEmailDetailCacheForMailbox`; delete drops matching detail cache keys.

- Unified mailbox re-entry: `switchMailboxViewMode('unified')` / `loadUnifiedMailboxes(false)` soft-loads when `directorySignature` matches `getUnifiedMailboxRequestSignature()` and `directoryPayload` is warm; filter/search/page/refresh still call `loadUnifiedMailboxes(true)`. Soft joins any same-signature in-flight; force joins only force (`directoryLoadForce`) and supersedes soft by bumping `directoryLoadSeq` so abandoned soft responses do not write `directoryPayload`. Always warm directory soft cache; paint loading/directory/error only while `isCurrentUnifiedDirectoryView()` (`mailboxViewMode === 'unified'`, mailbox page, and live request signature still matches).

- Unified mailbox message preview: `loadUnifiedMailboxMessages` soft-loads when the same `messagesSignature` (key|folder|skip|top) is warm and `!options.force`; soft joins any in-flight for the same signature and force joins only force (`preview.messagesLoadForce`) and supersedes soft so abandoned soft responses do not repaint; always warm preview soft state and paint loading/list/error only while `isCurrentUnifiedMailboxSurface()`; refresh/retry buttons pass `{ force: true }`; `openUnifiedMessagePreview` soft-opens (`force: false`).

- Unified mailbox message detail: `loadUnifiedMailboxMessageDetail` soft-loads when the same `detailSignature` (key|folder|messageId) is warm and `!options.force`; soft joins any in-flight for the same signature and force joins only force (`preview.detailLoadForce`) and supersedes soft; always warm detail soft state and paint only while `isCurrentUnifiedMailboxSurface()`; row click soft-selects; retry and post-list auto-select pass `{ force: true }`; list refresh clears `detailSignature`.

- Unified mailbox verification: `loadUnifiedMailboxVerification` soft-loads when the same `verificationSignature` (key|folder) is warm and `!options.force`; soft joins any in-flight for the same signature and force joins only force (`preview.verificationLoadForce`) and supersedes soft; always warm verification soft state and paint only while `isCurrentUnifiedMailboxSurface()`; extract button passes `{ force: true }`; list refresh / detail load clear `verificationSignature`.

- Account/temp inventory force-refresh (`loadAccountsByGroup(..., true)` / `loadTempEmails(true)`) must call `window.invalidateUnifiedMailboxDirectoryCache()` so soft re-entry does not paint stale directory rows.

- `invalidateUnifiedMailboxDirectoryCache()` must also `resetUnifiedMessagePreview()` (clear selected mailbox, messages/detail/verification soft signatures + in-flight flags, bump seqs) so inventory delete/overwrite cannot leave a warm preview of a removed mailbox.

- `navigate('refresh-log')` / `navigate('audit')` soft-load via `loadRefreshLogPage()` / `loadAuditLogPage()` using `refreshLogPageCache` / `auditLogPageCache`; soft joins any in-flight and force joins only force (`refreshLogPageLoadForce` / `auditLogPageLoadForce`) and supersedes soft so abandoned soft responses do not repaint; always warm soft cache and paint/loading/error only while `isCurrentRefreshLogPage()` / `isCurrentAuditLogPage()`; invalidate refresh-log cache after full/selected/retry refresh success paths; invalidate audit soft cache (`window.invalidateAuditLogPageCache`) after settings save/auto-save, inventory force-refresh, and refresh success paths; pass `forceRefresh=true` to force network.

- `navigate('settings')` / `showSettingsModal` soft-load via `loadSettings()` using `settingsPageCache` for the last successful GET `/api/settings`; soft joins any in-flight and force joins only force (`settingsPageLoadForce`) via `fetchSettingsPagePayload`, with force superseding soft (generation bump); `saveSettings` / `autoSaveSettings` / layout PUT invalidate the cache; `refreshTempMailSettingsSnapshotFromServer` / `initPollingSettings` fallback / `triggerUpdate` read through `fetchSettingsPagePayload` (force only when server truth must refresh after write); network error toast only while `isSettingsSurfaceActive()` so soft loads finishing after navigate away / modal close stay silent (console.error still always logs)

- Cold cache / first boot -> `switchOverviewTab` still fetches the active tab endpoint once.

- Refresh button or `overview-data-changed` while Dashboard is active -> force-reload remains required.

- Boot `DOMContentLoaded` -> must not eagerly call `loadGroups()` / `loadTags()`; mailbox navigate and tag modal load them on demand.

- `loadGroups(forceRefresh=false)` soft-loads when the in-memory `groups` array is non-empty (re-render only via `applyLoadedGroups(..., { refreshAccounts: false })`); soft joins any in-flight and force joins only force (`groupsLoadForce`) and supersedes soft; create/delete/import/move/batch mutations must call `loadGroups(true)`. Loading/error chrome for `#groupList` only while `isCurrentMailboxGroupsSurface()` (`currentPage === 'mailbox'`) so pool-admin / export / batch-move cold loads do not flash the mailbox sidebar spinner. `applyLoadedGroups` always warms the global `groups` array, but paints `#groupList` / compact strip and account-inventory refresh only while on the mailbox surface. `updateGroupSelects` rewrites `importGroupSelect` / `editGroupSelect` only while the owning modal (`addAccountModal` / `editAccountModal`) is open. `renderCompactGroupStrip` / `renderCompactAccountList` paint only while `currentPage === 'mailbox'` and `mailboxViewMode === 'compact'`. `renderAccountList` paints shared `#accountList` only while on mailbox, not temp group, and not unified mode.

- `editGroup(groupId, forceRefresh=false)` soft-loads the edit modal from the warm `groups` array when the row is present; concurrent cold GET `/api/groups/<id>` coalesce via `groupDetailLoadPromises`; `editGroupPaintTargetId` + `shouldPaintEditGroupForm` cancel late paint after `hideAddGroupModal` / `showAddGroupModal` so abandoned responses cannot re-open or clobber the shared add/edit modal; cold success may still warm the matching `groups` list row; save/delete still force-refresh the list.

- `loadGroupsForBatchMove` must reuse warm `groups` / soft `loadGroups(false)` and must not raw-fetch `/api/groups`.

- `loadExportGroupList` must soft-load cold groups via `loadGroups(false)` then paint from warm `groups` (no raw GET).

- `loadAccountsByGroup` soft-loads warm `accountsCache[groupId]` when queryKey matches **and** `accountListMetaCache[groupId].queryKey` matches; soft joins any in-flight and force joins only force (`accountsByGroupLoadForce[queryKey]`) and supersedes soft for the same queryKey. Always warm inventory cache via `updateAccountListCache`; paint/loading/error and `currentAccountPage` sync only while `isCurrentAccountListView()` (same `currentGroupId` + live `buildAccountListQueryKey` matches the request queryKey) so rapid group/page/filter switches cannot clobber the active `#accountList` or rewrite the live page cursor from a stale response.

- `invalidateAccountsCache(groupId?)` owns inventory soft-cache drops: clears `accountsCache` + `accountListMetaCache` (+ in-flight maps for that group). Mutations must call this helper instead of bare `delete accountsCache[...]` so pagination meta cannot soft-match a deleted list.

- `showEditAccountModal(accountId, forceRefresh=false)` soft-loads warm `accountDetailCache` from a prior GET `/api/accounts/<id>` only (never from list `accountsCache` rows — list truncates `client_id`); concurrent cold loads coalesce via `accountDetailLoadPromises`; `editAccountPaintTargetId` + `shouldPaintEditAccountForm` cancel late paint after `hideEditAccountModal` so abandoned soft/network responses still warm the detail cache but cannot re-add `#editAccountModal.show`; update/remark/delete/status mutations call `invalidateAccountDetailCache`; batch delete/status/move/tag paths call `window.invalidateAccountDetailCacheMany(accountIds)`.

- `loadTags(forceRefresh=false)` soft-loads when `allTags` is non-empty; soft joins any in-flight and force joins only force (`tagsLoadForce`) and supersedes soft; create/delete must call `loadTags(true)`; `loadTagsForSelect` reuses warm `allTags` / soft `loadTags(false)` and must not raw-fetch `/api/tags`. Always warm soft cache and paint via surface-gated helpers (`renderTagList` / `updateTagFilter` / `paintBatchTagSelectFromWarmTags`); network error toast only while `isActiveTagLoadSurface()` (tag management modal, batch-tag modal, or mailbox page) so soft loads finishing off those surfaces stay silent.

- `loadTags` warm soft path and network success must call `paintBatchTagSelectFromWarmTags()` so an open batch-tag modal select stays aligned after create/delete without a second `/api/tags` GET.

- `renderTagList` paints `#tagList` only while `isTagManagementModalOpen()` so batch-tag soft `loadTags(false)` can warm `allTags` without rewriting closed tag-management modal DOM (null-safe when `#tagList` missing).

- `updateTagFilter` paints mailbox `#tagFilterContainer` only while `currentPage === 'mailbox'`. `paintBatchTagSelectFromWarmTags` rewrites `#batchTagSelect` only while `isBatchTagModalOpen()` so soft `loadTags` from other surfaces cannot clobber closed batch-tag select or off-page mailbox filter chrome.
- `loadProviderPreflightSnapshot(forceRefresh, probeNetwork)` soft-loads warm `providerPreflightCache`; soft joins any in-flight and force/probe joins only force (`providerPreflightLoadForce`) and supersedes soft so abandoned soft responses do not write cache. Always warm soft cache; paint loading/ready/error console only while `isCurrentApiSecuritySurface()`.

- `loadRefreshStats(forceRefresh=false)` soft-loads via `refreshStatsCache` + `refreshStatsLoadPromise`; always warm soft cache and paint only while `isRefreshModalOpen()`; `applyRefreshStats` is null-safe when modal DOM is missing; `showRefreshModal` uses soft load; retry/single-refresh/batch-delete/invalid-token governance force-refresh; full refresh complete updates cache from the completed run; selected-batch complete invalidates stats cache.

- Failed refresh list: `fetchFailedRefreshLogs` owns the only raw GET `/api/accounts/refresh-logs/failed`; `autoLoadFailedListIfNeeded` and `loadFailedLogs` soft-load via shared cache/coalesce; `loadFailedLogs` paints only while `isRefreshModalOpen()` so retries that finish after modal close cannot show/hide modal panels; `showFailedListFromData` / `hideFailedList` seed or clear the soft cache; single-account retry calls `loadFailedLogs(true)`.

- Refresh modal history: `loadRefreshLogs(forceRefresh=false)` soft-loads via `refreshModalHistoryCache` (limit=1000, separate from page `refreshLogPageCache` limit=200); always warm soft cache and paint only while `isRefreshModalOpen()`; `invalidateRefreshLogPageCache` clears both page and modal history caches after refresh mutations.

- Invalid-token governance: `loadInvalidTokenGovernanceCandidates({ forceRefresh })` soft-loads when `invalidTokenGovernanceCandidatesLoaded` is true; soft joins any in-flight and force joins only force (`invalidTokenGovernanceLoadForce`) and supersedes soft so abandoned soft responses do not apply; always warm candidates soft cache and paint only while `isRefreshModalOpen()`; `resetInvalidTokenGovernanceState` only hides UI (does not clear soft cache); batch inactive/refresh complete force-refresh; batch delete calls `invalidateInvalidTokenGovernanceCache()`.

- Boot must not synchronously call `Notification.requestPermission()`; use `scheduleBrowserNotificationPermissionPrompt()` (first gesture + late idle fallback).

- `ui-language-changed` must re-paint warm soft-load surfaces without network: deployment warnings, tags list/filter/batch select (including empty tags when tag management modal is open), pool-admin group/provider filters, import provider select, open refresh-modal stats/failed/history/invalid-token panels, and visible refresh-log/audit pages.

- Unified mailbox language change must soft-paint warm `directoryPayload` via `applyUnifiedMailboxDirectoryPayload` (not `loadUnifiedMailboxes(true)`), plus workspace switcher/preview chrome.

- Standard mailbox language change must soft-paint open `currentEmails` / `currentEmailDetail` via `renderEmailList` / `renderEmailDetail` without network (including empty folder chrome when `.empty-state` is visible) and re-run `updateEmailBatchActionBar()` so selected-count labels re-translate; temp mailbox language change must soft-paint warm `accountsCache['temp']` (including empty arrays) and current temp messages (including empty lists) without network.

- Standard groups language change must soft-paint warm `groups` via `renderGroupList` / `updateGroupSelects` / `ensurePoolAdminGroupOptions(false)` without network — including empty group list chrome when `.empty-state` is visible. Warm `accountsCache[currentGroupId]` via `renderAccountList` only when `currentPage === 'mailbox'` and `!isTempEmailGroup`.

- Pool-admin language change must soft-paint warm `__poolAdminState.cache` via `renderPoolAdmin` only while `isCurrentPoolAdminPage()`, plus group/provider filters via `ensurePoolAdminGroupOptions(false)` / `ensurePoolAdminProviderOptions(false)` without `loadPoolAdmin(true)`.

- Token-tool language change must soft-paint warm scope chips and `tokenToolAccountsCache` account select without force network; `t()` must call live `window.translateAppText` (not a frozen module-load capture).

- Plugin manager language change must soft-paint warm `_plugins` via `softPaintOnLanguageChange` / `_renderPluginList` without `loadPlugins({ force: true })`; `plT()` must call live `window.translateAppText`.

- Plugin provider config panel chrome (`_resetProviderConfigPanel`, `showProviderConfig`, `_renderConfigForm`) must use `plT`; language change soft-paints open form from warm `_activeConfigFields` / DOM values without network.

- Plugin lifecycle action chrome (install/uninstall/save/test/apply/custom-install) must use `plT` for buttons, toasts, and confirms so English UI does not leave Chinese action feedback.

- Theme toggle (`applyTheme`) and Settings secret/multi-key hints (`setExternalApiKeysEditor`, external/verification API key hints) must translate at paint time; language change soft-paints via `applyTheme` + `softPaintSettingsSecretHintsIfOpen` while Settings is open.

- CF Worker domain sync chrome (`syncCfWorkerDomains`, `updateCfWorkerReadonlyFields`, temp-provider action success hints) must translate sync success/last-synced/failure labels via `translateAppTextLocal`.

- Verification AI test and Token refresh completion chrome (`testVerificationAiConfig`, refresh SSE complete toasts) must translate validation/progress/result strings via `translateAppTextLocal`.

- Mailbox delete/copy and temp-mailbox generate/delete chrome (`deleteEmails`, `copyEmail`, `generateTempEmail`, `deleteTempEmail`) must translate toast and empty-state strings via `translateAppTextLocal`.

- Invalid-token governance and batch Token refresh action chrome (`loadInvalidTokenGovernanceCandidates`, `batchSetInvalidTokenInactive`, `batchDeleteInvalidTokenCandidates`, `showBatchRefreshConfirm`, `batchRefreshSelected`, `handleBatchRefreshSSEEvent`) must translate toasts/progress via `translateAppTextLocal`; confirms keep Chinese source for the i18n confirm wrapper.

- Settings tab auto-save / proxy test / temp-provider action chrome (`autoSaveSettings` failure toast, `switchSettingsTab` password discard toast, `testTelegramProxy` result, `runTempProviderSettingsAction` error hint) must translate via `translateAppTextLocal`.

- Temp mailbox current-name copy must compare against both Chinese source and translated placeholder (`copyTempEmailCurrent`); provider catalog fallback descriptions (`第三方插件 Provider` / dynamic-create / generic temp provider / currently-saved provider) must use `translateAppTextLocal`.

- Full refresh / retry-failed / single-retry completion toasts must use `translateAppTextLocal` with Chinese source + patterns (not `getUiLanguage()` ternaries).

- `formatSelectedItemsLabel(count)` must use `translateAppTextLocal('已选 ' + count + ' 项')` (not `getUiLanguage()` ternary).

- Import summary / verification copy / compact count labels / temp mailbox current-email suffix must use `translateAppTextLocal` (or compact/local helpers) with Chinese source + patterns — not `getUiLanguage()` ternaries.

- Confirm dialogs must keep Chinese source strings (window.confirm is wrapped by i18n). Missing exact/pattern keys for double-confirm delete, trust-mode warning, and invalid-token batch delete danger prompts must live in `i18n.js`.

- Email detail warm/network render failure empty states must use `translateAppTextLocal` for `邮件渲染失败` / `网络错误，请重试` / `未知错误` / `加载失败`.

- Temp mailbox messages/detail network empty states must use `translateAppTextLocal` for `网络错误，请重试` / `加载失败`.

- Account delete / selectAccount empty mailbox chrome must use `translateAppTextLocal` for `请从左侧选择一个邮箱账号` / `选择一封邮件查看详情`.

- Group list action button titles (`编辑` / `删除`) and temp mailbox card action titles (`点击复制` / `提取验证码` / `复制` / `清空` / `删除`) must use `translateAppTextLocal` at paint time.

- `renderEmailList` empty chrome must be folder-aware via `getEmailListEmptyMessage()` (`收件箱为空` / `垃圾邮件为空` / `暂无邮件`) so junk folder empty state is not hard-coded as inbox.

- Cold folder (no warm `emailListCache` entry) must show fetch prompt via `paintEmailListColdFetchPrompt` / `getEmailListColdFetchPrompt` (`点击"获取邮件"按钮获取收件箱|垃圾邮件`); language change must re-paint that cold prompt without rewriting it as inbox-empty.

- `loadEmails` must capture `targetEmail`/`targetFolder`/`requestMethod` at request start, always warm `emailListCache[cacheKey]`, and paint/error UI only while `isCurrentEmailListView()` so rapid mailbox/folder switches cannot clobber the active list.

- `selectEmail` must capture mailbox/folder/method/messageId at request start, always warm `emailDetailCache[cacheKey]`, and paint/error/loading only while `isCurrentMailboxFolderMethod()` so rapid switches cannot clobber the active detail pane.

- `loadTempEmailMessages` / `getTempEmailDetail` must always warm their soft caches, and paint/error/loading only while still on the same temp mailbox (`currentAccount === targetEmail` / `isCurrentTempMailbox()`), so rapid temp switches cannot clobber the active list/detail.

- `loadTempEmails` / `renderTempEmailList` must always warm `accountsCache['temp']` (and group badge counts), paint only while `isCurrentTempEmailsPage()`, and write **only** `#tempEmailContainer` (never `#accountList`).

- Groups language soft-repaint must call `renderAccountList` only when `currentPage === 'mailbox'` and `!isTempEmailGroup`. `refreshAccountProviderTagsFromCatalog` must likewise skip non-mailbox / temp surfaces so catalog arrival cannot clobber hidden inventory.

- `loadAccountsByGroup` must always warm `accountsCache[groupId]` / `accountListMetaCache`, and paint/error/loading only while `isCurrentAccountListView()`; `updateAccountListCache(..., { syncCurrentPage })` must not rewrite `currentAccountPage` for stale (non-current) responses.

- `loadMoreEmails` must capture mailbox/folder/method/skip at request start, always upsert `emailListCache` for that key from a baseline merge, and paint only while still on the same mailbox+folder (`isCurrentEmailListView()`).

- Export modal `loadExportGroupList` must soft-paint warm `groups` via `paintExportGroupList` without spinner flash; cold path uses `loadGroups(false)` only; `paintExportGroupList` / loading/error chrome only while `isExportModalOpen()` so soft loadGroups finishing after close cannot rewrite export DOM; language change soft-paints open export modal via `softPaintExportGroupListIfOpen` (preserve checkbox selection).

- Batch-tag select `loadTagsForSelect` and batch-move `loadGroupsForBatchMove` must soft-paint warm `allTags` / `groups` without "加载中..." flash; cold path shows loading then soft-loads; `paintBatchMoveGroupSelectFromWarmGroups` only while `isBatchMoveGroupModalOpen()`; language change soft-paints open batch-move select via `softPaintBatchMoveGroupSelectIfOpen` and open batch-tag modal title from `batchActionType`.

- Version banner `applyVersionCheckPayload` must translate chrome via `translateAppTextLocal` at paint time; language change soft-paints from warm `versionCheckCache` without network.

- Refresh-modal failed list / history paint paths (`showFailedListFromData`, `loadFailedLogs`, `renderRefreshModalHistory`) must translate empty states, retry buttons, status labels, and history header via `translateAppTextLocal` so language soft re-paint works.

- Invalid-token governance paint (`showInvalidTokenDetectionSummary`, `applyInvalidTokenGovernanceCandidates`) must translate summary/count/status/reason chrome via `translateAppTextLocal` so language soft re-paint works.

- Group switch empty email list and account search loading/error chrome must use `translateAppTextLocal` (`请从左侧选择一个邮箱账号`, `搜索中…`, `搜索失败，请重试`).

- `loadDeploymentInfo({ forceRefresh })` soft-loads warm `lastDeploymentInfo`; soft joins any in-flight and force joins only force (`deploymentInfoLoadForce`) and supersedes soft so abandoned soft responses do not paint; always warm soft cache and paint warnings/update-method radios only while `isSettingsSurfaceActive()` via `applyDeploymentInfo(deployment, { paint })`; Settings open uses soft load; language change re-renders from cache without network.



### 5. Good/Base/Bad Cases



- Good: `renderOverviewSummary()` calls `renderOverviewCommandCenter(data.command_center || {})` before rendering `.kpi-row`.

- Good: command-center CSS lives in the Overview Dashboard block and mobile rules collapse `.ov-command-grid` to one column at narrow widths.

- Good: `initOverview()` calls `switchOverviewTab(activeTab)` without a second `loadOverviewTab(..., true)` when cache is warm.

- Good: boot init omits `loadGroups()`/`loadTags()`; `navigate('mailbox')` loads groups when empty; tag modal loads tags.

- Base: `external_api.pool_status=disabled` can be shown as restricted/disabled while the external mailbox directory remains ready.

- Bad: adding browser fetches to `/api/v1/external/health` or `/api/mailboxes` from the summary tab to compute readiness.

- Bad: reading `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey` inside summary render helpers.

- Bad: forcing overview network refresh on every Dashboard navigation even when `__overviewState.cache[activeTab]` is warm.

- Bad: eager `/api/groups` + `/api/tags` on every page boot for dashboard-first sessions.

### 6. Tests Required

- Frontend contract tests must assert helper names, render order before `.kpi-row`, CSS hooks, i18n labels, and forbidden secret references.
- Backend API tests must assert the command-center schema and secret safety because the frontend is intentionally thin.
- Browser QA is required for material layout changes and must inspect desktop/mobile page-level overflow plus `#ov-summary-body`, `.overview-tab-shell`, and `.ov-command-center` overflow.

### 7. Wrong vs Correct

#### Wrong
```javascript
const key = document.getElementById('settingsExternalApiKey').value;
const health = await fetch('/api/v1/external/health', { headers: { 'X-API-Key': key } });
```

#### Correct
```javascript
const commandCenter = data.command_center || {};
return renderOverviewCommandCenter(commandCenter);
```

## Scenario: Workspace Masthead Pipeline Mobile Collapse

### 1. Scope / Trigger

Trigger: frontend changes that add a product-level masthead, workflow pipeline, stage rail, or fixed-count status strip to a dense operational workspace, especially `#mailboxUnifiedLayout` and other first-viewport dashboard pages.

### 2. Signatures

- `templates/index.html -> .unified-workspace-masthead`
- `templates/index.html -> .unified-workspace-pipeline`
- `static/css/main.css -> .unified-workspace-pipeline`
- `static/css/main.css -> @media (max-width: 768px)`

### 3. Contracts

Fixed-count pipeline items must not depend on desktop width. The desktop layout may use four or more columns, but the mobile breakpoint must explicitly collapse the masthead and pipeline into a mobile-safe flow. For the unified mailbox workspace, the masthead uses a column layout on mobile and the pipeline uses `repeat(2, minmax(0, 1fr))` so long Chinese and English labels can wrap inside the viewport.

### 4. Validation & Error Matrix

- Desktop masthead uses a multi-column or horizontal pipeline -> mobile CSS must reset masthead flow and pipeline grid.
- Page-level overflow is zero but pipeline items are clipped -> treat as a layout failure.
- Long labels such as `Provider 路由` or `External API` -> labels may wrap vertically, but must not increase page-level horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: `.unified-workspace-pipeline { grid-template-columns: repeat(4, minmax(...)); }` plus mobile `repeat(2, minmax(0, 1fr))` and masthead `flex-direction: column`.
- Base: mobile pipeline cards can grow taller to preserve readable labels.
- Bad: keeping four fixed columns on a 390px viewport and accepting screenshots without checking `scrollWidth - clientWidth`.

### 6. Tests Required

- Frontend contract tests should assert persistent masthead and pipeline hooks when the masthead is part of the product UI.
- Browser checks are required after changing masthead or pipeline layout and must inspect page-level overflow plus the toolbar/internal workspace overflow.

### 7. Wrong vs Correct

#### Wrong

```css
.unified-workspace-pipeline {
  grid-template-columns: repeat(4, 128px);
}
```

#### Correct

```css
.unified-workspace-pipeline {
  grid-template-columns: repeat(4, minmax(94px, 1fr));
}

@media (max-width: 768px) {
  .unified-workspace-masthead {
    flex-direction: column;
  }
  .unified-workspace-pipeline {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

## Scenario: Mobile Grid Collapse Integrity


### 1. Scope / Trigger



Trigger: frontend changes that make a desktop grid item span rows, pin it to a specific grid column, or move dense operational controls between grid columns, especially in the unified mailbox directory, provider workbench, external API command center, and other first-viewport dashboards.



### 2. Signatures



- `static/css/main.css -> @media (max-width: 1180px)`

- `static/css/main.css -> @media (max-width: 768px)`

- Grid item rules such as `.unified-command-main`, `.unified-command-views`, `.unified-command-workflows`, and any selector that sets `grid-column` or `grid-row` for a desktop dashboard layout.



### 3. Contracts



When a desktop layout pins a child to a numbered grid column or row span, the tablet/mobile breakpoint must explicitly collapse those children back into the single-column grid. Do not rely on `grid-template-columns: 1fr` alone, because a child with `grid-column: 2` can create an implicit second column and compress sibling content without producing page-level horizontal overflow.



Mobile overrides should reset affected children with `grid-column: 1 / -1` and `grid-row: auto`, or use an equivalent selector that covers every direct child in that grid surface. Horizontal scrolling is allowed only inside a deliberate rail such as a quick-view strip; the surrounding page and parent grid must stay single-column.



### 4. Validation & Error Matrix



- Desktop child uses `grid-column: 2` or `grid-row: span 2` -> mobile CSS must reset that child or all direct children to the single-column flow.

- Mobile browser has `documentElement.scrollWidth - clientWidth === 0` but a key panel child is much narrower than its parent -> treat this as a layout failure, not a pass.

- A rail intentionally scrolls horizontally -> assert the rail has `overflow-x: auto` and the page-level overflow remains zero.

- Text appears wrapped into very narrow columns in a mobile screenshot -> inspect computed `gridColumn`, element width, and parent width before accepting the layout.



### 5. Good/Base/Bad Cases



- Good: desktop `.unified-command-views { grid-column: 2; }` plus mobile `.unified-command-center > * { grid-column: 1 / -1; }` and `.unified-command-main { grid-row: auto; }`.

- Base: mobile quick-view rails can scroll inside their own container while the command center, workflow chips, and notices occupy the full parent width.

- Bad: only setting `.unified-command-center { grid-template-columns: 1fr; }` while a child still has `grid-column: 2`; the browser creates an implicit second column and compresses the first column.



### 6. Tests Required



- Frontend contract tests must assert the mobile breakpoint contains a selector that resets affected dashboard grid children to `grid-column: 1 / -1` when desktop CSS uses numbered grid placement.

- Browser checks must inspect both page-level horizontal overflow and key child widths on mobile. A passing check should prove the main command copy, workflows, or equivalent dense controls are close to the parent width, not squeezed into an implicit column.

- Screenshots are required when command-center, summary, rail, workflow chip, or provider matrix grid placement changes.



### 7. Wrong vs Correct



#### Wrong



```css

.unified-command-views {

  grid-column: 2;

}



@media (max-width: 768px) {

  .unified-command-center {

    grid-template-columns: 1fr;

  }

}

```



#### Correct



```css

.unified-command-views {

  grid-column: 2;

}



@media (max-width: 768px) {

  .unified-command-center {

    grid-template-columns: 1fr;

  }

  .unified-command-center > * {

    grid-column: 1 / -1;

  }

  .unified-command-main {

    grid-row: auto;

  }

}

```



## Scenario: Dense Filter Toolbar Intrinsic Overflow



### 1. Scope / Trigger



Trigger: frontend changes that add, wrap, relabel, or resize dense filter controls in operational workspaces, especially `.unified-toolbar` in the unified mailbox directory.



### 2. Signatures



- `templates/index.html -> .unified-toolbar`

- `templates/index.html -> .unified-toolbar-field`

- `static/css/main.css -> .unified-toolbar`

- `static/css/main.css -> .unified-toolbar-field-search`

- Browser checks that inspect `element.scrollWidth - element.clientWidth` for dense toolbar containers.



### 3. Contracts



Dense toolbars must prove that the toolbar container itself has no internal horizontal overflow, not only that the page has no horizontal overflow. A page can report `documentElement.scrollWidth - clientWidth === 0` while a grid toolbar still has `scrollWidth > clientWidth`, which means controls are clipped or squeezed inside the panel.



For the unified mailbox toolbar, use an auto-fitting grid such as `grid-template-columns: repeat(auto-fit, minmax(..., 1fr))` and let the search field span two tracks on desktop, then collapse all toolbar fields to `grid-column: 1 / -1` on mobile. Avoid fixed column counts that assume a specific number of filters, because the unified directory can add contract-driven filters while keeping the same toolbar shell.



### 4. Validation & Error Matrix



- Toolbar page overflow is zero but `.unified-toolbar.scrollWidth - clientWidth > 0` -> treat as a layout failure.

- Adding a new filter field -> toolbar CSS must continue to wrap without implicit overflow.

- Mobile viewport -> every `.unified-toolbar-field`, `.unified-toolbar-field-search`, and `.unified-toolbar-refresh` must collapse to the single-column flow.

- Long translated labels or provider labels -> fields may grow vertically, but must not force horizontal clipping.



### 5. Good/Base/Bad Cases



- Good: `.unified-toolbar { grid-template-columns: repeat(auto-fit, minmax(124px, 1fr)); }` with desktop `.unified-toolbar-field-search { grid-column: span 2; }` and mobile single-column overrides.

- Base: search can occupy more width than compact select fields, but it must still wrap when the content pane is narrower than a full desktop.

- Bad: hardcoding seven or eight grid tracks for the current filter set and accepting a browser check that only inspects page-level overflow.



### 6. Tests Required



- Frontend contract tests must assert the unified toolbar uses an auto-fit/minmax grid when the filter shell is touched.

- Frontend contract tests must assert the search field and refresh button have CSS hooks for desktop span and mobile collapse.

- Browser checks are required for toolbar/layout changes and must record both page-level overflow and `.unified-toolbar` internal overflow at desktop and mobile sizes.



### 7. Wrong vs Correct



#### Wrong



```css

.unified-toolbar {

  grid-template-columns: minmax(240px, 1fr) repeat(6, 116px) auto;

}

```



This can pass a page-level overflow check while the toolbar itself clips controls.



#### Correct



```css

.unified-toolbar {

  grid-template-columns: repeat(auto-fit, minmax(124px, 1fr));

}



.unified-toolbar-field-search {

  grid-column: span 2;

}



@media (max-width: 768px) {

  .unified-toolbar-field,

  .unified-toolbar-field-search,

  .unified-toolbar-refresh {

    grid-column: 1 / -1;

  }

}

```



## Scenario: Settings Provider Workbench UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that render Settings -> API Security provider routing, provider readiness, provider-config-file state, source priority, secret policy, deployment templates, integration guide, or provider console summaries.



### 2. Signatures



- `templates/index.html -> #providerWorkbench`

- `templates/index.html -> #providerWorkbenchSummary`

- `static/js/main.js -> renderProviderWorkbench(settings, state)`

- `static/js/main.js -> getProviderWorkbenchConfigFileStatus(settings)`

- `static/js/main.js -> getProviderWorkbenchSecretPolicyText()`



### 3. Contracts



The provider workbench is a read-only display adapter over authenticated settings data and `/api/providers` discovery data. It must consume `externalApiSettingsSnapshot`, `mailboxProviderDiagnosticsCache`, `mailboxProviderDeploymentProfileCache`, and `mailboxProviderIntegrationGuideCache` rather than creating a local provider registry or provider-specific routing table.



The overview may display provider key names, provider labels, routing mode, default claim provider, provider readiness totals, provider-config-file status, source priority, and secret-policy posture. It must not read API-key or provider-token input elements, masked placeholder values, plaintext credential values, or external API endpoints to build its summary.



It must preserve the backend provider selection contract. Do not change provider aliases, source priority, provider selection request fields, or discovery endpoint behavior when adjusting this UI.



On mobile, the Settings page owns several inline `padding` declarations in the template. Provider workbench changes must include mobile CSS that overrides those wrappers when needed, so the API Security pane keeps enough usable width for dense metrics and long endpoint/config strings. Passing page-level overflow alone is not enough if the workbench is squeezed into a narrow column.



### 4. Validation & Error Matrix



- Settings loaded before provider catalog -> render settings-derived route/default/config-file values while provider readiness can show catalog unavailable.

- Provider catalog loaded before settings -> render provider-derived readiness/source/secret-policy values without reading form inputs.

- Provider catalog failure -> keep the workbench visible with a degraded readiness state.

- Provider config file disabled -> show a neutral inactive state, not a warning.

- Provider config file error -> show the error code/path from settings or deployment profile without failing the page.

- Long provider names, config file paths, and source-priority strings -> wrap without horizontal overflow on mobile.

- Mobile browser has no horizontal overflow but `#providerWorkbench` is much narrower than the settings card body -> treat it as a layout failure and inspect page/card-body padding.



### 5. Good/Base/Bad Cases



- Good: `renderProviderWorkbench()` calls shared helpers such as `getExternalApiCommandRouteMode()` and `getExternalApiCommandSourcePriority()`.

- Good: the workbench shows `DUCKMAIL_BEARER_TOKEN` only as a key name when that name arrives from discovery metadata.

- Base: provider diagnostics/templates/guide/console remain separate detailed panels inside the workbench after the overview.

- Base: mobile `#page-settings` and `.settings-tab-pane .card-body` may need explicit `!important` padding overrides because the template uses inline padding on the page and card body wrappers.

- Bad: the workbench reads `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey`.

- Bad: the workbench branches on `provider === "duckmail"`, `provider === "mail_tm"`, `provider === "emailnator"`, or `provider === "gptmail"` to decide routing semantics.



### 6. Tests Required



- Frontend contract tests must assert the workbench mounts, overview render helper names, provider catalog success/failure render calls, settings-load render call, language-change render call, CSS hooks, and long-text wrapping styles.

- Secret-safety tests must assert the workbench render/helper slice does not reference API key or provider credential input IDs.

- Browser checks are required on desktop and mobile when the workbench summary grid, wrapper, or provider-detail panel layout changes. They must inspect page-level overflow and the workbench/container widths, not just screenshots.





## Scenario: Settings Provider Contract Status UI



### 1. Scope / Trigger



Trigger: frontend changes that render temp-mail provider extension contract validation in Settings -> API Security, or consume `contract_validation` from `/api/providers` and `/api/plugins`.



### 2. Signatures



- `templates/index.html -> #providerContractStatus`

- `templates/index.html -> #providerContractStatusSummary`

- `templates/index.html -> #providerContractStatusList`

- `GET /api/providers -> data.mailbox_providers[*].contract_validation`

- `GET /api/providers -> data.provider_integration_guide.providers[*].contract_validation`

- `GET /api/plugins -> data.data.plugins[*].contract_validation`

- `static/js/main.js -> updateProviderContractStateFromCatalog(payload)`

- `static/js/main.js -> updateProviderContractStateFromPlugins(plugins)`

- `static/js/main.js -> renderProviderContractStatus()`



### 3. Contracts



The provider contract panel is a display adapter over backend validation summaries. JavaScript may normalize status, count totals, merge catalog/plugin rows, sort rows, and render issue-code chips. JavaScript must not reimplement provider validation checks or infer provider readiness from provider-specific names.



The only validation fields the panel may render are `status`, `summary.errors`, `summary.warnings`, `summary.checks`, `issue_codes`, provider key/label/kind, and plugin load status. It must not render `safe_metadata`, raw `checks`, raw `issues.message`, config-field defaults, plugin config fields, masked placeholders, API keys, bearer tokens, passwords, JWTs, refresh tokens, task tokens, consumer keys, or provider secret values.



Catalog rows from `/api/providers` are authoritative for built-in and configured temp providers. Plugin rows from `/api/plugins` may supplement compact contract status and plugin load state when a plugin provider exists. Missing `contract_validation` must become an `unknown` status, not a JavaScript error.



The panel must stay provider-agnostic. Do not branch on provider names such as `duckmail`, `mail_tm`, `emailnator`, `gptmail`, `tempmail_lol`, or future plugin provider keys to decide validation behavior. Provider-specific behavior belongs in backend provider validation and provider catalog payloads.



Language-change events must re-render the panel because status labels, empty states, and plugin load labels are translated at render time.



### 4. Validation & Error Matrix



- `/api/providers` returns catalog rows with contract summaries -> render valid/warning/invalid/unknown counts and provider rows.

- `/api/providers` returns no temp provider rows -> render the unavailable empty state without throwing.

- `/api/providers` fails -> clear catalog contract state and keep the panel visible with an unavailable state.

- `/api/plugins` loads after catalog -> merge plugin contract summaries and plugin load labels into matching provider rows.

- `/api/plugins` fails -> clear plugin contract state without removing catalog rows.

- A provider lacks `contract_validation` -> render `unknown` with zero summary counts and no issue code.

- Contract payload contains raw issue messages or metadata -> ignore them in the UI and render only compact issue codes.

- Mobile viewport -> provider rows collapse to one column, wrap long keys/codes, and keep page-level horizontal overflow at zero.



### 5. Good/Base/Bad Cases



- Good: `renderProviderContractStatus()` consumes `contract_validation.status`, `summary`, and `issue_codes` from provider/plugin payloads.

- Good: plugin rows show `Plugin installed`, `Plugin load failed`, or equivalent translated load state without exposing plugin config values.

- Base: catalog data renders before plugin data; plugin data later updates only matching provider rows.

- Base: all built-in providers can show `valid` while still displaying separate readiness details such as missing configuration.

- Bad: frontend code checks `provider === "duckmail"` or `provider === "mail_tm"` to decide which checks passed.

- Bad: frontend code renders `safe_metadata`, `config_fields`, raw validation `checks`, raw issue messages, provider token values, or secret input element values.



### 6. Tests Required



- Frontend contract tests must assert the DOM mount, summary/list IDs, render helper names, catalog/plugin state update calls, CSS hooks, i18n strings, and language-change re-render call.

- Secret-safety tests must assert the provider contract helper/render slice does not reference secret input IDs and does not render raw validation payload fields such as `safe_metadata`, `config_fields`, `checks.map`, or `issues.map`.

- Provider-agnostic tests must assert the helper/render slice has no provider-name conditionals.

- Backend/provider API tests must remain green so the UI consumes the same provider catalog and plugin discovery contract used by external APIs.

- Browser checks are required when changing the panel layout. Capture desktop and mobile screenshots and inspect page-level overflow plus provider-row internal overflow.



### 7. Wrong vs Correct



#### Wrong



```javascript

if (provider.provider === 'duckmail') {

  row.innerHTML = provider.contract_validation.safe_metadata.token_hint;

}

```



#### Correct



```javascript

const contract = normalizeProviderContractSummary(provider.contract_validation, provider.provider);

renderProviderContractIssueCodes(contract.issue_codes);

```



## Scenario: Settings Save Payload Collector Reuse



### 1. Scope / Trigger



Trigger: frontend changes that save Settings fields through `saveSettings()` or `autoSaveSettings(tabName)`, especially temp-mail provider settings, provider credentials, API Security settings, external API keys, or JSON-backed settings fields.



### 2. Signatures



- `static/js/main.js -> saveSettings()`

- `static/js/main.js -> autoSaveSettings(tabName)`

- `static/js/main.js -> collectTempMailSettingsPayload()`

- `static/js/main.js -> collectApiSecuritySettingsPayload()`

- `static/js/main.js -> assignSecretSettingFromInput(settings, settingKey, inputEl)`



### 3. Contracts



Manual Settings save and tab-switch auto-save must reuse shared payload collectors for settings sections they both write. Do not keep provider credential parsing, masked placeholder checks, JSON parsing, API-key multi-key normalization, or clear-empty behavior in two separate save branches.



`assignSecretSettingFromInput()` owns the masked-secret placeholder rule for frontend payloads: if the input value equals the loaded masked placeholder and `dataset.isSet === "true"`, the outgoing payload must omit that secret field. Empty user input is still a deliberate clear when the field is otherwise included by the collector.



JSON-backed settings collectors must fail before `PUT /api/settings` when the input is invalid and show the same translated validation message in manual save and auto-save. Empty JSON fields should preserve the section's existing full-save semantics, such as `[]` for temp-mail domains, default prefix rules for prefix-rule fields, `['public_gmail_plus']` for Emailnator types, and `[]` for clearing changed external API multi-key configuration.



### 4. Validation & Error Matrix



- Masked provider/API secret placeholder -> omit that secret from the payload.

- New provider/API secret value -> include the plaintext value for backend encryption/storage.

- Cleared secret input -> include an empty string so the backend can clear it.

- Invalid JSON settings field -> show a validation toast and do not send the save request.

- Empty external multi-key editor with an existing original canonical value -> send `external_api_keys: []`.



### 5. Good/Base/Bad Cases



- Good: `saveSettings()` and `autoSaveSettings('temp-mail')` both call `collectTempMailSettingsPayload()`.

- Good: `saveSettings()` and `autoSaveSettings('api-security')` both call `collectApiSecuritySettingsPayload()`.

- Base: automation-only settings may stay in the automation auto-save branch until they are shared with the full save path.

- Bad: auto-save branches contain private parsing for `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsExternalApiKeysJson` while full save has separate logic.



### 6. Tests Required



- Frontend contract tests must assert the shared collector names, that both save paths call the collectors, and that auto-save no longer contains duplicated provider/API field parsing branches.

- Settings/API tests must continue to cover masked secret preservation and multi-key editing behavior.

- Static checks must keep production scripts free of `console.log(` and `console.debug(`.



### 7. Wrong vs Correct



#### Wrong



```javascript

if (tabName === 'temp-mail') {

  const tokenEl = document.getElementById('settingsDuckmailBearerToken');

  settings.duckmail_bearer_token = tokenEl.value.trim();

}

```



#### Correct



```javascript

if (tabName === 'temp-mail') {

  const tempMailSettings = collectTempMailSettingsPayload();

  if (!tempMailSettings) return;

  Object.assign(settings, tempMailSettings);

}

```



## Scenario: Temp Mail Provider Selector Catalog Consumption


### 1. Scope / Trigger



Trigger: frontend changes that render, populate, refresh, or save the temp-mail creation provider selector.



### 2. Signatures



- `GET /api/providers -> data.mailbox_providers`

- `templates/index.html -> #tempEmailProviderSelect`

- `static/js/main.js -> loadMailboxProviderCatalog()`

- `static/js/main.js -> syncTempEmailProviderSelectWithCatalog()`

- `static/js/features/temp_emails.js -> getTempEmailProviderDisplayLabel()`



### 3. Contracts



The temp-mail creation selector must use `/api/providers` as the source of truth after the provider catalog loads. Static HTML options are allowed only as startup fallback values before catalog data arrives.



Selector population must include temp providers from `mailbox_providers` and must not add account providers, `auto`, empty provider names, or duplicate provider values. Display labels must prefer shared catalog helpers (`resolveMailboxProviderLabel` / temp catalog item labels) for status text and domain hints when available.



The selector must preserve the user's current value when that provider is still present. Plugin-manager refreshes and catalog refreshes must cooperate: plugin lifecycle must `await loadMailboxProviderCatalog(true)` first, then re-inject plugin DOM fallbacks so async catalog rewrites cannot wipe installed-but-not-loaded plugin options.



This selector is a provider-choice UI only. It must not change backend provider selection priority, provider aliases, request field names, external API endpoints, or secret handling.



### 4. Validation & Error Matrix



- Catalog unavailable -> keep existing static selector options and continue to show degraded provider status where applicable.

- Catalog contains a plugin temp provider -> add or update one selector option for that provider.

- Catalog contains account providers or `auto` -> do not add them to the temp-mail creation selector.

- Catalog refresh happens after the user selected a provider -> keep the selected value if still present.

- Plugin-manager refresh runs after catalog refresh -> update existing plugin option labels without creating duplicate values.



### 5. Good/Base/Bad Cases



- Good: a newly installed plugin temp provider appears in `#tempEmailProviderSelect` after `/api/providers` refreshes.

- Base: built-in `mail_tm`, `duckmail`, `tempmail_lol`, and `emailnator` remain available from the static fallback even if provider catalog loading fails.

- Bad: adding a new provider only to `templates/index.html` while ignoring `/api/providers`.

- Bad: appending plugin options every time the plugin manager refreshes, creating duplicate `<option value="plugin_name">` entries.



### 6. Tests Required



- Frontend contract tests must assert the selector mount, static fallback options, catalog-driven sync helper, temp-only filtering, duplicate prevention, selection preservation, catalog label usage, and plugin refresh duplicate prevention.



### 7. Wrong vs Correct



#### Wrong



```javascript

select.innerHTML += '<option value="new_provider">New Provider</option>';

```



#### Correct



```javascript

syncTempEmailProviderSelectWithCatalog();
```

## Scenario: Settings Temp Mail Provider Selector Catalog Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render, populate, refresh, save, or route the Settings -> Temp Mail provider radio cards in `#tempMailProviderOptions`.

### 2. Signatures

- `GET /api/providers -> data.mailbox_providers`
- `GET /api/providers -> data.provider_diagnostics.providers`
- `templates/index.html -> #tempMailProviderOptions`
- `static/js/main.js -> renderTempMailProviderOptions(preferredProvider)`
- `static/js/main.js -> getTempMailSettingsProviderOptions(selectedProvider, mount)`
- `static/js/main.js -> collectTempMailSettingsPayload()`
- `static/js/main.js -> onTempMailProviderChange(provider)`

### 3. Contracts

The Settings temp-mail provider selector must expose only a stable mount in the template. Radio options named `tempMailProvider` must be rendered by JavaScript from `/api/providers` catalog data, with `provider_diagnostics.providers` used to preserve inactive provider choices when the active allowlist filters the primary catalog.

The selector must have a non-secret built-in fallback list for startup, offline, or catalog-failure states. The fallback can contain provider keys, display labels, and descriptions only. It must not contain API keys, bearer tokens, masked placeholders, passwords, JWTs, refresh tokens, external API keys, consumer keys, or task tokens.

Historical compatible-bridge aliases such as `custom_domain_temp_mail`, `gptmail`, `legacy_gptmail`, and `temp_mail` should normalize to the displayed `legacy_bridge` Settings option. Option generation must not require editing `templates/index.html` when a future temp provider appears in catalog/diagnostics. The saved payload contract remains `settings.temp_mail_provider = checked input[name="tempMailProvider"].value` via `collectTempMailSettingsPayload()`.

Panel routing is catalog-driven: when `settings_ui.panel === 'schema'` (including `legacy_bridge`, `cloudflare_temp_mail`, DuckMail, Emailnator, Mail.tm, and other schema-described built-ins), Settings renders through `#tempMailProviderConfigPanel` via `renderTempMailProviderConfigPanel()`. `#gptmailConfigPanel` / `#cfWorkerConfigPanel` may remain as empty hidden compatibility mounts only. Catalog rows with `configuration.config_source === 'plugin'` (or unknown plugin providers before catalog settles) still use `PluginManager.showProviderConfig(provider)` for config UI until plugin runtime config is fully unified into the same schema panel save path.



The selector renderer is a display adapter. It may show provider keys, labels, descriptions, readiness, configured state, and missing config key names from catalog/diagnostics, but it must not read credential input elements or render credential values.

### 4. Validation & Error Matrix

- Catalog unavailable -> render fallback provider radio cards and keep save/load usable.
- Catalog returns temp providers -> render one radio card per normalized temp provider.
- Catalog omits inactive providers while diagnostics includes them -> include diagnostics temp providers so Settings still offers configurable choices.
- Catalog or diagnostics includes account providers or `auto` -> exclude them from the Settings temp provider selector.
- Settings loads before catalog -> store the saved provider as pending, render fallback, then restore it after catalog/diagnostics refresh.
- Saved provider is unknown/future and absent from catalog -> render a selectable saved-provider card so the value does not disappear.
- Language changes -> rerender labels/descriptions/status without reading settings credential inputs.
- Mobile viewport -> `#tempMailProviderOptions` must not create page, pane, or mount-level horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: `#tempMailProviderOptions` starts as a loading mount in `templates/index.html`, and `renderTempMailProviderOptions()` creates `input[name="tempMailProvider"]` radio cards from catalog/diagnostics.
- Good: diagnostics rows supplement catalog rows when active provider allowlists hide inactive built-ins.
- Good: missing config is shown as key names such as `DUCKMAIL_BEARER_TOKEN`, never as secret values.

- Base: the fallback list contains current built-ins so Settings remains usable before `/api/providers` returns.

- Base: catalog-ready plugins with `panel=schema` use the generic schema Settings panel; PluginManager remains install/lifecycle UI and catalog-warmup fallback only.

- Base: warmup alias map (`gptmail` / `custom_domain_temp_mail` → `legacy_bridge`) keeps historical built-in names on the schema path before catalog settles.

- Bad: hardcoding one `<label class="provider-radio">` block per provider in `templates/index.html`.

- Bad: reading `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, `settingsTempMailApiKey`, `settingsExternalApiKey`, or `settingsExternalApiKeysJson` inside the selector renderer.

### 6. Tests Required

- Frontend contract tests must assert the template mount, absence of static radio options in the mount, fallback metadata, renderer helper names, temp-only filtering, diagnostics supplementation, alias normalization, future/saved-provider preservation, dynamic `input[name="tempMailProvider"]` rendering, and language/render hooks.
- Secret-safety tests must assert the renderer slice does not reference Settings credential input IDs.
- Save/load tests must continue asserting `collectTempMailSettingsPayload()` is reused by manual save and auto-save.
- Browser checks are required when the Settings selector markup or layout changes. Record desktop and mobile provider counts plus page/body/mount/pane horizontal overflow.

### 7. Wrong vs Correct

#### Wrong

```html
<label class="provider-radio">
  <input type="radio" name="tempMailProvider" value="new_provider">
  <span class="provider-radio-label">New Provider</span>
</label>
```

#### Correct

```javascript
renderTempMailProviderOptions();
const checked = document.querySelector('input[name="tempMailProvider"]:checked');
settings.temp_mail_provider = checked ? checked.value : 'legacy_bridge';
```

## Scenario: Settings Temp Mail Provider Config Schema Consumption

### 1. Scope / Trigger

Trigger: frontend or backend changes that expose, render, refresh, or save Settings -> Temp Mail built-in provider configuration fields from provider catalog metadata, especially when a provider supplies `configuration.config_schema` or equivalent sanitized configuration metadata.

### 2. Signatures

- `GET /api/providers -> data.mailbox_providers[*].configuration.config_schema`
- `GET /api/settings -> data.settings.<setting>_set` and `data.settings.<setting>_masked` for secret state hints
- `PUT /api/settings -> settings.<provider setting key>`
- `outlook_web/services/provider_catalog.py -> configuration.config_schema`
- `templates/index.html -> #tempMailProviderConfigPanel`
- `templates/index.html -> #tempMailProviderConfigBody`
- `templates/index.html -> #tempMailProviderConfigSubtitle`
- `static/js/main.js -> renderTempMailProviderConfigPanel(provider)`
- `static/js/main.js -> providerUsesTempSettingsSchemaPanel(provider)`
- `static/js/main.js -> collectTempProviderSchemaSettings(settings)`
- `static/js/main.js -> getTempProviderConfiguration(provider)`
- `static/js/main.js -> getTempProviderSchemaFields(provider)`

### 3. Contracts

Built-in temp-mail provider configuration must be catalog/schema driven when the catalog exposes sanitized field metadata. The frontend may project safe display fields from `configuration.config_schema`, `settings_keys`, `required_settings`, `secret_settings`, and defaults, but it must not add a second local provider registry for field definitions.

Secret fields render as empty password inputs. The UI may show key names, required markers, and `*_set` or `*_masked` preservation hints from `/api/settings`; it must not place saved secret values in `value`, `placeholder`, `data-*`, text content, copied snippets, logs, or tests. Blank secret inputs and masked placeholders mean preserve the current backend value. Only a non-empty replacement secret may be submitted.

Non-secret fields may render safe defaults from catalog metadata, but unchanged default values should be omitted from save payloads when omission preserves environment/default semantics. Clearing a non-secret field is allowed only when the collector can distinguish a user-entered empty value from an untouched default placeholder.

The generic schema panel owns `/api/settings`-persisted schema-described built-ins, including `mail_tm`, `duckmail`, `tempmail_lol`, `emailnator`, `legacy_bridge`, and `cloudflare_temp_mail`. Bridge/CF special workflows (for example CF domain sync) must be expressed as catalog `settings_ui.actions` + schema readonly fields, not as authoritative dedicated field panels. Empty compatibility mounts may remain hidden. Catalog rows with `configuration.config_source === 'plugin'` must continue through `PluginManager.showProviderConfig(provider)` for interactive config UI until plugin runtime config is fully unified with the schema panel; plugin settings keys under `plugin.<name>.*` may still round-trip through `/api/settings` with masked secrets. Provider change routing must use a built-in fallback list before `/api/providers` finishes loading so a saved built-in provider is not misrouted to the plugin panel during startup.

### 4. Validation & Error Matrix

- Catalog loads before settings -> render schema fields, then apply secret preservation hints after settings arrive.

- Settings load before catalog -> preserve the selected provider and reroute after catalog refresh, using built-in fallback classification during the gap.

- Catalog has no configurable fields -> show the generic panel empty/configured state without showing the plugin panel.

- Secret field has `*_set` or `*_masked` true -> render an empty password input plus a preserved hint; saving blank preserves the backend value.

- Secret input receives a new non-empty value -> include only that new value in `PUT /api/settings`.

- Non-secret field equals an untouched safe default -> omit it from save payload when provider runtime should keep env/default behavior.

- Legacy bridge or Cloudflare Worker selected -> keep the generic schema panel visible; hide empty compatibility mounts; render CF actions from `settings_ui.actions`.

- Catalog row has `configuration.config_source === 'plugin'` and `settings_ui.panel === 'schema'` -> generic schema panel + `/api/settings` `plugin.*` keys; optional test-connection action posts `/api/plugins/<name>/test-connection`.

- Catalog missing + installed plugin (PluginManager) or unknown non-builtin name while PluginManager exists -> PluginManager path, never empty schema body during warmup.

- Catalog missing + built-in fallback (`legacy_bridge` / CF / mail_tm / duckmail / tempmail_lol / emailnator) -> schema path.
- Mobile viewport -> `#tempMailProviderConfigPanel`, field rows, env hints, long key names, and URLs must wrap without page, pane, or panel horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: provider catalog rows describe text/password/url fields, required flags, secret flags, and safe defaults; `renderTempMailProviderConfigPanel()` renders built-in provider fields without editing `templates/index.html` per provider.

- Good: DuckMail, Emailnator, legacy bridge, and Cloudflare use the generic schema panel with `data-temp-provider-setting` keys; they do not keep authoritative dedicated field panels.

- Good: a catalog-ready plugin with `config_source === 'plugin'` and `panel=schema` renders in `#tempMailProviderConfigPanel` with `data-temp-provider-setting="plugin.<name>.*"`, saves through Settings dirty-key collection, and can test connection via schema action.

- Good: before catalog loads, an installed plugin still opens PluginManager so operators never see an empty schema body.

- Good: a secret setting shows `DUCKMAIL_BEARER_TOKEN` as a key name and an empty input when configured, never the actual token.

- Good: `collectTempProviderSchemaSettings()` skips blank secret inputs and masked placeholders so existing secrets survive a normal save.

- Base: `#gptmailConfigPanel` / `#cfWorkerConfigPanel` may remain empty hidden nodes for older scripts/tests, but never own field markup or save/load.

- Bad: adding provider-specific template panels for every new built-in provider whose fields already exist in `config_schema`.

- Bad: rendering `plugin.*` keys in the generic schema panel unless `/api/settings` explicitly supports saving that plugin's settings.

- Bad: pre-filling a password input, placeholder, `data-loaded-value`, or copied text with a bearer token, API key, JWT, password, task token, refresh token, consumer key, or external API key.

- Bad: classifying built-in providers as plugins while `/api/providers` is still loading.

### 6. Tests Required

- Frontend contract tests must assert the generic panel mount IDs, schema helper names, `providerUsesTempSettingsSchemaPanel()` routing, built-in fallback classification, plugin fallback, secret-preservation hooks, and responsive CSS hooks.
- Frontend contract tests must assert DuckMail/Emailnator/bridge/CF dedicated field IDs are absent, while schema-rendered `data-temp-provider-setting` keys and CF actions remain present.

- Secret-safety tests must assert render helpers do not inject secret values and that secret inputs are blank while showing only `*_set` or `*_masked` state.
- Settings save/load tests must assert blank secret fields preserve existing values, masked placeholders are not serialized, and new non-empty secret values are accepted.
- Provider catalog/API tests must assert built-in `config_schema` payloads expose field metadata and never expose secret defaults or plaintext secret values.
- Browser checks are required when generic provider field layout changes. Record desktop and mobile screenshots plus page, Settings pane, and `#tempMailProviderConfigPanel` horizontal overflow.

### 7. Wrong vs Correct

#### Wrong

```javascript
if (provider === 'duckmail') {
  settings.duckmail_bearer_token = document.getElementById('settingsDuckmailBearerToken').value;
  document.getElementById('settingsDuckmailBearerToken').value = savedToken;
}
```

#### Correct

```javascript
renderTempMailProviderConfigPanel(provider);
collectTempProviderSchemaSettings(settings);
```

## Scenario: Shared Mailbox Provider Catalog Loader Lifecycle



### 1. Scope / Trigger



Trigger: frontend surfaces that read provider labels, selector options, pool filters, import providers, or temp-mail status from `/api/providers` catalog data.



### 2. Signatures



- `GET /api/providers -> data.mailbox_providers`

- `static/js/main.js -> loadMailboxProviderCatalog(forceRefresh)`

- `static/js/main.js -> getMailboxProviderCatalogLabel(providerKey)`

- `static/js/main.js -> resolveMailboxProviderLabel(providerKey, options)`

- `static/js/main.js -> refreshAccountProviderTagsFromCatalog()`

- `static/js/features/pool_admin.js -> ensurePoolAdminProviderOptions(forceRefresh)`

- `static/js/features/accounts.js -> loadProviders(forceRefresh)`; concurrent cold/force loads coalesce on `providersLoadPromise` after the `providersLoaded` short-circuit

- `static/js/features/plugins.js -> _refreshMailboxProviderCatalogFromPlugins(forceRefresh)`

- `static/js/features/plugins.js -> ensureLoaded(options)` / `loadPlugins(options)`

- Boot: `DOMContentLoaded` may call non-blocking `loadMailboxProviderCatalog(false)`

- Boot must **not** eagerly fetch `/api/plugins`; plugin list loads on temp-mail Settings tab (`ensureTempMailSettingsTabReady` → `ensureTempMailPluginsReady`), plugin-card expand, or explicit refresh/lifecycle

- Boot must **not** call `initTempMailProviderOptions()` or `initUpdateMethodConfigToggles()`

- Settings open has no empty shared bootstrap stub; tab controls bind only via `ensureTempMailSettingsTabReady()` / `ensureAutomationSettingsTabReady()` when those tabs become active (or when `loadSettings` runs already on that tab). Settings open must **not** fetch `/api/plugins` outside the temp-mail tab ready path

- Temp-mail radios bind via `ensureTempMailSettingsTabReady()` when the temp-mail tab becomes active; automation update-method toggles bind via `ensureAutomationSettingsTabReady()` when automation becomes active

- `applyTempMailSettingsSelection()` only paints radios/config after the temp-mail mount is bound; when unbound it must clear `dataset.pendingProvider` rather than leave a canonicalized pending value from Basic load

- `getCurrentTempMailSettingsProviderSelection()` uses checked radio, then pending only if bound, then snapshot, then operator default

- `collectTempMailSettingsPayload()` when radios are bound: checked radio → pending → snapshot → operator default (normalized). When unbound: use raw `tempMailSettingsSnapshot.temp_mail_provider` if present (do not canonicalize `custom_domain_temp_mail` → `legacy_bridge` on passive global save); otherwise operator default

- Primary Settings UX is `#page-settings` via `navigate('settings')`; `#settingsModal` is a compatibility redirect surface only

- `isSettingsSurfaceActive()` is true when `currentPage === 'settings'` / `#page-settings` is visible **or** `#settingsModal` is shown

- Settings open (`loadSettings`) soft-loads catalog/preflight when `mailboxProviderCatalogCache` is a non-empty array; force only when cache is missing or warm-but-empty. Post-save and temp-mail tab save still force-refresh

- Settings open must **not** always fetch external-api contract-check, operational readiness, or provider preflight; soft-load those only when `currentSettingsTab === 'api-security'` (or when switching to that tab). Save mutations on API security still force-refresh

- `loadExternalApiContractCheck` / `loadOperationalReadinessSnapshot` soft warm paths (`!force && cache`) must re-paint `renderExternalApiCommandCenter` from warm cache before return **only while** `isCurrentApiSecuritySurface()` (`isSettingsSurfaceActive()` + `currentSettingsTab === 'api-security'`) so re-entering api-security does not leave stale/empty command-center chrome while skipping network, and mid-flight tab switches cannot repaint command-center on other Settings tabs

- Settings open must **not** always render provider workbench / external API command center; paint those only when `currentSettingsTab === 'api-security'`. Switching to that tab must snapshot-render then soft-load network panels

- Temp-mail auto-save force-refreshes catalog only; invalidate preflight cache without network. Global Settings save (modal close) force-refreshes catalog and invalidates api-security panel caches without forced preflight/readiness/contract network

- `renderTempMailProviderOptions` no-ops until the Settings mount is bound (`isTempMailSettingsProviderMountBound`) so catalog preload does not rewrite hidden Settings DOM

- Catalog success/error rehydrates Settings selection/config only via `rehydrateTempMailSettingsFromCatalog()` after the mount is bound; account tags, pool, import, and unified labels still refresh on every catalog load

- Catalog success/error and language-change must not rewrite Settings-only provider surfaces while Settings is inactive; use `refreshSettingsProviderSurfaces()` gated by `isSettingsSurfaceActive()`

- Within an open Settings surface, catalog refresh may update temp-mail radios/badges always, but must gate workbench/command-center/diagnostics/guide/contract/pool chips to `currentSettingsTab === 'api-security'` via `paintApiSecuritySurfacesFromSnapshot()`

- Switching to api-security must call `paintApiSecuritySurfacesFromSnapshot()` before soft-loading preflight/contract/readiness so chips/guide/contract are not left on initial loading markup

- `static/js/main.js -> mailboxProviderDefaultTempMailProvider` / `getOperatorDefaultTempMailProvider()`

  caches admin `/api/providers.default_temp_mail_provider` for Settings selection/collection/panel fallbacks (schema routing, config panel, provider change, collect/load)

- Bare `'legacy_bridge'` string remains only inside `getOperatorDefaultTempMailProvider()` as the offline/static fallback



### 3. Contracts



`loadMailboxProviderCatalog` owns the secret-free catalog cache lifecycle (`mailboxProviderCatalogCache` plus diagnostics/selection_policy companions). Consumers must prefer:\n- Force catalog reload: soft joins any in-flight; force joins only force in-flight (\mailboxProviderCatalogLoadForce\) and supersedes soft in-flight so save/refresh always start a true network GET; abandoned soft responses must not write \mailboxProviderCatalogCache\.



1. warm shared cache

2. shared loader (`loadMailboxProviderCatalog`)

3. direct `fetch('/api/providers')` only as last-resort fallback when the shared loader is unavailable



Display labels must prefer `resolveMailboxProviderLabel` / catalog item labels rather than local hard-coded provider maps across:



- account cards and import results

- pool-admin filter options

- temp-email status/domain hints

- unified mailbox cards, preview, readiness list, routing chips, and capability matrix rows

- Settings schema panel titles, provider-integration guide cards, and provider-contract status rows



Catalog success should re-apply dependent UI (account tags, pool-admin filter, import provider select via `loadProviders(true)`, Settings radios, temp-email select). Empty array cache is warm-but-empty: callers that need a real network refill must pass `forceRefresh=true` (or detect empty array and force).



Plugin list loading budget:



- `PluginManager.init()` must not call `loadPlugins()` on every page boot.

- `showSettingsModal` / temp-mail tab / plugin-card expand call `ensureLoaded()`.

- Successful empty plugin list still counts as loaded (`_pluginsLoaded`); do not refetch until `force` / uninstall / applyChanges.

- Ordinary list load soft-loads catalog (`loadMailboxProviderCatalog(false)` unless empty warm cache).

- Uninstall / applyChanges force catalog refresh (`forceCatalogRefresh: true`) then re-inject plugin radios/options.

- Manual plugin-card refresh uses `loadPlugins({ force: true })`.

- `loadPlugins(options)` soft re-entry when `_pluginsLoaded && !force` returns warm list without network or loading flash; list/loading/error chrome paints only while `shouldPaintPluginList()` (`_cardExpanded`); soft joins any in-flight and force joins only force (`_pluginsLoadForce`) and supersedes soft so abandoned soft responses do not apply plugin list/catalog side effects; catalog/radio/select side effects still run after network success even when the card is collapsed; `force` and `forceCatalogRefresh` both count as force.

- `ensureLoaded` soft re-entry (`_pluginsLoaded && !force`) must re-paint via `_renderPluginList` from warm `_plugins` only when the plugin card is expanded, without a second `/api/plugins` GET.



### 4. Validation & Error Matrix



- Boot preload fails -> keep consumers usable with offline/static fallbacks; do not block first paint.

- Cache warm with providers -> consumers apply without a second network request.

- Cache is empty array -> next ensure/load path force-refreshes shared loader instead of treating empty as final.

- Shared loader missing -> last-resort direct fetch or offline fallback is allowed.

- Plugin list never opened this session -> no `/api/plugins` on boot.

- Plugin list loaded empty successfully -> Settings reopen does not refetch `/api/plugins`.

- Plugin list load fails -> leave unloaded so next ensureLoaded retries.

- Plugin uninstall/applyChanges succeeds -> force catalog refresh, then re-inject plugin DOM fallbacks.



### 5. Good/Base/Bad Cases



- Good: pool-admin and import selectors call `loadMailboxProviderCatalog` before any direct `/api/providers` fetch.

- Good: account tags, temp-email status, unified readiness, Settings guide/contract/schema titles resolve through shared helpers after catalog success.

- Good: catalog success calls `loadProviders(true)` so an already-open import modal refreshes offline/stale options.

- Good: boot soft-preloads `/api/providers` once; plugin list does not force a second providers fetch unless registry changed.

- Base: offline import keeps `auto`/`outlook` fallback when catalog is unavailable.

- Bad: each feature module maintains its own hard-coded provider label map.

- Bad: `PluginManager.init()` fetching `/api/plugins` on every page load for users who never open Settings.

- Bad: plugin manager injects options then fires a non-awaited catalog refresh that overwrites them.



### 6. Tests Required



- Frontend contracts assert boot preload `loadMailboxProviderCatalog(false)`, catalog-success `ensurePoolAdminProviderOptions(true)` + `loadProviders(true)`, pool-admin/import shared-loader preference, temp-email/unified/Settings `resolveMailboxProviderLabel` usage, and plugin await-then-reinject order.

- `node --check` on touched JS and `git diff --check` for whitespace.



### 7. Wrong vs Correct



#### Wrong



```javascript

fetch('/api/providers').then(/* feature-local cache */);

// plugin path:

_refreshProviderRadios();

loadMailboxProviderCatalog(true); // not awaited

```



#### Correct



```javascript

await loadMailboxProviderCatalog(forceCatalogLoad);

applyFromSharedCache();

// plugin path:

await loadMailboxProviderCatalog(true);

_refreshProviderRadios();

_refreshProviderSelect();

```



## Scenario: Provider Integration Guide UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that render, copy, filter, or otherwise consume `provider_integration_guide` from `/api/providers` or related provider discovery payloads.


### 2. Signatures



- `GET /api/providers -> data.provider_integration_guide`

- `static/js/main.js: loadMailboxProviderCatalog()` caches the guide response.

- `static/js/main.js: renderProviderIntegrationGuide()` renders guide summary and provider entries.

- `static/js/main.js: buildProviderIntegrationEnvSnippet(provider)` creates copyable `.env` snippets.



### 3. Contracts



The frontend must treat the backend guide as the source of truth. Provider labels, keys, kind, aliases, required/optional env keys, settings keys, activation examples, runtime defaults, pool defaults, pool claim request fields, task temp-mail request fields, readiness, and secret key lists must come from `provider_integration_guide` instead of local provider-specific instruction tables.



Secret key names may be displayed, but secret values must not be rendered or copied. Any key listed in `secret_env` or `configuration.secret_env` must be emitted as `KEY=` in copy helpers, even if a future payload accidentally includes a default value. Any key listed in `secret_settings` or `configuration.secret_settings` must also render with an empty value in guide step text.



GPTMail compatibility aliases must remain data-driven. Do not rewrite `gptmail`, `legacy_gptmail`, `temp_mail`, or `legacy_bridge` semantics in frontend code.



### 4. Validation & Error Matrix



- Missing `provider_integration_guide` or empty `providers` -> render an unavailable or empty state without breaking provider diagnostics or config templates.

- Fetch failure in `loadMailboxProviderCatalog()` -> clear the guide cache and rerender the guide empty state.

- `secret_policy.exposes_secret_values !== false` -> show the unknown secret-policy label instead of implying the payload is secret-free.

- Secret env/default value present in payload -> copy helper must output the key with an empty value.

- Secret setting value present in a guide step -> rendered step text must output the key with an empty value.



### 5. Good/Base/Bad Cases



- Good: DuckMail shows `DUCKMAIL_BEARER_TOKEN` as a required env key and copies `DUCKMAIL_BEARER_TOKEN=`.

- Base: Mail.tm shows public base-url defaults because `MAILTM_API_BASE` is not a secret key.

- Bad: frontend code branches on `provider === "duckmail"` to decide request fields or credential keys.

- Bad: copied snippets include a bearer token, API key, JWT, password, task token, or consumer key value.



### 6. Tests Required



- Frontend contract tests must assert the guide mount, cache, renderer, copy helper, filter controls, CSS hooks, translations, and secret-value masking logic.

- API-backed frontend tests must assert `/api/providers` returns `provider_integration_guide`, exposes secret key names, and does not expose provider secret values.

- Provider/API regressions must cover GPTMail alias preservation and guide consistency with backend selection policy.



### 7. Wrong vs Correct



#### Wrong



```javascript

if (providerName === 'duckmail') {

  return `DUCKMAIL_BEARER_TOKEN=${provider.token}`;

}

```



#### Correct



```javascript

const secretKeys = getProviderIntegrationSecretKeySets(provider).env;

addProviderIntegrationEnvLine(lines, envKey, envDefaults[envKey], secretKeys);

```



## Scenario: Unified Mailbox Command Center UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that render first-viewport status, provider readiness, routing policy, external endpoints, or capability counts for the unified mailbox directory from `/api/mailboxes`.



### 2. Signatures



- `GET /api/mailboxes -> data.summary`

- `GET /api/mailboxes -> data.facets`

- `GET /api/mailboxes -> data.provider_context`

- `GET /api/mailboxes -> data.provider_context.provider_diagnostics.summary`

- `GET /api/mailboxes -> data.provider_context.readiness_summary`

- `GET /api/mailboxes -> data.provider_context.selection_policy.source_priority`

- `GET /api/mailboxes -> data.provider_context.provider_integration_guide.endpoints`

- `GET /api/mailboxes -> data.contract.action_definitions`

- `static/js/features/mailboxes.js -> getUnifiedProviderReadinessSummary(providerContext)`

- `static/js/features/mailboxes.js -> renderUnifiedProviderReadinessSummary(providerContext)`



### 3. Contracts



The command center is a display adapter over `/api/mailboxes`; it must not introduce provider-specific branching or local provider registries. Inventory counts come from `summary` and `pagination`. Provider fleet counts and readiness should prefer `provider_context.readiness_summary.totals`, then fall back to `provider_context.provider_diagnostics.summary` for older payloads. The compact provider-readiness panel must consume `provider_context.readiness_summary` directly, including `totals`, `issues`, `provider_selector_fields`, `routing_matrix`, `endpoints`, and `providers`; it must not derive those rows from provider names or settings inputs. Routing mode comes from `provider_context.provider_filter` plus `defaults.active_mailbox_providers`. Source priority comes from `provider_context.selection_policy.source_priority`. External mailbox entry comes from `provider_context.provider_integration_guide.endpoints.mailboxes`, with documented discovery endpoint fallbacks only when the guide endpoint is absent. Available capability count comes from `contract.action_definitions`; `facets.actions` is result-context data, not a global capability registry.



The readiness summary UI should stay dense and operational: stable metric cells, routing matrix cards, rows with wrapped provider keys/endpoints, and responsive collapse rules for mobile. It may show provider labels, provider keys, selector field names, endpoint paths, readiness status, and counts. If it renders `readiness_summary.routing_matrix`, it must read scopes and providers from the matrix object, not from a local provider table or built-in provider-name branches. It must never render API keys, bearer token values, passwords, JWTs, task tokens, consumer keys, provider secret values, or values read from Settings credential inputs.



### 4. Validation & Error Matrix



- Missing command-center mount -> render helpers must no-op without breaking mailbox list loading.

- `state=loading` -> show loading copy and keep filters/list from rendering stale ready metrics.

- `state=error` -> show unavailable copy while provider context and result bar use their own error states.

- Missing `provider_context.readiness_summary` -> keep command-center and provider-context rendering functional by using diagnostics summary fallbacks.

- Missing or non-version-1 `provider_context.readiness_summary.routing_matrix` -> omit the routing matrix cards without breaking the readiness summary.

- Missing `provider_context.provider_diagnostics.summary.total` -> fall back to provider facet count.

- Missing `contract.action_definitions` -> fall back to positive action facets.

- Empty mailbox result set with configured providers -> provider count and capability count must still show the global catalog values, not zero.

- Long provider keys, selector field names, routing scope labels, and endpoint paths -> wrap inside `.unified-provider-readiness-*` and `.unified-provider-routing-*` containers without page-level horizontal overflow.



### 5. Good/Base/Bad Cases



- Good: empty mailbox directory shows `summary.total = 0` while provider count uses `provider_diagnostics.summary.total` and capability count uses `contract.action_definitions.length`.

- Good: the readiness summary row renders `provider_context.readiness_summary.providers[*].mailbox_count` and selector fields from `provider_context.readiness_summary.provider_selector_fields` without checking for built-in provider names.

- Good: the routing matrix row renders `provider_context.readiness_summary.routing_matrix.scopes` with `Object.values(scopes)` and uses `scope.request_field`, `scope.endpoint`, `scope.counts`, and `scope.providers[*].usable` without provider-specific branches.

- Base: filtered result set uses `facets.providers` for provider distribution chips, but the command center still uses provider diagnostics for fleet readiness.

- Bad: command center displays `0 available capabilities` only because all `facets.actions[*].count` values are zero.

- Bad: frontend branches on `provider === "duckmail"`, `provider === "mail_tm"`, or `provider === "gptmail"` to decide command-center routing copy.

- Bad: readiness rendering reads `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, `settingsTempMailApiKey`, `settingsExternalApiKey`, or any other credential input to decide status or copy.



### 6. Tests Required



- Frontend contract tests must assert the command-center mount, loading/error/ready render calls, CSS hooks, i18n labels, provider diagnostics fallback consumption, readiness summary helper/render consumption, routing matrix helper/render consumption, and contract action-definition consumption.

- API-backed tests must continue to assert `/api/mailboxes` exposes `provider_context`, `provider_integration_guide`, and `contract` in the same payload.

- API-backed tests must continue to assert `provider_context.readiness_summary` is secret-free and carries inventory counts for account and temp providers.

- Browser checks are required for desktop and mobile command-center changes that alter first-viewport density, metric layout, chips, or route text wrapping.



### 7. Wrong vs Correct



#### Wrong



```javascript

const actionCount = (facets.actions || []).filter(item => item.count > 0).length;

const providerCount = (facets.providers || []).length;

```



#### Correct



```javascript

const providerCount = Number(providerContext.provider_diagnostics?.summary?.total || 0);

const actionCount = Array.isArray(contract.action_definitions) ? contract.action_definitions.length : 0;

```



#### Wrong



```javascript

if (provider.provider === 'duckmail') {

  row.status = document.getElementById('settingsDuckmailBearerToken').value ? 'ready' : 'needs_config';

}

```



#### Correct

```javascript
const readinessSummary = getUnifiedProviderReadinessSummary(providerContext);
const providerRows = readinessSummary.providers || [];
```

## Scenario: Unified Mailbox Message Preview UI Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render, refresh, select, copy, or style the unified mailbox message preview panel inside the authenticated mailbox workspace.

### 2. Signatures

- `templates/index.html -> #unifiedMailboxMessagePreview`
- `static/js/features/mailboxes.js -> openUnifiedMessagePreview(item)`
- `static/js/features/mailboxes.js -> loadUnifiedMailboxMessages(item, options)`
- `static/js/features/mailboxes.js -> loadUnifiedMailboxMessageDetail(messageId)`
- `static/js/features/mailboxes.js -> loadUnifiedMailboxVerification()`
- `static/js/features/mailboxes.js -> renderUnifiedMailboxMessagePreview()`
- `static/js/features/mailboxes.js -> renderUnifiedMessageList(messages)`
- `static/js/features/mailboxes.js -> renderUnifiedMessageDetail(message)`
- `static/css/main.css -> .unified-message-*`
- `GET /api/mailboxes/<kind>/<source_id>/messages`
- `GET /api/mailboxes/<kind>/<source_id>/messages/<message_id>`
- `GET /api/mailboxes/<kind>/<source_id>/verification`

### 3. Contracts

The preview panel is a first-party display adapter over authenticated admin endpoints under `/api/mailboxes/...`. It must not call `/api/v1/external/*` or `/api/external/*`, must not read Settings credential inputs, and must not branch on built-in provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail` to decide read behavior.

The card primary action should open the in-place preview. Provider-specific navigation can remain as a secondary action through the existing internal open-mailbox path. Selected-card state must be visual and data-driven from the selected unified item, not from provider-specific CSS classes.

Preview state must cover empty, loading, ready, error, selected mailbox, selected message, verification loading, verification ready, and verification error states. The panel may render `mailbox`, `messages`, `message`, `verification`, `pagination`, and `contract` fields returned by the backend, but it must not persist message bodies, provider handles, task tokens, or mailbox credentials in `localStorage` or Settings form inputs.

All dynamic mailbox emails, provider labels, subjects, senders, previews, message bodies, verification values, endpoint text, and error messages must be escaped before entering `innerHTML`. HTML message bodies may be shown only as escaped or sanitized content owned by the renderer; never insert provider-supplied HTML directly.

The layout must stay dense and operational. Desktop may use a list/detail workbench with side-by-side panes. Mobile must collapse the message workbench to a single column and keep page-level, preview-panel, list, detail, and header horizontal overflow at zero. Intentional inner scrolling is allowed only inside a clearly bounded message body/list area.

### 4. Validation & Error Matrix

- No selected mailbox -> render an explicit empty preview state without fetching messages.
- Loading mailbox messages -> show loading copy and avoid stale selected message content.
- Empty message list -> show an empty list/detail state without throwing.
- Message detail fails -> keep the message list visible and show a detail-level error.
- Verification extraction fails -> keep the selected mailbox and message detail visible and show a verification-level error.
- Language change -> rerender labels from `i18n.js` without rereading Settings credential inputs.
- Long subjects, email addresses, verification links, or provider labels -> wrap inside `.unified-message-*` containers without page-level horizontal overflow.
- Backend returns secret-like fields accidentally -> frontend tests should still fail if render helper slices reference Settings credential inputs or external API endpoints; backend tests remain responsible for payload stripping.

### 5. Good/Base/Bad Cases

- Good: `openUnifiedMessagePreview(item)` reads `item.kind` and `item.source_id`, fetches `/api/mailboxes/${kind}/${source_id}/messages`, selects the first row, then fetches detail through the matching detail endpoint.
- Good: the verification action calls `/api/mailboxes/${kind}/${source_id}/verification` and renders only the returned safe result fields.
- Base: if a source is readable but currently has no messages, the panel still identifies the mailbox and shows a refresh action.
- Bad: selecting DuckMail reads `settingsDuckmailBearerToken` or uses a provider-specific URL path from JavaScript.
- Bad: inserting `message.body_html` directly through `innerHTML` without escaping or sanitizing.
- Bad: writing selected message detail to `localStorage` to preserve the preview across refreshes.

### 6. Tests Required

- Frontend contract tests must assert the preview mount point, render/helper names, event hooks, selected-card state, internal endpoint strings, forbidden external endpoint references, forbidden Settings secret input references, forbidden provider-name branches, i18n labels, CSS hooks, and mobile selectors.
- Backend API tests must cover the `/api/mailboxes/...` endpoints consumed by the panel because the frontend intentionally stays provider-neutral.
- Browser checks are required for material preview layout changes and must inspect desktop and mobile page-level overflow plus `#unifiedMailboxMessagePreview`, `.unified-message-head`, `.unified-message-workbench`, `.unified-message-list`, and `.unified-message-detail-pane` overflow. Screenshots are expected when the workbench structure changes.

### 7. Wrong vs Correct

#### Wrong

```javascript
if (item.provider === 'duckmail') {
  const token = document.getElementById('settingsDuckmailBearerToken').value;
  return fetch('/api/v1/external/messages', { headers: { 'Authorization': `Bearer ${token}` } });
}
```

#### Correct

```javascript
return fetch(`/api/mailboxes/${encodeURIComponent(item.kind)}/${encodeURIComponent(item.source_id)}/messages?folder=inbox`);
```

#### Wrong

```javascript
detailBody.innerHTML = message.body_html;
```

#### Correct

```javascript
detailBody.innerHTML = `<pre>${escapeHtml(message.body || message.body_text || '')}</pre>`;
```

## Scenario: Unified Mailbox Workspace View Switching

### 1. Scope / Trigger

Trigger: frontend changes that regroup, switch, relabel, or style the daily inbox workflow and advanced diagnostics inside the unified mailbox workspace.

### 2. Signatures

- `templates/index.html -> #unifiedWorkspaceViewSwitch`
- `templates/index.html -> #unifiedInboxWorkflow`
- `templates/index.html -> #unifiedDiagnosticsWorkspace`
- `static/js/features/mailboxes.js -> unifiedMailboxState.workspaceView`
- `static/js/features/mailboxes.js -> normalizeUnifiedWorkspaceView(view)`
- `static/js/features/mailboxes.js -> renderUnifiedWorkspaceViewSwitch()`
- `static/js/features/mailboxes.js -> setUnifiedWorkspaceView(view)`
- `static/css/main.css -> .unified-workspace-view-*`
- `static/css/main.css -> .unified-inbox-*`
- `static/css/main.css -> .unified-diagnostics-workspace`

### 3. Contracts

The default view is `inbox`. It keeps filters, quick views, result metadata, summary, directory/list, pagination, and `#unifiedMailboxMessagePreview` in one daily workflow. Activating `diagnostics` reveals the command center, setup guide, operational lens, provider context, and provider capability matrix without clearing filters, pagination, selected mailbox, selected message, or preview data.

Workspace switching is local presentation state. It must not refetch the directory solely because the view changed, call `/api/v1/external/*` or `/api/external/*`, read Settings credential inputs, or branch on built-in provider names. Existing diagnostic DOM IDs remain stable so their render helpers and contract tests continue to work.

Desktop may pair the directory and preview in a bounded grid. Mobile must collapse that grid to one column. Page-level and key-container horizontal overflow must remain zero. A deliberate horizontal quick-view rail is allowed on mobile only when its own overflow is bounded and the document remains overflow-free.

### 4. Validation & Error Matrix

- Missing or unknown view value -> normalize to `inbox`.
- Inbox view -> `#unifiedInboxWorkflow[data-active="true"]` and `#unifiedDiagnosticsWorkspace[data-active="false"]`.
- Diagnostics view -> keep inbox state mounted and set `#unifiedDiagnosticsWorkspace[data-active="true"]`.
- Language change -> rerender switch labels without resetting `workspaceView` or reading form inputs.
- Narrow viewport -> collapse the directory/preview grid; only the quick-view rail may have intentional internal overflow.
- Long mailbox addresses or summary labels -> wrap inside their pane instead of widening `.unified-directory-pane`.

### 5. Good/Base/Bad Cases

- Good: `setUnifiedWorkspaceView('diagnostics')` updates local state and delegates DOM reflection to `renderUnifiedWorkspaceViewSwitch()`.
- Good: the directory and preview remain mounted while diagnostics are revealed, preserving operator context.
- Base: if the switch mount point is absent on an older template, helpers return safely and directory rendering continues.
- Bad: rebuilding the unified mailbox state object during a view change and losing the selected mailbox or preview.
- Bad: hiding diagnostics by deleting or recreating its child panels, which breaks stable DOM hooks.
- Bad: treating mobile quick-view rail overflow as page overflow, or allowing that rail to widen the document.

### 6. Tests Required

- Frontend contract tests must assert the three workspace DOM hooks, default template order, state/helper names, event delegation, active-state attributes, translations, CSS hooks, mobile collapse rules, and secret/external-endpoint safety.
- Existing unified mailbox catalog and backend API tests must remain green because switching is presentation-only.
- Browser QA must cover desktop inbox, desktop diagnostics, mobile inbox, and mobile diagnostics. Record page/body overflow, key-container overflow, active view state, diagnostics state, rendered mailbox-card count, and screenshots.

### 7. Wrong vs Correct

#### Wrong

```javascript
function showDiagnostics() {
  unifiedMailboxState = { workspaceView: 'diagnostics' };
  loadUnifiedMailboxes();
}
```

#### Correct

```javascript
function setUnifiedWorkspaceView(view) {
  unifiedMailboxState.workspaceView = normalizeUnifiedWorkspaceView(view);
  renderUnifiedWorkspaceViewSwitch();
}
```

## Scenario: Unified Mailbox Setup Guide UI Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render first-run setup guidance, ordered setup steps, operator next actions, provider readiness posture, or external API onboarding hints inside the unified mailbox directory.

### 2. Signatures

- `templates/index.html -> #unifiedMailboxSetupGuide` after `#unifiedMailboxCommandCenter` and before `.unified-toolbar`
- `GET /api/mailboxes -> data.summary`
- `GET /api/mailboxes -> data.provider_context`
- `GET /api/mailboxes -> data.provider_context.readiness_summary`
- `GET /api/mailboxes -> data.provider_context.provider_integration_guide`
- `GET /api/mailboxes -> data.provider_context.documentation`
- `static/js/features/mailboxes.js -> getUnifiedSetupGuideModel(data, state)`
- `static/js/features/mailboxes.js -> renderUnifiedSetupGuide(data, state)`
- `static/js/features/mailboxes.js -> renderUnifiedSetupGuideStep(step)`

### 3. Contracts

The setup guide is a display and action adapter over the already-loaded `/api/mailboxes` payload. It must not add a backend endpoint, read Settings form inputs, call `/api/external/*` from the admin browser, or create a local provider registry. It may compute account inventory readiness, temp-mail inventory readiness, provider readiness, and external API onboarding state only from `summary`, `provider_context`, `provider_context.readiness_summary`, `provider_context.provider_integration_guide`, and `provider_context.documentation`.

The guide must remain provider-agnostic. Provider readiness labels and counts should come from aggregate readiness fields such as totals, issues, endpoints, and guide/documentation presence. Do not branch on built-in provider keys such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, `gptmail`, `legacy_bridge`, or future plugin provider names.

The guide actions must route to existing UI affordances: switch to account view, navigate to temp-mail workspace, scroll to provider context, refresh the unified directory, apply existing quick views, or open Settings -> API Security. Actions must not copy provider config, generate credentials, expose external API keys, or render API-key-protected payloads in the admin page.

### 4. Validation & Error Matrix

- Missing setup-guide mount -> render helpers must no-op and existing unified mailbox rendering must continue.
- `state=loading` -> render stable skeleton steps without stale ready actions.
- `state=error` -> show unavailable copy and keep filters/list/provider context independent.
- Empty account inventory -> show an account setup action, not a fatal error.
- Empty temp inventory -> show a temp-mail setup action, not a fatal error.
- Missing `provider_context.readiness_summary` -> show an unknown/provider-check action without provider-specific assumptions.
- Missing integration guide endpoints -> use documented setup copy and omit endpoint-specific text.
- Long endpoint paths, status details, or translated action labels -> wrap inside `.unified-setup-guide-*` containers without page-level or setup-guide internal horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: `getUnifiedSetupGuideModel(data, 'ready')` derives account/temp counts from `summary` and provider readiness from `provider_context.readiness_summary.totals`.
- Good: the external API step displays `/api/v1/external/integration-bundle` when that path arrives from provider context, with no real API key or provider secret values.
- Base: zero mailbox inventory can still render provider and external API steps as ready or partially ready when discovery data is available.
- Base: action buttons call existing functions such as `switchMailboxViewMode('standard')`, `navigate('temp-emails')`, or `switchSettingsTab('api-security')`.
- Bad: the setup guide reads `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, `settingsTempMailApiKey`, `settingsExternalApiKey`, `settingsExternalApiKeysJson`, or any credential input.
- Bad: the setup guide checks `provider === 'duckmail'` or `provider === 'mail_tm'` to decide whether provider routing is ready.

### 6. Tests Required

- Frontend contract tests must assert the setup-guide mount, loading/error/ready render calls, helper names, action event delegation, CSS hooks, mobile collapse rules, and i18n strings.
- Secret-safety tests must assert setup-guide helper slices do not reference Settings credential input IDs, copy token values, or render secret values.
- Provider-agnostic tests must assert setup-guide helper slices do not branch on built-in provider names.
- Browser checks are required on desktop and mobile when setup-guide layout, step density, action rows, or endpoint/status wrapping changes. They must inspect page-level overflow and `.unified-setup-guide` / `.unified-setup-guide-steps` internal overflow.

### 7. Wrong vs Correct

#### Wrong

```javascript
const token = document.getElementById('settingsDuckmailBearerToken').value;
const isDuckMailReady = provider === 'duckmail' && Boolean(token);
```

#### Correct

```javascript
const readiness = providerContext.readiness_summary || {};
const readyProviders = Number(readiness.totals?.ready || 0);
const totalProviders = Number(readiness.totals?.providers || 0);
```

## Scenario: Unified Mailbox Operational Lens UI Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render compact operational recommendations, current-view state, active-filter state, provider readiness posture, or next-action buttons inside the unified mailbox directory.

### 2. Signatures

- `templates/index.html -> #unifiedMailboxOperationalLens` after `#unifiedMailboxResultBar` and before `#unifiedMailboxSummary`
- `GET /api/mailboxes -> data.summary`
- `GET /api/mailboxes -> data.filters`
- `GET /api/mailboxes -> data.pagination`
- `GET /api/mailboxes -> data.facets`
- `GET /api/mailboxes -> data.contract.quick_view_presets`
- `GET /api/mailboxes -> data.provider_context.provider_diagnostics.summary`
- `GET /api/mailboxes -> data.provider_context.readiness_summary`
- `static/js/features/mailboxes.js -> renderUnifiedOperationalLens(data, state)`
- `static/js/features/mailboxes.js -> getUnifiedOperationalRecommendation(...)`

### 3. Contracts

The operational lens is a display and action adapter over the already-loaded `/api/mailboxes` payload. It must not call new backend endpoints, change provider selection behavior, read Settings form inputs, or create local provider registries. It may compute current-view text, active-filter count, provider readiness counts, empty/error/warning/ready state, and recommended actions only from `summary`, `filters`, `pagination`, `facets`, `contract`, and `provider_context`.

Recommended actions must use existing generic actions: refresh the directory, apply an existing quick-view preset, clear to the all-mailboxes preset, or scroll to provider context. The lens may call shared helpers such as `normalizeUnifiedQuickViewFilters`, `getUnifiedQuickViewKey`, `getUnifiedQuickViewPreset`, `applyUnifiedQuickView`, and `getUnifiedProviderReadinessSummary`. It must not branch on built-in provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, `gptmail`, or `legacy_bridge`.

The lens may render provider labels, status labels, counts, endpoint paths, and secret key names already exposed by discovery elsewhere, but it must not read or render API keys, bearer token values, passwords, JWTs, task tokens, consumer keys, provider secret values, or values from credential input IDs.

### 4. Validation & Error Matrix

- Missing lens mount -> renderer no-ops and existing unified mailbox rendering continues.
- `state=loading` -> show loading copy and no actionable buttons that imply ready data.
- `state=error` -> show retry action without clearing current filters.
- `pagination.total_count = 0` -> show empty state and recommend clearing filters when filters are active.
- Provider readiness reports needs-config or inactive counts -> show warning posture and a generic provider-context action.
- Ready non-empty view -> show continue/refresh action without forcing provider-specific remediation.
- Long labels, endpoint paths, or translated copy -> wrap inside `.unified-operational-lens` without page-level, toolbar, or lens overflow on desktop and mobile.

### 5. Good/Base/Bad Cases

- Good: empty filtered result recommends the all-mailboxes quick view by setting `data-unified-lens-action="quick-view"` and `data-unified-lens-view="all"`.
- Good: provider readiness warning recommends scrolling to `#unifiedMailboxProviderContext`, not reading settings credentials.
- Good: the lens uses `getUnifiedProviderReadinessSummary(providerContext)` rather than directly duplicating readiness-summary normalization.
- Base: if readiness summary is missing, fall back to `provider_context.provider_diagnostics.summary` counts and keep the lens visible.
- Bad: `if (provider === 'duckmail')` chooses a DuckMail-specific action or message.
- Bad: lens helpers reference `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, `settingsTempMailApiKey`, `settingsExternalApiKey`, or environment-token values to decide readiness.

### 6. Tests Required

- Frontend contract tests must assert the lens mount order, loading/error/ready render calls, helper names, event delegation hooks, CSS hooks, mobile collapse rules, i18n labels, and secret-safety/provider-agnostic source slices.
- Existing unified mailbox catalog and overview frontend contract tests must remain green because the lens is additive over existing payloads.
- Browser checks are required when changing lens layout or action density. Record desktop and mobile page-level overflow plus `.unified-operational-lens` and `.unified-toolbar` internal overflow.

### 7. Wrong vs Correct

#### Wrong

```javascript
if (provider === 'duckmail') {
  return document.getElementById('settingsDuckmailBearerToken').value ? 'ready' : 'needs_config';
}
```

#### Correct

```javascript
const providerCounts = getUnifiedOperationalProviderCounts(data.provider_context || {});
const lensState = getUnifiedOperationalLensState({ state, totalCount, providerCounts, summary });
```

## Scenario: Unified Provider Capability Matrix UI Consumption


### 1. Scope / Trigger



Trigger: frontend changes that render provider capability, readiness, required config, secret key names, health endpoints, or directory filter endpoints inside the authenticated unified mailbox directory.



### 2. Signatures



- `GET /api/mailboxes -> data.provider_context.provider_integration_guide.providers`

- `GET /api/mailboxes -> data.contract.read_capability_definitions`

- `templates/index.html -> #unifiedProviderCapabilityMatrix` after `#unifiedMailboxProviderContext` and before `#unifiedMailboxList`

- `static/js/features/mailboxes.js -> renderUnifiedProviderCapabilityMatrix(providerContext, contract, state, selectedProvider)`



### 3. Contracts



The matrix is a read-only display adapter over the same `/api/mailboxes` payload as the directory. It must use `provider_context.provider_integration_guide.providers` as the provider row source. Do not consume `provider_context.provider_diagnostics.providers` as the primary data source; directory diagnostics are summary-oriented in this payload.



Each row should derive provider key, label, kind, active/configured state, readiness state, missing config, required/optional env key names, secret key names, read capability, dynamic creation, remote mailbox deletion, message deletion, clear messages, health endpoint, and mailbox directory filter endpoint from that guide entry. Read-capability labels should use `contract.read_capability_definitions` when available.



The browser must not call `/api/external/*` from the matrix, probe provider health, read settings inputs, copy snippets, or inspect any API-key/provider-token input. Secret key names may render, but secret values, bearer tokens, API keys, passwords, JWTs, task tokens, and consumer keys must never render, copy, or log.



### 4. Validation & Error Matrix



- Missing mount -> renderer no-ops and directory loading continues.

- `state=loading` -> replace old rows with a loading placeholder.

- `state=error` -> replace old rows with an unavailable placeholder so stale ready data cannot survive a failed refresh.

- Missing or empty `provider_integration_guide.providers` -> render an empty state.

- Missing capability booleans -> render capability chips as unavailable, not provider-specific guesses.

- Long env keys or endpoint paths -> wrap within the matrix row; no horizontal overflow on mobile or common desktop widths.



### 5. Good/Base/Bad Cases



- Good: DuckMail displays `DUCKMAIL_BEARER_TOKEN` as a key name and does not copy or reveal a token value.

- Good: Mail.tm-compatible providers render from guide capabilities without frontend branches for their provider names.

- Base: a filtered directory uses `selectedProvider` only to mark/filter rows through the existing provider filter path.

- Bad: frontend branches on `provider === "duckmail"`, `provider === "mail_tm"`, `provider === "emailnator"`, or `provider === "gptmail"` to decide capabilities.

- Bad: the matrix reads `#settingsExternalApiKey`, `#settingsExternalApiKeysJson`, provider token inputs, or calls a provider health endpoint from the browser.



### 6. Tests Required



- Frontend contract tests must assert the matrix mount order, renderer name, loading/error/ready render calls, CSS hooks, translations, guide-provider consumption, capability-field consumption, and secret-safety expectations.

- Provider/API regressions must continue to assert `/api/mailboxes` includes `provider_context`, `provider_integration_guide`, and `contract` without leaking secret values.

- Browser checks are required for desktop and mobile when matrix density, grid columns, chip wrapping, or endpoint display changes.



### 7. Wrong vs Correct



#### Wrong



```javascript

if (provider.provider === 'duckmail') {

  return { canDeleteMessage: true, secret: provider.token };

}

```



#### Correct



```javascript

const providers = providerContext.provider_integration_guide?.providers || [];

const capabilities = provider.capabilities || {};

const secretKeys = [...(provider.secret_env || []), ...(provider.secret_settings || [])];

```



## Scenario: Unified Mailbox Quick View Presets UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that add, render, or change one-click preset filters in the unified mailbox directory.



### 2. Signatures



- `templates/index.html -> #unifiedMailboxQuickViews`

- `GET /api/mailboxes -> data.contract.quick_view_presets`

- `static/js/features/mailboxes.js -> getUnifiedQuickViewPresets(contract)`

- `static/js/features/mailboxes.js -> UNIFIED_QUICK_VIEW_PRESETS` as an older-payload fallback only

- `static/js/features/mailboxes.js -> applyUnifiedQuickView(key)`

- `static/js/features/mailboxes.js -> getUnifiedQuickViewKey(filters)`

- `static/js/features/mailboxes.js -> renderUnifiedQuickViews(filters, contract)`

- `static/js/features/mailboxes.js -> getUnifiedMailboxRequestSignature(filters, page, pageSize)`



### 3. Contracts



Quick-view presets are a UI adapter over `data.contract.quick_view_presets` from `/api/mailboxes`. The backend contract is the source of truth for recommended views, labels, descriptions, and filter values; local JavaScript presets are allowed only as a fallback for older payloads that do not include `contract.quick_view_presets`.



Preset filters must only set the existing filter fields: backend contract presets use `kind`, `status`, `read_capability`, `action`, `provider`, `sort`, and `search`; the frontend adapter may normalize `read_capability` to its existing `readCapability` state key. Presets must not add backend fields, infer provider readiness, inspect provider diagnostics, or branch on built-in provider names.



Preset availability should be checked against `contract.filters` when available. Manual changes to search, kind, status, read capability, action, provider, or sort must update the quick-view row so it shows the matching preset or the custom state.



Loading-state changes must be guarded against stale responses. If a request is in flight and the user applies another preset or changes filters, the loader must queue a refresh and avoid rendering a response whose request signature no longer matches the current filters, page, and page size.



### 4. Validation & Error Matrix



- Missing quick-view mount -> render helpers no-op and mailbox loading continues.

- Contract missing or partial -> keep safe local fallback presets available unless the contract explicitly excludes the preset value.

- User applies preset -> update DOM controls, reset page to 1, rerender quick-view active state, and call the existing unified loader.

- User manually edits a filter or search -> active preset becomes the matching preset or custom, never a stale preset.

- In-flight request resolves after filters changed -> do not render stale result data; queue a fresh request with current filters.

- Long labels on mobile -> quick-view row scrolls within its own container without causing page-level horizontal overflow.



### 5. Good/Base/Bad Cases



- Good: `readable` uses `action: "read_messages"` because that value comes from the mailbox contract.

- Good: `attention` uses a contract status such as `inactive` instead of provider readiness diagnostics.

- Base: provider facet chips can still change the provider filter and naturally move the quick view to custom.

- Bad: a preset branches on `provider === "duckmail"`, `provider === "mail_tm"`, `provider === "emailnator"`, or `provider === "gptmail"`.

- Bad: quick-view rendering reads Settings credential inputs, provider API keys, task tokens, bearer tokens, or masked secret placeholders.



### 6. Tests Required



- Frontend contract tests must assert the quick-view mount order, contract-first preset helper, fallback preset definitions, apply/sync helper names, event delegation, active/custom state hooks, request-signature stale-response guard, CSS hooks, mobile CSS hooks, i18n strings, and secret-safety slices.

- API-backed catalog tests should continue to assert that `contract.quick_view_presets` is exposed, provider-agnostic, secret-free, and uses filter values that exist in the `/api/mailboxes` contract.

- Browser checks are required on desktop and mobile when quick-view layout, overflow behavior, or interaction state changes.



### 7. Wrong vs Correct



#### Wrong



```javascript

if (provider === 'duckmail') {

  preset.filters.provider = 'duckmail';

}

```



#### Correct



```javascript

const preset = getUnifiedQuickViewPreset(key);

unifiedMailboxState.filters = normalizeUnifiedQuickViewFilters(preset.filters || {});

setUnifiedQuickViewDomFilters(unifiedMailboxState.filters);

unifiedMailboxState.page = 1;

loadUnifiedMailboxes(true);

```



## Scenario: External API Command Center UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that render, copy, or summarize external API readiness, endpoint paths, starter commands, provider routing, pool state, or API-key posture in Settings -> API Security.



### 2. Signatures



- `GET /api/settings -> data.settings`

- `GET /api/providers -> data.provider_diagnostics`

- `GET /api/providers -> data.deployment_profile`

- `GET /api/providers -> data.provider_integration_guide`

- `templates/index.html -> #externalApiCommandCenter` before `#settingsExternalApiKey`

- `static/js/main.js -> renderExternalApiCommandCenter(settings, state)`

- `static/js/main.js -> getExternalApiCommandStarterCommand()`

- `static/js/main.js -> getExternalApiSmokeCoverageItems()`
- `static/js/main.js -> renderExternalApiBundleLaunchpad(settings, state, providerSummary)`
- `static/js/main.js -> getExternalApiBundleCopyCommand()`
- `static/js/main.js -> copyExternalApiBundleCommand()`
- `static/js/main.js -> renderExternalApiSmokeCheckPanel()`

- `static/js/main.js -> copyExternalApiSmokeCommand()`



### 3. Contracts



The command center is read-only UI over authenticated admin payloads. It must not call `/api/external/*` from the browser and must not read `#settingsExternalApiKey`, `#settingsExternalApiKeysJson`, provider token inputs, masked token values, or plaintext key APIs to build commands.



API-key status comes from `data.settings.external_api_key_set`, `data.settings.external_api_keys_count`, and `data.settings.external_api_keys`. Public mode comes from `data.settings.external_api_public_mode`. Pool state comes from `data.settings.pool_external_enabled` plus the endpoint disable flags `external_api_disable_pool_claim_random`, `external_api_disable_pool_claim_release`, `external_api_disable_pool_claim_complete`, and `external_api_disable_pool_stats`. Routing display comes from `provider_integration_guide.provider_filter`, `provider_diagnostics.filter`, or `data.settings.active_mailbox_providers`. Source priority comes from `provider_integration_guide.source_priority` or `deployment_profile.templates.priority`.



Endpoint paths must prefer `provider_integration_guide.endpoints` and then fall back to stable documented external paths: `/api/external/capabilities`, `/api/external/openapi.json`, `/api/external/mailboxes`, `/api/external/providers`, `/api/external/pool/claim-random`, and `/api/external/temp-emails/apply`. If the guide endpoint map does not include a key, use the stable fallback rather than inventing a provider-specific path.



Copy helpers must use a placeholder header exactly like `X-API-Key: <your-api-key>`. They must never interpolate, copy, log, or render a real key, masked key, DuckMail bearer token, provider JWT, consumer key, password, or task token.



The smoke-check panel is a display and copy adapter for `scripts/external_api_smoke.py`. It must stay inside `#externalApiCommandCenter`, render after the onboarding checklist and before metrics, and expose only the script's read-only discovery coverage: `/api/v1/external/integration-bundle`, `/api/v1/external/health`, `/api/v1/external/capabilities`, `/api/v1/external/providers`, `/api/v1/external/mailboxes?page_size=1`, and `/api/v1/external/openapi.json`. The browser must not execute the smoke checker or call those external endpoints; it only copies a placeholder command such as `OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <origin-or-your-base-url>`.

The Integration Bundle launchpad is the primary external-developer starting point inside the same command center. It must render after the onboarding checklist and smoke-check panel, before detailed metrics, readiness, quickstart, mailbox-session, endpoint, recipe, and workflow sections. It displays the canonical `/api/v1/external/integration-bundle` path, the legacy `/api/external/integration-bundle` alias, placeholder auth, and compact readiness cards derived from settings, provider-catalog caches, and mailbox-readiness cache. It must not fetch the API-key-protected external bundle from the admin browser, because the admin page must not read or reuse configured API keys.

The launchpad copy command must use `curl -s -H "X-API-Key: <your-api-key>" "<origin>/api/v1/external/integration-bundle"` or equivalent placeholder-only output. It must not interpolate Settings API keys, multi-key editor values, masked values, provider bearer tokens, JWTs, passwords, task tokens, consumer keys, or provider secret values.

The External Integration Handoff Kit is the human-copyable companion to the Integration Bundle. It must render in `#externalApiCommandCenter` after `renderExternalApiBundleLaunchpad(...)` and before detailed metrics/readiness sections. Its text builder must compose only existing safe projections: `getExternalIntegrationManifestAuth()`, `getExternalIntegrationQuickstart()`, `getExternalApiBundleEndpointDescriptor(...)`, `getExternalApiSmokeCommand()`, `getExternalApiActionPlan(settings, state, providerSummary)`, `getExternalApiMailboxSessionRequestExamples()`, `getExternalApiStarterBaseUrl()`, and `getExternalApiCommandUrl(...)`. It may include `X-API-Key: <your-api-key>`, canonical/legacy paths, discovery sequence, provider selector field names, mailbox-session start/read/close placeholder examples, local action-plan rows, and documentation links. It must not call external protected endpoints from the admin browser, must not query `document.getElementById(...)` in the handoff builder/copy slice, and must not branch on built-in provider names.


### 4. Validation & Error Matrix



- Missing `#externalApiCommandCenter` -> render helpers no-op and settings loading continues.

- `state=loading` with no settings -> show loading text only, not stale readiness metrics.

- `/api/providers` failure -> show provider-catalog degraded notice while keeping core external endpoint fallbacks visible.

- Settings loaded before provider catalog -> render settings-derived API-key, public-mode, and pool metrics with provider degraded state.

- Provider catalog loaded before or during settings processing -> update `externalApiSettingsSnapshot` before calling `loadMailboxProviderCatalog(true)` to avoid a false `API key missing` flash.

- API key missing -> show calls will be rejected; do not hide endpoint discovery information.

- Pool external enabled with one or more disable flags -> show a partial state and name the disabled pool endpoints.

- Multi-key count missing -> derive count from `external_api_keys` only when it is an array.

- Smoke checker command copied -> command uses `OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key>`, never a Settings API key, multi-key editor value, masked value, provider token, or bearer token.
- Smoke coverage rendered -> coverage list stays fixed to the script's six read-only endpoints, including the integration bundle, and wraps long endpoint paths without horizontal overflow.
- Bundle launchpad rendered -> canonical and legacy paths display together; readiness cards can show degraded states but remain visible.
- Bundle launchpad command copied -> command uses only `X-API-Key: <your-api-key>` and the canonical v1 bundle path.
- Handoff kit rendered -> copied plaintext includes base URL, placeholder auth, canonical bundle endpoint, smoke command, discovery sequence, provider selectors, mailbox-session examples, action plan, and docs links.
- Handoff kit copied -> copy handler uses the last command-center render state from safe state, not DOM credential fields or masked values.
- Provider catalog or mailbox snapshot unavailable -> launchpad keeps endpoint and copy command visible while provider/inventory cards show degraded or loading state.


### 5. Good/Base/Bad Cases



- Good: copied command is `curl -s -H "X-API-Key: <your-api-key>" <origin>/api/external/capabilities`.

- Good: smoke copy command is `OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <origin-or-your-base-url>` and the panel lists `/api/v1/external/integration-bundle` plus `/api/v1/external/mailboxes?page_size=1`.
- Good: bundle copy command is `curl -s -H "X-API-Key: <your-api-key>" <origin>/api/v1/external/integration-bundle`.
- Good: handoff copy text includes `[mailbox_session_start]`, `[mailbox_session_read]`, `[mailbox_session_close]`, `provider`, `provider_name`, and docs links without reading any Settings input value.
- Good: provider catalog failure still shows `/api/external/capabilities` and `/api/external/openapi.json` with a degraded notice.
- Base: provider integration guide supplies `pool_claim_random` and the UI uses that value for the pool endpoint row.
- Bad: command builder reads `document.getElementById('settingsExternalApiKey').value`.
- Bad: handoff builder copies `settingsExternalApiKeysJson`, a provider bearer token, a masked API key value, or branches on a hardcoded provider key to decide examples.
- Bad: smoke panel runs `fetch('/api/external/health')` from Settings or reads `settingsExternalApiKeysJson` to build the command.
- Bad: frontend branches on `provider === "duckmail"`, `provider === "mail_tm"`, or `provider === "gptmail"` to decide command-center endpoints or routing copy.


### 6. Tests Required



- Frontend contract tests must assert mount order before `#settingsExternalApiKey`, renderer helper names, render calls from settings and provider success/failure paths, i18n strings, CSS hooks, and long-text overflow handling.

- Secret-safety tests must assert the copied command contains `X-API-Key: <your-api-key>`, does not contain `X-API-Key: ${`, and the copy helper does not reference `settingsExternalApiKey`.

- Smoke-panel tests must assert the smoke helper/render/copy names, `data-external-api-smoke-copy`, placeholder env auth, the six script-covered endpoints, render order before metrics, and no references to Settings credential inputs.
- Bundle-launchpad tests must assert helper/render/copy names, `data-external-api-bundle-copy`, canonical and legacy endpoint paths, placeholder curl auth, render order before metrics/readiness, CSS hooks, i18n strings, and secret-safety/provider-agnostic source slices.
- Handoff-kit tests must assert helper/render/copy names, `data-external-api-handoff-copy`, render order after Bundle and before metrics, placeholder auth, mailbox-session request keys, action-plan composition, docs links, CSS hooks, i18n strings, and no references to `document.getElementById`, Settings credential input IDs, or built-in provider branches in the handoff slice.
- Data-flow tests must assert `externalApiSettingsSnapshot = data.settings || {};` happens before provider catalog refresh can rerender the command center.
- Browser checks are required on desktop and mobile for first-screen API Security changes, including no horizontal overflow.


### 7. Wrong vs Correct



#### Wrong



```javascript

const key = document.getElementById('settingsExternalApiKey').value;

return `curl -H "X-API-Key: ${key}" ${window.location.origin}/api/external/capabilities`;

```



#### Correct

```javascript
return `curl -s -H "X-API-Key: <your-api-key>" ${getExternalApiCommandUrl('/api/external/capabilities')}`;
```

## Scenario: External API Consumer Usage Console UI Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render per-consumer external API key usage, status, mailbox scope, pool access, or last-used metadata inside Settings -> API Security.

### 2. Signatures

- `GET /api/settings -> data.settings.external_api_keys[*]`
- `data.settings.external_api_keys[*].consumer_key`
- `data.settings.external_api_keys[*].name`
- `data.settings.external_api_keys[*].enabled`
- `data.settings.external_api_keys[*].pool_access`
- `data.settings.external_api_keys[*].allowed_emails`
- `data.settings.external_api_keys[*].today_total_count`
- `data.settings.external_api_keys[*].today_success_count`
- `data.settings.external_api_keys[*].today_error_count`
- `data.settings.external_api_keys[*].today_last_used_at`
- `data.settings.external_api_keys[*].last_used_at`
- `static/js/main.js -> renderExternalApiConsumerUsageConsole(settings)`
- `static/css/main.css -> .external-api-consumer-*`

### 3. Contracts

The consumer usage console is a read-only display adapter over safe `/api/settings` fields. It must stay inside `#externalApiCommandCenter`, after the handoff kit and before aggregate command metrics.

The renderer may display consumer name, `consumer_key`, enabled state, pool access, allowed mailbox scope, current-day total/success/error counts, and last-used timestamps. It must not read `#settingsExternalApiKey`, `#settingsExternalApiKeysJson`, provider credential inputs, plaintext key APIs, masked placeholders, or JSON-editor values. It must not render `api_key`, `api_key_masked`, provider bearer tokens, passwords, JWTs, task tokens, or plaintext external API keys.

Status must be semantic, not color-only: disabled consumers render a disabled label/class, consumers with errors render an error label/class, zero-usage enabled consumers render a no-calls label/class, and successful active consumers render a healthy label/class.

Metric details should be user-facing copy such as `总计`, `请求数`, and `错误数`; do not expose implementation keys such as `configured`, `requests`, `total`, `success`, or `error` as visible detail labels.

### 4. Validation & Error Matrix

- Missing or non-array `external_api_keys` -> render the safe empty state without throwing.
- Consumer missing `consumer_key` -> use a stable local fallback label, not an API key or editor value.
- `allowed_emails` empty -> display all-mailbox scope.
- `allowed_emails` with one item -> display that email address.
- `allowed_emails` with multiple items -> display a count, not an overflowing raw array.
- `today_error_count > 0` -> render error text/class even when success count is also positive.
- `enabled === false` -> render disabled text/class and do not imply current-day health.
- Desktop or mobile viewport -> page, command center, and consumer console must have zero unintended horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: `renderExternalApiConsumerUsageConsole(safeSettings)` consumes only `safeSettings.external_api_keys` and escapes all rendered values.
- Good: the card shows `key:3` as `consumer_key`, `Pool 可用`, `范围: owner@example.test`, `今日有错误`, and `最近使用` from safe settings metadata.
- Base: no multi-key consumers renders a compact empty state explaining that usage appears after multi-key configuration.
- Bad: renderer reads `document.getElementById('settingsExternalApiKeysJson').value` to rebuild consumer rows.
- Bad: visible metric detail text includes `configured`, `requests`, `total`, `success`, or `error` because internal keys were passed directly to the UI.
- Bad: mobile QA checks only `documentElement.scrollWidth` and skips `#externalApiCommandCenter` or `.external-api-consumer-console` overflow.

### 6. Tests Required

- Frontend contract tests must assert helper names, render order after handoff kit and before metrics, CSS hooks, i18n strings, semantic tone classes, and safe-field usage.
- Secret-safety tests must assert the consumer console helper slice does not reference Settings credential input IDs, `source.api_key`, `source.api_key_masked`, `.api_key`, `.api_key_masked`, or `document.getElementById`.
- Text-quality tests must assert user-facing metric details and reject internal detail keys in the consumer console slice.
- Browser checks are required on desktop and mobile for this surface and must inspect page-level overflow, `#externalApiCommandCenter` overflow, and `.external-api-consumer-console` overflow. Use a seeded QA database to cover healthy, erroring, disabled, scoped, unscoped, and empty states when practical.

### 7. Wrong vs Correct

#### Wrong

```javascript
const rows = JSON.parse(document.getElementById('settingsExternalApiKeysJson').value || '[]');
return renderExternalApiConsumerSummaryMetric('今日调用', total, 'requests');
```

#### Correct

```javascript
const keys = Array.isArray(safeSettings.external_api_keys) ? safeSettings.external_api_keys : [];
return renderExternalApiConsumerSummaryMetric('今日调用', summary.totalToday, '请求数');
```

## Scenario: External Integration Quickstart Cockpit UI Consumption


### 1. Scope / Trigger



Trigger: frontend changes that render, copy, or reorganize the Quickstart surface inside Settings -> API Security external API command center.



### 2. Signatures



- `GET /api/providers -> data.quickstart`

- `GET /api/providers -> data.integration_manifest.quickstart`

- `static/js/main.js -> loadMailboxProviderCatalog(forceRefresh)`

- `static/js/main.js -> getExternalIntegrationQuickstart()`

- `static/js/main.js -> renderExternalApiQuickstartCockpit()`

- `static/js/main.js -> getExternalApiQuickstartText()`

- `static/js/main.js -> copyExternalApiQuickstart()`



### 3. Contracts



The quickstart cockpit is a compact display and copy adapter over the backend quickstart contract. It must stay inside `#externalApiCommandCenter` and must not add a second external integration entry point.



`loadMailboxProviderCatalog()` must cache top-level `data.quickstart` separately. `getExternalIntegrationQuickstart()` must return that top-level cache first, then fall back to `getExternalIntegrationManifest().quickstart`. Frontend code must not rebuild quickstart from provider lists, endpoint constants, settings form values, provider-specific env hints, or local provider-name branches when runtime quickstart exists.



The cockpit should show placeholder auth, recommended sequence, provider selector fields, and the primary pool/task request examples. Copied quickstart text must use `X-API-Key: <your-api-key>` or the equivalent quickstart placeholder header. It must never read Settings credential inputs, masked placeholders, provider bearer-token values, provider API keys, JWTs, passwords, task tokens, consumer keys, or provider secret env values.



### 4. Validation & Error Matrix



- Missing top-level `quickstart` with manifest quickstart present -> UI uses `integration_manifest.quickstart`.

- Provider catalog failure -> clear the quickstart cache and keep the existing command-center fallback surfaces visible.

- Missing or empty quickstart -> render an empty quickstart state without breaking endpoints, starter snippets, workflows, or provider recipes.

- Long endpoints, selector allowed values, or JSON request bodies -> wrap inside the quickstart cockpit without page-level horizontal overflow.

- Secret key names present in manifest providers -> quickstart copy remains free of those provider env key names and secret values.



### 5. Good/Base/Bad Cases



- Good: quickstart copy includes `# Auth: X-API-Key: <your-api-key>` and request examples from `quickstart.requests.pool_claim` and `quickstart.requests.task_temp_apply`.

- Good: the UI helper reads `mailboxProviderIntegrationQuickstartCache` before `manifest.quickstart`.

- Base: if quickstart is unavailable, the command center still renders endpoint cards, starter snippets, provider recipes, and workflow playbooks.

- Bad: frontend code reconstructs provider selector fields by branching on `provider === "duckmail"`, `provider === "mail_tm"`, `provider === "emailnator"`, or `provider === "gptmail"`.

- Bad: quickstart copy reads `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey`.



### 6. Tests Required



- Frontend contract tests must assert the quickstart cache, top-level-first helper fallback, cockpit renderer, copy handler, event delegation hook, CSS hooks, i18n strings, and secret-safety slices.

- API-backed UI tests must assert `/api/providers.quickstart` equals `integration_manifest.quickstart`, exposes placeholder auth headers, provider selector fields, pool/task request bodies, and does not include provider secret env key names or values.

- Responsive checks must cover desktop and mobile when quickstart grid, request cards, or copy action layout changes.



### 7. Wrong vs Correct



#### Wrong



```javascript

const token = document.getElementById('settingsDuckmailBearerToken').value;

return `PROVIDER_SECRET_ENV=${token}`;

```



#### Correct



```javascript

const quickstart = getExternalIntegrationQuickstart();

const auth = getExternalQuickstartAuth();

return `# Auth: ${auth.header}: ${auth.placeholder}\n`;

```



## Scenario: Operational Readiness Console UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that render or reorganize the operational readiness console inside Settings -> API Security external API command center.



### 2. Signatures



- `static/js/main.js -> loadOperationalReadinessSnapshot(forceRefresh)`

- `static/js/main.js -> getOperationalReadinessMailboxSnapshot()`

- `static/js/main.js -> getOperationalReadinessCards(settings, renderState)`

- `static/js/main.js -> getOperationalReadinessTaskTempStatus()`

- `static/js/main.js -> renderOperationalReadinessConsole(settings, state)`

- `static/css/main.css -> .operational-readiness-*`



### 3. Contracts



The readiness console is a read-only admin UI over authenticated, local, secret-free payloads. It must stay inside `#externalApiCommandCenter` and must not add a second readiness page or a second external integration entry point.



The console may consume `externalApiSettingsSnapshot`, `/api/providers` caches, and `/api/mailboxes` admin directory payload fields such as `summary`, `provider_context`, `provider_context.readiness_summary`, `contract`, and `facets`. It must not call `/api/external/*` from the browser. External API endpoints may be displayed as documented paths, but readiness data must come from authenticated admin payloads.



The console must remain provider-agnostic. Task temp-mail readiness is derived from provider diagnostics (`active`, `can_dynamic_create`, `status` / `readiness_status`) rather than hardcoded provider names. Account and temp inventory are derived from mailbox directory totals or summary fields.



The console must not read API-key or provider-token form inputs, masked placeholders, plaintext credential values, or external API key editor values. It must not copy or render provider authorization tokens, API keys, JWTs, passwords, task tokens, consumer keys, or provider secret values.



### 4. Validation & Error Matrix



- Settings loaded before provider catalog -> render API-key and pool status while provider and task-temp cards can show loading/degraded state.

- Provider catalog failure -> keep the console visible and mark provider/task-temp readiness degraded without hiding endpoint and quickstart surfaces.

- Mailbox snapshot loading -> show a loading subtitle and keep other readiness cards visible.

- Mailbox snapshot failure -> mark mailbox directory degraded and keep settings/provider-derived cards visible.

- Zero account or temp inventory -> show neutral inventory state, not a fatal error.

- Long endpoint paths, provider counts, or status details -> wrap without page-level horizontal overflow on mobile.



### 5. Good/Base/Bad Cases



- Good: `loadOperationalReadinessSnapshot()` fetches `/api/mailboxes?...page_size=1` and stores only compact `summary`, `provider_context`, `contract`, and `facets` projections.

- Good: `renderExternalApiCommandCenter()` renders `renderOperationalReadinessConsole(safeSettings, renderState)` before quickstart so operators see readiness before examples.

- Base: if mailbox snapshot is unavailable, quickstart, starter snippets, provider recipes, and workflow playbooks still render from their existing sources.

- Bad: calling `/api/external/health`, `/api/external/providers`, or `/api/external/capabilities` from the authenticated Settings page just to compute local readiness.

- Bad: branching on `provider === "duckmail"`, `provider === "mail_tm"`, `provider === "emailnator"`, `provider === "gptmail"`, or `provider === "tempmail_lol"` inside readiness helpers.

- Bad: reading `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey` in readiness helpers.



### 6. Tests Required



- Frontend contract tests must assert the readiness cache variables, mailbox snapshot loader, renderer helper names, `/api/mailboxes` fetch, render order before quickstart, settings/provider/language-change refresh hooks, CSS hooks, and i18n strings.

- Secret-safety tests must assert the readiness helper slice does not reference Settings credential input IDs or built-in provider names.

- Existing provider guide, external API, and unified mailbox contract tests should remain green because this console composes those contracts rather than replacing them.



### 7. Wrong vs Correct



#### Wrong



```javascript

const token = document.getElementById('settingsDuckmailBearerToken').value;

const health = await fetch('/api/external/health', { headers: { 'X-API-Key': token } });

```



#### Correct



```javascript

const snapshot = getOperationalReadinessMailboxSnapshot();

const taskTempStatus = getOperationalReadinessTaskTempStatus();

return renderOperationalReadinessConsole(externalApiSettingsSnapshot, 'ready');

```



## Scenario: External API Contract Check Console UI Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render, refresh, move, or style the local External API contract-check panel inside Settings -> API Security external API command center.

### 2. Signatures

- `GET /api/settings/external-api/contract-check -> { success: true, contract_check: ... }`
- `static/js/main.js -> loadExternalApiContractCheck(forceRefresh)`
- `static/js/main.js -> getExternalApiContractCheckSnapshot()`
- `static/js/main.js -> getExternalApiContractCheckTone(report, state)`
- `static/js/main.js -> renderExternalApiContractCheckPanel()`
- `static/js/main.js -> renderExternalApiContractCheckGroup(group)`
- `static/js/main.js -> renderExternalApiContractCheckRow(row)`
- `static/css/main.css -> .external-api-contract-*`

### 3. Contracts

The contract-check console is a display adapter over the authenticated admin endpoint `/api/settings/external-api/contract-check`. It must stay inside `#externalApiCommandCenter`, render after `renderExternalApiSmokeCheckPanel()` and before `renderExternalApiBundleLaunchpad(...)`, and keep quickstart, handoff, readiness, endpoint, recipe, and workflow panels usable when the check is loading or degraded.

The frontend must not call `/api/v1/external/*` or `/api/external/*` to compute this panel. It must not read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, provider token inputs, masked values, plaintext keys, provider bearer tokens, JWTs, passwords, task tokens, consumer keys, or provider secret values. The only fetch for this panel is the admin contract-check endpoint, and manual refresh must reuse the same loader.

The panel renders the backend report as-is: `status`, `summary`, `groups`, `local_only`, `network_probes`, `mutation_safe`, and bounded `next_actions`. It may map status to presentation tones, but it must not recompute provider readiness, endpoint parity, OpenAPI shape, or secret-scan results in JavaScript. Provider-specific branching is forbidden in contract-check helpers.

The loader must support idle, loading, pass, fail, and error states. It should cache the latest report, share an in-flight promise, refresh when API Security settings are saved, and trigger when the API Security tab is opened so first entry settles without requiring the user to click refresh.

### 4. Validation & Error Matrix

- Initial API Security tab open -> panel appears, fetches `/api/settings/external-api/contract-check`, and settles to `pass`, `fail`, or `error` without requiring a manual click.
- Manual refresh -> use `loadExternalApiContractCheck(true)` and keep other command-center panels visible while loading.
- Endpoint returns pass -> render green/pass badge, counters, safety chips, grouped checks, and next actions.
- Endpoint returns fail -> render attention state from backend groups without hiding quickstart or bundle surfaces.
- Endpoint returns error or request fails -> render local unavailable/error state without leaking exception details or credentials.
- Language change -> rerender from cached report and labels without reading form inputs.
- Desktop and mobile -> page, command center, contract panel, summary grid, group grid, and refresh button must not create unintended horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: `renderExternalApiCommandCenter()` calls `renderExternalApiSmokeCheckPanel()`, then `renderExternalApiContractCheckPanel()`, then `renderExternalApiBundleLaunchpad(...)`.
- Good: tab activation and settings save call `loadExternalApiContractCheck(false)` / `loadExternalApiContractCheck(true)`.
- Good: row rendering escapes backend-provided `name`, `description`, `detail`, labels, action targets, and group labels.
- Base: a loading or error panel may show zero counters while still displaying safety posture copy and a refresh control.
- Bad: calling `/api/v1/external/health`, `/api/v1/external/openapi.json`, or `/api/external/providers` from the admin browser to validate contracts.
- Bad: reading `document.getElementById('settingsExternalApiKey').value` or parsing `settingsExternalApiKeysJson` to run the check.
- Bad: branching on built-in provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail` inside contract-check helpers.

### 6. Tests Required

- Frontend contract tests must assert cache/promise/state variables, loader endpoint, renderer helper names, refresh event hook, settings-save refresh, tab-open refresh, render order after smoke and before bundle, CSS hooks, and i18n labels.
- Secret-safety tests must assert contract-check helper slices do not reference Settings credential input IDs, `/api/v1/external/*`, `/api/external/*`, or built-in provider names.
- Browser checks are required for visual changes and must inspect desktop and mobile page-level overflow plus `#externalApiCommandCenter`, `.external-api-contract-check`, `.external-api-contract-summary`, and `.external-api-contract-groups` overflow.

### 7. Wrong vs Correct

#### Wrong

```javascript
const key = document.getElementById('settingsExternalApiKey').value;
const health = await fetch('/api/v1/external/health', { headers: { 'X-API-Key': key } });
```

#### Correct

```javascript
const report = await loadExternalApiContractCheck(true);
return renderExternalApiContractCheckPanel(report);
```

## Scenario: External Integration Starter Kit UI Consumption


### 1. Scope / Trigger



Trigger: frontend changes that render, copy, or switch external-project starter snippets inside Settings -> API Security external API command center.



### 2. Signatures



- `static/js/main.js -> EXTERNAL_API_STARTER_MODES`

- `static/js/main.js -> getExternalApiStarterSnippet(mode, settings)`

- `static/js/main.js -> buildExternalApiStarterEnvSnippet(settings)`

- `static/js/main.js -> setExternalApiStarterMode(mode)`

- `static/js/main.js -> copyExternalApiCommandSnippet()`

- `static/css/main.css -> .external-api-starter-*`



### 3. Contracts



The starter kit is a display and copy adapter over the existing command-center helpers plus the provider discovery caches. It must stay inside `#externalApiCommandCenter` and must not add a second external integration entry point.



Supported modes are curl, JavaScript fetch, Python requests, and env/config hints. The snippets must prefer `integration_manifest` from `/api/providers`: use `auth.header`, `auth.placeholder`, `auth.curl_header`, `discovery.recommended_sequence`, `discovery.endpoints`, `selection.source_priority`, and `providers[*].env` / `providers[*].request_fields` when present. If the manifest is missing or partial, fall back to `provider_integration_guide.endpoints`, `provider_integration_guide.providers`, and then the documented external API fallbacks already owned by the command center.



The env/config hints mode must consume manifest provider hints first, then guide providers for older payloads. Secret hint objects with `secret: true` must emit `KEY=` even when `value` or `default` exists. Non-secret defaults such as provider base URLs may render from `default` or `value`. The guide fallback must keep using shared provider integration helpers such as `getProviderIntegrationSecretKeySets()` and `addProviderIntegrationEnvLine()`. Do not create provider-specific routing tables or branch on built-in provider names.



All copied snippets must be secret-safe. External API keys use the manifest placeholder, currently `X-API-Key: <your-api-key>` or `<your-api-key>`. Provider secret env keys may be shown as key names with empty values, but secret values, masked placeholders, bearer tokens, API keys, JWTs, passwords, task tokens, and consumer keys must never render or copy. Generated curl commands must quote URLs so manifest queries such as `?kind=all&provider=all` remain one shell argument.



### 4. Validation & Error Matrix



- Missing provider catalog -> keep curl, JavaScript, Python, and core env hints available from stable endpoint fallbacks.

- Provider catalog loaded with `integration_manifest` -> snippets use manifest auth, discovery sequence, endpoint map, provider env hints, request fields, and source priority.

- Provider catalog loaded without manifest -> env/config hints include provider env key names from the current guide, with secret keys emitted as `KEY=`.

- Provider catalog failure -> preserve the command-center degraded notice while still allowing mode switching and copying fallback snippets.

- Language change -> rerender the current starter mode without resetting provider policy or reading form inputs.

- Long endpoints, env keys, or generated code lines -> wrap inside the snippet panel without horizontal overflow on mobile.



### 5. Good/Base/Bad Cases



- Good: the copy button copies `getExternalApiStarterSnippet(externalApiStarterMode, externalApiSettingsSnapshot)`.

- Good: starter builders read `getExternalIntegrationManifestAuth()`, `getExternalIntegrationManifestDiscovery()`, and `getExternalIntegrationManifestProviders()` before guide fallback helpers.

- Good: DuckMail may appear as `DUCKMAIL_BEARER_TOKEN=` when that key name arrives from discovery metadata.

- Good: Mail.tm-compatible provider base URLs render from manifest non-secret defaults while bearer tokens remain blank.

- Base: `getExternalApiCommandStarterCommand()` may remain as a backward-compatible curl wrapper, but the rendered panel should use the selected starter mode.

- Bad: starter builders read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey`.

- Bad: starter builders branch on `provider === "duckmail"`, `provider === "mail_tm"`, `provider === "emailnator"`, or `provider === "gptmail"` to decide routing or credential behavior.



### 6. Tests Required



- Frontend contract tests must assert starter modes, render hooks, event delegation, current-mode copy behavior, CSS hooks, translations, and secret-safety slices.

- Frontend contract tests must assert `/api/providers` `integration_manifest` is cached and starter helpers prefer it while preserving guide fallback.

- Secret-safety tests must assert snippets contain `X-API-Key: <your-api-key>`, do not contain `X-API-Key: ${`, and do not reference API-key or provider-secret input IDs in starter builders.

- Browser checks are required on desktop and mobile when starter layout, code wrapping, or command-center responsive behavior changes.



## Scenario: External Integration Workflow Playbooks UI Consumption



### 1. Scope / Trigger



Trigger: frontend changes that render, select, copy, normalize, or style external-project workflow playbooks inside Settings -> API Security external API command center.



### 2. Signatures



- `GET /api/providers -> data.integration_manifest.workflows`

- `static/js/main.js -> getExternalIntegrationManifestWorkflows()`

- `static/js/main.js -> getExternalApiWorkflowPlaybooks()`

- `static/js/main.js -> getExternalApiWorkflowFallbacks(endpointMap)`

- `static/js/main.js -> renderExternalApiWorkflowPlaybooks(workflows)`

- `static/js/main.js -> getExternalApiWorkflowPlaybookText(workflowKey)`

- `static/js/main.js -> setExternalApiWorkflowPlaybook(key)`

- `static/js/main.js -> copyExternalApiWorkflowPlaybook()`

- `static/css/main.css -> .external-api-workflow-*`



### 3. Contracts



Workflow playbooks are a display and copy adapter over `integration_manifest.workflows`. They must stay inside `#externalApiCommandCenter` and must not add a second external integration entry point. Render logic must prefer manifest workflows first; fallback playbooks are allowed only when the manifest is missing or empty and must be derived from the shared external API endpoint helpers, not from a local provider registry.



Workflow selection must be provider-agnostic. The UI may render provider selector field names and allowed values when those values arrive in the manifest request metadata, but it must not branch on built-in provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail`.



Copied playbook text may include workflow labels, descriptions, endpoint paths, HTTP methods, request field names, response field names, next-action hints, and the external API placeholder auth header. It must never read Settings credential inputs, masked placeholder values, provider bearer tokens, provider API keys, JWTs, passwords, consumer keys, task tokens, or plaintext external API keys.



Long endpoint paths, query/body field lists, provider selector metadata, and copied-text hints must wrap in desktop and mobile layouts without creating page-level horizontal overflow.



### 4. Validation & Error Matrix



- Manifest contains workflows -> render `discover_external_api`, `browse_mailbox_directory`, `claim_pool_mailbox`, and `create_task_temp_mailbox` when present in the payload.

- Manifest missing or empty -> render fallback playbooks from the current endpoint map and keep copy available.

- Selected workflow key missing from the current payload -> normalize to `claim_pool_mailbox` when available, otherwise the first workflow.

- Provider catalog failure -> keep fallback workflow playbooks visible alongside the command-center degraded notice.

- Language change -> rerender the current workflow selection without reading form inputs.

- Long endpoints or metadata -> wrap inside `.external-api-workflow-*` containers; the page must not gain horizontal overflow.



### 5. Good/Base/Bad Cases



- Good: `getExternalApiWorkflowPlaybooks()` reads `getExternalIntegrationManifestWorkflows()` before `getExternalApiWorkflowFallbacks()`.

- Good: `copyExternalApiWorkflowPlaybook()` copies `getExternalApiWorkflowPlaybookText(externalApiWorkflowKey)` through `copyTextToClipboard(playbook)`.

- Good: request hints render `request.provider_selector.field` and manifest-provided allowed values as metadata.

- Base: fallback playbooks include stable external paths such as `/api/external/messages`, `/api/external/verification-code`, pool claim complete/release, and task temp-mail finish.

- Bad: workflow helpers read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey`.

- Bad: workflow helpers branch on provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail`.



### 6. Tests Required



- Frontend contract tests must assert workflow helper names, render hooks, event delegation hooks, copy behavior, manifest-first ordering, fallback availability, CSS hooks, translations, and secret-safety slices.

- Frontend contract tests must assert workflow helper source slices do not reference Settings credential input IDs or built-in provider names.

- API-backed UI tests must assert `/api/providers` includes `integration_manifest.workflows`, exposes the expected workflow keys, includes pool/task lifecycle endpoint paths, and does not include provider secret key names or secret values inside workflows.

- Browser checks are required on desktop and mobile when workflow playbook layout, tab density, endpoint wrapping, hint wrapping, or command-center responsive behavior changes.



### 7. Wrong vs Correct



#### Wrong



```javascript

if (provider === 'duckmail') {

  return [{ endpoint: '/api/external/messages', token: document.getElementById('settingsDuckmailBearerToken').value }];

}

```



#### Correct



```javascript
const workflows = getExternalIntegrationManifestWorkflows();
const playbook = getExternalApiWorkflowPlaybookText(externalApiWorkflowKey);
copyTextToClipboard(playbook);
```

## Scenario: External Mailbox Session Lifecycle UI Consumption

### 1. Scope / Trigger

Trigger: frontend changes that render, copy, normalize, or style the mailbox session lifecycle surface inside Settings -> API Security external API command center.

### 2. Signatures

- `GET /api/providers -> data.integration_manifest.workflows[*].key=start_mailbox_session`
- `GET /api/providers -> data.quickstart.requests.mailbox_session_start`
- `GET /api/providers -> data.quickstart.requests.mailbox_session_read`
- `GET /api/providers -> data.quickstart.requests.mailbox_session_close`
- `static/js/main.js -> getExternalApiMailboxSessionWorkflow()`
- `static/js/main.js -> getExternalApiMailboxSessionRequestExamples()`
- `static/js/main.js -> renderExternalApiMailboxSessionLifecycle()`
- `static/js/main.js -> getExternalApiMailboxSessionLifecycleText()`
- `static/js/main.js -> copyExternalApiMailboxSessionLifecycle()`
- `static/css/main.css -> .external-api-session-*`

### 3. Contracts

The mailbox session lifecycle panel is a display and copy adapter over the backend discovery and quickstart contracts. It must stay inside `#externalApiCommandCenter` and must not add a second external integration entry point.

Render logic must prefer `integration_manifest.workflows` and `quickstart.requests` when available. Fallback data may include stable mailbox session endpoints, but it must be derived from shared external API endpoint helpers rather than a local provider registry.

Copied lifecycle text may include placeholder auth, `POST /api/external/mailbox-sessions/start`, `POST /api/external/mailbox-sessions/read`, `POST /api/external/mailbox-sessions/close`, `session_type`, `read_action`, `claim_token`, `task_token`, `caller_id`, `task_id`, `email`, and safe placeholder handles. It must never read Settings credential inputs, masked placeholder values, provider bearer tokens, provider API keys, JWTs, passwords, consumer keys, or plaintext external API keys.

The UI must remain provider-agnostic. It may show provider selector field names or allowed values only when those values arrive from discovery metadata; it must not branch on built-in provider names to decide session behavior.

### 4. Validation & Error Matrix

- Manifest includes `start_mailbox_session` -> render start, read, and close steps from the manifest workflow.
- Manifest missing or empty -> render the fallback lifecycle from the current endpoint map and keep copy available.
- Quickstart includes mailbox session request examples -> render those examples before fallback examples.
- Quickstart missing request examples -> render placeholder-only start/read/close bodies.
- Provider catalog failure -> keep the lifecycle panel visible with fallback endpoints alongside the degraded command-center notice.
- Language change -> rerender visible labels without reading form inputs.
- Desktop or mobile viewport -> `.external-api-session-*` containers must wrap endpoint paths and JSON bodies without page-level, command-center, or panel-level horizontal overflow.

### 5. Good/Base/Bad Cases

- Good: `getExternalApiMailboxSessionWorkflow()` reads the normalized workflow playbooks and falls back to `getExternalApiWorkflowFallbacks()` only when needed.
- Good: copied examples include both `session_type: pool_claim` with `claim_token` and `session_type: task_temp_mailbox` with `task_token`.
- Good: the copy handler sends `getExternalApiMailboxSessionLifecycleText()` to `copyTextToClipboard()` and uses placeholder auth.
- Base: request metadata such as `read_action_values` can be rendered as chips when it arrives from discovery, but the panel still works without it.
- Bad: lifecycle helpers read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, `settingsEmailnatorApiKey`, or `settingsTempMailApiKey`.
- Bad: lifecycle helpers branch on provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail`.

### 6. Tests Required

- Frontend contract tests must assert lifecycle helper names, render order inside `renderExternalApiCommandCenter()`, copy event delegation, endpoint map keys, quickstart request keys, CSS hooks, translations, and placeholder copy output.
- Secret-safety tests must assert lifecycle helper source slices do not reference Settings credential input IDs or built-in provider names.
- API-backed tests should continue covering mailbox session endpoint discovery through `/api/providers`, OpenAPI, and external smoke paths when those payloads change.
- Browser checks are required on desktop and mobile when `.external-api-session-*` layout, JSON wrapping, summary grid, or copy action placement changes. They must record page-level, command-center, and lifecycle-panel horizontal overflow.

### 7. Wrong vs Correct

#### Wrong

```javascript
if (provider === 'duckmail') {
  return document.getElementById('settingsDuckmailBearerToken').value;
}
```

#### Correct

```javascript
const examples = getExternalApiMailboxSessionRequestExamples();
const lifecycle = getExternalApiMailboxSessionLifecycleText();
copyTextToClipboard(lifecycle);
```

### Mobile Fixed UI Safety

When adding or changing fixed-position UI on mobile, verify it cannot cover business controls in the active page. Prefer docking controls inside the mobile drawer or adding layout-owned space over floating a persistent control above content.


Good examples in this project:



```css

@media (max-width: 768px) {

  #globalLanguageSwitcher.switcher-docked {

    position: static;

    width: 100%;

  }

}

```



Bad pattern:



```css

@media (max-width: 768px) {

  #globalLanguageSwitcher.switcher-docked {

    position: fixed;

    bottom: 12px;

    right: 12px;

  }

}

```



Why this matters: fixed controls can pass static CSS review but still overlap action buttons after `scrollIntoView`, especially in dense operational pages like the unified mailbox directory.



---



## Testing Requirements

For mobile layout changes that involve fixed UI, action rows, or dense cards, add either a frontend contract assertion or a Playwright check that proves the floating or docked element does not overlap the target controls.

For template or static JS changes, add focused Python contract tests that assert stable DOM IDs/classes, script load order, helper names, endpoint keys, copy text placeholders, ARIA hooks, and forbidden secret references.

For standalone JavaScript utilities that export through `module.exports`, add or update Jest/jsdom tests under `tests/layout-system` or `tests/browser-extension`.

For UI layout changes in the unified mailbox workspace, provider workbench, overview dashboard, settings tabs, or external API command center, inspect both page-level overflow and key container-level overflow on mobile and desktop. Screenshots are expected when visual structure changes materially.


---



## Code Review Checklist

- Does the UI keep backend contracts as the source of truth for provider, mailbox, endpoint, and workflow values?
- Are dynamic strings escaped before `innerHTML` insertion?
- Are required mount points, ARIA labels, loading/empty states, and script order covered by contract tests?
- Does mobile CSS reset explicit desktop grid placement and avoid parent/container overflow?
- Are color/radius/spacing choices aligned with existing CSS variables instead of a one-off palette?
- Are production scripts free of `console.log` / `console.debug` and free of references to Settings secret inputs in public copy helpers?
- Are third-party scripts loaded from `static/vendor/` rather than a CDN?
