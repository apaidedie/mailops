#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README 视觉资产生成工具：基于本地 demo 栈产出双语 GIF 与区块截图。

前置：
    docker compose -f docker-compose.demo.yml up -d   # 5001 端口

产出：
    img/demo.gif / img/demo-en.gif          首屏演示动图（880px/12fps 调色板优化）
    img/仪表盘.png / img/邮箱界面.png        界面预览区块截图
    img/提取验证码.png / img/设置界面.png
    output/recording-{zh,en}/*.webm         原始录制（可删）

依赖：playwright（含 chromium）、imageio-ffmpeg。
用法：python scripts/record_demo_assets.py [--skip-gifs] [--skip-shots]
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output"
IMG_DIR = ROOT / "img"
DEMO_URL = "http://localhost:5001"

SHOT_PLAN = [
    ("dashboard", "仪表盘.png"),
    ("mailbox", "邮箱界面.png"),
    ("extraction", "提取验证码.png"),
    ("settings", "设置界面.png"),
]


def wait_for_demo(timeout_seconds: int = 60) -> None:
    import urllib.request

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{DEMO_URL}/login", timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(2)
    raise SystemExit(
        "demo stack is not reachable on :5001 — start it with: " "docker compose -f docker-compose.demo.yml up -d"
    )


def record(context_factory, page_flow, lang: str) -> None:
    recording_dir = OUT_DIR / f"recording-{lang}"
    recording_dir.mkdir(parents=True, exist_ok=True)
    with context_factory(recording_dir) as (browser, context):
        page = context.new_page()
        page_flow(page)
        context.close()  # video flushes on close
        browser.close()
        del lang


def capture_screenshots(lang: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            locale="zh-CN" if lang == "zh" else "en-US",
            viewport={"width": 1440, "height": 860},
        )
        page = context.new_page()
        page.set_default_timeout(20000)
        if lang != "zh":
            page.add_init_script("try { localStorage.setItem('ui_language', 'en'); } catch (e) {}")

        page.goto(f"{DEMO_URL}/login")
        time.sleep(1.5)
        page.fill("#password", "demo-admin-123")
        page.click("#loginBtn")
        time.sleep(3)

        page.locator('.nav-item[data-page="dashboard"]').click()
        time.sleep(2.5)
        page.screenshot(path=str(IMG_DIR / "仪表盘.png"))

        page.locator('.nav-item[data-page="mailbox"]').click()
        time.sleep(2.5)
        page.screenshot(path=str(IMG_DIR / "邮箱界面.png"))

        # 钱镜头：点选 duck.demo 并打开邮件预览，亮出验证码提取
        card = page.locator('.unified-mailbox-card[data-email*="duck.demo"]')
        card.click()
        time.sleep(1.2)
        card.get_by_text("预览邮件").or_(card.get_by_text("Preview messages")).first.click()
        page.get_by_text("391247").first.wait_for(timeout=15000)
        time.sleep(0.6)
        page.screenshot(path=str(IMG_DIR / "提取验证码.png"))

        page.locator('.nav-item[data-page="settings"]').click()
        time.sleep(2.2)
        page.screenshot(path=str(IMG_DIR / "设置界面.png"))

        browser.close()


def record_and_convert(lang: str) -> None:
    from playwright.sync_api import sync_playwright

    def context_factory(recording_dir: Path):
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            locale="zh-CN" if lang == "zh" else "en-US",
            viewport={"width": 1440, "height": 860},
            record_video_dir=str(recording_dir),
            record_video_size={"width": 1440, "height": 860},
        )
        return context_manager(pw, browser, context)

    def page_flow(page) -> None:
        page.set_default_timeout(20000)
        if lang != "zh":
            page.add_init_script("try { localStorage.setItem('ui_language', 'en'); } catch (e) {}")
        page.goto(f"{DEMO_URL}/login")
        hold(2.2)
        page.fill("#password", "demo-admin-123")
        page.click("#loginBtn")
        page.wait_for_url(lambda url: url.rstrip("/").endswith(DEMO_URL), timeout=20000)
        hold(3.0)
        page.locator('.nav-item[data-page="mailbox"]').click()
        hold(2.6)
        card = page.locator('.unified-mailbox-card[data-email*="duck.demo"]')
        card.click()
        hold(1.2)
        card.get_by_text("预览邮件").or_(card.get_by_text("Preview messages")).first.click()
        page.get_by_text("391247").first.wait_for(timeout=15000)
        hold(3.4)
        page.locator('.nav-item[data-page="temp-emails"]').click()
        hold(2.8)
        page.locator('.nav-item[data-page="dashboard"]').click()
        hold(3.0)
        page.locator('.nav-item[data-page="settings"]').click()
        hold(2.6)

    record(context_factory, page_flow, lang)

    try:
        import imageio_ffmpeg
    except ImportError:
        raise SystemExit("imageio-ffmpeg is required: pip install imageio imageio-ffmpeg")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    src = sorted((OUT_DIR / f"recording-{lang}").glob("*.webm"))[-1]
    palette = OUT_DIR / f"palette-{lang}.png"
    out = IMG_DIR / f"demo{'-en' if lang == 'en' else ''}.gif"
    subprocess.run(
        [ffmpeg, "-y", "-i", str(src), "-vf", "fps=12,scale=880:-1:flags=lanczos,palettegen=max_colors=200", str(palette)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-i",
            str(palette),
            "-lavfi",
            "fps=12,scale=880:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
            "-loop",
            "0",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    palette.unlink(missing_ok=True)
    print(f"  -> {out.relative_to(ROOT)} ({out.stat().st_size} bytes)")


class context_manager:
    """包一层 sync_playwright 生命周期，让 record() 以 with 形式使用。"""

    def __init__(self, pw, browser, context):
        self._pw = pw
        self._browser = browser
        self._context = context

    def __enter__(self):
        return self._browser, self._context

    def __exit__(self, *exc):
        self._context.close()
        self._browser.close()
        self._pw.stop()
        return False


def hold(seconds: float) -> None:
    time.sleep(seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-gifs", action="store_true", help="只重拍区块截图")
    parser.add_argument("--skip-shots", action="store_true", help="只重录 GIF")
    args = parser.parse_args()

    wait_for_demo()

    if not args.skip_shots:
        print("[1/2] capturing section screenshots (zh)…")
        capture_screenshots("zh")
        for _, filename in SHOT_PLAN:
            print(f"  -> img/{filename}")
    if not args.skip_gifs:
        print("[2/2] recording demo GIFs (zh + en)…")
        for lang in ("zh", "en"):
            print(f"  recording {lang}…")
            record_and_convert(lang)

    print("done. 建议清理：rm -rf output/recording-*")


if __name__ == "__main__":
    main()
