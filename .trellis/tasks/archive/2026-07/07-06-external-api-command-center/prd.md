# External API command center

## Goal

Turn the Settings -> API Security page into a professional entry point for using Outlook Email Plus as an external mailbox aggregation service. The first screen should explain external readiness, authentication, provider routing, and machine-readable integration endpoints without forcing users to scan several disconnected configuration blocks.

## Background

The backend already exposes external API capabilities, OpenAPI discovery, unified mailbox directory metadata, provider diagnostics, provider selection policy, deployment templates, provider integration guides, and external pool controls. The current settings UI exposes the raw controls, but the page still reads like a long settings form. For developers integrating this service into another project, the page should behave like a command center: read status, copy the right endpoint, understand provider routing, then adjust settings.

Evidence from the codebase:

- `templates/index.html` contains the API Security tab with external API key controls, multi-key JSON, public mode, external pool controls, provider diagnostics, deployment templates, provider integration guide, and provider console.
- `static/js/main.js` already loads `/api/settings` and `/api/providers`, caches `provider_diagnostics`, `deployment_profile`, and `provider_integration_guide`, and renders provider template / guide / console sections.
- `README.md` and `README.en.md` document `/api/external/capabilities`, `/api/external/openapi.json`, `/api/external/mailboxes`, provider selection priority, and environment/config-file activation.
- The UI stack is Flask/Jinja, vanilla JavaScript, and `static/css/main.css`. No new framework or component library should be introduced.

## Requirements

Add an `externalApiCommandCenter` section at the top of the API Security tab, before the API key form fields. It must be read-only and data-driven from already-loaded settings and provider catalog payloads.

The command center must summarize external access state, multi-key coverage, public-mode posture, pool endpoint state, provider route mode, provider readiness, and the primary integration endpoints: `/api/external/capabilities`, `/api/external/openapi.json`, `/api/external/mailboxes`, `/api/external/providers`, `/api/external/pool/claim-random`, and `/api/external/temp-emails/apply`.

The command center must make the recommended external integration path obvious: discover capabilities, read OpenAPI, list unified mailboxes, choose provider routing with env/config/settings, and call pool/task temp-mail endpoints as needed.

The UI must remain operational SaaS: compact, calm, scan-friendly, responsive, token-compatible, and free of decorative hero treatment. The existing API key fields, JSON editor, public-mode controls, provider diagnostics, deployment templates, provider integration guide, provider console, and pool disable toggles must keep working.

Do not change backend provider selection rules, API security behavior, database schema, external API contracts, or temp-mail provider implementations in this slice. Do not expose secret values. Do not write real user tokens into source, logs, tests, or docs.

## Acceptance Criteria

- `templates/index.html` includes `id="externalApiCommandCenter"` inside the API Security tab before `settingsExternalApiKey`.
- `static/js/main.js` renders the command center after `/api/settings` loads and after `/api/providers` loads or fails.
- Rendering is data-driven from `data.settings`, `mailboxProviderDiagnosticsCache`, `mailboxProviderDeploymentProfileCache`, and `mailboxProviderIntegrationGuideCache`.
- The command center shows API key status, multi-key count, public mode state, pool external state, provider readiness, active routing mode, source priority, and the external endpoint map.
- The command center includes a copyable curl-style starting command or endpoint bundle that never includes real API key values; placeholders are acceptable.
- CSS provides stable desktop and mobile layouts with no nested cards, no horizontal overflow, and readable long endpoint text.
- i18n includes all new visible labels.
- Frontend contract tests cover the mount, JS renderer/helpers/calls, CSS hooks, i18n strings, and secret-safe copy behavior.
- Browser verification covers desktop and mobile rendering of the API Security tab.
- Targeted syntax and frontend/settings tests pass.

## Out Of Scope

No provider implementation changes, database changes, API contract changes, new docs site, new component library, new animation framework, full settings-page redesign, or GitHub README rewrite is included in this slice.
