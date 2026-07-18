# Design: Project Full Cleanup Modernization

## Architecture

Four sequential waves; each leaves the app bootable and testable.

```text
W1 Hygiene ──► W2 API surface ──► W3 Frontend split ──► W4 Backend split
   docs/tree        contracts           static/js           mailops/
```

## W1 target tree

```text
docs/
  project-launchpad.md
  runtime-readiness.md
  external-integration-quickstart.md
  provider-onboarding.md
  manual_temp_mail_platform_checklist.md   # keep if still operational
  migration/                               # created in W2
README.md / README.en.md                   # slim links only
tests/test_pool_admin_ui.py                # moved from root
scripts/verify_issue49_governance.py       # moved from root (or tests/)
```

## W1 delete list (tracked)

- `WORKSPACE.md`
- `session/**`
- `preview_dashboard.html`, `screenshot_tc01_auto_banner.png`, `browser-extension.zip`
- Entire historical trees: `docs/API`, `docs/BUG`, `docs/DEV`, `docs/EXPERIENCE`, `docs/FD`, `docs/marketing`, `docs/mockup`, `docs/PRD`, `docs/TD`, `docs/TDD`, `docs/TODO`
- `docs/DEVLOG.md`
- One-off historical docs under `docs/` not in living whitelist (e.g. OAuth pitfall notes, 微软云配置提示词, 项目地图 if superseded by launchpad)
- Root: Chinese plugin/API docs if content superseded by `docs/provider-onboarding.md` / registration API docs moved under `docs/`

## W1 move list

| From | To |
|------|-----|
| `test_pool_admin_ui.py` | `tests/test_pool_admin_ui.py` |
| `verify_issue49_governance.py` | `scripts/verify_issue49_governance.py` |
| `registration-mail-pool-api.en.md` | `docs/registration-mail-pool-api.en.md` (or delete if fully covered by external quickstart — prefer move + link) |
| Root Chinese registration API doc | `docs/registration-mail-pool-api.zh.md` or delete if duplicate |

## Living docs whitelist

Must remain after W1:

- `docs/project-launchpad.md`
- `docs/runtime-readiness.md`
- `docs/external-integration-quickstart.md`
- `docs/provider-onboarding.md`
- `docs/manual_temp_mail_platform_checklist.md` (operational)

## Compatibility

W1 is path/doc only. No runtime API/DB changes.

## Rollback

`git checkout` deleted paths from pre-W1 commit.

## Later waves (summary)

- **W2**: Remove `add_external_api_url_rule` legacy dual-mount; single prefix; update OpenAPI/docs/controllers endpoint strings; `docs/migration/remove-legacy-external-api.md`.
- **W3**: `static/js/core/{nav,settings,shared}.js`; features keep domain; script order in `templates/partials/scripts.html`; contract tests.
- **W4**: Split `provider_catalog.py`, heavy controllers; enforce module boundaries tests.
