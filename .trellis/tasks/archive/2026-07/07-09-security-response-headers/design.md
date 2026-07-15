# Security response headers middleware Design

## Architecture

Add a small middleware module, `outlook_web/middleware/security_headers.py`, and register it through `app.after_request()` in `create_app()` after trace/error middleware and before blueprint/CORS setup. The middleware is response-only and has no database or request-body dependency.

## Header Contract

Use `setdefault` semantics so a future route, reverse-proxy integration, or file-serving path can intentionally override a header.

Baseline headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()`
- `Content-Security-Policy`: compatible with the current app shape while reducing broad browser surface.

The initial CSP should be strict where safe and permissive only where the current UI requires it:

```text
default-src 'self';
base-uri 'self';
object-src 'none';
frame-ancestors 'none';
img-src 'self' data: blob:;
style-src 'self' 'unsafe-inline';
script-src 'self' 'unsafe-inline';
connect-src 'self';
font-src 'self' data:;
form-action 'self';
upgrade-insecure-requests
```

`upgrade-insecure-requests` should only be included when the request is secure or when HSTS is forced; otherwise local HTTP development can be harder to debug.

## HSTS Contract

Set `Strict-Transport-Security` when either:

- Flask sees `request.is_secure`, including ProxyFix-enabled deployments that set `X-Forwarded-Proto: https` correctly.
- `SECURITY_HEADERS_FORCE_HSTS=true` is set.

Expose config helpers in `outlook_web/config.py`:

- `get_security_headers_enabled() -> bool`, default true.
- `get_security_headers_force_hsts() -> bool`, default false.
- `get_security_hsts_max_age() -> int`, default `31536000`, with a lower bound of zero.

## Compatibility

- Do not touch response bodies.
- Do not modify CORS headers; Flask-CORS may add them independently.
- Do not change static caching behavior.
- Do not add strict CSP nonces or hashes in this task.

## Rollback

Rollback by removing the middleware registration and helper module. Config helpers are pure env readers and do not require migration.
