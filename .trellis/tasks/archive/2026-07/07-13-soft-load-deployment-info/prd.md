# Soft-load deployment info with force option

## Problem

`loadDeploymentInfo` always GETs `/api/system/deployment-info` (even with
`cache: 'no-store'`) on every Settings load, despite `lastDeploymentInfo`
already caching for language re-render.

## Goal

1. Soft-load warm lastDeploymentInfo when !forceRefresh.
2. Coalesce concurrent network loads.
3. Settings open uses soft load; force available for explicit refresh.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path re-renders lastDeploymentInfo without network
- [x] In-flight coalesce
- [x] loadSettings soft-loads
- [x] Focused tests green
