# Provider integration guide UI design

## Boundaries

This task is a frontend consumption layer for an existing backend contract. `/api/providers` remains the single data source for provider catalog, diagnostics, deployment templates, and integration guide data. No provider selection, config-file, OpenAPI, or external API behavior changes are planned.

## UI Brief

Audience: authenticated administrators and developers wiring this service into other projects.

Primary workflow: open Settings, review provider readiness and deployment/call knobs, copy a safe provider-specific snippet.

Product archetype: operational SaaS. The UI should stay compact, text-dense, and scan-friendly instead of becoming a marketing panel.

Constraints: Flask/Jinja template, vanilla JavaScript, existing CSS tokens and card patterns, no new packages, no secret value exposure, responsive behavior for narrow settings panes.

States: loading, unavailable, empty provider filter, ready, inactive, needs_config, copy success, copy failure.

Acceptance: static frontend contract tests plus targeted provider/API tests. Browser verification should be attempted if the app can be launched cheaply.

## Data Flow

`GET /api/providers` returns `provider_integration_guide`. `loadMailboxProviderCatalog()` stores it in a new cache and calls `renderProviderIntegrationGuide()`. The renderer reads guide summary fields and `guide.providers`, filters entries by local UI state, formats examples into compact rows, and leaves provider semantics owned by backend payload fields.

The copy action reads the selected guide provider entry and generates a `.env` snippet. It uses env examples exposed under activation/default steps and configuration env defaults. Any env key listed in `secret_env` is emitted with an empty value, even if a future payload accidentally includes a default.

## Compatibility

Existing provider console filters, health probing, deployment template tabs, plugin provider config, and settings save/load logic remain intact. The guide sits between deployment templates and provider console so it complements existing status/diagnostic UI instead of replacing it.

GPTMail aliases stay visible as aliases for `legacy_bridge`. The label can remain user-friendly, but the internal provider key and alias map are not rewritten.

## Rollback

Rollback is limited to removing the UI mount, cache variable, render/copy helpers, CSS classes, and frontend tests. Backend contracts are unchanged.
