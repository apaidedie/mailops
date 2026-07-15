# External API Smoke Routing Matrix Coverage Implementation Plan

## Steps

1. Update smoke script tests with provider and mailbox payload fixtures that include routing matrices.
2. Add negative tests for missing provider routing matrix and missing mailbox routing matrix.
3. Implement helper validation for routing matrices in `scripts/external_api_smoke.py`.
4. Extend `run_smoke()` to fetch `/api/external/providers` and `/api/external/mailboxes?page_size=1`.
5. Update `docs/external-integration-quickstart.md` and backend spec notes for smoke coverage.
6. Run targeted tests and smoke-related checks.

## Validation Commands

- `python -m pytest tests/test_external_api_smoke_script.py -q`
- `python -m pytest tests/test_external_api.py::ExternalApiSchemaValidationTests::test_openapi_contract_exposes_external_api_paths_and_security -q`
- `python -m pytest tests/test_external_temp_emails_api.py::ExternalTempEmailsApiTests::test_external_providers_endpoint_returns_unified_catalog_and_runtime_defaults -q`

## Risk Notes

The main risk is making the smoke checker call a mutable endpoint accidentally. Keep new calls to GET-only discovery endpoints and keep mailbox directory page size small.
