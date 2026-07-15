from __future__ import annotations

from html import escape
from typing import Any

from outlook_web.services.external_api_openapi import get_external_api_openapi_contract
from outlook_web.services.provider_catalog import EXTERNAL_API_V1_PREFIX


def render_external_api_docs_html(*, consumer: dict[str, Any] | None = None) -> str:
    """Render a self-contained external API documentation page from OpenAPI."""
    contract = get_external_api_openapi_contract(consumer=consumer)
    capabilities = contract.get("x-capabilities") if isinstance(contract.get("x-capabilities"), dict) else {}
    endpoints = capabilities.get("endpoints") if isinstance(capabilities.get("endpoints"), dict) else {}
    manifest = capabilities.get("integration_manifest") if isinstance(capabilities.get("integration_manifest"), dict) else {}
    quickstart = manifest.get("quickstart") if isinstance(manifest.get("quickstart"), dict) else {}
    selection_policy = capabilities.get("selection_policy") if isinstance(capabilities.get("selection_policy"), dict) else {}
    defaults = capabilities.get("defaults") if isinstance(capabilities.get("defaults"), dict) else {}
    paths = contract.get("paths") if isinstance(contract.get("paths"), dict) else {}
    path_groups = _group_operations(paths)
    provider_diagnostics = capabilities.get("provider_diagnostics") if isinstance(capabilities.get("provider_diagnostics"), dict) else {}
    integration_bundle = capabilities.get("integration_bundle") if isinstance(capabilities.get("integration_bundle"), dict) else {}

    service_title = _text((contract.get("info") or {}).get("title"), "Outlook Email Plus External API")
    app_version = _text((contract.get("info") or {}).get("version"), "")
    external_version = _text(contract.get("x-external-api-version"), "v1")
    operation_count = _operation_count(path_groups)

    return "".join(
        [
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
            f"<title>{escape(service_title)} Docs</title>",
            _style_block(),
            "</head><body>",
            "<main class=\"page-shell\">",
            _hero(service_title=service_title, app_version=app_version, external_version=external_version, path_count=operation_count),
            _surface_metrics(
                app_version=app_version,
                external_version=external_version,
                path_count=operation_count,
                provider_diagnostics=provider_diagnostics,
                manifest=manifest,
            ),
            _quick_links(endpoints),
            _integration_bundle_section(integration_bundle=integration_bundle, endpoints=endpoints),
            _auth_section(manifest),
            _workflow_section(quickstart),
            _provider_section(selection_policy=selection_policy, defaults=defaults),
            _endpoint_catalog(path_groups),
            _footer(),
            "</main>",
            "</body></html>",
        ]
    )


def _text(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or fallback


def _method_badge(method: str) -> str:
    return f'<span class="method method-{escape(method.lower())}">{escape(method.upper())}</span>'


def _operation_count(path_groups: list[dict[str, Any]]) -> int:
    return sum(len(group.get("operations") or []) for group in path_groups)


def _style_block() -> str:
    return """
<style>
:root {
  color-scheme: light;
  --bg: #f6f8fb;
  --surface: #ffffff;
  --surface-soft: #eef3f8;
  --surface-ink: #101827;
  --text: #172033;
  --muted: #5f6f83;
  --border: #d8e1ec;
  --border-strong: #b8c7d9;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --green: #15803d;
  --green-soft: #dcfce7;
  --orange: #b45309;
  --orange-soft: #fef3c7;
  --red: #b91c1c;
  --shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
}
.page-shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 48px; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; align-items: end; padding: 30px; border: 1px solid var(--border); background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%); box-shadow: var(--shadow); }
.eyebrow { margin: 0 0 8px; color: var(--accent); font-size: 13px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }
h1 { margin: 0; font-size: 32px; line-height: 1.16; letter-spacing: 0; }
h2 { margin: 0 0 16px; font-size: 20px; line-height: 1.25; letter-spacing: 0; }
h3 { margin: 0 0 6px; font-size: 15px; letter-spacing: 0; }
p { margin: 0; color: var(--muted); }
.hero-text { max-width: 760px; }
.hero-copy { margin-top: 10px; max-width: 720px; }
.hero-rail { display: grid; gap: 8px; min-width: 230px; }
.hero-rail-item { display: flex; justify-content: space-between; gap: 18px; padding: 9px 11px; border: 1px solid var(--border); background: rgba(255, 255, 255, 0.75); }
.hero-rail-label { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
.hero-rail-value { color: var(--text); font-size: 13px; font-weight: 700; text-align: right; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.pill { display: inline-flex; align-items: center; min-height: 30px; padding: 4px 10px; border: 1px solid var(--border); background: var(--surface-soft); color: var(--text); font-size: 13px; font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; margin-top: 16px; }
.panel { min-width: 0; border: 1px solid var(--border); background: var(--surface); padding: 20px; }
.panel.span-4 { grid-column: span 4; }
.panel.span-6 { grid-column: span 6; }
.panel.span-8 { grid-column: span 8; }
.panel.span-12 { grid-column: span 12; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }
.metric-card { min-width: 0; padding: 16px; border: 1px solid var(--border); background: var(--surface); }
.metric-value { display: block; color: var(--surface-ink); font-size: 24px; line-height: 1.1; font-weight: 760; }
.metric-label { display: block; margin-top: 5px; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
.metric-note { margin-top: 8px; font-size: 13px; overflow-wrap: anywhere; }
.status-ok { color: var(--green); }
.status-warn { color: var(--orange); }
.link-list, .workflow-list, .meta-list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
.link-row, .workflow-row, .meta-row { display: grid; gap: 4px; min-width: 0; }
.label { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code, pre { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
code { overflow-wrap: anywhere; color: #0f172a; }
pre { margin: 12px 0 0; padding: 14px; overflow-x: auto; border: 1px solid #1e293b; background: #0f172a; color: #e2e8f0; font-size: 13px; }
.console-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; margin-top: 14px; }
.console-step { min-width: 0; padding: 12px; border: 1px solid var(--border); background: var(--surface-soft); }
.console-step strong { display: block; margin-bottom: 4px; color: var(--text); font-size: 13px; }
.workflow-number { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; margin-right: 8px; border: 1px solid var(--border-strong); background: var(--surface); color: var(--text); font-size: 12px; font-weight: 800; }
.endpoint-catalog { margin-top: 18px; }
.endpoint-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.endpoint-table th, .endpoint-table td { padding: 12px 10px; border-top: 1px solid var(--border); text-align: left; vertical-align: top; }
.endpoint-table th { color: var(--muted); font-size: 12px; text-transform: uppercase; }
.endpoint-table td { font-size: 14px; }
.endpoint-path { overflow-wrap: anywhere; }
.summary { color: var(--text); font-weight: 650; }
.operation-id { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.method { display: inline-flex; width: 58px; justify-content: center; padding: 4px 7px; font-size: 12px; font-weight: 800; color: #ffffff; }
.method-get { background: var(--green); }
.method-post { background: var(--accent); }
.method-put { background: var(--orange); }
.method-delete { background: var(--red); }
.schema-stack { display: grid; gap: 4px; color: var(--muted); font-size: 12px; }
.section-title { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.section-count { color: var(--muted); font-size: 13px; white-space: nowrap; }
.footer { margin-top: 16px; color: var(--muted); font-size: 13px; }
@media (max-width: 820px) {
  .page-shell { width: min(100% - 24px, 1180px); padding-top: 20px; }
  .hero { grid-template-columns: 1fr; padding: 18px; }
  .hero-rail { min-width: 0; }
  .hero, .panel { padding: 16px; }
  h1 { font-size: 25px; }
  .panel.span-4, .panel.span-6, .panel.span-8, .panel.span-12 { grid-column: span 12; }
  .metric-grid { grid-template-columns: 1fr; }
  .endpoint-table, .endpoint-table tbody, .endpoint-table tr, .endpoint-table td { display: block; width: 100%; }
  .endpoint-table thead { display: none; }
  .endpoint-table tr { border-top: 1px solid var(--border); padding: 10px 0; }
  .endpoint-table td { border: 0; padding: 5px 0; }
  .endpoint-table td::before { content: attr(data-label); display: block; color: var(--muted); font-size: 11px; font-weight: 800; text-transform: uppercase; }
}
</style>
"""


def _hero(*, service_title: str, app_version: str, external_version: str, path_count: int) -> str:
    return f"""
<section class="hero">
  <div class="hero-text">
    <p class="eyebrow">Authenticated integration surface</p>
    <h1>{escape(service_title)}</h1>
    <p class="hero-copy">Integration Console for unified Outlook, IMAP, pool, and temp-mail automation. Start with discovery, select a mailbox source, then use mailbox sessions to read verification messages without coupling clients to provider internals.</p>
  </div>
  <div class="hero-rail" aria-label="External API summary">
    <div class="hero-rail-item"><span class="hero-rail-label">App</span><span class="hero-rail-value">{escape(app_version or "unknown")}</span></div>
    <div class="hero-rail-item"><span class="hero-rail-label">API</span><span class="hero-rail-value">{escape(external_version)}</span></div>
    <div class="hero-rail-item"><span class="hero-rail-label">Endpoints</span><span class="hero-rail-value">{path_count}</span></div>
    <div class="hero-rail-item"><span class="hero-rail-label">Prefix</span><span class="hero-rail-value">{escape(EXTERNAL_API_V1_PREFIX)}</span></div>
  </div>
</section>
"""


def _surface_metrics(
    *,
    app_version: str,
    external_version: str,
    path_count: int,
    provider_diagnostics: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    summary = provider_diagnostics.get("summary") if isinstance(provider_diagnostics.get("summary"), dict) else {}
    provider_total = int(summary.get("total") or 0)
    provider_ready = int(summary.get("ready") or 0)
    workflow_count = len(manifest.get("workflows") or []) if isinstance(manifest.get("workflows"), list) else 0
    secret_policy = _text((manifest.get("auth") or {}).get("placeholder"), "<your-api-key>")
    return f"""
<section class="metric-grid" aria-label="API Surface">
  <div class="metric-card">
    <span class="metric-value">{path_count}</span>
    <span class="metric-label">API Surface</span>
    <p class="metric-note">Generated from OpenAPI {escape(external_version)} for app {escape(app_version or "unknown")}.</p>
  </div>
  <div class="metric-card">
    <span class="metric-value status-ok">{provider_ready}/{provider_total}</span>
    <span class="metric-label">Provider Readiness</span>
    <p class="metric-note">Local provider diagnostics only; upstream probes are explicit.</p>
  </div>
  <div class="metric-card">
    <span class="metric-value">{workflow_count}</span>
    <span class="metric-label">Workflow Playbooks</span>
    <p class="metric-note">Discovery, mailbox directory, pool claim, and task temp-mail flows.</p>
  </div>
  <div class="metric-card">
    <span class="metric-value status-warn">Safe</span>
    <span class="metric-label">Secret Policy</span>
    <p class="metric-note">Auth examples use {escape(secret_policy)} and never echo runtime secrets.</p>
  </div>
</section>
"""


def _quick_links(endpoints: dict[str, Any]) -> str:
    keys = ["docs", "integration_bundle", "openapi", "capabilities", "providers", "provider_preflight", "mailboxes"]
    rows = []
    for key in keys:
        endpoint = _text(endpoints.get(key))
        if not endpoint:
            continue
        rows.append(
            f'<li class="link-row"><span class="label">{escape(key.replace("_", " "))}</span>'
            f'<a href="{escape(endpoint)}"><code>{escape(endpoint)}</code></a></li>'
        )
    return f"""
<section class="grid">
  <div class="panel span-8">
    <h2>Start Here</h2>
    <p>Use these discovery endpoints before writing provider-specific code. They describe the live instance, allowed providers, mailbox directory filters, and generated client contract.</p>
    <ul class="link-list">{''.join(rows)}</ul>
  </div>
  <div class="panel span-4">
    <h2>Secret Policy</h2>
    <p>This page uses placeholders and contract metadata only. It never echoes API keys, provider bearer tokens, passwords, refresh tokens, task tokens, or consumer keys.</p>
    <div class="console-strip">
      <div class="console-step"><strong>Header</strong><code>X-API-Key</code></div>
      <div class="console-step"><strong>Placeholder</strong><code>&lt;your-api-key&gt;</code></div>
    </div>
  </div>
</section>
"""


def _integration_bundle_section(*, integration_bundle: dict[str, Any], endpoints: dict[str, Any]) -> str:
    bundle_endpoint = _text(integration_bundle.get("endpoint") or endpoints.get("integration_bundle"), f"{EXTERNAL_API_V1_PREFIX}/integration-bundle")
    contract = _text(integration_bundle.get("response_contract"), "integration_bundle")
    recommended = integration_bundle.get("recommended_for") if isinstance(integration_bundle.get("recommended_for"), list) else []
    chips = "".join(f'<span class="pill">{escape(str(item))}</span>' for item in recommended[:4])
    return f"""
<section class="grid">
  <div class="panel span-12 integration-bundle-panel">
    <div class="section-title"><h2>Integration Readiness Bundle</h2><span class="section-count">{escape(contract)}</span></div>
    <p>Fetch one secret-safe readiness bundle before wiring an external service. It summarizes auth placeholders, canonical and legacy endpoint maps, provider selection, mailbox-session readiness, OpenAPI metadata, smoke checks, and next actions.</p>
    <div class="console-strip integration-bundle-strip">
      <div class="console-step"><strong>Endpoint</strong><code>{escape(bundle_endpoint)}</code></div>
      <div class="console-step"><strong>Method</strong><code>GET</code></div>
      <div class="console-step"><strong>Contract</strong><code>{escape(contract)}</code></div>
    </div>
    <div class="hero-meta">{chips}</div>
  </div>
</section>
"""


def _auth_section(manifest: dict[str, Any]) -> str:
    auth = manifest.get("auth") if isinstance(manifest.get("auth"), dict) else {}
    header = _text(auth.get("header"), "X-API-Key")
    placeholder = _text(auth.get("placeholder"), "<your-api-key>")
    return f"""
<section class="grid">
  <div class="panel span-12">
    <h2>Authentication</h2>
    <p>Every external API request uses an API key header. Use a scoped key for each external service when possible.</p>
    <pre>curl -H "{escape(header)}: {escape(placeholder)}" https://your-host{escape(EXTERNAL_API_V1_PREFIX)}/capabilities</pre>
  </div>
</section>
"""


def _workflow_section(quickstart: dict[str, Any]) -> str:
    sequence = quickstart.get("recommended_sequence") if isinstance(quickstart.get("recommended_sequence"), list) else []
    rows = []
    for index, item in enumerate(sequence[:6], start=1):
        if not isinstance(item, dict):
            continue
        method = _text(item.get("method"), "GET")
        endpoint = _text(item.get("endpoint"))
        step = _text(item.get("step"), "step")
        rows.append(
            f'<li class="workflow-row"><span><span class="workflow-number">{index}</span>{_method_badge(method)} <strong>{escape(step)}</strong></span>'
            f'<code>{escape(endpoint)}</code></li>'
        )
    requests = quickstart.get("requests") if isinstance(quickstart.get("requests"), dict) else {}
    session_start = requests.get("mailbox_session_start") if isinstance(requests.get("mailbox_session_start"), dict) else {}
    session_read = requests.get("mailbox_session_read") if isinstance(requests.get("mailbox_session_read"), dict) else {}
    session_close = requests.get("mailbox_session_close") if isinstance(requests.get("mailbox_session_close"), dict) else {}
    session_rows = _request_rows([("start", session_start), ("read", session_read), ("close", session_close)])
    return f"""
<section class="grid">
  <div class="panel span-6">
    <h2>Discovery Workflow</h2>
    <p>Call discovery first, then generate clients or choose a provider from the live contract.</p>
    <ul class="workflow-list">{''.join(rows)}</ul>
  </div>
  <div class="panel span-6">
    <h2>Session Lifecycle</h2>
    <p>Start a provider-neutral mailbox session, read through the returned handles, and close it in a finally path.</p>
    <ul class="workflow-list">{session_rows}</ul>
  </div>
</section>
"""


def _request_rows(items: list[tuple[str, dict[str, Any]]]) -> str:
    rows = []
    for index, (label, item) in enumerate(items, start=1):
        method = _text(item.get("method"), "POST")
        endpoint = _text(item.get("endpoint"))
        if not endpoint:
            continue
        rows.append(
            f'<li class="workflow-row"><span><span class="workflow-number">{index}</span>{_method_badge(method)} <strong>{escape(label)}</strong></span>'
            f'<code>{escape(endpoint)}</code></li>'
        )
    return "".join(rows)


def _provider_section(*, selection_policy: dict[str, Any], defaults: dict[str, Any]) -> str:
    source_priority = selection_policy.get("source_priority") if isinstance(selection_policy.get("source_priority"), list) else []
    scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    explicit_pool = scopes.get("explicit_pool_claim") if isinstance(scopes.get("explicit_pool_claim"), dict) else {}
    task_temp = scopes.get("task_temp_apply") if isinstance(scopes.get("task_temp_apply"), dict) else {}
    rows = [
        ("Source priority", " -> ".join(str(item) for item in source_priority)),
        ("Runtime temp provider", _text(defaults.get("temp_mail_provider"), "default")),
        ("Pool default provider", _text(defaults.get("pool_claim_provider"), "auto")),
        ("Active provider allowlist", ", ".join(str(item) for item in (defaults.get("active_mailbox_providers") or [])) or "all providers"),
        ("Pool request field", _text(explicit_pool.get("request_field"), "provider")),
        ("Task temp request field", _text(task_temp.get("request_field"), "provider_name")),
    ]
    rendered = "".join(
        f'<li class="meta-row"><span class="label">{escape(label)}</span><code>{escape(value)}</code></li>'
        for label, value in rows
    )
    return f"""
<section class="grid">
  <div class="panel span-12">
    <h2>Provider Routing</h2>
    <p>External callers can stay provider-neutral, or override source selection with documented request fields and deployment keys.</p>
    <ul class="meta-list">{rendered}</ul>
  </div>
</section>
"""


def _endpoint_catalog(path_groups: list[dict[str, Any]]) -> str:
    sections = []
    for group in path_groups:
        rows = []
        for op in group["operations"]:
            rows.append(
                "<tr>"
                f'<td data-label="Method">{_method_badge(op["method"])}</td>'
                f'<td data-label="Path" class="endpoint-path"><code>{escape(op["path"])}</code></td>'
                f'<td data-label="Summary"><div class="summary">{escape(op["summary"])}</div><div class="operation-id">{escape(op["operation_id"])}</div></td>'
                f'<td data-label="Schemas"><div class="schema-stack">{_schema_lines(op)}</div></td>'
                "</tr>"
            )
        sections.append(
            f"""
<div class="panel span-12">
  <div class="section-title"><h2>{escape(group['label'])}</h2><span class="section-count">{len(group['operations'])} endpoints</span></div>
  <table class="endpoint-table">
    <thead><tr><th style="width:76px">Method</th><th>Path</th><th>Summary</th><th>Schemas</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
"""
        )
    return f"""
<section class="grid endpoint-catalog" aria-label="Endpoint Catalog">
  <div class="panel span-12">
    <div class="section-title"><h2>Endpoint Catalog</h2><span class="section-count">{_operation_count(path_groups)} operations</span></div>
    <p>Canonical `/api/v1/external/*` paths are listed here. Legacy `/api/external/*` routes were removed; clients must use v1 paths only.</p>
  </div>
  {''.join(sections)}
</section>
"""


def _schema_lines(op: dict[str, str]) -> str:
    lines = []
    if op.get("request_schema"):
        lines.append(f'<span>request: <code>{escape(op["request_schema"])}</code></span>')
    if op.get("response_schema"):
        lines.append(f'<span>response: <code>{escape(op["response_schema"])}</code></span>')
    return "".join(lines) or '<span>contract metadata</span>'


def _group_operations(paths: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for path, methods in sorted(paths.items()):
        if not isinstance(methods, dict):
            continue
        label = _group_label(path)
        group = groups.setdefault(label, {"label": label, "operations": []})
        for method, operation in sorted(methods.items()):
            if not isinstance(operation, dict):
                continue
            group["operations"].append(
                {
                    "method": method.upper(),
                    "path": str(path),
                    "summary": _text(operation.get("summary"), str(path)),
                    "operation_id": _text(operation.get("operationId"), ""),
                    "request_schema": _schema_name(_request_schema(operation)),
                    "response_schema": _schema_name(_response_schema(operation)),
                }
            )
    order = ["Discovery", "Mailbox Sessions", "Mailbox Reads", "Pool", "Task Temp Mail", "Other"]
    return sorted(groups.values(), key=lambda item: order.index(item["label"]) if item["label"] in order else len(order))


def _group_label(path: str) -> str:
    if "/mailbox-sessions/" in path:
        return "Mailbox Sessions"
    if "/pool/" in path:
        return "Pool"
    if "/temp-emails/" in path:
        return "Task Temp Mail"
    if any(marker in path for marker in ("/messages", "/verification-", "/wait-message", "/probe/", "/account-status")):
        return "Mailbox Reads"
    if any(marker in path for marker in ("/health", "/capabilities", "/docs", "/openapi", "/providers", "/mailboxes")):
        return "Discovery"
    return "Other"


def _request_schema(operation: dict[str, Any]) -> dict[str, Any]:
    body = operation.get("requestBody") if isinstance(operation.get("requestBody"), dict) else {}
    content = body.get("content") if isinstance(body.get("content"), dict) else {}
    json_content = content.get("application/json") if isinstance(content.get("application/json"), dict) else {}
    schema = json_content.get("schema") if isinstance(json_content.get("schema"), dict) else {}
    return schema


def _response_schema(operation: dict[str, Any]) -> dict[str, Any]:
    responses = operation.get("responses") if isinstance(operation.get("responses"), dict) else {}
    ok = responses.get("200") if isinstance(responses.get("200"), dict) else {}
    content = ok.get("content") if isinstance(ok.get("content"), dict) else {}
    json_content = content.get("application/json") if isinstance(content.get("application/json"), dict) else {}
    schema = json_content.get("schema") if isinstance(json_content.get("schema"), dict) else {}
    return schema


def _schema_name(schema: dict[str, Any]) -> str:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref:
        return ref.rsplit("/", 1)[-1]
    all_of = schema.get("allOf") if isinstance(schema.get("allOf"), list) else []
    names = [_schema_name(item) for item in all_of if isinstance(item, dict)]
    names = [item for item in names if item]
    return " + ".join(names)


def _footer() -> str:
    return """
<p class="footer">Generated from the live OpenAPI contract. Use the JSON contract for code generation and this page for human inspection.</p>
"""
