# Force temp messages and token-tool supersede soft in-flight

## Problem

`loadTempEmailMessages(true)` joins any in-flight soft GET, and token-tool
force loads do not supersede soft, so late soft responses can repaint stale
messages/config/accounts.

## Goal

1. Soft joins any; force joins only force; force supersedes soft.
2. Abandoned soft must not write caches / apply UI.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] temp messages loadForce + identity (keep requestSeq)
- [x] oauth config loadForce + identity
- [x] token accounts loadForce + identity
- [x] Focused tests green
