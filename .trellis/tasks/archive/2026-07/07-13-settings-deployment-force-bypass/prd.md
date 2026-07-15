# Force settings/deployment reload supersedes soft in-flight

## Problem

`fetchSettingsPagePayload(true)` and `loadDeploymentInfo({forceRefresh:true})`
start network GETs without superseding soft in-flight, so a late soft response
can repaint stale settings/deployment after force completes.

## Goal

1. Soft joins any in-flight; force joins only force in-flight.
2. Force supersedes soft; abandoned soft must not write cache / applyDeploymentInfo.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] settings loadForce + request identity
- [x] deployment loadForce + request identity
- [x] Focused tests green
