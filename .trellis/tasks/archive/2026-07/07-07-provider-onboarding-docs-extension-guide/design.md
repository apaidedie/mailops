# Provider onboarding docs and extension guide design

## Architecture and boundaries

This task adds provider onboarding documentation and documentation pointers to existing provider discovery contracts. It must not change provider selection behavior, endpoint paths, provider aliases, request fields, config-file sections, or secret masking behavior.

The central backend boundary is `outlook_web.services.provider_catalog`. It already builds `deployment_profile`, `selection_policy`, `provider_integration_guide`, `integration_manifest`, and mailbox `provider_context`. The new `documentation` object should be produced from one helper so these payloads stay aligned.

The OpenAPI boundary is `outlook_web.services.external_api_openapi`. Schemas need to tolerate the new object and describe it for external client generation.

The docs boundary is public repository docs. A new guide should become the preferred human entry point while README stays concise.

## Contract shape

Add a `documentation` object with stable repository-relative paths and purpose labels. It should be safe to expose through external APIs because it only contains local doc paths, labels, and descriptions.

Suggested keys:

- `provider_onboarding`: the new guide for external integration and provider selection.
- `plugin_extension`: the existing temp-mail provider plugin guide.
- `plugin_prompt`: the existing AI/agent prompt for implementing a new provider.
- `env_example`: `.env.example`.
- `provider_config_json`: `.runtime/providers.example.json`.
- `provider_config_toml`: `.runtime/providers.example.toml`.
- `openapi`: `/api/external/openapi.json` as an API endpoint reference.

Each entry should include `label`, `path`, `type`, and `purpose`. API endpoint entries can include `endpoint` instead of `path`.

## Data flow

`get_provider_documentation_contract()` returns the shared object. `get_provider_integration_guide()`, `get_external_integration_manifest()`, and `get_mailbox_directory_provider_context()` embed a deep copy of that object. `/api/external/capabilities`, `/api/external/providers`, admin `/api/providers`, external OpenAPI `x-capabilities`, and `/api/external/mailboxes` then receive it through existing assembly functions.

## Compatibility

The change is additive. Existing clients that ignore unknown fields keep working. Tests must still prove that secret values are not included anywhere in the manifest/guide/documentation payloads.

## Rollback

Rollback is a clean removal of the helper, schema additions, tests, and docs links. No database migration or settings change is involved.
