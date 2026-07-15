# Implement: invalid-token + page-log force supersede soft

## Changes
1. `loadInvalidTokenGovernanceCandidates` — `invalidTokenGovernanceLoadForce`; soft joins any; force joins only force; force supersedes soft; request identity guards.
2. `loadRefreshLogPage` / `loadAuditLogPage` — add `*LoadPromise` + `*LoadForce`; same soft/force semantics; invalidate clears promise/force.
3. Contract tests in `tests/test_overview_frontend_contract.py`.
4. Spec: `.trellis/spec/frontend/quality-guidelines.md`.

## Validation
- `node --check static/js/main.js`
- `python -m unittest tests.test_overview_frontend_contract -v` (focused methods)
- `git diff --check`
