# Design

## Backend

`_build_mailbox_provider_catalog` already iterates `get_provider_list()`. Copy `note` onto account catalog items so Settings/import can share one payload.

## Frontend

`loadProviders()`:

1. Fetch `/api/providers`
2. Build options from:
   - preferred: `mailbox_providers` where `kind === 'account'`
   - fallback: `providers` list
3. Map `{ key/provider, label, note, account_type }`
4. Render select options; keep `auto` first if present
5. Cache options for note display

`onProviderChange()`:

- Keep format-specific placeholders
- Append/update note text from cached option when present

## Template

Replace static Outlook-only option with loading placeholder option.
