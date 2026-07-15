# Document deferred plugin load and force refresh button

## Goal

1. Manual plugin-card refresh must force-reload `/api/plugins` even when list is already loaded.
2. Document deferred plugin-list loading + soft catalog refresh rules in frontend quality guidelines.

## Acceptance Criteria

- [x] Refresh button forces plugin list reload.
- [x] Spec documents boot vs Settings plugin load budget.
- [x] Focused tests + `git diff --check` pass.
