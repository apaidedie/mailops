# JavaScript Integration Bundle Design

## Boundary

This task changes only the copyable JavaScript external API starter, its tests, and quickstart documentation. It does not change server API behavior, OpenAPI schemas, provider routing, or the Python starter.

## Helper Contract

Add `buildIntegrationBundle(baseUrl, discovery)` to `examples/external_api_javascript_client.js`.

Input:

- `baseUrl`: Outlook Email Plus instance URL.
- `discovery`: output from `client.discover()`.

Output:

- `base_url`
- `endpoints`
- `auth.header` and placeholder only
- `documentation`
- `provider_selection.source_priority`, `provider_values`, and `config_file`
- `templates`
- compact workflow list with `key`, `label`, and `description`
- `readiness.overall_status`, `totals`, and `issues`
- `openapi.version` and `path_count`

This mirrors the Python helper's shape so external services can choose either language without learning a different integration artifact.

## CLI Contract

`integration-bundle` is read-only and calls `client.discover()` only. It prints JSON to stdout by default. When `--output <path>` is passed, it creates parent directories as needed, writes JSON with a trailing newline, and prints the output path.

## Safety

The bundle is built from discovery payloads and must not include the API key passed to the CLI. Tests will serialize the bundle and assert the key is absent.
