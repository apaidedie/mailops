# Force groups/tags/preflight supersede soft in-flight

## Problem

`loadGroups(true)`, `loadTags(true)`, and `loadProviderPreflightSnapshot(true)`
start network GETs without superseding soft in-flight, so late soft responses
can repaint stale groups/tags/preflight after mutations.

## Goal

1. Soft joins any in-flight; force joins only force in-flight.
2. Force supersedes soft; abandoned soft must not write state.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] groups loadForce + identity
- [x] tags loadForce + identity
- [x] preflight loadForce + identity
- [x] Focused tests green
