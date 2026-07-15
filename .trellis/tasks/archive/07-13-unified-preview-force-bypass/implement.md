# Implement: unified preview force supersede soft

## Changes
1. mailboxes.js preview state: messagesLoadForce / detailLoadForce / verificationLoadForce
2. loadUnifiedMailboxMessages / Detail / Verification force supersede soft for same signature
3. Contract tests + quality-guidelines.md

## Validation
- node --check static/js/features/mailboxes.js
- python -m unittest focused overview contract methods
- git diff --check
