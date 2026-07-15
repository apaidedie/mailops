# Gate Settings provider surfaces until settings open

## Problem

Boot soft-loads `/api/providers` and re-renders Settings-only surfaces
(workbench, diagnostics, integration guide, contract status, external API
command center, pool default datalist, active-provider chips) even when the
Settings modal is closed.

## Goal

1. Catalog success/error and language-change must not rewrite Settings-only
   provider surfaces while Settings is closed.
2. When Settings is open, catalog/language refresh still updates those surfaces.
3. Non-Settings consumers (temp-email select, account tags, pool-admin, import,
   unified labels) keep refreshing on catalog load.

## Acceptance Criteria

- [x] Catalog load does not call Settings-only renderers when `#settingsModal` is not shown
- [x] Catalog load still updates non-Settings consumers
- [x] Settings open path still hydrates via `loadSettings` / open-time refresh
- [x] Focused tests + `node --check` + `git diff --check` pass
