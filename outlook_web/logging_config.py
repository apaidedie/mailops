from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import IO, Any

from flask import Flask, g, has_request_context, request
from flask.logging import default_handler

from outlook_web import config

_MANAGED_HANDLER_ATTR = "_outlook_web_managed"
_SAFE_EXTRA_FIELDS = (
    "event",
    "code",
    "status",
    "status_code",
    "duration_ms",
    "provider",
    "endpoint",
    "action",
    "resource_type",
    "resource_id",
)


def _utc_timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_scalar(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _enrich_request_context(record: logging.LogRecord) -> None:
    if not has_request_context():
        return
    if not getattr(record, "trace_id", None):
        record.trace_id = getattr(g, "trace_id", None)
    if not getattr(record, "http_method", None):
        record.http_method = request.method
    if not getattr(record, "http_path", None):
        record.http_path = request.path
    if not getattr(record, "remote_addr", None):
        record.remote_addr = request.remote_addr


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        _enrich_request_context(record)
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        _enrich_request_context(record)
        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process": record.process,
            "thread": record.thread,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        for field in ("trace_id", "http_method", "http_path", "remote_addr", *_SAFE_EXTRA_FIELDS):
            value = getattr(record, field, None)
            if value not in (None, ""):
                payload[field] = _safe_scalar(value)
        if record.exc_info:
            exception_type = record.exc_info[0]
            exception_value = record.exc_info[1]
            payload["exception"] = {
                "type": exception_type.__name__ if exception_type else "Exception",
                "message": str(exception_value or ""),
                "stack": self.formatException(record.exc_info),
            }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _build_formatter(log_format: str) -> logging.Formatter:
    if log_format == "json":
        return JsonLogFormatter()
    return logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S")


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _MANAGED_HANDLER_ATTR, False):
            logger.removeHandler(handler)
            handler.close()


def configure_runtime_logging(
    app: Flask,
    *,
    stream: IO[str] | None = None,
    log_format: str | None = None,
    log_level: str | None = None,
) -> logging.Handler:
    resolved_format = (log_format or config.get_log_format()).strip().lower()
    if resolved_format not in {"text", "json"}:
        resolved_format = "text"
    resolved_level = (log_level or config.get_log_level()).strip().upper()
    level = getattr(logging, resolved_level, logging.INFO)

    handler = logging.StreamHandler(stream or sys.stderr)
    setattr(handler, _MANAGED_HANDLER_ATTR, True)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(_build_formatter(resolved_format))

    namespace_logger = logging.getLogger("outlook_web")
    _remove_managed_handlers(namespace_logger)
    namespace_logger.addHandler(handler)
    namespace_logger.setLevel(level)
    namespace_logger.propagate = False

    _remove_managed_handlers(app.logger)
    if default_handler in app.logger.handlers:
        app.logger.removeHandler(default_handler)
    app.logger.setLevel(level)
    app.logger.propagate = True
    return handler
