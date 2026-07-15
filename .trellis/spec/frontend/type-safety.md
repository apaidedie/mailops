# Frontend Type Safety

The main frontend is plain JavaScript, not TypeScript. Type safety comes from runtime normalization, defensive DOM access, JSDoc comments in standalone modules, and contract tests that assert public HTML/CSS/JS shapes.

## Runtime Validation

- Check that API payloads are objects or arrays before reading nested fields.
- Normalize optional strings, booleans, and numbers before storing them in feature state.
- Use defaults for missing backend contract fields, but keep those defaults minimal and visible as degraded/placeholder states.
- For localStorage payloads, validate structure before use and clear invalid state.

## JSDoc And Exports

- Use JSDoc in standalone modules that are tested under Node/jsdom, such as `static/js/state-manager.js`.
- Browser feature modules currently rely on globals; if a module needs Jest/node tests, expose only the smallest stable API via `module.exports` while preserving browser globals.
- Prefer named normalizer functions over repeated inline casts and `|| {}` chains across renderers.

## DOM Safety

- Always tolerate missing optional DOM nodes. Feature modules should return early when a mount point is absent.
- Required DOM hooks should be asserted by Python frontend contract tests.
- Use `textContent` for simple text insertion. When `innerHTML` is needed for repeated markup, escape dynamic values first.

## Contract Tests As Type Guards

- Backend-owned schemas are verified through API/OpenAPI tests.
- Template and static JS/CSS contracts are verified by Python tests that search for required IDs, classes, helper names, script order, ARIA hooks, and forbidden secret references.
- Standalone browser-state utilities are verified with Jest/jsdom tests under `tests/layout-system` or `tests/browser-extension`.

## Forbidden Patterns

- Do not assume a nested API field exists without an object/array check.
- Do not parse untrusted JSON from localStorage without try/catch and validation.
- Do not inject API strings into `innerHTML` without escaping.
- Do not silence shape errors by catching everything and returning a misleading ready state.
- Do not add TypeScript-only conventions to the main app unless a build pipeline migration is explicitly planned.
