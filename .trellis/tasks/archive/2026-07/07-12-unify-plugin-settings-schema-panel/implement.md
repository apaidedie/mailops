# Implementation Plan

1. Update `providerUsesTempSettingsSchemaPanel` for catalog-ready plugins with fields.
2. Add plugin test-connection action in schema panel render when `config_source=plugin`.
3. Update frontend contract tests + quality-guidelines note.
4. Validate.

## Validation

- `node --check static/js/main.js`
- Focused settings frontend unittest
- `git diff --check`
