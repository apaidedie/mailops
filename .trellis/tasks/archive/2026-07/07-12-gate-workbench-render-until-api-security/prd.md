# Gate workbench render on loadSettings to api-security tab

## Problem

`loadSettings` always calls `renderProviderWorkbench` and
`renderExternalApiCommandCenter` even when the active Settings tab is Basic or
Temp Mail. Those panels live under API security and are hidden until that tab
is selected.

## Goal

1. Only render workbench/command-center on loadSettings when already on api-security.
2. When switching to api-security, render from snapshot before soft-loading network panels.
3. Keep form field hydration for all tabs (inputs still populated for later switches).

## Acceptance Criteria

- [x] loadSettings does not always render workbench/command-center
- [x] switchSettingsTab('api-security') renders from snapshot then soft-loads
- [x] Save paths on api-security still re-render
- [x] Focused tests + node --check + git diff --check pass
