# Token-tool save-dialog account select paint guard

## Goal
loadAccountOptions always warms tokenToolAccountsCache but paints #accountSelect only while the save dialog is open.

## Done
- [x] isTokenToolSaveDialogOpen helper
- [x] applyTokenToolAccountOptions + loadAccountOptions paint guards
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
