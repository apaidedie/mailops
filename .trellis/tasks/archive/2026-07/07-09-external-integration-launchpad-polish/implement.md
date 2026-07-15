# External integration launchpad polish implementation plan

## Checklist

- [x] Start the Trellis task after planning artifacts are complete.
- [x] Load frontend/backend specs before editing.
- [x] Add `integration_bundle` to external command endpoint and smoke coverage lists.
- [x] Add launchpad helpers for endpoint metadata, summary cards, and placeholder copy command.
- [x] Render the launchpad inside `renderExternalApiCommandCenter()` before operational readiness/quickstart details.
- [x] Add copy handler and toast text for the launchpad command.
- [x] Add responsive CSS hooks for launchpad layout, summary cards, endpoint rows, command block, and mobile collapse.
- [x] Add i18n entries for all new visible strings.
- [x] Update frontend contract tests for launchpad rendering, ordering, copy hook, endpoint coverage, secret-safety, provider-agnostic behavior, CSS, and translations.
- [x] Run targeted frontend/external API tests and repository readiness check.
- [x] Update specs only if the implementation adds a reusable contract beyond current documented frontend rules.
- [ ] Commit the task, archive it, and record journal progress.

## Validation Commands

```powershell
python -m pytest tests\test_settings_tab_refactor_frontend.py -q
python -m pytest tests\test_external_api.py tests\test_external_api_docs_page.py -q
python scripts\project_readiness_check.py
git diff --check
```

If UI rendering tooling is available, also run a desktop and mobile browser check for Settings -> API Security and inspect horizontal overflow in the command center.

## Risk Points

- `static/js/main.js`: avoid reading credential input IDs in new helper slices.
- `static/css/main.css`: keep mobile Settings card width overrides and avoid implicit grid overflow.
- `tests/test_settings_tab_refactor_frontend.py`: existing tests use source-slice assertions, so new helper placement should keep secret-safety slices easy to inspect.

## Rollback Points

- Revert the new launchpad helper/render/copy additions in `static/js/main.js`.
- Revert `.external-api-bundle-*` styles in `static/css/main.css`.
- Revert new translations in `static/js/i18n.js`.
- Revert launchpad-specific test additions.
