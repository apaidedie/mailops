# External API docs page

## Goal

Add a first-party, browser-readable documentation page for the external API so integrators can inspect authentication, discovery endpoints, mailbox-session workflow, provider selection, and OpenAPI-backed endpoint groups without needing a separate Swagger/Redoc deployment.

This advances the product goal of making OutlookMail Plus a polished unified mailbox aggregation service that is easy for other services to adopt.

## Background / Confirmed Facts

- `GET /api/v1/external/openapi.json` already returns an OpenAPI 3.1 contract protected by `X-API-Key`.
- Legacy `/api/external/*` aliases are preserved through `add_external_api_url_rule()`.
- `README.md`, `README.en.md`, `integration_manifest`, and `provider_context.documentation` already point users at the OpenAPI JSON contract.
- There is no human-readable in-app API documentation route comparable to `/api/v1/external/docs`.
- The app now emits CSP through `outlook_web/middleware/security_headers.py`; a docs page must avoid remote scripts/styles and work with the current same-origin/inline-compatible policy.
- External API routes are meant for automation clients and must not expose plaintext API keys, provider secrets, IMAP passwords, refresh tokens, temp-mail task tokens, or consumer keys.

## Requirements

- Add canonical `GET /api/v1/external/docs` and legacy `GET /api/external/docs` routes.
- Protect the docs routes with the same external API key guard as `/api/v1/external/openapi.json`.
- Render a self-contained HTML page generated from the current OpenAPI contract and capabilities data.
- The page must include:
  - service title/version and external API version,
  - auth header contract for `X-API-Key`, using placeholder values only,
  - canonical links to docs, OpenAPI JSON, capabilities, providers, and mailbox directory,
  - grouped endpoint list with method, path, summary, operation id, and request/response schema names when available,
  - high-signal workflow guidance for discovery and mailbox sessions derived from `integration_manifest` / endpoint map,
  - provider selection summary including source priority and default provider values.
- The page must be zero-dependency: no CDN, no package install, no remote JS/CSS.
- The page must be readable on desktop and mobile and follow the repo's restrained operational SaaS style rather than a marketing landing page.
- Add docs page discovery to capabilities/documentation/integration-manifest surfaces where external consumers already discover docs and contracts.
- Update README and project map to mark OpenAPI / Swagger docs as completed through the first-party docs route.

## Acceptance Criteria

- [ ] `GET /api/v1/external/docs` without `X-API-Key` returns 401/403 consistently with guarded external API routes.
- [ ] `GET /api/v1/external/docs` with a valid key returns `text/html` and includes no provider secret values or plaintext API key values.
- [ ] The docs HTML contains the canonical OpenAPI JSON endpoint, capabilities endpoint, providers endpoint, mailbox directory endpoint, and mailbox session endpoints.
- [ ] The docs HTML includes at least one endpoint group generated from the OpenAPI `paths`, not a hard-coded stale list.
- [ ] `GET /api/external/docs` remains a legacy alias for compatibility.
- [ ] `GET /api/v1/external/capabilities` and `GET /api/v1/external/providers` expose the docs endpoint in their documentation metadata without leaking secrets.
- [ ] Existing OpenAPI JSON, capabilities, provider catalog, CORS, and security header tests continue to pass.
- [ ] README and `docs/项目地图.md` mention the new first-party docs page.

## Out Of Scope

- No hosted Swagger UI, Redoc, or Scalar bundle in this task.
- No unauthenticated public documentation page.
- No broad redesign of the settings page or admin dashboard.
- No OpenAPI schema expansion beyond what is needed to make the docs route discoverable.
