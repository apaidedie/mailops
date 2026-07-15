# External API Smoke UI Discoverability

## Goal

Make the external API smoke checker discoverable inside the Settings -> External API command center so operators can copy the read-only verification command before connecting external registration workers.

## UI Brief

- Audience: operators and integrators configuring Outlook Email Plus as a mailbox aggregation service for other systems.
- Primary workflow: inspect readiness, copy a smoke-check command, run it in CI/deployment verification, then connect workers only after discovery passes.
- Product archetype: operational SaaS admin console; dense, calm, utilitarian, not marketing-heavy.
- Constraints: existing vanilla HTML/CSS/JS stack, no new dependencies, no Settings secret input reads, no provider-name branches, no mutable API calls from the UI.
- Source of truth: `/api/providers` discovery caches, existing external API command center, `scripts/external_api_smoke.py`, and `docs/external-integration-quickstart.md`.
- States: loading/degraded command center, missing catalog, configured/unconfigured API key status, desktop/mobile responsive layout.
- Acceptance: frontend contract tests, CSS responsive hooks, and rendered desktop/mobile checks if layout changes materially.

## Confirmed Facts

- `static/js/main.js` already renders `renderExternalApiCommandCenter()` inside `#externalApiCommandCenter`.
- The command center already has copy helpers, starter snippets, quickstart, workflow playbooks, onboarding checklist, and endpoint maps.
- `scripts/external_api_smoke.py` now validates `/api/external/health`, `/api/external/capabilities`, `/api/external/providers`, `/api/external/mailboxes?page_size=1`, and `/api/external/openapi.json`.
- Frontend specs forbid reading `settingsExternalApiKey` / provider credential inputs while rendering command-center summaries.

## Requirements

1. Add a compact smoke-check panel to the External API command center.
2. The panel must expose the exact read-only endpoints covered by `scripts/external_api_smoke.py`.
3. The panel must provide copyable shell command text that uses placeholders, not real API keys or masked values.
4. The panel must be rendered from existing discovery/command-center state and must not read Settings credential inputs.
5. The panel must preserve the existing dense operational layout and remain responsive on mobile.
6. Frontend contract tests must cover helper names, copy behavior, secret safety, and CSS hooks.
7. Documentation/spec text must state that the command center surfaces the smoke checker without executing external calls from the browser.

## Acceptance Criteria

- [ ] `tests/test_settings_tab_refactor_frontend.py` proves the command center has smoke-check helper/render/copy functions.
- [ ] Frontend tests prove the smoke panel command includes `python scripts/external_api_smoke.py`, `--base-url`, and `OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key>` or equivalent placeholder auth.
- [ ] Frontend tests prove the smoke render/copy slice does not read `settingsExternalApiKey`, `settingsExternalApiKeysJson`, provider credential inputs, or provider secret values.
- [ ] CSS tests prove smoke panel responsive hooks exist and long endpoint/command text wraps.
- [ ] Existing external API command center tests remain green.

## Out of Scope

- Running the smoke checker from the browser.
- Creating/editing API keys automatically.
- Adding new provider selection behavior.
- Redesigning the whole Settings page in this slice.
