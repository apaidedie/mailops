from __future__ import annotations

import copy
from typing import Any

from outlook_web import __version__ as APP_VERSION
from outlook_web.services.external_request_limits import (
    CALLER_ID_MAX_LEN,
    DETAIL_MAX_LEN,
    EMAIL_DOMAIN_MAX_LEN,
    PROJECT_KEY_MAX_LEN,
    REASON_MAX_LEN,
    TASK_ID_MAX_LEN,
    TASK_MAILBOX_PREFIX_MAX_LEN,
)
from outlook_web.services.mailbox_directory_contract import get_mailbox_catalog_contract
from outlook_web.services.pool import VALID_RESULTS
from outlook_web.services.provider_catalog import EXTERNAL_API_V1_PREFIX, get_external_api_capabilities_contract

from .builders import _error_responses, _operation, _path_param, _query_param


def _paths(capabilities: dict[str, Any]) -> dict[str, Any]:
    endpoints = capabilities.get("endpoints") or {}
    mailbox_contract = get_mailbox_catalog_contract()
    email_query = _query_param("email", {"type": "string"}, required=True)
    claim_token_query = _query_param("claim_token", {"type": "string"}, description="Optional mailbox claim token")
    folder_query = _query_param("folder", {"type": "string", "default": "inbox"})
    return {
        endpoints.get("openapi", f"{EXTERNAL_API_V1_PREFIX}/openapi.json"): {
            "get": {
                "summary": "External API OpenAPI contract",
                "operationId": "externalOpenApi",
                "tags": ["External API"],
                "security": [{"ApiKeyAuth": []}],
                "responses": {
                    "200": {
                        "description": "OpenAPI document",
                        "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
                    },
                    **_error_responses(),
                },
            }
        },
        endpoints.get("docs", f"{EXTERNAL_API_V1_PREFIX}/docs"): {
            "get": {
                "summary": "External API documentation page",
                "operationId": "externalApiDocs",
                "tags": ["External API"],
                "security": [{"ApiKeyAuth": []}],
                "responses": {
                    "200": {
                        "description": "Browser-readable HTML documentation generated from this OpenAPI contract",
                        "content": {"text/html": {"schema": {"type": "string"}}},
                    },
                    **_error_responses(),
                },
            }
        },
        endpoints.get("health", f"{EXTERNAL_API_V1_PREFIX}/health"): _operation(
            method="GET",
            summary="External API health",
            operation_id="externalHealth",
            response_ref="#/components/schemas/HealthData",
        ),
        endpoints.get("capabilities", f"{EXTERNAL_API_V1_PREFIX}/capabilities"): _operation(
            method="GET",
            summary="External API capabilities",
            operation_id="externalCapabilities",
            response_ref="#/components/schemas/CapabilitiesData",
        ),
        endpoints.get("integration_bundle", f"{EXTERNAL_API_V1_PREFIX}/integration-bundle"): _operation(
            method="GET",
            summary="External integration readiness bundle",
            operation_id="externalIntegrationBundle",
            response_ref="#/components/schemas/IntegrationBundleData",
        ),
        endpoints.get("mailboxes", f"{EXTERNAL_API_V1_PREFIX}/mailboxes"): _operation(
            method="GET",
            summary="Unified mailbox directory",
            operation_id="externalMailboxes",
            response_ref="#/components/schemas/UnifiedMailboxDirectory",
            parameters=[
                _query_param("kind", {"type": "string", "enum": list(mailbox_contract["filters"]["kind"]), "default": "all"}),
                _query_param(
                    "status", {"type": "string", "enum": list(mailbox_contract["filters"]["status"]), "default": "all"}
                ),
                _query_param(
                    "read_capability",
                    {"type": "string", "enum": list(mailbox_contract["filters"]["read_capability"]), "default": "all"},
                ),
                _query_param(
                    "action", {"type": "string", "enum": list(mailbox_contract["filters"]["action"]), "default": "all"}
                ),
                _query_param("provider", {"type": "string", "default": "all"}),
                _query_param("search", {"type": "string"}),
                _query_param(
                    "sort",
                    {
                        "type": "string",
                        "enum": list(mailbox_contract["filters"]["sort"]),
                        "default": "updated_desc",
                    },
                ),
                _query_param("page", {"type": "integer", "minimum": 1, "default": 1}),
                _query_param("page_size", {"type": "integer", "minimum": 1, "maximum": 200, "default": 50}),
            ],
        ),
        endpoints.get("providers", f"{EXTERNAL_API_V1_PREFIX}/providers"): _operation(
            method="GET",
            summary="Mailbox provider catalog",
            operation_id="externalProviders",
            response_ref="#/components/schemas/ProviderCatalogData",
        ),
        endpoints.get("provider_preflight", f"{EXTERNAL_API_V1_PREFIX}/providers/preflight"): _operation(
            method="GET",
            summary="Mailbox provider readiness preflight",
            operation_id="externalProviderPreflight",
            response_ref="#/components/schemas/ProviderPreflightData",
            parameters=[_query_param("probe_network", {"type": "boolean", "default": False})],
        ),
        endpoints.get("provider_health", f"{EXTERNAL_API_V1_PREFIX}/providers/{{kind}}/{{provider}}/health"): _operation(
            method="GET",
            summary="Mailbox provider health",
            operation_id="externalProviderHealth",
            response_ref="#/components/schemas/ProviderHealthData",
            parameters=[
                _path_param("kind"),
                _path_param("provider"),
                _query_param("probe_network", {"type": "boolean", "default": False}),
            ],
        ),
        endpoints.get("mailbox_session_start", f"{EXTERNAL_API_V1_PREFIX}/mailbox-sessions/start"): _operation(
            method="POST",
            summary="Start a provider-neutral mailbox session",
            operation_id="externalMailboxSessionStart",
            response_ref="#/components/schemas/MailboxSessionData",
            request_schema_ref="#/components/schemas/MailboxSessionStartRequest",
        ),
        endpoints.get("mailbox_session_read", f"{EXTERNAL_API_V1_PREFIX}/mailbox-sessions/read"): _operation(
            method="POST",
            summary="Read a provider-neutral mailbox session",
            operation_id="externalMailboxSessionRead",
            response_ref="#/components/schemas/MailboxSessionReadData",
            request_schema_ref="#/components/schemas/MailboxSessionReadRequest",
        ),
        endpoints.get("mailbox_session_close", f"{EXTERNAL_API_V1_PREFIX}/mailbox-sessions/close"): _operation(
            method="POST",
            summary="Close a provider-neutral mailbox session",
            operation_id="externalMailboxSessionClose",
            response_ref="#/components/schemas/MailboxSessionCloseData",
            request_schema_ref="#/components/schemas/MailboxSessionCloseRequest",
        ),
        endpoints.get("account_status", f"{EXTERNAL_API_V1_PREFIX}/account-status"): _operation(
            method="GET",
            summary="Mailbox status",
            operation_id="externalAccountStatus",
            response_ref="#/components/schemas/AccountStatusData",
            parameters=[email_query],
        ),
        endpoints.get("messages", f"{EXTERNAL_API_V1_PREFIX}/messages"): _operation(
            method="GET",
            summary="List mailbox messages",
            operation_id="externalMessages",
            response_ref="#/components/schemas/MessagesData",
            parameters=[
                email_query,
                claim_token_query,
                folder_query,
                _query_param("skip", {"type": "integer", "minimum": 0}),
                _query_param("top", {"type": "integer", "minimum": 1, "maximum": 50}),
            ],
        ),
        endpoints.get("latest_message", f"{EXTERNAL_API_V1_PREFIX}/messages/latest"): _operation(
            method="GET",
            summary="Read latest matching message",
            operation_id="externalLatestMessage",
            response_ref="#/components/schemas/MessageSummary",
            parameters=[
                email_query,
                claim_token_query,
                folder_query,
                _query_param("from_contains", {"type": "string"}),
                _query_param("subject_contains", {"type": "string"}),
            ],
        ),
        endpoints.get("message_detail", f"{EXTERNAL_API_V1_PREFIX}/messages/{{message_id}}"): _operation(
            method="GET",
            summary="Read message detail",
            operation_id="externalMessageDetail",
            response_ref="#/components/schemas/MessageDetail",
            parameters=[_path_param("message_id"), email_query, claim_token_query, folder_query],
        ),
        endpoints.get("message_raw", f"{EXTERNAL_API_V1_PREFIX}/messages/{{message_id}}/raw"): _operation(
            method="GET",
            summary="Read raw message content",
            operation_id="externalMessageRaw",
            response_ref="#/components/schemas/RawMessageData",
            parameters=[_path_param("message_id"), email_query, claim_token_query, folder_query],
        ),
        endpoints.get("verification_code", f"{EXTERNAL_API_V1_PREFIX}/verification-code"): _operation(
            method="GET",
            summary="Extract verification code",
            operation_id="externalVerificationCode",
            response_ref="#/components/schemas/VerificationResult",
            parameters=[
                email_query,
                claim_token_query,
                folder_query,
                _query_param("code_length", {"type": "string"}),
                _query_param("code_regex", {"type": "string"}),
            ],
        ),
        endpoints.get("verification_link", f"{EXTERNAL_API_V1_PREFIX}/verification-link"): _operation(
            method="GET",
            summary="Extract verification link",
            operation_id="externalVerificationLink",
            response_ref="#/components/schemas/VerificationResult",
            parameters=[email_query, claim_token_query, folder_query],
        ),
        endpoints.get("wait_message", f"{EXTERNAL_API_V1_PREFIX}/wait-message"): _operation(
            method="GET",
            summary="Wait for a matching message",
            operation_id="externalWaitMessage",
            response_ref="#/components/schemas/MessageSummary",
            parameters=[
                email_query,
                claim_token_query,
                folder_query,
                _query_param("timeout_seconds", {"type": "integer", "minimum": 1, "maximum": 120}),
                _query_param("mode", {"type": "string", "enum": ["sync", "async"]}),
            ],
        ),
        endpoints.get("probe_status", f"{EXTERNAL_API_V1_PREFIX}/probe/{{probe_id}}"): _operation(
            method="GET",
            summary="Get async probe status",
            operation_id="externalProbeStatus",
            response_ref="#/components/schemas/ProbeStatusData",
            parameters=[_path_param("probe_id")],
        ),
        endpoints.get("pool_claim_random", f"{EXTERNAL_API_V1_PREFIX}/pool/claim-random"): _operation(
            method="POST",
            summary="Claim a mailbox from the pool",
            operation_id="externalPoolClaimRandom",
            response_ref="#/components/schemas/PoolClaimData",
            request_schema_ref="#/components/schemas/PoolClaimRequest",
        ),
        endpoints.get("pool_claim_release", f"{EXTERNAL_API_V1_PREFIX}/pool/claim-release"): _operation(
            method="POST",
            summary="Release a mailbox claim",
            operation_id="externalPoolClaimRelease",
            response_ref="#/components/schemas/PoolLifecycleData",
            request_schema_ref="#/components/schemas/PoolReleaseRequest",
        ),
        endpoints.get("pool_claim_complete", f"{EXTERNAL_API_V1_PREFIX}/pool/claim-complete"): _operation(
            method="POST",
            summary="Complete a mailbox claim",
            operation_id="externalPoolClaimComplete",
            response_ref="#/components/schemas/PoolLifecycleData",
            request_schema_ref="#/components/schemas/PoolCompleteRequest",
        ),
        endpoints.get("pool_stats", f"{EXTERNAL_API_V1_PREFIX}/pool/stats"): _operation(
            method="GET",
            summary="External pool stats",
            operation_id="externalPoolStats",
            response_ref="#/components/schemas/PoolStatsData",
        ),
        endpoints.get("temp_mail_apply", f"{EXTERNAL_API_V1_PREFIX}/temp-emails/apply"): _operation(
            method="POST",
            summary="Create a task-scoped temp mailbox",
            operation_id="externalTempMailApply",
            response_ref="#/components/schemas/TaskTempMailboxData",
            request_schema_ref="#/components/schemas/TaskTempMailboxApplyRequest",
        ),
        endpoints.get("temp_mail_finish", f"{EXTERNAL_API_V1_PREFIX}/temp-emails/{{task_token}}/finish"): _operation(
            method="POST",
            summary="Finish a task-scoped temp mailbox",
            operation_id="externalTempMailFinish",
            response_ref="#/components/schemas/TaskTempMailboxData",
            parameters=[_path_param("task_token")],
            request_schema_ref="#/components/schemas/TaskTempMailboxFinishRequest",
        ),
    }
