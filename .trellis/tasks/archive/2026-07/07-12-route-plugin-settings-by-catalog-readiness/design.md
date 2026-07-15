# Design

## Approach

Tighten `providerUsesTempSettingsSchemaPanel(provider)`:

1. Resolve catalog temp item.
2. If item exists and `config_source === 'plugin'` → `false` (PluginManager).
3. If item exists → use `settings_ui.panel === 'schema'`.
4. If item missing:
   - normalize name via aliases
   - if in built-in temp fallback set → `true`
   - if `PluginManager.hasInstalledProvider(name)` → `false`
   - else `false` when PluginManager exists and name is non-empty unknown (safer for third-party), `true` only for empty/legacy default

## Built-in fallback set

Canonical + aliases already normalized by `normalizeTempMailSettingsProviderName`:

- `legacy_bridge` (+ aliases resolve to it)
- `cloudflare_temp_mail`
- `mail_tm`
- `duckmail`
- `tempmail_lol`
- `emailnator`

## Non-goals

Do not yet write plugin fields into schema panel collectors; only fix routing misclassification.
