# External API Integration Action Plan

## Goal

Make the external API readiness bundle and Settings -> API Security console more actionable for first-time and automated integrations. External services should be able to fetch one secret-safe payload, inspect a prioritized action plan, and know whether to start mailbox sessions, fix provider configuration, run smoke checks, or adjust API-key/pool access before mutating mailbox state.

This advances the broader product goal of turning the project into a professional, extensible mailbox aggregation service by improving the machine-readable onboarding path for Outlook, IMAP, pool, and temp-mail backed workflows.

## Confirmed Facts

- The repository already exposes canonical `/api/v1/external/*` routes plus legacy `/api/external/*` aliases.
- `/api/v1/external/integration-bundle` returns a secret-safe readiness bundle with `status`, `auth`, endpoint maps, docs, quickstart, readiness, provider selection, OpenAPI metadata, workflows, smoke checks, and `recommendations`.
- Settings -> API Security already renders an external API command center, integration bundle launchpad, smoke command, starter snippets, workflow playbooks, provider recipes, and mailbox session lifecycle helpers.
- `scripts/external_api_smoke.py` validates live discovery contracts and checks for obvious secret leaks.
- Existing docs tell humans how to run the smoke checker and use mailbox sessions, but the live bundle does not expose a structured, ordered action plan with commands and blocking/non-blocking semantics.
- UI stack detection found no frontend framework or component library; implementation should use the existing Flask template, vanilla JS, and CSS patterns.

## Requirements

1. Add a secret-safe `action_plan` section to the external integration bundle.
2. The action plan must be generated from existing readiness, provider readiness, endpoint, smoke-check, recommendation, and quickstart data rather than a disconnected hardcoded checklist.
3. Each action item must be machine-readable and include at least: `key`, `priority`, `status`, `blocking`, `title`, `detail`, and `endpoint` or `command` where applicable.
4. The action plan must identify both healthy next steps and remediation steps, including provider configuration gaps, pool access restrictions, disabled external pool state, empty/restricted mailbox directory, smoke-check execution, client generation, and provider-neutral mailbox session startup.
5. The action plan must never expose API key values, provider bearer tokens, passwords, JWTs, refresh tokens, consumer keys, claim tokens, task tokens, or provider secret values.
6. OpenAPI must document the new action-plan schema as part of `IntegrationBundleData`.
7. `scripts/external_api_smoke.py` must validate action-plan presence, required fields, priority/status shape, and secret safety.
8. Settings -> API Security must render the action plan inside the existing external API command center/integration bundle surface without adding a new top-level Settings entry point.
9. The rendered UI must remain compact, responsive, and readable on desktop and mobile; long endpoints and commands must wrap without horizontal overflow.
10. Human docs must mention the action plan as the first machine-readable triage surface after fetching the bundle.

## UI Brief

- Audience: operators and developers wiring external registration workers, batch jobs, or automation services.
- Primary workflow: open Settings -> API Security, confirm external readiness, copy a smoke or bundle command, and act on the next blocking item.
- Product archetype: operational SaaS/data product.
- Constraints: Flask template, vanilla JS, existing CSS tokens, no new frontend dependency, authenticated Settings surface, mobile and desktop support.
- Source of truth: live integration bundle/action plan and existing external API discovery contracts.
- States: ready, needs config, degraded, blocked, optional next step, catalog/bundle unavailable, hover/focus, mobile wrapping.
- Acceptance: contract tests, smoke script tests, frontend source contract tests, JS syntax check, focused pytest, and rendered Settings QA if UI layout changes materially.

## Acceptance Criteria

- [ ] `GET /api/v1/external/integration-bundle` includes `data.action_plan` with versioned metadata and ordered action items.
- [ ] Legacy `/api/external/integration-bundle` returns the same action plan payload.
- [ ] Action-plan items include consistent `priority`, `status`, and `blocking` semantics and at least one actionable command or endpoint for smoke/client/session steps.
- [ ] Ready bundles include non-blocking next steps for smoke check, client generation, and starting provider-neutral mailbox sessions.
- [ ] Needs-config/degraded bundles include blocking remediation items before mutation-oriented next steps.
- [ ] OpenAPI includes `IntegrationBundleActionPlan` and `IntegrationBundleActionItem` schemas and references them from `IntegrationBundleData`.
- [ ] `scripts/external_api_smoke.py` fails when `action_plan` is missing, malformed, or contains obvious secret values.
- [ ] Settings -> API Security renders action-plan cards/rows inside the existing external API command center and exposes stable CSS/JS hooks.
- [ ] Frontend tests assert the action-plan renderer, copy-safe command rendering, event/render integration, and responsive CSS hooks.
- [ ] Docs describe fetching `action_plan` from the readiness bundle and using it before mutating mailbox state.
- [ ] Existing external API, provider, mailbox session, and Settings tests remain green.

## Out Of Scope

- Building a separate public documentation site.
- Adding a new frontend framework, charting library, component library, or build pipeline.
- Changing external API authentication semantics.
- Changing provider runtime behavior or adding a new mailbox provider in this slice.
- Replacing existing `recommendations`; this slice may keep them and add `action_plan` as the richer contract.
