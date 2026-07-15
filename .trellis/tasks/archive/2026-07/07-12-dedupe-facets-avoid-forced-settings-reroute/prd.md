# Dedupe provider facets and avoid forced settings reroute

## Goal

1. De-dupe unified mailbox provider facets/filter options for bridge aliases.
2. Avoid PluginManager radio inject always calling `onTempMailProviderChange`, which re-renders schema panel and can wipe mid-edit dirty state.

## Requirements

- Facet chips and provider filter options canonicalize temp keys and merge counts.
- Plugin radio inject only re-routes Settings when selection changes or a new plugin option was added.
- Contract tests cover markers.

## Acceptance Criteria

- [x] Facets/filter options use de-dupe/canonical keys.
- [x] Plugin inject does not always force Settings reroute.
- [x] Focused tests + `git diff --check` pass.
