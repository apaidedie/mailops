# Split remaining large modules

## Goal

Split remaining oversized single-purpose / multi-handler files after P0/P1, especially `openapi.py` and `temp_emails.js`, plus other easy wins.

## In scope

- `outlook_web/services/external_api/openapi.py` → submodules (builders, schemas, paths, contract)
- `static/js/features/temp_emails.js` → package
- `static/js/features/overview.js` → package (0-indent functions)
- Skip: `i18n.js`, `layout-manager.js` (IIFE / data maps)

## Out of scope

- Behavior, API, UX changes
- Re-splitting already fine-grained packages beyond openapi internals

## Acceptance

- [ ] Targets packaged; public imports stable
- [ ] scripts.html + frontend loaders updated
- [ ] Focused tests + readiness green
- [ ] Commit (+ push if requested)
