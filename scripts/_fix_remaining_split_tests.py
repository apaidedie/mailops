from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ("temp_emails", "overview")


def ensure_import(text: str) -> str:
    if "load_feature_package_js" not in text:
        return text
    if "from tests.frontend_js_bundle import" in text:
        line = [ln for ln in text.splitlines() if "from tests.frontend_js_bundle import" in ln][0]
        if "load_feature_package_js" not in line:
            text = text.replace(
                "from tests.frontend_js_bundle import",
                "from tests.frontend_js_bundle import load_feature_package_js, ",
                1,
            )
        return text
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    added = False
    for ln in lines:
        out.append(ln)
        if not added and ln.startswith("from __future__"):
            out.append("from tests.frontend_js_bundle import load_feature_package_js\n")
            added = True
    if not added:
        return "from tests.frontend_js_bundle import load_feature_package_js\n" + text
    return "".join(out)


def main() -> None:
    for path in (ROOT / "tests").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        original = text
        for feat in FEATURES:
            text = text.replace(
                f'self._get_text(client, "/static/js/features/{feat}.js")',
                f"load_feature_package_js('static/js/features/{feat}')",
            )
            text = text.replace(
                f'self._get_text("/static/js/features/{feat}.js")',
                f"load_feature_package_js('static/js/features/{feat}')",
            )
            text = text.replace(
                f'Path("static/js/features/{feat}.js").read_text(encoding="utf-8")',
                f"load_feature_package_js('static/js/features/{feat}')",
            )
            text = text.replace(
                f"(ROOT / 'static' / 'js' / 'features' / '{feat}.js').read_text(encoding='utf-8')",
                f"load_feature_package_js('static/js/features/{feat}')",
            )
            # HTML/path assertions: package entrypoint
            text = text.replace(f'js/features/{feat}.js', f'js/features/{feat}/globals.js')
            text = text.replace(f'"static/js/features/{feat}.js"', f'"static/js/features/{feat}/globals.js"')
            text = text.replace(f"'static/js/features/{feat}.js'", f"'static/js/features/{feat}/globals.js'")
        if text != original:
            text = ensure_import(text)
            path.write_text(text, encoding="utf-8")
            print(f"updated {path.name}")


if __name__ == "__main__":
    main()
