# Refresh catalog after plugin lifecycle

## Goal

After plugin list load / install / uninstall / apply-changes, force-refresh the secret-free provider catalog so Settings radios and temp-email selectors pick up installed plugins from `/api/providers` instead of relying only on dual-path DOM injection.

## Confirmed Facts

- Catalog already includes loaded plugin providers via `get_available_providers()`.
- Plugin manager still injects radios/options via `_refreshProviderRadios` / `_refreshProviderSelect`.
- Catalog render prefers catalog options and only keeps plugin-injected options when missing from catalog.
- Install without “应用变更” may leave plugins on disk but not loaded into the runtime registry.

## Requirements

- After successful plugin list refresh, force-refresh mailbox provider catalog when the helper exists.
- After apply-changes (reload-plugins), force-refresh catalog so newly loaded plugins appear in catalog-driven UI.
- Keep existing plugin radio/select injection as fallback for not-yet-loaded plugins.
- Contract tests assert the refresh call sites.

## Acceptance Criteria

- [x] Plugin lifecycle success paths call `loadMailboxProviderCatalog(true)` when available.
- [x] Existing plugin DOM injection remains as fallback.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Moving plugin config save fully off `/api/plugins/<name>/config`.
- Removing PluginManager config panel routing.
