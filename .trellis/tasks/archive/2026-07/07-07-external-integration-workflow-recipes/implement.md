# External integration workflow recipes implementation plan

## Steps

1. Inspect the current manifest builder, endpoint map, read contract helper, OpenAPI schema generation, and existing external API tests.
2. Add provider-catalog helpers that build secret-safe workflow recipe objects from the existing endpoint map, selection policy scopes, and read contracts.
3. Attach `workflows` to `integration_manifest` without changing existing manifest fields.
4. Add OpenAPI component schemas for manifest workflows and steps, then reference them from `IntegrationManifest`.
5. Update backend tests for capabilities, provider catalog payloads, OpenAPI schema exposure, workflow request field derivation, read step coverage, and secret-safety.
6. Update the provider selection spec if the new manifest field becomes a durable contract.
7. Run targeted tests, syntax checks if applicable, diff check, debug console scan, and DuckMail token scan.

## Validation Commands

- `python -m pytest tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_multi_mailbox.py -q`
- `python -m pytest tests/test_unified_mailbox_catalog.py tests/test_external_temp_emails_api.py tests/test_external_api.py -q`
- `git diff --check`
- `rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml mailops`

## Risk Points

- OpenAPI component tests are strict about required fields and schema refs.
- Workflow endpoint literals can drift if they are not derived from the existing endpoint map/read contract helpers.
- Secret-safety tests must distinguish allowed key names from forbidden secret values.
- Additive manifest fields should not break frontend starter-kit fallback behavior.
