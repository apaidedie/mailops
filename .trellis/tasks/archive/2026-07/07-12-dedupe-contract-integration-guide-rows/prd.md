# Dedupe contract and integration guide provider rows

## Goal

Collapse bridge aliases in provider-contract status rows and provider-integration guide cards.

## Requirements

- Canonicalize temp provider keys when building contract catalog rows.
- De-dupe integration guide providers before filter/render.
- Contract tests assert markers.

## Acceptance Criteria

- [x] Contract catalog rows use canonical provider keys.
- [x] Integration guide providers are de-duped.
- [x] Focused tests + `git diff --check` pass.
