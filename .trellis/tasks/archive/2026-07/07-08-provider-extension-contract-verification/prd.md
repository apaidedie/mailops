# Provider Extension Contract Verification

## Goal

Make future temp-mail provider additions safer and more scalable by exposing a machine-readable, secret-free contract validation result for every registered temp-mail provider. Plugin authors, operators, and external API clients should be able to see whether a provider satisfies the unified mailbox and external integration contract before relying on it in production.

## User Value

- New temp-mail providers can be added without modifying core routes, UI enums, or external client logic.
- Operators can diagnose provider extension issues from the existing plugin/provider discovery surfaces.
- External automation clients can distinguish a configured provider from a provider whose extension metadata or runtime contract is incomplete.

## Confirmed Facts

- `TempMailProviderBase` defines the provider extension surface: provider metadata, `config_schema`, capabilities, `get_options()`, mailbox creation, message list/detail, and delete/clear methods.
- `temp_mail_provider_factory.get_available_providers()` is the source of registered temp-mail provider class metadata consumed by provider catalog code.
- `provider_catalog.get_mailbox_provider_catalog()` projects provider metadata into `/api/providers`, `/api/external/providers`, capabilities, integration guide, integration manifest, and unified mailbox provider context.
- Current plugin APIs support install, uninstall, config schema, config read/write, reload, and connection test, but they do not expose a static contract validation result.
- Backend spec `.trellis/spec/backend/provider-selection-contract.md` requires provider discovery contracts to be generated from the shared provider catalog and to remain secret-free.

## Requirements

1. Add a single backend validation owner for temp-mail provider extension contracts.
2. Validation must work for both built-in and plugin temp-mail providers by consuming provider class metadata from the registry/factory path.
3. Validation must check at least: provider key, label/version metadata, normalized capabilities, `config_schema.fields` shape, secret default handling, required abstract methods, and whether `get_options()` can return a dictionary without leaking secret values.
4. Validation must not create, delete, clear, or mutate mailboxes, and must not call provider upstream network APIs except the existing local `get_options()` readiness shape already used by plugin connection tests.
5. Validation results must be secret-free. They may expose secret key names but must not expose API key values, bearer tokens, passwords, JWTs, task tokens, consumer keys, or provider secret defaults.
6. Provider catalog rows, provider integration guide entries, and integration manifest provider entries must include the validation result so every discovery route carries the same extension-readiness signal.
7. Authenticated plugin APIs must expose a per-plugin contract validation endpoint and include compact validation status in the plugin list.
8. Documentation must tell future provider authors to run/read the contract validation before enabling a provider.

## Acceptance Criteria

- [ ] `tests/test_temp_mail_provider_contract.py` or a focused new backend test proves valid providers receive `contract_validation.status == "valid"` with no issues.
- [ ] Tests prove invalid plugin metadata returns structured validation issues without crashing discovery routes.
- [ ] Tests prove secret defaults in `config_schema` are removed or redacted from validation/catalog/manifest payloads.
- [ ] Tests prove `get_available_providers()`, `get_mailbox_provider_catalog()`, `provider_integration_guide.providers`, and `integration_manifest.providers` all expose the same validation status for a plugin provider.
- [ ] `GET /api/plugins` includes compact contract validation state for installed/loaded plugins.
- [ ] `GET /api/plugins/<name>/contract` returns the full validation payload for a loaded plugin and `PLUGIN_NOT_LOADED` for unknown names.
- [ ] Existing provider discovery, plugin manager, smoke, and unified mailbox tests remain green.

## Out of Scope

- Adding a new concrete third-party provider.
- Running network health probes from validation.
- Changing external API authentication or mailbox lifecycle behavior.
- Redesigning the plugin manager UI in this slice.
