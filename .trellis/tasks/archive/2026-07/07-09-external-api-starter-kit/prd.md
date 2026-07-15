# External API starter kit

## Goal

Make Outlook Email Plus easier to adopt from external services by adding a copyable, zero-dependency Python starter client that demonstrates the canonical external API workflow: discover the live contract, start a provider-neutral mailbox session, read verification mail, and close the lifecycle.

This supports the larger product direction of turning the project into a professional unified Outlook/IMAP/temp-mail aggregation service with clean extension points and first-class API integration.

## Background / Confirmed Facts

- The project already exposes authenticated canonical external API routes under `/api/v1/external/*`, while legacy `/api/external/*` aliases remain supported.
- `GET /api/v1/external/capabilities`, `GET /api/v1/external/providers`, `GET /api/v1/external/docs`, and `GET /api/v1/external/openapi.json` are the current discovery and documentation entry points.
- `docs/external-integration-quickstart.md` explains the external workflow in prose and curl snippets.
- `scripts/external_api_smoke.py` is a read-only contract checker, not an application client. It does not start sessions, read mail, or close lifecycle handles.
- There is no `examples/` starter client that a separate service can import or copy.
- The starter must never embed real API keys, provider bearer tokens, refresh tokens, task tokens, consumer keys, mailbox passwords, or provider secret values.

## Requirements

- Add a zero-dependency Python starter client under `examples/`.
- The client must be importable by another project and also runnable as a CLI demo.
- The client must default to canonical `/api/v1/external/*` paths and prefer live `capabilities.data.endpoints` when present.
- The client must support:
  - `discover()` for capabilities, providers, and OpenAPI/doc links;
  - `start_mailbox_session(...)` using `POST /mailbox-sessions/start`;
  - `read_session(...)` using `POST /mailbox-sessions/read`;
  - `read_verification_code(...)` convenience wrapper;
  - `close_session(...)` using `POST /mailbox-sessions/close`;
  - a high-level `verification_flow(...)` helper that starts, reads, and closes in a `finally` path.
- The CLI demo must require `--base-url` and read the API key from `--api-key` or `OUTLOOK_EMAIL_PLUS_API_KEY`.
- The CLI must have a safe `discover` command that performs only read-only discovery.
- Any lifecycle demo command must make it clear that it mutates server state by starting and closing a mailbox session.
- Update the external integration quickstart and README references so users can find the starter client.
- Add tests that mock network I/O and prove endpoint selection, request bodies, lifecycle close behavior, error handling, CLI argument behavior, and secret-safe source text.

## Acceptance Criteria

- [ ] `examples/external_api_python_client.py` exists, is stdlib-only, importable, and runnable.
- [ ] The client reads canonical endpoints from discovery and falls back to `/api/v1/external/*` paths when discovery is unavailable or partial.
- [ ] The high-level verification flow closes a started session even when reading verification mail raises.
- [ ] The CLI `discover` command calls only read-only discovery endpoints.
- [ ] The example source and documentation use placeholders only, with no real provider token or plaintext API key values.
- [ ] Tests cover successful discover/start/read/close flow, close-on-error behavior, HTTP error handling, CLI env API-key fallback, and source secret-safety.
- [ ] `docs/external-integration-quickstart.md`, `README.md`, and `README.en.md` mention the starter client.
- [ ] Relevant external API and starter-kit tests pass.

## Out Of Scope

- No package publishing to PyPI or npm in this task.
- No generated SDK from OpenAPI in this task.
- No JavaScript/TypeScript client in this task.
- No broad UI redesign in this task.
- No changes to provider runtime behavior or mailbox lifecycle semantics.
