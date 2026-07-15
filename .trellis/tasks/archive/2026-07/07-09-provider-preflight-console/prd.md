# Provider preflight console

## Goal

Surface the provider readiness preflight contract in the authenticated Settings UI so administrators can validate Outlook/IMAP/temp-mail provider readiness before real use. The console should make the project feel more operationally complete by showing local readiness, configuration gaps, and explicit probe results in the same provider workbench that already documents routing, provider contracts, and external API integration.

## Confirmed Facts

- `GET /api/providers/preflight` already exists, requires login, and returns `{success: true, provider_preflight: ...}`.
- Default preflight is local-only and does not instantiate temp providers or call upstream networks.
- Explicit `probe_network=true` probes only locally ready temp providers; account providers remain local-only.
- Settings UI is static HTML/CSS/JS in `templates/index.html`, `static/js/main.js`, and `static/css/main.css`; no React/Tailwind/component library is present.
- Settings -> API Security already contains `#providerWorkbench`, provider diagnostics, provider contract status, deployment templates, integration guide, and `/api/providers` cache flow.
- Frontend specs require provider workbench UI to consume backend discovery/cache payloads, avoid local provider registries, avoid credential input reads, and keep mobile layouts free of squeezed/overflowing dense panels.

## Requirements

- Add a read-only provider preflight panel inside `#providerWorkbench`, not a new page or modal.
- Load preflight data from authenticated `/api/providers/preflight`; never call `/api/external/*` from the browser for this console.
- Cache the latest preflight payload and render loading, ready, error, and explicit probe states.
- Provide an explicit "run probe" control that calls `/api/providers/preflight?probe_network=true`; default load must remain local-only.
- Render secret-free status only: provider keys, labels, kind, local status, missing config key names, endpoint hints, and sanitized probe status/details. Do not read or display credential input values, masked placeholders, bearer tokens, API keys, JWTs, passwords, task tokens, consumer keys, or provider secret values.
- Stay provider-agnostic. Do not branch on built-in provider names such as DuckMail, Mail.tm, Emailnator, GPTMail, TempMail.lol, Outlook, or IMAP.
- Fit the existing operational SaaS settings style: compact, scannable, calm, responsive, and usable on mobile.

## Acceptance Criteria

- Settings markup includes stable mount points for provider preflight summary and provider preflight list inside `#providerWorkbench`.
- `static/js/main.js` loads `/api/providers/preflight` after settings/provider catalog load, caches the payload, renders it in provider workbench, and re-renders on language change.
- A manual probe button calls `/api/providers/preflight?probe_network=true`, shows pending state, and updates the same panel with probe counts/results.
- The renderer handles empty/error payloads without breaking the existing provider workbench, provider diagnostics, provider contracts, templates, integration guide, or external command center.
- Frontend contract tests assert DOM mount points, loader/renderer/control helper names, authenticated endpoint usage, no `/api/external/*` preflight fetch, secret-safety slices, provider-agnostic helper slices, i18n strings, and responsive CSS hooks.
- Existing provider backend/API tests and settings/unified mailbox frontend contract tests remain green.

## Out of Scope

- Adding a new backend endpoint or changing provider preflight semantics.
- Automatic network probing on page load.
- A new standalone provider management page.
- Editing or storing provider credentials from the preflight panel.
