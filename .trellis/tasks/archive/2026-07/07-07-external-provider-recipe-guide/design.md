# External provider recipe guide design

## Source of truth

The frontend reads provider recipes from the same catalog caches already used by the external API command center. The preferred source is `integration_manifest.selection_recipes`; compatible fallbacks are `integration_manifest.selection.recipes`, `provider_integration_guide.selection_recipes`, and `deployment_profile.selection_recipes`.

The UI remains a display adapter. It does not define provider-specific behavior and does not branch on built-in provider names.

## UI shape

The guide is rendered inside `renderExternalApiCommandCenter()` after the starter snippet and before workflow playbooks. It uses a compact two-column layout: recipe tabs on the left and selected recipe detail on the right. Tablet and mobile collapse to one column.

The selected detail includes the recipe label, scope/provider metadata, priority, configuration snippets, request examples, and provider env hints. Empty sections are omitted so short recipes stay readable.

## Copy behavior

`getExternalProviderRecipeText()` builds a plain-text handoff that is safe for external projects. API auth stays as `X-API-Key: <your-api-key>`. Secret env/settings hints are rendered with empty values. No DOM credential inputs are read.

## Tests

Frontend contract tests assert helper names, render wiring, event delegation, CSS hooks, source fallback strings, copy behavior strings, and secret-safety. Existing backend provider/API tests continue to own the typed API contract.
