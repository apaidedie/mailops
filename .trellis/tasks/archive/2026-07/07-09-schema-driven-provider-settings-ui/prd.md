# Schema Driven Provider Settings UI

## Goal

Move the Settings -> Temp Mail provider configuration for ordinary built-in temp-mail providers toward the provider catalog `configuration.config_schema` contract, so future providers need catalog/schema metadata instead of new provider-specific template panels and JavaScript branches.

## User Value

Operators can configure Mail.tm-compatible DuckMail, TempMail.lol, Emailnator, and future provider-like sources from one consistent panel. This lowers the cost of adding new providers while preserving existing settings keys and secret-preservation behavior.

## Confirmed Facts

- The app is a Flask-rendered static frontend: `templates/index.html`, `static/js/main.js`, `static/css/main.css`, and Python frontend contract tests are the relevant frontend surface.
- `/api/providers` already exposes temp provider configuration contracts with `configuration.settings_keys`, `configuration.required_settings`, `configuration.secret_settings`, `configuration.settings_defaults`, and `configuration.config_schema.fields`.
- `static/js/main.js` already has a schema-driven `#tempMailProviderConfigPanel`, field renderer, and `collectTempProviderSchemaSettings()` helper.
- `legacy_bridge` and `cloudflare_temp_mail` still require dedicated panels because they include legacy bridge fields and CF Worker domain sync/read-only behavior.
- DuckMail and Emailnator still have dedicated template panels and legacy load/save references, even though the catalog already describes their fields.

## Requirements

- Keep `legacy_bridge` and `cloudflare_temp_mail` as special panels for this slice.
- Render ordinary built-in temp providers through `#tempMailProviderConfigPanel` using catalog/schema metadata, including DuckMail, TempMail.lol, Emailnator, and Mail.tm.
- Keep plugin-backed providers on `PluginManager.showProviderConfig(provider)` until plugin settings are persisted through the same `/api/settings` path as built-ins.
- Remove visible dependency on DuckMail and Emailnator template-specific panels and field IDs.
- Preserve existing settings payload keys such as `duckmail_api_base`, `duckmail_bearer_token`, `tempmail_lol_api_key`, `emailnator_api_key`, and `emailnator_email_types`.
- Preserve secret behavior: masked secret values must display only as masked status, blank secret inputs must not clear stored secrets, and public helper/readiness UI must not read settings credential inputs.
- Preserve environment-backed defaults, especially DuckMail API Base, so unchanged defaults are not unnecessarily persisted.
- Keep implementation provider-agnostic where practical; do not add new provider-specific router branches for ordinary built-in providers.

## Acceptance Criteria

- [x] Settings -> Temp Mail exposes one catalog/schema-driven configuration panel for ordinary built-in non-special providers.
- [x] DuckMail and Emailnator no longer require dedicated template panels or provider-specific router branches.
- [x] Save/load paths hydrate and collect schema-rendered fields generically, including masked secret state and JSON fields.
- [x] DuckMail API Base remains unsaved when the user did not change the loaded/default value.
- [x] Focused frontend contract tests pass.
- [x] Relevant settings/provider tests pass or project readiness check passes.
- [x] No public helper/readiness slices read secret input IDs or render secret values.

## Out Of Scope

- Replacing the legacy bridge panel.
- Replacing the Cloudflare Worker panel or its domain-sync workflow.
- Moving plugin provider configuration from `/api/plugins/<name>/config` to `/api/settings`.
- Changing backend provider APIs or third-party provider protocol behavior.
- Adding a new frontend framework or package.
