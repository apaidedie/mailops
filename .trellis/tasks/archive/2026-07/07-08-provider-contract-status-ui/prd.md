# Provider Contract Status UI

## Goal

Make temp-mail provider extension readiness visible in the authenticated settings workflow. Operators and plugin authors should be able to see which providers pass the extension contract, which providers have warnings/errors, and what issue codes need attention without reading raw JSON payloads.

## User Value

- New mailbox providers can be reviewed from the UI before they are used by external API clients or runtime mailbox workflows.
- Secret-handling mistakes such as default bearer/API-key values become visible as contract issues while still staying redacted.
- The settings page becomes a stronger control plane for the unified mailbox aggregation service, not only a collection of provider toggles.

## UI Brief

- Audience: operators and developers maintaining Outlook/IMAP accounts, temp-mail providers, plugins, and external API access.
- Primary workflow: scan provider extension health, focus invalid/warning providers, and copy no secrets.
- Product archetype: operational SaaS admin surface; dense, calm, contract-driven, no marketing hero.
- Constraints: existing server-rendered template, vanilla JavaScript, existing CSS tokens/patterns, no new dependency.
- Source of truth: `/api/providers` `mailbox_providers` / `provider_integration_guide`, `/api/plugins`, and existing provider contract tests/specs.
- Required states: loading, empty, valid, warning, invalid, unknown, hover/focus, mobile wrapping.
- Acceptance: frontend contract tests and provider/plugin API tests cover the rendered mount, JS helpers, secret-safety, and propagation.

## Confirmed Facts

- `GET /api/providers` now attaches `contract_validation` to temp provider catalog entries, provider integration guide entries, and integration manifest providers.
- `GET /api/plugins` includes compact contract validation state for loaded temp-mail provider plugins.
- `GET /api/plugins/<name>/contract` returns full secret-free provider contract validation for one loaded plugin.
- Existing settings UI already fetches `/api/providers` through `loadMailboxProviderCatalog()` and renders provider diagnostics, deployment templates, provider console, and integration guide surfaces in `static/js/main.js`.
- Frontend quality guidelines forbid production `console.log(...)` / `console.debug(...)` and forbid reading secret input values inside command-center/helper UI.
- Backend provider-selection spec requires provider catalog and discovery payloads to remain provider-agnostic and secret-free.

## Requirements

1. Add a provider contract status area to the settings provider workflow using existing data from `/api/providers` and loaded plugin state from `/api/plugins` when available.
2. The UI must summarize provider contract counts by status and show per-provider label/key/kind, validation status, error/warning/check counts, issue codes, and plugin load state when present.
3. The UI must be data-driven and provider-agnostic. Do not branch on provider names such as DuckMail, Mail.tm, GPTMail, TempMail.lol, or Emailnator.
4. The UI must not read, render, copy, log, or include real API keys, bearer tokens, passwords, JWTs, refresh tokens, task tokens, consumer keys, or provider secret defaults.
5. The contract status area must degrade cleanly when contract validation data is missing, when no temp providers exist, or when plugin data has not loaded yet.
6. The layout must fit existing settings UI patterns, support desktop and mobile widths, and keep text wrapping stable without nested cards.
7. Tests must cover template mount, JavaScript state/render helpers, CSS hooks, and secret-safety constraints.

## Acceptance Criteria

- [ ] `templates/index.html` contains a dedicated provider contract status mount in the settings provider area.
- [ ] `static/js/main.js` caches provider contract state from `/api/providers` and plugin state from `/api/plugins`, then renders a concise status summary and provider rows.
- [ ] Provider contract rendering uses generic status/summary/issue-code fields and contains no provider-name conditionals.
- [ ] Contract rows show invalid/warning/valid/unknown states and compact issue codes without raw validation payloads or secret values.
- [ ] Missing provider contract data renders an empty/unavailable state instead of throwing.
- [ ] `static/css/style.css` adds responsive styling for the contract panel using existing visual language.
- [ ] Frontend contract tests assert DOM mount, JS helper names, generic rendering, secret-safety, and no production debug logging.
- [ ] Existing provider discovery/plugin API tests remain green.

## Out of Scope

- Changing backend validation semantics.
- Adding a new concrete provider.
- Building a modal JSON inspector for full validation payloads.
- Redesigning the entire settings page or adding a new frontend framework.
