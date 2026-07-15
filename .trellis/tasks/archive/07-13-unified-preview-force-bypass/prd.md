# Force unified mailbox preview loaders supersede soft in-flight

## Problem
Unified messages/detail/verification soft-load coalesces all in-flight loads; force paths do not supersede soft in-flight for the same signature.

## Goal
1. messages/detail/verification: soft joins any same-signature in-flight; force joins only force; force supersedes soft.
2. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria
- [ ] messagesLoadForce / detailLoadForce / verificationLoadForce
- [ ] request identity guards on apply
- [ ] Focused tests green
