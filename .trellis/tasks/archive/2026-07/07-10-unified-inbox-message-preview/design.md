# Design

## Architecture

Add `outlook_web/services/unified_mailbox_messages.py` as the service owner for internal unified message preview. It composes existing repositories and read services without exposing the external API auth surface to the admin browser.

Add thin controller handlers in `outlook_web/controllers/mailboxes.py` and URL registrations in `outlook_web/routes/mailboxes.py`:

- `GET /api/mailboxes/<kind>/<int:source_id>/messages`
- `GET /api/mailboxes/<kind>/<int:source_id>/messages/<path:message_id>`
- `GET /api/mailboxes/<kind>/<int:source_id>/verification`

The service resolves mailbox identity by `kind` and `source_id`. `kind=account` loads from `accounts_repo.get_account_by_id`. `kind=temp` loads from a new repository helper `temp_emails_repo.get_temp_email_by_id(..., view="descriptor")`. Account rows with `provider=cloudflare_temp_mail` are routed through `mailbox_resolver.resolve_mailbox(email)` and temp-mail read service, matching existing external behavior.

## Data Flow

The frontend directory payload already includes stable `kind`, `source_id`, `email`, `provider`, `provider_label`, and read capability fields. A card click calls `openUnifiedMessagePreview(item)` and fetches the new admin endpoint. Selecting a row fetches the detail endpoint. The verification button calls the verification endpoint.

The backend returns a DTO shaped for UI consumption:

- `mailbox`: safe mailbox identity and provider metadata
- `messages`: normalized list rows
- `message`: normalized detail row when applicable
- `verification`: normalized verification payload when applicable
- `count`, `folder`, `method`, `source`, `provider`

## UI Direction

UI brief: operators and developers need a fast, dense inbox workbench inside the unified directory. Product archetype is operational SaaS. The primary workflow is selecting a mailbox, scanning recent messages, opening one message, and extracting/copying verification data. The implementation must preserve the existing original JS/CSS stack, use the existing token system, expose loading/empty/error/success/selected states, and verify desktop/mobile layouts.

Art direction: quiet operational workspace with a directory rail and an inbox preview surface. Use restrained depth, compact typography, stable panels, visible focus, and no decorative hero treatment.

## Compatibility

The existing `openUnifiedMailbox(...)` function remains available for provider-specific navigation. The new preview action becomes the primary card action and a secondary button keeps the old open behavior.

No external API endpoints are called from the admin browser. No provider-specific JS routing table is introduced.

## Safety

Do not expose refresh tokens, IMAP passwords, provider secrets, external API keys, task tokens, claim tokens, consumer keys, or raw settings values. Do not persist message content or operational handles in localStorage.
