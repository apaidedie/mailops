# External readiness API contract design

## Boundary

The existing health endpoint remains the entry point. This task extends data.readiness with a compact mailbox_directory projection. It does not add a new route and does not change the full /api/external/mailboxes payload.

## Data Flow

1. api_external_health resolves the current external API consumer.
2. provider_catalog.get_external_api_readiness_summary receives the consumer and builds existing provider/pool/task readiness from get_external_api_capabilities_contract.
3. The readiness builder calls the unified mailbox catalog with page_size=1 and the consumer allowed_emails scope.
4. The readiness builder projects only summary, totals, endpoint, scoped state, and quick probe parameters into readiness.mailbox_directory.
5. OpenAPI documents the new required field on ExternalReadinessSummary.

## Contract

readiness.mailbox_directory contains:

- status: ready, empty, restricted, or degraded.
- endpoint: /api/external/mailboxes.
- scoped: true when the current multi-key consumer has allowed_emails.
- summary: the unified directory summary object, without mailbox item rows.
- totals: mailboxes, account_mailboxes, and temp_mailboxes derived from the same scoped directory payload.
- quick_probe_params: page=1, page_size=1, kind=all, status=all, read_capability=all, action=all, provider=all, sort=updated_desc.

The field is secret-free by construction because it never includes mailbox items, account credentials, provider diagnostic rows, task tokens, consumer keys, or provider secret values.

## Error Handling

If mailbox directory projection fails, health remains HTTP 200 when the controller is reachable. readiness.mailbox_directory.status becomes degraded, totals are zeroed, endpoint remains discoverable, and warnings includes mailbox_directory_unavailable.

## Compatibility

Existing health consumers keep all previous readiness fields. The new mailbox_directory field is additive at runtime and required in the OpenAPI schema for generated clients.

## Tradeoffs

Calling list_unified_mailboxes(page_size=1) reuses the directory contract and scoping logic rather than duplicating inventory queries. It is heavier than a bespoke count query, but the health payload remains compact and this avoids a second mailbox inventory implementation.
