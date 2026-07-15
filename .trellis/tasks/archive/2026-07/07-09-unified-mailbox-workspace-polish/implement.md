# Unified mailbox workspace polish Implementation Plan

## Steps

1. Read frontend guidelines and relevant thinking guides.
2. Update app shell branding and replace sidebar emoji nav icons with inline SVG symbols.
3. Update unified mailbox masthead copy and pipeline labels to clarify aggregation, provider routing, verification reads, and external API sessions.
4. Add/adjust CSS for sidebar SVG icons, brand lockup, masthead responsiveness, focus states, and reduced motion in changed UI.
5. Add i18n mappings for new copy.
6. Run focused validation and inspect diff for unrelated changes.
7. Commit, archive task, and journal the session.

## Validation Commands

- `node --check static/js/main.js`
- `node --check static/js/i18n.js`
- `node --check static/js/features/mailboxes.js`
- `npm run test:browser-extension -- --runTestsByPath tests/browser-extension/popup.integration.test.js`
- `python -m pytest tests/test_external_api_versioned_aliases.py tests/test_external_api_docs_page.py -q`
- `git diff --check`

## Risk Notes

- Do not rename element IDs used by JavaScript.
- Do not remove text labels from navigation; SVGs are decorative only.
- Avoid broad CSS rewrites because `main.css` also styles settings, overview, temp mail, and external API docs.
- Keep the first viewport dense and operational; no landing-page hero pattern.
