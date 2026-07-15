# Soft-load overview on dashboard navigate when cache warm

## Problem

`initOverview()` always calls `loadOverviewTab(activeTab, true)`, so every
return to Dashboard forces `/api/overview/*` even when `__overviewState.cache`
already has a warm tab payload. Boot and first open still need a network load;
subsequent navigation should reuse cache and only hard-refresh on explicit
Refresh / `overview-data-changed`.

## Goal

1. Soft-load overview when the active tab cache is warm.
2. Keep force-reload for boot (cold cache), Refresh button, and data-changed events.
3. Preserve DOM hooks, event bindings, and existing overview contract tests.

## Acceptance Criteria

- [x] `initOverview` does not force-reload when active tab cache exists.
- [x] Cold cache / first visit still loads from network.
- [x] Refresh button and `overview-data-changed` still force-reload.
- [x] Focused frontend contract tests + `node --check` + `git diff --check` pass.
