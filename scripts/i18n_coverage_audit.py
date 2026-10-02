#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i18n 覆盖率审计（只读诊断）。

统计前端中英翻译缺口：
1. JS 中 translate*() 显式调用的中文字面量是否都在 i18n.js exactMap 中；
2. 模板可见中文文本节点是否都能被 exactMap 覆盖。

用法：python scripts/i18n_coverage_audit.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "static" / "js" / "i18n.js"
CHINESE = re.compile(r"[\u4e00-\u9fff]")

# 已知非翻译文本：
# - 「管」是管理员头像首字（人名缩写位），不做语言翻译；
# - 其余豁免项在此登记，需注明原因。
ALLOWED_MISSING = {
    "管",
}


def load_exact_map_keys() -> set[str]:
    keys: set[str] = set()
    for line in I18N.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*'((?:[^'\\]|\\.)*)'\s*:\s*'", line)
        if m:
            keys.add(m.group(1).replace("\\'", "'"))
    return keys


def audit() -> int:
    keys = load_exact_map_keys()
    missing_total = 0

    # 1) JS 显式翻译调用
    call_pattern = re.compile(r"translate(?:AppTextLocal|UnifiedText|AppText)\(\s*'([^']*)'")
    calls: set[str] = set()
    for path in sorted((ROOT / "static" / "js").rglob("*.js")):
        parts = path.parts
        if "bundles" in parts or path.name == "i18n.js":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for raw in call_pattern.findall(text):
            s = raw.replace("\\'", "'")
            if CHINESE.search(s):
                calls.add(s)
    missing_calls = sorted(s for s in calls if s not in keys)
    print(f"[JS] 显式翻译调用 {len(calls)} 个中文串，缺 {len(missing_calls)} 个")
    for s in missing_calls[:200]:
        print("  -", s[:72])
    missing_total += len(missing_calls)

    # 2) 模板可见文本节点（先剥离内联 <script>/<style>，避免把 JS 源码当 UI 文本）
    tpl_texts: set[str] = set()
    node_pattern = re.compile(r">([^<>]*)<")
    script_pattern = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.S | re.I)
    for name in ("templates/index.html", "templates/login.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        text = script_pattern.sub("", text)
        for raw in node_pattern.findall(text):
            s = " ".join(raw.split())
            if CHINESE.search(s) and "{{" not in s:
                tpl_texts.add(s)
    missing_tpl = sorted(s for s in tpl_texts if s not in keys and s not in ALLOWED_MISSING)
    print(f"[模板] 可见中文文本 {len(tpl_texts)} 个，缺 {len(missing_tpl)} 个")
    for s in missing_tpl[:200]:
        print("  -", s[:72])
    missing_total += len(missing_tpl)

    print(f"合计缺口：{missing_total}")
    return 0 if missing_total == 0 else 1


if __name__ == "__main__":
    sys.exit(audit())
