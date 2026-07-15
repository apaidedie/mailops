# Provider Extension Contract Verification Design

## Architecture

Add a small provider-contract validation service under `outlook_web/services/` and make it the single owner of temp-mail provider extension validation. The service consumes provider class metadata from the registry and provider-info dictionaries produced by `temp_mail_provider_factory.get_available_providers()`.

Primary entry points:

- `outlook_web.services.temp_mail_provider_contract.validate_temp_mail_provider_class(name, provider_cls)`
- `outlook_web.services.temp_mail_provider_contract.validate_temp_mail_provider_info(provider_info)`
- `outlook_web.services.temp_mail_provider_contract.contract_validation_summary(validation)`

`temp_mail_provider_factory.get_available_providers()` attaches full `contract_validation` to each provider metadata object. Downstream catalog builders then pass that field through instead of recalculating.

## Data Flow

```text
Provider class registry
  -> temp_mail_provider_factory.get_available_providers()
  -> provider info with contract_validation
  -> provider_catalog._build_mailbox_provider_catalog()
  -> mailbox_providers / provider_diagnostics / provider_integration_guide / integration_manifest
  -> authenticated plugin API and external discovery clients
```

Plugin API flow:

```text
GET /api/plugins
  -> installed + available + load_state
  -> loaded provider validation summary when provider class exists

GET /api/plugins/<name>/contract
  -> temp_mail_plugin_manager.get_plugin_contract_validation(name)
  -> full validation payload or PLUGIN_NOT_LOADED
```

## Validation Contract

Validation payload shape:

```json
{
  "version": 1,
  "provider": "provider_key",
  "status": "valid | warning | invalid",
  "valid": true,
  "checks": [...],
  "issues": [...],
  "summary": {"errors": 0, "warnings": 0, "checks": 8},
  "safe_metadata": {...}
}
```

Issue shape:

```json
{
  "code": "CONFIG_FIELD_SECRET_DEFAULT",
  "severity": "error | warning",
  "path": "config_schema.fields[1].default",
  "message": "Secret config fields must not define default values"
}
```

Initial required checks:

- `provider_name`: non-empty string matching the registered key.
- `provider_label`: non-empty string; warning, not error, when missing.
- `provider_version`: non-empty string.
- `capabilities`: normalized `delete_mailbox`, `delete_message`, `clear_messages` booleans.
- `config_schema`: object with list-like `fields` when present.
- `config_schema.fields[*].key`: non-empty stable keys matching `[A-Za-z0-9_.-]+`.
- `config_schema.fields[*].type`: known UI type or warning fallback to text.
- secret fields: `type=password` or secret-like key names must not define `default` values.
- required provider methods: `get_options`, `create_mailbox`, `delete_mailbox`, `list_messages`, `get_message_detail`, `delete_message`, `clear_messages` are callable and implemented away from abstract placeholders.
- optional local runtime probe: instantiate the provider and call `get_options()` only. If it raises, record a warning because missing credentials should not make a provider extension structurally invalid.

## Secret Policy

The validator never calls mailbox mutation methods. It must not include raw `get_options()` payloads because they may contain upstream URLs or operational state. It may expose compact facts such as `options_probe_ok`, `domain_count`, and whether the return value is a dict.

The validator uses the same secret hint vocabulary as provider catalog where possible. Secret defaults are removed from provider catalog by existing `_plugin_config_schema()` sanitation; the validator adds an explicit issue so plugin authors see the problem.

## Compatibility

Built-in providers should validate as `valid` or at worst `warning` if they intentionally lack plugin-style config schema. Existing plugin APIs keep current response envelopes; new fields are additive.

The full validation payload is additive in discovery responses. External clients that ignore unknown fields keep working.

## Rollback

If validation causes unexpected regressions, disable catalog propagation by removing the `contract_validation` pass-through from `get_available_providers()` and provider catalog while keeping the standalone service/tests for later correction.
