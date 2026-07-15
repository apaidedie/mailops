# Operational Readiness Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for behavior/UI changes. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secret-safe readiness console inside the existing external API command center.

**Architecture:** Reuse existing settings and provider caches, add one authenticated mailbox-directory snapshot fetch, then render a compact read-only readiness grid. Keep provider selection data-driven and avoid new backend routes.

**Tech Stack:** Flask templates, plain JavaScript, plain CSS, Python unittest/pytest frontend contract tests.

---

### Task 1: Frontend Contract Test

**Files:**
- Modify: `tests/test_settings_tab_refactor_frontend.py`

- [ ] Add assertions for operational readiness cache variables, snapshot loader, renderer helpers, `/api/mailboxes` fetch, render hooks, CSS hooks, i18n strings, and secret-safety slice.
- [ ] Run the focused test and confirm it fails because the console is not implemented yet.

### Task 2: JavaScript Implementation

**Files:**
- Modify: `static/js/main.js`

- [ ] Add readiness snapshot cache and promise variables.
- [ ] Implement `loadOperationalReadinessSnapshot(forceRefresh = false)` using `/api/mailboxes` with bounded page size.
- [ ] Implement provider-agnostic readiness helpers and `renderOperationalReadinessConsole(settings, state)`.
- [ ] Call the snapshot loader after settings load and settings save, and rerender on provider catalog success/failure and language changes.
- [ ] Insert the console into `renderExternalApiCommandCenter()` before Quickstart.

### Task 3: CSS and I18n

**Files:**
- Modify: `static/css/main.css`
- Modify: `static/js/i18n.js`

- [ ] Add compact readiness console styles with stable grid columns, semantic status variants, wrapping, and mobile single-column collapse.
- [ ] Add bilingual strings for readiness labels and degraded/empty states.

### Task 4: Verification

**Commands:**
- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q -rs`
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_external_api.py -q -rs`
- `node --check static/js/main.js`
- `node --check static/js/i18n.js`
- `git diff --check`
- secret scan over `git diff` for DuckMail/API-key/token-like values.

### Task 5: Finish

**Files:**
- Modify: `.trellis/workspace/apaidedie/journal-1.md`

- [ ] Update specs only if the implementation creates a new reusable frontend contract.
- [ ] Commit the task changes and archive the Trellis task.
