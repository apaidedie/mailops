# JavaScript Integration Bundle

## Goal

Bring the JavaScript external API starter client up to parity with the Python starter by adding a read-only `integration-bundle` command for Node services that need deployment planning data before starting mailbox sessions.

## Background

`examples/external_api_python_client.py` already exposes `integration-bundle`, which composes live discovery into a compact secret-free JSON object containing endpoint paths, auth placeholder, documentation links, provider selection values, templates, workflow summary, readiness summary, and OpenAPI metadata. `examples/external_api_javascript_client.js` currently supports discovery and verification-code lifecycle demos, but does not offer the same bundle command.

## Requirements

- Add a reusable JavaScript `buildIntegrationBundle(baseUrl, discovery)` helper with the same output intent as the Python helper.
- Add a CLI `integration-bundle` command to the JavaScript starter.
- Support optional `--output <path>` for writing the bundle JSON to disk, matching Python ergonomics.
- Keep the command read-only: it must use discovery only and must not start mailbox sessions, read messages, or close sessions.
- Keep output secret-safe: no API key value, provider bearer token value, claim token, task token, or message content.
- Update quickstart docs so Node users can generate the bundle too.

## Acceptance Criteria

- [ ] `node examples/external_api_javascript_client.js --base-url <url> integration-bundle` prints a compact JSON bundle built from discovery.
- [ ] `--output <path>` writes the same JSON bundle and prints the path.
- [ ] Unit tests prove the JS bundle command uses only GET discovery calls.
- [ ] Unit tests prove bundle output includes endpoint, provider selection, workflow/readiness, and OpenAPI summary data without the API key.
- [ ] `docs/external-integration-quickstart.md` documents the JavaScript bundle command next to the Python command.
