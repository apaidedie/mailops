# Professional unified mailbox platform

## Goal

Turn Outlook Email Plus into a professional unified mailbox platform that combines Outlook/IMAP account mailboxes, provider-backed temp mailboxes, external automation APIs, and future provider extensibility behind one coherent product and developer experience.

## Background

The project already has a unified mailbox directory, provider discovery APIs, an external integration manifest, task-scoped temp mailbox APIs, pool claim APIs, and configurable provider selection through environment variables, a provider config file, settings, and request fields. Recent work added Mail.tm, DuckMail, TempMail.lol, Emailnator, GPTMail compatibility, Cloudflare temp mail, external workflow playbooks, and secret-safe manifests.

The long-term product direction is broader than one feature. The platform must feel like a polished mailbox operations product rather than a collection of provider-specific screens. It should stay easy to extend when new mailbox kinds or temp-mail providers are added.

## Requirements

- Preserve the upstream-friendly custom branch workflow so local improvements can keep consuming original project updates without losing custom features.
- Treat the unified mailbox directory as the primary mailbox inventory surface for Outlook, IMAP, temp mail, and future mailbox kinds.
- Keep provider selection contract-driven: environment variables, provider config files, settings, and request fields must remain discoverable through machine-readable APIs.
- Keep all external integration payloads secret-safe. They may expose secret key names but must not expose API key, bearer token, JWT, password, refresh token, consumer key, task token, or stored provider secret values.
- Make provider addition low-friction by relying on provider catalogs, provider capabilities, selection policies, and shared directory contracts instead of hardcoded provider-specific UI or API tables.
- Improve UI/UX in the direction of a calm operational SaaS product: dense but readable, restrained visuals, clear hierarchy, strong empty/error/loading states, responsive layouts, accessible controls, and concise product copy.
- Remove or de-emphasize legacy GPTMail branding from product-facing surfaces while preserving compatibility aliases and migration behavior.
- Remove features only when current evidence shows they are redundant, risky, or inconsistent with the unified platform direction; preserve migration paths for existing users.

## Child Tasks

- `07-07-provider-selection-recipes`: expose provider-selection recipes that external projects can consume to choose mailbox sources through env, config files, settings, or per-request fields.

## Acceptance Criteria

- Each platform improvement is captured as a child task with testable acceptance criteria before implementation.
- Backend changes that affect provider selection, provider discovery, external APIs, or unified mailbox payloads pass the provider/API regression suite and do not leak provider secrets.
- Frontend changes that affect mailbox, provider, or external API screens follow the project UI specs, pass contract tests, and receive rendered desktop/mobile QA when layout or interaction changes.
- The final platform state has current README/API/provider docs, a coherent first-run external integration path, and a unified mailbox UI that can support future provider kinds without provider-specific branching.

## Out Of Scope For This Parent Task

This parent task does not directly implement every product change. It owns the roadmap, cross-child acceptance criteria, and final integration review. Implementation belongs in child tasks that can be verified independently.
