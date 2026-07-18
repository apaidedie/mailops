# External API docs page Design

## UI Brief

- Audience: external integrators, automation script authors, and operators configuring mailbox providers.
- Primary workflow: open one authenticated URL, understand how to authenticate, discover providers/mailboxes, start/read/close mailbox sessions, and find the OpenAPI JSON for client generation.
- Product archetype: operational SaaS documentation surface, dense but calm, not a marketing page.
- Constraints: Flask app with server-rendered templates/static files, current CSP allows same-origin assets and inline styles/scripts, self-hosted deployments should work offline, no new frontend build pipeline.
- Source of truth: existing OpenAPI contract, `integration_manifest`, endpoint map, provider selection policy, README external integration section.
- States: authenticated success page, guarded unauthenticated failure through existing external guard, mobile/desktop responsive layouts.
- Acceptance: contract tests for auth, route aliasing, content, secret safety, and discovery metadata.

## Architecture

Add a small HTML-rendering service beside the existing OpenAPI generator:

- `mailops/services/external_api_docs.py`
  - Calls `get_external_api_openapi_contract(consumer=consumer)`.
  - Extracts endpoint groups from `paths` dynamically.
  - Extracts discovery/workflow/provider-selection metadata from `x-capabilities`.
  - Renders a self-contained HTML document with escaped values.

Controller and routing:

- Add `api_external_docs()` to `mailops/controllers/system.py`.
- Register `/api/external/docs` through `add_external_api_url_rule()`, which also exposes `/api/v1/external/docs`.
- Use `@external_api_guards()` so access behavior matches existing external docs contracts.

Discovery:

- Extend provider documentation metadata in `mailops/services/provider_catalog.py` so `documentation.entries.api_docs` points to `/api/v1/external/docs` with legacy endpoint `/api/external/docs`.
- If endpoint maps are centralized, add `docs` to that map so capabilities, integration manifest, and generated docs can reference the same canonical path.

## HTML Contract

The page is a documentation tool, not an admin UI. It should include:

- Compact top banner: service title, app version, external API version.
- Auth block: `X-API-Key: <your-api-key>` only; never echo the actual request key.
- Quick links: docs, OpenAPI JSON, capabilities, providers, mailboxes.
- Workflow section: recommended discovery sequence and mailbox session lifecycle.
- Provider selection section: source priority, runtime temp provider, pool default provider, active provider allowlist.
- Endpoint catalog: grouped by path prefix and OpenAPI tags, showing method/path/summary/operation id/schema refs.

Use inline CSS only, no JavaScript requirement. Layout should be responsive with grid/flex and no horizontal overflow on narrow screens.

## Compatibility / Safety

- Do not change existing JSON response envelopes.
- Do not expose secrets. Only show placeholders or endpoint paths.
- Use HTML escaping for all generated strings.
- Preserve legacy aliases.
- Keep OpenAPI `paths` canonical under `/api/v1/external/*`; the docs page may mention the legacy docs alias in metadata and README.

## Rollback

Remove the docs service, controller method, route registration, and documentation metadata addition. Existing OpenAPI JSON and capabilities routes remain unchanged.
