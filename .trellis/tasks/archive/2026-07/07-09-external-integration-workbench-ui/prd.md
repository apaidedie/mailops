# External integration workbench UI

## Goal

Improve the Settings > API Security external integration command center so an operator can understand and copy the full external mailbox integration path from one place: discover API capabilities, choose a mailbox source, start or claim a mailbox session, read messages or verification codes through the unified session read endpoint, then close or complete the lifecycle.

## Background

- The backend now exposes a provider-agnostic mailbox session read endpoint for pool claims and task temp mailboxes.
- The Settings UI already has an external API command center, quickstart cockpit, smoke check, provider recipes, workflow playbooks, provider workbench, preflight console, and integration guide.
- The next product gap is not another external entry point; it is making the existing command center show the complete start -> read -> close flow in a dense, copyable, secret-safe way.
- The UI stack is Flask templates plus vanilla HTML/CSS/JS. No new frontend framework should be introduced.

## Requirements

- Keep the enhancement inside the existing `#externalApiCommandCenter`; do not create a second external integration surface.
- Surface the unified mailbox session lifecycle in the Settings UI using existing discovery data from `integration_manifest`, `quickstart`, and endpoint maps.
- Include the new `POST /api/external/mailbox-sessions/read` capability in the visible endpoint/workflow surface when discovery data is available, with a fallback that remains useful before provider catalog loads.
- Provide copyable, provider-agnostic integration material that demonstrates both `session_type=pool_claim` + `claim_token` and `session_type=task_temp_mailbox` + `task_token` read shapes without exposing secret values.
- Preserve the existing secret-safety rules: new UI/helper slices must not read credential input IDs or masked/plain secret values.
- Preserve provider-agnostic frontend logic: no provider-specific branches for DuckMail, mail.tm, TempMail.lol, Emailnator, GPTMail, or legacy bridge behavior.
- Keep the operational UI dense, professional, responsive, and consistent with the existing CSS token system.
- Update tests to cover the new UI contract, secret-safety boundary, and responsive styling hooks.

## Acceptance Criteria

- [ ] `static/js/main.js` renders a mailbox session workflow panel from backend discovery/fallback contracts and inserts it in the existing external API command center.
- [ ] The panel shows start, read, and close/finish steps for both pool-claim and task-temp-mailbox sessions using endpoint names and request fields rather than provider-specific logic.
- [ ] A copy action exports a complete, placeholder-based session workflow guide that includes `/api/external/mailbox-sessions/read`, `session_type`, `claim_token`, `task_token`, and read actions such as `verification_code` or `latest_message`.
- [ ] `static/css/main.css` provides stable desktop/mobile layout rules for the new panel without horizontal overflow.
- [ ] `tests/test_settings_tab_refactor_frontend.py` covers helper names, copy wiring, secret-safe/provider-agnostic slices, endpoint surfacing, and CSS/i18n hooks.
- [ ] Relevant frontend/i18n/unit checks pass.

## Out Of Scope

- No backend API redesign in this task.
- No new provider integration in this task.
- No new frontend framework or icon library in this task.
- No destructive cleanup of unrelated Settings panels.
