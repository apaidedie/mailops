"""Helpers for reading the frontend app JS bundle (split core + feature packages)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_FUNC_START = re.compile(r"^( *)(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")


def _package_order(rel_dir: str) -> tuple[str, ...]:
    order_path = ROOT / rel_dir / "_load_order.json"
    names = json.loads(order_path.read_text(encoding="utf-8"))
    return tuple(f"{rel_dir}/{name}" for name in names)


def _extract_top_level_functions(text: str) -> dict[str, str]:
    """Map top-level function name -> source slice (same indent level as first function)."""
    lines = text.splitlines(keepends=True)
    base_indent: int | None = None
    starts: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = _FUNC_START.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        if base_indent is None:
            base_indent = indent
        if indent != base_indent:
            continue
        starts.append((m.group(2), i))
    out: dict[str, str] = {}
    for idx, (name, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        out[name] = "".join(lines[start:end])
    return out


def load_feature_package_js(rel_dir: str) -> str:
    """Concatenate a package preserving original top-level function order."""
    pkg = ROOT / rel_dir
    globals_path = pkg / "globals.js"
    if not globals_path.is_file():
        raise FileNotFoundError(f"{rel_dir}/globals.js")

    parts: list[str] = [globals_path.read_text(encoding="utf-8")]

    order_path = pkg / "_function_order.json"
    if order_path.is_file():
        function_order: list[str] = json.loads(order_path.read_text(encoding="utf-8"))
        bodies: dict[str, str] = {}
        for rel in _package_order(rel_dir):
            name = Path(rel).name
            if name in {"globals.js", "_load_order.json", "_function_order.json"}:
                continue
            if not name.endswith(".js"):
                continue
            bodies.update(_extract_top_level_functions((ROOT / rel).read_text(encoding="utf-8")))
        missing = [n for n in function_order if n not in bodies]
        if missing:
            raise KeyError(f"{rel_dir}: missing functions in package modules: {missing[:10]}")
        for name in function_order:
            parts.append(bodies[name])
        return "".join(parts)

    for rel in _package_order(rel_dir):
        if rel.endswith("globals.js"):
            continue
        path = ROOT / rel
        if path.is_file() and path.suffix == ".js":
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def load_mailboxes_js() -> str:
    return load_feature_package_js("static/js/features/mailboxes")


def load_settings_js() -> str:
    return load_feature_package_js("static/js/core/settings")


# Must match templates/partials/scripts.html load order for core modules.
CORE_JS_RELATIVE_PATHS: tuple[str, ...] = (
    *_package_order("static/js/core/state"),
    "static/js/core/poll-ui.js",
    "static/js/core/nav.js",
    "static/js/core/http.js",
    "static/js/core/utils.js",
    *_package_order("static/js/core/settings"),
    *_package_order("static/js/core/admin"),
)


def load_frontend_app_js() -> str:
    """Return concatenated core app JS with packages in original function order."""
    parts: list[str] = [
        load_feature_package_js("static/js/core/state"),
        (ROOT / "static/js/core/poll-ui.js").read_text(encoding="utf-8"),
        (ROOT / "static/js/core/nav.js").read_text(encoding="utf-8"),
        (ROOT / "static/js/core/http.js").read_text(encoding="utf-8"),
        (ROOT / "static/js/core/utils.js").read_text(encoding="utf-8"),
        load_feature_package_js("static/js/core/settings"),
        load_feature_package_js("static/js/core/admin"),
    ]
    return "\n".join(parts)


def frontend_app_js_paths() -> tuple[Path, ...]:
    return tuple(ROOT / rel for rel in CORE_JS_RELATIVE_PATHS)
