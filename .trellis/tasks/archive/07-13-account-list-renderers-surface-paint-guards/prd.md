# Account list renderer surface paint guards

## Goal
Defense-in-depth: renderAccountList / renderCompactAccountList must no-op off their active mailbox surfaces even if a caller forgets a guard.

## Done
- [x] renderAccountList gated to mailbox / non-temp / non-unified
- [x] renderCompactAccountList gated to mailbox compact
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
