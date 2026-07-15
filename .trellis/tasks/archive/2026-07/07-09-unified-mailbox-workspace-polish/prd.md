# Unified mailbox workspace polish

## Goal

Make the main authenticated UI more clearly present Outlook Email Plus as a professional unified mailbox aggregation service instead of a narrow Outlook-only mailbox manager. The mailbox workspace should make the product model obvious: Outlook/IMAP accounts, provider-backed temp mailboxes, mailbox pool lifecycle, provider routing, and external API access are parts of one operational control plane.

UI brief:

- Audience: operators and developers who manage mailbox sources and connect other automation services.
- Product archetype: operational SaaS / data-dense admin console.
- Primary workflow: open the mailbox page, understand source health and routing, filter mailbox inventory, copy/read the right mailbox, and move into source-specific workflows only when needed.
- Constraints: existing Flask/Jinja templates, plain CSS, existing static JS, current i18n helper, no new frontend framework or icon package.
- Art direction: quiet technical control plane, compact but readable, status colors used semantically, vector icons in structural navigation, stable responsive dimensions.

## Requirements

- Reposition the app shell from Outlook-only wording to unified mailbox aggregation wording while preserving existing routes and behavior.
- Replace structural sidebar emoji icons with consistent inline SVG symbols so navigation looks less toy-like and more production-grade.
- Improve the mailbox workspace first viewport so it communicates the aggregation pipeline, source coverage, and external API entry point without adding explanatory clutter.
- Keep unified mailbox filters, quick views, result bar, provider context, provider capability matrix, mailbox list, pagination, and existing actions intact.
- Improve responsive and accessibility basics for changed UI: accessible names, focus states, reduced-motion compatibility, and no mobile overflow.
- Preserve the existing visual system and CSS variables; do not introduce React, Tailwind, shadcn, or another component library in this task.
- Keep changes scoped to UI/UX presentation and copy. No provider runtime behavior, mailbox lifecycle semantics, or external API contract changes.

## Acceptance Criteria

- [ ] Browser title, sidebar brand, and topbar copy present the product as a unified mailbox service while retaining recognizable Outlook Email Plus identity.
- [ ] Sidebar navigation uses consistent vector icons with accessible-hidden decorative SVGs and no emoji structural icons in the app shell navigation.
- [ ] Unified mailbox masthead communicates the pipeline: account inventory, provider routing, verification reads, and external API sessions.
- [ ] Unified mailbox page remains responsive at desktop and mobile widths with no obvious horizontal overflow in the changed sections.
- [ ] Changed interactive controls have visible hover/focus states and do not resize surrounding layout.
- [ ] Existing mailbox view switching and unified mailbox loading still work in tests or syntax checks.
- [ ] Updated i18n strings cover new Chinese copy for English UI mode.
- [ ] Frontend-focused validation and relevant mailbox/API tests pass.

## Notes

- UI skill evidence: `ui-design-suite` routed this as a general dashboard/workspace task; detector found no React/Tailwind stack; `ui-ux-pro-max` recommended a data-dense operational dashboard direction.
- This is a focused slice of the long-running product polish objective, not a declaration that the whole objective is complete.
