# Implementation Plan

## Steps

1. Add failing tests for origin normalization/rejection, default extension behavior, configured web origins, extension disable, internal-route isolation, headers, and canonical/legacy paths.
2. Add failing capabilities/readiness tests for the safe CORS contract.
3. Implement config parsing/validation in `outlook_web/config.py`.
4. Add `outlook_web/cors_config.py` and replace inline app-factory CORS setup.
5. Add the safe contract to provider capabilities and readiness.
6. Update `.env.example`, runtime readiness, external quickstart, readiness checks/tests, CI path triggers, and project map.
7. Run focused tests plus external API/readiness/security regressions, readiness gate, format/import/lint/type checks, and `git diff --check`.

## Validation Commands

`python -m unittest tests.test_external_api_cors tests.test_security_headers tests.test_external_api tests.test_project_readiness_check -v`

`python scripts/project_readiness_check.py`

`black --check outlook_web/cors_config.py outlook_web/config.py outlook_web/app.py outlook_web/services/provider_catalog.py tests/test_external_api_cors.py tests/test_project_readiness_check.py`

`isort --check-only --diff --profile black outlook_web/cors_config.py outlook_web/config.py outlook_web/app.py outlook_web/services/provider_catalog.py tests/test_external_api_cors.py tests/test_project_readiness_check.py`

`flake8 outlook_web/cors_config.py outlook_web/config.py outlook_web/app.py outlook_web/services/provider_catalog.py tests/test_external_api_cors.py tests/test_project_readiness_check.py --count --select=E9,F63,F7,F82 --show-source --statistics`

`mypy --config-file pyproject.toml outlook_web/cors_config.py outlook_web/config.py outlook_web/app.py outlook_web/services/provider_catalog.py`

`git diff --check`

## Risk And Rollback Points

- Flask-CORS origin matching must echo only approved origins and never widen internal APIs.
- Do not let discovery import the Flask app or create circular imports.
- Invalid entries must stay inactive and secret-safe.
- Keep API-key authentication tests green; CORS is not authorization.
