# Shared catalog provider label helper

## Goal

Centralize mailbox provider label resolution from `mailboxProviderCatalogCache` so account cards, import summaries, and future UI share one lookup path and cannot drift.

## Confirmed Facts

- `groups.js getProviderLabel` and `accounts.js getImportResultProviderLabel` both re-implement catalog lookup.
- `main.js` owns the catalog cache and loads first in script order.
- Soft-load + repaint after catalog load already exist.

## Requirements

- Add a shared helper in `main.js` for catalog label resolution (+ optional soft-load).
- Route account-card and import-result label helpers through the shared function.
- Keep existing fallback behavior (import selector options, raw key, translation at call sites).
- Contract tests assert the shared helper and consumers.

## Acceptance Criteria

- [x] Shared helper exists in `main.js` and reads `mailboxProviderCatalogCache`.
- [x] `getProviderLabel` / `getImportResultProviderLabel` use the shared helper.
- [x] No duplicated multi-line catalog find logic remains in those two consumers.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Moving all provider label call sites across mailboxes.js/overview.
- Backend label localization API.
