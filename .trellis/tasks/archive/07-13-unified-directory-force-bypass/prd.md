# Force loadUnifiedMailboxes directory supersede soft in-flight

## Problem
While soft directory load is in-flight, force only queues pendingForceRefresh and waits for soft to finish (and potentially write cache) before starting a true GET.

## Goal
Soft joins same-signature in-flight; force joins only force; force supersedes soft via directoryLoadSeq.

## Acceptance
- [ ] directoryLoadForce / directoryLoadSeq
- [ ] contract tests green
