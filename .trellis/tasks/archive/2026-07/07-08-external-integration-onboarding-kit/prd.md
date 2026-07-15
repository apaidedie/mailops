# External integration onboarding kit

## Goal

External developers should have a short, reliable path to connect another service to Outlook Email Plus without reading the full README or reverse-engineering the API surface. The kit should explain the recommended unified mailbox session workflow and provide a non-mutating smoke checker that validates a running instance exposes the expected discovery, manifest, OpenAPI, and documentation contracts.

## Background

The project now exposes provider discovery, unified mailbox directory, task temp-mail, pool lifecycle, external read actions, OpenAPI, and the provider-neutral mailbox session start endpoint. The current README and API docs contain useful details, but the integration path is spread across long documents. A professional integration surface needs a concise entry point and a repeatable verification tool.

## Requirements

- Add a dedicated external integration quickstart document aimed at registration workers and third-party services.
- Explain the preferred discovery sequence: health, capabilities, quickstart or integration manifest, OpenAPI, mailbox session start, read actions, and lifecycle finish or release.
- Include copy-paste examples using placeholders only, never real API keys or provider secret values.
- Document the non-mutating readiness checks a new integrator should run before creating mailbox sessions.
- Add a script that checks a live instance with `X-API-Key` and validates health, capabilities, OpenAPI, integration manifest, quickstart parity, mailbox session discovery, provider selection fields, and secret-safety markers.
- Keep the script read-only by default. It must not claim pool mailboxes, create task temp-mailboxes, finish tasks, release claims, or read messages.
- Add focused tests for the script using mocked HTTP responses, including success and at least one missing-contract failure.
- Link the quickstart from README and documentation discovery when appropriate, without disrupting existing provider onboarding docs.
- Do not echo real DuckMail bearer tokens or any user-provided secret.

## Acceptance Criteria

- `docs/external-integration-quickstart.md` exists and gives a concise external integration path, including the new mailbox session start endpoint.
- `scripts/external_api_smoke.py` validates a base URL and API key through read-only external endpoints and returns a non-zero exit code when required contract fields are missing.
- Tests cover the smoke checker success path and a failure path.
- README points external integrators to the new quickstart.
- Discovery documentation contract includes the new quickstart as a stable documentation entry if the provider documentation contract supports it cleanly.
- Focused tests and script help output pass.
- Secret scan over changed files finds no real token values.

## Out Of Scope

- UI/UX redesign.
- Changing external API runtime behavior.
- Mutating end-to-end tests that claim or create mailboxes against a live instance.
- Adding new mailbox providers.
