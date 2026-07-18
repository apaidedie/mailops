"""Compatibility shim — OpenAPI contract lives in ``external_api.openapi``."""

from __future__ import annotations

from mailops.services.external_api.openapi import get_external_api_openapi_contract

__all__ = ["get_external_api_openapi_contract"]
