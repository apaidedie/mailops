# External message read OpenAPI contract implementation plan

## Checklist

1. Add failing schema assertions in tests/test_external_api.py for typed external read OpenAPI schemas and raw endpoint response refs.
2. Run targeted OpenAPI test and confirm it fails because schemas are loose or missing.
3. Update outlook_web/services/external_api_openapi.py schemas and response refs.
4. Update .trellis/spec/backend/provider-selection-contract.md with the typed read-contract requirement and tests.
5. Run focused and relevant regression checks.
6. Commit, archive task, and record journal.

## Validation Commands

- python -m pytest tests/test_external_api.py -q -rs -k "openapi_contract_exposes_external_api_paths_and_security"
- python -m pytest tests/test_external_api.py -q -rs
- python -m py_compile outlook_web/services/external_api_openapi.py
- git diff --check
- Run the repository secret scan pattern used by recent external API tasks.

## Risk

- If runtime payloads vary by provider, schemas should allow additionalProperties rather than rejecting existing fields.
- Do not add secret-looking fixture values to schema examples.
