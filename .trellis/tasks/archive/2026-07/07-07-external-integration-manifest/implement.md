# External integration manifest implementation plan

## Steps

1. Read `provider_catalog.py`, external providers controllers, capabilities tests, and OpenAPI schema generation to locate the canonical insertion points.
2. Add a manifest builder in `provider_catalog.py` that consumes the current guide, selection policy, deployment profile, diagnostics, endpoint map, and provider filter.
3. Include the manifest in `get_external_api_capabilities_contract()` and provider catalog discovery payloads without altering existing fields.
4. Extend OpenAPI schemas with `IntegrationManifest` and related provider/auth/discovery/config structures, and wire it into `CapabilitiesData` plus provider catalog data schemas.
5. Add tests for capabilities, providers, OpenAPI schema exposure, provider key hints, alias preservation, and secret-safety.
6. Update backend spec with the manifest contract.
7. Run syntax, pytest target suites, diff check, debug scan, and DuckMail token scan.

## Validation Commands

- `python -m pytest tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_multi_mailbox.py -q`
- `python -m pytest tests/test_temp_mail_target_contract.py tests/test_temp_mail_settings_platform_contract.py tests/test_external_api_temp_mail_compat.py tests/test_external_temp_emails_api.py -q`
- `git diff --check`
- `rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml mailops`

## Risk Points

- OpenAPI `CapabilitiesData.required` tests are strict and must be updated when the manifest becomes required.
- `/api/providers` and `/api/external/providers` should not drift; use the same manifest builder inputs where possible.
- Secret-safety tests must verify both service payload and OpenAPI `x-capabilities` do not expose token values.
