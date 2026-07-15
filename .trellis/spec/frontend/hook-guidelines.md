# Stateful Helper Guidelines

This project does not use React hooks. Treat this file as the convention for stateful browser helpers, data-fetching functions, and event wiring in static JavaScript modules.

## Stateful Helper Patterns

- Keep feature state in one feature-scoped object or a small group of feature-prefixed variables. Example: `unifiedMailboxState` owns filters, pagination, loading state, and loaded contract data.
- Name helpers by feature and action: `loadUnifiedMailboxes`, `renderUnifiedQuickViews`, `syncUnifiedFiltersFromDom`, `applyUnifiedQuickView`.
- Normalize input before mutating state. Use helper functions for filter values, integers, and API payload shapes.
- Keep event handlers thin: read DOM inputs, update state, and call the relevant loader/renderer.

## Data Fetching

- Use `fetch()` directly. There is no shared query library.
- Build query strings with `URLSearchParams`, not manual string concatenation.
- Read endpoint paths from backend discovery contracts where available. Fallbacks must use canonical constants or helper functions, not provider-specific paths.
- Track in-flight promises for shared discovery payloads to avoid duplicate requests. Existing examples include provider catalog/preflight caches in `main.js`.
- Always handle failure by showing a degraded/empty UI state, not by leaving stale loading text forever.

## Event Wiring

- Template inline handlers exist in legacy areas, but new dense feature modules should prefer event delegation or explicit initializer functions when practical.
- Use stable `data-*` attributes for repeated controls, such as `data-unified-quick-view` and `data-provider-console-filter`.
- Re-render active/pressed states after state changes. Keep `aria-pressed` and class state in sync.

## Browser Storage

- For layout persistence, use `StateManager` or the existing layout state helpers. Guard `localStorage` access with try/catch because it can throw in private or restricted browser modes.
- Include version fields in persisted state and support migration/validation before use.
- Do not store API keys, provider secrets, task tokens, claim tokens, mailbox credentials, or message content in localStorage.

## Common Mistakes

- Creating unprefixed globals that collide with existing `main.js` state.
- Fetching provider/config data separately in multiple renderers instead of sharing a cached discovery promise.
- Leaving a failed fetch in `loading=true` state.
- Reading Settings secret input values to build public copy examples or integration snippets.
