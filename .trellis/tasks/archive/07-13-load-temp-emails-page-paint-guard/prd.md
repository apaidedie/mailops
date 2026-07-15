# loadTempEmails page-level paint guard

## Goal
Prevent loadTempEmails / renderTempEmailList from clobbering shared #accountList when not on the temp-emails page.

## Done
- [x] isCurrentTempEmailsPage() + paint guards in loadTempEmails
- [x] renderTempEmailList no-op off temp-emails page
- [x] contract test + quality-guidelines
- [x] node --check + unittest + git diff --check
