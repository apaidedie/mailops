#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_parse():
    spec = importlib.util.spec_from_file_location("split_js", ROOT / "scripts/_split_js_file.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def classify_settings(name: str) -> str:
    n = name.lower()
    if "externalapi" in n or "external_api" in n or "starter" in n or "workflow" in n:
        return "external_api"
    if "tempmail" in n or "temp_mail" in n or "tempprovider" in n:
        return "temp_mail"
    if "provider" in n or "preflight" in n or "plugin" in n:
        return "providers"
    if "modal" in n or "settings" in n or "update" in n or "toggle" in n:
        return "modal"
    if "test" in n or "validate" in n or "sync" in n or "telegram" in n or "webhook" in n or "cron" in n:
        return "tests_actions"
    return "misc"


def classify_feature(name: str) -> str:
    n = name.lower()
    if "render" in n or "paint" in n or "format" in n:
        return "render"
    if "load" in n or "fetch" in n or "cache" in n or "invalidate" in n:
        return "data"
    if "select" in n or "batch" in n or "delete" in n or "edit" in n or "add" in n or "save" in n or "confirm" in n:
        return "actions"
    if "bind" in n or "event" in n or "click" in n or "open" in n or "close" in n or "show" in n or "hide" in n:
        return "ui"
    return "misc"


def classify_i18n(name: str) -> str:
    n = name.lower()
    if "language" in n or "setlanguage" in n or "getlanguage" in n:
        return "language"
    if "translate" in n or "attribute" in n or "apply" in n:
        return "translate"
    return "misc"


def build(source: Path, classifier):
    mod = load_parse()
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    _, funcs = mod.parse_top_level(lines)
    buckets: dict[str, list[str]] = {}
    order = {name: i for i, (name, _, __) in enumerate(funcs)}
    for name, _, __ in funcs:
        buckets.setdefault(classifier(name), []).append(name)
    for k in buckets:
        buckets[k] = sorted(buckets[k], key=lambda n: order[n])
    return buckets


def main():
    targets = [
        (ROOT / "static/js/core/settings.js", classify_settings, "settings_js.json"),
        (ROOT / "static/js/i18n.js", classify_i18n, "i18n_js.json"),
        (ROOT / "static/js/features/emails.js", classify_feature, "emails_js.json"),
        (ROOT / "static/js/features/groups.js", classify_feature, "groups_js.json"),
        (ROOT / "static/js/features/accounts.js", classify_feature, "accounts_js.json"),
    ]
    outdir = ROOT / "scripts/_split_maps"
    for src, clf, name in targets:
        m = build(src, clf)
        (outdir / name).write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        print(src.name, {k: len(v) for k, v in m.items()}, "total", sum(len(v) for v in m.values()))


if __name__ == "__main__":
    main()
