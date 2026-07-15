# syncTempEmailProviderSelectWithCatalog page paint guard

## Goal
Catalog soft re-entry must not rewrite #tempEmailProviderSelect while off the temp-emails page.

## Done
- [x] currentPage === temp-emails gate in syncTempEmailProviderSelectWithCatalog
- [x] contract + quality-guidelines
- [x] node --check + unittest + git diff --check
