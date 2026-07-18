# External integration manifest design

## Boundary

The manifest is a read-only projection over existing external discovery data. It lives in `mailops.services.provider_catalog` near `get_provider_integration_guide()` and `get_external_api_capabilities_contract()` because that module already owns endpoint maps, provider deployment profile, selection policy, diagnostics, aliases, and the integration guide.

No controller should rebuild the manifest directly. Controllers should receive it from the same service payload that owns their `provider_integration_guide`.

## Data Flow

`provider_catalog` builds or receives these existing inputs: catalog, deployment profile, selection policy, provider diagnostics, endpoint map, provider filter, and `provider_integration_guide`.

The manifest builder consumes those inputs and emits:

- `version`: manifest schema version, starting at `1`.
- `auth`: API key header metadata and placeholder, never a real key.
- `discovery`: ordered discovery calls and endpoint map.
- `selection`: source priority, active allowlist field, runtime temp-mail field, pool claim field, and task temp-mail field.
- `deployment`: env/config file hints, source priority, and template pointers/examples from deployment profile / selection policy.
- `providers`: provider key/name/kind/label, readiness/configuration state, request fields, env key hints, secret key names, capabilities, health endpoint, aliases, and mailbox-directory filter endpoint.
- `secret_policy`: copied or summarized from the guide, with `exposes_secret_values=false` preserved.

The manifest is embedded into:

- authenticated `/api/providers`
- external `/api/external/providers`
- external `/api/external/capabilities`
- OpenAPI `x-capabilities` and schemas.

## Compatibility

All existing fields remain unchanged. Existing clients can keep using `provider_integration_guide`; the manifest is additive.

The manifest must avoid provider-name conditionals. If DuckMail or a plugin provider appears, it appears because the guide includes it. Secret handling is driven by `secret_env` / `configuration.secret_env` and `secret_settings` / `configuration.secret_settings`.

## Rollback

The change is additive. A rollback removes `integration_manifest` from the service payload and schemas without database migrations or runtime provider changes.
