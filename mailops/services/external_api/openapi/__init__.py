"""Package facade — re-exports public symbols for stable imports."""

from __future__ import annotations

from .builders import (
    _envelope_ref,
    _error_responses,
    _json_response,
    _json_value_schema,
    _nullable_string_enum_schema,
    _operation,
    _path_param,
    _query_param,
    _string_array_schema,
)
from .contract import (
    get_external_api_openapi_contract,
)
from .paths import (
    _paths,
)
from .schemas import (
    _schemas,
)

__all__ = [
    "_envelope_ref",
    "_json_response",
    "_error_responses",
    "_query_param",
    "_path_param",
    "_string_array_schema",
    "_nullable_string_enum_schema",
    "_json_value_schema",
    "_operation",
    "_schemas",
    "_paths",
    "get_external_api_openapi_contract",
]
