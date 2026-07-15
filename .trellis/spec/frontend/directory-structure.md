# Frontend Directory Structure

The frontend is a Flask-rendered, static-asset application. There is no React/Vue build step for the main app. Treat templates, static JavaScript feature modules, CSS, and frontend contract tests as the frontend architecture.

## Layout

```text
templates/
  index.html              # main authenticated workspace shell
  login.html              # login page
  token_tool.html         # optional OAuth helper page
  partials/scripts.html   # static JS load order (classic scripts)
  partials/modals.html    # shared modal markup
static/
  css/core/tokens.css     # design tokens + reset (linked before main.css)
  css/main.css            # primary app styles (components/pages)
  css/layout.css          # layout-system styles where applicable
  css/token_tool.css      # token tool page styles
  js/core/
    state/                # package: globals + domain modules (+ _load_order / _function_order)
    admin/                # package: refresh, invalid_token, audit, version_update, …
    poll-ui.js nav.js http.js utils.js settings.js
  js/main.js              # thin bootstrap note only (logic lives in core/)
  js/i18n.js              # translation map and local translation helpers
  js/state-manager.js     # testable layout-state persistence class
  js/layout-*.js          # layout system helpers
  js/features/
    mailboxes/            # package: workspace, render, filters, quickview, data, actions
    *.js                  # other page modules (overview, pool_admin, accounts, …)
  vendor/*.js             # vendored third-party browser assets
tests/frontend_js_bundle.py  # core/feature package loaders for contract tests
tests/*frontend*          # Python contract tests over HTML/CSS/JS text
tests/layout-system/*     # Jest/jsdom tests for standalone JS modules
```

## Module Ownership

- `templates/index.html` owns stable DOM mount points, accessible labels, initial placeholders, and page shell structure.
- `templates/partials/scripts.html` owns browser script order for classic (non-module) scripts. Large domains load as multiple files under a package directory (`state/globals.js` then domain files, etc.).
- `static/js/core/` owns global navigation, shared settings helpers, global caches, CSRF/HTTP helpers, and cross-feature utility functions.
- Large core/feature files are **packages**:
  - Each package has `globals.js` (top-level `let`/`const` and non-function lines) loaded first.
  - Domain modules hold top-level `function` declarations (8-space indent convention from the historical main.js extract).
  - `_load_order.json` lists browser file order; `_function_order.json` lists original function appearance order for test bundle reconstruction.
- `static/js/features/<feature>.js` or `features/<feature>/` owns one page or feature area. Examples: `mailboxes/`, `overview.js`, `pool_admin.js`, `temp_emails.js`.
- `tests/frontend_js_bundle.py` owns `load_frontend_app_js()` and `load_mailboxes_js()` so contract tests see original function order even when browser loads by domain module.
- `static/css/core/tokens.css` owns CSS variables and reset; `static/css/main.css` owns component/page styling.
- `static/vendor/` is the place for reviewed third-party browser scripts; do not load protected app scripts from CDNs.

## Adding A Frontend Feature

1. Add stable DOM mount points in `templates/index.html` with IDs/classes that can be asserted by contract tests.
2. Add behavior in the closest `static/js/features/*` module or package. Prefer a package submodule when the feature file is already multi-domain.
3. Keep global function names stable when templates or other scripts call them.
4. Update `templates/partials/scripts.html` and package `_load_order.json` / `_function_order.json` when splitting or adding package files.
5. Add Python frontend contract tests for required HTML hooks, JS helper names, script order, copy text, and CSS selectors. Use `load_frontend_app_js()` / `load_mailboxes_js()` instead of hardcoding monofile paths.
6. Add Jest/jsdom tests only for standalone JS modules that export through `module.exports` or can be tested without the Flask page shell.

## Naming Conventions

- DOM IDs are camelCase or descriptive lowerCamel-like IDs used by existing code, for example `unifiedMailboxProviderContext`.
- CSS classes use kebab-case and feature prefixes, for example `.unified-toolbar`, `.ov-command-shell`, `.provider-workbench`.
- Feature JS state objects use feature prefixes, for example `unifiedMailboxState`.
- Public data attributes should be descriptive and stable, for example `data-provider-console-filter` or `data-unified-quick-view`.

## Examples To Follow

- Unified mailbox workspace: `templates/index.html`, `static/js/features/mailboxes/`, `static/css/main.css`, and `tests/test_unified_mailbox_frontend_contract.py` (via `load_mailboxes_js()`).
- Core shell: `static/js/core/state/`, `static/js/core/admin/`, `tests/frontend_js_bundle.py`.
- Overview dashboard: `static/js/features/overview.js` and `tests/test_overview_frontend_contract.py`.
- Layout state manager: `static/js/state-manager.js` and `tests/layout-system/unit/state-manager.test.js`.

## Forbidden Patterns

- Do not add a separate frontend build stack for a small feature without a project-level migration plan.
- Do not hardcode provider capability logic in JS when discovery contracts expose it.
- Do not add CDN script dependencies to authenticated pages; vendor reviewed assets under `static/vendor/`.
- Do not rely on template-only options for contract-driven selects. The unified mailbox filters intentionally start with minimal placeholders and hydrate from API contracts.
- Do not assert monofile paths like `static/js/core/state.js` or `features/mailboxes.js` in new tests after those domains became packages.
- Do not drop top-level `let`/`const` when splitting: put them in `globals.js` and keep package `_function_order.json` in sync for contract tests.
