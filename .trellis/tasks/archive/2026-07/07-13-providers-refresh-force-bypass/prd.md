# Force providers and refresh-log loaders supersede soft in-flight

## Problem

`loadProviders`, refresh stats/logs/failed-logs, version-check, and operational
readiness force paths join soft in-flight and can paint stale data after refresh.

## Goal

1. Soft joins any; force joins only force; force supersedes soft.
2. Abandoned soft must not write caches.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadProviders loadForce
- [x] refresh stats/logs/failed loadForce
- [x] version-check + operational readiness loadForce
- [x] Focused tests green
