# External integration workflow recipes design

## Boundary

The workflow recipes are an additive projection inside `integration_manifest`. The owner stays `mailops.services.provider_catalog` because that module already builds the external endpoint map, provider integration guide, deployment profile, selection policy, provider diagnostics, and the current manifest.

Controllers must not rebuild recipes. `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, and OpenAPI `x-capabilities` should receive recipes only through `get_external_integration_manifest()` or the existing capabilities contract path.

## Data Flow

`get_external_integration_manifest()` receives the current guide, selection policy, deployment profile, provider diagnostics summary, and endpoint map. The new workflow builder consumes that same context plus existing external read contracts from `get_external_mailbox_read_contract()`.

The manifest emits `workflows` as a list of recipe objects. Each recipe has a stable `key`, human labels, a short description, and ordered `steps`. Each step includes a stable `key`, `method`, `endpoint`, `auth`, optional `query`, optional `body`, optional `response`, and optional `next` metadata.

Provider override request hints come from `selection_policy.scopes.explicit_pool_claim` and `selection_policy.scopes.task_temp_apply`. Endpoint paths come from the endpoint map when available. Message and verification-code read steps use the existing external read contract so the same lifecycle-specific read guidance is available to catalog clients and generated OpenAPI clients.

## Workflow Set

The initial contract covers four practical recipes:

- `discover_external_api`: call capabilities, providers, and mailbox directory discovery before choosing a provider or mailbox source.
- `browse_mailbox_directory`: list the unified mailbox directory and use provider context/action contracts for follow-up reads.
- `claim_pool_mailbox`: claim a reusable mailbox, read messages or verification codes, then complete or release the claim.
- `create_task_temp_mailbox`: create a task-scoped temp mailbox, read messages or verification codes, then finish the task mailbox lifecycle.

## Compatibility

The change is additive. Existing manifest fields and endpoint behavior stay unchanged. Clients that ignore `workflows` continue to work.

Workflow recipes are provider-agnostic. Provider-specific names may appear in allowed values only because the selection policy already exposes them. The builder must not contain provider-name branches.

## Secret Safety

Recipes should document request field names and response field names, not credential values. API auth remains the existing `auth.placeholder` value. Workflow data must not include real API keys, provider tokens, bearer tokens, passwords, JWTs, task tokens, refresh tokens, or consumer keys.

## Rollback

Rollback removes the `workflows` property from the manifest builder and OpenAPI schema. No database migration, provider runtime migration, or frontend state migration is involved.
