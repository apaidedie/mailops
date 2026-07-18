# Design: Deep module split (Approach C)

## 1. Goal structure

### Principles

- Split by **responsibility**, not arbitrary line targets.
- One coordinated refactor (Approach C): complete structural move, then unified validation.
- **External** HTTP/API contracts and UX behavior stay stable.
- **Internal** package layout, test imports, and script tags may change aggressively.
- Do **not** re-touch `provider_catalog/` (W4 complete).

### Backend target shape

```text
mailops/
  controllers/
    accounts/                 # was accounts.py
      __init__.py             # re-export public handlers + helpers tests need
      list.py | import_export_http.py | batch.py | ...  # by handler domain
    settings/
    emails/
    system/
    external_temp_emails/     # P1 if multi-domain
    # small controllers stay single-file
  services/
    external_api/             # was external_api.py + external_api_openapi.py
      __init__.py
      runtime.py | probes.py | messages.py | openapi.py | ...
    # other fat services split only when multi-responsibility (P1)
  db/                         # was db.py — import path remains mailops.db
    __init__.py               # re-export get_db, init_db, create_sqlite_connection, ...
    connection.py
    schema.py                 # migrations / version
    helpers.py                # if needed
```

- `routes/*.py` continue to import controller callables only (no services/db).
- Controllers keep HTTP/auth/audit/response orchestration; pure logic stays in services (already true for `account_import_export`).
- Package `__init__.py` re-exports symbols heavily imported by tests to limit blast radius (`_detect_line_type`, `_build_export_text`, external_api helpers, etc.).

### Frontend target shape

```text
static/js/
  core/
    state/                    # was state.js
      store.js | surfaces.js | paint.js | bootstrap.js | ...
    admin/                    # was admin.js
    settings/                 # optional further split of settings.js
    http.js nav.js utils.js poll-ui.js  # further split only if multi-domain
  features/
    mailboxes/                # was mailboxes.js
    accounts/ emails/ groups/ ...
  i18n/                       # optional if i18n.js multi-domain
templates/partials/scripts.html   # ordered list of all modules
tests/frontend_js_bundle.py       # keep contract loader in sync
```

- Prefer **stable global function names** used by templates/onclick/tests.
- Load order is explicit and tested; no bundler in this task.

## 2. Priority inventory

| Pri | Target | Strategy |
|-----|--------|----------|
| P0 | `controllers/accounts,settings,emails,system` | Package by handler/resource domain |
| P0 | `services/external_api` + `external_api_openapi` | Single package, domain submodules |
| P0 | `db.py` | Package; keep `mailops.db` public path |
| P0 | `static/js/core/state.js` | Directory by store/surface/paint/bootstrap |
| P0 | `core/admin.js`, `features/mailboxes.js` | Directory by UI domain |
| P1 | `external_temp_emails` controller, other ≥1k services/features, `i18n.js` | Same patterns when clearly multi-responsibility |
| Skip | `provider_catalog/` | Already split |

## 3. Execution rhythm (big-bang, controlled)

1. Backend structural moves + fix all in-repo Python imports.
2. Frontend structural moves + `scripts.html` + frontend test bundle paths.
3. Unified validation gate (must all pass before “done”).
4. Update Trellis specs for directory layout.
5. Commit as one or two large refactor commits (`refactor(backend):…`, `refactor(frontend):…`).

Local WIP commits allowed for recovery; do not treat partial P0 as complete.

## 4. Compatibility

### Must preserve

- `/api/v1/external/*` paths, auth, envelopes, OpenAPI *semantics*
- Layer boundary rules (`test_module_boundaries`)
- User-visible app behavior
- `from mailops.db import get_db` (and other public db entrypoints already used widely)

### Allowed to break

- File paths under controllers/services/static/js
- Test import paths (update in same change)
- `scripts.html` script list and order
- Private symbol locations (re-export from package root when tests monkeypatch or import them)

### Shock absorbers

- Thin package `__init__.py` re-exports for public symbols
- Frontend: split files first, rename globals only when forced (full-repo search/replace)
- If tests monkeypatch package attributes used inside submodules, mirror W4-style facade `__setattr__` only where proven necessary

## 5. Validation gate

```text
python -m unittest tests.test_module_boundaries
# focused:
#   accounts detect/export, multi_mailbox/unified catalog as relevant
#   external v1 aliases + critical external_api tests
#   db schema/migration tests as relevant
#   frontend contract suite
node --check <all changed js>
python scripts/project_readiness_check.py
git diff --check
```

Success = all of the above green + specs updated + no intentional behavior diffs.

## 6. Rollback

- Before push: reset/revert to task baseline commit on `custom`.
- After commit(s): `git revert` of the refactor commit(s).
- No long-lived half-split branch required if WIP commits are linear and revertible.

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Missed import after package move | Full-repo search for old module paths; run boundaries + import-heavy tests |
| Frontend load-order regressions | Single ordered list in scripts.html + bundle contract tests + node --check |
| Monkeypatch targets break | Re-export + facade setattr where tests require |
| Scope explosion into behavior changes | Strict “structure only” rule; reject drive-by fixes |
| Mega-diff hard to review | Two commits BE/FE; implement.md checklist for file groups |

## 8. Spec updates (required at end)

- `.trellis/spec/backend/directory-structure.md` — package examples for controllers/db/external_api
- `.trellis/spec/frontend/directory-structure.md` (and state-management if needed) — `core/state/*`, feature packages, script order
