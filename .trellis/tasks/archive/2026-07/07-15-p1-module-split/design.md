# Design: P1 module splits

Inherits Approach C patterns from `07-15-deep-module-split`.

## Backend

| Target | Strategy |
|--------|----------|
| `external_temp_emails.py` | Package by handler groups (providers, session, messages, pool) + helpers |
| `refresh.py` | Package: constants/errors if any, core refresh ops, batch/scheduled helpers |

Public: `from mailops.controllers.external_temp_emails import ...`, `from mailops.services.refresh import ...` via `__init__` re-exports. Facade setattr if tests patch package attrs.

## Frontend

| Target | Strategy |
|--------|----------|
| `core/settings.js` | Package: globals + domain modules (providers, external api settings, temp mail, …) |
| `i18n.js` | Package only if clear domain clusters; else single-file stay if mostly data map |
| `features/{emails,groups,accounts}.js` | Same 8-space function split as mailboxes |

Browser order in `scripts.html`; tests via `frontend_js_bundle` + `_function_order.json`.

## Validation

```text
python -m unittest tests.test_module_boundaries …
python scripts/project_readiness_check.py
node --check <new js>
git diff --check
```
