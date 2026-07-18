#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deprecated entrypoint shim.

Prefer ``web_mailops_app:app`` / ``python web_mailops_app.py``.
This module re-exports the MailOps app for older Docker/Gunicorn overrides.
"""

from web_mailops_app import *  # noqa: F401,F403
from web_mailops_app import __all__ as _ALL
from web_mailops_app import app, main

__all__ = list(_ALL)
