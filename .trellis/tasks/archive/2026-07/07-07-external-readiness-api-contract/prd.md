# External readiness API contract

## Goal

External API consumers should be able to call GET /api/external/health first and decide whether this instance has usable unified mailbox directory inventory before making heavier discovery or mailbox directory calls.

## Background

The external health response already exposes secret-free readiness for database access, cached upstream probe state, provider discovery, pool access, and task temp-mail workflows. The unified mailbox directory already owns account/temp mailbox inventory and exposes provider_context.readiness_summary through /api/external/mailboxes, including account scoping for multi-key consumers.

The remaining gap is that health readiness points callers to /api/external/mailboxes but does not expose a compact directory inventory status. External clients must either fetch the full directory or guess whether mailbox assets exist.

## Requirements

- Add a required readiness.mailbox_directory object to GET /api/external/health.
- Reuse the unified mailbox directory service contract for mailbox inventory counts instead of rebuilding mailbox/provider rules in the health controller.
- Respect multi-key allowed_emails account scoping before computing health directory counts.
- Keep the health response compact and secret-free: no mailbox item rows, account credentials, provider bearer tokens, task tokens, consumer keys, JWTs, refresh tokens, or passwords.
- Keep health successful when directory readiness cannot be loaded; report a degraded mailbox directory status and a warning instead of failing the whole endpoint.
- Document the new field in the external OpenAPI schema and backend provider-selection contract.

## Acceptance Criteria

- GET /api/external/health returns data.readiness.mailbox_directory.endpoint == /api/external/mailboxes.
- readiness.mailbox_directory includes a stable status, scoped flag, compact totals for all/account/temp mailboxes, summary counts, and quick probe parameters for a one-item directory probe.
- A multi-key API consumer with allowed_emails sees account mailbox counts scoped to that allowlist while user-visible temp mailboxes remain counted.
- Health readiness remains secret-free even when stored account or temp mailbox metadata contains token-like values.
- ExternalReadinessSummary in /api/external/openapi.json requires and types mailbox_directory.
- Focused external API tests pass, and touched Python files compile.

## Out Of Scope

- Adding a new /api/external/readiness endpoint.
- Changing mailbox directory item shape or frontend UI behavior.
- Calling provider upstream networks from health readiness.
- Returning full provider diagnostics or mailbox rows from health.
