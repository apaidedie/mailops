# Gate catalog refresh workbench paint to api-security tab

## Problem

`refreshSettingsProviderSurfaces()` runs on catalog success while Settings is open
and always paints api-security-only panels (workbench, command center, diagnostics,
guide, contract, pool datalist, active chips) even when the user is on Basic or
Temp Mail.

## Goal

1. Keep temp-mail radio/badge/rehydrate updates when Settings is active.
2. Paint api-security-only panels only when `currentSettingsTab === 'api-security'`.
3. Preserve switch-to-api-security snapshot paint + soft-load paths.

## Acceptance Criteria

- [x] refreshSettingsProviderSurfaces gates workbench/command-center to api-security
- [x] temp-mail radio rehydrate still runs when Settings is active
- [x] Focused tests + node --check + git diff --check pass
