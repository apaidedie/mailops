# UI Workflow Polish A–E (Scheme B continuation)

**Date:** 2026-07-18  
**Status:** Approved approach; awaiting implementation plans per child  
**Extends:** `docs/superpowers/specs/2026-07-17-ui-simplify-workflow-b-design.md`  
**Trellis:** `.trellis/tasks/07-18-ui-workflow-polish-ae/` (+ children A–E)

## Goal

Continue scheme B with a **thin, sequential polish** of the MailOps admin UI so daily ops stay workflow-first: import/group/browse → read mail/codes → optional external API. No marketing/command-center chrome on default views.

## Approach (approved)

**Option 1 — sequential thin pass A→E** (not deep redesign, not shell-first).

Shared rules on every surface:

1. Remove default marketing kickers / command-center hero copy  
2. Default UI shows only the primary ops actions  
3. Advanced filters / diagnostics / contracts / capability matrices stay **collapsed**, not deleted  
4. Empty states offer one next action  
5. Frontend contract tests update in the same change set; keep `main` CI green  

## Delivery order

| # | Child task | Focus |
|---|------------|--------|
| A | `07-18-ui-polish-a-mailbox` | Mailbox standard/compact: group → account → mail/code |
| B | `07-18-ui-polish-b-import-groups` | Import modal + group empty states |
| C | `07-18-ui-polish-c-unified-temp` | Unified mailbox + temp email; collapse service chrome |
| D | `07-18-ui-polish-d-external-api` | API key + core toggles; collapse smoke/contract/playbooks |
| E | `07-18-ui-polish-e-shell` | Nav / topbar / i18n consistency pass |

Implement and ship **one child at a time**. Parent owns cross-child acceptance only.

## Product priorities (unchanged)

1. Import / group / browse accounts  
2. Read mail / extract verification codes  
3. Optional: configure external API key  

## Surfaces (default vs advanced)

| Surface | Default | Advanced (collapsed) |
|---------|---------|----------------------|
| A Mailbox (standard/compact) | Group + account list + mail/code | Diagnostics, residual essays |
| B Import / groups | Import action + group management | Long format essays, advanced group fields emphasis |
| C Unified / temp | Search + list + preview | Command center, Setup Path, capability matrix |
| D External API | API key + core toggles | Smoke, contract tools, workflow playbooks |
| E Shell | Quiet nav + topbar titles | Marketing taglines / leftover kickers |

## Technical boundaries

- **In scope:** `templates/`, `static/js/`, `static/css/`, `static/js/i18n.js`, frontend contract tests, CSS cache-bust query when CSS changes  
- **Out of scope:** backend API contracts, removing refresh log / pool / external API features, design-system rewrite, SonarCloud  
- **Compatibility:** prefer hide/collapse over deleting critical element `id`s used by JS  
- **Rollout:** one child commit series on `main`; revert unit = child commit set  

## Acceptance (parent)

- [ ] Children A–E each meet their PRD acceptance  
- [ ] Default admin UI has no command-center marketing shell on primary ops pages  
- [ ] Import / read mail / API key reachable in ≤3 steps from primary nav  
- [ ] Advanced panels remain expandable  
- [ ] `main`: Code Quality + Python Tests + Docker Build/Push green  

## Non-goals

- No backend API contract changes  
- No removal of refresh log or pool features  
- No restoration of OAuth Token tool  

## Implementation note

Detailed execution checklists live in Trellis:

- Parent: `.trellis/tasks/07-18-ui-workflow-polish-ae/implement.md`  
- Per-child requirements: each child `prd.md`  
