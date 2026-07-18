"""Package facade — re-exports public symbols for stable imports."""

from __future__ import annotations

import time

from mailops.repositories.distributed_locks import (
    acquire_distributed_lock,
    release_distributed_lock,
)

from .classify import (
    _classify_refresh_failure,
    _record_invalid_token_failure,
    compute_refresh_lock_ttl_seconds,
    utcnow,
)
from .constants import (
    INVALID_TOKEN_ERROR_KEYWORDS,
    INVALID_TOKEN_FAILED_LIST_LIMIT,
    REFRESH_LOCK_TTL_SECONDS,
    REFRESHABLE_OUTLOOK_ACCOUNT_SELECT,
    REFRESHABLE_OUTLOOK_ACCOUNT_WHERE,
    build_refreshable_outlook_account_where,
    is_refreshable_outlook_account,
)
from .failed import (
    refresh_failed_accounts,
)
from .stream_all import (
    stream_refresh_all_accounts,
)
from .stream_scheduled import (
    stream_trigger_scheduled_refresh,
)
from .stream_selected import (
    stream_refresh_selected_accounts,
)

__all__ = [
    # Module/function shims for historical unittest.patch targets after package split.
    "time",
    "acquire_distributed_lock",
    "release_distributed_lock",
    "REFRESH_LOCK_TTL_SECONDS",
    "build_refreshable_outlook_account_where",
    "REFRESHABLE_OUTLOOK_ACCOUNT_WHERE",
    "REFRESHABLE_OUTLOOK_ACCOUNT_SELECT",
    "is_refreshable_outlook_account",
    "INVALID_TOKEN_FAILED_LIST_LIMIT",
    "INVALID_TOKEN_ERROR_KEYWORDS",
    "_classify_refresh_failure",
    "_record_invalid_token_failure",
    "utcnow",
    "compute_refresh_lock_ttl_seconds",
    "stream_refresh_all_accounts",
    "stream_trigger_scheduled_refresh",
    "stream_refresh_selected_accounts",
    "refresh_failed_accounts",
]
