# Schema Driven Provider Settings Design

## Boundaries

This slice touches the Settings Temp Mail configuration UI and the metadata projection needed to render it. It should not change provider runtime behavior or external API discovery semantics.

Primary files:

- `outlook_web/services/provider_catalog.py`
- `outlook_web/controllers/settings.py`
- `templates/index.html`
- `static/js/main.js`
- `static/js/features/plugins.js` only if reuse or compatibility requires a small shared behavior adjustment
- `static/css/main.css`
- Settings and provider contract tests under `tests/`

## Source Of Truth

Provider configuration metadata should flow from the backend provider catalog and the safe settings payload:

```text
provider_catalog configuration metadata
  -> /api/providers and/or authenticated settings data
  -> Settings Temp Mail provider option state
  -> generic built-in provider config renderer
  -> collect/save settings payload
```

The frontend may normalize metadata for display, but it must not own provider readiness rules, alias rules, or secret policy.

## UI Brief

- Audience: operators/admins configuring mailbox providers for automation and external integrations.
- Primary workflow: choose a temp-mail provider, understand whether it needs configuration, enter or preserve settings, and save/test without reading docs first.
- Product archetype: operational SaaS/data product.
- Constraints: Flask templates, vanilla JS, existing CSS tokens and cards, no new UI dependencies, dense Settings page, desktop and mobile support.
- States: loading/catalog unavailable, no configurable fields, configured, needs config, secret preserved, validation/error, hover/focus, mobile wrapping.
- Acceptance: contract tests plus rendered desktop/mobile Settings checks with overflow inspection.

## Data Contract

Generic built-in fields can be projected from catalog configuration:

- `settings_keys`: candidate settings persisted through `/api/settings`.
- `required_settings`: keys that should be marked required in the UI.
- `secret_settings`: keys that render as blank password inputs and are preserved when blank.
- `settings_defaults`: non-secret defaults for placeholders or hints.
- `required_env`, `optional_env`, `secret_env`, and `env_defaults`: key names and deployment hints only; never values for secrets.

If backend catalog entries already include a sanitized `config_schema`, use it as the preferred field list. Otherwise, build a frontend field projection from `settings_keys` and known safe display metadata such as labels, defaults, and required/secret flags.

## Rendering Strategy

Add one generic mount inside Settings -> Temp Mail:

```text
#tempMailProviderConfigPanel
  .temp-provider-config-summary
  .temp-provider-config-fields
  .temp-provider-config-hints
```

Provider routing should prefer generic rendering for built-in providers with catalog configuration metadata. Dedicated panels may remain temporarily for workflows that have extra behavior, notably Cloudflare Worker domain sync and plugin-provider schema rendering.

The panel should render compact rows instead of nested cards, using existing Settings card styling and stable responsive grid constraints. Long key names and URLs must wrap.

## Save Semantics

Collection should be metadata-driven:

1. Find the active provider.
2. Resolve its projected configurable fields.
3. For each non-secret field, include the current input value when present or when clearing is intentional.
4. For each secret field, include only a non-empty new input value. Blank means preserve existing setting.
5. Merge with existing explicit collectors for special panels until those panels are migrated.

Masked placeholders, hint text, and preserved markers must never be sent as settings values.

## Compatibility

- Existing input IDs may remain for backward-compatible tests and special flows during migration, but new generic collection should not depend on provider-name branches for newly catalog-driven providers.
- Plugin-provider config continues through `pluginManager.showProviderConfig()` unless it becomes practical to share a renderer later.
- Cloudflare Worker temp mail keeps its domain loading/sync controls in this slice.
- Legacy bridge can remain dedicated if its fields map poorly to catalog metadata, but provider-specific branch count should not grow.

## Secret Safety

Secret values must not be read by display-only workbench/render helpers. Secret inputs may be read only by save collectors. The renderer may show secret key names and a preserved/masked state, but saved secret values must not be placed in `value`, `data-*`, text content, copied snippets, or logs.

## Rollback

Rollback is local to the Settings UI: remove the generic mount, field projection helpers, and tests, then restore the previous provider-specific routing behavior. Backend provider catalog changes should be additive and can remain if they only expose sanitized metadata.
