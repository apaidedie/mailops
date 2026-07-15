# Runtime readiness and handoff

## Goal

Make the current project state usable for near-term local operation by verifying startup, configuration completeness, core API reachability, and Settings UI readiness. The task should produce actionable evidence about whether the user can start using the project now, and fix only blockers that materially prevent runtime use or handoff clarity.

This is a short readiness slice under the larger product goal. It does not attempt to finish the full long-term unified mailbox platform vision.

## Requirements

- Verify the repository is clean enough to start from the current `custom` branch without relying on uncommitted changes.
- Verify backend startup using the documented local entrypoint and identify the reachable local URL.
- Verify environment configuration documentation is sufficient for the currently integrated temp-mail providers without exposing secret values.
- Verify key API surfaces needed by external consumers are reachable enough for a readiness pass: health, settings/provider catalog or diagnostics, plugin/provider metadata, and mailbox-related public endpoints where applicable.
- Verify the main web UI and Settings temp-mail provider area render without obvious desktop/mobile layout breakage.
- Fix any high-impact blockers found during this readiness pass.
- Produce a concise handoff note covering how to run the app, which checks passed, and what remains as follow-up work.

## Constraints

- Do not print or commit secret values from `.env`.
- Do not push to a remote.
- Keep fixes scoped to runtime readiness and handoff clarity.
- Keep this task PRD-only unless inspection shows a design-level change is required.

## Acceptance Criteria

- [x] Git state is inspected before and after the task; generated QA output is ignored by existing `.gitignore` rules.
- [x] Local startup command succeeds after fixing Windows redirected-output startup safety.
- [x] At least one backend health/API endpoint responds from a running local server.
- [x] Provider catalog/settings diagnostics are checked without exposing secrets.
- [x] Main page and Settings provider selector are browser-checked on desktop and mobile.
- [x] Readiness documentation exists with the validated local run path and provider configuration checklist.
- [x] Focused validation commands pass before commit.

## Notes

- This readiness slice should prefer evidence and small corrective edits over broad refactors.
- Evidence is summarized in `docs/runtime-readiness.md`.
