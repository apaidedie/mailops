# Token-tool OAuth config soft repaint guard

## Goal
Soft loadOAuthConfig must not overwrite in-progress form edits.

## Done
- [x] isOAuthConfigFormUnhydrated helper
- [x] soft re-entry paints only when form unhydrated; force always paints
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
