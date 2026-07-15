# Error Handling

Backend errors use two related contracts: general Flask/API errors go through `outlook_web.errors` and `middleware/error_handler.py`; external API service functions raise typed `ExternalApiError` subclasses and controllers serialize them with `external_api.ok()` / `external_api.fail()` envelopes.

## Global Error Middleware

- `outlook_web.app.create_app()` registers `ensure_trace_id`, `attach_trace_id_and_normalize_errors`, `attach_security_headers`, `handle_http_exception`, and `handle_exception`.
- API/JSON failures from middleware return `{"success": false, "error": <payload>}` where the payload comes from `build_error_payload()`.
- Non-API browser requests may return plain text with the trace ID, but API routes should return JSON envelopes.
- Unhandled exceptions must be logged with `current_app.logger.exception(...)` and returned as `INTERNAL_ERROR` without details.

## Error Payloads

- Use stable uppercase error codes such as `INVALID_PARAM`, `ACCOUNT_NOT_FOUND`, `FEATURE_DISABLED`, or `MAILBOX_CONFLICT`.
- Add Chinese and English message mappings in `outlook_web/errors.py` when a new code is user-visible or appears in public API responses.
- Include `trace_id` on server-generated errors. `generate_trace_id()` and middleware own trace IDs.
- Use `sanitize_error_details()` before storing or returning exception details that could include tokens, passwords, bearer auth, refresh tokens, or client secrets.

## External API Errors

- For external API service behavior, define or reuse subclasses of `ExternalApiError` in `services/external_api.py` with `code` and `status` class attributes.
- Controllers should catch those errors and return `jsonify(external_api_service.fail(error.code, error.message, data=error.data)), error.status`.
- External API success responses use `external_api_service.ok(data)`, producing `success`, `code`, `message`, and `data`.
- External API auth/guard failures must stay consistent between canonical `/api/v1/external/*` and legacy `/api/external/*` routes.

## Controller Validation Pattern

- Validate request JSON shape before reading fields. `controllers/external_temp_emails._json_object_body()` is the pattern for accepting only object bodies.
- Normalize and bound string/integer inputs close to the controller or service boundary.
- Audit expected external API failures with a stable code and reason before returning the error response.
- Keep fallback behavior explicit. For example, mailbox sessions may fall back from pool to task temp-mail only for disabled/empty pool cases, not for validation, permission, provider config, upstream, public-mode, or internal errors.

## Service-Level Domain Errors

- Domain services may define local exception classes when the error belongs to that service, such as `MailboxCatalogError` in `services/mailbox_catalog.py`.
- Error classes should carry a stable `code`, human message, and optional safe `data` object.
- Do not raise raw `sqlite3`, HTTP client, or provider SDK exceptions across public service/controller boundaries when callers need stable API behavior.

## Common Mistakes

- Returning different envelope shapes for the same feature across admin, external, and legacy routes.
- Exposing exception strings from provider HTTP clients or database migrations without sanitizing them.
- Adding a new error code in a controller without updating tests and user-facing message maps.
- Catching broad exceptions and silently treating them as success. Only audit logging and best-effort cleanup are allowed to swallow errors by design.
