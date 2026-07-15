# Canonicalize active providers in external displays

## Goal

External API command-center route text and starter env snippets should use the same canonical provider keys as Settings chips/allowlists.

## Requirements

- Shared helper to de-dupe/canonicalize provider lists.
- Use in external command route mode and starter env snippet.
- Canonicalize pool/temp defaults in those displays when practical.
- Contract tests assert helper usage.

## Acceptance Criteria

- [x] Active provider lists in external displays are canonicalized.
- [x] Focused tests + `git diff --check` pass.
