# Provider workbench IA polish

## Goal

Make the Settings -> API Security provider workbench read like a professional mailbox-source operations console. It should help operators understand routing, defaults, readiness, configuration source, provider discovery, and external integration posture without digging through several disconnected panels.

## Background

The project already exposes a provider workbench, diagnostics summary, integration guide, deployment templates, and provider console. Previous work made these payloads contract-driven and secret-safe, but the first-screen hierarchy still reads like a stack of technical panels. The long-term platform goal needs a cleaner, more focused control surface for Outlook/IMAP, temp-mail providers, external API consumers, and future provider kinds.

## Requirements

- Keep provider semantics data-driven from settings and `/api/providers`; do not introduce provider-name routing branches or local provider registries.
- Improve the workbench overview so it foregrounds the decisions an operator needs first: active mode, runtime temp-mail default, pool claim default, provider readiness, config-file state, source priority, and secret posture.
- Add concise in-panel copy that explains which endpoint external projects should discover first and how provider selection priority works, without exposing or reading secret input values.
- Keep diagnostics, deployment templates, integration guide, and provider console available as detailed sections under the same workbench rather than creating a second entry point.
- Preserve mobile usability with wrapping text, stable metric tile dimensions, and no horizontal page overflow.
- Update frontend contract tests for any new copy, helpers, CSS hooks, or secret-safety expectations.

## Acceptance Criteria

- [ ] `templates/index.html` presents the provider workbench as a coherent operations console with a clearer overview heading, compact explanatory copy, and stable mounts for overview, diagnostics, templates, integration guide, and provider console.
- [ ] `static/js/main.js` renders the overview from existing settings/catalog caches only and does not read API key or provider credential input IDs.
- [ ] The overview exposes runtime default, pool default, active provider mode, readiness count, config-file state, source priority, and secret policy in a scan-friendly order.
- [ ] `static/css/main.css` keeps the workbench responsive, wraps long provider names/paths/source-priority strings, and avoids nested card clutter.
- [ ] Frontend contract tests and relevant JS static checks pass.
- [ ] Browser QA verifies the API Security provider workbench on desktop and mobile with no page-level horizontal overflow.

## UI Brief

Audience: operators and developers who deploy Outlook Email Plus, connect external projects, and troubleshoot provider readiness. Primary workflow: understand active mailbox sources, defaults, selection priority, readiness, and discovery endpoints in the first scan. Product archetype: operational SaaS dashboard. Constraints: keep the current Flask template, static CSS, static JS, existing provider caches, and secret-safe contract behavior. Acceptance: focused frontend contract tests plus desktop/mobile browser QA with no horizontal overflow.

## Out Of Scope

- Changing provider selection semantics, aliases, environment variables, request fields, external API endpoint paths, or OpenAPI schemas.
- Adding a new provider or removing an existing provider.
- Replacing the current Flask template/static JS stack.
