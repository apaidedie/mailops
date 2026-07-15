# State Management

The frontend uses plain JavaScript state, DOM state, backend contracts, and limited browser storage. There is no global state library.

## State Categories

- Global app state lives mostly in `static/js/main.js`: current page, selected account/group, provider discovery caches, settings snapshots, and layout settings.
- Feature state lives in feature modules with a feature prefix, such as `unifiedMailboxState` in `static/js/features/mailboxes/` (see package `globals.js` + domain modules).
- Server state is fetched from Flask API endpoints and should be treated as authoritative. Do not duplicate provider/default rules in frontend constants when discovery contracts expose them.
- DOM state is acceptable for form controls, but sync it into a normalized state object before fetches or renders.
- Persistent browser state is limited to UI preferences such as layout and selected view mode; use versioned storage and validation.

## When To Use Global State

Use globals only when multiple feature modules or page shell code need the same data, such as current navigation state, provider catalog cache, or settings snapshots. Keep one owner for each global and document the owner through naming.

Do not promote temporary render state to `main.js` when it is local to one feature panel. Keep it in that feature module.

## Server Contract State

- The backend owns enums and definitions for mailbox directory filters, provider readiness, external endpoints, and integration workflows.
- Hydrate UI controls from `contract.*_definitions`, `provider_context`, `readiness_summary`, `integration_manifest`, and `quickstart` payloads.
- If discovery fails, show fallback placeholders and degraded status, but do not invent a new provider registry in JS.

## Derived State

- Derive quick-view active keys, summary text, and chips from the normalized state object plus backend contract definitions.
- Recompute derived DOM after every state mutation rather than manually patching several disconnected nodes.
- Keep pagination and filter signatures explicit so pending reloads can detect stale requests.

## Storage

- `localStorage` is used for mailbox view mode and layout state. Always guard access and provide defaults.
- Persisted state must include a version and be validated/migrated before use; follow `static/js/state-manager.js`.
- Do not persist secrets, tokens, credentials, mailbox content, or provider config values.

## Common Mistakes

- Duplicating backend enum values in JS beyond minimal startup placeholders.
- Updating DOM controls without updating the feature state object, causing the next reload to use stale filters.
- Reusing a cache after settings/provider configuration changed without exposing a forced refresh path.
- Storing operational handles such as claim tokens or task tokens in long-lived browser storage.
