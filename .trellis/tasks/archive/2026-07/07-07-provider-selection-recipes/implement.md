# Provider Selection Recipes Implementation Plan

## Steps

- Add backend recipe builder helpers in `outlook_web.services.provider_catalog`.
- Expose recipes from deployment profile, selection policy, provider integration guide, and integration manifest.
- Extend external OpenAPI schemas for the new recipe payload.
- Add backend tests for recipe presence, derivation, future-provider behavior, and secret safety.
- Add or update frontend contract tests only if existing Settings UI slices need to reference the new fields.
- Run provider/API regression tests and static secret scans.

## Validation Commands

- `python -m pytest tests/test_external_api.py tests/test_unified_mailbox_catalog.py -q -rs`
- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q -rs`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\\s*=\\s*dk_|Bearer\\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml outlook_web`
- `git diff --check`

## Rollback Notes

The change is additive. If a schema or payload regression appears, revert the recipe exposure and helper tests without touching existing provider selection behavior.
