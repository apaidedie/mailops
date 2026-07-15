# Overview External API Operations Console Design

## Boundaries

- Backend ownership stays in `outlook_web/repositories/overview.py`; the controller and routes remain thin.
- Frontend ownership stays in `static/js/features/overview.js` and the existing Overview section of `static/css/main.css`.
- Template mount points in `templates/index.html` remain unchanged unless a missing accessibility hook is discovered.
- The feature consumes existing `external_api_consumer_usage_daily` data only. It does not create new persistence or call upstream providers.

## Data Flow

`external_api_consumer_usage_daily` -> `overview_repo.get_external_api_stats()` -> `/api/overview/external-api` -> `renderExternalApiStats()` -> `#ov-external-api-body`.

Repository normalization owns numeric coercion, date-window filtering, caller aggregation, endpoint aggregation, and health summary derivation. The frontend owns display formatting only.

## API Contract

The response keeps existing top-level fields:

- `kpi.today_calls`
- `kpi.week_calls`
- `kpi.today_vs_yesterday_rate`
- `kpi.success_rate`
- `kpi.error_count`
- `kpi.active_callers`
- `daily_series[]`
- `by_endpoint[]`
- `caller_rank[]`

New safe fields:

- `kpi.error_rate`: `week_errors / week_calls`.
- `health`: `{status, label, risk_count, top_error_endpoint, top_error_caller}`.
- `endpoint_health[]`: each row has `{endpoint, count, success_count, error_count, success_rate, error_rate, rate, last_used_at, last_status}`.
- `caller_rank[]` gains `{error_count, error_rate, endpoint_count, last_status}` while preserving existing row keys.

`health.status` is derived locally:

- `idle` when `week_calls == 0`.
- `attention` when error rate is at least 10% or any caller has at least 5 errors.
- `healthy` otherwise.

## Secret Safety

Do not add any secret-bearing fields. The repository reads usage metadata only. The UI may show `consumer_key` because the existing overview already exposes that safe aggregation identifier, but it must never read Settings credential inputs or render `api_key`, `api_key_masked`, bearer tokens, task tokens, claim tokens, passwords, JWTs, refresh tokens, or provider secret values.

## Frontend Layout

- Keep the KPI row as the first scan surface.
- Add a compact operations strip for health status, top error endpoint, top error caller, and 7-day error count.
- Keep the 7-day bar chart and endpoint distribution in a two-column grid.
- Replace the simple endpoint progress list with endpoint health rows that include success/error rates.
- Expand caller table to show calls, success rate, error rate, endpoint count, status, and last used.
- Use existing `renderDataCard`, `renderProgressBlock`, `renderTable`, and badge helpers where possible; add small helpers only when they reduce duplication.

## Compatibility

- Existing tests expecting `kpi`, `daily_series`, `caller_rank`, and `by_endpoint` continue to pass.
- Empty datasets return zero counts and empty arrays, plus `health.status = idle`.
- Old rows that have only `date`/`call_count` still work through the existing fallback logic.

## UI Art Direction

Operational SaaS: compact, clear hierarchy, restrained semantic color. No marketing hero, no structural emoji, no one-off palette, no nested decorative cards. The visual emphasis is on risk signals and scanability.

## Rollback

Rollback is limited to reverting the repository projection, overview renderer/CSS, and focused tests. No schema migration or external route contract changes are involved.
