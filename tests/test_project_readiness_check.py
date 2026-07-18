from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import project_readiness_check


def _write(root: Path, relative: str, content: str = "ok") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _minimal_ready_repo(root: Path) -> None:
    canonical = project_readiness_check.CANONICAL
    _write(
        root,
        "README.md",
        " ".join(
            [
                "./docs/project-launchpad.md",
                "./docs/runtime-readiness.md",
                "./docs/external-integration-quickstart.md",
                "./docs/provider-onboarding.md",
                "./examples/external_api_python_client.py",
                project_readiness_check.CANONICAL_EXTERNAL_PREFIX,
                "integration_manifest",
                "X-API-Key",
            ]
        ),
    )
    _write(
        root,
        "README.en.md",
        " ".join(
            [
                "./docs/project-launchpad.md",
                "./docs/runtime-readiness.md",
                "./docs/external-integration-quickstart.md",
                "./docs/provider-onboarding.md",
                "./examples/external_api_python_client.py",
                project_readiness_check.CANONICAL_EXTERNAL_PREFIX,
                "integration_manifest",
                "X-API-Key",
            ]
        ),
    )
    _write(
        root,
        "docs/project-launchpad.md",
        "\n".join(
            [
                "unified mailbox workspace",
                "Outlook / Microsoft Graph",
                "Generic IMAP",
                "Mailbox pool",
                "mail_tm duckmail tempmail_lol emailnator cloudflare_temp_mail legacy_bridge",
                "plugin contract",
                "TEMP_MAIL_PROVIDER EXTERNAL_POOL_DEFAULT_PROVIDER ACTIVE_MAILBOX_PROVIDERS OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE",
                "python scripts/project_readiness_check.py",
                "python scripts/seed_demo_workspace.py --reset",
                "output/demo/mailops-demo.db",
                "scripts/external_api_smoke.py",
                "X-API-Key: <your-api-key>",
                canonical["integration_bundle"],
                canonical["capabilities"],
                canonical["providers"],
                canonical["mailboxes"],
                project_readiness_check.CANONICAL_EXTERNAL_PREFIX + "/docs",
                canonical["openapi"],
                canonical["session_start"],
                canonical["session_read"],
                canonical["session_close"],
                "examples/external_api_python_client.py",
                "examples/external_api_javascript_client.js",
                "validate-provider",
                "contract_validation.status=valid",
                "External Integration Quickstart",
                "Provider Onboarding Guide",
            ]
        ),
    )
    _write(
        root,
        "docs/runtime-readiness.md",
        "\n".join(
            [
                "python web_outlook_app.py",
                "SCHEDULER_AUTOSTART=false",
                "DUCKMAIL_API_BASE=https://api.duckmail.sbs",
                "DUCKMAIL_BEARER_TOKEN=",
                "X-API-Key",
                canonical["capabilities"],
                canonical["providers"],
                canonical["openapi"],
                canonical["integration_bundle"],
                "LOG_FORMAT=json LOG_LEVEL=INFO PERF_LOGGING=true",
                "line-delimited JSON trace_id ELK Loki",
                "EXTERNAL_API_CORS_ORIGINS EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION",
                "supports_credentials=false /api/v1/external/* /api/v1/external/* X-Trace-Id",
            ]
        ),
    )
    _write(
        root,
        "docs/external-integration-quickstart.md",
        "\n".join(
            [
                "scripts/project_readiness_check.py",
                "scripts/external_api_smoke.py --format json",
                "integration-bundle integration_manifest",
                canonical["integration_bundle"],
                "X-API-Key: <your-api-key>",
                canonical["capabilities"],
                canonical["openapi"],
                canonical["session_start"],
                canonical["session_read"],
                canonical["session_close"],
                "provider_name source_strategy",
                project_readiness_check.LEGACY_EXTERNAL_PREFIX,
                "EXTERNAL_API_CORS_ORIGINS EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION",
                "supports_credentials=false /api/v1/external/* /api/v1/external/* X-Trace-Id",
            ]
        ),
    )
    _write(
        root,
        "docs/provider-onboarding.md",
        "\n".join(
            [
                "scripts/project_readiness_check.py",
                canonical["capabilities"],
                canonical["providers"],
                canonical["mailboxes"],
                canonical["pool_claim"],
                canonical["temp_apply"],
                canonical["session_start"],
                canonical["openapi"],
                "integration_manifest provider_name provider contract_validation",
                "provider-dev-kit scripts/provider_dev_kit.py --format json --probe-options secret_scan offline",
                ".runtime/providers.example.json .runtime/providers.example.toml",
                "validate-provider DUCKMAIL_BEARER_TOKEN",
            ]
        ),
    )
    _write(root, ".env.example", "\n".join(f"{key}=" for key in project_readiness_check.REQUIRED_ENV_KEYS))
    _write(
        root,
        ".runtime/providers.example.json",
        json.dumps(
            {
                "providers": {
                    "temp_mail_provider": "mail_tm",
                    "pool_default_provider": "auto",
                    "active_mailbox_providers": ["mail_tm", "imap"],
                }
            }
        ),
    )
    _write(
        root,
        ".runtime/providers.example.toml",
        '[providers]\ntemp_mail_provider = "mail_tm"\npool_default_provider = "auto"\nactive_mailbox_providers = ["mail_tm", "imap"]\n',
    )
    _write(
        root,
        "examples/external_api_python_client.py",
        " ".join(
            [
                project_readiness_check.CANONICAL_EXTERNAL_PREFIX,
                "/integration-bundle",
                "mailbox-sessions/start mailbox-sessions/read mailbox-sessions/close",
                "MAILOPS_API_KEY X-API-Key integration-bundle provider_name",
            ]
        ),
    )
    _write(
        root,
        "examples/external_api_javascript_client.js",
        " ".join(
            [
                project_readiness_check.CANONICAL_EXTERNAL_PREFIX,
                "/integration-bundle",
                "mailbox-sessions/start mailbox-sessions/read mailbox-sessions/close",
                "MAILOPS_API_KEY X-API-Key integration-bundle provider_name",
            ]
        ),
    )
    _write(root, "examples/temp_mail_provider_plugin_template.py")
    _write(
        root,
        "scripts/provider_dev_kit.py",
        "PROVIDER_DEV_KIT_NAME provider-dev-kit build_scaffold_report build_validation_report scan_provider_file_for_secrets SECRET_PATTERNS scaffold_provider_plugin validate_provider_contract --format json text --probe-options secret_scan contract_validation\n",
    )
    _write(
        root,
        "scripts/seed_demo_workspace.py",
        "DEFAULT_DB_PATH output demo mailops-demo.db --dry-run --reset --format seed_demo_workspace init_db SCHEDULER_AUTOSTART DATABASE_PATH web_outlook_app.py\n",
    )
    _write(
        root,
        "scripts/external_api_smoke.py",
        f'CANONICAL_EXTERNAL_PREFIX = "{project_readiness_check.CANONICAL_EXTERNAL_PREFIX}"\n--format text json run_smoke build_report SECRET_PATTERNS /health /capabilities /integration-bundle /providers /mailboxes /openapi.json\n',
    )
    _write(
        root,
        ".github/dependabot.yml",
        'version: 2\npackage-ecosystem: "pip"\npackage-ecosystem: "github-actions"\ninterval: "weekly"\n',
    )
    _write(
        root,
        ".github/workflows/dependency-security.yml",
        "\n".join(
            [
                "name: Dependency Security",
                "permissions:",
                "  contents: read",
                "schedule:",
                "workflow_dispatch:",
                "python -m pip install pip-audit==2.10.1",
                "pip-audit -r requirements.txt",
                "--format json",
                "--output pip-audit-report.json",
                "actions/upload-artifact@v4",
                "if: always()",
                "steps.audit.outputs.exit_code",
            ]
        ),
    )
    for relative in (
        "tests/test_external_api_smoke_script.py",
        "tests/test_external_api_python_client.py",
        "tests/external_api_javascript_client.test.js",
        "tests/test_temp_mail_provider_contract_validation.py",
        "tests/test_temp_mail_provider_plugin_template.py",
    ):
        _write(root, relative)


class ProjectReadinessCheckTests(unittest.TestCase):
    def test_runtime_logging_env_contract_is_required(self):
        self.assertIn("LOG_FORMAT", project_readiness_check.REQUIRED_ENV_KEYS)
        self.assertIn("LOG_LEVEL", project_readiness_check.REQUIRED_ENV_KEYS)

    def test_external_api_cors_env_contract_is_required(self):
        self.assertIn("EXTERNAL_API_CORS_ORIGINS", project_readiness_check.REQUIRED_ENV_KEYS)
        self.assertIn("EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION", project_readiness_check.REQUIRED_ENV_KEYS)

    def test_external_api_cors_docs_contract_fails_when_policy_drifts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            _write(
                root, "docs/runtime-readiness.md", "LOG_FORMAT LOG_LEVEL PERF_LOGGING line-delimited JSON trace_id ELK Loki"
            )
            _write(root, "docs/external-integration-quickstart.md", "scripts/project_readiness_check.py")

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        failure = next(item for item in report["failures"] if item["name"] == "docs.external_api_cors.contract")
        self.assertIn("supports_credentials=false", failure["details"]["missing"])
        self.assertIn("X-Trace-Id", failure["details"]["missing"])

    def test_current_repository_passes(self):
        results = project_readiness_check.run_checks(Path.cwd())

        self.assertTrue(all(result.ok for result in results), [result for result in results if not result.ok])

    def test_missing_required_asset_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            (root / "README.md").unlink()

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        asset_failure = next(item for item in report["failures"] if item["name"] == "assets.required")
        self.assertIn("README.md", asset_failure["details"]["missing"])

    def test_project_launchpad_contract_fails_when_key_references_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            _write(root, "docs/project-launchpad.md", "unified mailbox workspace only")

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        launchpad_failure = next(item for item in report["failures"] if item["name"] == "docs.project_launchpad.contract")
        self.assertIn(project_readiness_check.CANONICAL["integration_bundle"], launchpad_failure["details"]["missing"])
        self.assertIn("Provider Onboarding Guide", launchpad_failure["details"]["missing"])
        self.assertIn("python scripts/seed_demo_workspace.py --reset", launchpad_failure["details"]["missing"])

    def test_runtime_logging_docs_contract_fails_when_controls_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            _write(root, "docs/runtime-readiness.md", "python web_outlook_app.py")

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        failure = next(item for item in report["failures"] if item["name"] == "docs.runtime_logging.contract")
        self.assertIn("LOG_FORMAT", failure["details"]["missing"])
        self.assertIn("line-delimited JSON", failure["details"]["missing"])

    def test_dependency_security_contract_fails_when_workflow_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            _write(root, ".github/workflows/dependency-security.yml", "name: Dependency Security")

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        failure = next(item for item in report["failures"] if item["name"] == "security.dependency_automation")
        self.assertIn("pip-audit==2.10.1", failure["details"]["workflow_missing"])
        self.assertIn("actions/upload-artifact@v4", failure["details"]["workflow_missing"])

    def test_missing_demo_seed_script_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            (root / "scripts/seed_demo_workspace.py").unlink()

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        asset_failure = next(item for item in report["failures"] if item["name"] == "assets.required")
        self.assertIn("scripts/seed_demo_workspace.py", asset_failure["details"]["missing"])

    def test_missing_provider_dev_kit_script_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            (root / "scripts/provider_dev_kit.py").unlink()

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        asset_failure = next(item for item in report["failures"] if item["name"] == "assets.required")
        self.assertIn("scripts/provider_dev_kit.py", asset_failure["details"]["missing"])

    def test_provider_onboarding_contract_requires_dev_kit_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            _write(
                root, "docs/provider-onboarding.md", "scripts/project_readiness_check.py contract_validation validate-provider"
            )

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        provider_failure = next(item for item in report["failures"] if item["name"] == "docs.provider_onboarding.contract")
        self.assertIn("scripts/provider_dev_kit.py", provider_failure["details"]["missing"])
        self.assertIn("secret_scan", provider_failure["details"]["missing"])

    def test_json_output_is_stable_and_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = project_readiness_check.main(["--root", str(root), "--format", "json"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["failed"], 0)
        self.assertIsInstance(payload["checks"], list)
        self.assertEqual(payload["failures"], [])

    def test_secret_leak_detection_fails_on_realistic_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_ready_repo(root)
            _write(root, ".env.example", "DUCKMAIL_BEARER_TOKEN=dk_" + "a" * 64)

            report = project_readiness_check.build_report(project_readiness_check.run_checks(root))

        self.assertFalse(report["success"])
        secret_failure = next(item for item in report["failures"] if item["name"] == "secrets.checked_in_templates")
        self.assertEqual(secret_failure["details"]["hits"][0]["file"], ".env.example")
        self.assertEqual(secret_failure["details"]["hits"][0]["pattern"], "duckmail_bearer_token")


if __name__ == "__main__":
    unittest.main()
