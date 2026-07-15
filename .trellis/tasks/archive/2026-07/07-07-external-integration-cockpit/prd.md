# External integration cockpit

## Goal

Make the existing Settings external API command center use the new `quickstart` contract as its first-class machine-client onboarding surface, so operators can see the shortest integration path and copy a secret-free starter packet without reverse-engineering the full manifest.

## Confirmed Facts

- The project uses Flask templates plus plain CSS/JS in `templates/index.html`, `static/js/main.js`, and `static/css/main.css`.
- `/api/providers` already returns `integration_manifest` and top-level `quickstart`; both are secret-free and equal by backend tests.
- The Settings API security tab already mounts `#externalApiCommandCenter` before the API key fields.
- The current command center reads `integration_manifest` for auth, discovery, workflows, recipes, and starter snippets.
- The UI design route is operational SaaS: dense, calm, scan-first, with existing repo styling instead of adding a new UI library.

## Requirements

- Add a quickstart cockpit block inside the existing external API command center.
- Prefer top-level `quickstart` and fall back to `integration_manifest.quickstart`; do not rebuild quickstart from separate UI constants when runtime data exists.
- Show auth header, recommended sequence, provider selector fields, and the primary pool/task request examples in a compact, readable layout.
- Add a copy action that copies a short, secret-free quickstart packet suitable for another service to paste into its integration docs or config notes.
- Keep the existing starter snippets, workflow playbooks, provider recipes, and endpoint cards working.
- Keep the visual treatment restrained and consistent with the current settings page.
- Add frontend contract tests and API payload checks so the UI cannot regress to manifest-only onboarding.

## Acceptance Criteria

- [ ] `static/js/main.js` stores top-level `data.quickstart` from `/api/providers` and resets it on provider catalog load failure.
- [ ] `getExternalIntegrationQuickstart()` returns top-level quickstart first and falls back to `integration_manifest.quickstart`.
- [ ] `renderExternalApiCommandCenter()` renders a quickstart cockpit section before the generic endpoint/snippet area.
- [ ] The cockpit includes auth, discovery sequence, provider selector fields, pool claim body, task temp-mail apply body, and a copy button.
- [ ] Copied quickstart text uses `<your-api-key>` and contains no provider credential key names such as `DUCKMAIL_BEARER_TOKEN`.
- [ ] i18n entries and CSS classes exist for the new quickstart cockpit.
- [ ] Focused frontend contract tests and `/api/providers` quickstart tests pass.
- [ ] No real secrets or bearer token values appear in the diff.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
