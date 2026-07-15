#!/usr/bin/env python3
"""Point contract tests at package loaders instead of monofile / globals-only URLs."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

# Tests that used to fetch a monofile for content assertions.
CONTENT_REPLACEMENTS = [
    (
        'self._get_text(client, "/static/js/features/groups/globals.js")',
        "load_feature_package_js('static/js/features/groups')",
    ),
    (
        'self._get_text(client, "/static/js/features/accounts/globals.js")',
        "load_feature_package_js('static/js/features/accounts')",
    ),
    (
        'self._get_text(client, "/static/js/features/emails/globals.js")',
        "load_feature_package_js('static/js/features/emails')",
    ),
    (
        'self._get_text(client, "/static/js/core/settings/globals.js")',
        "load_feature_package_js('static/js/core/settings')",
    ),
    (
        'self._get_text("/static/js/features/groups/globals.js")',
        "load_feature_package_js('static/js/features/groups')",
    ),
    (
        'self._get_text("/static/js/features/accounts/globals.js")',
        "load_feature_package_js('static/js/features/accounts')",
    ),
    (
        'self._get_text("/static/js/features/emails/globals.js")',
        "load_feature_package_js('static/js/features/emails')",
    ),
    (
        'self._get_text("/static/js/core/settings/globals.js")',
        "load_feature_package_js('static/js/core/settings')",
    ),
]

# Path-only existence checks may keep globals.js.
IMPORT_SNIPPET = "from tests.frontend_js_bundle import load_feature_package_js"


def ensure_import(text: str) -> str:
    if "load_feature_package_js" not in text:
        if "from tests.frontend_js_bundle import" in text:
            text = text.replace(
                "from tests.frontend_js_bundle import",
                "from tests.frontend_js_bundle import load_feature_package_js, ",
                1,
            )
            # fix double spaces / trailing commas mess
            text = text.replace(
                "from tests.frontend_js_bundle import load_feature_package_js, load_frontend_app_js",
                "from tests.frontend_js_bundle import load_feature_package_js, load_frontend_app_js",
            )
        else:
            # insert after future import if present
            lines = text.splitlines(keepends=True)
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("from __future__"):
                    insert_at = i + 1
                    break
            lines.insert(insert_at, IMPORT_SNIPPET + "\n")
            text = "".join(lines)
    # clean accidental "import load_feature_package_js, \n"
    text = text.replace(
        "from tests.frontend_js_bundle import load_feature_package_js, \n",
        "from tests.frontend_js_bundle import load_feature_package_js\n",
    )
    return text


def main() -> None:
    for path in TESTS.glob("*.py"):
        original = path.read_text(encoding="utf-8")
        text = original
        touched = False
        for old, new in CONTENT_REPLACEMENTS:
            if old in text:
                text = text.replace(old, new)
                touched = True
        if touched:
            text = ensure_import(text)
            path.write_text(text, encoding="utf-8")
            print(f"updated {path.name}")


if __name__ == "__main__":
    main()
