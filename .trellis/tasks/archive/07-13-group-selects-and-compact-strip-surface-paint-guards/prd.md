# Group selects + compact strip surface paint guards

## Goal
Soft loadGroups must not rewrite closed import/edit group selects or compact strip chrome off mailbox compact mode.

## Done
- [x] updateGroupSelects only paints open add/edit account modals
- [x] renderCompactGroupStrip gated to mailbox compact surface
- [x] language soft-paint compact account list gated
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
