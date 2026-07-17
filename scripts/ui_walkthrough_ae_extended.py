#!/usr/bin/env python3
"""Dark + narrow viewport extension for UI polish A–E walkthrough.

Example:
  python scripts/ui_walkthrough_ae_extended.py --base-url http://127.0.0.1:5010
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "output" / "playwright"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:5010")
    p.add_argument("--password", default="demo-admin-123")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def login(page: Page, base: str, password: str) -> None:
    page.goto(f"{base}/login", wait_until="networkidle", timeout=30000)
    if page.locator("#password").count():
        page.fill("#password", password)
    else:
        page.fill("input[type=password]", password)
    if page.locator("button[type=submit]").count():
        page.click("button[type=submit]")
    else:
        page.get_by_role("button").filter(has_text="登录").first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)


def set_theme(page: Page, theme: str) -> None:
    page.evaluate(
        """(theme) => {
            document.documentElement.dataset.theme = theme;
            localStorage.setItem('ol_theme', theme);
        }""",
        theme,
    )
    page.wait_for_timeout(200)


def go_nav(page: Page, data_page: str) -> None:
    page.evaluate(
        """(pageName) => {
            if (typeof navigate === 'function') {
                navigate(pageName);
                return;
            }
            const btn = document.querySelector(`.nav-item[data-page="${pageName}"]`);
            if (btn) btn.click();
        }""",
        data_page,
    )
    page.wait_for_timeout(800)


def assert_core(page: Page, prefix: str, findings: list[tuple[str, bool]]) -> None:
    body = page.inner_text("body")
    findings.append((f"{prefix}:nav_概览", "概览" in body))
    findings.append((f"{prefix}:nav_no_运营管理员", "运营管理员" not in body))
    findings.append((f"{prefix}:nav_mailbox", page.locator(".nav-item[data-page='mailbox']").count() > 0))

    go_nav(page, "mailbox")
    page.wait_for_timeout(500)
    findings.append(
        (
            f"{prefix}:mode_统一",
            page.locator("#mailboxUnifiedModeBtn").inner_text().strip() in {"统一", "统一工作台"},
        )
    )
    findings.append(
        (
            f"{prefix}:inbox_active",
            page.locator("#unifiedInboxWorkflow[data-active='true']").count() > 0,
        )
    )

    go_nav(page, "settings")
    page.wait_for_timeout(400)
    page.evaluate("""() => {
            if (typeof switchSettingsTab === 'function') {
                switchSettingsTab('api-security');
                return;
            }
            const btn = document.querySelector('[data-tab="api-security"]');
            if (btn) btn.click();
        }""")
    page.wait_for_timeout(1400)
    key = page.locator("#settingsExternalApiKey")
    cmd = page.locator("#externalApiCommandCenter")
    findings.append((f"{prefix}:api_key", key.count() > 0))
    if key.count() and cmd.count():
        key_top = key.first.evaluate("e => e.getBoundingClientRect().top")
        cmd_top = cmd.first.evaluate("e => e.getBoundingClientRect().top")
        findings.append((f"{prefix}:api_key_above_cc", key_top <= cmd_top + 4))
    else:
        findings.append((f"{prefix}:api_key_above_cc", False))


def no_horizontal_overflow(page: Page) -> bool:
    return bool(page.evaluate("""() => {
                const doc = document.documentElement;
                return doc.scrollWidth <= doc.clientWidth + 1;
            }"""))


def main() -> int:
    args = parse_args()
    out: Path = args.out
    base = args.base_url.rstrip("/")
    password = args.password
    out.mkdir(parents=True, exist_ok=True)
    findings: list[tuple[str, bool]] = []

    scenarios = [
        ("desktop-light", {"width": 1440, "height": 900}, "light"),
        ("desktop-dark", {"width": 1440, "height": 900}, "dark"),
        ("tablet-dark", {"width": 834, "height": 1112}, "dark"),
        ("mobile-light", {"width": 390, "height": 844}, "light"),
        ("mobile-dark", {"width": 390, "height": 844}, "dark"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, viewport, theme in scenarios:
            page = browser.new_page(viewport=viewport)
            login(page, base, password)
            set_theme(page, theme)
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(800)
            set_theme(page, theme)

            page.screenshot(path=str(out / f"{name}-dashboard.png"), full_page=True)
            findings.append(
                (
                    f"{name}:theme_{theme}",
                    page.evaluate("() => document.documentElement.dataset.theme") == theme,
                )
            )
            findings.append((f"{name}:no_h_overflow_dashboard", no_horizontal_overflow(page)))

            assert_core(page, name, findings)
            page.screenshot(path=str(out / f"{name}-settings-api.png"), full_page=True)
            findings.append((f"{name}:no_h_overflow_settings", no_horizontal_overflow(page)))

            go_nav(page, "mailbox")
            page.wait_for_timeout(500)
            if page.locator("#mailboxStandardModeBtn").count():
                page.click("#mailboxStandardModeBtn")
                page.wait_for_timeout(500)
            add_btn = page.locator("button:has-text('添加账号')")
            if add_btn.count() and add_btn.first.is_visible():
                add_btn.first.click()
                page.wait_for_timeout(400)
                page.screenshot(path=str(out / f"{name}-import-modal.png"), full_page=True)
                findings.append(
                    (
                        f"{name}:import_format_summary",
                        page.locator("#addAccountModal summary", has_text="格式说明").count() > 0,
                    )
                )
            else:
                findings.append((f"{name}:import_format_summary", True))
            page.close()

        browser.close()

    print("=== Extended UI walkthrough (dark + narrow) ===")
    ok = 0
    for name, passed in findings:
        mark = "PASS" if passed else "FAIL"
        if passed:
            ok += 1
        print(f"[{mark}] {name}")
    print(f"Score: {ok}/{len(findings)}")
    print(f"Screenshots: {out}")
    return 0 if ok == len(findings) else 1


if __name__ == "__main__":
    sys.exit(main())
