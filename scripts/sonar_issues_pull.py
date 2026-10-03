#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取 SonarCloud 问题清单并归类（只读诊断，token 从环境变量 .env 读取）。"""

from __future__ import annotations

import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_token() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("SONAR_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("SONAR_TOKEN not found in .env")


def fetch_issues(token: str) -> list[dict]:
    issues: list[dict] = []
    page = 1
    while True:
        url = (
            "https://sonarcloud.io/api/issues/search"
            f"?componentKeys=apaidedie_mailops&resolved=false&ps=500&p={page}"
            "&s=SEVERITY&asc=false"
        )
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        batch = payload.get("issues", [])
        issues.extend(batch)
        total = int(payload.get("total", 0))
        if len(issues) >= total or not batch:
            break
        page += 1
        if page > 10:  # API 单次最多取 10 页
            break
    return issues


def main() -> None:
    token = load_token()
    issues = fetch_issues(token)
    print(f"总问题数（未解决）：{len(issues)}")
    print("按类型：", dict(Counter(i["type"] for i in issues)))
    print("按严重度：", dict(Counter(i["severity"] for i in issues)))

    by_rule = Counter(f"{i['rule']} | {i['message'][:60]}" for i in issues)
    print("\n== TOP 规则（前 25）==")
    for rule, count in by_rule.most_common(25):
        print(f"  {count:4d}  {rule}")

    print("\n== BUG 与 高严重度 CODE_SMELL 明细 ==")
    for i in issues:
        if i["type"] == "BUG" or (i["type"] == "CODE_SMELL" and i["severity"] in ("CRITICAL", "MAJOR")):
            component = i.get("component", "").replace("apaidedie_mailops:", "")
            line = i.get("line", "?")
            print(f"  [{i['severity'][:4]}] {component}:{line} | {i['message'][:100]} ({i['rule']})")

    out = ROOT / "output" / "sonar-issues.json"
    out.write_text(json.dumps(issues, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n完整清单已存：{out}")


if __name__ == "__main__":
    main()
