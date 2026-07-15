# Unified mailbox command center polish

## Goal

Polish the unified mailbox command center so the first viewport reads as the main workspace for Outlook, IMAP, temporary mailboxes, and external provider routing. The surface should be dense, operational, and easy to scan without becoming a landing page or duplicating provider-selection logic.

## Requirements

- Inspect `#unifiedMailboxCommandCenter` and its render path for layout, copy, contract consumption, mobile behavior, and secret-safety gaps.
- Keep `/api/mailboxes` as the only source for command-center summary, provider context, selection policy, integration guide, facets, and contract metadata.
- Improve the command-center hierarchy only where it clarifies inventory, routing, external entry points, or quick workflow decisions.
- Preserve provider-agnostic behavior. Do not branch on built-in provider names or read Settings credential inputs.
- Keep the UI in the existing Flask template plus static CSS/JS stack. Do not add a framework or component dependency.
- Update focused frontend contract tests for any new helper, text hook, CSS hook, or secret-safety requirement.
- Verify desktop and mobile rendering when layout or responsive behavior changes.

## Acceptance Criteria

- [ ] The command center clearly separates inventory status, provider routing, external entry, and workflow/quick-view context.
- [ ] Rendering remains a display adapter over `/api/mailboxes`; no local provider registry or credential input reads are introduced.
- [ ] Mobile layout stays single-column except deliberate horizontal rails, with no page-level overflow.
- [ ] Contract tests cover the command-center helper/copy/CSS hooks and provider-agnostic secret-safety slices.
- [ ] Focused tests, syntax checks, secret scan, diff whitespace check, and rendered desktop/mobile QA pass.

## UI Brief

Audience: operators and external-project integrators managing mailbox inventory and provider routing.

Primary workflow: land on the unified mailbox directory, understand available inventory and provider-routing posture, then apply a quick view or filter without hunting through Settings.

Product archetype: operational SaaS dashboard. The UI should be quiet, compact, structured, and work-focused.

Constraints: existing Flask templates, static JavaScript, static CSS, current i18n helper, no new frontend dependencies, and strict secret-free discovery display.

Source of truth: `/api/mailboxes` payload, frontend quality guidelines, provider selection contract, and existing design tokens/classes.

States: loading, degraded/missing provider context, empty result, active quick view, custom filter state, desktop, tablet, and mobile.

Acceptance: tests plus browser checks at desktop and mobile widths.
