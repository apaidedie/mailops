from __future__ import annotations

import unittest
from pathlib import Path

CODE_QUALITY_WORKFLOW = Path(".github/workflows/code-quality.yml")
DOCKER_WORKFLOW = Path(".github/workflows/docker-build-push.yml")

REQUIRED_READINESS_PATHS = (
    ".env.example",
    ".runtime/providers.example.json",
    ".runtime/providers.example.toml",
    "docs/external-integration-quickstart.md",
    "docs/provider-onboarding.md",
    "docs/runtime-readiness.md",
    "docs/project-launchpad.md",
    "examples/external_api_python_client.py",
    "examples/external_api_javascript_client.js",
    "examples/temp_mail_provider_plugin_template.py",
    "scripts/external_api_smoke.py",
    "scripts/project_readiness_check.py",
    "tests/test_ci_readiness_gate_workflows.py",
    "tests/test_dependency_security_automation.py",
    "tests/test_project_readiness_check.py",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/code-quality.yml",
    ".github/workflows/dependency-security.yml",
    ".github/workflows/docker-build-push.yml",
    "RELEASE.md",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class CiReadinessGateWorkflowTests(unittest.TestCase):
    def test_code_quality_workflow_runs_repository_readiness_gate(self):
        workflow = _read(CODE_QUALITY_WORKFLOW)

        self.assertIn("repository-readiness:", workflow)
        self.assertIn("name: Repository Readiness", workflow)
        self.assertIn("python scripts/project_readiness_check.py", workflow)
        self.assertIn(
            "python -m unittest tests.test_ci_readiness_gate_workflows tests.test_project_readiness_check -v",
            workflow,
        )
        self.assertIn('python-version: "3.13"', workflow)

    def test_code_quality_workflow_triggers_on_integration_readiness_assets(self):
        workflow = _read(CODE_QUALITY_WORKFLOW)

        for path in REQUIRED_READINESS_PATHS:
            self.assertIn(f'- "{path}"', workflow)

    def test_docker_publish_quality_gate_runs_repository_readiness_before_tests(self):
        workflow = _read(DOCKER_WORKFLOW)

        readiness_index = workflow.index("Repository readiness gate")
        tests_index = workflow.index("Focused contract tests")
        self.assertIn("python scripts/project_readiness_check.py", workflow[readiness_index:tests_index])
        self.assertLess(readiness_index, tests_index)


if __name__ == "__main__":
    unittest.main()
