# loadTagsForSelect + import provider modal paint guards

## Goal
Cold loadTagsForSelect and loadProviders must not rewrite closed modal DOM.

## Done
- [x] loadTagsForSelect loading/error only when batch-tag modal open
- [x] isAddAccountModalOpen + loadProviders paint only when add-account modal open
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
