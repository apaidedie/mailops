# External provider recipe guide

## Goal

Expose the backend `selection_recipes` contract inside Settings -> API Security so external integrators can pick a provider selection scenario and copy the exact env, provider-config, settings, and request examples without reading backend tests or OpenAPI by hand.

## Requirements

- Keep the guide inside the existing `#externalApiCommandCenter`; do not add a second external integration entry point.
- Prefer `integration_manifest.selection_recipes`, then compatible manifest/guide/deployment fallbacks, and keep rendering provider-agnostic.
- Show loading, empty, and provider-catalog degraded states without hiding the existing endpoint and starter snippets.
- Copy snippets must use API-key placeholders and blank values for secret provider env/settings hints.
- The UI must not read Settings API key inputs, provider credential inputs, masked placeholders, or plaintext secrets.
- Long env keys, provider config examples, request paths, and provider names must wrap on desktop and mobile.

## Acceptance Criteria

- [ ] Settings -> API Security renders a selectable provider recipe guide from the current discovery payload.
- [ ] The selected recipe detail shows source priority, env snippet, provider config JSON/TOML, settings payload, request endpoint/body, and provider env hints when available.
- [ ] Copying a recipe returns a secret-safe text block and never interpolates real external API keys or provider tokens.
- [ ] Frontend contract tests cover helper names, render wiring, event delegation, CSS hooks, and secret-safety slices.
- [ ] Provider/API regressions, frontend contract tests, diff checks, and secret scans pass.

## Notes

- Product shape is an operational SaaS settings surface: dense, quiet, scan-first, and consistent with the existing Flask template plus static CSS/JS stack.
