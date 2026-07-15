# Catalog-driven import result provider labels

## Goal

Remove the hard-coded provider display-name map from auto-import success toasts so import results stay aligned with the live account/temp catalog and newly added providers.

## Confirmed Facts

- Auto-import summary toast in `static/js/features/accounts.js` uses a fixed `provNames` map for keys like outlook/gmail/qq/gptmail/temp_mail.
- Import selector already loads catalog-backed options into `providerOptions` and/or shared `mailboxProviderCatalogCache`.
- Unknown providers currently fall back to raw key (good), but known aliases like gptmail/temp_mail stay hard-coded.

## Requirements

- Resolve import-summary provider labels from catalog/import provider options instead of a fixed map.
- Prefer cached mailbox provider catalog labels (account + temp); fall back to import selector options; then raw key.
- Keep existing toast structure and counts (imported/skipped/failed, groups_created).
- Add frontend contract assertions covering the helper and absence of the hard-coded map.

## Acceptance Criteria

- [x] Auto-import success path no longer uses a hard-coded `provNames = {outlook:..., gmail:...}` map.
- [x] Labels resolve from catalog/import options when available.
- [x] Unknown provider keys still render safely (raw key).
- [x] Focused frontend tests + `git diff --check` pass.

## Out Of Scope

- Changing backend import summary payload shape.
- Reworking toast UX design/layout.
- Localizing every provider label beyond existing catalog labels.
