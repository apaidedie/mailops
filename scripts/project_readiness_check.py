from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"
LEGACY_EXTERNAL_PREFIX = "/api/external"
CANONICAL = {
    "capabilities": f"{CANONICAL_EXTERNAL_PREFIX}/capabilities",
    "integration_bundle": f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle",
    "providers": f"{CANONICAL_EXTERNAL_PREFIX}/providers",
    "mailboxes": f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes",
    "openapi": f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json",
    "session_start": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start",
    "session_read": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read",
    "session_close": f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close",
    "pool_claim": f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-random",
    "temp_apply": f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
}

REQUIRED_ASSETS = (
    "README.md",
    "README.en.md",
    "docs/project-launchpad.md",
    "docs/runtime-readiness.md",
    "docs/external-integration-quickstart.md",
    "docs/provider-onboarding.md",
    ".env.example",
    ".runtime/providers.example.json",
    ".runtime/providers.example.toml",
    "examples/external_api_python_client.py",
    "examples/external_api_javascript_client.js",
    "examples/temp_mail_provider_plugin_template.py",
    "scripts/provider_dev_kit.py",
    "scripts/seed_demo_workspace.py",
    "scripts/external_api_smoke.py",
    "tests/test_external_api_smoke_script.py",
    "tests/test_external_api_python_client.py",
    "tests/external_api_javascript_client.test.js",
    "tests/test_temp_mail_provider_contract_validation.py",
    "tests/test_temp_mail_provider_plugin_template.py",
)

SECRET_SCAN_PATHS = (
    "README.md",
    "README.en.md",
    "docs/project-launchpad.md",
    "docs/runtime-readiness.md",
    "docs/external-integration-quickstart.md",
    "docs/provider-onboarding.md",
    ".env.example",
    ".runtime/providers.example.json",
    ".runtime/providers.example.toml",
    "examples/external_api_python_client.py",
    "examples/external_api_javascript_client.js",
    "examples/temp_mail_provider_plugin_template.py",
    "scripts/provider_dev_kit.py",
    "scripts/seed_demo_workspace.py",
    "scripts/external_api_smoke.py",
    "scripts/project_readiness_check.py",
)

REQUIRED_ENV_KEYS = (
    "LOG_FORMAT",
    "LOG_LEVEL",
    "TEMP_MAIL_PROVIDER",
    "EXTERNAL_POOL_DEFAULT_PROVIDER",
    "ACTIVE_MAILBOX_PROVIDERS",
    "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE",
    "EXTERNAL_API_CORS_ORIGINS",
    "EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION",
    "MAILTM_API_BASE",
    "DUCKMAIL_API_BASE",
    "DUCKMAIL_BEARER_TOKEN",
    "TEMPMAIL_LOL_API_KEY",
    "TEMP_MAIL_LOL_API_KEY",
    "EMAILNATOR_API_KEY",
    "EMAILNATOR_EMAIL_TYPES",
    "CF_WORKER_BASE_URL",
    "CF_WORKER_ADMIN_KEY",
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("duckmail_bearer_token", re.compile(r"dk_[0-9a-fA-F]{40,}")),
    ("bearer_header", re.compile(r"Bearer\s+(?!<|your-|token\b|TOKEN\b|\$\{)[A-Za-z0-9_.-]{20,}", re.I)),
    ("x_api_key_header", re.compile(r"X-API-Key:\s+(?!<your-api-key>|your-api-key|\$\{)[A-Za-z0-9_.-]{20,}", re.I)),
    ("openai_style_key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
)


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    name: str
    message: str
    details: dict[str, Any] | None = None


def _check(ok: bool, name: str, message: str, details: dict[str, Any] | None = None) -> CheckResult:
    return CheckResult(bool(ok), name, message, details or None)


def _read(root: Path, relative: str) -> str | None:
    path = root / relative
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def _missing(text: str | None, required: tuple[str, ...]) -> list[str]:
    if text is None:
        return list(required)
    return [item for item in required if item not in text]


def _required_assets(root: Path) -> CheckResult:
    missing = [item for item in REQUIRED_ASSETS if not (root / item).is_file()]
    return _check(
        not missing,
        "assets.required",
        "required integration docs, examples, scripts, and tests are present",
        {"missing": missing} if missing else None,
    )


def _readme_links(root: Path) -> list[CheckResult]:
    required = (
        "./docs/project-launchpad.md",
        "./docs/external-integration-quickstart.md",
        "./docs/provider-onboarding.md",
        "./examples/external_api_python_client.py",
        CANONICAL_EXTERNAL_PREFIX,
        "integration_manifest",
        "X-API-Key",
    )
    zh_missing = _missing(_read(root, "README.md"), required)
    en_missing = _missing(_read(root, "README.en.md"), required)
    return [
        _check(
            not zh_missing,
            "readme.zh.integration_links",
            "Chinese README links the external integration surface",
            {"missing": zh_missing},
        ),
        _check(
            not en_missing,
            "readme.en.integration_links",
            "English README links the external integration surface",
            {"missing": en_missing},
        ),
    ]


def _project_launchpad(root: Path) -> CheckResult:
    required = (
        "unified mailbox workspace",
        "Outlook / Microsoft Graph",
        "Generic IMAP",
        "Mailbox pool",
        "mail_tm",
        "duckmail",
        "tempmail_lol",
        "emailnator",
        "cloudflare_temp_mail",
        "legacy_bridge",
        "plugin contract",
        "TEMP_MAIL_PROVIDER",
        "EXTERNAL_POOL_DEFAULT_PROVIDER",
        "ACTIVE_MAILBOX_PROVIDERS",
        "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE",
        "python scripts/project_readiness_check.py",
        "python scripts/seed_demo_workspace.py --reset",
        "output/demo/outlook-email-plus-demo.db",
        "scripts/external_api_smoke.py",
        "X-API-Key: <your-api-key>",
        CANONICAL["integration_bundle"],
        CANONICAL["capabilities"],
        CANONICAL["providers"],
        CANONICAL["mailboxes"],
        CANONICAL_EXTERNAL_PREFIX + "/docs",
        CANONICAL["openapi"],
        CANONICAL["session_start"],
        CANONICAL["session_read"],
        CANONICAL["session_close"],
        "examples/external_api_python_client.py",
        "examples/external_api_javascript_client.js",
        "validate-provider",
        "contract_validation.status=valid",
        "External Integration Quickstart",
        "Provider Onboarding Guide",
    )
    missing = _missing(_read(root, "docs/project-launchpad.md"), required)
    return _check(
        not missing,
        "docs.project_launchpad.contract",
        "project launchpad summarizes product shape, mailbox sources, integration paths, and readiness gates",
        {"missing": missing},
    )


def _runtime_logging_docs(root: Path) -> CheckResult:
    required = (
        "LOG_FORMAT",
        "LOG_LEVEL",
        "PERF_LOGGING",
        "line-delimited JSON",
        "trace_id",
        "ELK",
        "Loki",
    )
    missing = _missing(_read(root, "docs/runtime-readiness.md"), required)
    return _check(
        not missing,
        "docs.runtime_logging.contract",
        "runtime handoff documents text and structured JSON logging controls",
        {"missing": missing} if missing else None,
    )


def _external_quickstart(root: Path) -> CheckResult:
    required = (
        "scripts/project_readiness_check.py",
        "scripts/external_api_smoke.py",
        "--format json",
        "integration-bundle",
        CANONICAL["integration_bundle"],
        "integration_manifest",
        "X-API-Key: <your-api-key>",
        CANONICAL["capabilities"],
        CANONICAL["openapi"],
        CANONICAL["session_start"],
        CANONICAL["session_read"],
        CANONICAL["session_close"],
        "provider_name",
        "source_strategy",
        CANONICAL_EXTERNAL_PREFIX,
    )
    missing = _missing(_read(root, "docs/external-integration-quickstart.md"), required)
    return _check(
        not missing,
        "docs.external_quickstart.contract",
        "external quickstart documents local gate, live smoke, canonical endpoints, and placeholder auth",
        {"missing": missing},
    )


def _external_api_cors_docs(root: Path) -> CheckResult:
    required = (
        "EXTERNAL_API_CORS_ORIGINS",
        "EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION",
        "supports_credentials=false",
        "/api/v1/external/*",
        "X-Trace-Id",
    )
    texts = "\n".join(
        text
        for text in (
            _read(root, ".env.example"),
            _read(root, "docs/runtime-readiness.md"),
            _read(root, "docs/external-integration-quickstart.md"),
        )
        if text is not None
    )
    missing = _missing(texts, required)
    return _check(
        not missing,
        "docs.external_api_cors.contract",
        "external API browser CORS policy is explicit, scoped, and documented",
        {"missing": missing} if missing else None,
    )


def _provider_onboarding(root: Path) -> CheckResult:
    required = (
        "scripts/project_readiness_check.py",
        CANONICAL["capabilities"],
        CANONICAL["providers"],
        CANONICAL["mailboxes"],
        CANONICAL["pool_claim"],
        CANONICAL["temp_apply"],
        CANONICAL["session_start"],
        CANONICAL["openapi"],
        "integration_manifest",
        "provider_name",
        "provider",
        "contract_validation",
        "provider-dev-kit",
        "scripts/provider_dev_kit.py",
        "--format json",
        "--probe-options",
        "secret_scan",
        "offline",
        ".runtime/providers.example.json",
        ".runtime/providers.example.toml",
        "validate-provider",
        "DUCKMAIL_BEARER_TOKEN",
    )
    missing = _missing(_read(root, "docs/provider-onboarding.md"), required)
    return _check(
        not missing,
        "docs.provider_onboarding.contract",
        "provider onboarding guide documents canonical provider selection and extension readiness",
        {"missing": missing},
    )


def _env_example(root: Path) -> CheckResult:
    missing = _missing(_read(root, ".env.example"), REQUIRED_ENV_KEYS)
    return _check(
        not missing,
        "config.env_example.provider_keys",
        ".env.example lists provider selection and external provider configuration keys",
        {"missing": missing},
    )


def _provider_json(root: Path) -> CheckResult:
    text = _read(root, ".runtime/providers.example.json")
    if text is None:
        return _check(False, "config.providers_json", "provider JSON example exists and parses", {"missing": True})
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return _check(False, "config.providers_json", "provider JSON example exists and parses", {"error": str(exc)})
    providers = parsed.get("providers") if isinstance(parsed, dict) else None
    missing = [
        key
        for key in ("temp_mail_provider", "pool_default_provider", "active_mailbox_providers")
        if not isinstance(providers, dict) or key not in providers
    ]
    return _check(
        not missing, "config.providers_json", "provider JSON example exposes provider selection fields", {"missing": missing}
    )


def _provider_toml(root: Path) -> CheckResult:
    text = _read(root, ".runtime/providers.example.toml")
    if text is None:
        return _check(False, "config.providers_toml", "provider TOML example exists and parses", {"missing": True})
    required = ("[providers]", "temp_mail_provider", "pool_default_provider", "active_mailbox_providers")
    missing = _missing(text, required)
    if not missing and tomllib is not None:
        try:
            parsed = tomllib.loads(text)
        except Exception as exc:  # pragma: no cover
            return _check(False, "config.providers_toml", "provider TOML example exists and parses", {"error": str(exc)})
        providers = parsed.get("providers") if isinstance(parsed, dict) else None
        missing = [key for key in required[1:] if not isinstance(providers, dict) or key not in providers]
    return _check(
        not missing, "config.providers_toml", "provider TOML example exposes provider selection fields", {"missing": missing}
    )


def _starter_clients(root: Path) -> list[CheckResult]:
    python_required = (
        CANONICAL_EXTERNAL_PREFIX,
        "/integration-bundle",
        "mailbox-sessions/start",
        "mailbox-sessions/read",
        "mailbox-sessions/close",
        "OUTLOOK_EMAIL_PLUS_API_KEY",
        "X-API-Key",
        "integration-bundle",
        "provider_name",
    )
    js_required = python_required
    py_missing = _missing(_read(root, "examples/external_api_python_client.py"), python_required)
    js_missing = _missing(_read(root, "examples/external_api_javascript_client.js"), js_required)
    return [
        _check(
            not py_missing,
            "examples.python_client",
            "Python starter client uses canonical discovery and session workflow",
            {"missing": py_missing},
        ),
        _check(
            not js_missing,
            "examples.javascript_client",
            "JavaScript starter client uses canonical discovery and session workflow",
            {"missing": js_missing},
        ),
    ]


def _smoke_checker(root: Path) -> CheckResult:
    required = (
        "--format",
        "text",
        "json",
        f'CANONICAL_EXTERNAL_PREFIX = "{CANONICAL_EXTERNAL_PREFIX}"',
        "run_smoke",
        "build_report",
        "SECRET_PATTERNS",
        "/health",
        "/capabilities",
        "/integration-bundle",
        "/providers",
        "/mailboxes",
        "/openapi.json",
    )
    missing = _missing(_read(root, "scripts/external_api_smoke.py"), required)
    return _check(
        not missing,
        "scripts.external_api_smoke",
        "live external API smoke checker remains available with canonical read-only discovery checks",
        {"missing": missing},
    )


def _demo_seed_script(root: Path) -> CheckResult:
    required = (
        "DEFAULT_DB_PATH",
        "output",
        "demo",
        "outlook-email-plus-demo.db",
        "--dry-run",
        "--reset",
        "--format",
        "seed_demo_workspace",
        "init_db",
        "SCHEDULER_AUTOSTART",
        "DATABASE_PATH",
        "web_outlook_app.py",
    )
    missing = _missing(_read(root, "scripts/seed_demo_workspace.py"), required)
    return _check(
        not missing,
        "scripts.seed_demo_workspace",
        "local demo workspace seed script remains available, isolated, and operator-friendly",
        {"missing": missing} if missing else None,
    )


def _dependency_security_automation(root: Path) -> CheckResult:
    dependabot_required = (
        "version: 2",
        'package-ecosystem: "pip"',
        'package-ecosystem: "github-actions"',
        'interval: "weekly"',
    )
    workflow_required = (
        "name: Dependency Security",
        "permissions:",
        "contents: read",
        "schedule:",
        "workflow_dispatch:",
        "pip-audit==2.10.1",
        "pip-audit -r requirements.txt",
        "--format json",
        "--output pip-audit-report.json",
        "actions/upload-artifact@v4",
        "if: always()",
        "steps.audit.outputs.exit_code",
    )
    dependabot_missing = _missing(_read(root, ".github/dependabot.yml"), dependabot_required)
    workflow_missing = _missing(_read(root, ".github/workflows/dependency-security.yml"), workflow_required)
    ok = not dependabot_missing and not workflow_missing
    return _check(
        ok,
        "security.dependency_automation",
        "Dependabot and the pinned Python dependency audit workflow remain wired",
        (
            {
                "dependabot_missing": dependabot_missing,
                "workflow_missing": workflow_missing,
            }
            if not ok
            else None
        ),
    )


def _provider_dev_kit(root: Path) -> CheckResult:
    required = (
        "PROVIDER_DEV_KIT_NAME",
        "provider-dev-kit",
        "build_scaffold_report",
        "build_validation_report",
        "scan_provider_file_for_secrets",
        "SECRET_PATTERNS",
        "scaffold_provider_plugin",
        "validate_provider_contract",
        "--format",
        "json",
        "text",
        "--probe-options",
        "secret_scan",
        "contract_validation",
    )
    missing = _missing(_read(root, "scripts/provider_dev_kit.py"), required)
    return _check(
        not missing,
        "scripts.provider_dev_kit",
        "provider developer kit remains available with scaffold, offline validation, JSON output, and secret scanning",
        {"missing": missing} if missing else None,
    )


def scan_secret_values(root: Path, paths: tuple[str, ...] = SECRET_SCAN_PATHS) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for relative in paths:
        text = _read(root, relative)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hits.append({"file": relative, "line": line_number, "pattern": name})
    return hits


def _secret_scan(root: Path) -> CheckResult:
    hits = scan_secret_values(root)
    return _check(
        not hits,
        "secrets.checked_in_templates",
        "checked-in integration docs, examples, scripts, and config templates do not contain obvious secret values",
        {"hits": hits} if hits else None,
    )


def run_checks(root: Path) -> list[CheckResult]:
    root = root.resolve()
    return [
        _required_assets(root),
        *_readme_links(root),
        _project_launchpad(root),
        _runtime_logging_docs(root),
        _external_quickstart(root),
        _external_api_cors_docs(root),
        _provider_onboarding(root),
        _env_example(root),
        _provider_json(root),
        _provider_toml(root),
        *_starter_clients(root),
        _provider_dev_kit(root),
        _demo_seed_script(root),
        _smoke_checker(root),
        _dependency_security_automation(root),
        _secret_scan(root),
    ]


def build_report(results: list[CheckResult]) -> dict[str, Any]:
    checks = [
        {
            "ok": result.ok,
            "name": result.name,
            "message": result.message,
            **({"details": result.details} if result.details else {}),
        }
        for result in results
    ]
    failures = [check for check in checks if not check["ok"]]
    return {
        "success": not failures,
        "total": len(checks),
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "checks": checks,
        "failures": failures,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local read-only readiness check for repository integration assets.")
    parser.add_argument("--root", default=".", help="Repository root to check. Default: current directory.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format. Default: text.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = build_report(run_checks(Path(args.root)))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        for result in report["checks"]:
            prefix = "OK" if result["ok"] else "FAIL"
            line = f"{prefix} {result['name']}: {result['message']}"
            if not result["ok"] and result.get("details"):
                line += " " + json.dumps(result["details"], ensure_ascii=False, sort_keys=True)
            print(line)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
