# Project Launchpad

Use this page when you need the fastest map of what Outlook Email Plus is, how to
try it, and how another service should integrate with it.

## Product Shape

Outlook Email Plus is a unified mailbox workspace for registration and
verification workflows. It aggregates long-lived accounts, temporary mailboxes,
mailbox-pool inventory, and external automation APIs behind one provider catalog
and one mailbox directory contract.

It is intentionally not a general email client. The product is optimized for
claiming a mailbox, receiving a registration email, extracting a code or link,
and closing the lifecycle safely.

## Mailbox Sources

Supported source families:

- Outlook / Microsoft Graph accounts for long-lived mailbox inventory.
- Generic IMAP accounts for Gmail, QQ, 163, self-hosted mailboxes, and similar
  providers.
- Mailbox pool claims with project-scoped reuse through `project_key`,
  `caller_id`, and `task_id`.
- Built-in temporary mailbox providers: `mail_tm`, `duckmail`, `tempmail_lol`,
  and `emailnator`.
- Cloudflare Worker temporary mail through `cloudflare_temp_mail`.
- Compatible legacy temp-mail bridge through `legacy_bridge`. Historical aliases
  such as `gptmail`, `legacy_gptmail`, and `temp_mail` normalize to this bridge.
- Future providers through the temp-mail plugin contract.

Provider routing is catalog-driven. Operators can use `TEMP_MAIL_PROVIDER`,
`EXTERNAL_POOL_DEFAULT_PROVIDER`, `ACTIVE_MAILBOX_PROVIDERS`, or
`OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE` to choose deployment-level defaults without
adding provider-specific routes.

## Two-Minute Trial Path

For Docker, start from the root README quick-start section and mount `data/` so
the SQLite database and runtime files survive container restarts.

For local development:

```bash
python -m venv .venv
pip install -r requirements.txt
python web_outlook_app.py
```

To try the unified workspace before configuring real providers, seed the local
demo database. It writes synthetic Outlook, IMAP, temp-mail, pool, verification,
and external-API activity to `output/demo/mailops-demo.db`:

```bash
python scripts/seed_demo_workspace.py --reset
```

Then start the app against that generated database:

```powershell
$env:DATABASE_PATH="output/demo/mailops-demo.db"
$env:SCHEDULER_AUTOSTART="false"
python web_outlook_app.py
```

Before handing the repository to another operator or service, run the local
readiness gate:

```bash
python scripts/project_readiness_check.py
python scripts/project_readiness_check.py --format json
```

The local gate is read-only. It does not need a running server, provider secrets,
network access, mailbox sessions, or database mutation.

For the latest local runtime handoff, including the validated startup command,
provider checklist, API smoke scope, and browser QA evidence, see
[Runtime Readiness](./runtime-readiness.md).

## External Integration Path

New external consumers should start with the integration bundle:

```bash
curl -s https://mailbox.example.com/api/v1/external/integration-bundle \
  -H "X-API-Key: <your-api-key>"
```

Then use the discovery endpoints only as needed:

- `GET /api/v1/external/capabilities` for feature, endpoint, workflow, and
  selection discovery.
- `GET /api/v1/external/providers` for provider catalog, readiness, templates,
  and provider selection rules.
- `GET /api/v1/external/mailboxes` for the external caller-visible unified
  mailbox directory.
- `GET /api/v1/external/docs` for the built-in authenticated API docs page.
- `GET /api/v1/external/openapi.json` for OpenAPI 3.1 client generation.

Use the provider-neutral mailbox session lifecycle for registration workers:

1. `POST /api/v1/external/mailbox-sessions/start`
2. `POST /api/v1/external/mailbox-sessions/read`
3. `POST /api/v1/external/mailbox-sessions/close`

Legacy `/api/external/*` routes were removed. Integrations must use canonical
`/api/v1/external/*` paths from discovery payloads. See
[migration notes](./migration/remove-legacy-external-api.md).

## Starter Clients

Copyable starter clients are available without runtime dependencies:

```bash
MAILOPS_API_KEY=<your-api-key> \
python examples/external_api_python_client.py \
  --base-url https://mailbox.example.com \
  integration-bundle

MAILOPS_API_KEY=<your-api-key> \
node examples/external_api_javascript_client.js \
  --base-url https://mailbox.example.com \
  integration-bundle
```

Use `discover` before running a mutating verification-code demo. The
`verification-code` command starts a mailbox session, reads verification mail,
and closes the lifecycle.

## Provider Configuration And Extension

For built-in providers, keep secrets in the deployment environment or Settings,
not in source control. Secret keys should be blank in shared templates, for
example:

```env
DUCKMAIL_BEARER_TOKEN=
TEMPMAIL_LOL_API_KEY=
EMAILNATOR_API_KEY=
CF_WORKER_ADMIN_KEY=
```

For future providers, prefer the plugin contract:

```bash
python web_outlook_app.py scaffold-provider <provider_key>
python web_outlook_app.py validate-provider <provider_key> --file path/to/<provider_key>.py
```

Production provider rows should report `contract_validation.status=valid` before
being enabled in `ACTIVE_MAILBOX_PROVIDERS`, `TEMP_MAIL_PROVIDER`, or
`EXTERNAL_POOL_DEFAULT_PROVIDER`.

## Live Instance Smoke Check

Before connecting a production registration worker, run the read-only external
smoke checker against the target instance:

```bash
MAILOPS_API_KEY=<your-api-key> \
python scripts/external_api_smoke.py \
  --base-url https://mailbox.example.com \
  --format json
```

The smoke checker only calls read-only discovery endpoints. It does not claim a
pool mailbox, create a task temp mailbox, read messages, finish task mailboxes,
or mutate server state.

## Deep Docs

- [External Integration Quickstart](./external-integration-quickstart.md)
- [Runtime Readiness](./runtime-readiness.md)
- [Provider Onboarding Guide](./provider-onboarding.md)
- [Temp Mail Provider Plugin Guide](./temp-mail-provider-plugin-guide.md)
- [README](../README.md)
- [English README](../README.en.md)
