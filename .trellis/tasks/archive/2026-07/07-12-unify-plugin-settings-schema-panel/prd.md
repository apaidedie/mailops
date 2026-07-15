# Unify plugin settings into schema panel when catalog ready

## Goal

When `/api/providers` catalog is ready, render plugin temp-provider settings through the same generic schema panel used by built-ins, saving via `/api/settings` (`plugin.<name>.*` keys). Keep PluginManager path only as warmup/fallback when catalog is unavailable or fields are missing.

## Problem / user value (evidence)

- Backend already round-trips `plugin.*` keys through `/api/settings` with secret mask/empty-ignore.
- Catalog already projects plugin rows as `settings_ui.panel=schema` with `configuration.settings_keys` and `config_schema.fields`.
- Frontend schema field resolver already maps field keys to `plugin.<name>.field` via `settings_keys` suffix match.
- Current routing forces all `config_source=plugin` into PluginManager, duplicating UI and blocking the unified Settings save path operators already use for built-ins.

## Requirements

- Catalog-ready plugin with schema fields → schema panel (`providerUsesTempSettingsSchemaPanel` true).
- Catalog missing / no fields → keep PluginManager fallback (preserve prior warmup safety).
- Schema save continues through dirty-key + secret blank ignore (existing collectors).
- Optional: expose plugin test-connection from schema panel without leaving Settings autosave flow.
- Contract tests assert catalog-ready plugin uses schema path; warmup still protects empty catalog.

## Acceptance Criteria

- [x] Catalog-ready plugin (`config_source=plugin`, panel=schema, fields present) uses schema panel.
- [x] Catalog-missing installed plugin still routes to PluginManager.
- [x] Built-in schema routing unchanged.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Removing PluginManager install/uninstall/lifecycle UI.
- Changing plugin backend config API shape.
- Redesigning Settings visual layout (no screenshot skill needed for routing-only).

## Compatibility / rollback

- No DB migration. Rollback = code revert; both PluginManager and `/api/settings` write the same `plugin.*` keys.
