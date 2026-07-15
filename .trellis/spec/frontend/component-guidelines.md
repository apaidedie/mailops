# Component Guidelines

The main app does not use a component framework. In this repository, "component" means a stable UI block made from Flask template markup, CSS hooks, and one or more JavaScript render/update functions.

## Component Structure

- Template markup should provide semantic containers, stable IDs, accessible labels, loading/empty states, and minimal placeholder options.
- JavaScript renderers should accept normalized data and write into one mount point. Keep DOM querying near the renderer or helper that owns the block.
- CSS should use a feature-prefixed class set and responsive rules in the same feature section where possible.
- Contract tests should assert the required DOM hooks and render-helper names for important workspaces.

## DOM Contracts

- IDs used by JS are public contracts. Do not rename them without updating feature JS and tests.
- Use `aria-live="polite"` for async status/summary panels, and `aria-label` or `aria-labelledby` for toolbars, groups, and operational panels.
- Initial template options for API-driven filters should stay minimal. Hydrate full option lists from backend contracts such as `contract.kind_definitions`, `contract.action_definitions`, and provider readiness data.
- Keep loading states visible and specific. Existing patterns use `data-state="loading"`, skeleton rows, and copy such as "正在读取...".

## Rendering Patterns

- Escape untrusted or API-provided text before injecting HTML. Existing renderers use `escapeHtml(...)` helpers.
- Prefer small normalizer helpers before renderers, for example `normalizeUnifiedQuickViewFilters()` and `normalizeUnifiedQuickViewPreset()`.
- Preserve feature-specific prefixes in helper names, such as `renderUnifiedQuickViews`, `renderExternalApiCommandCenter`, or `renderProviderPreflightConsole`.
- For repeated cards/tables, render from arrays of normalized objects rather than branching on provider names or localized labels.

## Styling Patterns

- Reuse CSS variables from `:root` and `[data-theme="dark"]` in `static/css/main.css`.
- Dense operational pages should use restrained, scannable controls rather than marketing-style hero sections.
- Keep cards/panels at the existing radius scale (`--radius`, `--radius-sm`) and avoid nested decorative cards.
- Use responsive constraints for grids, toolbars, summary cards, and status strips. Mobile breakpoints must reset explicit desktop `grid-column` / `grid-row` placement.

## Accessibility

- Buttons need visible text or a `title`/`aria-label` when icon-only.
- Async result/status regions should use `aria-live` when content changes after fetch.
- Controls rendered from API contracts should preserve labels tied to inputs via `for`/`id` or `aria-label`.
- Focus styles must remain visible; do not remove `:focus-visible` rules without replacement.

## Common Mistakes

- Renaming an ID in `index.html` without updating `static/js/features/*.js` and contract tests.
- Rendering raw API strings into `innerHTML` without escaping.
- Treating provider keys as UI behavior branches instead of reading provider catalog/discovery metadata.
- Adding a wide toolbar/grid on desktop without mobile collapse rules and browser overflow checks.
