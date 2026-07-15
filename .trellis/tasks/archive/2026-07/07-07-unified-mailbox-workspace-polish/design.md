# Unified mailbox workspace polish design

## Boundary

This task changes the authenticated unified mailbox workspace only. It does not change mailbox provider selection semantics, temp-mail provider APIs, mailbox directory response shapes, OpenAPI, external endpoints, database schema, or credential handling.

## Data Flow

`loadUnifiedMailboxes()` already stores `data.contract` in `unifiedMailboxState.contract`. The new command-center quick-view rail will consume the same `getUnifiedQuickViewPresets(contract)` helper used by the quick-view row, and each button will call `applyUnifiedQuickView(key)`. That keeps filter normalization, DOM sync, page reset, in-flight request queuing, and stale-response protection in one path.

The command center will receive current filters from `data.filters || unifiedMailboxState.filters`. It will compute the current quick-view key through `getUnifiedQuickViewKey(filters, contract)` and show a small active/custom state near the recommended views. It will not read provider diagnostics to decide preset membership.

## UI Direction

The first viewport remains an operational dashboard, not a marketing hero. The main command center should use a two-column desktop layout with compact copy and route context on the left, metrics plus contract-backed view shortcuts on the right, then workflow chips below. Loading and error states should use the same shell dimensions so the first viewport does not jump when data arrives.

The visual language is restrained and data-oriented: existing CSS variables, 8px radius, semantic status tints, compact type, visible focus rings, and no decorative blobs or nested cards. On mobile, the quick-view rail scrolls horizontally inside the command center and does not create page-level overflow.

## Compatibility

Existing `#unifiedMailboxQuickViews` remains unchanged as the detailed quick-view row below the toolbar. The command-center rail is a second control surface over the same helper and click path, so it is compatible with old payloads through the fallback presets already owned by `getUnifiedQuickViewPresets()`.

No provider-specific strings or secret key values are introduced. Provider names may appear only when they come from existing data-driven route/context values.

## Tests

Update frontend contract tests to assert command-center quick-view rail helpers, markup hooks, event delegation, CSS hooks, translations, and secret-safety. Browser QA will check desktop and mobile after implementation.
