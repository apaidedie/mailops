# Schema-driven temp-mail provider settings

## Goal

Make the Temp Mail settings workspace consume the provider catalog as its source of truth so built-in and future plugin providers can appear, describe configuration, and render editable fields without adding provider names to templates or frontend JavaScript.

## Confirmed Facts

- `provider_catalog` already exposes provider configuration metadata and diagnostics.
- `main.js` can render configuration fields from catalog metadata, but still contains hard-coded provider fallbacks, alias maps, and schema/special-panel provider sets.
- `templates/index.html` contains static provider options in more than one selector.
- Legacy bridge and Cloudflare panels have richer specialized controls that must remain compatible during migration.
- Plugin providers can expose required/optional env and settings metadata, but the settings UI contract is not explicit enough to guarantee generic rendering.

## Requirements

- Add a stable, secret-safe `settings_ui` contract to temp-provider catalog entries.
- Derive provider selector options, canonical aliases, panel mode, descriptions, and generic fields from the catalog.
- Remove built-in provider-name fallbacks and schema-provider sets from `main.js`; retain only a minimal failure state when catalog loading fails.
- Replace static template provider options with loading placeholders populated from catalog data.
- Preserve specialized legacy bridge and Cloudflare panels through catalog-declared panel modes, not frontend provider-name branches.
- Generic providers and compatible plugins must render fields from settings metadata without frontend changes.
- Preserve masked-secret semantics: unchanged masked values are not overwritten, empty secret values do not silently clear configured secrets.
- Keep current provider selection, save flow, i18n, responsive layout, and accessibility behavior.
- Add backend contract, frontend contract, settings save, plugin extensibility, and browser QA coverage.

## Acceptance Criteria

- [x] No built-in temp-provider list or schema-provider set remains in `main.js`.
- [x] Static temp-provider selectors are populated from the live catalog.
- [x] Catalog entries expose `settings_ui.panel`, localized description fields, aliases, and normalized editable field metadata.
- [x] Legacy bridge and Cloudflare specialized configuration remain reachable.
- [x] A fixture plugin with settings fields appears and renders without adding its name to frontend source.
- [x] Existing providers save and reload correctly with secret masking preserved.
- [x] Relevant backend/frontend tests, lint/type checks, browser desktop/mobile QA, readiness, and `git diff --check` pass.

## Out Of Scope

- Replacing the entire Settings page architecture.
- Adding new provider credentials or changing upstream API behavior.
- Database-managed provider schemas.
- Removing specialized panels before their controls can be represented generically.
