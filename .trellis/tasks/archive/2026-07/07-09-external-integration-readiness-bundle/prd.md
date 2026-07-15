# External integration readiness bundle

## Goal

Add a first-class, authenticated external integration readiness bundle so third-party services can discover whether this Outlook/IMAP/temp-mail aggregation service is ready to integrate without stitching together multiple discovery endpoints manually.

The bundle should make the project more professional and extensible by presenting canonical endpoints, provider readiness, mailbox-session support, OpenAPI metadata, documentation pointers, smoke-check targets, and next-action recommendations through one secret-safe API surface.

## Background

- The project already exposes API-key protected discovery surfaces: `/api/v1/external/capabilities`, `/api/v1/external/providers`, `/api/v1/external/mailboxes`, `/api/v1/external/openapi.json`, and `/api/v1/external/docs`.
- Legacy `/api/external/*` aliases must stay callable and discoverable, but new contracts should prefer canonical `/api/v1/external/*` paths.
- Existing starter clients already build a local `integration-bundle` from capabilities, providers, and OpenAPI. This task converts that concept into a live server contract that other services can fetch directly.
- Provider selection/readiness logic is owned by `outlook_web.services.provider_catalog`; controllers and docs must consume service helpers rather than rebuilding provider rules.
- The docs page is self-contained vanilla HTML/CSS generated from OpenAPI and capabilities metadata.

## Requirements

- Add a canonical `GET /api/v1/external/integration-bundle` endpoint and a legacy `GET /api/external/integration-bundle` alias through the shared external route helper.
- The endpoint must require the same API-key auth and external guard chain as capabilities, docs, OpenAPI, and health.
- The endpoint response must use the existing external API envelope and return a secret-free readiness bundle with:
  - `version`, `service`, and `status`.
  - `endpoints`, `legacy_endpoints`, and `compatibility` copied from the canonical discovery contract.
  - `auth` placeholder metadata using `X-API-Key` and `<your-api-key>` only.
  - `readiness` sections for overall external readiness, providers, mailbox directory, pool, and task temp mailbox.
  - `provider_selection` summary derived from the existing provider selection policy/deployment profile.
  - `openapi` metadata including version, path count, schema count, operation count, and endpoint.
  - `documentation`, `quickstart`, `workflows`, `smoke_checks`, and `recommendations` for external-service onboarding.
- The new route must be discoverable from capabilities endpoint maps, integration manifest discovery endpoints, OpenAPI paths, first-party docs, the smoke checker, and starter clients.
- The implementation must not expose API keys, provider bearer token values, passwords, JWTs, refresh tokens, task tokens, consumer keys, mailbox credentials, or provider secret values. Secret key names may appear only where the existing provider/integration contracts already permit them.
- The bundle must remain provider-agnostic: do not hardcode provider-specific readiness behavior in controllers, docs, smoke checks, or starter clients.
- The endpoint must remain read-only and must not call upstream provider networks. It may compose local capability/readiness state and the generated OpenAPI contract.

## Acceptance Criteria

- [ ] `/api/v1/external/integration-bundle` requires API key auth and returns an external API envelope with the required bundle fields.
- [ ] `/api/external/integration-bundle` returns the same semantics through the legacy alias.
- [ ] `/api/v1/external/capabilities` exposes `endpoints.integration_bundle`, `legacy_endpoints.integration_bundle`, and `integration_manifest.discovery.endpoints.integration_bundle`.
- [ ] OpenAPI documents only the canonical `/api/v1/external/integration-bundle` path and includes a typed `IntegrationBundleData` schema; legacy duplication remains absent from `paths`.
- [ ] The first-party `/api/v1/external/docs` page links and summarizes the integration bundle without leaking configured secrets.
- [ ] `scripts/external_api_smoke.py` fetches and validates the new bundle as a read-only discovery endpoint.
- [ ] Python and JavaScript starter clients discover and prefer the live `integration_bundle` endpoint for their `integration-bundle` command, while preserving local fallback behavior.
- [ ] Targeted tests and repository readiness checks pass.

## Notes

- This is a focused API/discovery slice. Broader visual redesign and provider onboarding improvements remain part of the persistent product goal, but are out of scope for this task.
