from __future__ import annotations

import unittest
from pathlib import Path

DEPENDABOT_CONFIG = Path(".github/dependabot.yml")
DEPENDENCY_SECURITY_WORKFLOW = Path(".github/workflows/dependency-security.yml")
DOCKER_WORKFLOW = Path(".github/workflows/docker-build-push.yml")
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DependencySecurityAutomationTests(unittest.TestCase):
    def test_dependabot_covers_python_and_github_actions_with_bounded_weekly_updates(self):
        config = _read(DEPENDABOT_CONFIG)

        self.assertIn("version: 2", config)
        self.assertIn('package-ecosystem: "pip"', config)
        self.assertIn('package-ecosystem: "github-actions"', config)
        self.assertGreaterEqual(config.count('directory: "/"'), 2)
        self.assertGreaterEqual(config.count('interval: "weekly"'), 2)
        self.assertGreaterEqual(config.count("open-pull-requests-limit: 5"), 2)
        self.assertIn('"dependencies"', config)
        self.assertIn('"security"', config)
        self.assertIn("python-non-major:", config)
        self.assertIn("actions-non-major:", config)
        self.assertGreaterEqual(config.count('update-types: ["minor", "patch"]'), 2)

    def test_dependency_security_workflow_is_scheduled_reported_and_blocking(self):
        workflow = _read(DEPENDENCY_SECURITY_WORKFLOW)

        for trigger in ("push:", "pull_request:", "schedule:", "workflow_dispatch:"):
            self.assertIn(trigger, workflow)
        self.assertIn('cron: "23 3 * * 1"', workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        for path in (
            "requirements.txt",
            ".github/dependabot.yml",
            ".github/workflows/dependency-security.yml",
            ".github/workflows/docker-build-push.yml",
        ):
            self.assertIn(path, workflow)

        self.assertIn("python -m pip install pip-audit==2.10.1", workflow)
        self.assertIn("pip-audit -r requirements.txt", workflow)
        self.assertIn("--progress-spinner off", workflow)
        self.assertIn("--format json", workflow)
        self.assertIn("--output pip-audit-report.json", workflow)
        self.assertIn('echo "exit_code=$audit_status" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn("uses: actions/upload-artifact@v4", workflow)
        self.assertIn("path: pip-audit-report.json", workflow)
        self.assertIn("retention-days: 14", workflow)
        self.assertIn("steps.audit.outputs.exit_code", workflow)
        self.assertIn('exit "$status"', workflow)

    def test_docker_publish_quality_gate_audits_dependencies_before_readiness_and_tests(self):
        workflow = _read(DOCKER_WORKFLOW)

        install_index = workflow.index("python -m pip install pip-audit==2.10.1")
        audit_index = workflow.index("pip-audit -r requirements.txt --progress-spinner off")
        readiness_index = workflow.index("Run repository readiness gate")
        tests_index = workflow.index("Run publish gate tests")
        self.assertLess(install_index, audit_index)
        self.assertLess(audit_index, readiness_index)
        self.assertLess(readiness_index, tests_index)

    def test_dependency_security_assets_exist_and_document_audit_tooling(self):
        self.assertTrue(DEPENDABOT_CONFIG.is_file())
        self.assertTrue(DEPENDENCY_SECURITY_WORKFLOW.is_file())
        workflow = _read(DEPENDENCY_SECURITY_WORKFLOW)
        config = _read(DEPENDABOT_CONFIG)
        self.assertIn("pip-audit", workflow)
        self.assertIn('package-ecosystem: "pip"', config)
        self.assertIn('"security"', config)


if __name__ == "__main__":
    unittest.main()
