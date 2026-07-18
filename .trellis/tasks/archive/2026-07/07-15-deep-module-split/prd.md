# Deep module split (controllers, services, frontend)

## Goal

Split oversized backend controllers/services/db modules and oversized frontend JS modules into responsibility-bounded packages in one coordinated refactor (Approach C), so the codebase is easier to navigate and change without changing external API behavior or product UX.

## Background / confirmed facts

- W1–W4 full cleanup is done (`provider_catalog` already a package; frontend already has `static/js/core/*` + features load order).
- Largest backend hotspots (approx lines): `controllers/accounts.py` (~2300), `services/external_api_openapi.py` (~2121), `services/external_api.py` (~1476), `controllers/settings.py` (~1482), `controllers/emails.py` (~1393), `db.py` (~1259), `controllers/system.py` (~1165), `controllers/external_temp_emails.py` (~968).
- Largest frontend hotspots: `static/js/core/state.js` (~5800+), `features/mailboxes.js` (~3100+), `core/admin.js` (~2500+), `i18n.js` / `core/settings.js` / other features ≥1k.
- Layer rules live in `.trellis/spec/backend/directory-structure.md` and frontend directory/state specs; `tests/test_module_boundaries.py` enforces routes isolation.
- Many tests import symbols from `mailops.controllers.accounts`, `mailops.services.external_api`, and `mailops.db`.

## Requirements

1. **Backend package splits (P0):** Convert fat modules into packages with thin public re-exports where useful:
   - `controllers/accounts`, `settings`, `emails`, `system` (and P1: `external_temp_emails` if multi-responsibility)
   - `services/external_api` (fold `external_api.py` + `external_api_openapi.py` into one package with clear submodules)
   - `db` → package preserving import path `mailops.db` for `get_db`, `init_db`, `create_sqlite_connection`, schema helpers
2. **Frontend package splits (P0):** Split `core/state.js`, `core/admin.js`, `features/mailboxes.js` into directories by responsibility; update `templates/partials/scripts.html` and `tests/frontend_js_bundle.py` (or equivalent) for load order.
3. **P1 in same delivery:** Other ≥~1k line controllers/services/features/`i18n.js` when clearly multi-responsibility; do not leave half-split P0 files.
4. **Compatibility:** External `/api/v1/external/*` contracts and user-visible behavior unchanged. Internal module paths, test imports, and static script paths may change aggressively.
5. **Boundaries:** Preserve existing layer rules (routes vs controllers vs services vs repositories vs db).
6. **No product changes:** No feature work, no API field changes, no UI redesign, no dependency upgrades as part of this task.
7. **Docs/specs:** Update `.trellis/spec/backend/directory-structure.md` and frontend directory-structure (and related) to match new layout.
8. **Delivery style:** Approach C — coordinated big refactor with unified validation gate before claiming done (local WIP commits OK; no half-split “done” state).

## Acceptance Criteria

- [ ] P0 backend modules above exist as packages (or equivalent domain modules) with routes still binding controller callables only.
- [ ] `from mailops.db import get_db` (and other currently public db helpers used in-repo) still works.
- [ ] Public external API behavior unchanged; readiness + focused external tests green.
- [ ] P0 frontend files split; app script load order documented and contract tests updated; `node --check` passes on changed JS.
- [ ] `tests/test_module_boundaries.py` green.
- [ ] Focused regression set green (accounts detect/export, multi_mailbox/unified catalog as relevant, external v1 aliases, db schema tests as relevant, frontend contracts).
- [ ] `python scripts/project_readiness_check.py` green; `git diff --check` clean on commit.
- [ ] Spec directory docs updated for new backend/frontend layout.
- [ ] No intentional behavior/API/UX diffs beyond structure.

## Out of scope

- Re-splitting `provider_catalog/` (already done in W4)
- TypeScript migration, bundler introduction, new UI framework
- Changing external API paths or envelopes
- Unrelated bugfixes or features
- Pushing to remote (unless separately requested)

## Constraints

- Solo developer; breaking internal imports allowed
- Prefer responsibility cuts over hard line-count caps (line count is guidance only)
- Keep global JS entry names stable when templates/tests depend on them

## Open questions

- (none blocking — decisions locked in design interview: both BE+FE, deep split, aggressive internal breaks, responsibility-first, Approach C)
