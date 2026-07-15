# PRD: Project Full Cleanup Modernization

## Goal

Make Outlook Email Plus a clean, maintainable personal-dev workspace through a four-wave modernization (W1 hygiene → W2 API surface → W3 frontend split → W4 backend modernization). Historical process docs are removed (recoverable via git). Breaking changes are allowed and documented.

## Background

- Root clutter: `WORKSPACE.md`, loose Chinese API/plugin docs, preview/screenshot/zip, root-level test/verify scripts.
- `docs/` holds ~140 historical PRD/FD/TDD/TODO/BUG/DEV process files; living docs are few (`project-launchpad`, `runtime-readiness`, external/provider guides).
- Runtime debt deferred to later waves: `static/js/main.js` ~12k lines, dual `/api/external/*` + `/api/v1/external/*`, fat services/controllers.
- Acceptance audience: solo developer continuing work (findability + editability), not open-source marketing polish.

## Confirmed Decisions

| Decision | Choice |
|----------|--------|
| Scope | Full cleanup (all four waves) |
| Compatibility | Breaking changes allowed |
| Audience | Solo developer |
| Historical docs | Delete; rely on git history |
| Code depth | Deep refactor (W3–W4) |
| Delivery | Four phased waves (A) |

## Requirements

### R1 — W1 Repository hygiene
1. Remove tracked historical process docs under `docs/{API,BUG,DEV,EXPERIENCE,FD,marketing,mockup,PRD,TD,TDD,TODO}/`, `docs/DEVLOG.md`, and other one-off historical markdown not in the living set.
2. Remove `WORKSPACE.md`, `session/`, root preview/screenshot/zip artifacts.
3. Relocate root `test_pool_admin_ui.py` → `tests/`; `verify_issue49_governance.py` → `scripts/` or `tests/` as appropriate.
4. Consolidate root API/plugin Chinese/English loose docs into living `docs/` paths or delete if redundant with `docs/provider-onboarding.md` / external guides.
5. Slim README entry points to living docs only; fix broken links.
6. Tighten `.gitignore` for residual local clutter (`session/`, root zip/previews if recreated).

### R2 — W2 External API surface (later)
- Canonical-only `/api/v1/external/*`; remove legacy `/api/external/*` mounts and dual endpoint strings; migration note under `docs/migration/`.

### R3 — W3 Frontend deep split (later)
- Split `main.js` / `main.css` into `static/js/core/` + `features/`; keep no-build Flask static model; update contract tests.

### R4 — W4 Backend modernization (later)
- Split fat services/controllers; remove dead projections; align with `.trellis/spec/backend/*`.

## Acceptance Criteria

### W1 (this implementation slice)
- [ ] No `WORKSPACE.md`, `session/`, root `preview_dashboard.html`, `screenshot_tc01_auto_banner.png`, `browser-extension.zip` in git tree.
- [ ] Historical `docs/` process directories removed; living docs remain: `project-launchpad.md`, `runtime-readiness.md`, `external-integration-quickstart.md`, `provider-onboarding.md`, plus any intentionally kept operational checklists.
- [ ] Root test/verify scripts live under `tests/` or `scripts/`; imports/CI still discover them if needed.
- [ ] Root Chinese/English loose API docs either deleted or moved under `docs/` with README links updated.
- [ ] `python scripts/project_readiness_check.py` passes.
- [ ] Targeted tests still pass for relocated modules if any.

### Full program (parent)
- [ ] W1–W4 each green independently with CHANGELOG notes for breaking waves.
- [ ] Living knowledge: `.trellis/spec/*` + slim `docs/*` only.

## Out of Scope (W1)

- Removing `/api/external/*` legacy routes (W2).
- Splitting `main.js` (W3).
- Backend service decomposition (W4).
- DB schema migrations / provider default migration residual (`custom_domain_temp_mail`).

## Risks

- Broken README/docs links after deletes → fix in same W1 PR.
- CI or tests referencing deleted paths → grep and update.
- Accidental deletion of living operational docs → whitelist living set explicitly.
