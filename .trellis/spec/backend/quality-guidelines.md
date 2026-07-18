# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend quality is contract-first: public API envelopes, provider discovery payloads, database migrations, and secret-safety rules are part of the product. Prefer small service-owned contracts, focused controllers, and tests that prove the external behavior rather than only implementation details.

---

## Forbidden Patterns

- Rebuilding provider selection, endpoint maps, integration manifests, quickstarts, or readiness summaries outside `outlook_web.services.provider_catalog`.
- Adding direct SQLite writes in controllers when a repository or service-owned read model should own the data access.
- Adding external automation routes outside `/api/v1/external/*`, or re-introducing removed `/api/external/*` dual mounts without an explicit migration plan.
- Returning raw provider diagnostics, mailbox credentials, task tokens, claim tokens, refresh tokens, or provider bearer/API token values from discovery/readiness/list endpoints.
- Adding network probes to local discovery, readiness, OpenAPI, docs, or project readiness paths. Upstream probes must remain explicit.
- Adding broad `except Exception: pass` blocks except for explicitly best-effort behavior such as audit logging or cleanup.

---

## Required Patterns

<!-- Patterns that must always be used -->

### Scenario: Overview External API Usage Projection

#### 1. Scope / Trigger
- Trigger: backend changes that add, remove, or reinterpret fields returned by `/api/overview/external-api` or aggregate rows from `external_api_consumer_usage_daily` for Dashboard operations UI.

#### 2. Signatures
- `outlook_web.repositories.overview.get_external_api_stats(conn: sqlite3.Connection | None = None, *, days: int = 7) -> dict[str, Any]`
- `outlook_web.controllers.overview.api_get_overview_external_api() -> Response`
- `GET /api/overview/external-api`
- `GET /api/overview/external-api-stats`
- `external_api_consumer_usage_daily(consumer_key, consumer_name, caller_id, usage_date, date, endpoint, total_count, call_count, success_count, error_count, last_status, last_used_at)`

#### 3. Contracts
The overview repository owns the external API operations projection. Controllers and frontend code must not re-aggregate raw usage rows. The response must preserve the backward-compatible fields `kpi`, `daily_series`, `by_endpoint`, and `caller_rank` while allowing additive safe fields such as `health`, `endpoint_health`, `kpi.error_rate`, caller `error_rate`, `endpoint_count`, and `last_status`.

Aggregation must accept both current and legacy row shapes: prefer `usage_date` while falling back to `date`, and prefer positive `call_count` while falling back to `total_count`. Empty data must return valid zero/empty structures rather than omitting keys.

The projection is local-only and secret-safe. It may expose operational identifiers already stored in the usage table, such as `consumer_key`, `consumer_name`, `caller_id`, endpoint path, counts, rates, status, and timestamps. It must not return plaintext API keys, masked key placeholders, provider bearer/API token values, passwords, JWTs, refresh tokens, mailbox credentials, claim tokens, task tokens, or decrypted account fields.

#### 4. Validation & Error Matrix
- No rows in the selected window -> `kpi.week_calls=0`, `health.status=idle`, empty `endpoint_health`, empty `caller_rank`, and a full `daily_series` with zero counts.
- Rows use only legacy `date`/`call_count` -> counts still contribute to KPI, caller, endpoint, and series projections.
- Endpoint or caller has errors -> error counts/rates contribute to `health.status=attention` when error rate is at least 10% or a caller has at least 5 errors.
- Multiple endpoints for one consumer -> caller `endpoint_count` counts distinct non-empty endpoints.
- Multiple statuses for one caller/endpoint -> `last_status` follows the latest `last_used_at` string.

#### 5. Good/Base/Bad Cases
- Good: repository query reads only `external_api_consumer_usage_daily` and returns normalized dictionaries.
- Good: `by_endpoint` remains available for older UI/tests while `endpoint_health` adds richer operational fields.
- Base: `consumer_key` remains visible as a stable usage identifier because older overview rows already expose it.
- Bad: controller code manually querying the usage table to add one more response field.
- Bad: adding API-key or provider-token values to overview payloads to make the UI more convenient.

#### 6. Tests Required
- Repository tests must cover empty data, populated current rows, legacy row compatibility when touched, endpoint health error rates, caller health fields, and health status derivation.
- API tests must assert authenticated success, unauthenticated 401, top-level schema, and enriched fields when seeded data exists.
- Frontend contract tests must be updated when response fields are consumed by Overview JS.

#### 7. Wrong vs Correct
##### Wrong
```python
@login_required
def api_get_overview_external_api():
    rows = get_db().execute("SELECT * FROM external_api_consumer_usage_daily").fetchall()
    return jsonify({"rows": [dict(row) for row in rows]})
```

##### Correct
```python
@login_required
def api_get_overview_external_api() -> Any:
    return jsonify(overview_repo.get_external_api_stats())
```

### Scenario: Overview Unified Mailbox Command Center

#### 1. Scope / Trigger
- Trigger: backend changes that add, remove, or reinterpret fields returned by `/api/overview/summary.command_center` for the Dashboard summary tab.

#### 2. Signatures
- `outlook_web.repositories.overview.get_overview_summary(conn: sqlite3.Connection | None = None) -> dict[str, Any]`
- `outlook_web.services.overview_command_center.get_overview_command_center() -> dict[str, Any]`
- `outlook_web.services.overview_command_center.get_overview_command_center_degraded() -> dict[str, Any]`
- `outlook_web.controllers.overview.api_get_overview_summary() -> Response`
- `GET /api/overview/summary`

#### 3. Contracts
The overview repository remains SQL-only and must not import service modules. The controller composes the existing SQL summary with `command_center` from `outlook_web.services.overview_command_center`, then caches the combined payload with the existing overview TTL.

`command_center` is a local-only, read-only projection over existing service contracts. It may call `list_unified_mailboxes(page=1, page_size=1)` and `get_external_api_readiness_summary(consumer=None, database_ok=True, upstream_probe_ok=None)`, but it must not start provider upstream probes, create mailboxes, claim pool inventory, read messages, or rebuild provider selection rules outside `provider_catalog`.

The payload must include `overall_status`, `mailbox_inventory`, `provider_readiness`, `external_api`, and `actions`. It may expose counts, statuses, safe endpoint paths such as `/api/v1/external/integration-bundle`, docs/navigation targets, and action metadata. It must not return API keys, bearer values, JWTs, passwords, refresh tokens, mailbox credentials, claim tokens, task tokens, consumer keys, provider secret values, or raw Settings credential fields.

#### 4. Validation & Error Matrix
- Mailbox catalog loads normally -> inventory counts come from `summary`, `pagination`, `facets.providers`, and `provider_context.readiness_summary`.
- Mailbox count is zero -> `mailbox_inventory.status=empty` and `overall_status=empty` unless a degradation is present.
- Provider readiness reports needs-config -> `provider_readiness.status=needs_config` and actions include provider configuration guidance.
- External readiness is restricted because pool endpoints are disabled or unavailable -> command center may still be `ready` when the mailbox directory and provider routing are usable.
- Any command-center projection failure -> `/api/overview/summary` still returns the base SQL summary and `command_center.overall_status=degraded` from `get_overview_command_center_degraded()`.

#### 5. Good/Base/Bad Cases
- Good: controller attaches `result["command_center"] = get_overview_command_center()` after repository summary aggregation.
- Good: service helper reuses `provider_context.readiness_summary` and external readiness fields instead of duplicating provider rules.
- Base: action `target` values are safe app navigation tokens or endpoint paths, never credential values.
- Bad: importing `outlook_web.services.mailbox_catalog` from `outlook_web.repositories.overview` to make the repository the single aggregation point.
- Bad: adding provider-name branches such as `duckmail`, `mail_tm`, `tempmail_lol`, `emailnator`, or `gptmail` to the overview controller or frontend command-center projection.

#### 6. Tests Required
- API tests must assert authenticated schema, unauthenticated 401, stable command-center fields, degraded fallback, and secret safety.
- Module-boundary tests must remain green so repositories do not import services and routes stay thin.
- Frontend contract tests must be updated when command-center fields are consumed by Overview JS.

#### 7. Wrong vs Correct
##### Wrong
```python
from outlook_web.services.mailbox_catalog import list_unified_mailboxes

def get_overview_summary():
    summary = _sql_summary()
    summary["command_center"] = list_unified_mailboxes(page=1, page_size=1)
    return summary
```

##### Correct
```python
def api_get_overview_summary() -> Any:
    result = overview_repo.get_overview_summary()
    result["command_center"] = get_overview_command_center()
    return jsonify(result)
```

### Scenario: Local Demo Workspace Seed

#### 1. Scope / Trigger
- Trigger: changes to first-run onboarding, local demo data, GitHub visitor trial paths, or scripts that generate sample Outlook/IMAP/temp-mail/external-API state.
- Scope: `scripts/seed_demo_workspace.py`, `docs/project-launchpad.md`, README first-run sections, `scripts/project_readiness_check.py`, and focused demo-seed tests.

#### 2. Contracts
The local demo workspace must stay an explicit operator command, not an app startup side effect. The default target database is `output/demo/mailops-demo.db`; the script must not write to `data/outlook_accounts.db` unless an operator explicitly passes that path.

Demo seeding must call the real `init_db(database_path=...)` migration path, then write only synthetic, clearly tagged rows. Repeated runs must be deterministic by deleting or replacing only rows that match stable demo markers before inserting fresh demo rows.

The demo seed is local-only and network-free. It must not instantiate the Flask app, start schedulers, call upstream temp-mail providers, claim real mailboxes, or probe provider networks.

The seed data must remain secret-safe. It may use placeholder credentials that cannot authenticate anywhere and should encrypt account credential placeholders when writing account fields. It must not contain real API keys, provider bearer tokens, refresh tokens, mailbox passwords, task tokens, claim tokens, JWTs, consumer secrets, or token-like literals that match readiness secret scanners.

#### 3. Tests Required
- Test dry-run output does not create or mutate a database.
- Test reset seeding creates representative account, temp-mail, message, pool, verification, and external API usage rows.
- Test repeated seeding keeps stable demo counts deterministic.
- Test JSON output remains parseable and secret-scanner safe.
- Update `scripts/project_readiness_check.py` and its tests when demo onboarding docs or the seed script contract changes.

#### 4. Wrong vs Correct
##### Wrong
```python
init_db()
seed_demo_rows(config.get_database_path())
```

This can mutate the production database during ordinary startup.

##### Correct
```python
db_path = Path("output/demo/mailops-demo.db")
init_db(database_path=str(db_path))
```

Keep demo data isolated behind an explicit script and an explicit database path.

### Scenario: Local Demo Workspace Bootstrap

#### 1. Scope / Trigger
- Trigger: changes to authenticated first-run onboarding, `/api/bootstrap`, or UI surfaces that identify the local demo database.
- Scope: `outlook_web.controllers.system.api_bootstrap`, the demo database detector, the authenticated workspace shell, and focused bootstrap/frontend contract tests.

#### 2. Signatures
- `GET /api/bootstrap -> { success: true, bootstrap: { demo_workspace: {...} } }`
- Demo database path: `output/demo/mailops-demo.db`.

#### 3. Contracts
`/api/bootstrap` may expose `demo_workspace` only as secret-safe page-shell metadata. For the default local demo database it returns `enabled=true`, `label`, relative `database`, `synthetic=true`, and quick-action descriptors with `key`, `label`, `page`, and optional `tab`. For ordinary databases it returns exactly `{"enabled": false}`.

The detector must compare the configured `DATABASE_PATH` to the default demo database without creating the database, seeding rows, starting schedulers, or probing provider networks. The payload must never include absolute filesystem paths, provider bearer tokens, API keys, task tokens, claim tokens, mailbox passwords, refresh tokens, or live mailbox content.

#### 4. Validation & Error Matrix
- `DATABASE_PATH=output/demo/mailops-demo.db` -> `demo_workspace.enabled=true` with relative database label and quick actions.
- `DATABASE_PATH=data/outlook_accounts.db` or any other ordinary path -> `demo_workspace={"enabled": false}`.
- Path resolution fails -> treat as disabled rather than raising during bootstrap.
- Future quick actions are added -> keep them navigation descriptors only; no credentials or provider-specific routing logic in bootstrap.

#### 5. Good/Base/Bad Cases
- Good: bootstrap returns `database: "output/demo/mailops-demo.db"` and `quick_actions: [{"key":"external_api","page":"dashboard","tab":"external-api"}]`.
- Base: a non-demo deployment still includes a disabled `demo_workspace` object so frontend code can stay defensive and simple.
- Bad: returning `E:\...\output\demo\mailops-demo.db`, environment variables, provider tokens, or seeded mailbox message bodies.
- Bad: automatically calling `seed_demo_workspace.py` during app startup or bootstrap.

#### 6. Tests Required
- API tests must cover enabled and disabled bootstrap payloads.
- Tests must assert the enabled payload is relative-path only and secret-safe.
- Frontend contract tests must cover the mount point and consumer helpers when the bootstrap field is used by the UI.

#### 7. Wrong vs Correct
##### Wrong
```python
return {"demo_workspace": {"enabled": True, "database": config.get_database_path()}}
```

##### Correct
```python
return {"demo_workspace": {"enabled": True, "database": "output/demo/mailops-demo.db", "synthetic": True}}
```

### Scenario: Baseline Security Response Headers

#### 1. Scope / Trigger
- Trigger: Backend infra changes that register Flask middleware, touch response headers, static response handling, trace/error after-request hooks, CORS, or deployment-facing security behavior.
- Scope: `outlook_web/middleware/security_headers.py`, the `create_app()` middleware registration in `outlook_web/app.py`, and related config helpers in `outlook_web/config.py`.

#### 2. Signatures
- Middleware: `attach_security_headers(response) -> response`.
- CSP helper: `build_content_security_policy(*, upgrade_insecure_requests: bool = False) -> str`.
- HSTS helper: `build_hsts_header() -> str`.
- Config helpers: `get_security_headers_enabled() -> bool`, `get_security_headers_force_hsts() -> bool`, `get_security_hsts_max_age() -> int`.

#### 3. Contracts
- Default behavior: every Flask response receives `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Content-Security-Policy` unless `SECURITY_HEADERS_ENABLED=false`.
- Header writes must use `response.headers.setdefault(...)` so route-specific headers, static cache headers, trace IDs, content types, and CORS headers are not overwritten.
- CSP must stay compatible with the current template shape, including existing inline scripts/styles, until a separate nonce/hash CSP refactor removes inline code.
- Browser scripts required by protected app pages must be served from first-party static paths. Do not add CDN script hosts to `script-src`; vendor the asset under `static/` or add a build step that emits a local file.
- HSTS is emitted only when `request.is_secure` is true or `SECURITY_HEADERS_FORCE_HSTS=true`; ordinary local HTTP responses must not emit HSTS by default.
- `SECURITY_HSTS_MAX_AGE` is optional, defaults to `31536000`, invalid values fall back safely, and negative values are clamped to zero.

#### 4. Validation & Error Matrix
- `SECURITY_HEADERS_ENABLED=false` -> skip all baseline security headers and leave other middleware behavior untouched.
- Local HTTP request with default config -> no `Strict-Transport-Security`; CSP must not include `upgrade-insecure-requests`.
- HTTPS or forced-HSTS request -> include `Strict-Transport-Security` and add `upgrade-insecure-requests` to CSP.
- Existing route header value -> preserve the existing value and still add missing baseline headers.
- Extension CORS preflight -> preserve `Access-Control-Allow-Origin` and `Access-Control-Allow-Headers` while adding security headers.
- Template adds a required script dependency -> verify the script URL is compatible with `script-src 'self'` and that the browser does not emit a CSP violation.

#### 5. Good/Base/Bad Cases
- Good: a secure `/healthz` response includes baseline headers, trace ID, HSTS, and CSP `upgrade-insecure-requests`.
- Base: a local HTTP `/healthz` response includes baseline headers and trace ID, but no HSTS.
- Bad: middleware assigns headers directly with `response.headers[...] = ...`, which can overwrite route-specific CSP, static caching, or CORS integration behavior.
- Bad: adding `<script src="https://cdn.example.com/library.js">` to a protected app page and then widening `script-src` to allow that CDN.
- Good: storing the reviewed library file under `static/vendor/library.min.js` and loading it through `url_for('static', filename='vendor/library.min.js')`.

#### 6. Tests Required
- HTML response assertions for baseline headers and compatible CSP directives.
- JSON/API response assertions that baseline headers coexist with `X-Trace-Id`.
- Static asset assertions that `Cache-Control` remains unchanged while security headers are present.
- HSTS assertions for local HTTP absence, HTTPS presence, forced-HSTS presence, and custom max-age.
- No-overwrite assertions for route-specific `X-Frame-Options` and `Content-Security-Policy`.
- Extension CORS preflight assertions for both CORS headers and security headers.
- Template/static asset assertions for required browser libraries that must run under the self-only script policy.

#### 7. Wrong vs Correct
##### Wrong
```python
response.headers["Content-Security-Policy"] = strict_policy
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

##### Correct
```python
response.headers.setdefault("Content-Security-Policy", build_content_security_policy(upgrade_insecure_requests=emit_hsts))
if emit_hsts:
    response.headers.setdefault("Strict-Transport-Security", build_hsts_header())
```

### Scenario: Container Healthcheck Wiring

#### 1. Scope / Trigger
- Trigger: Deployment changes that touch `Dockerfile`, `docker-compose.yml`, `/healthz`, Gunicorn startup, or container health check behavior.
- Scope: `scripts/healthcheck.py`, `Dockerfile`, `docker-compose.yml`, and tests that assert deployment wiring.

#### 2. Signatures
- Command: `python scripts/healthcheck.py [--url URL] [--timeout SECONDS]`.
- Default URL: `http://localhost:5000/healthz`.
- Default timeout: `4` seconds.

#### 3. Contracts
- Dockerfile and Compose health checks must call `python scripts/healthcheck.py`; do not duplicate inline `python -c` or `urllib.request` snippets in deployment config.
- The script must remain standard-library only so it works inside the slim production image before optional dependencies or app imports are available.
- Exit code `0` means the endpoint returned HTTP 200 and, for JSON responses, `status` is exactly `ok`.
- Non-200 responses, invalid JSON, JSON without `status=ok`, connection failures, and invalid CLI arguments must return non-zero.
- Failure output must be concise and must not print secrets or unrelated environment values.

#### 4. Validation & Error Matrix
- HTTP 200 with `{"status":"ok"}` -> exit `0`.
- HTTP 200 with non-JSON body -> exit `0`; this preserves compatibility with simple liveness endpoints.
- HTTP 200 with JSON `status` not equal to `ok` -> exit `1`.
- HTTP 4xx/5xx -> exit `1`.
- Connection refused, timeout, DNS, or socket error -> exit `1`.
- `--timeout <= 0` -> exit `2`.

#### 5. Good/Base/Bad Cases
- Good: `HEALTHCHECK ... CMD ["python", "scripts/healthcheck.py"]` in `Dockerfile` and `test: ["CMD", "python", "scripts/healthcheck.py"]` in Compose.
- Base: local operators can run `python scripts/healthcheck.py --url http://127.0.0.1:5000/healthz` for the same contract Docker uses.
- Bad: keeping separate inline `urllib.request.urlopen(...)` commands in Dockerfile and Compose, which can drift from each other and from tests.

#### 6. Tests Required
- Unit tests for healthy JSON, healthy plain 200, non-200, invalid JSON, JSON `status` mismatch, connection failure, and invalid timeout.
- A subprocess CLI test that executes `python scripts/healthcheck.py --url <test-server>`.
- Deployment wiring tests that assert Dockerfile and Compose call `scripts/healthcheck.py` and do not reintroduce inline `urllib.request` checks.

#### 7. Wrong vs Correct
##### Wrong
```dockerfile
HEALTHCHECK CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://localhost:5000/healthz').read()"]
```

##### Correct
```dockerfile
HEALTHCHECK CMD ["python", "scripts/healthcheck.py"]
```

### Scenario: Dependency Security Automation

#### 1. Scope / Trigger
- Trigger: changes to `requirements.txt`, dependency update automation, GitHub Actions versions, Docker release quality gates, or local repository readiness checks.

#### 2. Signatures
- `.github/dependabot.yml -> updates[package-ecosystem=pip|github-actions]`
- `.github/workflows/dependency-security.yml -> python-dependency-audit`
- `.github/workflows/docker-build-push.yml -> quality-gate`
- `scripts.project_readiness_check._dependency_security_automation(root: Path) -> CheckResult`
- Scanner command: `pip-audit -r requirements.txt --progress-spinner off`.

#### 3. Contracts
Dependabot must cover both the root Python requirements and GitHub Actions on a restrained weekly cadence. Non-major updates may be grouped to reduce pull-request noise, but major updates remain isolated for explicit review. Automatic merge is not part of this contract.

CI must install a pinned `pip-audit` version. The dedicated dependency workflow captures the scanner exit code, writes a JSON report, uploads that report with `if: always()`, and only then fails on vulnerabilities or audit errors. Do not use `continue-on-error: true` without a later explicit failure gate, because that can turn known vulnerabilities into a permanently green workflow.

The Docker publish `quality-gate` must repeat the dependency audit before repository readiness, tests, image build, or registry push. The local project readiness checker validates workflow/config wiring statically and remains network-free: it must not install the scanner, resolve requirements, query PyPI, or call GitHub APIs.

#### 4. Validation & Error Matrix
- No known vulnerabilities -> dedicated workflow uploads the JSON report and exits successfully.
- Known vulnerability -> report upload still runs, then the captured non-zero status fails the job.
- Dependency resolution or audit error -> treat the non-zero status as a blocking failure; do not silently downgrade it to a warning.
- Scanner step does not publish an exit code -> explicit failure step exits non-zero.
- Dependabot or workflow file is missing/drifts -> local readiness reports `security.dependency_automation` failure without network access.
- Docker tag build -> dependency audit passes before readiness/tests and before any image publication step.

#### 5. Good/Base/Bad Cases
- Good: `pip-audit==2.10.1` is synchronized across the dedicated workflow, Docker gate, readiness contract, task tests, and documentation.
- Good: the workflow artifact contains package names, versions, vulnerability IDs, and fix versions but no project credentials.
- Base: a local developer may run the same audit through an isolated tool runner such as `uvx --from pip-audit==2.10.1`.
- Bad: auditing only on a weekly schedule, so a vulnerable dependency change can merge before the next scan.
- Bad: scanning pull requests but omitting the release gate, allowing a tag build to publish without a fresh dependency audit.
- Bad: adding network resolution to `scripts/project_readiness_check.py`.

#### 6. Tests Required
- Contract tests must assert Dependabot ecosystems, weekly cadence, PR limits, labels, and non-major grouping.
- Workflow tests must assert triggers, read-only permissions, pinned scanner version, JSON output, unconditional artifact upload, captured exit code, and explicit failure behavior.
- Docker workflow tests must assert audit ordering before readiness and full tests.
- Readiness tests must cover the green repository and a drifted/missing dependency workflow.
- Before commit, run the focused workflow/readiness tests, a real local `pip-audit`, YAML parsing, formatter/import/lint checks for changed Python files, `python scripts/project_readiness_check.py`, and `git diff --check`.

#### 7. Wrong vs Correct

##### Wrong
```yaml
- name: Audit dependencies
  continue-on-error: true
  run: pip-audit -r requirements.txt
```

##### Correct
```yaml
- name: Audit dependencies
  id: audit
  run: |
    set +e
    pip-audit -r requirements.txt --format json --output pip-audit-report.json
    status=$?
    echo "exit_code=$status" >> "$GITHUB_OUTPUT"
    exit 0

- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4

- name: Fail on audit findings
  if: always()
  run: exit "${{ steps.audit.outputs.exit_code }}"
```

---

## Testing Requirements

- Backend API changes need focused tests for status code, response envelope, auth/guard behavior, and secret safety.
- External API changes must cover canonical `/api/v1/external/*` and legacy `/api/external/*` behavior when the route is externally visible.
- Provider selection/discovery changes must cover provider catalog/readiness/routing/capability contracts and OpenAPI schema impact.
- Database schema changes require migration tests plus idempotent fresh-db behavior.
- Docs/examples/readiness changes should run `python scripts/project_readiness_check.py` and related readiness tests when the checked assets or scanner behavior changes.
- Broad backend changes should run a focused pytest/unittest subset first, then the full suite or a documented high-signal subset before release handoff.

---

## Code Review Checklist

- Does the change preserve route -> controller -> service -> repository boundaries?
- Are public response envelopes stable and typed in OpenAPI/docs when exposed externally?
- Are canonical and legacy external API paths kept in sync through shared route registration?
- Are provider rules data-driven through provider catalog helpers instead of provider-name branches?
- Are all secrets represented only as key names/placeholders/blank values in public payloads?
- Are upstream network calls avoided in discovery/readiness/docs/OpenAPI/local readiness checks?
- Are tests scoped to the changed contract and strong enough to fail if the behavior is removed?
