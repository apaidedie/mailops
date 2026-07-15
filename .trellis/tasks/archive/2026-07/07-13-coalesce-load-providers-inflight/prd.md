# Coalesce concurrent loadProviders fetches

## Problem

`loadProviders` soft-returns when `providersLoaded` but concurrent cold opens
(import modal + catalog race) can still start multiple shared-catalog/network
paths before the first finishes.

## Goal

1. Share one in-flight promise for concurrent soft/force loads.
2. Warm soft path unchanged.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] providersLoadPromise coalesces concurrent loads
- [x] Warm providersLoaded short-circuit first
- [x] Focused tests green
