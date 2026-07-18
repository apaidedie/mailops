# Implementation Plan

## Steps

1. Add failing unit tests for config normalization, text/JSON formatting, safe request context, exception fields, safe structured extras, and duplicate-handler prevention.
2. Add an app-factory integration test proving `current_app.logger` emits request trace context through the shared handler.
3. Implement `LOG_FORMAT`, `LOG_LEVEL`, and backward-compatible `PERF_LOGGING` helpers in `mailops/config.py`.
4. Add `mailops/logging_config.py` with managed handler setup, request context filter, text formatter, and JSON formatter.
5. Replace inline logging setup in `mailops/app.py` with the shared configurator.
6. Update `.env.example`, runtime documentation, readiness checks/tests, and `docs/项目地图.md`.
7. Run focused tests, relevant app/error/security regressions, readiness gate, formatter/import/lint checks, and `git diff --check`.

## Validation Commands

`python -m unittest tests.test_logging_config tests.test_project_readiness_check tests.test_security_headers -v`

`python scripts/project_readiness_check.py`

`black --check mailops/logging_config.py mailops/config.py mailops/app.py tests/test_logging_config.py tests/test_project_readiness_check.py`

`isort --check-only --diff --profile black mailops/logging_config.py mailops/config.py mailops/app.py tests/test_logging_config.py tests/test_project_readiness_check.py`

`flake8 mailops/logging_config.py mailops/config.py mailops/app.py tests/test_logging_config.py tests/test_project_readiness_check.py --count --select=E9,F63,F7,F82 --show-source --statistics`

`git diff --check`

## Risk And Rollback Points

- Avoid Flask app logger propagation loops or duplicate lines.
- Do not access `request`/`g` outside an active request context.
- Keep JSON serialization resilient to non-JSON-safe `extra` values by exposing only a safe field allowlist.
- Preserve text output and `PERF_LOGGING` behavior for existing deployments.
