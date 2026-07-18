# External API v1 versioned aliases Design

## Architecture

The implementation adds a versioned route alias layer without changing controller ownership. Each external route keeps its existing controller function and gains a second URL under `/api/v1/external/*`.

Route files remain the assembly boundary:

- `mailops/routes/system.py` owns health, capabilities, OpenAPI, and account status.
- `mailops/routes/emails.py` owns external read endpoints.
- `mailops/routes/external_pool.py` owns pool lifecycle endpoints.
- `mailops/routes/external_temp_emails.py` owns mailbox directory, provider catalog, mailbox sessions, and task temp-mail lifecycle endpoints.

## Route Strategy

Introduce a tiny helper in the routes layer to register an external endpoint at both paths:

- canonical path: `/api/v1/external/...`
- legacy path: `/api/external/...`

The helper should call `bp.add_url_rule()` twice with distinct endpoint names. This avoids Flask endpoint-name collisions while preserving the same `view_func`, methods, decorators, and optional `csrf_exempt` wrapping.

## Discovery Contract

Provider catalog remains the source of truth for endpoint maps. Add shared helpers/constants so code can derive:

- canonical v1 endpoint map
- legacy endpoint map
- legacy alias metadata mapping endpoint keys from canonical path to legacy path

`get_external_api_capabilities_contract()` should expose canonical v1 paths in `endpoints`, `mailbox_session`, `pool`, `task_temp_mailbox`, `integration_manifest`, and `quickstart`. It should also expose legacy compatibility under a clearly named metadata field such as `legacy_endpoints` or `compatibility.legacy_endpoints`.

## OpenAPI Contract

`get_external_api_openapi_contract()` should build operation paths from the canonical endpoint map, so generated clients target `/api/v1/external/*` by default. Add an OpenAPI extension, for example `x-legacy-endpoints`, copied from the compatibility map. Do not duplicate every legacy operation in `paths`; that would make the schema noisy and easier to drift.

## Compatibility

Existing `/api/external/*` routes must remain first-class for now:

- no redirects
- no deprecation response changes
- same status codes and response envelopes
- same API-key header: `X-API-Key`
- same public-mode and feature-disable behavior

Audit endpoint strings may continue using legacy literals where controller code currently records them. Changing audit strings is not required for this task and could make existing audit tests brittle.

## Rollback

The change should be revertible by removing the route alias helper usage and restoring the provider catalog endpoint map to legacy paths. No database migration or setting migration is needed.
