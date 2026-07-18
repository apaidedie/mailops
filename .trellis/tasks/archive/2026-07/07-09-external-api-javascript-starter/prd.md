# External API JavaScript starter client

## Goal

Add a copyable Node.js starter client for the Outlook Email Plus external API so JavaScript services can discover the instance contract, start a provider-neutral mailbox session, read verification mail, and close the lifecycle without reimplementing request details from curl examples.

This closes the current integration gap: Python consumers already have `examples/external_api_python_client.py`, while JavaScript consumers only have prose and curl snippets.

## Confirmed Facts

- `examples/external_api_python_client.py` already implements discovery, session start/read/close, verification-code flow, typed API errors, CLI commands, and canonical v1 fallback endpoints.
- `docs/external-integration-quickstart.md` documents the smoke checker, Python starter, provider-neutral mailbox sessions, provider selection, error handling, and safety rules.
- `package.json` uses CommonJS and has Jest available, but there is no scoped JavaScript starter test script yet.
- Node v24.13.0 is available in this workspace, so the starter can rely on the Node 18+ global `fetch` API without adding runtime dependencies.

## Requirements

- Add `examples/external_api_javascript_client.js` as a dependency-free CommonJS starter for Node 18+.
- Export an importable `MailOpsClient`, `MailOpsApiError`, `DEFAULT_ENDPOINTS`, and `CANONICAL_EXTERNAL_PREFIX`.
- Mirror the Python starter's external API behavior:
  - discover live endpoints from `GET /api/v1/external/capabilities` and update the local endpoint map when `data.endpoints` is present;
  - fetch providers and OpenAPI metadata during discovery;
  - support mailbox session start, generic session read, verification-code read, close, and an end-to-end verification flow;
  - close an already-started lifecycle in a `finally` path if verification read fails;
  - reject unsupported read filter fields before sending a request;
  - raise a typed error for HTTP failures and `{ success: false }` envelopes;
  - keep canonical `/api/v1/external/*` endpoints as fallback defaults.
- Include CLI commands equivalent to the Python starter:
  - `discover` for read-only discovery;
  - `verification-code` for stateful start/read/close demonstration.
- Read API keys from `--api-key` or `MAILOPS_API_KEY` and avoid embedding provider secrets or real API keys in source/docs/tests.
- Update `docs/external-integration-quickstart.md` with JavaScript starter usage next to the Python starter.
- Add focused automated tests for the JavaScript starter.

## Acceptance Criteria

- [x] `node --check examples/external_api_javascript_client.js` succeeds.
- [x] New JavaScript starter tests cover discovery endpoint caching, verification flow request bodies, canonical fallback without discovery, close-on-read-failure behavior, envelope/API error handling, CLI environment API-key usage, CLI selector forwarding, and source secret-safety checks.
- [x] Existing Python starter and smoke script tests still pass.
- [x] Quickstart docs include copyable JavaScript `discover` and `verification-code` commands.
- [x] `git diff --check` reports no whitespace errors.

## Out of Scope

- No new external API endpoints.
- No browser package, npm publish workflow, TypeScript declarations, or generated OpenAPI client.
- No provider-specific client logic or hardcoded provider credentials.

## Notes

- This is a lightweight, independently testable examples/docs task. PRD-only planning is sufficient.
