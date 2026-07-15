# Unified mailbox workspace UX polish

## Goal

Improve the unified mailbox workspace first viewport so it reads like a professional mailbox aggregation service rather than an internal implementation panel. The page should make the four core jobs obvious: directory inventory, provider routing, verification reads, and external API access.

## Requirements

- Use the existing traditional HTML/CSS/JS stack and existing unified mailbox components. Do not add a new frontend framework, component library, or duplicate workspace entry point.
- Apply the UI brief:
  - Audience: operators and developers using the app repeatedly to manage account mailboxes, temp-mail providers, pool inventory, and external integrations.
  - Product archetype: operational SaaS / data product, dense but calm, scan-first, simple copy.
  - Primary workflow: open Unified Mailbox, understand inventory/routing/API readiness, then filter or open records.
  - Constraints: existing templates, static CSS/JS, i18n dictionary, provider-selection contract, mobile overflow rules.
- Refine static masthead and loading copy to use clearer product language in Chinese and English.
- Keep command-center data rendering provider-agnostic and contract-driven; do not branch on provider names or read any credential inputs.
- Preserve responsive behavior for the masthead, command center, toolbar, quick views, provider context, and mailbox cards.
- Update frontend contract tests and i18n strings so the UI contract matches the intended user-facing language.

## Acceptance Criteria

- [x] `templates/index.html` exposes the unified workspace masthead with clearer product copy and the four workflow stages: directory inventory, provider routing, verification reading, and external API.
- [x] `static/js/features/mailboxes.js` command-center copy remains data-driven and uses the refined product language without provider-specific branches or credential-input reads.
- [x] `static/js/i18n.js` contains matching English translations for new or changed user-facing copy.
- [x] Existing unified mailbox frontend contract tests are updated and pass.
- [x] Focused frontend/static tests, Python compile, and whitespace checks pass.

## Notes

This is a lightweight UI/UX polish task. PRD-only planning is sufficient.
