#!/usr/bin/env python3
"""Generate responsibility-ish function maps for large classic JS files."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_parse():
    spec = importlib.util.spec_from_file_location("split_js", ROOT / "scripts/_split_js_file.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def classify_state(name: str) -> str:
    n = name.lower()
    rules = [
        ("layout", ("layout",)),
        ("i18n", ("translate", "getuilanguage", "formatgroup", "language")),
        ("provider_catalog", ("provider", "preflight", "mailboxprovider", "tempprovider", "plugin")),
        ("temp_settings", ("tempmail", "temp_mail", "tempmailsettings")),
        ("external_api_ui", ("externalapi", "external_api", "openapi", "starter", "workflow")),
        ("readiness", ("readiness", "operational")),
        ("surface", ("surface", "paint", "isactive", "shouldpaint", "pagesurface")),
        ("bootstrap", ("bootstrap", "initapp", "domcontent", "startup")),
        ("polling", ("poll", "polling", "autopoll")),
        ("accounts_state", ("account", "group", "tag", "selected")),
        ("utils_local", ("format", "parse", "normalize", "is", "get", "set", "build", "render", "apply", "load", "save", "clear", "reset", "update", "show", "hide", "toggle", "copy", "debounce")),
    ]
    for bucket, keys in rules:
        if any(k in n for k in keys):
            return bucket
    return "misc"


def classify_admin(name: str) -> str:
    n = name.lower()
    if "invalidtoken" in n or "invalid_token" in n:
        return "invalid_token"
    if "refresh" in n or "failed" in n and "log" in n:
        return "refresh"
    if "audit" in n:
        return "audit"
    if "version" in n or "update" in n or "restart" in n or "watchtower" in n:
        return "version_update"
    if "docker" in n or "deploy" in n:
        return "deploy"
    if "system" in n or "health" in n or "diagnostic" in n:
        return "system"
    return "misc"


def classify_mailboxes(name: str) -> str:
    n = name.lower()
    if "quickview" in n:
        return "quickview"
    if "facet" in n or "filter" in n or "kind" in n or "status" in n or "definition" in n:
        return "filters"
    if "render" in n or "row" in n or "table" in n or "list" in n:
        return "render"
    if "page" in n or "search" in n or "load" in n or "fetch" in n or "request" in n:
        return "data"
    if "bind" in n or "open" in n or "copy" in n or "action" in n or "click" in n:
        return "actions"
    if "workspace" in n or "view" in n or "unified" in n:
        return "workspace"
    return "misc"


def build_map(source: Path, classifier) -> dict[str, list[str]]:
    mod = load_parse()
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    _, funcs = mod.parse_top_level(lines)
    buckets: dict[str, list[str]] = {}
    for name, _, __ in funcs:
        buckets.setdefault(classifier(name), []).append(name)
    # stable order by first appearance
    order_index = {name: i for i, (name, _, __) in enumerate(funcs)}
    for k in buckets:
        buckets[k] = sorted(buckets[k], key=lambda n: order_index[n])
    return buckets


def main() -> None:
    targets = [
        (ROOT / "static/js/core/state.js", classify_state, ROOT / "scripts/_split_maps/state_js.json"),
        (ROOT / "static/js/core/admin.js", classify_admin, ROOT / "scripts/_split_maps/admin_js.json"),
        (ROOT / "static/js/features/mailboxes.js", classify_mailboxes, ROOT / "scripts/_split_maps/mailboxes_js.json"),
    ]
    for src, clf, out in targets:
        m = build_map(src, clf)
        out.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        sizes = {k: len(v) for k, v in m.items()}
        print(src.name, sizes, "total", sum(sizes.values()))


if __name__ == "__main__":
    main()
