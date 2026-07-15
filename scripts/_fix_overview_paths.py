from pathlib import Path

p = Path("tests/test_overview_frontend_contract.py")
t = p.read_text(encoding="utf-8")
repls = {
    "(ROOT / 'static' / 'js' / 'features' / 'groups.js').read_text(encoding='utf-8')": "load_feature_package_js('static/js/features/groups')",
    "(ROOT / 'static' / 'js' / 'features' / 'accounts.js').read_text(encoding='utf-8')": "load_feature_package_js('static/js/features/accounts')",
    "(ROOT / 'static' / 'js' / 'features' / 'emails.js').read_text(encoding='utf-8')": "load_feature_package_js('static/js/features/emails')",
}
for a, b in repls.items():
    t = t.replace(a, b)
if "from tests.frontend_js_bundle import" in t:
    for line in t.splitlines():
        if line.startswith("from tests.frontend_js_bundle import"):
            if "load_feature_package_js" not in line:
                t = t.replace(
                    "from tests.frontend_js_bundle import",
                    "from tests.frontend_js_bundle import load_feature_package_js, ",
                    1,
                )
            break
p.write_text(t, encoding="utf-8")
print("done", "groups.js path left", t.count("features' / 'groups.js"))
