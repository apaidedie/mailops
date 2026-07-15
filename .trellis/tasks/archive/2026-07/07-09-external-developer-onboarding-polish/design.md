# Design

## Boundary

This task is documentation plus local readiness validation. It does not change
mailbox services, provider selection semantics, external API controllers, or UI
runtime code.

## Launchpad Shape

`docs/project-launchpad.md` is a short, skimmable map that sits above the existing
deep docs. It should answer:

- What is this product?
- Which mailbox sources can it aggregate?
- How do I run it quickly?
- How does another service integrate through the API?
- How do I add or configure a provider?
- What checks prove the repository or a running instance is ready?

It links to existing authoritative docs instead of duplicating full API or
provider contracts.

## Readiness Gate

`scripts/project_readiness_check.py` remains local-only and zero-dependency. Add
the launchpad to required assets, secret scan paths, README link checks, and a new
launchpad contract check. The checker should only verify durable references and
safe placeholders; it must not require network access or inspect live runtime
state.

## Compatibility

Canonical external paths remain `/api/v1/external/*`. Legacy paths are only
mentioned as compatibility metadata in existing docs. The launchpad should point
new clients at canonical paths.

## Security

The launchpad can show secret key names with empty placeholders but must not show
real credential-looking values. Reuse the existing secret scanner by adding the
new doc to `SECRET_SCAN_PATHS`.
