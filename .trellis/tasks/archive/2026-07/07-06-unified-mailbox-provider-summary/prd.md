# Unified mailbox provider summary band

## Goal

Make the unified mailbox workspace feel like the central control surface for all mailbox sources by showing a compact provider summary band above the directory results.

## Requirements

- The authenticated unified mailbox page must summarize the active provider policy, current defaults, provider readiness, and local provider facets near the result summary.
- The summary must use only the existing `/api/mailboxes` response: `provider_context`, `facets.providers`, `summary`, `filters`, and `contract`.
- The UI must stay secret-free. It may show provider names, labels, counts, readiness counts, policy source, and discovery endpoint paths, but never token, key, password, bearer, JWT, or credential values.
- The summary must be resilient when provider context is missing, partially populated, or reports config-file errors.
- The layout must be responsive and match the existing native HTML/CSS/JS stack without adding a frontend framework or component library.
- The summary must improve extensibility by rendering provider chips from response data rather than hardcoded provider lists.

## Acceptance Criteria

- [x] Unified mailbox frontend renders a provider summary band from `data.provider_context` and provider facets.
- [x] The band shows active provider mode, temp runtime default, pool claim default, readiness counts, source priority, and discovery endpoint when available.
- [x] Provider chips are generated from `facets.providers` and include provider label, source kind, count, and current filter state.
- [x] Empty or missing provider data renders a calm fallback instead of breaking the page.
- [x] Frontend contract tests cover the new render path and CSS hooks.
- [x] Relevant unified mailbox/provider tests pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
