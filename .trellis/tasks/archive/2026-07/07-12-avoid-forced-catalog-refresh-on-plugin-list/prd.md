# Avoid forced catalog refresh on every plugin list load

## Goal

Stop PluginManager boot/list refresh from always forcing `/api/providers`, which duplicates the boot soft preload on every page load.

## Evidence

- Boot path already calls non-blocking `loadMailboxProviderCatalog(false)`.
- `PluginManager.init → loadPlugins → _refreshMailboxProviderCatalogFromPlugins` always awaits `loadMailboxProviderCatalog(true)`.
- Result: every page load issues a second full providers fetch even when plugin registry did not change.

## Requirements

- Soft-load catalog on ordinary plugin list load (reuse warm cache when present).
- Force-refresh only after install / uninstall / applyChanges (registry may have changed).
- Keep inject-after-catalog order.
- Contract tests assert soft vs force call sites.

## Acceptance Criteria

- [x] Default plugin list load uses soft catalog refresh.
- [x] Lifecycle mutations force catalog refresh.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Broader performance rewrites without measurement.
- Backend catalog dual-bridge removal.
