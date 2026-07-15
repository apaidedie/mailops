# Force catalog reload supersedes soft in-flight

## Problem

`loadMailboxProviderCatalog(true)` starts a new GET but soft in-flight responses
can still write `mailboxProviderCatalogCache` after force completes (no request
identity). Soft and force also thrash the shared promise finally-nulling.

## Goal

1. Soft joins soft/force in-flight; force joins only force in-flight.
2. Force supersedes soft in-flight; soft responses must not write after supersede.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadForce flag + request identity
- [x] Soft cannot overwrite after force supersede
- [x] Focused tests green
