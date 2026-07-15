# Implementation Plan

## Steps

1. Add failing external API tests for capabilities/providers/admin providers quickstart exposure, selector derivation, OpenAPI schemas, and secret-safety.
2. Add a provider-catalog helper that builds `integration_manifest.quickstart` from endpoints and selection policy.
3. Expose top-level `quickstart` from capabilities and provider discovery payloads by reusing `integration_manifest.quickstart`.
4. Update OpenAPI schemas for `IntegrationQuickstart` and references from capabilities/provider catalog/manifest.
5. Update provider onboarding docs and provider-selection spec with the quickstart contract.
6. Run focused external API tests, syntax checks, and diff checks.

## Validation Commands

```powershell
python -m pytest tests/test_external_api.py -q -rs
python -m py_compile outlook_web\services\provider_catalog.py outlook_web\services\external_api_openapi.py outlook_web\controllers\external_temp_emails.py outlook_web\controllers\accounts.py
git diff --check
```

## Rollback

Remove the quickstart helper, response fields, OpenAPI schemas, tests, and spec/doc updates. Existing integration manifest, workflows, providers, and endpoint discovery remain unchanged.
