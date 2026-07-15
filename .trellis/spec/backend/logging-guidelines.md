# Logging Guidelines

The project uses Python `logging` for operational logs and SQLite audit logs for user/API activity. Logs are useful for diagnosing mailbox/provider flows, but they must never expose credentials or live mailbox contents.

## Runtime Logging

- `outlook_web.logging_config.configure_runtime_logging()` owns the managed stderr handler for the `outlook_web` namespace and Flask app logger propagation.
- Default output is text with format `%(asctime)s %(name)s %(levelname)s %(message)s`; `LOG_FORMAT=json` selects line-delimited JSON.
- Default logger level is `INFO`; explicit `LOG_LEVEL` wins, while `PERF_LOGGING=true` remains the backward-compatible `DEBUG` fallback when `LOG_LEVEL` is absent.
- Use `current_app.logger.exception(...)` for unexpected server errors so tracebacks are preserved in server logs while API responses remain sanitized.
- Prefer module loggers under the `outlook_web.*` namespace for new service logs.

## Scenario: Runtime Text And JSON Logging

### 1. Scope / Trigger

Trigger: changes to application startup logging, `outlook_web.*` logger handlers, Flask `app.logger`, runtime log environment keys, request trace enrichment, JSON fields, or container log collection behavior.

### 2. Signatures

- `outlook_web.config.get_log_format() -> str`
- `outlook_web.config.get_log_level() -> str`
- `outlook_web.logging_config.RequestContextFilter`
- `outlook_web.logging_config.JsonLogFormatter`
- `outlook_web.logging_config.configure_runtime_logging(app, *, stream=None, log_format=None, log_level=None) -> logging.Handler`
- Environment: `LOG_FORMAT`, `LOG_LEVEL`, and legacy `PERF_LOGGING`.

### 3. Contracts

`LOG_FORMAT` accepts `text` or `json`; invalid/empty input falls back to `text`. `LOG_LEVEL` accepts `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`; invalid/empty input falls back to `DEBUG` only when `PERF_LOGGING=true`, otherwise `INFO`.

JSON output is one object per line. Stable fields are `timestamp` (UTC ISO-8601 with `Z`), `level`, `logger`, `message`, `process`, `thread`, `module`, `function`, and `line`. Request logs add `trace_id`, `http_method`, `http_path`, and `remote_addr` when available. Safe structured extras are allowlisted: `event`, `code`, `status`, `status_code`, `duration_ms`, `provider`, `endpoint`, `action`, `resource_type`, and `resource_id`.

The automatic request context must use `request.path`, never a full URL or query string. It must not add request bodies, headers, cookies, environment values, provider config contents, mailbox content, API keys, bearer tokens, passwords, task/claim tokens, JWTs, or arbitrary `LogRecord` extras.

The `outlook_web` namespace owns one managed handler and does not propagate to the root logger. Flask's default handler is removed from `app.logger`, which then propagates to the namespace handler. Reconfiguration replaces only handlers marked as managed so tests and reloads do not multiply output or remove operator-owned handlers.

### 4. Validation & Error Matrix

- Default environment -> readable text at INFO.
- `LOG_FORMAT=json` -> valid line-delimited JSON.
- Invalid `LOG_FORMAT` -> text fallback.
- Explicit valid `LOG_LEVEL` plus `PERF_LOGGING=true` -> explicit level wins.
- No request context -> omit request fields without raising.
- Request with query parameters -> include path only; omit query string.
- Exception log -> include `exception.type`, `exception.message`, and formatted `exception.stack`.
- Repeated configuration -> exactly one managed namespace handler and one emitted line.

### 5. Good/Base/Bad Cases

- Good: `current_app.logger.info("request complete", extra={"event": "request_complete", "duration_ms": 42})` produces optional safe fields in JSON mode and remains readable in text mode.
- Good: a 404 warning has the same `trace_id` as the `X-Trace-Id` response header.
- Base: existing `%s`-style messages continue to work without conversion to structured extras.
- Bad: attaching separate managed handlers to both `app.logger` and `outlook_web`, which emits every Flask line twice.
- Bad: serializing `record.__dict__` wholesale, which can expose arbitrary secret-bearing extras.
- Bad: logging `request.url`, `request.query_string`, request bodies, headers, or cookies automatically.

### 6. Tests Required

- Config tests must cover defaults, invalid values, explicit levels, and `PERF_LOGGING` compatibility.
- Formatter tests must cover stable fields, safe extra allowlisting, request trace/method/path, query exclusion, exception structure, and text compatibility.
- Handler tests must cover repeated configuration and Flask app logger propagation.
- App-factory integration must prove a real request log trace matches the response header.
- Operational QA for JSON mode should start an isolated process, request an error path, parse stderr as JSON, and confirm no query leakage.
- Run error/trace and security-header regressions because the shared Flask app factory changes.

### 7. Wrong vs Correct

#### Wrong

```python
handler = logging.StreamHandler()
app.logger.addHandler(handler)
logging.getLogger("outlook_web").addHandler(handler)
payload = record.__dict__
```

#### Correct

```python
configure_runtime_logging(app)
current_app.logger.info(
    "mailbox refresh complete",
    extra={"event": "mailbox_refresh", "duration_ms": elapsed_ms},
)
```

## Audit Logging

- Use `outlook_web.audit.log_audit()` for app-side audit events and `external_api_service.audit_external_api_access()` for external API access logs.
- Audit records should include stable action/resource/endpoint/status details and the request trace ID when available.
- Audit logging is best-effort and must not break primary user flows. This exception is intentional; do not copy silent failure handling to normal writes.

## What To Log

- Startup and migration diagnostics that help operators understand upgrade state, schema version, and trace IDs.
- External API access status, endpoint, stable error code, caller/task identifiers when safe, and feature-disabled reasons.
- Provider readiness/config status as key names, provider names, counts, and status codes.
- Unexpected exceptions with trace ID and sanitized context.

## What Not To Log

- API keys, provider bearer tokens, refresh tokens, task tokens, claim tokens, JWTs, mailbox passwords, IMAP passwords, consumer keys, OAuth secrets, or decrypted account credentials.
- Full mailbox message content, raw MIME content, verification links with sensitive tokens, or screenshots/export data with live mailbox details.
- Complete environment dumps or provider config file contents.

## Patterns

```python
current_app.logger.exception("Unhandled exception trace_id=%s", trace_id_value or "unknown")
```

```python
external_api_service.audit_external_api_access(
    action="external_api_access",
    email_addr=email_addr,
    endpoint=endpoint,
    status="error",
    details={"code": "INVALID_PARAM", "reason": "json_body_not_object"},
)
```

## Common Mistakes

- Logging provider exception bodies without redaction. Provider upstream errors often include authorization headers or token-like request IDs.
- Using `print()` in request-path code. Reserve prints for startup/migration operator notices already present in `db.py`; use logging elsewhere.
- Adding noisy debug logs to polling or batch operations without guarding them behind `PERF_LOGGING` or a targeted test helper.
