#!/usr/bin/env python3
"""Write _function_order.json for already-split packages using git monofile history."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _split_js_file import parse_top_level  # noqa: E402

TARGETS = [
    ("static/js/core/state.js", "static/js/core/state"),
    ("static/js/core/admin.js", "static/js/core/admin"),
    ("static/js/features/mailboxes.js", "static/js/features/mailboxes"),
]


def main() -> int:
    for monofile, pkg in TARGETS:
        raw = subprocess.check_output(
            ["git", "show", f"HEAD:{monofile}"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        lines = raw.splitlines(keepends=True)
        _, funcs = parse_top_level(lines)
        order = [name for name, _, __ in funcs]
        out = ROOT / pkg / "_function_order.json"
        out.write_text(json.dumps(order, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(order)} functions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
