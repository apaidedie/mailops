# Design

## Architecture

This task is frontend-only unless tests reveal a narrow backend contract gap. The existing backend contracts remain the source of truth for mailbox directory data, provider readiness, and message preview data.

The template will add a lightweight workspace navigation/control block near the unified mailbox masthead. The main content will be grouped into stable sections:

- Inbox workflow: toolbar, quick views, result bar, summary, mailbox list, pagination, and `#unifiedMailboxMessagePreview`.
- Diagnostics/setup: command center, setup guide, operational lens, provider context, and provider capability matrix.

The JavaScript module will own a small view state field such as `unifiedMailboxState.workspaceView`, with helpers to set the current view, reflect selected state on buttons, and keep existing renderers working. Existing data-loading and message-preview state should not reset when switching views.

## UI Direction

Product archetype: dense operational SaaS for registration workers and mailbox operators. The default screen should answer: what mailbox sources exist, which mailbox is selected, what recent messages are available, and what verification data can be extracted.

Advanced provider readiness remains important for extensibility, but it should be one click away rather than occupying the main scan path by default. The page should feel like an inbox workbench, not a documentation console.

## Data Flow

No new data source is required. Existing flows stay intact:

- `/api/mailboxes` populates directory, command center, setup guide, provider context, and capability matrix.
- `/api/mailboxes/<kind>/<source_id>/messages` populates preview.
- `/api/mailboxes/<kind>/<source_id>/messages/<message_id>` populates detail.
- `/api/mailboxes/<kind>/<source_id>/verification` populates verification extraction.

The view switch only changes visibility and visual grouping. It must not change filters, provider selection, pagination, selected mailbox, selected message, or cached provider context.

## Compatibility

Keep all existing IDs used by tests and render helpers. New wrappers/classes can be added, but existing DOM hooks must remain addressable. The old provider-specific open path remains as a secondary action on mailbox cards.

## Safety

The view switch must not read Settings secret inputs, call `/api/v1/external/*` or `/api/external/*`, or branch on provider names. It should use only local state and already-loaded admin payloads.

## Visual QA

After implementation, run focused contract tests and browser QA for desktop and mobile. Browser QA should inspect page-level overflow and key containers: `#mailboxUnifiedLayout`, `.unified-mailbox-shell`, the inbox workflow wrapper, `#unifiedMailboxList`, `#unifiedMailboxMessagePreview`, and the diagnostics wrapper.
