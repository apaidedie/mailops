# Temp inventory dedicated container only

## Goal
Stop dual-painting temp inventory into shared mailbox #accountList; soft-repaint account list only on mailbox page.

## Done
- [x] loadTempEmails/renderTempEmailList write only #tempEmailContainer
- [x] groups language soft-repaint gated to mailbox + !isTempEmailGroup
- [x] refreshAccountProviderTagsFromCatalog skips non-mailbox/temp
- [x] contracts + quality-guidelines
- [x] node --check + focused unittest + git diff --check
