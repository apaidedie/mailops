# External API Integration Action Plan Design

## Boundaries

Primary backend files:

- `outlook_web/services/provider_catalog.py`
- `outlook_web/services/external_api_openapi.py`
- `scripts/external_api_smoke.py`

Primary frontend/docs files:

- `static/js/main.js`
- `static/css/main.css`
- `docs/external-integration-quickstart.md`
- `docs/provider-onboarding.md` if provider-onboarding checklist needs a reference

Primary tests:

- `tests/test_external_api.py`
- `tests/test_external_api_smoke_script.py`
- `tests/test_external_api_docs_page.py` if docs page displays action-plan summary
- `tests/test_settings_tab_refactor_frontend.py` or another existing frontend contract test for Settings -> API Security hooks

## Data Contract

Add `action_plan` to `IntegrationBundleData`:

```json
{
  "version": 1,
  "status": "ready | needs_config | degraded",
  "summary": {
    "total": 0,
    "blocking": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "items": [
    {
      "key": "run_smoke_check",
      "priority": "high | medium | low",
      "status": "ready | action_required | optional | blocked",
      "blocking": false,
      "title": "Run the read-only smoke check",
      "detail": "Validate discovery before mutating mailbox state.",
      "endpoint": "/api/v1/external/integration-bundle",
      "command": "MAILOPS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
      "docs": "docs/external-integration-quickstart.md"
    }
  ]
}
```

All strings must be placeholder-safe. Commands use `<your-api-key>` and `<your-base-url>` only. Provider secret env key names may appear only if already exposed as safe key names by existing discovery metadata; this slice should not add secret key values.

## Generation Rules

Build the action plan inside `provider_catalog.py` close to `_integration_bundle_recommendations` so it can reuse the same inputs:

1. Start with blocking remediation when `status` is `degraded` or `needs_config`.
2. Add provider-configuration action when provider warnings/issues show missing config.
3. Add pool-access or external-pool actions when readiness warnings include the existing restriction markers.
4. Add mailbox-directory probe action when the directory is empty/restricted.
5. Always add smoke-check and OpenAPI client-generation actions.
6. Add start-mailbox-session action only after blocking remediation items, marking it `ready` when bundle status is ready and `blocked` otherwise.
7. Deduplicate by `key` while preserving order.
8. Compute summary counts from final items.

## Frontend Rendering

Render inside the existing external API command center/integration bundle section, not as a separate Settings page.

Add helpers near current bundle rendering functions:

- `getExternalApiActionPlan(settings, state)`
- `renderExternalApiActionPlan(plan)`
- `renderExternalApiActionPlanItem(item)`
- optional copy helper only if a command is rendered with a copy button

The UI should use compact rows/cards:

- priority/status chip
- title/detail
- endpoint/command code line when present
- blocking state indicated by text/chip, not color alone

The UI must avoid nested cards and use stable responsive grid/list constraints. Long command lines should wrap or scroll inside the code block without page-level overflow.

## OpenAPI And Smoke Validation

OpenAPI adds two schemas:

- `IntegrationBundleActionPlan`
- `IntegrationBundleActionItem`

`IntegrationBundleData.required` includes `action_plan`.

Smoke validation checks:

- action plan exists and `version == 1`
- summary counters are non-negative integers and match item shape where practical
- each item has required fields and valid priority/status values
- at least one smoke-check action exists
- ready plans expose a start-session action
- serialized action plan contains no obvious secret values

## Compatibility

`recommendations` remain in place for existing clients. `action_plan` is additive and versioned. Legacy endpoint alias returns the same payload because it already shares the same controller.

## Rollback

Remove `action_plan` from bundle generation, OpenAPI schema, smoke validation, frontend render helpers, CSS hooks, and docs. Existing recommendations and integration bundle fields remain unchanged.
