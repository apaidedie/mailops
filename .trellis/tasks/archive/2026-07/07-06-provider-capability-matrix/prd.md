# Provider capability matrix

## Goal

Add a read-only provider capability matrix to the authenticated unified mailbox directory so operators can quickly see which mailbox sources are enabled, locally ready, dynamically creatable, readable, and remotely cleanable without opening the lower-level provider discovery endpoints.

## Background

The unified mailbox directory already consumes `GET /api/mailboxes` and renders a command center, provider policy band, contract-driven filters, summary cards, mailbox cards, and pagination. The same payload already exposes `provider_context`, `provider_context.provider_integration_guide`, `provider_context.provider_diagnostics`, `provider_context.selection_policy`, and `contract.action_definitions`.

Recent audit checks confirmed the public temp-mail providers are wired as built-ins: `legacy_bridge`, `mail_tm`, `duckmail`, `tempmail_lol`, `emailnator`, and `cloudflare_temp_mail`, plus plugin providers. DuckMail remains a Mail.tm-compatible provider that changes base URL and service bearer token while reusing Mail.tm request shapes. GPTMail-related names remain compatibility aliases for `legacy_bridge`; they must not be removed or rebranded out of the compatibility contract.

## Requirements

- Render the matrix inside `mailboxUnifiedLayout`, near the existing provider context and before the mailbox list, so the source policy and actual mailbox inventory stay in one operational view.
- Use only data already returned by `GET /api/mailboxes`; do not make browser calls to `/api/external/*`, do not read API key inputs, and do not call upstream provider networks from the UI.
- Treat `provider_context.provider_integration_guide.providers` as the preferred provider list for matrix rows. Use diagnostics, facets, and the shared mailbox contract only as supporting context.
- Display provider label, provider key, kind, active/configured/readiness state, missing config keys, required and optional env key names, read mode, dynamic create support, remote mailbox delete support, message delete support, clear messages support, health endpoint, and directory filter endpoint when available.
- Keep the rendering data-driven. Do not branch on specific provider keys such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, `gptmail`, or `legacy_bridge` to decide capability behavior.
- Preserve secret safety. Secret key names may be displayed, but secret values, bearer tokens, API keys, passwords, JWTs, task tokens, consumer keys, and masked input values must not be rendered, copied, or logged.
- The matrix must handle loading, error, ready, and empty states without leaving stale rows on refresh failure.
- Matrix provider row interactions may reuse the existing provider filter path, but only when the row provider is meaningful for the current directory filter.
- CSS must follow the existing operational SaaS style: compact, scannable, responsive, no nested cards, no decorative orbs/blobs, no horizontal overflow on mobile.

## Out Of Scope

- Changing backend provider selection priority, provider aliases, provider default resolution, or active allowlist semantics.
- Adding a new provider or changing provider runtime behavior.
- Probing upstream provider health from the browser.
- Exposing message content or adding mailbox read actions to the matrix.
- Replacing the existing settings-page provider integration guide.

## Acceptance Criteria

- `templates/index.html` contains a stable mount for the provider capability matrix inside the unified mailbox layout.
- `static/js/features/mailboxes.js` renders loading, error, empty, and ready states for the matrix and calls the renderer from unified mailbox loading, error, and success paths.
- Matrix rows are derived from `provider_context.provider_integration_guide.providers` and capability fields from the provider guide/catalog payload, not from a local provider registry.
- Existing unified mailbox controls still render status, read-capability, action, and sort options from `contract.*_definitions`.
- The UI never renders real provider secret values and production static JS remains free of `console.log(` and `console.debug(`.
- Frontend contract tests cover the new mount, renderer names, render calls, CSS selectors, i18n strings, data-driven provider guide consumption, and secret-safety expectations.
- Existing provider/API regression tests for provider discovery, OpenAPI, external temp-mail apply, public providers, and unified mailbox catalog continue to pass.
- A desktop and mobile browser check is performed if the visual density or layout changes materially.

## Evidence From Audit

- Secret scan for the real DuckMail token pattern returned no matches in application, test, documentation, template, and Trellis paths.
- Production static JS scan returned no `console.log` or `console.debug` matches under `static/js`.
- TempMail.lol documentation and client libraries confirm `POST https://api.tempmail.lol/v2/inbox/create` and `GET /v2/inbox?token=...`, matching the current provider implementation.
- GPTMail API documentation exposes `/api/generate-email`, `/api/emails`, `/api/email/{id}`, and `/api/emails/clear`, matching the current legacy bridge implementation.

## Open Questions

No blocking product questions remain for the first implementation slice. The recommended MVP is a read-only matrix fed by the existing `/api/mailboxes` payload.
