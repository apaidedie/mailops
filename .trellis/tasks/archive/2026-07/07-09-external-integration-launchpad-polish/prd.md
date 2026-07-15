# External integration launchpad polish

## Goal

Make the Settings -> API Security external access command center feel like a practical launchpad for operators and third-party developers who want to integrate with this unified Outlook/IMAP/temp-mail aggregation service.

The launchpad should surface the already-implemented integration readiness bundle as the primary discovery path, explain the canonical and legacy paths, expose a safe copy command, and keep the existing provider readiness, quickstart, smoke-check, workflow, and mailbox-session panels intact.

## Background

- The backend already exposes a secret-safe `GET /api/v1/external/integration-bundle` endpoint with legacy alias `GET /api/external/integration-bundle`.
- Capabilities, OpenAPI, first-party docs, smoke scripts, starter clients, and readiness checks already know about the bundle.
- The Settings -> API Security command center currently shows onboarding, smoke checks, readiness, quickstart, mailbox sessions, endpoints, snippets, provider recipes, and workflow playbooks.
- The command center does not yet make the live integration bundle visibly central in the admin UI, so an operator still has to infer that it is the best first endpoint for external services.
- The project UI stack is Flask templates plus vanilla JavaScript/CSS. No frontend framework or component library was detected.

## Requirements

- Add a first-class launchpad panel inside `#externalApiCommandCenter` that presents the integration bundle as the recommended one-stop discovery payload.
- The panel must show the canonical bundle endpoint, legacy alias, placeholder auth header, and a concise readiness summary drawn from existing settings/provider/readiness caches.
- The panel must include a copy action for a safe command using `X-API-Key: <your-api-key>` and the current base URL placeholder. It must never copy or render real API keys or provider credential values.
- The command center endpoint list and smoke-check coverage must include the integration bundle endpoint so the UI matches the backend discovery contract.
- The implementation must remain provider-agnostic. Do not add frontend branches for built-in providers such as DuckMail, Mail.tm, TempMail.lol, Emailnator, GPTMail, Outlook, or IMAP.
- The UI must preserve existing command-center panels and render order: onboarding and smoke checks remain early; the new bundle launchpad should appear before detailed operational readiness and quickstart material.
- The layout must be responsive and avoid horizontal overflow for long endpoint paths, copy commands, translated labels, and narrow mobile Settings panes.
- Visible strings must be translated through `static/js/i18n.js`.

## Out Of Scope

- Adding new backend discovery fields or changing external API auth behavior.
- Fetching the API-key protected external bundle from the admin browser with a real API key.
- Rebuilding provider selection/readiness rules in JavaScript.
- Adding a new frontend framework, icon library, or component system.

## Acceptance Criteria

- [ ] The command center renders an integration bundle launchpad panel with canonical endpoint `/api/v1/external/integration-bundle`, legacy alias `/api/external/integration-bundle`, placeholder auth, and safe copy action.
- [ ] The launchpad summary is computed from existing `settings`, provider catalog/manifest, and mailbox readiness caches without reading credential input elements.
- [ ] The command center endpoint list and smoke coverage include the `integration_bundle` discovery endpoint.
- [ ] Copy handlers exist for the new launchpad command and copy only placeholder credentials.
- [ ] CSS hooks exist for the launchpad panel, summary grid, endpoint rows, command block, and mobile collapse; long text wraps without page-level horizontal overflow.
- [ ] i18n entries exist for all new visible UI strings.
- [ ] Frontend contract tests cover render order, secret-safety, provider-agnostic behavior, copy hooks, endpoint coverage, CSS hooks, and translations.
- [ ] Existing external API/backend contract tests continue to pass where relevant.

## UI Brief

- Audience: operators configuring the app and developers integrating another service with its mailbox API.
- Primary workflow: find the correct first endpoint, copy a safe read-only discovery command, and understand whether the service is ready enough to integrate.
- Product archetype: operational SaaS dashboard, dense but calm.
- Constraints: Flask templates, vanilla JS/CSS, existing Settings tab and command-center visual system, mobile-safe Settings card body.
- Source of truth: existing backend integration bundle contract, provider catalog caches, frontend quality guidelines, and current command-center components.
- States: loading, provider catalog degraded, missing API key, ready, mobile/narrow layout, copy success/failure.
- Acceptance: focused frontend contract tests plus targeted external API/docs tests; rendered browser QA if local tooling is available.
