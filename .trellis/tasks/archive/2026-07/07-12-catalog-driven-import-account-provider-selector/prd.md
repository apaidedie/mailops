# Catalog-driven import account provider selector

## Goal

Make the “导入邮箱账号” provider dropdown fully catalog-driven and resilient: no sole hard-coded Outlook option, prefer `/api/providers` account catalog entries, and surface provider notes for operators.

## Confirmed Facts

- Modal `#accountProvider` currently ships with a single hard-coded Outlook option as SSR fallback.
- `loadProviders()` already fetches `/api/providers` and renders `data.providers` (`get_provider_list()`).
- Account catalog (`mailbox_providers` kind=`account`) is built from `get_provider_list()` but currently drops `note`.
- Import UI needs `auto` + account providers only (not temp-mail providers).

## Requirements

- Template mount should not present a hard-coded provider roster; loading/empty placeholder is OK.
- Frontend fills options from provider API; prefer `mailbox_providers` with `kind=account`, fallback to `providers`.
- Preserve `auto` first ordering when present; default selection prefers `auto` then `outlook`.
- Show selected provider note when available.
- Keep existing import format placeholder behavior for auto/outlook/custom/imap families.
- Add/extend frontend contract coverage.

## Acceptance Criteria

- [x] `#accountProvider` template has no hard-coded multi-provider option list (Outlook-only static roster removed).
- [x] `accounts.js` populates options from `/api/providers` account catalog/providers payload.
- [x] Provider note is shown when the API provides it.
- [x] Default selection prefers `auto` when available.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing import backend parsing rules.
- Adding new mail providers to `MAIL_PROVIDERS`.
- Temp-mail import as dedicated account provider options.
