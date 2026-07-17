# Design — UI workflow polish A–E

## Principles

1. **Workflow-first defaults** — first paint = next useful action, not documentation.
2. **Collapse, don’t delete** — advanced/diagnostic stay behind `<details>` / tabs / collapsible panels.
3. **Same rules every surface** — thin pass, low risk, independently shippable.
4. **Contract-aware** — frontend unittest contracts often assert DOM strings; update tests with UI, never leave red main.
5. **No API churn** — templates/JS/CSS/i18n only unless a pure presentation helper is required.

## Shared UI patterns

| Pattern | Implementation |
|---------|----------------|
| Quiet chrome | Remove/hide kickers, page essays, `*-command-center` default hero blocks |
| Collapsed advanced | `<details class="…-advanced">` or existing tab shells; default `open=false` |
| Short help | Prefer `title` / `aria-label`; optional one-line hint |
| Empty state | Icon + one sentence + primary button |
| Cache bust | Bump `ui-modern.css?v=` in `templates/index.html` / `login.html` when CSS changes |

## Architecture boundaries

```
templates/index.html, partials/modals.html   → structure, default visibility
static/js/features/**                       → render/empty/command blocks
static/js/core/nav.js                       → topbar titles, mailbox actions
static/js/core/state/external_api_ui_*.js   → API command head
static/js/i18n.js                           → copy keys
static/css/core/ui-modern.css               → density, collapsed sections
tests/test_*frontend*contract*.py           → lock behavior
```

**No changes expected:** Graph/IMAP services, external API route contracts, pool claim semantics, refresh token pipeline.

## Child designs (summary)

### A — Mailbox main path

**Target default path:** open 邮箱 → (standard) pick group → select account → read mail / copy code.

**Touch:**
- `templates/index.html` mailbox page chrome
- `static/js/features/accounts/*`, `emails/*`, `mailbox_compact.js`, `nav.js` topbar actions
- Contracts: `test_v190_frontend_contract`, mailbox/account type contracts if they assert chrome

**Keep:** view mode switcher (unified/standard/compact); add/export/refresh actions on standard mode.

**Change:** strip residual subtitles/help strips on standard/compact; ensure email list empty states call out refresh/get mail; avoid promoting diagnostics.

### B — Import & groups

**Touch:**
- `templates/partials/modals.html` import modal
- `static/js/features/groups/*`, account add flow
- Form hints → short default or collapsible “格式说明”

**Keep:** all import modes, duplicate strategy, pool checkbox, group proxy fields.

### C — Unified & temp email

**Touch:**
- `unifiedMailboxCommandCenter` block: collapse readiness/workflows/capability matrix behind “高级 / 服务状态”
- `static/js/features/mailboxes/render.js` (kickers, Setup Path, command workflows)
- temp email page empty/list chrome in `temp_emails/*`

**Keep:** data sources and capability matrix features; only change default visibility and copy.

### D — External API

**Touch:**
- `externalApiCommandCenter` + settings external API tab
- `static/js/core/state/external_api_ui_*.js`
- Collapse smoke/contract/playbooks; keep key + toggles visible

**Keep:** all endpoints and backend settings keys.

### E — Global shell

**Touch:**
- Sidebar labels/sections in `index.html`
- `nav.js` titles map (already mostly empty subtitles — audit all pages)
- `i18n.js` command-center strings
- Brand tagline only if still marketing-heavy (`统一邮箱工作台` may stay if product name-aligned)

**Role:** consistency pass after A–D; fix leftovers only.

## Compatibility

- Prefer **hide/collapse** over renaming critical `id`s used by JS (`unifiedMailboxCommandCenter`, `externalApiCommandCenter`) to reduce breakage.
- If contracts assert removed marketing strings, update contracts to assert **workflow invariants** (e.g. import modal present, API key field present, advanced section exists collapsed).
- Package facades / unittest patch shims: **out of scope** unless a test import path breaks (should not).

## Testing strategy

Per child:

1. Targeted frontend contract tests for touched surfaces  
2. `python -m black --check` on edited py tests  
3. After push: Code Quality + Python Tests (+ Docker if templates change)

Parent done when all five children green and smoke checklist in implement.md signed off.

## Rollout / rollback

- Ship each child as one or few commits on `main` (or short-lived branch if preferred later).
- Rollback = revert child commit(s); no DB migration.

## Risks

| Risk | Mitigation |
|------|------------|
| Contracts hard-coded to command-center copy | Grep contracts before edit; update in same commit |
| Collapsing breaks JS that assumes visible nodes | Keep nodes in DOM; CSS/details only |
| Scope creep into redesign | Thin pass only; defer deep IA to later task |
