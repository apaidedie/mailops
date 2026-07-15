# Soft re-entry repaints pool-admin group filter from warm groups

## Goal
ensurePoolAdminGroupOptions soft path re-paints warm groups; force still loadGroups(true).

## Acceptance
- [ ] !force && (hasWarmGroups || groupOptionsLoaded) re-paints
- [ ] contract green
