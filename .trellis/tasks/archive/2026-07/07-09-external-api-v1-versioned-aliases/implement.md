# External API v1 versioned aliases Implementation Plan

## Steps

1. Add a route-layer helper for dual external route registration.
2. Update external route files to register both `/api/external/*` and `/api/v1/external/*` paths.
3. Add provider catalog endpoint helpers/constants for canonical v1 paths and legacy aliases.
4. Update capabilities, integration manifest, quickstart, mailbox session discovery, pool/task discovery, and documentation endpoint references to use canonical v1 paths plus legacy compatibility metadata.
5. Update OpenAPI generation to emit canonical v1 `paths` and a legacy compatibility extension.
6. Update smoke script contract checks and focused tests for canonical v1 plus legacy compatibility.
7. Add backend spec coverage for versioned external APIs.
8. Run focused tests and syntax checks, then commit and archive the Trellis task.

## Validation Commands

- `python -m pytest tests/test_external_api_versioned_aliases.py -q`
- `python -m pytest tests/test_external_api_smoke_script.py tests/test_multi_mailbox.py -k "capabilities or openapi or mailbox_session" -q`
- `python -m pytest tests/test_external_temp_emails_api.py tests/test_external_mailbox_session_start_api.py -q`
- `python -m py_compile outlook_web/routes/system.py outlook_web/routes/emails.py outlook_web/routes/external_pool.py outlook_web/routes/external_temp_emails.py outlook_web/services/provider_catalog.py outlook_web/services/external_api_openapi.py scripts/external_api_smoke.py`
- `git diff --check`

## Risk Notes

- Many tests currently assert exact `/api/external/*` strings. Update only tests that inspect discovery's canonical endpoint map; legacy behavior tests should remain on old paths.
- Flask requires distinct endpoint names when the same view is registered twice.
- Dynamic route order matters for message detail versus raw message paths; keep the same order when adding aliases.
- Do not weaken auth tests by making v1 public. v1 aliases must traverse the same decorators as legacy routes.
