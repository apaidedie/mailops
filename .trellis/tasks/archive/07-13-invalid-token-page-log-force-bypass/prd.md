# Force invalid-token and page-log loaders supersede soft in-flight

## Problem

`loadInvalidTokenGovernanceCandidates` force paths do not supersede soft
in-flight. Audit/refresh page log loaders lack coalesce + force identity.

## Goal

1. invalid-token: soft joins any; force joins only force; force supersedes soft.
2. audit/refresh page logs: add coalesce + force supersede soft.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [ ] invalidTokenGovernanceLoadForce
- [ ] auditLogPage / refreshLogPage loadForce + promises
- [ ] Focused tests green
