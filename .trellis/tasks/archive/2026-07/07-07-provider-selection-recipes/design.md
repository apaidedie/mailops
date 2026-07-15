# Provider Selection Recipes Design

## Contract Shape

Add a `selection_recipes` list and a `selection_recipe_index` map. The list is convenient for UI rendering and ordered discovery. The index is convenient for automation that wants a recipe by `scope:provider` key.

Each recipe contains a stable `key`, `scope`, `provider`, `label`, `kind`, `active`, `source_priority`, `description`, optional `endpoint`, optional `request`, and `configuration` examples. Configuration examples include env variables, provider config object patches, settings payload fragments, and non-secret provider env hints.

## Data Sources

Recipes must be generated from `deployment_profile.provider_examples`, `deployment_profile.provider_values`, `selection_policy.scopes`, and `provider_integration_guide.providers`. The same recipe helper should feed every payload so capabilities, providers, OpenAPI, and mailbox directory context cannot drift.

## Secret Safety

Provider env hints reuse manifest key-hint rules: secret keys render as empty values. Recipes never call `os.environ` and never read stored secret values. Non-secret defaults such as provider base URLs may be included.

## Compatibility

Existing fields remain unchanged. The new fields are additive and versioned by the owning contracts, so existing clients can ignore them.

## OpenAPI

Add typed schemas for recipe entries and key hints. Wire them into `ProviderSelectionPolicy`, `ProviderIntegrationGuide`, `IntegrationManifest`, and deployment profile schema areas where those schemas already exist.
