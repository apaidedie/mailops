# External API contract validation console design

## Architecture

- Add `outlook_web.services.external_api_contract_check` as the service owner for the admin validation report.
- Add `api_external_api_contract_check()` to `outlook_web.controllers.settings` and mount it under `outlook_web.routes.settings` at `/api/settings/external-api/contract-check` with `login_required`.
- Keep `/api/v1/external/*` unchanged. This is an admin readiness surface, not a new external API contract.
- Update `static/js/main.js` and `static/css/main.css` inside the existing External API command center block.

## Backend Data Flow

1. Controller receives authenticated admin request.
2. Service composes local payloads:
   - health-like data with `get_external_api_readiness_summary(database_ok=True, upstream_probe_ok=None)`.
   - capabilities with `get_external_api_capabilities_contract(consumer=None)`.
   - OpenAPI with `get_external_api_openapi_contract(consumer=None)`.
   - integration bundle with `get_external_api_integration_bundle(..., openapi_metadata=openapi_contract)`.
   - provider discovery from capabilities/provider readiness fields.
   - mailbox directory sample through `list_unified_mailboxes(page=1, page_size=1)`.
3. The service adapts those payloads into the same envelope shapes expected by `scripts.external_api_smoke.validate_contracts`.
4. The service maps `CheckResult` values to UI-safe rows grouped by contract area.
5. The service returns a report with counters, grouped checks, safety flags, and next actions.

## Contracts

`contract_check` fields:

- `version`: integer report version.
- `status`: `pass`, `fail`, or `error`.
- `generated_at`: UTC ISO timestamp.
- `local_only`: `true`.
- `network_probes`: `false`.
- `mutation_safe`: `true`.
- `summary`: `total`, `passed`, `failed`, `warnings`, `critical`, `groups`.
- `groups`: ordered objects with `key`, `label`, `status`, `summary`, and `checks`.
- `next_actions`: bounded, secret-safe action hints.

Check rows contain `name`, `description`, `passed`, `group`, and `severity`. They may include a safe `detail`, but never raw provider diagnostics or credential values.

## Safety

- No plaintext external API key is required because the service runs local contracts directly.
- No upstream probes are run; external health readiness uses `upstream_probe_ok=None`.
- No mailbox rows beyond a one-item directory sample envelope are returned to the UI; the report returns only validation summaries.
- Secret-safety scanner checks serialized report text for common secret field names and known token-like values where tests seed them.

## Frontend Design

- Add a contract validation panel immediately after the existing smoke command panel and before the integration bundle launchpad.
- Panel tone follows service `status`: pass -> green, fail -> gold/red attention, error -> degraded.
- Loading state shows a compact stable shell.
- Error state keeps copy and other command-center panels usable.
- The panel shows counters, grouped check rows, and next actions from the API. It does not recompute provider rules or call external API endpoints.

## Rollback

- Backend rollback removes one service file, one controller, and one route.
- Frontend rollback removes one panel renderer/fetch helper and CSS block. Existing smoke/bundle/quickstart panels remain unaffected.
