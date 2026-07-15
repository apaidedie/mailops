# Catalog driven temp provider settings design

## UI Brief

- Audience: operators configuring a unified mailbox service with built-in or future temp-mail providers.
- Workflow: open Settings -> Temp Mail, pick the runtime temp provider, see readiness/config state, then fill the relevant provider configuration panel if needed.
- Product archetype: operational SaaS/data product; dense, calm, predictable.
- Stack: Flask template mount point, vanilla JS renderer, existing CSS classes; no new libraries.
- Source of truth: `/api/providers` provider catalog and existing Settings data.

## Boundaries

- This task changes the Settings temp-mail provider selector only.
- It does not change backend provider discovery, provider aliases, provider selection policy, temp-mail service behavior, or external API contracts.
- It keeps existing dedicated provider config panels and the plugin provider config panel.
- It does not introduce schema-driven provider forms yet.

## Rendering Model

1. Replace hardcoded provider radio labels in `templates/index.html` with a stable `#tempMailProviderOptions` mount inside the existing `.provider-radio-group`.
2. Add a small fallback provider list in `static/js/main.js` for pre-catalog and catalog-failure states. The fallback contains only non-secret display metadata and preserves currently supported built-ins.
3. Add helpers that derive temp provider option rows from `mailboxProviderCatalogCache`:
   - filter `kind === "temp"`.
   - normalize provider key, label, description, active/configured/missing config/readiness fields.
   - merge current/pending provider if it is absent from the catalog so the saved value does not disappear.
   - sort built-in/fallback order first, then catalog-only future providers by label/key.
4. Render radio inputs named `tempMailProvider` so existing save logic keeps working.
5. Re-render options after `loadMailboxProviderCatalog()` succeeds or fails, after Settings loads a pending provider, and after provider changes.

## Panel Routing Model

Provider option generation should be catalog-driven, but panel routing can remain explicit while specialized panels are hardcoded:

- `legacy_bridge` -> compatible bridge panel.
- `cloudflare_temp_mail` -> CF Worker panel.
- `duckmail` -> DuckMail panel.
- `emailnator` -> Emailnator panel.
- all other providers -> generic plugin/future-provider panel, delegating to `PluginManager.showProviderConfig(provider)` when available.

This keeps current UX intact while moving the extensibility bottleneck away from the option list.

## Secret Safety

The option renderer may show provider key names, labels, readiness status, and missing config key names from catalog metadata. It must not read credential inputs or display credential values. Missing config values such as `DUCKMAIL_BEARER_TOKEN` are key names only.

## Compatibility

- Existing tests that assert built-in provider options exist should still pass, but they should assert rendered helper/fallback coverage rather than static markup per provider.
- Existing `collectTempMailSettingsPayload()` keeps using the checked radio.
- Existing `onTempMailProviderChange(provider)` remains the routing entrypoint.
- If `/api/providers` is unavailable, Settings remains usable through the fallback list.

## Validation

- Frontend contract tests for mount/helper names/fallback/future provider rendering/secret safety.
- Settings frontend contract tests for existing built-in panel mounts and save collector reuse.
- JS syntax checks for `static/js/main.js` and `static/js/i18n.js` if i18n changes.
- Browser check on Settings -> Temp Mail if layout changes beyond the option renderer.
