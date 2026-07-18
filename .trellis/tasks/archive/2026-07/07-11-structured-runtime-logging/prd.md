# Structured runtime logging

## Goal

Add production-grade structured runtime logging that can emit one JSON object per line for container log collectors while preserving the current concise text format for local development. Logs should expose safe operational context such as trace ID, request method/path, logger, level, event, status, and exception details without logging credentials, query strings, request bodies, or mailbox content.

## Confirmed Facts

- `mailops.app.create_app()` currently creates one stderr handler with `%(asctime)s %(name)s %(levelname)s %(message)s`.
- `PERF_LOGGING=true` currently raises the `mailops` namespace to `DEBUG`; default level is `INFO`.
- Request middleware already creates or forwards `g.trace_id` and returns it through `X-Trace-Id`.
- Application modules use `current_app.logger` and `mailops.*` module loggers.
- The project has logging secret-safety rules but no machine-readable runtime formatter or `LOG_FORMAT`/`LOG_LEVEL` configuration.
- Docker already writes application stdout/stderr through the container logging driver, so line-delimited JSON is sufficient for ELK/Loki collectors.

## Requirements

- Implement structured logging with the Python standard library; do not add a runtime dependency solely for JSON formatting.
- Add config helpers for `LOG_FORMAT=text|json` and `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL`.
- Preserve `PERF_LOGGING=true` as the backward-compatible DEBUG fallback when `LOG_LEVEL` is not explicitly set.
- Keep the default format and level compatible with current behavior: text + INFO.
- JSON logs must include stable top-level fields for UTC timestamp, level, logger, message, process/thread metadata, module/function/line, trace ID, request method/path, and safe structured event fields when provided.
- Exception logs must preserve exception type, message, and formatted stack data in JSON mode.
- Never add request query strings, bodies, headers, cookies, environment dumps, provider config contents, mailbox content, or secret values automatically.
- Configure the `mailops` namespace and Flask app logger without duplicate handlers or duplicate emitted lines, including repeated test configuration.
- Add focused formatter/configuration tests and an application-factory integration test proving request trace context reaches JSON logs.
- Document the new environment keys in `.env.example` and deployment/runtime documentation.
- Extend the local readiness contract so the logging configuration remains documented and discoverable.
- Mark JSON structured logging complete in `docs/项目地图.md` after verification.

## Acceptance Criteria

- [x] Default configuration produces one compatible human-readable text line at INFO level.
- [x] `LOG_FORMAT=json` produces valid line-delimited JSON with stable safe fields.
- [x] A request-context log includes the current `trace_id`, HTTP method, and path without query parameters.
- [x] `LOG_LEVEL` validation is deterministic and `PERF_LOGGING=true` remains a DEBUG fallback.
- [x] Exception logging includes structured exception data and stack text in JSON mode.
- [x] Reconfiguring logging does not multiply managed handlers or emitted lines.
- [x] `.env.example`, runtime documentation, readiness checks, and project map describe the new logging mode.
- [x] Focused tests, relevant app/security tests, readiness gate, format/lint checks, and `git diff --check` pass.

## Out Of Scope

- Shipping logs directly to Elasticsearch, Loki, Sentry, or another network service.
- Persisting runtime logs in SQLite or adding a log viewer UI.
- Rewriting every existing log call to structured `extra` fields in one task.
- Redacting arbitrary third-party exception strings beyond existing logging discipline; call sites must continue to avoid logging secret-bearing upstream payloads.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
