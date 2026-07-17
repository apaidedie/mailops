"""Package facade — re-exports public symbols for stable imports."""

from __future__ import annotations

# Historical unittest.patch target: controllers.system.external_api_service.*
from outlook_web.services import external_api as external_api_service

from .constants import (
    _HEALTHZ_BOOT_ID,
    _LOCAL_DEMO_DB_RELATIVE_PATH,
    _REPO_ROOT,
    _VERSION_CACHE_TTL,
    _version_cache,
    _version_cache_at,
    logger,
)
from .external_docs_api import (
    api_external_account_status,
    api_external_capabilities,
    api_external_docs,
    api_external_integration_bundle,
    api_external_openapi,
)
from .health_api import (
    api_bootstrap,
    api_external_health,
    api_reload_plugins,
    api_system_diagnostics,
    api_system_health,
    api_system_upgrade_status,
    healthz,
)
from .helpers import (
    _safe_demo_workspace_metadata,
    _trigger_docker_api_update,
    _trigger_watchtower_update,
    _version_gt,
    utcnow,
)
from .update_api import (
    api_deployment_info,
    api_test_watchtower,
    api_trigger_update,
    api_version_check,
)

__all__ = [
    "external_api_service",
    "logger",
    "_version_cache",
    "_version_cache_at",
    "_VERSION_CACHE_TTL",
    "_HEALTHZ_BOOT_ID",
    "_REPO_ROOT",
    "_LOCAL_DEMO_DB_RELATIVE_PATH",
    "_safe_demo_workspace_metadata",
    "utcnow",
    "_version_gt",
    "_trigger_watchtower_update",
    "_trigger_docker_api_update",
    "api_bootstrap",
    "api_reload_plugins",
    "healthz",
    "api_system_health",
    "api_system_diagnostics",
    "api_system_upgrade_status",
    "api_external_health",
    "api_version_check",
    "api_trigger_update",
    "api_deployment_info",
    "api_test_watchtower",
    "api_external_capabilities",
    "api_external_integration_bundle",
    "api_external_openapi",
    "api_external_docs",
    "api_external_account_status",
]
