# Unified mailbox workspace first impression polish design

## Architecture and boundaries

This task changes the authenticated frontend shell and mailbox mode defaults only. It must not change mailbox catalog APIs, provider selection contracts, backend provider behavior, external API behavior, or stored account/temp-mail data.

The main files are `templates/index.html`, `static/js/main.js`, `static/js/features/mailbox_compact.js`, `static/js/features/mailboxes.js`, `static/js/i18n.js`, `static/css/main.css`, and the existing frontend contract tests.

## UX direction

The mailbox page should read as a unified operations workspace. The sidebar entry should lead with unified mailbox wording. The mode switcher should present `unified` as the first/default workspace, with standard and compact account views as focused alternatives.

The visual archetype remains calm operational SaaS: dense, restrained, readable, and contract-driven. Avoid marketing hero treatment, decorative graphics, and new component libraries.

## Data flow and state

`mailboxViewMode` is currently persisted in `localStorage` under `ol_mailbox_view_mode`. The new default should be `unified` only when the stored value is missing or invalid. Existing users with `standard` or `compact` stored should keep their preference.

When `mailboxViewMode === 'unified'`, the existing `syncMailboxHeader()` path already hides account-only actions and triggers `loadUnifiedMailboxes(false)` through the view-mode switcher. This task should preserve that flow.

## Compatibility

Keep the page route as `mailbox` and preserve the `standard`, `compact`, and `unified` mode values. Tests and browser checks should prove older modes still render and the new default does not break local-storage-based preference restoration.

## Rollback

Rollback is limited to restoring old labels and the previous `standard` fallback in `mailboxViewMode`. No migration or data cleanup is required.
