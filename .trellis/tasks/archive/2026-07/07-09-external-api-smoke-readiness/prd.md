# External API smoke readiness polish

## Goal

Make the read-only External API smoke checker more useful as a deployment and handoff gate for external consumers. It should prove that the discovery surface, readiness summary, provider preflight pointer, docs pointer, and mailbox-session contract are coherent before a worker is wired to the instance.

## Requirements

- Extend the existing `scripts/external_api_smoke.py` flow instead of adding a second checker.
- Keep the checker read-only. It must not start mailbox sessions, claim pool accounts, create temp mailboxes, read messages, close lifecycles, or run upstream provider probes.
- Validate that health readiness exposes the expected operational sections and next endpoints.
- Validate that capabilities/documentation/OpenAPI expose docs and provider-preflight endpoints through canonical v1 paths, while keeping legacy aliases as metadata.
- Validate that provider and mailbox readiness payloads contain compact status/totals/selector fields useful to operators and external workers.
- Keep all checks secret-safe and continue detecting obvious leaked API keys, bearer tokens, provider tokens, and task/consumer-like values.
- Update quickstart documentation so deployers know what the smoke checker verifies and what it intentionally does not mutate.

## Acceptance Criteria

- [x] `scripts/external_api_smoke.py` checks health readiness, docs endpoint discovery, provider preflight discovery, readiness summaries, and existing mailbox-session contracts.
- [x] Smoke tests cover both successful readiness validation and at least one new failure mode.
- [x] `docs/external-integration-quickstart.md` describes the enhanced smoke gate in practical deployment terms.
- [x] Focused tests for the smoke checker and starter client pass.
- [x] Python compile and whitespace checks pass for touched files.

## Notes

This is a lightweight, bounded task. PRD-only planning is sufficient.
