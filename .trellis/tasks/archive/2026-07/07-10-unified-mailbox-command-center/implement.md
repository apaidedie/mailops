# Implementation Plan

## Checklist

- [x] Read relevant Trellis backend/frontend/shared specs before editing code.
- [x] Add backend command-center projection helper in `outlook_web/services/overview_command_center.py` and compose it from the overview controller.
- [x] Add backend tests for command-center schema, degraded fallback, and secret safety.
- [x] Add `renderOverviewCommandCenter` and small formatting helpers in `static/js/features/overview.js`.
- [x] Add Overview Dashboard CSS classes for the command center in `static/css/main.css`.
- [x] Add i18n entries for new dashboard labels in `static/js/i18n.js`.
- [x] Update frontend contract tests to assert render order, labels, CSS hooks, responsiveness, and secret safety.
- [x] Run focused tests and fix failures.
- [x] Run rendered desktop/mobile dashboard checks with Playwright or an equivalent browser automation path.
- [x] Run `git diff --check`.

## Validation Commands

```powershell
python -m pytest tests/test_overview_api.py tests/test_overview_frontend_contract.py
python -m pytest tests/test_unified_mailbox_catalog.py tests/test_unified_mailbox_frontend_contract.py tests/test_settings_tab_refactor_frontend.py
python scripts/project_readiness_check.py
git diff --check
```

Rendered QA:

```powershell
python scripts/start_local_demo.py --port 5064
# Browser check dashboard at http://127.0.0.1:5064 on desktop and mobile widths.
```

## Risk Points

- `overview.py` currently performs SQL-only summary aggregation. Calling `list_unified_mailboxes` adds service-layer aggregation, so failures must be contained.
- `/api/overview/summary` is TTL cached. Tests that mutate provider settings may need cache reset or direct repository calls.
- `overview.js` has existing secret-safety tests around the External API section. New command-center code must not include secret-related setting ids or raw key fields.
- CSS must stay inside the existing Overview Dashboard block to avoid broad visual regressions.
