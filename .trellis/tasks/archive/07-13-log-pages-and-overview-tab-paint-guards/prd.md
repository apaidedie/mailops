# Log pages + overview tab paint guards

## Goal
Paint refresh-log/audit page chrome only on the matching page; paint overview tab loading/result only while that tab is active.

## Done
- [x] isCurrentRefreshLogPage / isCurrentAuditLogPage guards
- [x] isCurrentOverviewTab guard in loadOverviewTab
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
