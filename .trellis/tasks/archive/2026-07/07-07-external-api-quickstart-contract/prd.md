# External API quickstart contract

## Goal

Expose a compact, secret-free quickstart contract for external services so they can discover the API, choose a provider, list mailbox inventory, and start either pool-claim or task-temp-mail flows without reverse-engineering the larger integration manifest.

## Confirmed Facts

- `/api/external/capabilities` already returns `integration_manifest`, `provider_integration_guide`, `selection_policy`, endpoint maps, pool discovery, task-temp-mail discovery, and mailbox directory discovery.
- `/api/external/providers` and authenticated `/api/providers` already build the same `integration_manifest` from provider catalog helpers.
- `integration_manifest.workflows` is comprehensive but too large for a first machine-readable starter surface.
- The frontend Settings command center currently creates starter snippets from manifest data, which proves the data exists but leaves external clients to reconstruct a quickstart object themselves.
- Secret values must never be returned. Existing manifests may expose secret key names with empty values, but workflow quickstart examples should not include provider secret key names unless they are deployment hints.

## Requirements

- Add `integration_manifest.quickstart` as a stable versioned object generated in `provider_catalog`, not in controllers or frontend code.
- Reuse the same quickstart object at top level in `/api/external/capabilities`, `/api/external/providers`, and authenticated `/api/providers` for easy client discovery.
- Include auth placeholder, recommended discovery order, minimal request examples, provider selector fields, endpoint paths, and workflow keys for mailbox browsing, pool claiming, and task temp-mail creation.
- Derive selector fields and allowed values from `selection_policy`; do not hardcode provider names or request fields.
- Keep examples secret-free. API key examples must use `X-API-Key: <your-api-key>`, and provider credentials must not appear in quickstart request examples.
- Update OpenAPI so generated clients know `quickstart` exists and can type its request examples.
- Update provider onboarding docs and backend specs so future provider work keeps the quickstart contract in sync with the manifest.

## Acceptance Criteria

- `/api/external/capabilities` returns `data.quickstart` and `data.integration_manifest.quickstart`, and both objects are equal.
- `/api/external/providers` returns `data.quickstart` equal to `data.integration_manifest.quickstart`.
- Authenticated `/api/providers` returns the same quickstart shape for the admin UI.
- Quickstart includes `version=1`, auth placeholder headers, `recommended_sequence`, `provider_selector_fields`, `endpoints`, `requests`, and `workflow_keys`.
- Pool claim request examples use `provider`; task temp-mail request examples use `provider_name`; allowed values match `selection_policy.scopes.*.allowed_values`.
- Quickstart payloads do not expose real API keys, bearer token values, task tokens, consumer keys, JWTs, passwords, or provider secret values.
- OpenAPI marks `quickstart` under `CapabilitiesData`, `ProviderCatalogData`, and `IntegrationManifest`, and defines `IntegrationQuickstart` schemas.
- Focused external API tests pass, plus Python/JS syntax and diff checks.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
