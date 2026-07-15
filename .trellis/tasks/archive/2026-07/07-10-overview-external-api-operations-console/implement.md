# Implementation Plan

## Steps

1. Extend `get_external_api_stats()` aggregation with endpoint health, caller error metrics, and health summary while preserving existing fields.
2. Add repository/API tests for populated and empty enriched schema.
3. Update `renderExternalApiStats()` to render health strip, endpoint health, and enriched caller ranking.
4. Add CSS hooks for operation strip, endpoint rows, and responsive table behavior using existing tokens.
5. Add frontend contract assertions for helper names, labels, CSS hooks, forbidden secret references, and i18n strings.
6. Run focused checks and fix regressions.
7. Run browser QA against desktop and mobile viewports with seeded usage data.
8. Run readiness check, commit task changes, archive the task, and record journal.

## Validation Commands

- `node --check static/js/features/overview.js`
- `python -m pytest tests/test_overview_repository.py -q`
- `python -m pytest tests/test_overview_api.py -q`
- `python -m pytest tests/test_overview_frontend_contract.py -q`
- `python scripts/project_readiness_check.py --format json`
- `git diff --check`

## Browser QA

- Start the Flask app with an isolated QA database.
- Seed `external_api_consumer_usage_daily` with healthy, degraded, and idle-ish caller/endpoint rows.
- Login, open Dashboard -> External API.
- Verify desktop viewport around 1440x900 and mobile viewport around 390x844.
- Record page overflow and `#ov-external-api-body` overflow.

## Risk Points

- Date column compatibility: rows may use `usage_date` or legacy `date`.
- Numeric compatibility: rows may use `total_count` or `call_count`.
- UI tables must escape caller/endpoint names.
- Responsive tables may intentionally scroll inside `.data-table-shell`, but the page and overview body must not overflow unexpectedly.
