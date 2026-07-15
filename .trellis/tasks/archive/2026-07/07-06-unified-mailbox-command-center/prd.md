# Unified mailbox command center

## Goal

Make the unified mailbox mode feel like the product's primary command center rather than a secondary list view. The first screen should clearly communicate that Outlook/IMAP accounts, temporary mailboxes, provider selection, and external API consumption are one configurable mailbox fabric.

## Background

The backend already exposes `/api/mailboxes` with account and temp mailbox DTOs, contract metadata, facets, provider context, deployment templates, provider selection policy, and provider integration guide. The current unified UI renders filters, summary cards, provider context, and mailbox cards, but it lacks a strong first-viewport product layer that explains the operating model and helps users quickly understand scope, provider health, external call readiness, and active routing.

UI stack evidence: Flask/Jinja templates, vanilla JavaScript modules, and CSS in `static/css/main.css`. No React/Tailwind/component-library migration is planned.

## Requirements

Add a data-driven command center section at the top of unified mailbox mode. It must render from `/api/mailboxes` payload fields already available in the frontend, including `summary`, `facets`, `filters`, `provider_context`, `provider_context.selection_policy`, `provider_context.provider_diagnostics`, `provider_context.provider_integration_guide`, and `contract`.

The command center must show current catalog scope, total mailbox count, account/temp mix, active provider count, ready provider count, provider routing mode, external mailbox endpoint, and source-priority route. It must include short workflow chips for account mailboxes, temporary mailboxes, provider routing, and external API access without hardcoding provider-specific instructions.

The design must fit operational SaaS usage: compact, calm, scan-friendly, responsive, keyboard-readable, and compatible with the existing design tokens. Do not add a landing hero, decorative blobs, new frontend frameworks, or emoji-driven structural icons.

The existing unified filters, provider context, result bar, mailbox list, pagination, and open/copy flows must keep working. The new UI must have loading, error/unavailable, empty, ready, desktop, and mobile states.

## Acceptance Criteria

- `templates/index.html` includes a `unifiedMailboxCommandCenter` mount before the unified filter toolbar.
- `static/js/features/mailboxes.js` renders the command center on loading, error, and successful `/api/mailboxes` loads.
- Rendering is data-driven from `/api/mailboxes`; no provider-specific branch such as DuckMail/Mail.tm/GPTMail rules is introduced.
- The command center summarizes mailbox scope, source mix, provider health, routing mode, source priority, and external mailbox endpoint.
- CSS defines stable desktop and mobile layouts for command-center metrics, route text, and workflow chips without nested cards or text overflow.
- i18n covers new visible labels and fallback copy.
- Frontend contract tests cover the mount, JS renderer, CSS hooks, and translations.
- Targeted unified mailbox frontend tests and syntax checks pass.

## Out Of Scope

No database schema changes, provider resolution changes, new mailbox provider implementation, external API contract change, or full visual redesign of every application page is part of this slice.
