from __future__ import annotations

import sys
from typing import Any


def configure_process_output() -> None:
    """Keep console output safe when Windows redirects logs through a legacy code page."""

    for stream_name in ("stdout", "stderr"):
        stream: Any = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except TypeError:
            reconfigure(errors="replace")
        except Exception:
            continue
