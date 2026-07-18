# Implement: Project Full Cleanup

## Wave order

1. **W1** — repository hygiene — **DONE**
2. **W2** — external API canonical-only — **DONE**
3. **W3** — frontend deep split — **DONE** (core JS modules + tokens.css)
4. **W4** — backend modernization — **DONE**

## W4 checklist

1. [x] Convert `mailops/services/provider_catalog.py` → package `provider_catalog/`
2. [x] Extract real domains: `endpoints.py`, `health.py`, `catalog.py`, `integration.py`, `capabilities.py`, `selection.py`, `bridge.py`, `constants.py`
3. [x] Thin `_impl.py` to re-export hub (~100 lines)
4. [x] Extract accounts import/export pure logic → `services/account_import_export.py`
5. [x] Keep public import path `mailops.services.provider_catalog` stable
6. [x] Focused tests green (boundaries, detect/export, multi_mailbox, unified catalog, v1 aliases)
7. [x] Update `.trellis/spec/backend/directory-structure.md` for package layout
8. [x] Full readiness gate + commit (`26ae7627`)

## W3 checklist

1. [x] Split `static/js/main.js` into `static/js/core/{state,poll-ui,nav,http,utils,settings,admin}.js`
2. [x] Update `templates/partials/scripts.html` load order
3. [x] Extract `static/css/core/tokens.css`; link before `main.css`
4. [x] Add `tests/frontend_js_bundle.py` for contract tests
5. [x] Fix contract tests + `node --check` on core modules

## W2 checklist

1. [x] Route helper mounts only `/api/v1/external/*`
2. [x] `compatibility.legacy_supported=false`, empty legacy maps
3. [x] Controllers/audit/docs/CORS/smoke/readiness updated to v1
4. [x] `docs/migration/remove-legacy-external-api.md`
5. [x] Tests green for external API surface

## W1 checklist

1. [x] Inventory references to files being deleted/moved (`rg` README, tests, CI, scripts).
2. [x] `git mv` root test/verify + registration API docs into place.
3. [x] `git rm` WORKSPACE, session, previews, zip, historical docs trees.
4. [x] Update README.md / README.en.md / CONTRIBUTING links; fix readiness scripts if they scan docs.
5. [x] Update `.gitignore` for `session/`, root zip/previews.
6. [x] Run `python scripts/project_readiness_check.py`.
7. [x] Run relocated readiness/CI contract tests (pool UI is manual Playwright, not unittest).
8. [x] `git status` review; no secrets; no accidental living-doc delete.

## Validation commands

```bash
python scripts/project_readiness_check.py
python -m unittest discover -s tests -p "test_pool_admin_ui.py" -v
python scripts/verify_issue49_governance.py   # if still a runnable check
git diff --check
```

## Rollback points

- After deletes, before commit: restore via `git checkout HEAD -- <path>`.
- After commit: revert commit.

## Risky files

- `README.md` / `README.en.md` (many links)
- `scripts/project_readiness_check.py` (may assert doc presence)
- CI workflows under `.github/workflows/`
