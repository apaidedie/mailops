# External integration workflow playbooks UI

## Goal

Expose the backend `integration_manifest.workflows` contract inside Settings -> API Security so an admin or external-project maintainer can understand and copy the real discovery, mailbox directory, pool claim, and task temp-mail workflows from the same command center that already owns starter snippets.

## Background

The backend now returns secret-safe workflow recipes in `integration_manifest.workflows` from `/api/providers`, `/api/external/providers`, `/api/external/capabilities`, and OpenAPI `x-capabilities`. The Settings API Security command center already caches `/api/providers` `integration_manifest` and uses `auth`, `discovery`, `selection`, and `providers` for starter snippets, but it does not render or copy `workflows` yet.

Frontend quality guidelines require Settings -> API Security external integration UI to stay inside `#externalApiCommandCenter`, prefer `integration_manifest`, avoid provider-specific routing branches, and never read secret input fields for generated snippets.

## UI Brief

Audience: administrators and external automation developers who need a dense, trustworthy setup surface rather than marketing copy.

Primary workflow: open Settings -> API Security, check readiness, choose a workflow playbook, inspect ordered steps, then copy a secret-safe text version for another project.

Product archetype: operational SaaS dashboard.

Constraints: existing vanilla JS/CSS/templates, no new UI library, no second external integration entry point, dark/light theme support, desktop and mobile responsiveness, secret-safe output, and existing command-center starter controls must keep working.

States: loading/degraded provider catalog, missing workflows fallback, active selected workflow, copy success/failure, long endpoints, mobile stacked layout.

## Requirements

- Render a workflow playbook area inside `#externalApiCommandCenter` using `integration_manifest.workflows` from the existing `/api/providers` manifest cache.
- Keep workflow selection provider-agnostic. UI code must not branch on built-in provider names such as DuckMail, Mail.tm, GPTMail, TempMail.lol, or Emailnator.
- Provide stable fallback playbooks when `integration_manifest.workflows` is unavailable, derived from existing command-center endpoint helpers rather than a second provider registry.
- Show each workflow as a compact selectable rail with label, step count, and primary endpoint context. The selected workflow must show ordered steps with method, endpoint, request hints, response hints, and next-action hints where present.
- Add a copy action for the selected workflow that copies a secret-safe text playbook using API-key placeholders and endpoint/request metadata, not real API keys or provider tokens.
- Preserve starter snippet modes and current copy behavior.
- Add styles for desktop and mobile with stable dimensions, wrapping long paths and code fields without horizontal overflow.
- Add translations for new visible text.
- Update frontend contract tests for render hooks, helpers, CSS hooks, translations, copy behavior, manifest workflow preference, fallback behavior, and secret-safety slices.

## Out of Scope

- No backend endpoint behavior changes.
- No new provider support in this task.
- No new component library or icon package.
- No generated real credentials, masked secret values, bearer tokens, API keys, JWTs, passwords, task tokens, refresh tokens, or consumer keys.

## Acceptance Criteria

- Settings -> API Security command center renders a workflow playbook section using `getExternalIntegrationManifestWorkflows()`.
- Workflow tabs/buttons support `discover_external_api`, `browse_mailbox_directory`, `claim_pool_mailbox`, and `create_task_temp_mailbox` when the manifest exposes them.
- Selected workflow details render ordered step rows with endpoint wrapping, method badges, request/response/next metadata, and no layout-shifting interactive states.
- Copying uses `getExternalApiWorkflowPlaybookText(...)` through the selected workflow key and does not reference settings API-key or provider-secret input IDs.
- Missing workflow manifest falls back to stable playbooks from current endpoint helpers and still allows copying.
- Tests assert CSS hooks, translations, render/event hooks, workflow helper preference for manifest data, provider-agnostic source slices, and secret-safety.
- `node --check static/js/main.js`, targeted frontend tests, `git diff --check`, console debug scan, and DuckMail token scan pass.
