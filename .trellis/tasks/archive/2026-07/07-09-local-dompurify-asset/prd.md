# Local DOMPurify Asset

## Goal

Remove the authenticated UI's blocked CDN dependency for DOMPurify so HTML email rendering uses the intended sanitizer under the project's existing Content Security Policy.

## Background

- `templates/index.html` loads DOMPurify from `https://cdn.jsdelivr.net/npm/dompurify@3.0.8/dist/purify.min.js`.
- `mailops/middleware/security_headers.py` emits `script-src 'self' 'unsafe-inline'`, so the browser blocks that CDN script in normal app pages.
- `static/js/features/emails.js` has a fallback sanitizer when `DOMPurify` is missing, but the production path should load the stronger sanitizer reliably from a first-party static URL.

## Requirements

- Replace the external DOMPurify script tag with a local static asset path.
- Preserve the existing DOMPurify version unless there is a concrete compatibility reason to upgrade.
- Keep the existing CSP policy strict; do not loosen `script-src` to allow CDN execution.
- Do not change email rendering behavior beyond making the intended sanitizer load reliably.
- Keep changes scoped to static asset wiring, tests, and documentation/spec updates if needed.

## Acceptance Criteria

- [ ] `templates/index.html` no longer references `cdn.jsdelivr.net` for DOMPurify.
- [ ] A local DOMPurify asset is available under `static/` and is served by the Flask static route.
- [ ] Browser verification of the authenticated page shows `window.DOMPurify` is present and no CSP console error is emitted for the DOMPurify script.
- [ ] Security header tests still pass without loosening CSP.
- [ ] Focused JS/email tests still pass.
- [ ] The final diff does not include unrelated provider/API/UI changes.

## Out Of Scope

- Rewriting the email rendering sanitizer pipeline.
- Changing CSP semantics beyond removing the incompatible CDN dependency.
- Broad asset bundling or frontend build tooling.
