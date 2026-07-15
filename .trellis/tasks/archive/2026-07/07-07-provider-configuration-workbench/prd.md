# Provider configuration workbench

## Goal

Make Settings -> API Security easier to audit by turning the scattered provider controls, diagnostics, deployment templates, integration guide, and provider console into one coherent provider configuration workbench.

The workbench must help an administrator quickly understand provider routing mode, default claim provider, readiness counts, provider-config-file state, source priority, and secret-display policy without reading provider secret inputs or changing backend selection behavior.

## Requirements

- Add a provider workbench container in the API Security external pool area that groups the existing provider settings, diagnostics, deployment templates, integration guide, and provider console.
- Add a compact read-only overview inside that container. It should summarize the current routing mode, default pool claim provider, readiness totals, provider-config-file state, source priority, and secret policy from existing settings and `/api/providers` catalog payloads.
- Reuse existing frontend caches and helpers where possible: `externalApiSettingsSnapshot`, `mailboxProviderDiagnosticsCache`, `mailboxProviderDeploymentProfileCache`, `mailboxProviderIntegrationGuideCache`, route-mode helpers, source-priority helpers, and pool-status helpers.
- Keep the frontend secret-free. The overview must not read `#settingsExternalApiKey`, `#settingsExternalApiKeysJson`, provider credential inputs, masked placeholders, or any plaintext key/token input.
- Preserve backend provider contracts, aliases, provider selection priority, and public discovery payloads. No backend provider selection behavior changes are in scope.
- Keep the UI dense, operational, responsive, and aligned with the existing Flask/Jinja + vanilla JS + CSS token system. Do not introduce a new frontend framework, icon library, or marketing-style layout.
- Keep copy helpers secret-safe. Any exported snippets should continue to show key names or placeholders only, never real key values.

## Acceptance Criteria

- `templates/index.html` contains a provider workbench wrapper and a dedicated overview mount before the detailed diagnostics/templates/guide/console sections.
- `static/js/main.js` defines and calls a `renderProviderWorkbench()` render path after settings load, provider catalog success, provider catalog failure, and UI language changes.
- `renderProviderWorkbench()` consumes existing settings/catalog caches and does not reference secret input IDs such as `settingsExternalApiKey`, `settingsExternalApiKeysJson`, `settingsDuckmailBearerToken`, or `settingsEmailnatorApiKey`.
- `static/css/main.css` defines responsive provider workbench styles with stable grid sizing and long-text wrapping for provider names, file paths, and source-priority strings.
- Frontend contract tests assert the new mounts, render calls, secret-safety constraints, and CSS hooks.
- Existing settings/provider regression tests continue to pass.
- Static scans find no production `console.log`/`console.debug` and no committed DuckMail bearer token value.

## Out of Scope

- Changing provider selection priority, provider aliases, database schema, provider factory behavior, external API request fields, or OpenAPI schemas.
- Persisting, displaying, copying, logging, or testing with real API keys, bearer tokens, passwords, JWTs, task tokens, or consumer keys.
- Redesigning the whole Settings page or introducing a new component system.
