from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# responsive
p = ROOT / "tests/test_responsive_detail_focus_contract.py"
t = p.read_text(encoding="utf-8")
if "load_feature_package_js" not in t:
    t = "from tests.frontend_js_bundle import load_feature_package_js\n" + t
t = t.replace(
    'Path("static/js/features/emails.js").read_text(encoding="utf-8")',
    "load_feature_package_js('static/js/features/emails')",
)
t = t.replace(
    'Path("static/js/features/accounts.js").read_text(encoding="utf-8")',
    "load_feature_package_js('static/js/features/accounts')",
)
p.write_text(t, encoding="utf-8")
print("fixed responsive")

# settings tab - just path existence list
p = ROOT / "tests/test_settings_tab_refactor_frontend.py"
t = p.read_text(encoding="utf-8")
t = t.replace('"static/js/features/emails.js"', '"static/js/features/emails/globals.js"')
t = t.replace('"static/js/features/groups.js"', '"static/js/features/groups/globals.js"')
t = t.replace('"static/js/features/accounts.js"', '"static/js/features/accounts/globals.js"')
t = t.replace('"static/js/core/settings.js"', '"static/js/core/settings/globals.js"')
p.write_text(t, encoding="utf-8")
print("fixed settings tab")

# smoke - html should contain package paths
p = ROOT / "tests/test_smoke_contract.py"
t = p.read_text(encoding="utf-8")
t = t.replace('self.assertIn("js/features/groups.js", html)', 'self.assertIn("js/features/groups/globals.js", html)')
t = t.replace('self.assertIn("js/features/accounts.js", html)', 'self.assertIn("js/features/accounts/globals.js", html)')
p.write_text(t, encoding="utf-8")
print("fixed smoke")
