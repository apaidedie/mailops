# Design

## Boundaries

- Frontend template owns only stable mount points and special panels.
- Provider catalog remains the source of truth for ordinary temp provider fields.
- Settings API payload keys remain unchanged for backward compatibility.

## Data Flow

1. `loadSettings()` fetches `/api/settings` and stores `tempMailSettingsSnapshot`.
2. `loadMailboxProviderCatalog()` fetches `/api/providers` and stores provider catalog/diagnostics caches.
3. `onTempMailProviderChange()` decides whether to show a special panel or schema panel.
4. `renderTempMailProviderConfigPanel(provider)` reads `configuration.config_schema.fields` and renders inputs with `data-temp-provider-*` attributes.
5. `collectTempProviderSchemaSettings(settings)` reads visible schema inputs and writes changed values to the existing settings payload keys.
6. Plugin-backed providers bypass the Settings schema panel and save through the plugin manager because their config endpoint is `/api/plugins/<name>/config`, not `/api/settings`.

## Compatibility

- Special providers remain unchanged: `legacy_bridge` -> `#gptmailConfigPanel`, `cloudflare_temp_mail` -> `#cfWorkerConfigPanel`.
- Plugin providers remain unchanged: `config_source === 'plugin'` -> `PluginManager.showProviderConfig(provider)`.
- Ordinary built-ins use catalog fields:
  - DuckMail: `duckmail_api_base`, `duckmail_bearer_token`.
  - TempMail.lol: `tempmail_lol_api_key`.
  - Emailnator: `emailnator_api_key`, `emailnator_email_types`.
- Existing backend masking contracts remain unchanged: `<key>_set` and `<key>_masked` values hydrate secret field status.
- If provider catalog is unavailable, fallback providers still render; providers without field schema show a no-local-config state.

## Secret Safety

- Secret schema inputs render empty values and use masked status text from the settings snapshot.
- Saving a blank secret input sends no secret key, preserving stored secrets.
- Saving a nonblank secret input sends only that field's setting key.
- Public workbench, quickstart, readiness, and integration-copy helpers remain separate from settings input collection.

## UI Direction

Audience: operators configuring mailbox providers under time pressure.

Primary workflow: choose a temp-mail provider, see its config readiness, edit only the provider-specific fields that matter, save.

Product archetype: dense operational SaaS. Use the existing card/form style, compact metadata, wrapping hints, and no new visual system.

States: catalog loading, catalog unavailable, configured, needs configuration, no local config, masked secret set/unset, JSON validation error.

## Tradeoffs

- The generic schema collector still accepts provider settings keys from the backend catalog. That keeps new providers extensible but means backend validation remains the final trust boundary.
- The schema normalizer still understands catalog field-to-setting mappings, but plugin providers do not enter the generic panel until their save path is unified with `/api/settings`.
