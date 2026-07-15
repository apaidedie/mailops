# Expose operator default temp provider on admin providers API

## Problem

External `GET /api/external/providers` exposes `default_temp_mail_provider` (operator-canonical
via `get_operator_temp_mail_default_provider()`). Admin `GET /api/providers` only exposes
`default_pool_claim_provider`, so admin discovery cannot read the same default temp key
without re-deriving from settings/diagnostics.

## Goal

1. Add secret-free `default_temp_mail_provider` (+ env + label + configured flags) to admin
   `/api/providers`, aligned with external providers payload and operator bridge projection.
2. Keep full catalog dual-register; do not migrate stored settings.

## Acceptance Criteria

- [x] Admin `/api/providers` includes operator-canonical default temp provider fields
- [x] Value matches collapsed guide (bridge keys → `legacy_bridge`)
- [x] Focused tests + `git diff --check` pass
