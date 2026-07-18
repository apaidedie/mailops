# Unified mailbox workspace polish

## Goal

Turn the unified mailbox first viewport into a calmer operational workspace that makes the mailbox aggregation model immediately actionable. The command center should not only describe Outlook, IMAP, temp-mail, provider routing, and external access; it should also let users jump into the most useful shared directory views from the same contract-backed source of truth.

## UI Brief

Audience: operators and builders who manage account mailboxes, temp-mail providers, and external API integrations under time pressure.

Primary workflow: scan overall inventory and provider readiness, choose a recommended mailbox view, then refine filters or open mailbox records.

Product archetype: operational SaaS dashboard. Keep density high but calm, with restrained colors, stable grid dimensions, and status-oriented hierarchy.

Constraints: Flask templates, static CSS, and static JavaScript; no frontend framework or component library detected. Existing CSS variables, card radius, contract-driven unified mailbox APIs, i18n, secret-safety rules, and mobile layout rules must remain the source of truth.

Source of truth: `/api/mailboxes` response data, especially `contract.quick_view_presets`, `summary`, `facets`, `provider_context`, and `pagination`.

States: loading, error, ready, active quick view, custom filters, mobile scroll, focus-visible, and disabled/loading refresh state.

## Requirements

- Add a command-center quick-view rail driven by `contract.quick_view_presets`, not by a second local preset registry.
- The rail must expose recommended views as accessible buttons and apply the existing quick-view flow, including DOM filter sync, page reset, stale-response guard, and custom state behavior.
- Loading and error command-center states must keep stable first-viewport dimensions and avoid blank or frozen UI.
- Visual styling must stay operational, compact, and responsive. It must avoid nested cards, decorative blobs, one-note palettes, text overflow, and layout shifts.
- Mobile layout must keep the new command-center rail readable without causing page-level horizontal overflow.
- The implementation must stay provider-agnostic and secret-safe. It must not branch on `duckmail`, `mail_tm`, `emailnator`, `gptmail`, or other provider names, and must not read or render credential input values.
- Existing unified mailbox directory APIs, external API contract behavior, provider capability matrix, quick-view row, result bar, manual filters, and mailbox open flows must keep working.

## Acceptance Criteria

- [x] `static/js/features/mailboxes.js` renders a command-center quick-view rail from `getUnifiedQuickViewPresets(contract)` and applies views through the existing `applyUnifiedQuickView(key)` path.
- [x] The command center reflects the active quick view or custom filter state consistently with the existing quick-view row.
- [x] Loading and error command-center states include stable, polished UI states instead of a bare single-line placeholder.
- [x] `static/css/main.css` defines responsive command-center quick-view rail styles, focus states, and mobile wrapping/scroll behavior.
- [x] `static/js/i18n.js` covers any new visible labels.
- [x] Frontend contract tests cover the new helper names, event delegation, CSS hooks, i18n strings, provider-agnostic behavior, and secret-safety slices.
- [x] Rendered desktop and mobile checks show no blank command center, no incoherent overlap, and no page-level horizontal overflow.
- [x] `node --check static/js/features/mailboxes.js`, targeted pytest, `git diff --check`, debug-console scan, and DuckMail-token scan pass.

## Notes

- UI design skill evidence: `ui-design-suite` routed this work to `ui-ux-pro-max`; the design-system search recommended a data-dense operational dashboard with stable filters, status colors, loading feedback, and responsive checks.
- Audit findings fixed: the startup template still used the removed `.unified-command-center-empty` placeholder, so the initial shell now matches the JS loading state. Desktop `grid-column: 2` placement also created a mobile implicit-column squeeze; mobile/tablet CSS now resets command-center children to `grid-column: 1 / -1` and `grid-row: auto` where needed.

## Verification

- `node --check static/js/features/mailboxes.js`
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_unified_mailbox_catalog.py -q` -> 22 passed
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_unified_mailbox_catalog.py tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_multi_mailbox.py -q` -> 194 passed, 5 subtests passed
- `git diff --check`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml mailops` -> no matches
- `rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'` -> no matches
- Playwright QA on `http://127.0.0.1:5017` with a temporary database: `output/playwright/unified-mailbox-desktop.png`, `output/playwright/unified-mailbox-mobile.png`, and `output/playwright/unified-mailbox-qa.json`. Desktop rail rendered 5 buttons with page overflow 0; mobile rail rendered as internal horizontal scroll with page overflow 0; clicking `readable` set `action=read_messages`; clicking `temp` set `kind=temp`.
