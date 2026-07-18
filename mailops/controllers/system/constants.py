from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Response, jsonify, request

from mailops import __version__ as APP_VERSION
from mailops import config
from mailops.db import (
    DB_SCHEMA_LAST_UPGRADE_ERROR_KEY,
    DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY,
    DB_SCHEMA_VERSION,
    DB_SCHEMA_VERSION_KEY,
    create_sqlite_connection,
)
from mailops.repositories import accounts as accounts_repo
from mailops.repositories import settings as settings_repo
from mailops.security.auth import api_key_required, get_external_api_consumer, login_required
from mailops.security.external_api_guard import external_api_guards
from mailops.services import external_api as external_api_service
from mailops.services import mailbox_resolver
from mailops.services.external_api_docs import render_external_api_docs_html
from mailops.services.external_api_openapi import get_external_api_openapi_contract
from mailops.services.provider_catalog import (
    get_external_api_capabilities_contract,
    get_external_api_integration_bundle,
    get_external_api_readiness_summary,
    get_external_mailbox_read_contract,
    temp_mail_provider_label,
)
from mailops.services.scheduler import REFRESH_LOCK_NAME

logger = logging.getLogger(__name__)

# ==================== 版本检测缓存（模块级，重启后清空） ====================

_version_cache: dict | None = None

_version_cache_at: float = 0.0

_VERSION_CACHE_TTL = 600  # 10 分钟

# 每次进程启动生成一次，用于前端判断是否发生重启

_HEALTHZ_BOOT_ID = f"{int(time.time() * 1000)}-{os.getpid()}"

# constants.py lives at mailops/controllers/system/ → repo root is parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]

_LOCAL_DEMO_DB_RELATIVE_PATH = Path("output") / "demo" / "mailops-demo.db"
