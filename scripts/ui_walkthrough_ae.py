#!/usr/bin/env python3
"""Desktop UI smoke walkthrough for MailOps UI polish A–E.

Prereq:
  1) Seed demo DB: python scripts/seed_demo_workspace.py --reset
  2) Start app on BASE_URL with LOGIN_PASSWORD=demo-admin-123
  3) pip install playwright && playwright install chromium

Example:
  python scripts/ui_walkthrough_ae.py --base-url http://127.0.0.1:5010
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "output" / "playwright"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:5010")
    p.add_argument("--password", default="demo-admin-123")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out: Path = args.out
    base = args.base_url.rstrip("/")
    password = args.password
    out.mkdir(parents=True, exist_ok=True)
    findings: list[tuple[str, bool]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(f"{base}/login", wait_until="networkidle", timeout=30000)
        html = page.content()
        findings.append(
            (
                "login_copy_quiet",
                "安全登录" in html and "统一邮箱工作台 · 安全登录" not in html,
            )
        )
        page.screenshot(path=str(out / "01-login.png"), full_page=True)

        if page.locator("#password").count():
            page.fill("#password", password)
        else:
            page.fill("input[type=password]", password)

        if page.locator("button[type=submit]").count():
            page.click("button[type=submit]")
        else:
            page.get_by_role("button").filter(has_text="登录").first.click()

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / "02-dashboard.png"), full_page=True)

        body = page.inner_text("body")
        findings.append(("nav_has_概览", "概览" in body))
        findings.append(("nav_section_邮箱", page.locator(".nav-section", has_text="邮箱").count() > 0))
        findings.append(
            (
                "nav_not_label_统一邮箱",
                page.locator(".nav-item span", has_text="统一邮箱").count() == 0,
            )
        )
        findings.append(("nav_mailbox_item", page.locator(".nav-item[data-page='mailbox']").count() > 0))
        findings.append(("role_not_运营管理员", "运营管理员" not in body))
        findings.append(("topbar_overview", "概览" in page.locator("#topbarTitle").inner_text()))

        page.evaluate("() => typeof navigate === 'function' && navigate('mailbox')")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / "03-mailbox.png"), full_page=True)
        findings.append(("mode_统一", page.locator("#mailboxUnifiedModeBtn").inner_text().strip() == "统一"))
        findings.append(("mode_账号", page.locator("#mailboxStandardModeBtn").inner_text().strip() == "账号"))
        findings.append(("mode_紧凑", page.locator("#mailboxCompactModeBtn").inner_text().strip() == "紧凑"))
        findings.append(
            (
                "unified_inbox_active",
                page.locator("#unifiedInboxWorkflow[data-active='true']").count() > 0,
            )
        )
        findings.append(
            (
                "diagnostics_inactive",
                page.locator("#unifiedDiagnosticsWorkspace[data-active='false']").count() > 0,
            )
        )

        page.click("#mailboxStandardModeBtn")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(out / "04-mailbox-standard.png"), full_page=True)
        findings.append(("standard_layout_visible", page.locator("#mailboxStandardLayout").is_visible()))

        if page.locator("button:has-text('添加账号')").count():
            page.click("button:has-text('添加账号')")
            page.wait_for_timeout(600)
            page.screenshot(path=str(out / "05-import-modal.png"), full_page=True)
            findings.append(
                (
                    "import_format_summary",
                    page.locator("#addAccountModal summary", has_text="格式说明").count() > 0,
                )
            )
            findings.append(("import_account_input", page.locator("#accountInput").count() > 0))
            page.evaluate("""() => {
                    const m = document.getElementById('addAccountModal');
                    if (!m) return;
                    m.style.display = 'none';
                    m.classList.remove('show', 'active');
                }""")

        page.evaluate("() => typeof navigate === 'function' && navigate('temp-emails')")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(out / "06-temp-emails.png"), full_page=True)
        temp_text = page.inner_text("#page-temp-emails")
        findings.append(
            (
                "temp_create_or_list",
                "创建" in temp_text or page.locator("#tempEmailContainer .account-card").count() > 0,
            )
        )

        page.evaluate("""() => {
                if (typeof navigate === 'function') navigate('settings');
                if (typeof switchSettingsTab === 'function') switchSettingsTab('api-security');
            }""")
        page.wait_for_timeout(1800)
        page.screenshot(path=str(out / "07-settings-api.png"), full_page=True)

        key = page.locator("#settingsExternalApiKey")
        cmd = page.locator("#externalApiCommandCenter")
        findings.append(("api_key_present", key.count() > 0))
        if key.count() and cmd.count():
            key_top = key.first.evaluate("e => e.getBoundingClientRect().top")
            cmd_top = cmd.first.evaluate("e => e.getBoundingClientRect().top")
            findings.append(("api_key_above_command_center", key_top <= cmd_top + 2))
        else:
            findings.append(("api_key_above_command_center", False))

        findings.append(("multi_key_summary", page.locator("summary", has_text="多 Key 配置").count() > 0))
        findings.append(
            (
                "provider_diag_summary",
                page.locator("summary", has_text="邮箱来源与诊断").count() > 0,
            )
        )
        findings.append(
            (
                "advanced_tools_present",
                "高级工具" in page.content() or page.locator("summary.external-api-advanced-tools-summary").count() > 0,
            )
        )

        browser.close()

    print("=== UI walkthrough findings ===")
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
