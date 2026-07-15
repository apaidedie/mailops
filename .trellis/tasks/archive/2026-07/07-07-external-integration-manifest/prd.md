# External integration manifest

## Goal

Make the external discovery contract easier for other projects to consume by exposing a secret-safe, machine-readable integration manifest derived from the existing provider catalog, selection policy, endpoint map, and provider integration guide.

External clients should be able to call `/api/external/capabilities` or read OpenAPI `x-capabilities`, then discover the API key header, endpoint paths, provider override fields, deployment env/config keys, and safe placeholders without scraping the Settings UI or reverse-engineering provider behavior.

## Confirmed Facts

- `outlook_web.services.provider_catalog.get_external_api_capabilities_contract()` already builds the canonical external discovery payload with `selection_policy`, `provider_integration_guide`, endpoint map, mailbox directory discovery, pool discovery, and task temp-mail discovery.
- `GET /api/external/providers`, `GET /api/external/capabilities`, `GET /api/external/openapi.json`, and the authenticated `/api/providers` contract already expose provider catalog data and must stay consistent.
- `provider_integration_guide` is already secret-free and may expose key names such as `DUCKMAIL_BEARER_TOKEN`, but not secret values.
- Source priority is fixed as `env`, `provider_config_file`, `settings`, `default`; provider aliases such as `gptmail`, `legacy_gptmail`, `temp_mail`, and `legacy_bridge` must remain data-driven.
- The frontend starter kit already renders curl, JavaScript, Python, and env snippets from the same discovery caches.

## Requirements

- Add a top-level `integration_manifest` object to the external capabilities contract and provider catalog discovery payloads without changing existing request fields, provider aliases, endpoint behavior, or provider selection priority.
- Generate the manifest from existing helpers and payloads, not from a separate provider registry or provider-specific branches.
- Include at least: manifest version, authentication header/name placeholder, endpoint map, recommended discovery sequence, provider source priority, provider override request fields, env/config deployment key hints, provider env key names, provider config-file template pointers or examples, and secret policy.
- Keep all manifest values secret-safe. API keys must use placeholders such as `<your-api-key>`. Provider secret env/settings keys may appear only as key names with empty placeholder values. No bearer tokens, API keys, JWTs, passwords, task tokens, consumer keys, refresh tokens, or masked placeholder values may appear.
- Keep the manifest extensible for future mailbox/provider kinds. New catalog providers should appear through `provider_integration_guide.providers` and selection policy scopes without editing provider-name conditionals.
- Expose the manifest in OpenAPI schemas so generated clients can type and discover it.
- Preserve compatibility for existing tests and clients that consume `provider_integration_guide` directly.

## Acceptance Criteria

- `outlook_web.services.provider_catalog` defines a reusable manifest builder and `get_external_api_capabilities_contract()` includes `integration_manifest` at top level.
- `GET /api/external/capabilities` returns `integration_manifest` in the response data.
- `GET /api/external/providers` and authenticated `/api/providers` include the same manifest shape, generated from the same provider catalog/selection-policy inputs as their `provider_integration_guide`.
- `GET /api/external/openapi.json` includes `integration_manifest` in `x-capabilities`, in the `CapabilitiesData` schema, and in provider catalog/discovery schemas where applicable.
- Tests assert the manifest includes API key placeholder/header metadata, discovery endpoints, provider selection request fields, source priority, provider env key hints, DuckMail secret key name with empty value, Mail.tm base URL default, and GPTMail compatibility aliases through the existing guide/policy data.
- Tests assert the manifest does not leak the real DuckMail bearer token, external API keys, provider JWTs, passwords, task tokens, consumer keys, or `dk_...` token patterns.
- Static scans for production `console.log`/`console.debug` and committed DuckMail bearer token values still pass.

## Out of Scope

- Adding a new external API endpoint solely for the manifest.
- Changing API key authentication, provider selection precedence, provider aliases, request field names, OpenAPI route paths, or provider runtime behavior.
- Generating SDK packages or adding frontend UI for the manifest in this task.
