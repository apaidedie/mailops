# External API command center design

## UI Brief

Audience: developers and operators who want to use Outlook Email Plus from registration workers, automation scripts, or another backend service.

Primary workflow: open Settings -> API Security, confirm external API readiness, copy the correct discovery endpoints or starter command, then adjust API key, provider routing, and pool controls below.

Product archetype: operational SaaS / developer control plane. The page should be dense, precise, and trustworthy rather than decorative.

Constraints: Flask/Jinja template, vanilla JavaScript in `static/js/main.js`, global CSS in `static/css/main.css`, existing i18n helper, no backend or database changes, no new packages, no secret-value exposure.

Source of truth: `/api/settings`, `/api/providers`, cached provider diagnostics/deployment profile/integration guide, and existing external API endpoint constants already documented in README/OpenAPI.

States: loading, provider-catalog unavailable, API key missing, API key configured, multi-key configured, public mode enabled/disabled, external pool enabled/disabled, all providers active, allowlist active, mobile stacked layout.

Acceptance: static contract tests, syntax checks, targeted settings tests, and rendered desktop/mobile Playwright screenshots.

## Data Flow

`loadSettings()` already receives `data.settings` and populates external API controls. A new `renderExternalApiCommandCenter(settings = {}, state = 'ready')` helper will derive status metrics from the same settings object.

`loadMailboxProviderCatalog()` already caches `mailboxProviderDiagnosticsCache`, `mailboxProviderDeploymentProfileCache`, and `mailboxProviderIntegrationGuideCache`. After cache updates or failure, it will call the command-center renderer again using the latest settings snapshot.

To avoid introducing a new global store, keep one lightweight `lastSettingsSnapshot` object that is updated on successful settings load and used only to rerender this read-only command center when provider catalog data arrives later.

## Display Model

The command center has four parts:

- Header: external API service title, short positioning, and readiness badge.
- Metrics: API key, multi-key clients, public mode, external pool, provider readiness, routing mode.
- Endpoint rail: capabilities, OpenAPI, unified mailboxes, providers, pool claim, task temp-mail apply.
- Starter command: a secret-safe curl command using `X-API-Key: <your-api-key>` and the capabilities endpoint, plus one copy button.

The endpoint rail uses constant endpoint paths because these are stable public contract paths in the current backend and README. Provider-specific behavior remains data-driven from provider diagnostics and integration guide; no provider-specific branching belongs here.

## Compatibility

The command center is read-only. It must not replace or mutate existing external API settings fields. It must not call external endpoints from the browser with API keys. It may use same-origin settings/provider payloads already available in the authenticated admin session.

## Rollback

Rollback removes the template mount, JS helper/state/calls, CSS classes, i18n entries, tests, and task artifacts.
