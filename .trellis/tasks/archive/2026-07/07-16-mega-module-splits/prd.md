# Mega module splits

## Goal
Further split remaining oversized modules: state provider_catalog/external_api_ui JS, provider_catalog catalog+integration Python, db schema if practical. layout-manager IIFE skip unless clean cut found.

## Acceptance
- Packages/modules land without behavior change
- Tests + readiness green
- Commit/push
