# Catalog-driven account list provider labels

## Goal

Replace the hard-coded provider label map in standard mailbox account cards with catalog-backed labels so newly added account/temp providers display correctly without frontend map updates.

## Confirmed Facts

- `static/js/features/groups.js` `getProviderLabel()` hard-codes outlook/gmail/qq/163/126/yahoo/aliyun/custom/cloudflare_temp_mail.
- Shared `mailboxProviderCatalogCache` already powers Settings, pool admin, and import result labels.
- Account list tags use `acc.provider || acc.account_type`.

## Requirements

- Resolve card provider tags from mailbox provider catalog when available.
- Fall back to raw provider/account_type key when catalog missing.
- Remove hard-coded multi-provider label map.
- Optionally ensure catalog is loaded before/while rendering account lists (non-blocking).
- Frontend contract tests assert helper uses catalog cache and omits hard-coded map.

## Acceptance Criteria

- [x] `getProviderLabel` no longer contains a hard-coded multi-provider map.
- [x] Labels prefer `mailboxProviderCatalogCache` matches.
- [x] Unknown providers fall back safely to the raw key.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Compact mailbox view redesign.
- Backend account list payload changes.
- i18n rewrite of every catalog label.
