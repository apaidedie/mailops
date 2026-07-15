# Sync catalog loader and schema panel specs

## Goal

Update frontend/backend Trellis specs so they match the current schema-complete Settings path and the shared catalog loader/label lifecycle.

## Confirmed Facts

- `legacy_bridge` and `cloudflare_temp_mail` render through generic schema panel (`settings_ui.panel=schema`); dedicated mounts are empty compatibility nodes.
- Shared helpers: `loadMailboxProviderCatalog`, `resolveMailboxProviderLabel`, boot preload, plugin lifecycle catalog refresh.
- Pool-admin and import-account selectors prefer shared catalog cache/loader before direct `/api/providers` fetch.

## Requirements

- Correct outdated “dedicated panel” language for bridge/CF.
- Document shared catalog loader ownership and consumer preference order.
- Keep plugin config panel dual-path documented (still PluginManager until fully unified).

## Acceptance Criteria

- [x] Frontend quality guidelines no longer require dedicated bridge/CF workflow panels for field editing.
- [x] Shared catalog loader/label/lifecycle contracts are documented with tests pointers.
- [x] Spec-only change; no product code required.

## Out Of Scope

- Implementing plugin config full merge into schema panel UI.
