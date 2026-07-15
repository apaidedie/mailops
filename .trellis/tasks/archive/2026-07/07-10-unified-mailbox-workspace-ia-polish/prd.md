# Unified mailbox workspace IA polish

## Goal

Refine the existing Unified Mailbox page into a cleaner operational workspace where the primary workflow is visible immediately: choose a mailbox, preview messages, inspect details, and extract verification data. Keep provider readiness, setup guidance, source policy, and capability matrix available, but stop letting those advanced diagnostics push the inbox preview below a long stack of panels.

This is a product-quality/UI information-architecture increment toward the larger goal of a professional unified temp-mail + Outlook aggregation service. It must improve the existing Flask template/static JS/CSS implementation without introducing a new frontend framework.

## Confirmed Facts

- The unified mailbox page lives in `templates/index.html`, `static/js/features/mailboxes.js`, `static/css/main.css`, and `static/js/i18n.js`.
- The page already renders a command center, setup guide, toolbar, quick views, result bar, operational lens, summary, provider context, provider capability matrix, mailbox list, pagination, and message preview panel.
- The message preview panel is currently rendered after the mailbox list and advanced provider panels, so the most important operator workflow is not first-screen prominent.
- The frontend stack detector reports no React/Tailwind/component library; this project uses Flask templates plus static JavaScript/CSS.
- Existing frontend contract tests assert DOM hooks, render order, CSS selectors, i18n labels, secret-safety slices, and mobile rules.
- Existing browser QA for the previous task verified message preview renders on desktop and mobile with no horizontal overflow.

## Requirements

- Make the inbox preview a first-class part of the unified mailbox workspace, visually paired with the mailbox directory/list rather than buried after provider diagnostics.
- Preserve all existing advanced surfaces: command center, setup guide, operational lens, summary, source policy, provider context, and provider capability matrix.
- Add a lightweight view/section control for the workspace so operators can switch between the day-to-day inbox workflow and advanced diagnostics without losing the directory filters or selected mailbox context.
- Keep the default view focused on the daily read workflow: filters, list, pagination, and preview should be close together and visible before advanced provider diagnostics.
- Keep provider/External API setup and diagnostics available for operators who need to configure sources or inspect extensibility readiness.
- Keep UI dense, calm, and operational. Do not add landing-page hero treatment, decorative gradients, extra nested cards, or framework dependencies.
- Do not change backend message-preview API behavior in this task unless a UI contract requires a narrowly scoped addition.
- Do not call External API endpoints from the admin browser and do not read Settings secret inputs.
- Preserve mobile usability: no page-level horizontal overflow, no compressed implicit grid columns, and no overlapping controls.

## Acceptance Criteria

- [ ] The Unified Mailbox template contains a stable workspace view switch/control with options for the inbox workflow and advanced diagnostics.
- [ ] The default workspace flow places mailbox list/pagination and `#unifiedMailboxMessagePreview` together before advanced provider diagnostics.
- [ ] The advanced diagnostics view/section includes the existing setup guide, operational lens, provider context, and provider capability matrix without removing their DOM hooks.
- [ ] Frontend JavaScript exposes small provider-agnostic helpers for switching/rerendering workspace sections and keeps selected mailbox/message preview state intact across view changes.
- [ ] Frontend contract tests cover the new DOM hooks, default render order, switch helper/event binding, secret-safety constraints, i18n labels, and CSS/mobile selectors.
- [ ] Existing unified mailbox backend/API tests remain green.
- [ ] Desktop and mobile browser QA verifies the default inbox workflow renders without page-level or key-container horizontal overflow.

## Out of Scope

- New mailbox providers, new backend source types, new external API endpoints, and a full visual rebrand are out of scope for this task.
- Removing existing diagnostic panels is out of scope; this task reorganizes and polishes the workspace IA.
