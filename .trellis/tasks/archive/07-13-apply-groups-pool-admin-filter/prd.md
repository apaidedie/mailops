# applyLoadedGroups soft-syncs pool-admin group filter

## Goal
After groups load/mutate, ensurePoolAdminGroupOptions(false) re-paints pool filter from warm groups.

## Acceptance
- [ ] applyLoadedGroups calls ensurePoolAdminGroupOptions(false)
- [ ] contract green
