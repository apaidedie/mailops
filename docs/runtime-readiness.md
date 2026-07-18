# Runtime Readiness

This note is the short operational handoff for running the current project state
locally and checking that the unified mailbox, temp-mail provider catalog, and
external API discovery surfaces are usable.

## Local Run Path

Use the compatibility entrypoint for local operation:

```bash
python web_mailops_app.py
```

Useful environment controls:

- `HOST` and `PORT` choose the bind address. Local verification can use
  `HOST=127.0.0.1` and a non-default port such as `5107`.
- `SCHEDULER_AUTOSTART=false` starts the web UI without background scheduler
  jobs, which is useful for readiness checks and browser QA.
- `SECRET_KEY` must stay stable for an existing database. `start.py` can create
  one for first-run use, but operational deployments should keep it in `.env` or
  the hosting secret store.
- `LOGIN_PASSWORD` controls the initial admin login password when the database
  has not stored one yet.

## Runtime Logging

Local development keeps the existing readable text logs by default:

```env
LOG_FORMAT=text
LOG_LEVEL=INFO
```

Container deployments can emit one line-delimited JSON object per log event for
ELK or Loki collectors:

```env
LOG_FORMAT=json
LOG_LEVEL=INFO
```

JSON records include stable operational fields such as UTC timestamp, level,
logger, message, process/thread metadata, module/function/line, and request
`trace_id`, method, path, and remote address when a request context exists. The
path never includes the query string. Safe structured fields such as event,
status code, duration, provider, and endpoint are included when a call site
supplies them.

`PERF_LOGGING=true` remains backward compatible: when `LOG_LEVEL` is not set it
selects DEBUG. An explicit valid `LOG_LEVEL` takes precedence. Runtime logging
must never include API keys, bearer tokens, passwords, cookies, request bodies,
mailbox content, or complete environment/provider configuration dumps.

The process should answer:

```bash
curl http://127.0.0.1:5000/healthz
```

with a `200` response containing `status=ok`.

## Provider Configuration Checklist

The provider catalog is the source of truth for both built-in and future mailbox
providers. Check authenticated discovery first:

```bash
GET /api/providers
GET /api/providers/preflight
```

Temporary mailbox providers currently exposed to Settings are:

- `legacy_bridge`
- `cloudflare_temp_mail`
- `mail_tm`
- `duckmail`
- `tempmail_lol`
- `emailnator`

Required or optional configuration keys are documented in `.env.example` and in
the live provider discovery payload. Keep secret values out of source control and
shared docs. For DuckMail, use the Mail.tm-compatible API shape with:

```env
DUCKMAIL_API_BASE=https://api.duckmail.sbs
DUCKMAIL_BEARER_TOKEN=
```

`DUCKMAIL_BEARER_TOKEN` must be set in the runtime environment or Settings for
DuckMail to move from `needs_config` to ready. Do not put the token in README,
examples, screenshots, or issue text.

## External API Readiness

Browser access to the external API is default-deny for ordinary web origins.
Set `EXTERNAL_API_CORS_ORIGINS` to a comma- or newline-separated exact list of
`http://` or `https://` origins. `EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION`
defaults to `true` for Chrome/Edge extension compatibility. The policy applies
only to `/api/v1/external/*` and legacy `/api/v1/external/*`; internal `/api/*`
routes remain same-origin. Credentials are disabled (`supports_credentials=false`),
and approved clients may send `Content-Type`, `X-API-Key`, `X-Request-Id`, and
`X-Trace-Id`; responses expose `X-Trace-Id` for diagnostics.

External callers should discover the live instance through the canonical v1
endpoints:

```bash
GET /api/v1/external/health
GET /api/v1/external/capabilities
GET /api/v1/external/providers
GET /api/v1/external/openapi.json
GET /api/v1/external/integration-bundle
```

These endpoints require `X-API-Key`. When no external API key is configured,
they should return `401` or `403` rather than falling back to an admin session.
After configuring a key in Settings -> API Security, run:

```bash
MAILOPS_API_KEY=<your-api-key> \
python scripts/external_api_smoke.py \
  --base-url http://127.0.0.1:5000 \
  --format json
```

The smoke checker is read-only. It verifies discovery, provider catalog,
OpenAPI, integration bundle, and secret-safety behavior without claiming or
creating mailboxes.

## Latest Local Readiness Evidence

Last checked on 2026-07-09 against a local Windows development environment.

- `python web_mailops_app.py` started successfully on `127.0.0.1:5107` with
  `SCHEDULER_AUTOSTART=false`.
- `GET /healthz` returned `200` with app version `2.7.0`.
- Admin session checks passed for `/api/bootstrap`, `/api/providers`,
  `/api/providers/preflight`, `/api/mailboxes?page=1&page_size=1`, and `/`.
- Provider discovery returned `16` mailbox provider rows and temp provider
  diagnostics without exposing provider token values.
- External v1 discovery endpoints returned `401` without `X-API-Key`, as
  expected for an unconfigured public integration surface.
- A separate isolated database instance with a temporary external API key
  returned `200` from health, capabilities, providers, OpenAPI, and integration
  bundle endpoints; responses did not echo the API key.
- Browser QA rendered Settings -> Temp Mail on desktop `1440x1000` and mobile
  `390x844`, with six provider options, no console errors, and zero horizontal
  overflow at page, body, provider-mount, and active-pane levels.

## Known Follow-Ups

- Configure real `X-API-Key` access before connecting external services to the
  production instance.
- Set provider secrets, especially `DUCKMAIL_BEARER_TOKEN`, in the runtime
  environment or Settings before relying on those providers.
- Continue the next product slice by moving provider-specific configuration
  panels toward schema/catalog-driven rendering so future providers require less
  template work.
