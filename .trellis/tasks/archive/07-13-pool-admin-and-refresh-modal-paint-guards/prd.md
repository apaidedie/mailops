# Pool-admin + refresh-modal paint guards

## Goal
Paint pool-admin table only on pool-admin page with matching queryKey; paint refresh-modal history/failed list only while refresh modal is open.

## Done
- [x] isCurrentPoolAdminPage / isCurrentPoolAdminView in loadPoolAdmin
- [x] language soft-repaint gated to pool-admin page
- [x] isRefreshModalOpen for loadRefreshLogs / loadFailedLogs
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
