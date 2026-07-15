# Force initCSRFToken supersede soft in-flight

## Problem
initCSRFToken force recovery joins any soft in-flight CSRF pull, so CSRF_TOKEN_INVALID retry may attach a token already known stale.

## Goal
Soft joins any; force joins only force; force supersedes soft with request identity.

## Acceptance
- [ ] csrfTokenRefreshForce
- [ ] smoke contract asserts force path
- [ ] node --check + tests green
