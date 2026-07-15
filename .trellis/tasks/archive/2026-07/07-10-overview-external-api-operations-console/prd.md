# Overview external API operations console

## Goal

Turn the Dashboard -> External API tab into an operational console for external API consumers. Operators should be able to see whether the integration surface is healthy, which callers are active, which endpoints are noisy, and where errors are concentrated without opening Settings or inspecting raw database rows.

This moves the project toward a professional unified mailbox aggregation service by making the external API surface observable after other services begin using it.

## Confirmed Facts

- The authenticated Overview dashboard already has an `external-api` tab mounted at `#ov-external-api-body` in `templates/index.html`.
- `/api/overview/external-api` is served by `overview_repo.get_external_api_stats()` and currently returns `kpi`, `daily_series`, `by_endpoint`, and `caller_rank`.
- External API consumer usage is stored in `external_api_consumer_usage_daily` with safe operational fields: `consumer_key`, `consumer_name`, `caller_id`, `usage_date`/`date`, `endpoint`, counts, `last_status`, and `last_used_at`.
- Settings already has a per-consumer usage console. This task should not duplicate secret-management UI or expose API keys.
- The main frontend is Flask templates plus plain JavaScript/CSS. No new frontend framework or component library should be introduced.

## UI Brief

- Audience: operator/developer managing external services that consume Outlook/temp-mail aggregation APIs.
- Primary workflow: scan API health, identify active/erroring callers, inspect endpoint distribution, and decide whether an integration needs attention.
- Product archetype: dense operational SaaS dashboard.
- Constraints: use existing Overview CSS tokens/components, no structural emoji, no nested decorative cards, no secrets, mobile and desktop must avoid page/container overflow.
- States: loading, empty, populated, degraded/error counts, responsive desktop/mobile tables and metric blocks.

## Requirements

- R1. Enrich `/api/overview/external-api` with safe operational projections beyond coarse totals:
  - rolling 7-day KPI stays backward compatible;
  - per-endpoint totals include success/error counts and error rate;
  - per-caller rows include week calls, today calls, success/error counts, error rate, success rate, endpoint count, last status, and last used time;
  - provide a compact `health` summary with status and top risk signals.
- R2. The API response must remain secret-safe. It must not include plaintext API keys, masked API-key placeholders, bearer tokens, task tokens, claim tokens, provider secret values, or external consumer key values beyond the existing safe `consumer_key` identifier already used for usage aggregation.
- R3. The Overview external API tab must render a professional operations surface:
  - KPI row for calls, trend, success/error posture, and active callers;
  - trend chart preserved;
  - endpoint health panel with error-rate visibility;
  - caller health/ranking table with safe identifiers and status badges;
  - clear empty state when no usage exists.
- R4. Frontend rendering must normalize optional API fields and escape dynamic strings before `innerHTML` insertion.
- R5. The UI must preserve the existing operational visual language: restrained tokens, dense layout, stable dimensions, no decorative hero treatment, no structural emoji, no hover-only explanatory copy.
- R6. Tests must prove the enriched repository/API schema, frontend contract hooks, i18n labels, and secret-safety constraints.
- R7. Browser QA must verify desktop and mobile rendered layouts for page-level and `#ov-external-api-body` overflow.

## Acceptance Criteria

- [ ] `get_external_api_stats()` returns backward-compatible keys plus enriched `health`, `endpoint_health`, and enriched `caller_rank` fields for seeded data.
- [ ] `/api/overview/external-api` returns the enriched schema to authenticated users and still returns 401 unauthenticated.
- [ ] Overview JS renders endpoint health and caller operations with escaped dynamic strings and no references to Settings secret input IDs.
- [ ] Overview CSS contains stable, responsive hooks for the new operations surface and does not introduce forbidden decorative patterns.
- [ ] Focused tests pass: `tests/test_overview_repository.py`, `tests/test_overview_api.py`, `tests/test_overview_frontend_contract.py`.
- [ ] Static JS syntax check passes for `static/js/features/overview.js`.
- [ ] Project readiness check remains green.
- [ ] Browser QA confirms desktop and mobile external API overview layouts have no page-level or container-level horizontal overflow.

## Out Of Scope

- Do not add a new external API endpoint or change existing external API auth/route behavior.
- Do not add a charting library.
- Do not redesign the whole dashboard navigation in this task.
- Do not expose or manage API secrets in Overview.
