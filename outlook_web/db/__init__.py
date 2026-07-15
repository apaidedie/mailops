"""Package facade — re-exports public symbols for stable imports."""
from __future__ import annotations

from .constants import (
    DB_SCHEMA_VERSION,
    DB_SCHEMA_VERSION_KEY,
    DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY,
    DB_SCHEMA_LAST_UPGRADE_ERROR_KEY,
)

from .connection import (
    create_sqlite_connection,
    get_db,
    close_db,
    register_db,
)

from .schema import (
    init_db,
)

from .sensitive import (
    migrate_sensitive_data,
)

__all__ = [
    "DB_SCHEMA_VERSION",
    "DB_SCHEMA_VERSION_KEY",
    "DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY",
    "DB_SCHEMA_LAST_UPGRADE_ERROR_KEY",
    "create_sqlite_connection",
    "get_db",
    "close_db",
    "register_db",
    "init_db",
    "migrate_sensitive_data",
]
