# External API Smoke Routing Matrix Coverage Design

## Architecture

The smoke checker remains a standalone read-only Python script. It will fetch two additional discovery endpoints and pass their payloads into `validate_contracts()` alongside health, capabilities, and OpenAPI.

The checker validates shape, parity, and secret-safety only. It must not call mutable lifecycle endpoints or provider health network probes.

## Data Flow

`run_smoke()` fetches:

1. `/api/external/health`
2. `/api/external/capabilities`
3. `/api/external/providers`
4. `/api/external/mailboxes?page_size=1`
5. `/api/external/openapi.json`

`validate_contracts()` unwraps external envelopes, reads `readiness_summary.routing_matrix` from provider discovery, reads `provider_context.readiness_summary.routing_matrix` from mailbox directory discovery, and checks the required routing scopes.

## Contract Checks

A valid routing matrix has `version == 1`, `scopes` containing `temp_runtime_default`, `task_temp_apply`, `pool_claim_default`, and `explicit_pool_claim`, and each scope exposes `request_field`, `allowed_values`, `counts`, and `providers`. Providers are not required to be usable in all deployments, but the rows must be objects when present.

Secret scanning expands from capabilities/OpenAPI to include provider discovery and mailbox directory discovery.

## Compatibility

The smoke script gets stricter. Instances missing the newly established routing matrix contract should fail smoke checks so external integrators do not proceed with an incomplete discovery surface.

## Rollback

Remove the two new fetches and the routing matrix validations from `scripts/external_api_smoke.py`, then revert docs/test updates.
