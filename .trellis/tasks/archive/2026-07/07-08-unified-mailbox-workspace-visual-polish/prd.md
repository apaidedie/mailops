# Unified mailbox workspace visual polish

## Goal

Make the unified mailbox workspace feel like the primary product surface for a professional mailbox aggregation service. The page should present Outlook/IMAP accounts, temp-mail providers, provider readiness, routing policy, and external API entry points as one coherent operational console instead of a collection of raw admin widgets.

This task is one high-value UI/UX iteration, not a full rewrite. It must improve the first viewport, scan path, responsive behavior, copy quality, and state clarity while preserving the existing Flask template, static CSS, static JavaScript, and contract-driven provider architecture.

## Background and confirmed facts

The current project is a single-repo Flask/static frontend. UI stack detection found no React, Tailwind, Semi Design, or component-library stack, so implementation should use the existing `templates/index.html`, `static/css/main.css`, and `static/js/features/mailboxes.js` patterns.

The unified mailbox page already has `#mailboxUnifiedLayout`, a command center, dense filters, quick views, result bar, provider context, provider capability matrix, mailbox cards, and pagination. The frontend contract tests in `tests/test_unified_mailbox_frontend_contract.py` assert these hooks and several provider-agnostic safety rules.

The UI design route used `ui-design-suite` with `ui-ux-pro-max` as the primary skill. The appropriate art direction is operational SaaS: calm, precise, premium enough for a GitHub-facing product, but dense enough for real mailbox operations. Visual richness should support scanning, confidence, and routing clarity.

## Requirements

The unified mailbox workspace must open with a stronger product-level header that explains the value of the unified console, exposes the relationship between mailbox directory, provider routing, and external API integration, and avoids decorative clutter.

The first viewport must have a clearer hierarchy. The command center should read as the main operational summary, while filters, quick views, provider readiness, capability matrix, and mailbox cards should feel like connected parts of one workflow.

The filter toolbar must remain contract-driven and provider-agnostic. No frontend logic may branch on provider names such as DuckMail, Mail.tm, TempMail.lol, Emailnator, GPTMail, or future providers. The UI may render provider names and field names that arrive from backend discovery payloads.

The UI must not read or render secret values. It must not reference Settings credential input IDs or provider token fields to produce unified mailbox visuals.

Loading, empty, error, hover, focus, selected, busy, and disabled states must stay visible and stable. Motion must remain subtle and respect `prefers-reduced-motion`.

Desktop and mobile layouts must not overflow horizontally. Dense toolbar controls must wrap inside `.unified-toolbar`, and command-center children with explicit grid positions must collapse back into a single-column mobile flow.

The change must preserve existing IDs and class hooks relied on by tests and JavaScript unless tests and code are updated together.

## Out of scope

This task will not introduce a new frontend framework, redesign every application page, replace the provider contract model, add new backend provider integrations, or change external API behavior. It will not chase tiny visual preferences after the main workspace quality bar is met.

## Acceptance criteria

`templates/index.html` contains the enhanced unified workspace shell and preserves existing unified mailbox control IDs, labels, and JavaScript entry points.

`static/css/main.css` defines a cohesive polished workspace treatment for the unified mailbox page, including command center, toolbar, quick views, result bar, provider panels, capability matrix, mailbox cards, mobile breakpoints, focus states, reduced-motion handling, and no page-level or toolbar-level horizontal overflow by design.

`static/js/features/mailboxes.js` renders any new visual helpers from existing backend contract payloads only, stays provider-agnostic, and keeps loading/error/empty states graceful.

Frontend contract tests covering the unified mailbox page pass.

A rendered browser check inspects desktop and mobile viewports for page-level overflow, toolbar internal overflow, and key unified workspace widths.
