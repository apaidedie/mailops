# External Integration Readiness Bundle Design

## Architecture

The provider catalog remains the owner of external discovery data. Add `get_external_api_integration_bundle()` to `mailops.services.provider_catalog` and make it compose:

- `get_external_api_capabilities_contract()` for endpoint maps, compatibility, provider selection, quickstart, documentation, and integration manifest.
- `get_external_api_readiness_summary()` for local operational readiness.
- Optional OpenAPI metadata passed from the controller after `get_external_api_openapi_contract()` runs, so path/schema/operation counts reflect the generated contract without creating service-level recursion.

The controller adds only a thin authenticated route handler that fetches the consumer, calls the service helper, audits the request, and returns the existing external envelope. Shared route registration mounts both canonical and legacy aliases.

## Contract Shape

`IntegrationBundleData` is read-only and secret-safe:

- `version`: integer contract version.
- `service`, `status`, `generated_at`: service identity and aggregate readiness.
- `auth`: `{header, placeholder}` copied from the integration manifest or safe defaults.
- `endpoints`, `legacy_endpoints`, `compatibility`: canonical and legacy route maps.
- `documentation`: existing documentation pointer contract.
- `quickstart`: existing integration quickstart projection.
- `readiness`: compact sections for external readiness, provider readiness, mailbox directory, pool, and task temp mailbox.
- `provider_selection`: source priority, selector fields, provider values, and config-file status from existing provider contracts.
- `openapi`: endpoint, version, path count, schema count, and operation count.
- `workflows`: compact workflow summary from `integration_manifest.workflows`.
- `smoke_checks`: read-only endpoints external services can probe before stateful mailbox operations.
- `recommendations`: ordered next actions derived from readiness warnings/restrictions.

## Data Flow

API key request -> `api_external_integration_bundle()` -> consumer context -> provider catalog bundle helper -> optional OpenAPI metadata callback -> external API envelope.

Capabilities -> endpoint map includes `integration_bundle` -> OpenAPI uses same endpoint map -> docs page and starter clients discover the endpoint from capabilities -> smoke script validates the live contract.

## Compatibility

The canonical endpoint is `/api/v1/external/integration-bundle`; `/api/external/integration-bundle` is a legacy alias registered by `add_external_api_url_rule()`. OpenAPI `paths` includes only canonical v1 operations. Legacy compatibility stays in `legacy_endpoints` and `x-legacy-endpoints` metadata.

## UI / Docs Brief

Audience: external service developers and operators integrating mailbox automation.

Primary workflow: quickly determine readiness, find docs/OpenAPI, run read-only smoke checks, then choose a mailbox session workflow.

Product archetype: operational SaaS/API documentation surface.

Constraints: vanilla server-rendered HTML/CSS, self-contained docs page, existing restrained palette, no new frontend framework, no CDN, responsive wrapping.

Acceptance: docs tests verify visible bundle link/summary, canonical path, responsive CSS hooks, and no secret leakage.

## Risks

- Avoid recursion between bundle generation and OpenAPI generation. The provider catalog helper accepts optional `openapi_metadata`; the controller can pass metadata from the generated OpenAPI document, while capabilities can expose the endpoint without building the bundle.
- Avoid provider-rule drift. Readiness and selection summaries must consume existing capability/manifest/readiness fields only.
- Avoid making the smoke script stateful. It should only fetch health, capabilities, providers, mailboxes, OpenAPI, and the bundle.
