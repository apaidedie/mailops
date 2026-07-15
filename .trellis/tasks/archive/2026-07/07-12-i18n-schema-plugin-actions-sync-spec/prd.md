# I18n schema plugin actions and sync routing spec

## Goal

1. Add i18n entries for schema-panel action strings used by plugin test-connection and related UI.
2. Correct outdated frontend quality-guidelines that still claim plugins always use PluginManager when catalog is ready.

## Acceptance Criteria

- [x] i18n map covers `测试连接`, `处理中…`, `操作端点不可用`, and schema subtitle if missing.
- [x] Spec base case updated for catalog-ready plugin schema path + warmup alias note.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Full Settings UI redesign / screenshots.
