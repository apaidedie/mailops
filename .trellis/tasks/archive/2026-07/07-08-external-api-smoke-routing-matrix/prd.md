# External API Smoke Routing Matrix Coverage

## Goal

Improve the external integration smoke checker so third-party services can verify that an Outlook Email Plus instance exposes the provider routing matrix and unified mailbox provider context needed for provider-neutral mailbox orchestration.

## Confirmed Facts

- `scripts/external_api_smoke.py` currently performs read-only checks against `/api/external/health`, `/api/external/capabilities`, and `/api/external/openapi.json`.
- The provider discovery contract now exposes `readiness_summary.routing_matrix` through `/api/providers`, `/api/external/providers`, and unified mailbox `provider_context.readiness_summary`.
- The smoke script is documented in `docs/external-integration-quickstart.md` as a read-only CI/deployment verification step.
- Existing tests in `tests/test_external_api_smoke_script.py` use injected payloads, so the checker can be extended without requiring a live server.

## Requirements

1. Extend the smoke checker to fetch read-only provider and mailbox directory discovery endpoints.
2. Validate that `/api/external/providers` exposes `readiness_summary.routing_matrix.version == 1` with the required selection scopes.
3. Validate that `/api/external/mailboxes` exposes `provider_context.readiness_summary.routing_matrix.version == 1` with the required selection scopes.
4. Validate that routing scope rows expose provider-selector fields, allowed values, counts, and provider rows enough for generated clients to choose providers without scraping docs.
5. Keep the checker secret-safe: it must scan the newly fetched provider and mailbox discovery payloads for obvious API keys, bearer tokens, and DuckMail-style tokens.
6. Preserve the read-only behavior: the script must not claim pool mailboxes, create temp mailboxes, read messages, finish tasks, release/complete claims, or probe provider upstream networks.
7. Update quickstart documentation so integrators know the smoke checker validates provider routing and mailbox context discovery.

## Acceptance Criteria

- [ ] `tests/test_external_api_smoke_script.py` proves the smoke checker fetches `/api/external/providers` and `/api/external/mailboxes`.
- [ ] Smoke tests fail when provider discovery lacks `readiness_summary.routing_matrix`.
- [ ] Smoke tests fail when mailbox directory discovery lacks `provider_context.readiness_summary.routing_matrix`.
- [ ] Smoke tests prove secret scanning includes provider and mailbox discovery payloads.
- [ ] Documentation mentions the two added read-only endpoints and the routing matrix coverage.
- [ ] Targeted Python tests pass.

## Out of Scope

- Changing runtime provider selection behavior.
- Adding a new mailbox provider.
- Creating a generated SDK.
- Running mutable external lifecycle operations from the smoke script.
