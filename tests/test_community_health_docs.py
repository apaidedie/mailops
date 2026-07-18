from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class CommunityHealthDocsTests(unittest.TestCase):
    def test_top_level_community_health_docs_exist(self):
        for relative in ("CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md"):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_top_level_community_health_docs_are_not_gitignored(self):
        for relative in ("CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md"):
            result = subprocess.run(["git", "check-ignore", "-q", relative], cwd=ROOT, check=False)
            self.assertEqual(result.returncode, 1, relative)

    def test_readmes_link_community_health_docs(self):
        for relative in ("README.md", "README.en.md"):
            content = _read(relative)
            self.assertIn("./CONTRIBUTING.md", content)
            self.assertIn("./SECURITY.md", content)
            self.assertIn("./SUPPORT.md", content)

    def test_readmes_link_project_launchpad(self):
        for relative in ("README.md", "README.en.md"):
            content = _read(relative)
            self.assertIn("./docs/project-launchpad.md", content)

    def test_contributing_doc_covers_project_workflow(self):
        content = _read("CONTRIBUTING.md")
        for expected in (
            "python scripts/project_readiness_check.py",
            "docs/external-integration-quickstart.md",
            "docs/provider-onboarding.md",
            "python web_mailops_app.py validate-provider",
            "node --test tests/external_api_javascript_client.test.js",
        ):
            self.assertIn(expected, content)

    def test_security_doc_forbids_public_secret_disclosure(self):
        content = _read("SECURITY.md")
        for secret_name in (
            "X-API-Key",
            "DUCKMAIL_BEARER_TOKEN",
            "refresh tokens",
            "task tokens",
            "mailbox passwords",
            "database files",
            "live message content",
        ):
            self.assertIn(secret_name, content)

    def test_support_doc_routes_users_to_expected_docs_and_diagnostics(self):
        content = _read("SUPPORT.md")
        for expected in (
            "README.md",
            "RELEASE.md",
            "docs/project-launchpad.md",
            "docs/external-integration-quickstart.md",
            "docs/provider-onboarding.md",
            ".github/ISSUE_TEMPLATE/",
            "Version, commit, Docker image tag, or deployment mode",
            "python scripts/external_api_smoke.py",
        ):
            self.assertIn(expected, content)


if __name__ == "__main__":
    unittest.main()
