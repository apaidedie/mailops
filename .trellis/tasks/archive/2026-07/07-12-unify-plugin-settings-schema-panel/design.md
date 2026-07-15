# Design

## Routing truth table

| State | Route |
|-------|-------|
| Catalog item, `config_source=plugin`, `panel=schema`, fields length > 0 | Schema panel |
| Catalog item, `config_source=plugin`, no fields | PluginManager (or empty schema "无需配置") — prefer schema empty if panel=schema |
| Catalog item, builtin schema | Schema panel |
| Catalog missing, builtin fallback | Schema panel |
| Catalog missing, PluginManager installed / unknown with PluginManager | PluginManager |

## Save path

- Schema fields use `data-temp-provider-setting="plugin.name.key"`.
- `collectTempProviderSchemaSettings` only emits dirty keys.
- Backend already ignores empty secrets for plugin keys.

## Test connection

- For plugin config_source, render a secondary action button in schema panel that POSTs `/api/plugins/<name>/test-connection` without requiring PluginManager panel open.
- Keep PluginManager test-connection for fallback path.

## Risk

- Do not default unknown pre-catalog names into empty schema.
- Secret inputs must stay blank + `*_set`/`*_masked` from settings snapshot.
