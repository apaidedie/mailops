# External API Integration Action Plan Implementation Plan

## Checklist

1. Read Trellis backend/frontend specs and cross-layer/code-reuse guides before editing.
2. Add failing/updated tests for the action-plan bundle contract and smoke checker validation.
3. Implement `action_plan` generation in `mailops/services/provider_catalog.py`.
4. Update OpenAPI schemas in `mailops/services/external_api_openapi.py`.
5. Update `scripts/external_api_smoke.py` and its fixtures/tests.
6. Add Settings -> API Security action-plan rendering in `static/js/main.js` and responsive CSS in `static/css/main.css`.
7. Update frontend contract tests for new JS/CSS hooks.
8. Update external integration docs.
9. Run focused validation commands.
10. If UI changed materially, run rendered Settings browser QA at desktop and mobile sizes.
11. Update Trellis specs if a new durable contract is established, then commit, archive, and journal.

## Validation Commands

```powershell
node --check static\js\main.js
python -m pytest tests\test_external_api.py tests\test_external_api_smoke_script.py tests\test_external_api_docs_page.py -q
python -m pytest tests\test_settings_tab_refactor_frontend.py tests\test_ui_settings_external_api_key.py -q
python scripts\project_readiness_check.py
git diff --check
```

If UI browser QA is needed:

- Start Flask with scheduler disabled on a free localhost port.
- Open Settings -> API Security at `1440x1000` and `390x844`.
- Verify the action plan is visible, command/endpoint text wraps, copy buttons do not overlap, and no page/pane/panel horizontal overflow exists.

## Risk Points

- Duplicating recommendation logic without reusing readiness inputs.
- Making action-plan items look authoritative while omitting blocking provider config or pool restrictions.
- Accidentally copying real API keys or provider secrets into commands, docs, tests, or rendered HTML.
- Breaking existing clients by removing or renaming `recommendations`.
- Overcrowding the Settings external API command center on mobile.
