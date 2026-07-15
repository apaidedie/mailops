# Provider readiness preflight contract

## Goal

Add a provider readiness preflight contract so administrators and external integrations can validate the whole mailbox provider surface before real use. The preflight must cover Outlook/IMAP account sources and temp-mail providers through the existing provider catalog, without leaking credential values or performing upstream network calls unless explicitly requested.

## Requirements

- Expose a batch preflight endpoint for the authenticated admin app.
- Expose the same batch preflight endpoint through the external API key surface.
- Reuse the existing provider catalog, provider diagnostics, selection policy, integration guide, and single-provider health logic instead of rebuilding provider rules in controllers.
- Default behavior must be local-only: no provider factory calls, no upstream domains request, and no mailbox creation.
- Optional `probe_network=true` may probe only temp providers that are locally ready and supported by the existing `health_check()` contract.
- The response must be secret-free. It may expose secret key names such as `DUCKMAIL_BEARER_TOKEN`, but must never expose API key values, bearer tokens, passwords, refresh tokens, provider JWTs, task tokens, or consumer keys.
- External discovery contracts must advertise the preflight endpoint so generated clients can find it from capabilities, provider discovery, quickstart, and OpenAPI.

## Acceptance Criteria

- `GET /api/providers/preflight` requires login and returns a secret-free preflight summary with per-provider rows.
- `GET /api/external/providers/preflight` requires `X-API-Key` and returns the same data under the existing external API envelope.
- Without `probe_network=true`, batch preflight does not instantiate temp-mail providers or call upstream networks.
- With `probe_network=true`, batch preflight delegates provider probing to the existing single-provider health logic and redacts returned details.
- Unknown or inactive/default configuration issues are surfaced as local readiness issues without failing the whole discovery request.
- `/api/external/capabilities`, `/api/external/providers`, and `/api/external/openapi.json` include the preflight endpoint contract.
- Focused Python tests cover the admin route, external route, no-network default, explicit probe behavior, OpenAPI discovery, and secret redaction.

## Notes

This is a backend/API contract task. UI can consume the new endpoint later; do not spend this turn on small visual changes.
