# Design

## Architecture

Add `outlook_web/logging_config.py` as the single owner of runtime formatter/filter/handler setup. `outlook_web.config` owns environment normalization, and `create_app()` delegates logging setup to the new module after Flask app creation.

`RequestContextFilter` enriches records only when a Flask request context exists. `JsonLogFormatter` converts a `LogRecord` into a deterministic dictionary and serializes it with `json.dumps(..., ensure_ascii=False)`. Text mode reuses the existing timestamp/name/level/message format.

## Configuration Contract

- `LOG_FORMAT`: `text` or `json`; invalid/empty values fall back to `text`.
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`; invalid/empty values fall back to `DEBUG` when `PERF_LOGGING=true`, otherwise `INFO`.
- `PERF_LOGGING`: remains accepted for backward compatibility and only affects the fallback when `LOG_LEVEL` is absent.

## JSON Contract

Always include: `timestamp`, `level`, `logger`, `message`, `process`, `thread`, `module`, `function`, and `line`.

Include when available: `trace_id`, `http_method`, `http_path`, `remote_addr`, `event`, `code`, `status`, `status_code`, `duration_ms`, `provider`, `endpoint`, `action`, `resource_type`, and `resource_id`.

For exceptions include an `exception` object with `type`, `message`, and `stack`. Do not include query strings, request bodies, headers, cookies, or environment/config snapshots.

## Handler Ownership

The `outlook_web` namespace owns one managed stderr handler and does not propagate to the root logger. The Flask app logger removes Flask's default handler and any prior managed handler, then propagates to `outlook_web`. Reconfiguration replaces only handlers marked as managed by this module so unrelated operator handlers remain intact.

## Compatibility And Rollback

Default output remains text at INFO. Existing `%s`-style log calls continue to work. A deployment can roll back JSON collection by setting `LOG_FORMAT=text`; no schema or application-data rollback is required.
