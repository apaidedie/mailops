from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Sequence

from mailops.services.temp_mail_plugin_manager import (
    PluginManagerError,
    check_provider_in_use,
    get_installed_plugins,
    install_plugin,
    scaffold_provider_plugin,
    uninstall_plugin,
)
from mailops.services.temp_mail_provider_contract import validate_temp_mail_provider_class
from mailops.services.temp_mail_provider_factory import get_available_providers


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _cmd_install(name: str, url: str | None) -> int:
    if url:
        print(f"[警告] 该插件来自自定义地址，未经过官方审核: {url}")
    if not _confirm(f"确认安装插件 {name} 吗？"):
        print("已取消")
        return 1

    try:
        result = install_plugin(name, url=url)
    except PluginManagerError as exc:
        print(f"[错误] {exc.code}: {exc.message}")
        return 1

    print(f"[OK] 插件 {result['plugin_name']} 已安装")
    print(f"文件路径: {result['file_path']}")

    dependencies = result.get("dependencies") or []
    if dependencies:
        print("检测到额外依赖，请手动安装：")
        for item in dependencies:
            print(f"- {item}")
    return 0


def _cmd_uninstall(name: str) -> int:
    usage = check_provider_in_use(name)
    task_count = int(usage.get("task_count", 0) or 0)
    active_count = int(usage.get("active_count", 0) or 0)
    if task_count > 0:
        print(f"[错误] 当前有 {task_count} 个进行中的任务邮箱，不能卸载 {name}")
        return 1
    if active_count > 0:
        print(f"[提示] 当前有 {active_count} 个活跃邮箱记录，卸载后仅保留历史记录")

    if not _confirm(f"确认卸载插件 {name} 吗？"):
        print("已取消")
        return 1

    try:
        result = uninstall_plugin(name)
    except PluginManagerError as exc:
        print(f"[错误] {exc.code}: {exc.message}")
        return 1

    print(f"[OK] 插件 {result['plugin_name']} 已卸载")
    return 0


def _cmd_list() -> int:
    installed_names = {str(item.get("name") or "") for item in get_installed_plugins()}
    providers = get_available_providers()
    if not providers:
        print("没有已注册的 Provider。")
        return 0

    for item in providers:
        name = str(item.get("name") or "")
        label = str(item.get("label") or name)
        version = str(item.get("version") or "")
        provider_type = "插件" if name in installed_names else "内置"
        suffix = f" ({version})" if version else ""
        print(f"[{provider_type}] {name} - {label}{suffix}")
    return 0


def _cmd_scaffold(name: str, output_dir: str | None, force: bool) -> int:
    try:
        result = scaffold_provider_plugin(name, output_dir=output_dir, force=force)
    except PluginManagerError as exc:
        print(f"[错误] {exc.code}: {exc.message}")
        return 1

    print(f"[OK] Provider 插件骨架已生成: {result['plugin_name']}")
    print(f"文件路径: {result['file_path']}")
    print(f"Provider 类: {result['class_name']}")
    print("下一步：替换 _request_json 适配器，然后运行 reload-plugins 并检查 /api/plugins/<name>/contract。")
    return 0


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _error_payload(code: str, message: str, **data: object) -> dict[str, object]:
    payload: dict[str, object] = {"success": False, "code": code, "message": message}
    if data:
        payload["data"] = data
    return payload


def _load_provider_file(provider_name: str, file_path: str) -> None:
    target = Path(file_path).expanduser().resolve()
    if not target.is_file():
        raise PluginManagerError(
            "PLUGIN_FILE_NOT_FOUND",
            f"Provider plugin file not found: {target}",
            status=404,
            data={"file_path": str(target)},
        )

    module_name = f"_plugin_validate_{provider_name}"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise PluginManagerError(
            "PLUGIN_FILE_LOAD_FAILED",
            f"Provider plugin file could not be loaded: {target}",
            status=400,
            data={"file_path": str(target)},
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise PluginManagerError(
            "PLUGIN_FILE_LOAD_FAILED",
            f"Provider plugin file failed during import: {type(exc).__name__}",
            status=400,
            data={"file_path": str(target), "error_type": type(exc).__name__},
        ) from exc


def validate_provider_contract(
    provider_name: str, file_path: str | None = None, *, probe_options: bool = True
) -> dict[str, object]:
    provider_key = str(provider_name or "").strip()
    if not provider_key:
        raise PluginManagerError("INVALID_PARAMS", "Provider name is required", status=400)

    if file_path:
        _load_provider_file(provider_key, file_path)

    from mailops.temp_mail_registry import _REGISTRY

    provider_cls = _REGISTRY.get(provider_key)
    if provider_cls is None:
        raise PluginManagerError(
            "PLUGIN_NOT_LOADED",
            f"Provider {provider_key} is not loaded. Pass --file to validate a local plugin file.",
            status=404,
            data={"provider": provider_key},
        )

    validation = validate_temp_mail_provider_class(provider_key, provider_cls, probe_options=probe_options)
    return {
        "success": bool(validation.get("status") == "valid"),
        "provider": provider_key,
        "source": "file" if file_path else "registry",
        "contract_validation": validation,
    }


def _cmd_validate_provider(name: str, file_path: str | None, probe_options: bool) -> int:
    try:
        payload = validate_provider_contract(name, file_path, probe_options=probe_options)
        print(_json_dump(payload))
        validation = payload.get("contract_validation") if isinstance(payload, dict) else {}
        return 0 if validation.get("status") == "valid" else 2
    except PluginManagerError as exc:
        data = exc.data if isinstance(exc.data, dict) else {}
        print(_json_dump(_error_payload(exc.code, exc.message, **data)))
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python web_outlook_app.py")
    sub = parser.add_subparsers(dest="command")

    install_parser = sub.add_parser("install-provider", help="安装临时邮箱 Provider 插件")
    install_parser.add_argument("name")
    install_parser.add_argument("--from", dest="url", default=None)

    uninstall_parser = sub.add_parser("uninstall-provider", help="卸载临时邮箱 Provider 插件")
    uninstall_parser.add_argument("name")

    scaffold_parser = sub.add_parser("scaffold-provider", help="从模板生成临时邮箱 Provider 插件骨架")
    scaffold_parser.add_argument("name")
    scaffold_parser.add_argument("--output-dir", default=None, help="输出目录，默认写入运行时插件目录")
    scaffold_parser.add_argument("--force", action="store_true", help="覆盖已存在的插件文件")

    validate_parser = sub.add_parser("validate-provider", help="校验临时邮箱 Provider 插件契约")
    validate_parser.add_argument("name")
    validate_parser.add_argument("--file", dest="file_path", default=None, help="要导入并校验的插件 .py 文件")
    validate_parser.add_argument(
        "--no-probe-options",
        action="store_true",
        help="只做静态结构校验，不调用 get_options() 形状探针",
    )

    sub.add_parser("list-providers", help="查看已注册 Provider")

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "install-provider":
        return _cmd_install(args.name, args.url)
    if args.command == "uninstall-provider":
        return _cmd_uninstall(args.name)
    if args.command == "scaffold-provider":
        return _cmd_scaffold(args.name, args.output_dir, args.force)
    if args.command == "validate-provider":
        return _cmd_validate_provider(args.name, args.file_path, probe_options=not args.no_probe_options)
    if args.command == "list-providers":
        return _cmd_list()

    parser.print_help()
    return 0
