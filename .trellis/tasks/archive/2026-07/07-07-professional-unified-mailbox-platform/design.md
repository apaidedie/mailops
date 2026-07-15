# Professional Unified Mailbox Platform Design

## Product Direction

The product should present one mailbox platform with multiple source types rather than separate Outlook, IMAP, temp-mail, and automation islands. The user-facing mental model is workspace first, provider second. Provider details remain visible where they affect routing, readiness, or configuration.

## Architecture Boundaries

Provider discovery, selection policy, deployment templates, and integration manifests stay in `outlook_web.services.provider_catalog`. Unified inventory stays in `outlook_web.services.mailbox_catalog` and consumes provider context from the catalog helpers. UI surfaces act as display adapters over these contracts and must not rebuild provider semantics locally.

## UI Direction

The UI archetype is operational SaaS. It should favor compact information density, predictable filters, clear status bands, restrained color, stable dimensions, and strong affordances over marketing-style hero sections. The existing Flask templates and static CSS/JS stack stays in place unless a future child task proves a framework migration is worth the cost.

## Extensibility Direction

New mailbox kinds and temp-mail providers should appear through shared registries, provider capabilities, provider selection policy values, OpenAPI enums, integration manifest providers, and unified mailbox facets. Child tasks should avoid provider-name conditionals except in provider implementation classes and compatibility alias handling.

## Verification Strategy

Backend work must include contract tests for `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, `/api/external/openapi.json`, and `/api/mailboxes` when relevant. Frontend work must include static contract tests and rendered QA for desktop and mobile when layout changes.
