# Unified mailbox workspace UI polish

## Goal

Make the unified mailbox directory feel like the primary operational workspace for the forked service: operators should be able to scan Outlook/IMAP accounts, temp-mail providers, provider routing policy, readiness, filters, and next actions from one coherent first viewport.

## Background

The backend unified mailbox and external integration contracts already exist. `/api/mailboxes` owns the directory payload, `contract` definitions, facets, `provider_context`, provider readiness summary, and item `action_contract`. The UI must remain a consumer of those contracts rather than defining provider-specific behavior locally.

The current page already exposes a command center, toolbar, quick views, result bar, summary, provider context, provider capability matrix, mailbox list, and pagination. This task is a focused polish pass over that workspace, not a redesign of the entire application.

## Requirements

- Keep the existing Flask template plus static CSS/JavaScript stack. Do not introduce React, Tailwind, or a new component library.
- Improve the unified mailbox first viewport with a calmer operational SaaS hierarchy: command center, route/defaults, inventory metrics, quick views, filters, readiness, and mailbox actions should scan clearly.
- Preserve contract-driven rendering. Status/read-capability/action/sort/provider options must continue to come from `/api/mailboxes` contract/facets after load, with only minimal template placeholders before load.
- Keep provider handling provider-agnostic. Do not add branches for specific built-in providers and do not expose provider secret values, API keys, bearer tokens, JWTs, passwords, task tokens, consumer keys, or refresh tokens.
- Improve responsive behavior for the unified command center, filter toolbar, provider status surfaces, capability matrix, and mailbox cards. Mobile must not rely on implicit grid columns and must keep controls usable without horizontal overflow.
- Preserve loading, error, empty, hover, focus, active, and selected states for the workspace controls.
- Avoid backend API behavior changes unless a frontend contract gap is discovered and explicitly required for the UI to render safely.

## Acceptance Criteria

- [x] The unified mailbox workspace has a clear command-center hierarchy for directory inventory, provider defaults, source priority, route mode, discovery endpoint, quick views, and workflow chips.
- [x] Toolbar/search/filter controls are grouped and responsive with stable control sizing and accessible labels.
- [x] Result bar, provider context, provider readiness, provider capability matrix, and mailbox cards read as product UI rather than raw debug output while keeping all existing contract data visible.
- [x] Mailbox cards show source, status, provider, read capability, action capabilities, latest signal, verification code action, and open/copy actions without layout shifts.
- [x] No provider-specific frontend branch or secret-value rendering is introduced.
- [x] Existing unified mailbox frontend and catalog tests pass.
- [x] `git diff --check` passes.

## Out of Scope

- Reworking provider catalog or external API backend behavior.
- Replacing the app shell or redesigning unrelated Settings, Temp Emails, or standard mailbox pages.
- Adding a new frontend framework, build pipeline, or icon library.
- Implementing new provider integrations beyond the providers already wired into the catalog.
