# Implement: Deep module split

## Status

`in_progress` — P0 backend + frontend splits done; P1 deferred; close-out in progress.

## Ordered checklist (post-approval)

### Backend

1. [x] Snapshot baseline on `custom`; splitter at `scripts/_split_module_package.py`
2. [x] Split `mailops/db.py` → `mailops/db/` (`constants`, `connection`, `schema`, `sensitive`)
3. [x] Split `controllers/accounts.py` → `controllers/accounts/` (+ import/export re-exports)
4. [x] Split `controllers/settings.py` → `controllers/settings/`
5. [x] Split `controllers/emails.py` → `controllers/emails/`
6. [x] Split `controllers/system.py` → `controllers/system/` (version cache via constants module)
7. [x] Split `services/external_api.py` + openapi → `services/external_api/` (+ shim `external_api_openapi.py`)
8. [x] P1 backend deferred (optional follow-up; P0 complete)
9. [x] Focused Python suites + import smoke (boundaries, export, external, unified, frontend contracts)

### Frontend

10. [x] Split `static/js/core/state.js` → `static/js/core/state/`
11. [x] Split `static/js/core/admin.js` → `static/js/core/admin/`
12. [x] Split `static/js/features/mailboxes.js` → `static/js/features/mailboxes/`
13. [x] P1 frontend deferred (optional follow-up; P0 complete)
14. [x] Update `templates/partials/scripts.html` + `tests/frontend_js_bundle.py`
15. [x] Fix package load order via `_function_order.json` + frontend contract tests (unified/v191/smoke/security OK)

### Close-out

16. [x] Update backend + frontend directory specs
17. [x] Full readiness gate + `git diff --check` (readiness OK; diff --check OK)
18. [x] Commit `b20d0b4d` — deep-split backend + frontend packages
19. [ ] Quality check / archive via finish-work when user requests

## Validation commands

```bash
python -m unittest tests.test_module_boundaries
python -m unittest tests.test_detect_line_type tests.test_export_enhanced_v2
python -m unittest tests.test_external_api_versioned_aliases
python -m unittest tests.test_multi_mailbox tests.test_unified_mailbox_catalog
# add db schema + external_api focused modules as touched
python scripts/project_readiness_check.py
# node --check on every new/changed JS file
git diff --check
```

## Risky files

- `mailops/db.py` (wide import fan-out)
- `mailops/routes/*` (must only rebind callables)
- `services/external_api*.py` (contract surface)
- `static/js/core/state.js` + `scripts.html` (boot order)
- `tests/frontend_js_bundle.py`, `tests/test_module_boundaries.py`

## Rollback points

- After each major package move: if imports fail hard, restore that package only from baseline
- Final: revert refactor commit(s)

## Definition of done

Matches `prd.md` acceptance criteria; design §5 gate green; specs updated.
