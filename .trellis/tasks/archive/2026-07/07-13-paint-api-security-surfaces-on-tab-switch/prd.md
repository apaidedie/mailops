# Paint full api-security surfaces when switching to that tab

## Problem

After gating catalog refresh workbench paint to api-security, `switchSettingsTab('api-security')`
only snapshot-renders workbench + command center. Pool chips, diagnostics, guide, contract,
and config templates stay on their initial empty/loading markup until a later catalog force
refresh happens while already on that tab.

## Goal

1. When switching to api-security, paint the full api-security surface set from caches/snapshot.
2. Keep soft-load of preflight/contract/readiness after snapshot paint.
3. Keep Basic/Temp Mail free of that expensive paint.

## Acceptance Criteria

- [x] switchSettingsTab api-security paints pool chips, diagnostics, guide, contract, templates, workbench, command center
- [x] network soft-loads still follow snapshot paint
- [x] Focused tests + node --check + git diff --check pass
