#!/usr/bin/env python3
"""Mechanical monofile -> package splitter for Approach C deep split.

Usage:
  python scripts/_split_module_package.py --source mailops/db.py --package mailops/db --map scripts/_split_maps/db.json --delete-source
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path


def _slice_source(src: str, start: int, end: int | None) -> str:
    lines = src.splitlines(keepends=True)
    chunk = lines[start - 1 : None if end is None else end - 1]
    return "".join(chunk)


def _node_start_lineno(node: ast.AST) -> int:
    """First line of a definition, including decorators."""
    deco = getattr(node, "decorator_list", None) or []
    if deco:
        return min(d.lineno for d in deco if getattr(d, "lineno", None))
    return int(getattr(node, "lineno"))


def _top_level_spans(tree: ast.AST, src: str) -> list[tuple[str, int, int]]:
    total = len(src.splitlines()) + 1
    items: list[tuple[str, int, int]] = []
    body = [
        node
        for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom))
        and not (
            isinstance(node, ast.Expr)
            and isinstance(getattr(node, "value", None), ast.Constant)
        )
    ]
    for i, node in enumerate(body):
        start = _node_start_lineno(node)
        end = _node_start_lineno(body[i + 1]) if i + 1 < len(body) else total
        names: list[str] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        else:
            names = [f"_node_{getattr(node, 'lineno', start)}"]
        for name in names or [f"_node_{start}"]:
            items.append((name, start, end))
    return items


def _header_block(src: str, tree: ast.Module) -> str:
    lines = src.splitlines(keepends=True)
    cutoff = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
            continue
        cutoff = node.lineno
        break
    if cutoff is None:
        return src
    return "".join(lines[: cutoff - 1]).rstrip() + "\n\n"


def _used_names(src: str) -> set[str]:
    tree = ast.parse(src)
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            used.add(node.func.id)
    return used


def _inject_relative_imports(
    module_path: Path,
    *,
    own_symbols: set[str],
    symbol_to_module: dict[str, str],
    current_mod: str,
) -> None:
    text = module_path.read_text(encoding="utf-8")
    used = _used_names(text)
    needed: dict[str, list[str]] = {}
    for name in sorted(used):
        if name in own_symbols:
            continue
        owner = symbol_to_module.get(name)
        if owner and owner != current_mod:
            needed.setdefault(owner, []).append(name)
    if not needed:
        return
    import_block = []
    for owner in sorted(needed):
        syms = sorted(set(needed[owner]))
        import_block.append(f"from .{owner} import {', '.join(syms)}")
    # Insert after the last top-level import statement (AST-accurate for multi-line imports).
    tree = ast.parse(text)
    last_import_end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_end = max(last_import_end, int(getattr(node, "end_lineno", node.lineno)))
        else:
            break
    lines = text.splitlines(keepends=True)
    insert_at = last_import_end  # 0-based index = end_lineno (1-based) → after that line
    block = "\n" + "\n".join(import_block) + "\n"
    new_text = "".join(lines[:insert_at]) + block + "".join(lines[insert_at:])
    module_path.write_text(new_text, encoding="utf-8")
    print(f"  + relative imports in {module_path.name}: {import_block}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--package", required=True, help="Target package directory")
    ap.add_argument("--map", required=True, help="JSON map: module -> [symbol,...]")
    ap.add_argument("--delete-source", action="store_true")
    args = ap.parse_args()

    source = Path(args.source)
    package = Path(args.package)
    mapping = json.loads(Path(args.map).read_text(encoding="utf-8-sig"))

    src = source.read_text(encoding="utf-8")
    tree = ast.parse(src)
    spans = {name: (start, end) for name, start, end in _top_level_spans(tree, src)}
    header = _header_block(src, tree)

    symbol_to_module: dict[str, str] = {}
    assigned: set[str] = set()
    for mod, symbols in mapping.items():
        if mod.startswith("_"):
            continue
        for sym in symbols:
            if sym not in spans:
                print(f"ERROR: symbol {sym!r} not found in {source}", file=sys.stderr)
                return 1
            if sym in symbol_to_module:
                print(f"ERROR: symbol {sym!r} mapped twice", file=sys.stderr)
                return 1
            symbol_to_module[sym] = mod
            assigned.add(sym)

    unassigned = sorted(set(spans) - assigned)
    if unassigned:
        print(f"ERROR: unassigned symbols: {unassigned}", file=sys.stderr)
        return 1

    if package.exists() and any(package.iterdir()):
        print(f"ERROR: package dir not empty: {package}", file=sys.stderr)
        return 1

    package.mkdir(parents=True, exist_ok=True)
    public_exports: list[str] = []
    module_own: dict[str, set[str]] = {}

    for mod, symbols in mapping.items():
        if mod.startswith("_"):
            continue
        chunks: list[str] = [header.rstrip(), ""]
        ordered = sorted(symbols, key=lambda s: spans[s][0])
        module_own[mod] = set(ordered)
        for sym in ordered:
            start, end = spans[sym]
            chunks.append(_slice_source(src, start, end).rstrip())
            chunks.append("")
            public_exports.append(sym)
        out = package / f"{mod}.py"
        out.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(ordered)} symbols)")

    for mod, symbols in mapping.items():
        if mod.startswith("_"):
            continue
        _inject_relative_imports(
            package / f"{mod}.py",
            own_symbols=module_own[mod],
            symbol_to_module=symbol_to_module,
            current_mod=mod,
        )

    init_lines = [
        '"""Package facade — re-exports public symbols for stable imports."""',
        "from __future__ import annotations",
        "",
    ]
    for mod, symbols in mapping.items():
        if mod.startswith("_"):
            continue
        ordered = sorted(symbols, key=lambda s: spans[s][0])
        if not ordered:
            continue
        init_lines.append(f"from .{mod} import (")
        for sym in ordered:
            init_lines.append(f"    {sym},")
        init_lines.append(")")
        init_lines.append("")
    init_lines.append("__all__ = [")
    for sym in public_exports:
        init_lines.append(f'    "{sym}",')
    init_lines.append("]")
    init_lines.append("")
    (package / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")
    print(f"wrote {package / '__init__.py'}")

    if args.delete_source:
        source.unlink()
        print(f"deleted {source}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
