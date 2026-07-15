# Design

## UI brief

Audience: operators and developers who use this project as a mailbox aggregation service and need quick confidence that mailbox sources, provider routing, and external API entry points are usable.

Primary workflow: enter the unified mailbox workspace, understand operational status, filter the directory, inspect provider readiness, and open/copy mailbox data without switching mental models between Outlook accounts and temp-mail providers.

Product archetype: operational SaaS with a premium, calm, technical dashboard personality.

Constraints: existing Flask/Jinja template, static CSS, static JavaScript, no new frontend framework or component library, existing contract tests, provider-agnostic security rules, Chinese-first UI with existing i18n support.

Source of truth: current repository hooks and tests, backend mailbox/provider contracts, existing CSS tokens, `ui-design-suite` routing, and `ui-ux-pro-max` operational SaaS guidance.

States: loading, ready, empty, error, hover, focus-visible, active quick views, selected provider facets, busy refresh, disabled pagination, mobile single-column collapse, reduced motion.

Acceptance: frontend contract tests plus rendered checks at desktop and mobile sizes that inspect page overflow and toolbar overflow.

## Art direction

The unified mailbox page should feel like a command console for a serious mailbox platform. The layout should use one depth model: soft elevated operational surfaces. Colors should move away from scattered emoji-led affordances and toward semantic blue/action, amber/warning, green/ready, red/error, while still respecting the existing project theme tokens. Typography should be compact and stable.

The top of the page gets a workspace masthead that frames the product: unified directory, provider routing, and API integration. The command center remains the main operational card. Filters sit directly below it as a controlled cockpit, not a separate form dump. Provider panels and mailbox cards should use consistent radius, border, shadow, and spacing.

## Technical boundaries

Template changes stay inside `#mailboxUnifiedLayout` and preserve all existing IDs used by JavaScript and tests.

CSS changes stay in `static/css/main.css` and extend existing `.mailbox-unified-*`, `.unified-*`, and responsive sections. Do not add a new stylesheet unless the current file becomes structurally unsafe.

JavaScript changes stay in `static/js/features/mailboxes.js` if needed. New rendering must consume the existing `/api/mailboxes` response fields: summary, facets, contract, provider_context, provider diagnostics, and mailbox items. It must not read Settings form inputs or provider secret fields.

## Data flow

The existing `loadUnifiedMailboxes()` flow remains authoritative. It fetches `/api/mailboxes`, stores `data.contract`, renders filter definitions, command center, summary, provider context, provider capability matrix, mailbox list, result bar, and pagination. This task may polish render output and state copy but should not change the request contract.

## Responsive design

Desktop uses a centered shell with generous but compact spacing. Tablet collapses the command-center grid to one column while retaining readable cards. Mobile collapses toolbar fields and command-center children to full width. Any horizontal rails, such as quick views, may scroll internally, but the page and toolbar must not overflow.

## Accessibility

Interactive controls keep accessible names, visible focus states, stable dimensions, and semantic button/select/input elements. Motion is limited to transform/opacity and disabled under `prefers-reduced-motion: reduce`. Color is not the only indicator for provider/readiness state; text labels remain present.

## Compatibility and rollback

The change is safe to roll back by reverting template/CSS/JS edits for this task. Existing backend and API behavior are not modified. Existing contract tests should catch missing hooks, provider-specific branching, and responsive CSS regressions.
