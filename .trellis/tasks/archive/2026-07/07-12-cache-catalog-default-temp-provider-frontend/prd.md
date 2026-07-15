# Cache catalog default temp provider for Settings warmup fallback

## Problem

Admin `/api/providers` now returns operator-canonical `default_temp_mail_provider`,
but the frontend still hard-codes `'legacy_bridge'` as the Settings selection
fallback and never caches the discovery default.

## Goal

1. Cache `default_temp_mail_provider` from `/api/providers` next to other catalog caches.
2. Use it as the Settings radio/collection fallback when no radio is checked yet.
3. Keep alias normalization and DOM hooks unchanged.

## Acceptance Criteria

- [x] Catalog success stores operator default temp provider
- [x] Selection/collection fallbacks prefer cached default over hard-coded string
- [x] Focused frontend contract tests + `node --check` + `git diff --check` pass
