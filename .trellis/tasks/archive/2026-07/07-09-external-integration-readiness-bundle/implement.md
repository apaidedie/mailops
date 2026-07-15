# External Integration Readiness Bundle Implementation Plan

## Checklist

1. Extend external endpoint maps with `integration_bundle` for canonical and legacy routes.
2. Add `get_external_api_integration_bundle()` to `provider_catalog.py`, composing existing capabilities/readiness/manifest contracts and optional OpenAPI metadata.
3. Add an authenticated controller route and shared route registration for `/api/external/integration-bundle` and `/api/v1/external/integration-bundle`.
4. Update OpenAPI schemas and paths with typed `IntegrationBundleData` and canonical path only.
5. Update the generated docs page to surface the integration bundle as a first-step readiness artifact.
6. Update `scripts/external_api_smoke.py` to fetch and validate the bundle.
7. Update Python and JavaScript starter clients so `integration-bundle` prefers the live endpoint and falls back to local assembly when unavailable.
8. Add or update tests for API contract, OpenAPI/docs, smoke script, and starter clients.

## Validation Commands

```powershell
python -m pytest tests\test_external_api.py tests\test_external_api_docs_page.py tests\test_external_api_smoke_script.py -q
python -m pytest tests\test_external_api_python_client.py -q
npm run test:external-api-js-client
python scripts\project_readiness_check.py
git diff --check
```

If docs layout changes materially, start the Flask app and run desktop/mobile browser overflow checks against `/api/v1/external/docs`.

## Rollback Points

- Route and endpoint-map changes are tightly coupled; if the route fails auth/alias tests, revert both together.
- OpenAPI schema/path changes can be reverted independently if runtime endpoint behavior is correct but documentation generation regresses.
- Starter client live-bundle preference can fall back to existing local assembly if live endpoint compatibility creates test failures.
