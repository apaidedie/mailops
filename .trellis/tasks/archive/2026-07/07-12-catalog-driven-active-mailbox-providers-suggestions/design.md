# Design

## Approach

Add a suggestion chips strip under `#activeMailboxProviders`. Source values from cached selection policy (`active_allowlist.allowed_values`), same pattern as pool-default datalist.

## Interaction

- Chip inactive: provider not in textarea → click appends line
- Chip active: provider already present → click removes that line
- Free-text edits still allowed; chip active state re-syncs on textarea input

## Data flow

`/api/providers` → `mailboxProviderSelectionPolicyCache` → `renderActiveMailboxProviderSuggestions()` → chips DOM

## Compatibility

- Empty textarea still means all providers
- Unknown typed values still submitted; backend remains authority
