# Unified readiness uses shared catalog labels

## Goal

Route unified-mailbox readiness, routing-matrix, and capability-matrix provider display names through the shared catalog label helper.

## Confirmed Facts

- Cards/preview already use `getUnifiedMailboxProviderDisplayLabel`.
- Readiness/routing/capability rows still render `provider.label || provider.provider`.
- Shared helper currently prefers `provider_label`; readiness payloads often use `label`.

## Requirements

- Extend the unified label helper to accept `label` as well as `provider_label`.
- Use it for readiness list, routing matrix chips, and capability matrix row labels.
- Contract tests assert those call sites.

## Acceptance Criteria

- [x] Readiness/routing/capability provider labels use shared catalog resolution.
- [x] Payload `label` / `provider_label` remain fallbacks.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing readiness_summary backend payload shape.
- Redesigning readiness/capability layout.
