# Export + batch-move modal paint guards

## Goal
Soft loadGroups finishing after export/batch-move modals close must not rewrite closed modal DOM.

## Done
- [x] isExportModalOpen + paintExportGroupList/loadExportGroupList guards
- [x] isBatchMoveGroupModalOpen + paintBatchMoveGroupSelectFromWarmGroups/loadGroupsForBatchMove guards
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
