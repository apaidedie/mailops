# External API starter kit Design

## Architecture

Add one stdlib-only Python module:

- `examples/external_api_python_client.py`

The module owns a small `MailOpsClient` class over `urllib.request` and JSON. It should be easy to copy into an external service and should not import project internals.

## Client Contract

Constructor:

- `MailOpsClient(base_url: str, api_key: str, timeout: float = 20.0)`

Core methods:

- `discover() -> dict[str, Any]`
  - GET capabilities, providers, and OpenAPI JSON.
  - Cache `capabilities.data.endpoints` for subsequent calls.
- `start_mailbox_session(...) -> dict[str, Any]`
  - POST JSON to `mailbox_session_start` endpoint.
  - Required caller-controlled fields: `caller_id`, `task_id`.
  - Optional selectors: `source_strategy`, `provider`, `provider_name`, `email_domain`, `project_key`, `prefix`, `domain`.
- `read_session(...) -> dict[str, Any]`
  - POST JSON to `mailbox_session_read` endpoint.
  - Accepts session type, read action, caller/task identifiers, lifecycle handles, and common read filters.
- `read_verification_code(...) -> dict[str, Any]`
  - Thin wrapper around `read_session(read_action="verification_code")`.
- `close_session(...) -> dict[str, Any]`
  - POST JSON to `mailbox_session_close` endpoint.
- `verification_flow(...) -> dict[str, Any]`
  - Start session, read verification code, and close in `finally`.
  - Return a compact object containing `session`, `verification`, and `close` data.

## CLI Contract

Subcommands:

- `discover`: read-only capabilities/providers/openapi discovery.
- `verification-code`: stateful demo that starts a session, reads a verification code, and closes it.

Common flags:

- `--base-url` required.
- `--api-key` optional, defaults to `MAILOPS_API_KEY`.
- `--timeout` optional.

`verification-code` flags:

- `--caller-id`, `--task-id`, `--source-strategy`, `--provider`, `--provider-name`, `--email-domain`, `--project-key`, `--prefix`, `--domain`, `--since-minutes`, `--result`.

## Error Handling

Raise `MailOpsApiError` on HTTP errors, non-object JSON, or response envelopes with `success=false`. The exception should expose `status`, `code`, and `payload` when available.

## Secret Safety

The example source and docs may contain placeholder strings only:

- `<your-api-key>`
- `MAILOPS_API_KEY`
- fake caller/task IDs

They must not include provider bearer token examples, real API keys, refresh tokens, consumer keys, task token literals with realistic secret values, or mailbox passwords.

## Compatibility

Use canonical v1 fallbacks. Legacy endpoints stay available in the server but new starter code should only use legacy paths if a future server explicitly returns them in discovery; this task will not implement a legacy fallback preference.

## Validation

Add unit tests with mocked transport so no network or real server is required.
