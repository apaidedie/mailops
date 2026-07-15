# Technical Design

## Boundaries

- Backend owner: `outlook_web.controllers.overview.api_get_overview_summary` composes the existing repository KPI summary with a service-owned command-center projection.
- Dashboard SQL owner: `outlook_web.repositories.overview.get_overview_summary` remains SQL-only and must not import services.
- Command-center projection owner: `outlook_web.services.overview_command_center.get_overview_command_center` builds the mailbox/provider/external-readiness summary from existing service contracts.
- Provider readiness source of truth: `outlook_web.services.provider_catalog.get_mailbox_directory_provider_context` and `get_external_api_readiness_summary`.
- Mailbox inventory source of truth: `outlook_web.services.mailbox_catalog.list_unified_mailboxes(page=1, page_size=1)` and its existing `summary`, `pagination`, `facets`, and `provider_context` fields.
- Frontend owner: `static/js/features/overview.js` renders the dashboard summary tab and consumes only `/api/overview/summary`.
- Styling owner: the existing Overview Dashboard CSS block in `static/css/main.css`.

## Backend Contract

Add `command_center` to `/api/overview/summary`:

```json
{
  "overall_status": "ready|needs_config|degraded|empty|unknown",
  "mailbox_inventory": {
    "status": "ready|empty|degraded",
    "total": 0,
    "account": 0,
    "temp": 0,
    "providers": 0
  },
  "provider_readiness": {
    "status": "ready|needs_config|degraded|unknown",
    "ready": 0,
    "active": 0,
    "needs_config": 0,
    "dynamic_create": 0,
    "temp_providers": 0,
    "account_providers": 0
  },
  "external_api": {
    "status": "ready|needs_config|degraded|restricted|unknown",
    "discovery_status": "available|unavailable|unknown",
    "mailbox_directory_status": "ready|empty|restricted|degraded|unknown",
    "task_temp_mailbox_status": "ready|needs_config|restricted|unknown",
    "pool_status": "ready|disabled|restricted|degraded|unknown",
    "integration_bundle_endpoint": "/api/v1/external/integration-bundle"
  },
  "actions": [
    {"key": "...", "label": "...", "detail": "...", "target": "...", "priority": "high|medium|low", "status": "ready|needs_config|degraded|neutral"}
  ]
}
```

The backend catches command-center projection failures and returns a degraded command-center object instead of failing the entire overview summary.

## Data Flow

1. `get_overview_summary` keeps existing SQL KPI aggregation.
2. A service helper builds command-center data from `list_unified_mailboxes(page_size=1)` plus provider readiness and external API readiness contracts.
3. The overview controller attaches `command_center` to the SQL summary and caches the whole summary object with the existing 30 second TTL.
4. `renderOverviewSummary` renders `renderOverviewCommandCenter(data.command_center || {})` before the existing KPI grid.

## UI Direction

- Product archetype: operational SaaS / data-dense dashboard.
- First viewport job: quickly tell whether the unified mailbox service can serve account mailboxes, temp-provider mailboxes, and external consumers.
- Visual model: restrained token surfaces, compact status cards, no marketing hero.
- Responsive model: command-center cards collapse to one column on narrow screens, action rows wrap without changing control height unpredictably.

## Safety

- The command-center payload contains no tokens, API key values, bearer values, or raw settings.
- External API endpoint paths and documentation paths are safe to expose.
- Provider readiness remains local configuration based; no upstream probes are started by dashboard loading.

## Rollback

- Remove `command_center` helper and field from `overview.py`.
- Remove `renderOverviewCommandCenter` calls and CSS classes.
- Existing summary KPI cards remain unchanged and can continue using current fields.
