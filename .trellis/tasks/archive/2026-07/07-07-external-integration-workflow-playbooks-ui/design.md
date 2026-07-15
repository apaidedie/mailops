# External integration workflow playbooks UI design

## Boundary

The playbook UI is a display/copy adapter inside the existing Settings -> API Security command center. It lives in `static/js/main.js` beside the current external API starter helpers and uses the existing `/api/providers` caches: `mailboxProviderIntegrationManifestCache`, `mailboxProviderIntegrationGuideCache`, and command-center endpoint helpers.

No template-level second entry point is added. `templates/index.html` already owns the `#externalApiCommandCenter` loading shell, and the command center render function owns the hydrated UI.

## Data Flow

`loadMailboxProviderCatalog()` caches `data.integration_manifest`. New helper `getExternalIntegrationManifestWorkflows()` reads `manifest.workflows` and normalizes only objects with stable keys and step arrays.

`renderExternalApiCommandCenter()` calls the workflow helpers after endpoint map and starter snippet calculation. It renders a playbook area below the starter snippet, with selectable workflow buttons and the selected workflow's ordered step list.

Copy flow uses `copyExternalApiWorkflowPlaybook()`, which calls `getExternalApiWorkflowPlaybookText(selectedKey)` and writes the generated text through the existing `copyTextToClipboard()` helper.

Fallback flow builds provider-agnostic playbooks from `getExternalApiStarterEndpointMap()` and existing stable endpoint keys. It is used only when the manifest has no workflows.

## Visual Direction

Operational SaaS, dense but calm. The playbook section should look like a professional integration console: compact rail, clear method badges, endpoint-first rows, restrained borders, and readable metadata. It must not use oversized hero copy or decorative cards.

Desktop layout: workflow selector rail and selected workflow details share one band under the starter kit. Mobile layout stacks the selector and details, keeping endpoints wrapped and copy controls reachable.

## Compatibility

Starter snippet modes and existing copy button stay unchanged. Language switching rerenders the command center through existing render paths. Degraded provider catalog state still shows fallback endpoints and fallback playbooks.

## Secret Safety

The playbook text and UI render only endpoint paths, request field names, response field names, API-key placeholder text, and provider selector allowed values supplied by the manifest. It must not read secret input IDs or render real key values.

## Rollback

Rollback removes the workflow helper/render/style/test additions. No backend or storage changes are involved.
