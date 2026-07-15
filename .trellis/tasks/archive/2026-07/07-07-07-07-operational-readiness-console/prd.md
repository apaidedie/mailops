# Operational Readiness Console

## Goal

Add a compact operational readiness console to the Settings API Security external access command center so an operator can tell whether the unified mailbox service is ready for local use and external integrations without inspecting several panels.

## Requirements

- Keep the console inside the existing external API command center instead of adding another page or entry point.
- Consume existing authenticated, secret-free payloads: `/api/settings`, `/api/providers`, and `/api/mailboxes` provider context. Do not call `/api/external/*` from the browser.
- Summarize API key readiness, external pool status, provider catalog readiness, mailbox inventory, account mailbox readiness, temp-mail readiness, discovery/OpenAPI availability, and task-temp creation readiness.
- Preserve provider-agnostic behavior. The frontend must not branch on built-in provider names to compute readiness.
- Keep all rendered and copied content secret-safe. The console must not read API-key or provider-token input fields.
- Render useful loading, degraded, and empty states while keeping existing quickstart, starter-kit, recipe, and workflow surfaces available.
- Follow the existing Flask template plus plain JavaScript/CSS UI stack and the current Settings page visual language.

## Acceptance Criteria

- Frontend contract tests assert the console helper names, `/api/mailboxes` readiness snapshot load, provider/settings render hooks, and language-change render hook.
- Frontend secret-safety tests assert the console slice does not reference external API key fields or provider credential input IDs.
- CSS and i18n contract tests assert the console has responsive, wrapping styles and bilingual strings.
- Existing external API quickstart, provider guide, and unified mailbox contract tests remain green.
- Static checks pass for touched JavaScript and no token-like secrets appear in the diff.
