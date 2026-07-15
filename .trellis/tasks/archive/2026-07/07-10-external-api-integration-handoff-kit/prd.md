# External API Integration Handoff Kit

## Goal

Upgrade Settings -> API Security -> external API command center so an operator can copy one safe, professional integration handoff kit for another service or developer. The kit should package the existing Integration Bundle endpoint, placeholder auth, discovery order, smoke-check command, provider selector fields, mailbox-session lifecycle, and action-plan priorities without exposing secrets or creating new backend contracts.

## User Value

A third-party service can onboard faster because the admin UI provides one concise, copyable handoff instead of forcing the operator to manually combine README text, OpenAPI paths, provider docs, and settings state. This improves the product's automation story and moves the project closer to a polished unified mailbox aggregation service.

## Confirmed Facts

- The backend already exposes canonical external discovery through `/api/v1/external/integration-bundle`, capabilities, providers, OpenAPI, mailbox directory, and mailbox session endpoints.
- `static/js/main.js` already has an external API command center, quickstart cockpit, smoke-check panel, Integration Bundle launchpad, action plan renderer, starter snippets, provider recipes, and mailbox-session lifecycle display.
- The current frontend bundle launchpad derives an action plan locally from settings, provider catalog cache, and mailbox snapshot; the admin browser must not call API-key-protected `/api/v1/external/*` endpoints or read saved API key values.
- The main app is a Flask template plus static JS/CSS frontend; there is no frontend build framework.
- UI design skill evidence recommends a professional developer-tool direction, but repo constraints require using existing tokens, dense operational cards, responsive grids, and contract tests rather than adding new packages or a new visual system.

## Requirements

- Add a copyable External Integration Handoff Kit inside `#externalApiCommandCenter`, positioned with the Integration Bundle launchpad and before detailed metrics/readiness sections.
- Generate the handoff kit from existing client-safe frontend sources: provider integration manifest/quickstart/workflows, endpoint map, placeholder auth, local action plan projection, mailbox-session request examples, smoke-check command, and documentation paths.
- Keep the handoff kit provider-agnostic and data-driven; do not branch on specific providers such as DuckMail, Mail.tm, Emailnator, GPTMail, or TempMail.lol.
- Keep all copied and rendered content secret-safe. The kit may include placeholder auth and secret key names only when already present in safe discovery data, but must not read settings credential inputs, masked values, plaintext API key endpoints, provider bearer tokens, JWTs, passwords, task tokens, claim tokens, consumer keys, or real API keys.
- Include enough sections for a third-party developer to start work without reading the whole admin UI: base URL, auth placeholder, canonical Integration Bundle endpoint, smoke command, recommended discovery sequence, provider selector fields, mailbox-session start/read/close examples, action plan, and docs links.
- Preserve existing command-center behavior, quickstart, smoke-check, provider recipes, workflow playbooks, and mailbox-session lifecycle panels.
- Add CSS hooks and responsive layout so long endpoint URLs, command lines, JSON examples, and action items wrap without horizontal overflow on desktop and mobile.
- Add frontend contract tests for helper names, copy hook, render order, secret safety, provider-agnostic slices, i18n strings, and CSS selectors.

## Acceptance Criteria

- [x] Settings -> API Security renders an External Integration Handoff Kit inside `#externalApiCommandCenter`.
- [x] A copy button produces a single plaintext handoff document with placeholder auth, canonical bundle endpoint, smoke command, discovery sequence, selector fields, mailbox-session examples, action plan, and docs links.
- [x] Handoff generation does not reference `document.getElementById`, Settings credential input IDs, plaintext API key APIs, or provider-specific branches.
- [x] Existing quickstart, smoke-check, bundle launchpad, operational readiness, starter snippets, provider recipes, workflow playbooks, and mailbox-session lifecycle remain present.
- [x] Contract tests assert render order, copy hook, helper names, CSS hooks, i18n strings, secret safety, and provider-agnostic behavior.
- [x] Syntax, focused frontend tests, and `git diff --check` pass.
- [x] Browser QA confirms the API Security command center has no horizontal overflow on desktop and mobile.

## Out Of Scope

- Changing backend external API routes, OpenAPI schemas, or provider catalog payloads.
- Fetching `/api/v1/external/integration-bundle` from the admin browser.
- Executing the smoke checker from the browser.
- Rebuilding the entire Settings page visual system.
- Moving provider configuration storage paths.
