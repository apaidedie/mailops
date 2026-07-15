# P1 continue deep module splits

## Goal

Continue deep package splits for remaining multi-responsibility hotspots deferred after `07-15-deep-module-split` (P0).

## Scope (P1)

**Backend**
- `controllers/external_temp_emails.py` → package
- `services/refresh.py` → package (if multi-domain handlers/helpers)

**Frontend**
- `static/js/core/settings.js` → package
- `static/js/i18n.js` → package (if multi-domain)
- Large features when clearly multi-domain: `features/emails.js`, `groups.js`, `accounts.js` (priority order by size/churn)

**Out of scope**
- Re-splitting already packaged domains (`provider_catalog`, `external_api` runtime modules, `db/schema` migration blob as pure dump)
- Behavior/API/UX changes

## Constraints

- Same as deep-split: external API stable; internal paths may break; responsibility-first
- Reuse `scripts/_split_module_package.py` and `scripts/_split_js_file.py`
- Keep public Python import paths stable via package `__init__` re-exports + facades where tests monkeypatch
- JS: `globals.js` + `_load_order.json` + `_function_order.json`; update `scripts.html` and `frontend_js_bundle.py`

## Acceptance Criteria

- [ ] Listed P1 targets packaged (or documented skip with reason)
- [ ] Focused tests green (boundaries, multi_mailbox, external aliases, frontend contracts as touched)
- [ ] `project_readiness_check.py` green
- [ ] Specs updated if layout changes
- [ ] Committed
