#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tag(filename: str, *, first: bool = False) -> str:
    indent = "" if first else "    "
    return (
        f"{indent}<script src=\"{{{{ url_for('static', filename='{filename}') }}}}"
        f"?v={{{{ APP_VERSION }}}}\"></script>"
    )


def pkg_tags(rel_dir: str, *, first: bool = False) -> list[str]:
    order = json.loads((ROOT / rel_dir / "_load_order.json").read_text(encoding="utf-8"))
    # static/js/foo -> js/foo
    prefix = rel_dir.replace("\\", "/").removeprefix("static/")
    out: list[str] = []
    for i, name in enumerate(order):
        out.append(tag(f"{prefix}/{name}", first=first and i == 0))
    return out


def main() -> None:
    lines: list[str] = []
    # i18n stays monofile (large translation map + IIFE-friendly layout).
    lines.append(tag("js/i18n.js", first=True))
    lines.extend(pkg_tags("static/js/core/state"))
    for f in ("js/core/poll-ui.js", "js/core/nav.js", "js/core/http.js", "js/core/utils.js"):
        lines.append(tag(f))
    lines.extend(pkg_tags("static/js/core/settings"))
    lines.extend(pkg_tags("static/js/core/admin"))
    for f in ("js/features/poll-engine.js", "js/features/mailbox_compact.js"):
        lines.append(tag(f))
    lines.extend(pkg_tags("static/js/features/groups"))
    lines.extend(pkg_tags("static/js/features/temp_emails"))
    lines.extend(pkg_tags("static/js/features/accounts"))
    lines.extend(pkg_tags("static/js/features/mailboxes"))
    lines.extend(pkg_tags("static/js/features/overview"))
    lines.append(tag("js/features/pool_admin.js"))
    lines.extend(pkg_tags("static/js/features/emails"))
    lines.append(tag("js/features/plugins.js"))
    (ROOT / "templates/partials/scripts.html").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote scripts.html ({len(lines)} tags)")


if __name__ == "__main__":
    main()
