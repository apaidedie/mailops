from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from scripts import external_api_smoke
from tests._import_app import clear_login_attempts, import_web_app_module

CANONICAL_EXTERNAL_PREFIX = external_api_smoke.CANONICAL_EXTERNAL_PREFIX
LEGACY_EXTERNAL_PREFIX = external_api_smoke.LEGACY_EXTERNAL_PREFIX
CANONICAL_INTEGRATION_BUNDLE = external_api_smoke.CANONICAL_INTEGRATION_BUNDLE
CANONICAL_DOCS = external_api_smoke.CANONICAL_DOCS
CANONICAL_OPENAPI = external_api_smoke.CANONICAL_OPENAPI
CANONICAL_PROVIDERS = external_api_smoke.CANONICAL_PROVIDERS
CANONICAL_PROVIDER_PREFLIGHT = external_api_smoke.CANONICAL_PROVIDER_PREFLIGHT
CANONICAL_MAILBOXES = external_api_smoke.CANONICAL_MAILBOXES
CANONICAL_SESSION_START = external_api_smoke.CANONICAL_SESSION_START
CANONICAL_SESSION_CLOSE = external_api_smoke.CANONICAL_SESSION_CLOSE
LEGACY_DOCS = external_api_smoke.LEGACY_DOCS
LEGACY_INTEGRATION_BUNDLE = external_api_smoke.LEGACY_INTEGRATION_BUNDLE
LEGACY_PROVIDER_PREFLIGHT = external_api_smoke.LEGACY_PROVIDER_PREFLIGHT
LEGACY_SESSION_START = external_api_smoke.LEGACY_SESSION_START
LEGACY_SESSION_CLOSE = external_api_smoke.LEGACY_SESSION_CLOSE


def _capabilities_payload() -> dict:
    quickstart = {
        "version": 1,
        "auth": {"header": "X-API-Key", "placeholder": "<your-api-key>"},
        "endpoints": {
            "integration_bundle": CANONICAL_INTEGRATION_BUNDLE,
            "provider_preflight": CANONICAL_PROVIDER_PREFLIGHT,
            "mailbox_session_start": CANONICAL_SESSION_START,
            "mailbox_session_close": CANONICAL_SESSION_CLOSE,
        },
    }
    return {
        "success": True,
        "code": "OK",
        "message": "success",
        "data": {
            "integration_manifest": {
                "auth": {"header": "X-API-Key", "placeholder": "<your-api-key>"},
                "discovery": {
                    "endpoints": {
                        "docs": CANONICAL_DOCS,
                        "integration_bundle": CANONICAL_INTEGRATION_BUNDLE,
                        "openapi": CANONICAL_OPENAPI,
                        "providers": CANONICAL_PROVIDERS,
                        "provider_preflight": CANONICAL_PROVIDER_PREFLIGHT,
                        "mailboxes": CANONICAL_MAILBOXES,
                    }
                },
                "quickstart": quickstart,
                "workflows": [
                    {"key": "start_mailbox_session", "steps": []},
                    {"key": "browse_mailbox_directory", "steps": []},
                    {"key": "claim_pool_mailbox", "steps": []},
                    {"key": "create_task_temp_mailbox", "steps": []},
                ],
            },
            "quickstart": quickstart,
            "documentation": {
                "version": 1,
                "entries": {
                    "external_integration_quickstart": {
                        "label": "External integration quickstart",
                        "type": "guide",
                        "path": "docs/external-integration-quickstart.md",
                        "purpose": "Short path for external services.",
                    },
                    "api_docs": {
                        "label": "External API docs",
                        "type": "api_docs",
                        "endpoint": CANONICAL_DOCS,
                    },
                    "openapi": {
                        "label": "OpenAPI",
                        "type": "api_contract",
                        "endpoint": CANONICAL_OPENAPI,
                    },
                },
            },
            "integration_bundle": {
                "endpoint": CANONICAL_INTEGRATION_BUNDLE,
                "response_contract": "integration_bundle",
                "recommended_for": "external services that need one secret-safe readiness bundle",
            },
            "endpoints": {
                "docs": CANONICAL_DOCS,
                "integration_bundle": CANONICAL_INTEGRATION_BUNDLE,
                "openapi": CANONICAL_OPENAPI,
                "providers": CANONICAL_PROVIDERS,
                "provider_preflight": CANONICAL_PROVIDER_PREFLIGHT,
                "mailboxes": CANONICAL_MAILBOXES,
                "mailbox_session_start": CANONICAL_SESSION_START,
                "mailbox_session_close": CANONICAL_SESSION_CLOSE,
            },
            "legacy_endpoints": {},
            "compatibility": {
                "canonical_prefix": CANONICAL_EXTERNAL_PREFIX,
                "legacy_prefix": LEGACY_EXTERNAL_PREFIX,
                "legacy_supported": False,
                "legacy_endpoints": {},
                "aliases": {},
            },
            "mailbox_session": {
                "start_endpoint": CANONICAL_SESSION_START,
                "close_endpoint": CANONICAL_SESSION_CLOSE,
                "source_strategy_values": ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
            },
            "external_mailbox_read_contract": {"version": 1},
        },
    }


def _routing_matrix() -> dict:
    def scope(name: str, request_field: str, endpoint: str, allowed_values: list[str]) -> dict:
        providers = [
            {
                "provider": value,
                "canonical_provider": value,
                "label": value,
                "kind": "auto" if value == "auto" else "temp",
                "active": True,
                "configured": value != "duckmail",
                "usable": value != "duckmail",
                "status": "ready" if value != "duckmail" else "needs_config",
                "reason": "local_config_ready" if value != "duckmail" else "missing_config",
                "aliases": [],
                "endpoints": {
                    "request": endpoint,
                    "health": f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health",
                },
            }
            for value in allowed_values
        ]
        return {
            "scope": name,
            "label": name.replace("_", " ").title(),
            "request_field": request_field,
            "settings_key": "temp_mail_provider" if "temp" in name else "pool_claim_provider",
            "env": "TEMP_MAIL_PROVIDER" if "temp" in name else "EXTERNAL_POOL_DEFAULT_PROVIDER",
            "endpoint": endpoint,
            "allowed_values": allowed_values,
            "counts": {
                "total": len(providers),
                "usable": sum(1 for provider in providers if provider["usable"]),
                "needs_config": 1 if "duckmail" in allowed_values else 0,
                "inactive": 0,
            },
            "providers": providers,
        }

    return {
        "version": 1,
        "source_priority": ["env", "provider_config_file", "settings", "default"],
        "scopes": {
            "temp_runtime_default": scope(
                "temp_runtime_default",
                "provider_name",
                f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
                ["mail_tm", "gptmail"],
            ),
            "task_temp_apply": scope(
                "task_temp_apply",
                "provider_name",
                f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
                ["mail_tm", "duckmail"],
            ),
            "pool_claim_default": scope(
                "pool_claim_default",
                "provider",
                f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-random",
                ["auto", "mail_tm"],
            ),
            "explicit_pool_claim": scope(
                "explicit_pool_claim",
                "provider",
                f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-random",
                ["auto", "imap"],
            ),
        },
    }


def _providers_payload() -> dict:
    readiness = _readiness_summary()
    return {
        "success": True,
        "code": "OK",
        "message": "success",
        "data": {
            "readiness_summary": readiness,
        },
    }


def _mailboxes_payload() -> dict:
    readiness = _readiness_summary()
    return {
        "success": True,
        "code": "OK",
        "message": "success",
        "data": {
            "success": True,
            "mailboxes": [],
            "summary": {"total": 0},
            "provider_context": {
                "version": 1,
                "readiness_summary": readiness,
            },
        },
    }


def _readiness_summary() -> dict:
    return {
        "version": 1,
        "overall_status": "needs_config",
        "totals": {
            "mailboxes": 0,
            "account_mailboxes": 0,
            "temp_mailboxes": 0,
            "providers": 4,
            "active_providers": 4,
            "ready_providers": 3,
            "configured_providers": 3,
            "needs_config_providers": 1,
            "dynamic_create_providers": 2,
            "account_providers": 1,
            "temp_providers": 3,
        },
        "issues": {
            "needs_config": 1,
            "inactive": 0,
            "unknown_filter_entries": 0,
            "invalid_default_entries": 0,
            "inactive_default_entries": 0,
        },
        "source_priority": ["env", "provider_config_file", "settings", "default"],
        "provider_selector_fields": {
            "pool_claim": "provider",
            "task_temp_apply": "provider_name",
        },
        "routing_matrix": _routing_matrix(),
        "endpoints": {
            "mailboxes": CANONICAL_MAILBOXES,
            "providers": CANONICAL_PROVIDERS,
            "provider_health": f"{CANONICAL_EXTERNAL_PREFIX}/providers/{{kind}}/{{provider}}/health",
            "provider_preflight": CANONICAL_PROVIDER_PREFLIGHT,
        },
        "providers": [
            {
                "kind": "temp",
                "provider": "mail_tm",
                "label": "Mail.tm",
                "active": True,
                "configured": True,
                "readiness_status": "ready",
                "mailbox_count": 0,
                "account_count": 0,
                "temp_count": 0,
                "can_dynamic_create": True,
                "requires_pool_inventory": False,
                "read_capability": "temp_provider",
                "read_capabilities": ["temp_provider"],
                "missing_config_count": 0,
                "endpoints": {"provider_preflight": CANONICAL_PROVIDER_PREFLIGHT},
            }
        ],
    }


def _health_payload() -> dict:
    return {
        "success": True,
        "data": {
            "status": "ready",
            "service": "mailops",
            "readiness": {
                "status": "ready",
                "database": "ok",
                "upstream_probe": {"status": "not_requested", "ok": None},
                "discovery": {
                    "status": "ready",
                    "next_endpoints": {
                        "capabilities": f"{CANONICAL_EXTERNAL_PREFIX}/capabilities",
                        "integration_bundle": CANONICAL_INTEGRATION_BUNDLE,
                        "docs": CANONICAL_DOCS,
                        "providers": CANONICAL_PROVIDERS,
                        "mailboxes": CANONICAL_MAILBOXES,
                        "openapi": CANONICAL_OPENAPI,
                    },
                },
                "providers": {
                    "status": "ready",
                    "summary": {
                        "total": 4,
                        "active": 4,
                        "ready": 3,
                        "needs_config": 1,
                        "dynamic_create": 2,
                        "account": 1,
                        "temp": 3,
                        "unknown_filter_entries": 0,
                        "invalid_default_entries": 0,
                        "inactive_default_entries": 0,
                    },
                    "filter_mode": "all",
                    "active_allowlist": [],
                },
                "mailbox_directory": {
                    "status": "empty",
                    "endpoint": CANONICAL_MAILBOXES,
                    "scoped": False,
                    "summary": {"total": 0},
                    "totals": {"mailboxes": 0, "account_mailboxes": 0, "temp_mailboxes": 0},
                    "quick_probe_params": {"page_size": 1},
                },
                "pool": {
                    "status": "ready",
                    "external_enabled": True,
                    "current_consumer_has_access": True,
                    "default_provider": "auto",
                    "restrictions": [],
                    "claim_endpoint": f"{CANONICAL_EXTERNAL_PREFIX}/pool/claim-random",
                },
                "task_temp_mailbox": {
                    "status": "ready",
                    "default_provider": "mail_tm",
                    "provider_selector_field": "provider_name",
                    "apply_endpoint": f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
                    "finish_endpoint": f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/{{task_token}}/finish",
                },
                "warnings": [],
            },
        },
    }


def _openapi_payload() -> dict:
    return {
        "openapi": "3.1.0",
        "paths": {
            CANONICAL_DOCS: {"get": {}},
            CANONICAL_INTEGRATION_BUNDLE: {"get": {}},
            CANONICAL_PROVIDER_PREFLIGHT: {"get": {}},
            CANONICAL_SESSION_START: {"post": {}},
            CANONICAL_SESSION_CLOSE: {"post": {}},
        },
        "x-external-api-version": "v1",
        "x-legacy-endpoints": {},
        "components": {
            "schemas": {
                "MailboxSessionStartRequest": {"type": "object"},
                "MailboxSessionCloseRequest": {"type": "object"},
                "MailboxSessionData": {"type": "object"},
                "MailboxSessionCloseData": {"type": "object"},
                "MailboxSessionDiscovery": {"type": "object"},
                "IntegrationBundleData": {"type": "object"},
            }
        },
    }


def _integration_bundle_payload() -> dict:
    capabilities = _capabilities_payload()["data"]
    provider_readiness = _readiness_summary()
    return {
        "success": True,
        "data": {
            "version": 1,
            "service": "mailops",
            "app_version": "test",
            "status": "ready",
            "generated_at": "2026-07-09T00:00:00Z",
            "auth": {"header": "X-API-Key", "placeholder": "<your-api-key>"},
            "endpoints": capabilities["endpoints"],
            "legacy_endpoints": capabilities["legacy_endpoints"],
            "compatibility": capabilities["compatibility"],
            "documentation": capabilities["documentation"],
            "quickstart": capabilities["quickstart"],
            "readiness": {
                "status": "ready",
                "external_api": _health_payload()["data"]["readiness"],
                "providers": provider_readiness,
                "mailbox_directory": _health_payload()["data"]["readiness"]["mailbox_directory"],
                "pool": _health_payload()["data"]["readiness"]["pool"],
                "task_temp_mailbox": _health_payload()["data"]["readiness"]["task_temp_mailbox"],
                "warnings": [],
            },
            "provider_selection": {
                "source_priority": ["env", "provider_config_file", "settings", "default"],
                "selector_fields": {"pool_claim": "provider", "task_temp_apply": "provider_name"},
                "provider_values": {"temp_apply": ["mail_tm", "duckmail"]},
                "defaults": {"pool_claim_provider": "auto", "temp_mail_provider": "mail_tm", "active_mailbox_providers": []},
                "config_file": {},
                "selection_recipes_count": 0,
                "routing_matrix": _routing_matrix(),
            },
            "openapi": {
                "endpoint": CANONICAL_OPENAPI,
                "version": "3.1.0",
                "path_count": len(_openapi_payload()["paths"]),
                "schema_count": len(_openapi_payload()["components"]["schemas"]),
                "operation_count": 4,
            },
            "workflows": [
                {"key": "start_mailbox_session", "label": "Start mailbox session", "description": "", "step_count": 3}
            ],
            "smoke_checks": [
                {"key": "health", "method": "GET", "endpoint": f"{CANONICAL_EXTERNAL_PREFIX}/health", "purpose": "health"},
                {
                    "key": "capabilities",
                    "method": "GET",
                    "endpoint": f"{CANONICAL_EXTERNAL_PREFIX}/capabilities",
                    "purpose": "capabilities",
                },
                {"key": "integration_bundle", "method": "GET", "endpoint": CANONICAL_INTEGRATION_BUNDLE, "purpose": "bundle"},
                {"key": "providers", "method": "GET", "endpoint": CANONICAL_PROVIDERS, "purpose": "providers"},
                {"key": "mailboxes", "method": "GET", "endpoint": CANONICAL_MAILBOXES, "purpose": "mailboxes"},
                {"key": "openapi", "method": "GET", "endpoint": CANONICAL_OPENAPI, "purpose": "openapi"},
            ],
            "recommendations": [
                {"key": "generate_client", "priority": "low", "label": "Generate client", "endpoint": CANONICAL_OPENAPI}
            ],
            "action_plan": {
                "version": 1,
                "status": "ready",
                "summary": {"total": 3, "blocking": 0, "high": 2, "medium": 1, "low": 0},
                "items": [
                    {
                        "key": "run_smoke_check",
                        "priority": "high",
                        "status": "ready",
                        "blocking": False,
                        "title": "Run the read-only smoke check",
                        "detail": "Validate discovery before mutating mailbox state.",
                        "endpoint": CANONICAL_INTEGRATION_BUNDLE,
                        "command": "OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
                        "docs": "docs/external-integration-quickstart.md",
                    },
                    {
                        "key": "generate_client",
                        "priority": "medium",
                        "status": "ready",
                        "blocking": False,
                        "title": "Generate or refresh the external client",
                        "detail": "Use OpenAPI after smoke checks pass.",
                        "endpoint": CANONICAL_OPENAPI,
                        "docs": "docs/external-integration-quickstart.md",
                    },
                    {
                        "key": "start_mailbox_session",
                        "priority": "high",
                        "status": "ready",
                        "blocking": False,
                        "title": "Start a provider-neutral mailbox session",
                        "detail": "Use mailbox sessions over provider-specific lifecycles.",
                        "endpoint": CANONICAL_SESSION_START,
                        "docs": "docs/external-integration-quickstart.md",
                    },
                ],
            },
        },
    }


def _valid_smoke_results() -> list[external_api_smoke.CheckResult]:
    return external_api_smoke.validate_contracts(
        health_payload=_health_payload(),
        capabilities_payload=_capabilities_payload(),
        integration_bundle_payload=_integration_bundle_payload(),
        providers_payload=_providers_payload(),
        mailboxes_payload=_mailboxes_payload(),
        openapi_payload=_openapi_payload(),
    )


class ExternalApiSmokeScriptTests(unittest.TestCase):
    def test_main_defaults_to_text_output(self):
        results = [external_api_smoke.CheckResult(True, "health", "health endpoint returned service data")]
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch.object(external_api_smoke, "run_smoke", return_value=results) as run_smoke:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = external_api_smoke.main(["--base-url", "https://mailbox.example.test", "--api-key", "test-key"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("OK health: health endpoint returned service data", stdout.getvalue())
        run_smoke.assert_called_once_with(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            timeout=10.0,
        )

    def test_main_json_success_output_reports_totals_and_endpoints(self):
        results = _valid_smoke_results()
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch.object(external_api_smoke, "run_smoke", return_value=results):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = external_api_smoke.main(
                    ["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "--format", "json"]
                )

        report = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertTrue(report["success"])
        self.assertEqual(report["total"], len(results))
        self.assertEqual(report["passed"], len(results))
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["endpoints"], external_api_smoke.smoke_endpoints())
        self.assertEqual(report["endpoints"]["mailboxes"], f"{CANONICAL_MAILBOXES}?page_size=1")
        self.assertEqual(report["endpoints"]["openapi"], CANONICAL_OPENAPI)

    def test_main_json_failure_output_lists_failed_checks(self):
        openapi = _openapi_payload()
        del openapi["components"]["schemas"]["MailboxSessionData"]
        results = external_api_smoke.validate_contracts(
            health_payload=_health_payload(),
            capabilities_payload=_capabilities_payload(),
            integration_bundle_payload=_integration_bundle_payload(),
            providers_payload=_providers_payload(),
            mailboxes_payload=_mailboxes_payload(),
            openapi_payload=openapi,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch.object(external_api_smoke, "run_smoke", return_value=results):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = external_api_smoke.main(
                    ["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "--format", "json"]
                )

        report = json.loads(stdout.getvalue())
        failure_names = {failure["name"] for failure in report["failures"]}
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(report["success"])
        self.assertGreater(report["failed"], 0)
        self.assertEqual(report["failed"], len(report["failures"]))
        self.assertIn("openapi.schema.MailboxSessionData", failure_names)

    def test_main_json_smoke_error_writes_parseable_stderr(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch.object(external_api_smoke, "run_smoke", side_effect=external_api_smoke.SmokeError("boom")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = external_api_smoke.main(
                    ["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "--format", "json"]
                )

        report = json.loads(stderr.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(report["success"])
        self.assertEqual(report["code"], "SMOKE_ERROR")
        self.assertEqual(report["message"], "boom")
        self.assertEqual(report["endpoints"], external_api_smoke.smoke_endpoints())

    def test_run_smoke_succeeds_with_required_discovery_contracts(self):
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }
        seen_paths = []

        def fetcher(base_url: str, api_key: str, path: str) -> dict:
            self.assertEqual(base_url, "https://mailbox.example.test")
            self.assertEqual(api_key, "test-key")
            seen_paths.append(path)
            return payloads[path]

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=fetcher,
        )

        self.assertTrue(results)
        self.assertTrue(all(result.ok for result in results), [result for result in results if not result.ok])
        self.assertEqual(
            seen_paths,
            [
                f"{CANONICAL_EXTERNAL_PREFIX}/health",
                f"{CANONICAL_EXTERNAL_PREFIX}/capabilities",
                f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle",
                f"{CANONICAL_EXTERNAL_PREFIX}/providers",
                f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1",
                f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json",
            ],
        )

    def test_run_smoke_reports_missing_openapi_schema(self):
        openapi = _openapi_payload()
        del openapi["components"]["schemas"]["MailboxSessionData"]
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": openapi,
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("openapi.schema.MailboxSessionData", failures)

    def test_run_smoke_reports_missing_provider_routing_matrix(self):
        providers = _providers_payload()
        del providers["data"]["readiness_summary"]["routing_matrix"]
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": providers,
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("providers.routing_matrix.version", failures)

    def test_run_smoke_reports_missing_mailbox_routing_matrix(self):
        mailboxes = _mailboxes_payload()
        del mailboxes["data"]["provider_context"]["readiness_summary"]["routing_matrix"]
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": mailboxes,
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("mailboxes.routing_matrix.version", failures)

    def test_run_smoke_reports_missing_health_readiness(self):
        health = _health_payload()
        del health["data"]["readiness"]
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": health,
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("health.readiness", failures)

    def test_run_smoke_reports_provider_preflight_endpoint_drift(self):
        capabilities = _capabilities_payload()
        capabilities["data"]["endpoints"]["provider_preflight"] = "/api/external/providers/preflight"
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": capabilities,
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("endpoints.provider_preflight", failures)

    def test_run_smoke_reports_missing_integration_bundle_action_plan(self):
        bundle = _integration_bundle_payload()
        del bundle["data"]["action_plan"]
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": bundle,
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("integration_bundle", failures)
        self.assertIn("integration_bundle.action_plan", failures)

    def test_run_smoke_reports_malformed_integration_bundle_action_plan(self):
        bundle = _integration_bundle_payload()
        plan = bundle["data"]["action_plan"]
        plan["summary"]["total"] = 999
        plan["items"][0]["priority"] = "urgent"
        plan["items"][1].pop("detail")
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": bundle,
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("integration_bundle.action_plan.summary", failures)
        self.assertIn("integration_bundle.action_plan.items", failures)

    def test_run_smoke_scans_integration_bundle_action_plan_for_secret_values(self):
        bundle = _integration_bundle_payload()
        bundle["data"]["action_plan"]["items"][0][
            "command"
        ] = "OUTLOOK_EMAIL_PLUS_API_KEY=sk-secret-secret-secret-1234567890 python scripts/external_api_smoke.py --base-url https://example.test"
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": bundle,
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": _providers_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": _mailboxes_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("integration_bundle.action_plan.placeholder_command", failures)
        self.assertIn("secret_scan.discovery_payload", failures)

    def test_run_smoke_scans_provider_and_mailbox_discovery_for_secret_values(self):
        providers = _providers_payload()
        providers["data"]["readiness_summary"]["routing_matrix"]["leaked"] = (
            "dk_" + "1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        mailboxes = _mailboxes_payload()
        mailboxes["data"]["provider_context"]["readiness_summary"]["routing_matrix"]["auth"] = (
            "Bearer " + "secret-token-value-" + "1234567890"
        )
        payloads = {
            f"{CANONICAL_EXTERNAL_PREFIX}/health": _health_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/capabilities": _capabilities_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle": _integration_bundle_payload(),
            f"{CANONICAL_EXTERNAL_PREFIX}/providers": providers,
            f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes?page_size=1": mailboxes,
            f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json": _openapi_payload(),
        }

        results = external_api_smoke.run_smoke(
            base_url="https://mailbox.example.test",
            api_key="test-key",
            fetcher=lambda _base_url, _api_key, path: payloads[path],
        )

        failures = {result.name: result for result in results if not result.ok}
        self.assertIn("secret_scan.discovery_payload", failures)

    def test_run_smoke_requires_api_key(self):
        with self.assertRaises(external_api_smoke.SmokeError):
            external_api_smoke.run_smoke(base_url="https://mailbox.example.test", api_key="", fetcher=lambda *_args: {})


class ExternalApiSmokeScriptIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = import_web_app_module()
        cls.app = cls.module.app

    def setUp(self):
        with self.app.app_context():
            clear_login_attempts()
            from outlook_web.db import get_db
            from outlook_web.repositories import settings as settings_repo

            db = get_db()
            db.execute("DELETE FROM external_api_keys")
            db.execute("DELETE FROM external_api_consumer_usage_daily")
            db.execute("DELETE FROM external_upstream_probes")
            db.execute("DELETE FROM external_probe_cache")
            db.commit()
            settings_repo.set_setting("external_api_key", "smoke-contract-key")

    def test_validate_contracts_accepts_live_external_discovery_payloads(self):
        client = self.app.test_client()
        headers = {"X-API-Key": "smoke-contract-key"}
        paths = {
            "health": external_api_smoke.CANONICAL_HEALTH,
            "capabilities": external_api_smoke.CANONICAL_CAPABILITIES,
            "integration_bundle": external_api_smoke.CANONICAL_INTEGRATION_BUNDLE,
            "providers": external_api_smoke.CANONICAL_PROVIDERS,
            "mailboxes": f"{external_api_smoke.CANONICAL_MAILBOXES}?page_size=1",
            "openapi": external_api_smoke.CANONICAL_OPENAPI,
        }
        payloads = {}
        for name, path in paths.items():
            response = client.get(path, headers=headers)
            self.assertEqual(response.status_code, 200, path)
            payloads[name] = response.get_json()

        results = external_api_smoke.validate_contracts(
            health_payload=payloads["health"],
            capabilities_payload=payloads["capabilities"],
            integration_bundle_payload=payloads["integration_bundle"],
            providers_payload=payloads["providers"],
            mailboxes_payload=payloads["mailboxes"],
            openapi_payload=payloads["openapi"],
        )

        self.assertTrue(all(result.ok for result in results), [result for result in results if not result.ok])


if __name__ == "__main__":
    unittest.main()
