from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fix_unified():
    p = ROOT / "tests/test_unified_mailbox_frontend_contract.py"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        'self._get_text(client, "/static/js/features/mailboxes.js")',
        "load_mailboxes_js()",
    )
    p.write_text(t, encoding="utf-8")
    print("unified remaining", [i + 1 for i, l in enumerate(t.splitlines()) if "mailboxes.js" in l])


def fix_overview():
    p = ROOT / "tests/test_overview_frontend_contract.py"
    t = p.read_text(encoding="utf-8")
    if "load_mailboxes_js" not in t:
        t = t.replace(
            "from tests.frontend_js_bundle import load_frontend_app_js",
            "from tests.frontend_js_bundle import load_frontend_app_js, load_mailboxes_js",
        )
    old = "(ROOT / 'static' / 'js' / 'features' / 'mailboxes.js').read_text(encoding='utf-8')"
    t = t.replace(old, "load_mailboxes_js()")
    p.write_text(t, encoding="utf-8")
    print("overview remaining", [i + 1 for i, l in enumerate(t.splitlines()) if "mailboxes.js" in l])


if __name__ == "__main__":
    fix_unified()
    fix_overview()
