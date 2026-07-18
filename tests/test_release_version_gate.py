"""Release version alignment gate (scripts/check_release_version.py)."""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from mailops import __version__ as APP_VERSION
from scripts import check_release_version as gate

REPO_ROOT = Path(__file__).resolve().parents[1]
STABLE_VERSION_RE = re.compile(r"(?:当前稳定版本：|Current stable version:)\s*`(?P<version>v[^`]+)`")


class ReleaseVersionGateTests(unittest.TestCase):
    def test_skip_on_main_ref(self):
        self.assertEqual(gate.run_checks("refs/heads/main"), [])

    def test_ok_when_version_and_changelog_match(self):
        ref = "refs/tags/v2.7.0"
        with patch.object(gate, "check_app_version", return_value=[]):
            with patch.object(gate, "check_changelog", return_value=[]):
                self.assertEqual(gate.run_checks(ref), [])

    def test_errors_when_version_mismatch(self):
        ref = "refs/tags/v2.7.0"
        with patch.object(gate, "check_app_version", return_value=["version mismatch"]):
            with patch.object(gate, "check_changelog", return_value=[]):
                errors = gate.run_checks(ref)
        self.assertEqual(len(errors), 1)
        self.assertIn("version", errors[0])

    def test_main_exits_zero(self):
        with patch.dict(os.environ, {"GITHUB_REF": "refs/heads/main"}, clear=False):
            self.assertEqual(gate.main(), 0)

    def test_tag_mismatch_exits_nonzero(self):
        with patch.dict(os.environ, {"GITHUB_REF": "refs/tags/v9.9.9"}, clear=False):
            code = gate.main()
        self.assertEqual(code, 1)


class VersionMetadataConsistencyTests(unittest.TestCase):
    def test_npm_metadata_and_readme_stable_versions_match_runtime(self):
        package_data = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        package_lock_data = json.loads((REPO_ROOT / "package-lock.json").read_text(encoding="utf-8"))

        with self.subTest(file="package.json"):
            self.assertEqual(package_data.get("version"), APP_VERSION)

        with self.subTest(file="package-lock.json"):
            self.assertEqual(package_lock_data.get("version"), APP_VERSION)
            self.assertEqual(package_lock_data.get("packages", {}).get("", {}).get("version"), APP_VERSION)

        expected_readme_version = f"v{APP_VERSION}"
        for readme_name in ("README.md", "README.en.md"):
            with self.subTest(file=readme_name):
                readme = (REPO_ROOT / readme_name).read_text(encoding="utf-8")
                match = STABLE_VERSION_RE.search(readme)
                self.assertIsNotNone(match, f"{readme_name} must declare the current stable version")
                self.assertEqual(match.group("version"), expected_readme_version)


if __name__ == "__main__":
    unittest.main()
