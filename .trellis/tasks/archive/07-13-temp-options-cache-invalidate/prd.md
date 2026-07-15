# Invalidate tempEmailOptionsCache after settings/plugin mutations

## Problem
loadTempEmailOptions soft-cache had no invalidate path; settings/plugin credential changes could soft-paint stale domains.

## Goal
Shared invalidateTempEmailOptionsCache + call sites on save/auto-save/plugin/list force.

## Acceptance
- [ ] invalidate helper + window export
- [ ] saveSettings / autoSaveSettings / plugins / loadTempEmails(true)
- [ ] contract tests green
