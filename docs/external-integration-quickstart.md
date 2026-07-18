# External Integration Quickstart

This is the shortest path for connecting a registration worker, batch job, or another service to Outlook Email Plus.

Use this guide when you want to consume mailbox sessions from an existing Outlook Email Plus instance. Use [Provider Onboarding Guide](./provider-onboarding.md) when you are adding or configuring mailbox providers.

## Prerequisites

- A running Outlook Email Plus instance, for example `https://mailbox.example.com`.
- An external API key. Send it as `X-API-Key`.
- If you need pool-backed sessions from a multi-key consumer, that key must have pool access enabled. Keys without pool access can still use `source_strategy=task_temp_only`.

Do not put provider secrets in client code. Keep provider credentials such as `DUCKMAIL_BEARER_TOKEN`, `GPTMAIL_API_KEY`, `TEMPMAIL_LOL_API_KEY`, or `EMAILNATOR_API_KEY` in the Outlook Email Plus deployment environment or settings.

Browser clients also require an explicit server allowlist. Configure
`EXTERNAL_API_CORS_ORIGINS=https://console.example.com` with exact HTTP(S)
origins; wildcards are rejected. Chrome/Edge extensions remain enabled by
default and can be disabled with `EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION=false`.
This policy covers only `/api/v1/external/*` (legacy `/api/external/*` was removed), uses
`supports_credentials=false`, accepts API-key and request/trace headers, and
exposes `X-Trace-Id`. CORS does not replace `X-API-Key` authentication.

## 0. Local Repository Readiness Gate

Before publishing a fork, cutting a release, or handing the project to another service, run the local repository gate:

```bash
python scripts/project_readiness_check.py
```

For CI or release pipelines, use JSON output:

```bash
python scripts/project_readiness_check.py --format json
```

This checker is local-only and read-only. It does not need a running server, API key, network access, provider secrets, mailbox sessions, or database mutation. It verifies that the repository still contains the integration docs, env/provider config examples, starter clients, live smoke checker, provider plugin template, key external API tests, canonical `/api/v1/external/*` references, placeholder auth, and no obvious checked-in secret values.

## 1. Smoke Check The Instance

Run the read-only checker before wiring a worker to the instance:

```bash
python scripts/external_api_smoke.py \
  --base-url https://mailbox.example.com \
  --api-key <your-api-key>
```

Or pass the key through the environment:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
python scripts/external_api_smoke.py --base-url https://mailbox.example.com
```

For CI or deployment gates, request machine-readable JSON:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
python scripts/external_api_smoke.py \
  --base-url https://mailbox.example.com \
  --format json
```

JSON mode prints a summary object to stdout on contract checks, including `success`, totals, `checks`, `failures`, and the read-only endpoints tested. Setup or fetch errors print a JSON error object to stderr. Exit codes stay the same in both formats: `0` means all checks passed, `1` means contract checks failed, and `2` means the smoke checker could not complete setup or fetch a required discovery document.

The checker only calls:

- `GET /api/v1/external/health`
- `GET /api/v1/external/capabilities`
- `GET /api/v1/external/integration-bundle`
- `GET /api/v1/external/providers`
- `GET /api/v1/external/mailboxes?page_size=1`
- `GET /api/v1/external/openapi.json`

It does not claim pool mailboxes, create task temp-mailboxes, read messages, release claims, complete claims, or finish task mailboxes.

The checker validates the provider-neutral discovery surface that external workers depend on:

- Health readiness exposes database, provider, mailbox-directory, pool, and task-temp status sections.
- Health readiness `next_endpoints`, capabilities `endpoints`, documentation entries, integration-manifest discovery, and OpenAPI paths all point new clients at canonical `/api/v1/external/*` routes.
- Legacy `/api/external/*` routes are removed; discovery reports `compatibility.legacy_supported=false`.
- Provider preflight is discoverable through `provider_preflight=/api/v1/external/providers/preflight` without running provider probes.
- Provider and unified mailbox readiness summaries expose selector fields, routing matrix scopes, capability matrix workflow groups, compact provider rows, and non-negative counters.
- Mailbox-session start/close paths, OpenAPI schemas, workflow keys, and obvious secret-value leaks are checked.

Use this as a deployment gate before connecting a production worker. A failure usually means discovery drift, missing provider readiness data, a broken OpenAPI/docs pointer, or an accidental secret leak. Fix those first; do not work around them in the external consumer.

## 2. Try The Copyable Starter Clients

The zero-dependency starter client in `examples/external_api_python_client.py` is importable by another service and also works as a CLI demo. Use the read-only `discover` command first:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
python examples/external_api_python_client.py \
  --base-url https://mailbox.example.com \
  discover
```

For deployment planning, fetch the live readiness bundle at `/api/v1/external/integration-bundle` or generate the same compact bundle through the starter client:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
python examples/external_api_python_client.py \
  --base-url https://mailbox.example.com \
  integration-bundle \
  --output ./mailops.integration.json
```

JavaScript services can generate the same bundle without installing packages:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
node examples/external_api_javascript_client.js \
  --base-url https://mailbox.example.com \
  integration-bundle \
  --output ./mailops.integration.json
```

For CI logs or a quick operator check, ask either starter client for only the action-plan summary:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
python examples/external_api_python_client.py \
  --base-url https://mailbox.example.com \
  integration-bundle \
  --summary
```

The summary keeps `status`, summary counters, blocking item keys, action-required keys, ready next steps, and safe endpoint or placeholder command targets. Use it to stop automation before mailbox-session mutation when `blocking_keys` or `action_required_keys` are non-empty.

The bundle is read-only. It contains discovered endpoints, auth placeholder, documentation entries, provider values, env/provider-config templates, workflow keys, readiness counters, and an OpenAPI summary. It does not include the API key, provider secrets, mailbox sessions, claim tokens, task tokens, or message content.

Read `data.action_plan` before mutating mailbox state. It is a versioned, machine-readable triage list with prioritized items such as `configure_providers`, `probe_mailbox_directory`, `run_smoke_check`, `generate_client`, and `start_mailbox_session`. Run blocking or `action_required` items before starting mailbox sessions; ready bundles still include non-blocking next steps for smoke checks, client generation, and provider-neutral session startup. Commands in the plan use placeholders such as `<your-api-key>` and `<your-base-url>` only.

The Node.js starter client in `examples/external_api_javascript_client.js` provides the same discovery and session lifecycle helpers for JavaScript services. It requires Node 18+ and no runtime package install:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
node examples/external_api_javascript_client.js \
  --base-url https://mailbox.example.com \
  discover
```

Both starters discover live endpoints from `capabilities.data.endpoints` and fall back to canonical `/api/v1/external/*` paths when discovery is partial.

For an end-to-end verification-code demo, use `verification-code`. This command mutates server state: it starts a mailbox session, reads verification mail, and closes the lifecycle in a `finally` path.

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
python examples/external_api_python_client.py \
  --base-url https://mailbox.example.com \
  verification-code \
  --caller-id registration-worker-1 \
  --task-id signup-demo-1 \
  --source-strategy task_temp_only \
  --provider-name mail_tm
```

The JavaScript command accepts the same selector fields:

```bash
OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> \
node examples/external_api_javascript_client.js \
  --base-url https://mailbox.example.com \
  verification-code \
  --caller-id registration-worker-1 \
  --task-id signup-demo-1 \
  --source-strategy task_temp_only \
  --provider-name mail_tm
```

## 3. Discover The Contract

Start with capabilities:

```bash
curl -s https://mailbox.example.com/api/v1/external/capabilities \
  -H "X-API-Key: <your-api-key>"
```

Use these fields first:

- `data.action_plan` from `/api/v1/external/integration-bundle`: prioritized remediation and next actions.
- `data.quickstart`: compact endpoint, request, selector, and workflow hints.
- `data.integration_manifest`: full machine-readable workflows and deployment hints.
- `data.readiness_summary.capability_matrix` from provider discovery, or `data.readiness.providers.capability_matrix` from the integration bundle: provider-neutral workflow support, selector fields, read actions, lifecycle actions, and configuration status.
- `data.mailbox_session`: provider-neutral mailbox session start/read/close contract.
- `data.external_mailbox_read_contract`: read, wait, verification-code, and verification-link actions.
- `data.documentation`: stable links to human docs and OpenAPI.

Generated clients can also fetch:

```bash
curl -s https://mailbox.example.com/api/v1/external/openapi.json \
  -H "X-API-Key: <your-api-key>"
```

## 4. Start A Mailbox Session

For most external workers, prefer the provider-neutral session endpoint:

```bash
curl -s -X POST https://mailbox.example.com/api/v1/external/mailbox-sessions/start \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "caller_id": "registration-worker-1",
    "task_id": "signup-20260708-0001",
    "source_strategy": "pool_first",
    "provider": "auto",
    "provider_name": "mail_tm",
    "project_key": "project-a"
  }'
```

Supported `source_strategy` values:

- `pool_first`: try the pool, then fall back to task temp-mail only when the pool is disabled or empty.
- `task_temp_first`: start with task temp-mail. This is treated as a pool-including strategy for restricted multi-key permission checks.
- `pool_only`: use pool lifecycle only.
- `task_temp_only`: use task temp-mail lifecycle only. This is the right choice for API keys without pool access.

The response `data` is a `MailboxSessionData` object. Important fields:

- `session_type`: `pool_claim` or `task_temp_mailbox`.
- `email`: mailbox address to use in the target signup flow.
- `lifecycle`: contains the claim or task token required by follow-up lifecycle actions.
- `next_actions`: machine-readable read and finish/release actions.
- `external_mailbox_read_contract`: the full read contract for this lifecycle.

## 5. Read Verification Mail

Prefer the session read endpoint so your worker does not branch between pool claims and task temp-mailboxes. Send the `session_type`, `email`, and lifecycle handle from the start response. For a simple verification-code read from a pool-backed session:

```bash
curl -s -X POST https://mailbox.example.com/api/v1/external/mailbox-sessions/read \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "pool_claim",
    "read_action": "verification_code",
    "caller_id": "registration-worker-1",
    "task_id": "signup-20260708-0001",
    "email": "user@example.com",
    "claim_token": "clm_xxx",
    "since_minutes": 10
  }'
```

For a task temp-mailbox session, use the `task_token` from `data.lifecycle.task_token` instead of `claim_token`:

```bash
curl -s -X POST https://mailbox.example.com/api/v1/external/mailbox-sessions/read \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "task_temp_mailbox",
    "read_action": "verification_code",
    "caller_id": "registration-worker-1",
    "task_id": "signup-20260708-0001",
    "task_token": "tmptask_xxx",
    "since_minutes": 10
  }'
```

The response `data.result` has the same shape as the underlying read action result. Supported `read_action` values are `messages`, `latest_message`, `message_detail`, `message_raw`, `verification_code`, `verification_link`, and `wait_message`.

The direct read endpoints are also available under the canonical v1 prefix. For example:

```bash
curl -s 'https://mailbox.example.com/api/v1/external/verification-code?email=user@example.com&since_minutes=10' \
  -H "X-API-Key: <your-api-key>"
```

For high-concurrency workers, use session read with async wait mode:

```bash
curl -s -X POST https://mailbox.example.com/api/v1/external/mailbox-sessions/read \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "pool_claim",
    "read_action": "wait_message",
    "caller_id": "registration-worker-1",
    "task_id": "signup-20260708-0001",
    "claim_token": "clm_xxx",
    "mode": "async",
    "timeout_seconds": 60,
    "poll_interval": 5
  }'
```

The direct wait endpoint is still available for clients that do not use session reads:

```bash
curl -s 'https://mailbox.example.com/api/v1/external/wait-message?email=user@example.com&mode=async&timeout_seconds=60&poll_interval=5' \
  -H "X-API-Key: <your-api-key>"
```

Then poll the returned probe:

```bash
curl -s https://mailbox.example.com/api/v1/external/probe/<probe-id> \
  -H "X-API-Key: <your-api-key>"
```

## 6. Close The Lifecycle

Prefer the unified close endpoint for both session types. Send the `session_type` from the start response plus the lifecycle handles that apply to that session:

```bash
curl -s -X POST https://mailbox.example.com/api/v1/external/mailbox-sessions/close \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "pool_claim",
    "account_id": 123,
    "claim_token": "clm_xxx",
    "caller_id": "registration-worker-1",
    "task_id": "signup-20260708-0001",
    "result": "success"
  }'
```

For a task temp-mailbox session, close with the task token from `data.lifecycle.task_token`:

```bash
curl -s -X POST https://mailbox.example.com/api/v1/external/mailbox-sessions/close \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "task_temp_mailbox",
    "task_token": "tmptask_xxx",
    "caller_id": "registration-worker-1",
    "task_id": "signup-20260708-0001",
    "result": "success"
  }'
```

For pool sessions, `result=release` releases the claim back to the pool. Other valid pool result values, such as `success`, complete the claim through the pool lifecycle.

Specialized lifecycle endpoints remain available for existing integration styles:

- `POST /api/v1/external/pool/claim-complete`
- `POST /api/v1/external/pool/claim-release`
- `POST /api/v1/external/temp-emails/{task_token}/finish`

Use only `/api/v1/external/*` paths from discovery payloads. Legacy `/api/external/*` routes return 404; see `docs/migration/remove-legacy-external-api.md`.

## Provider Selection

Read allowed provider values from the live instance instead of hardcoding them:

- `data.selection_policy.scopes.explicit_pool_claim.allowed_values` for request field `provider`.
- `data.selection_policy.scopes.task_temp_apply.allowed_values` for request field `provider_name`.

Deployment-level routing priority is always:

1. environment variables
2. provider config file
3. settings page values
4. built-in defaults

Useful deployment keys:

- `ACTIVE_MAILBOX_PROVIDERS`: restrict enabled providers.
- `TEMP_MAIL_PROVIDER`: default temp-mail provider.
- `EXTERNAL_POOL_DEFAULT_PROVIDER`: default pool claim provider.
- `OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE`: JSON/TOML provider selection file.

## Error Handling

Check both HTTP status and response body:

- `UNAUTHORIZED`: missing or invalid API key.
- `FORBIDDEN`: the current key cannot access the requested mailbox or pool workflow.
- `FEATURE_DISABLED`: public-mode or server-side feature switch disabled the endpoint.
- `RATE_LIMIT_EXCEEDED`: caller exceeded configured limits.
- `INVALID_PARAM`: invalid request field or value.
- `no_available_account`: pool has no matching mailbox. This can use HTTP 200 in current pool responses, so always inspect `success` and `code`.

## Safety Rules

- Keep API keys and provider credentials outside source control.
- Treat `claim_token` and `task_token` as lifecycle handles. Store them only for the active registration task.
- Use `task_temp_only` for restricted consumers that should not touch the pool.
- Use the smoke checker in CI or deployment verification before enabling workers.
