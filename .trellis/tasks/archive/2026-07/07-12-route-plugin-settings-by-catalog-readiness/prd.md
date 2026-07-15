# Route plugin settings by catalog readiness

## Goal

Prevent installed plugin providers from being misrouted to the empty generic schema panel before `/api/providers` catalog is ready, and keep `config_source === 'plugin'` on the PluginManager interactive config path until full schema-panel unification.

## Problem / user value (evidence)

- Backend already projects plugin fields as `settings_ui.panel=schema` with `plugin.<name>.*` keys that round-trip via `/api/settings`.
- Frontend `providerUsesTempSettingsSchemaPanel()` currently returns true whenever catalog item is missing (default `panel || 'schema'`), so an installed plugin selected during startup/plugin inject can open the empty schema panel instead of PluginManager.
- Spec already requires: built-in fallback classification before catalog loads; plugin `config_source` continues through PluginManager for interactive config.

## Requirements

- If catalog item has `config_source === 'plugin'`, do not use the generic schema panel for interactive config.
- If catalog item is missing, use a built-in temp-provider fallback list for schema routing; treat PluginManager-installed providers as plugin path.
- Keep PluginManager show/hide wiring in `onTempMailProviderChange`.
- Contract tests assert the routing rules.

## Acceptance Criteria

- [x] Installed plugin provider is not classified as schema panel while catalog is empty.
- [x] Catalog plugin rows (`config_source=plugin`) route to PluginManager path.
- [x] Known built-ins still route to schema panel before/after catalog load.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Full merge of plugin save UI into schema panel + test-connection parity.
- Changing `/api/plugins/*/config` backend.
- Removing `#pluginProviderConfigPanel` mount.

## Compatibility / rollback

- No data migration. Rollback is code revert; plugin configs remain in settings keys and plugin API.
