# Unified mailbox workspace polish Design

## Architecture

This task stays inside the existing server-rendered frontend:

- `templates/index.html` owns app shell markup and the unified mailbox page structure.
- `static/css/main.css` owns the visual system and responsive layout.
- `static/js/main.js` owns topbar title/subtitle/action rendering.
- `static/js/i18n.js` owns copy translation for dynamic and static text.

No new package, build tool, frontend framework, or icon dependency is introduced. The project currently has plain CSS/JS with Jinja templates, so the safest path is to add a small inline SVG icon set in the sidebar and extend existing CSS tokens.

## UI Direction

The app should read as a quiet technical control plane:

- tighter, professional app identity: `OutlookMail Plus` + unified mailbox service tagline;
- vector navigation glyphs instead of emoji as structural icons;
- masthead copy that names the unified mailbox fabric and the source/routing/API pipeline;
- compact metric-like pipeline chips instead of marketing hero content;
- stable dimensions and wrapping rules for small viewports.

## Boundaries

In scope:

- app shell title/sidebar/topbar copy;
- sidebar icon markup and associated CSS;
- unified mailbox masthead copy, labels, and layout polish;
- i18n entries for new copy;
- targeted tests/syntax checks.

Out of scope:

- backend provider behavior;
- mailbox DTO schema changes;
- OpenAPI/external API changes;
- redesigning every settings card or modal;
- replacing the UI stack.

## Compatibility

Existing `data-page`, `onclick`, element IDs, and mailbox view switcher IDs must remain stable because `static/js/main.js`, feature modules, and tests depend on them. Icons are decorative and should use `aria-hidden="true"` so button labels remain the text nodes already present.

## Validation

Use syntax and focused tests over broad visual snapshot infrastructure for this slice:

- parse/check changed static JS for syntax;
- run existing layout/mailbox-related Jest tests where available;
- run relevant Python tests for unified mailbox directory/external API if touched indirectly;
- run `git diff --check`.
