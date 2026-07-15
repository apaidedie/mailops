# Design

## Boundary

The provider catalog remains the source of truth. This task adds a projection to the existing readiness summary instead of creating a second registry or new route.

## Data Flow

Provider catalog and diagnostics -> provider integration guide -> routing matrix -> `get_mailbox_provider_readiness_summary()` -> `capability_matrix` -> external providers/capabilities/mailbox-directory/integration-bundle/OpenAPI surfaces.

## Contract

`MailboxProviderReadinessSummary.capability_matrix` is a versioned object with:

- `version`: integer, initially `1`.
- `generated_from`: list of source contracts used for the projection.
- `totals`: non-negative counters for provider categories and workflow support.
- `workflows`: object keyed by workflow name. Each workflow has `workflow`, `label`, `provider_count`, `providers`, and `selector_fields`.
- `providers`: ordered row list. Each row includes provider identity, active/configured/readiness state, config source, aliases, capability booleans, read actions, lifecycle actions, selection fields, and endpoint hints.

Capability booleans are derived from existing catalog semantics:

- Account providers require pool inventory, are pool-claim capable, directory visible, and session capable through pool-backed sessions.
- Temp providers are dynamic-create capable, task-temp capable, directory visible, and session capable through task-temp sessions.
- Provider health is available for both account and temp providers through the existing provider health endpoint.
- Read actions are the provider-neutral read actions already exposed by mailbox-session/read contracts.

## Safety

Rows may expose secret key names only through existing config status counts or selector metadata, but must not expose secret values. The matrix itself should avoid required env/settings lists and use counts plus status flags instead.

## Compatibility

Adding `capability_matrix` is additive. Existing consumers of readiness summary continue to work. OpenAPI updates make the new field discoverable to generated clients.

## Rollback

Remove the helper, the readiness summary field, OpenAPI schema references, docs, and tests. Existing provider readiness fields remain unchanged.
