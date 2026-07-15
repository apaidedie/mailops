# Do not set pending temp provider when radios unbound

## Problem

`applyTempMailSettingsSelection()` always writes a canonicalized `pendingProvider`
even when the temp-mail mount is unbound (user opened Basic Settings only).
That pending value can still influence selection helpers and is easy to misuse
in future collect/rehydrate paths.

## Goal

1. When unbound, do not write `dataset.pendingProvider`.
2. When bound, keep pending/paint behavior.
3. loadSettings on non-temp-mail tabs should not leave a stale pending value.

## Acceptance Criteria

- [x] applyTempMailSettingsSelection does not set pending when unbound
- [x] Bound path still paints radios and clears pending after check
- [x] Focused tests + node --check + git diff --check pass
