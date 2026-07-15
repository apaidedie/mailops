# Coalesce concurrent loadSettings fetches

## Problem

Rapid double-entry into Settings (or modal + navigate race) can start two
GET `/api/settings` before either finishes, even with soft-load cache after
the first success.

## Goal

1. Share one in-flight network promise for concurrent soft loadSettings.
2. forceRefresh still bypasses cache and starts a fresh fetch.
3. Soft cache still short-circuits when warm.
4. Contract tests green.

## Acceptance Criteria

- [x] settingsLoadPromise coalesces concurrent soft fetches
- [x] forceRefresh does not reuse soft in-flight if inappropriate (or still safe)
- [x] Focused tests + node --check pass
