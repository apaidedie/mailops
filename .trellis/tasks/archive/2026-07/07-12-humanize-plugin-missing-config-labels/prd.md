# Humanize plugin missing-config labels

## Goal

Show human-readable labels for plugin missing-config keys (e.g. `plugin.foo.base_url`) using catalog schema field labels instead of raw setting keys.

## Problem / user value

- After schema-panel unification, plugin readiness/status text uses `missing_config` keys like `plugin.x_plugin.base_url`.
- Operators see opaque machine keys in Settings summary and temp-email status.

## Requirements

- Prefer catalog `config_schema.fields[].label` when key matches `plugin.<provider>.<field>`.
- Fall back to known built-in map, then raw key.
- Contract test asserts plugin key resolution path.

## Acceptance Criteria

- [x] `getMissingConfigDisplayName('plugin.foo.base_url')` uses catalog field label when available.
- [x] Built-in keys unchanged.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Backend missing_config payload reshape.
