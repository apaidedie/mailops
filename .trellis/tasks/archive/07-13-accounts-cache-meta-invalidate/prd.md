# Keep accountListMetaCache in sync when dropping accountsCache

## Problem
Mutations used bare delete accountsCache[groupId] without clearing accountListMetaCache; soft-load could see mismatched meta.

## Goal
Shared invalidateAccountsCache clears rows + meta + in-flight maps; all call sites use it.

## Acceptance
- [ ] helper + window export
- [ ] no bare delete accountsCache[ in accounts/main/temp
- [ ] contract tests green
