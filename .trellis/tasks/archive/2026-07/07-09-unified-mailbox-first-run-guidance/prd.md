# Unified mailbox first-run guidance

## Goal

Make the unified mailbox workspace easier to use on a first run by turning the existing mailbox/provider/readiness data into a concise operator setup guide. The improvement should help a user understand the next practical step for building a combined Outlook/IMAP plus temp-mail mailbox service without requiring them to read docs first.

## Requirements

- Add an in-app first-run/setup guidance surface to the unified mailbox workspace.
- Use existing `/api/mailboxes` response data and existing frontend state; do not add a backend route for this slice.
- Keep the UI provider-agnostic. The frontend must not branch on hardcoded provider names such as DuckMail, mail.tm, GPTMail, TempMail.lol, Emailnator, or legacy bridge names.
- Keep the UI secret-safe. It must not read, render, or copy real API keys, provider tokens, passwords, JWTs, refresh tokens, or task tokens.
- Guide the core operator path: connect/import account mailboxes, configure temp-mail providers, confirm provider readiness, and use the external API integration material.
- Preserve the current Flask template + vanilla JS/CSS stack and the existing unified mailbox design language.
- Support empty, partial, ready, loading, and error/unknown states without layout shift.
- Keep copy short, operational, and suitable for a public GitHub project.

## Acceptance Criteria

- [ ] `templates/index.html` exposes a stable mount point for the setup guidance inside the unified mailbox workspace.
- [ ] `static/js/features/mailboxes.js` renders prioritized setup steps from aggregate mailbox/provider/readiness data without reading credential inputs or hardcoding provider-specific logic.
- [ ] `static/css/main.css` adds responsive, polished layout hooks for desktop and mobile with no card nesting and no text overflow in normal viewport checks.
- [ ] `static/js/i18n.js` includes English and Chinese strings for the new surface.
- [ ] Frontend contract tests cover the new mount point, render helpers, provider-agnostic behavior, secret safety, CSS hooks, and i18n strings.
- [ ] Focused frontend/catalog tests and syntax checks pass.
- [ ] A rendered desktop and mobile browser check confirms the unified mailbox page is nonblank and has no obvious horizontal overflow.

## Notes

- This is one high-impact slice toward the larger mailbox aggregation goal. It does not close the long-running product optimization objective by itself.
