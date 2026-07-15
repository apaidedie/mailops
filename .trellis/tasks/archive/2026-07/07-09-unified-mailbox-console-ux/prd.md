# Unified Mailbox Console UX

## Goal

Improve the unified mailbox workspace from a catalog display into a more operational console. Operators should be able to open the unified mailbox page and quickly understand the current filtered view, provider readiness risk, empty-result cause, and the next useful action without reading raw provider diagnostics.

## Background

The project already exposes a unified mailbox directory through `/api/mailboxes` and renders the unified mailbox workspace in `templates/index.html`, `static/js/features/mailboxes.js`, and `static/css/main.css`. The page includes the command center, filters, quick views, result bar, summary metrics, provider context, provider capability matrix, and mailbox cards. The next high-leverage UX improvement is to turn those existing payloads into an operator-facing status layer rather than adding another backend contract.

## Requirements

- Add a compact operational lens to the unified mailbox workspace, positioned after the result bar and before summary/provider detail sections.
- Build the lens only from the existing `/api/mailboxes` response: `summary`, `filters`, `pagination`, `facets`, `contract`, and `provider_context`.
- Surface current view state, provider readiness posture, active filters, and recommended next actions.
- Keep the implementation provider-agnostic. Do not branch on built-in provider names such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail`.
- Keep the lens secret-safe. It may show provider labels, counts, endpoint paths, status labels, and secret key names already exposed by discovery, but it must not read or render API keys, bearer tokens, passwords, JWTs, task tokens, consumer keys, or provider secret values.
- Preserve existing unified mailbox APIs and existing mailbox open/copy flows.
- Keep layout dense, responsive, accessible, and consistent with the existing Flask template plus vanilla CSS/JS stack. Do not introduce a new UI framework.

## Acceptance Criteria

- [ ] `templates/index.html` exposes `#unifiedMailboxOperationalLens` between `#unifiedMailboxResultBar` and `#unifiedMailboxSummary`.
- [ ] `static/js/features/mailboxes.js` renders loading, error, empty, warning, and ready operational-lens states.
- [ ] The lens shows at least three actionable sections: current view, provider readiness, and recommended action.
- [ ] Recommended actions are derived from generic response fields and can apply quick views or trigger refresh without provider-name conditionals.
- [ ] The frontend contract test asserts the new DOM hook, render helpers, render order, CSS hooks, i18n strings, and secret-safety/provider-agnostic slices.
- [ ] `static/css/main.css` provides responsive layout for the lens, with no fixed-width desktop-only grid that can create mobile overflow.
- [ ] Existing unified mailbox, overview, and catalog contract tests remain green.

## Out Of Scope

- No backend API or schema changes.
- No provider selection logic changes.
- No new dependency or component framework.
- No broad redesign of the entire application shell in this task.
