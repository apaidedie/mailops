# loadAccountsByGroup current-view paint guard

## Goal
Prevent loadAccountsByGroup from painting stale group/page inventory into shared #accountList and rewriting currentAccountPage from abandoned responses.

## Done
- [x] isCurrentAccountListView() + paint guards in loadAccountsByGroup
- [x] updateAccountListCache syncCurrentPage option for stale views
- [x] contract test + quality-guidelines
- [x] node --check + unittest + git diff --check
