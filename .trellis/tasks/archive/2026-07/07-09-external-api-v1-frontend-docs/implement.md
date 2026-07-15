# External API v1 frontend docs canonical Implementation Plan

## Steps

1. Update `static/js/main.js` endpoint fallbacks, starter snippets, smoke checks, degraded-state details, and key hints to default to `/api/v1/external/*`.
2. Update `templates/index.html` and `static/js/i18n.js` external API key/help text to mention v1 plus legacy aliases.
3. Update `README.md`, `README.en.md`, `docs/external-integration-quickstart.md`, and `docs/项目地图.md` to present v1 as canonical and legacy as compatibility.
4. Update frontend contract tests that currently assert legacy fallback strings for user-facing command-center output.
5. Run focused frontend/docs/backend compatibility validation.

## Validation Commands

- `python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_v190_frontend_contract.py -q`
- `python -m pytest tests/test_external_api_versioned_aliases.py tests/test_external_api_smoke_script.py tests/test_multi_mailbox.py -q`
- `python -m py_compile outlook_web/services/provider_catalog.py outlook_web/services/external_api_openapi.py`
- `rg -n "/api/external" static/js/main.js templates/index.html static/js/i18n.js README.md README.en.md docs/external-integration-quickstart.md docs/项目地图.md`
- `git diff --check`

## Risk Notes

- Do not update tests that intentionally call legacy `/api/external/*` routes for backwards compatibility.
- Do not replace `legacy_endpoint` or compatibility metadata examples with v1; those fields intentionally contain legacy aliases.
- Fallback endpoint literals should be centralized where existing helper functions already read endpoint maps; avoid adding new endpoint registries.
