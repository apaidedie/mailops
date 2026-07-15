from pathlib import Path
import re

html = Path("templates/index.html").read_text(encoding="utf-8")
start = html.find('id="page-settings"')
chunk = html[start : start + 80000]
print("pane ids:", re.findall(r'id="(settings-tab-[^"]+)"', chunk))
print("nav buttons:", re.findall(r"switchSettingsTab\('([^']+)'\)", chunk))

# Simulate toggle logic
from tests.frontend_js_bundle import load_feature_package_js

js = load_feature_package_js("static/js/core/settings")
assert "function switchSettingsTab" in js
# Scope bug: overview also uses settings-tab
print("overview settings-tab buttons:", len(re.findall(r'class="settings-tab ov-tab', html)))
print("settings page settings-tab buttons:", chunk.count('class="settings-tab'))
