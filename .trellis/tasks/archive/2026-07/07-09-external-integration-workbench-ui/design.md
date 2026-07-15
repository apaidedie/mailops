# External integration workbench UI Design

## UI Brief

- Audience: operators and developers integrating this service into another automation system.
- Primary workflow: inspect available external API paths, copy a complete mailbox session lifecycle guide, then implement against placeholders without reading admin secrets from the page.
- Product archetype: operational SaaS admin console.
- Constraints: Flask templates plus vanilla HTML/CSS/JS, existing settings card structure, existing color tokens, no new frontend framework, no provider-specific frontend branches.
- Source of truth: `/api/providers` discovery payload, `integration_manifest`, `quickstart`, workflow playbooks, and existing endpoint map fallbacks.
- States: loading and provider-catalog unavailable must still render a useful fallback; desktop and mobile layouts must avoid horizontal overflow.
- Acceptance: frontend contract tests, i18n completeness where applicable, diff whitespace checks, and rendered settings UI inspection when feasible.

## Boundaries

- Modify the existing `#externalApiCommandCenter` render path in `static/js/main.js`.
- Add CSS under the existing external API command center styles in `static/css/main.css`.
- Update frontend tests in `tests/test_settings_tab_refactor_frontend.py`.
- Add i18n strings only when visible copy is introduced.

## Data Flow

1. Load provider catalog through the existing authenticated Settings flow.
2. Cache `integration_manifest` and `quickstart` exactly as today.
3. Build a mailbox session workbench model from manifest workflows and fallback endpoint maps.
4. Render a compact lifecycle panel inside the command center.
5. Copy a placeholder-only guide using manifest auth metadata and endpoint/request field names.

## Contracts

- The session read endpoint appears as `/api/external/mailbox-sessions/read` in endpoint lists, workflow panels, and copy output.
- The panel must describe both session modes: `pool_claim` with `claim_token`, and `task_temp_mailbox` with `task_token`.
- The copy output must include safe placeholders only: `<your-api-key>`, `<claim-token>`, `<task-token>`, `<email>`, and example action names.
- New helpers must not reference credential input element IDs.
- New helpers must not branch on concrete provider names.

## Rollback

- The change is frontend-only. Reverting `static/js/main.js`, `static/css/main.css`, i18n, and frontend tests returns the UI to the prior command center behavior.
