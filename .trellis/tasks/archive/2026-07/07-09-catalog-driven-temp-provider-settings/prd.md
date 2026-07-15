# Catalog driven temp provider settings

## Goal

Render Settings -> Temp Mail provider choices from the existing provider catalog so future temp-mail providers can appear in the operator UI without editing `templates/index.html` for every new provider.

This advances the larger product goal by reducing a visible extensibility bottleneck: backend provider discovery, plugin validation, and external API contracts are already catalog-driven, but the Settings temp-mail selector still hardcodes built-in provider cards.

## Confirmed Facts

- The app uses Flask templates plus vanilla JavaScript/CSS; no frontend framework should be added.
- `/api/providers` already returns `mailbox_providers`, provider diagnostics, deployment profile, integration guide, integration manifest, quickstart, and documentation.
- `static/js/main.js` already caches the provider catalog through `loadMailboxProviderCatalog()` and renders provider readiness/status badges from catalog rows.
- `templates/index.html` currently hardcodes six temp provider radio cards: `legacy_bridge`, `cloudflare_temp_mail`, `mail_tm`, `duckmail`, `tempmail_lol`, and `emailnator`.
- Built-in provider-specific configuration panels still exist and must remain usable for this slice.
- Existing plugin UI uses `#pluginProviderConfigPanel` plus `PluginManager.showProviderConfig(provider)` for plugin providers.
- Existing frontend specs require provider-aware UI to be secret-safe and avoid provider-specific branching where catalog data can own behavior.

## Requirements

- Replace the hardcoded Settings temp-mail provider option markup with a stable dynamic mount that can render temp providers from `/api/providers` catalog data.
- Preserve current provider selection behavior and saved setting field: `collectTempMailSettingsPayload()` must continue writing `settings.temp_mail_provider` from the checked `input[name="tempMailProvider"]`.
- Render a safe fallback set of built-in temp provider choices before `/api/providers` loads or when the catalog fails, so Settings remains usable offline/local-first.
- Preserve current specialized configuration panels:
  - `legacy_bridge` shows the compatible bridge panel.
  - `cloudflare_temp_mail` shows the CF Worker panel.
  - `duckmail` shows the DuckMail panel.
  - `emailnator` shows the Emailnator panel.
  - providers without a dedicated panel use the generic plugin provider panel/manager path.
- Do not read or render real provider secrets, API keys, bearer tokens, external API keys, task tokens, JWTs, refresh tokens, passwords, or consumer keys in the selector renderer.
- Keep the selector provider-agnostic for option generation: labels, descriptions, status, missing config, and provider keys should come from catalog rows or a small non-secret fallback label map used only before catalog data is available.
- Keep existing provider status badges and pending provider restoration working when Settings loads before the provider catalog has returned.
- Update tests so this extensibility path is enforced and future providers are not silently excluded from the Settings selector.
- Maintain responsive, polished UI with no obvious desktop/mobile horizontal overflow for the changed Settings temp-mail area.

## Acceptance Criteria

- [ ] `templates/index.html` exposes a stable mount for catalog-rendered temp provider choices instead of hardcoding one label block per provider option.
- [ ] `static/js/main.js` contains helper logic to normalize temp provider catalog rows, render radio choices, preserve the selected/pending provider, and fall back safely when `/api/providers` is unavailable.
- [ ] Provider option generation is secret-safe and does not read provider credential inputs or render credential values.
- [ ] A catalog row for an unknown future temp provider can render as a selectable radio choice without adding new template markup.
- [ ] Dedicated panel routing for current built-in providers still works; plugin/future providers use the existing generic plugin configuration path.
- [ ] Existing Settings save/load behavior continues to use `input[name="tempMailProvider"]` and `temp_mail_provider`.
- [ ] Frontend contract tests cover the dynamic mount, helper names, fallback behavior, future-provider rendering path, secret safety, and preservation of dedicated panel routing.
- [ ] Focused Settings/frontend tests and JS syntax checks pass.
- [ ] If visual layout changes are material, desktop/mobile rendered checks confirm Settings -> Temp Mail has no obvious horizontal overflow.

## Notes

- Out of scope: replacing built-in provider-specific config panels with a fully schema-driven settings form. That is a larger step and should happen only after backend provider metadata exposes enough form schema safely.
- Out of scope: changing `/api/providers`, provider aliases, provider selection policy, or external API behavior.
