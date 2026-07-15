# Force detail loaders and external contract supersede soft in-flight

## Problem

Detail soft-load promises and external API contract-check join soft on force
paths, so force re-open/refresh can paint stale detail or contract reports.

## Goal

1. Soft joins any; force joins only force; force supersedes soft.
2. Abandoned soft must not write detail/contract caches.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] account/group/email/temp detail loadForce
- [x] externalApiContractCheck loadForce
- [x] Focused tests green
