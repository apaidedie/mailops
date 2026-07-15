# Plugins soft-warm + tag modal paint guard

## Goal
Avoid loadPlugins loading flash on soft re-entry when already loaded; paint tag management list only while modal is open.

## Done
- [x] loadPlugins soft-warm short-circuit before coalesce/loading
- [x] renderTagList gated by isTagManagementModalOpen + null-safe
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
