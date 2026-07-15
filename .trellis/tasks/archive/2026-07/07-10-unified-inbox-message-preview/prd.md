# Unified Inbox Message Preview Workspace

## Goal

Build a logged-in unified inbox preview workspace inside the existing Unified Mailbox page so operators can inspect messages, message details, and verification data from Outlook, IMAP, and provider-backed temp mailboxes without leaving the unified directory or understanding provider-specific pages.

## User Value

The unified mailbox directory already normalizes Outlook, IMAP, mailbox pool, provider temp mailboxes, and external API contracts. The missing operator experience is a provider-neutral read surface. This task turns the directory into a real inbox workbench by letting a user select any readable mailbox and preview messages in the same UI.

## Confirmed Facts

The project is a Flask app with static JS/CSS frontend. The unified mailbox directory is served by `GET /api/mailboxes`, registered in `outlook_web/routes/mailboxes.py`, handled by `outlook_web/controllers/mailboxes.py`, and owned by `outlook_web/services/mailbox_catalog.py`. The frontend unified workspace lives in `templates/index.html`, `static/js/features/mailboxes.js`, and `static/css/main.css`.

Existing account read endpoints are provider-specific through `/api/emails/<email>` and `/api/email/<email>/<message_id>`. Existing temp-mail read endpoints are provider-specific through `/api/temp-emails/<email>/messages` and `/api/temp-emails/<email>/messages/<message_id>`. The current unified mailbox card action calls `openUnifiedMailbox(...)`, which navigates to the account or temp-mail page instead of rendering messages in place.

The external API already has provider-neutral message and mailbox-session routes, but the admin browser must not use plaintext External API keys or call `/api/v1/external/*` for internal UI work.

## Requirements

Add authenticated admin endpoints under `/api/mailboxes/...` for a selected mailbox message list, selected message detail, and verification extraction. These endpoints must use the logged-in session and must not require or expose External API keys.

Add a backend service owner for unified mailbox message preview behavior. The controller must stay thin, and the route file must only register URLs.

Normalize account and temp-mail message list/detail responses into a single DTO that includes mailbox identity, source kind, provider, method, folder, message id, sender, subject, preview/body, body type, date/timestamp, and safe status metadata. The DTO must not expose refresh tokens, IMAP passwords, provider bearer/API tokens, task tokens, claim tokens, consumer keys, or raw credential fields.

Extend the Unified Mailbox page with a message preview panel that appears alongside the directory. It must support loading, empty, error, selected mailbox, selected message, verification result, refresh, and mobile states. It must remain dense, calm, and operational rather than marketing-styled.

The UI must use existing static JS/CSS patterns, escape dynamic strings before inserting HTML, avoid provider-specific branches, avoid Settings secret inputs, and avoid External API endpoints.

## Acceptance Criteria

`GET /api/mailboxes/<kind>/<source_id>/messages` returns a logged-in, secret-safe, normalized message list for account and temp mailboxes.

`GET /api/mailboxes/<kind>/<source_id>/messages/<message_id>` returns a logged-in, secret-safe, normalized message detail for account and temp mailboxes.

`GET /api/mailboxes/<kind>/<source_id>/verification` returns a logged-in, secret-safe verification result for account and temp mailboxes.

The unified mailbox card primary action loads the preview panel in the unified workspace instead of forcing navigation to a provider-specific page. Existing provider-specific navigation remains available as a secondary path.

Frontend contract tests cover DOM hooks, JS state/helpers, fetch endpoints, event binding, secret-safety slices, and CSS selectors for the preview panel.

Backend tests cover authentication, normalized account/temp message list and detail responses, verification response shape, invalid kind/source behavior, and secret safety.

Module-boundary tests remain green, focused backend/frontend tests pass, project readiness passes if integration surfaces are affected, and desktop/mobile browser QA confirms no page-level or key-container horizontal overflow.

## Out of Scope

This task does not change the public external API contract, add a new frontend framework, redesign all mailbox pages, remove legacy provider-specific account/temp pages, or persist message content in browser storage.
