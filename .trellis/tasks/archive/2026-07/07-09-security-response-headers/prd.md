# Security response headers middleware

## Goal

Add a production-grade security response header baseline to the Flask app so self-hosted and public deployments get safer browser behavior by default without breaking the existing admin UI, external API, browser extension CORS, static assets, SSE, or JSON endpoints.

This closes the high-priority item in `docs/项目地图.md`: security response headers are currently missing even though the app already has CSRF, API-key auth, rate limits, trace IDs, and CORS for extension-facing external APIs.

## Confirmed Facts

- `mailops/app.py` currently registers trace/error after-request handling, static cache headers, blueprint routes, and CORS for `/api/external/*` and `/api/v1/external/*`.
- No centralized middleware currently sets `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, or HSTS.
- The UI uses existing inline scripts/styles and template event handlers, so an enforcing CSP cannot be too strict in this first pass.
- HSTS should not be forced on local HTTP development responses, but should be available for secure/proxied production requests.
- Existing CORS headers for browser-extension external API paths must remain intact.

## Requirements

- Add a reusable response-header middleware under `mailops/middleware` and register it in `create_app()`.
- Set these baseline headers when the response does not already define them:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy` denying high-risk browser capabilities that the app does not use.
  - `Content-Security-Policy` with a compatibility baseline that permits current same-origin assets and existing inline code, while restricting object/embed/frame/base targets.
- Add `Strict-Transport-Security` only when the request is secure or when an explicit env setting enables it for proxied deployments.
- Do not overwrite route-specific headers such as `Cache-Control`, `Content-Type`, `X-Trace-Id`, or CORS headers.
- Do not break extension CORS preflight for external API paths.
- Update `docs/项目地图.md` to mark the security response header item complete.

## Acceptance Criteria

- [ ] HTML and JSON responses include the baseline security headers.
- [ ] Static file responses keep their existing `Cache-Control` behavior and also receive security headers.
- [ ] HTTPS or forced-HSTS requests include `Strict-Transport-Security`; ordinary local HTTP requests do not.
- [ ] External API CORS preflight still includes `Access-Control-Allow-Origin` for extension origins while also receiving security headers.
- [ ] Tests cover default headers, no overwrite behavior, HSTS behavior, static cache interaction, and CORS compatibility.
- [ ] Project map marks security response headers as completed.

## Notes

- This task intentionally does not remove inline JavaScript or implement nonce/hash CSP. That is a larger UI refactor and should be handled separately after template/script cleanup.
