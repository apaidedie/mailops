# External mailbox session start API implementation plan

## Checklist

1. Add failing tests for the new session start endpoint: pool success, pool-empty fallback to task temp-mail, multi-key no-pool-access behavior, invalid input, capabilities/OpenAPI exposure.
2. Add the route to the external temp-mail blueprint or a nearby external workflow module while keeping API key and external guard decorators.
3. Implement controller helpers to normalize strategy, validate JSON object bodies, enforce pool-access strategy rules, call existing pool/task-temp services, and shape a secret-free response.
4. Add the endpoint to provider catalog endpoint maps, capabilities features, quickstart, and integration manifest workflows.
5. Add typed OpenAPI request/response schemas and path operation.
6. Update the backend provider-selection contract with the new endpoint/discovery rule.
7. Run focused tests and quality checks, then commit, archive, and record the session.

## Validation Commands

- `python -m pytest tests/test_external_mailbox_session_start_api.py tests/test_external_api.py -q -rs -k "mailbox_session or capabilities_returns_feature_list_and_audits or openapi_contract_exposes_external_api_paths_and_security"`
- `python -m pytest tests/test_external_mailbox_session_start_api.py -q -rs`
- `python -m py_compile mailops/controllers/external_temp_emails.py mailops/routes/external_temp_emails.py mailops/services/provider_catalog.py mailops/services/external_api_openapi.py`
- `git diff --check`
- Run the repository secret scan pattern used by recent external API tasks.

## Risk

- The endpoint must not duplicate pool permission logic incorrectly. Keep permission behavior explicit and covered by tests.
- Fallback should be narrow. If fallback catches broad errors, real provider failures become hard to diagnose.
- Discovery contracts are broad; update capabilities, manifest, and OpenAPI together to avoid drift.
