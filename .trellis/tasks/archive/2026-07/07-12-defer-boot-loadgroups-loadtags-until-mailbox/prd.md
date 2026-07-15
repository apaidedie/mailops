# PRD: Defer boot loadGroups/loadTags until mailbox

## Problem

On `DOMContentLoaded`, `main.js` always calls `loadGroups()` and `loadTags()`.
Dashboard-first sessions (default landing) do not need mailbox groups/tags on
first paint. Those requests compete with overview + catalog on the shared sync
worker and inflate boot network budget.

Measured residual after soft-load overview (session journal residual #2).

## Goal

- Do not call `loadGroups()` / `loadTags()` during boot `DOMContentLoaded`.
- Load them when the user actually needs mailbox/group/tag UI:
  - `navigate('mailbox')` already loads groups when empty
  - Tag management modal already calls `loadTags()`
  - Other call sites that already fetch on demand stay unchanged
- Preserve DOM hooks, CSP, and no CF/bridge API changes.

## Acceptance criteria

- [x] Boot `DOMContentLoaded` init slice does not contain eager `loadGroups()` / `loadTags()`.
- [x] Mailbox navigation still loads groups when `groups.length === 0`.
- [x] Tag management modal still loads tags on open.
- [x] Contract tests cover the boot deferral.
- [x] Related frontend contract / smoke tests pass.

## Non-goals

- Backend dual-register inventory collapse (separate residual).
- Visual UI redesign (no screenshot path required for this perf change).
