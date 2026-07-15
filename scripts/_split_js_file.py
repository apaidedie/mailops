#!/usr/bin/env python3
"""Split a classic browser JS file extracted from main.js (8-space top-level indent).

Top-level declarations and non-function lines go to globals.js.
Top-level functions (indent == base_indent) are grouped by map modules.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def detect_base_indent(lines: list[str]) -> int:
    for line in lines:
        m = re.match(r"^( *)(?:async\s+)?function\s+\w+", line)
        if m and not line.lstrip().startswith("//"):
            return len(m.group(1))
    return 8


def parse_top_level(lines: list[str], base_indent: int | None = None) -> tuple[list[tuple[int, int]], list[tuple[str, int, int]]]:
    if base_indent is None:
        base_indent = detect_base_indent(lines)
    func_re = re.compile(
        rf"^[ ]{{{base_indent}}}(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("
    )
    starts: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = func_re.match(line)
        if m:
            starts.append((m.group(1), i))
    funcs: list[tuple[str, int, int]] = []
    for idx, (name, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        funcs.append((name, start, end))

    covered = [False] * len(lines)
    for _, start, end in funcs:
        for j in range(start, end):
            covered[j] = True
    non_func: list[tuple[int, int]] = []
    j = 0
    while j < len(lines):
        if covered[j]:
            j += 1
            continue
        start = j
        while j < len(lines) and not covered[j]:
            j += 1
        non_func.append((start, j))
    return non_func, funcs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--delete-source", action="store_true")
    args = ap.parse_args()

    source = Path(args.source)
    outdir = Path(args.outdir)
    mapping: dict[str, list[str]] = json.loads(Path(args.map).read_text(encoding="utf-8-sig"))

    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    non_func_spans, funcs = parse_top_level(lines)
    by_name = {name: (start, end) for name, start, end in funcs}

    assigned: set[str] = set()
    for mod, names in mapping.items():
        if mod.startswith("_"):
            continue
        for n in names:
            if n not in by_name:
                raise SystemExit(f"ERROR: function {n!r} not found in {source} (have {len(by_name)} top-level)")
            assigned.add(n)
    unassigned = sorted(set(by_name) - assigned)
    if unassigned:
        raise SystemExit(f"ERROR: {len(unassigned)} unassigned: {unassigned[:20]}")

    if outdir.exists() and any(outdir.iterdir()):
        raise SystemExit(f"ERROR: outdir not empty: {outdir}")
    outdir.mkdir(parents=True, exist_ok=True)

    g_chunks = [f"// split globals from {source.name}\n"]
    for start, end in non_func_spans:
        chunk = "".join(lines[start:end])
        if chunk.strip():
            g_chunks.append(chunk if chunk.endswith("\n") else chunk + "\n")
    (outdir / "globals.js").write_text("".join(g_chunks), encoding="utf-8")
    print(f"wrote {outdir / 'globals.js'} top-level funcs={len(funcs)}")

    order = ["globals.js"]
    for mod, names in mapping.items():
        if mod.startswith("_"):
            continue
        chunks = [f"// split from {source.name} → {mod}.js\n"]
        for n in sorted(names, key=lambda x: by_name[x][0]):
            start, end = by_name[n]
            chunk = "".join(lines[start:end])
            chunks.append(chunk if chunk.endswith("\n") else chunk + "\n")
        (outdir / f"{mod}.js").write_text("".join(chunks), encoding="utf-8")
        order.append(f"{mod}.js")
        print(f"wrote {outdir / (mod + '.js')} ({len(names)} functions)")

    (outdir / "_load_order.json").write_text(json.dumps(order, indent=2) + "\n", encoding="utf-8")
    # Original top-level function appearance order (for test bundle reconstruction).
    function_order = [name for name, _, __ in funcs]
    (outdir / "_function_order.json").write_text(
        json.dumps(function_order, indent=2) + "\n", encoding="utf-8"
    )
    print("load order:", order)
    print(f"function order: {len(function_order)} names")

    if args.delete_source:
        source.unlink()
        print(f"deleted {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
