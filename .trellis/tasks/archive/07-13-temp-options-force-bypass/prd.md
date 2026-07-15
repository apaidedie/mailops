# Force loadTempEmailOptions supersede soft in-flight

## Problem
loadTempEmailOptions soft-cached but concurrent cold loads double-fetch; force does not supersede soft in-flight per provider.

## Goal
Per-cacheKey coalesce + force supersede soft with request identity.

## Acceptance
- [ ] tempEmailOptionsLoadPromises / LoadForce
- [ ] contract test green
