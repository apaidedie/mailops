# External integration onboarding kit design

## Boundary

This task is documentation and tooling around existing external APIs. It does not change mailbox lifecycle semantics. Runtime API changes are limited to secret-free documentation discovery metadata if needed.

## Artifacts

- `docs/external-integration-quickstart.md`: human-facing short path for third-party services.
- `scripts/external_api_smoke.py`: read-only smoke checker for a live instance.
- `tests/test_external_api_smoke_script.py`: unit tests using mocked network calls.
- README links and, if clean, provider documentation contract entry.

## Smoke Checker Contract

The script accepts `--base-url` and an API key supplied by `--api-key` or `MAILOPS_API_KEY`. It calls only read-only endpoints:

- `GET /api/external/health`
- `GET /api/external/capabilities`
- `GET /api/external/openapi.json`

It validates:

- health envelope is reachable and authenticated.
- capabilities exposes `integration_manifest`, top-level `quickstart`, `documentation`, `endpoints`, `mailbox_session`, and `external_mailbox_read_contract`.
- top-level `quickstart` equals `integration_manifest.quickstart`.
- manifest auth uses `X-API-Key` and placeholder `<your-api-key>`.
- manifest workflows include `start_mailbox_session`, `browse_mailbox_directory`, `claim_pool_mailbox`, and `create_task_temp_mailbox`.
- mailbox session discovery exposes `/api/external/mailbox-sessions/start` and the four strategy values.
- OpenAPI exposes `/api/external/mailbox-sessions/start`, `MailboxSessionStartRequest`, `MailboxSessionData`, and `MailboxSessionDiscovery`.
- serialized discovery payload does not contain obvious secret values or accidentally replaced placeholder API keys.

The checker prints concise OK/FAIL lines and exits `0` only when all required checks pass.

## Compatibility

Use only Python standard library modules so the script works before project dependencies are installed. Tests can import the script directly.

## Rollback

Remove the docs file, script, tests, README links, and any documentation contract entry added for the quickstart.
