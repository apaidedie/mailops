# Unified mailbox workspace first impression polish

## Goal

Make the authenticated mailbox area feel like a unified mailbox operations workspace from the first interaction. The default mailbox experience should foreground the unified directory that combines Outlook/IMAP accounts, provider-backed temp mailboxes, provider routing context, and external automation entry points, while preserving the existing standard and compact account views for focused legacy workflows.

## Background

The project already has a contract-driven unified mailbox directory, provider context display, provider capability matrix, quick views, and frontend contract tests. Current navigation still labels the main mailbox page as account management and the default mailbox view mode remains the legacy standard account layout. That first impression works against the long-term platform direction because users must discover the unified workspace as a secondary mode.

UI brief: the audience is operators and developers who manage reusable mailbox inventory for automation. The primary workflow is scanning the unified directory, understanding provider routing/readiness, and opening the right mailbox source quickly. The product archetype is calm operational SaaS. Constraints are Flask templates with static CSS/JS, existing contract-driven rendering, responsive desktop/mobile layouts, no new UI framework, and secret-safe provider metadata. Acceptance requires static contract tests plus rendered desktop/mobile checks because this task changes the first viewport and responsive behavior.

## Requirements

- Rename the primary mailbox navigation and topbar copy toward the unified mailbox platform mental model without removing account management functionality.
- Make `unified` the default mailbox view mode for new sessions when no saved mailbox view preference exists.
- Keep the standard and compact mailbox modes available and clearly positioned as account-focused views.
- Keep all provider and mailbox behavior contract-driven. Do not add provider-specific frontend branches, endpoint literals, or secret value rendering.
- Improve first-viewport hierarchy and microcopy for the unified command center so it reads as the primary mailbox workspace, not a hidden experimental panel.
- Preserve mobile layout integrity. The unified command center, toolbar, quick views, provider context, and mailbox cards must not squeeze into implicit grid columns or create page-level horizontal overflow.
- Keep changes additive and reversible. Do not remove legacy pages, account flows, temp-mail flows, or external API workflows in this task.

## Acceptance Criteria

- The sidebar mailbox entry uses unified mailbox product wording while still routing to the existing `mailbox` page.
- The mailbox view switcher defaults to `unified` when local storage has no previous value, and still supports `standard` and `compact`.
- Topbar and mode labels make the three modes understandable as unified workspace, account workspace, and compact account view.
- Frontend contract tests cover the new default mode, updated product copy, and preservation of the legacy account modes.
- Static checks pass for touched JavaScript.
- Rendered QA proves the mailbox page opens in unified mode on desktop and mobile without horizontal overflow and with the unified command center visible in the first viewport.

## Notes

- This task intentionally does not redesign every provider/settings screen. It improves the first impression of the primary mailbox workspace and leaves broader navigation IA for later child tasks.
