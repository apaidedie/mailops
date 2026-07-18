from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mailops.services.temp_mail_plugin_cli import validate_provider_contract
from mailops.services.temp_mail_plugin_manager import PluginManagerError, scaffold_provider_plugin
from scripts.project_readiness_check import SECRET_PATTERNS


PROVIDER_DEV_KIT_NAME = "provider-dev-kit"


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def scan_provider_file_for_secrets(file_path: str | Path) -> dict[str, Any]:
    target = Path(file_path).expanduser().resolve()
    hits: list[dict[str, Any]] = []
    if not target.is_file():
        return {"ok": False, "hits": [{"file": str(target), "line": 0, "pattern": "file_missing"}]}

    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = target.read_text(encoding="utf-8-sig")

    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append({"file": str(target), "line": line_number, "pattern": pattern_name})
    return {"ok": not hits, "hits": hits}


def _next_steps(provider_key: str, file_path: str) -> list[str]:
    return [
        f"Edit {file_path} and replace the provider HTTP adapter with upstream API calls.",
        f"python scripts/provider_dev_kit.py validate {provider_key} --file {file_path} --format json",
        f"python web_outlook_app.py validate-provider {provider_key} --file {file_path}",
        "Reload plugins, inspect GET /api/plugins/<name>/contract, then enable routing only after status=valid.",
    ]


def _error_report(command: str, code: str, message: str, **data: object) -> dict[str, Any]:
    report: dict[str, Any] = {
        "success": False,
        "tool": PROVIDER_DEV_KIT_NAME,
        "command": command,
        "code": code,
        "message": message,
    }
    if data:
        report["data"] = data
    return report


def build_scaffold_report(provider_key: str, *, output_dir: str | None = None, force: bool = False) -> dict[str, Any]:
    result = scaffold_provider_plugin(provider_key, output_dir=output_dir, force=force)
    file_path = str(result["file_path"])
    secret_scan = scan_provider_file_for_secrets(file_path)
    return {
        "success": bool(secret_scan.get("ok")),
        "tool": PROVIDER_DEV_KIT_NAME,
        "command": "scaffold",
        "provider": result["plugin_name"],
        "file_path": file_path,
        "class_name": result["class_name"],
        "provider_label": result["provider_label"],
        "overwritten": bool(result.get("overwritten")),
        "secret_scan": secret_scan,
        "next_steps": _next_steps(str(result["plugin_name"]), file_path),
    }


def build_validation_report(provider_key: str, *, file_path: str, probe_options: bool = False) -> dict[str, Any]:
    target = str(Path(file_path).expanduser().resolve())
    contract_report = validate_provider_contract(provider_key, target, probe_options=probe_options)
    validation = contract_report.get("contract_validation") if isinstance(contract_report, dict) else {}
    secret_scan = scan_provider_file_for_secrets(target)
    contract_valid = isinstance(validation, dict) and validation.get("status") == "valid"
    return {
        "success": bool(contract_valid and secret_scan.get("ok")),
        "tool": PROVIDER_DEV_KIT_NAME,
        "command": "validate",
        "provider": str(provider_key or "").strip(),
        "file_path": target,
        "source": contract_report.get("source"),
        "probe_options": bool(probe_options),
        "contract_validation": validation,
        "secret_scan": secret_scan,
        "next_steps": _next_steps(str(provider_key or "").strip(), target),
    }


def _print_text(report: dict[str, Any]) -> None:
    status = "OK" if report.get("success") else "FAIL"
    print(f"{status} {report.get('tool', PROVIDER_DEV_KIT_NAME)} {report.get('command', '')}: {report.get('provider', '')}")
    if report.get("file_path"):
        print(f"file: {report['file_path']}")
    validation = report.get("contract_validation") if isinstance(report.get("contract_validation"), dict) else {}
    if validation:
        issue_codes = [str(item.get("code") or "") for item in validation.get("issues", []) if isinstance(item, dict)]
        print(f"contract: {validation.get('status')} errors={validation.get('summary', {}).get('errors', 0)}")
        if issue_codes:
            print("issues: " + ", ".join(code for code in issue_codes if code))
    secret_scan = report.get("secret_scan") if isinstance(report.get("secret_scan"), dict) else {}
    if secret_scan:
        print(f"secret_scan: {'ok' if secret_scan.get('ok') else 'failed'} hits={len(secret_scan.get('hits') or [])}")
    next_steps = report.get("next_steps") if isinstance(report.get("next_steps"), list) else []
    if next_steps:
        print("next_steps:")
        for item in next_steps:
            print(f"- {item}")
    if report.get("code"):
        print(f"error: {report.get('code')} {report.get('message', '')}")


def _emit(report: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(_json_dump(report))
    else:
        _print_text(report)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline provider-dev-kit for scaffolding and validating temp-mail provider plugins."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = sub.add_parser("scaffold", help="Generate a provider plugin skeleton from the safe template.")
    scaffold_parser.add_argument("provider_key")
    scaffold_parser.add_argument("--output-dir", default=None)
    scaffold_parser.add_argument("--force", action="store_true")
    scaffold_parser.add_argument("--format", choices=("text", "json"), default="text")

    validate_parser = sub.add_parser("validate", help="Validate a local provider plugin contract and secret safety.")
    validate_parser.add_argument("provider_key")
    validate_parser.add_argument("--file", dest="file_path", required=True)
    validate_parser.add_argument("--probe-options", action="store_true", help="Explicitly run the provider get_options() probe.")
    validate_parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "scaffold":
            report = build_scaffold_report(args.provider_key, output_dir=args.output_dir, force=args.force)
            _emit(report, args.format)
            return 0 if report.get("success") else 2
        if args.command == "validate":
            report = build_validation_report(args.provider_key, file_path=args.file_path, probe_options=args.probe_options)
            _emit(report, args.format)
            return 0 if report.get("success") else 2
    except PluginManagerError as exc:
        data = exc.data if isinstance(exc.data, dict) else {}
        report = _error_report(args.command or "unknown", exc.code, exc.message, **data)
        _emit(report, getattr(args, "format", "text"))
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
