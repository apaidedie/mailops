# Implementation Plan

## Checklist

1. Review current unified workspace markup, render helpers, CSS, and frontend contract tests.
2. Refine command-center rendering and copy using existing `data.summary`, `data.facets`, `data.contract`, and `data.provider_context` only.
3. Refine toolbar, result bar, provider context, capability matrix, and mailbox card CSS for hierarchy, stable dimensions, wrapping, focus, and mobile behavior.
4. Update tests only for intentional new hooks or stronger contract checks.
5. Run focused validation commands and fix failures.
6. Perform a secret-safety and provider-agnostic review over the changed frontend slices.
7. Commit the task, archive it, and record the journal.

## Validation Commands

- `python -m pytest tests/test_unified_mailbox_frontend_contract.py -q -rs`
- `python -m pytest tests/test_unified_mailbox_catalog.py -q -rs`
- `git diff --check`

Optional if app startup is feasible within the turn:

- Start the Flask app locally and inspect the unified mailbox page at desktop and mobile sizes.

## Risk Points

- Renaming existing IDs or classes can break tests and event handlers.
- Hardcoding enum options in the template would violate contract-driven frontend rendering.
- Adding provider-name branches can drift from the backend provider catalog and leak assumptions.
- Desktop grid placement must include mobile resets for direct children to avoid implicit columns.
- Long provider endpoints, provider names, and email addresses must wrap without page-level overflow.

## Rollback Points

- If JS render changes cause contract regressions, first revert JS markup refinements and keep CSS-only polish.
- If responsive CSS causes mobile compression, restore single-column grid resets before adjusting visual density.
- If browser verification is blocked by environment startup, keep static contract tests and report that rendered verification was not completed.
