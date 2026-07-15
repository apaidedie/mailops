# Defer Notification permission prompt until after boot settle

## Problem

`DOMContentLoaded` immediately calls `Notification.requestPermission()` when
permission is `default`. Modern browsers discourage permission prompts without
user gesture; the prompt also competes with boot work (catalog, overview).

## Goal

1. Do not request notification permission during critical boot path.
2. Prefer first user gesture; optional idle fallback after boot settle.
3. Contract tests assert boot slice does not call requestPermission synchronously.
4. node --check + git diff --check pass.

## Acceptance Criteria

- [x] Boot DOMContentLoaded does not call Notification.requestPermission inline
- [x] Permission may still be requested after user gesture (or delayed idle)
- [x] Focused tests green
