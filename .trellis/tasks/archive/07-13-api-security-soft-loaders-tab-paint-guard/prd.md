# API-security soft loaders tab paint guard

## Goal
Always warm operational readiness / contract-check / provider-preflight soft caches, but paint command-center and preflight chrome only while isCurrentApiSecuritySurface().

## Done
- [x] isCurrentApiSecuritySurface helper
- [x] paint guards in three soft loaders
- [x] settings tab contract tests + quality-guidelines
- [x] node --check + unittest + git diff --check
