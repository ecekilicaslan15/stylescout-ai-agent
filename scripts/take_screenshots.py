#!/usr/bin/env python3
"""Capture portfolio screenshots at 1440×900 via Playwright.

Requires: pip install playwright && playwright install chromium

By default this script copies ``wardrobe/wardrobe.json`` into ``data/screenshot_runtime/``
(gitignored), starts uvicorn against that copy (so ``sess_*`` clones never touch the
committed seed file), captures PNGs, then stops the server.

  python scripts/take_screenshots.py

To use an already-running server instead:

  SKIP_SCREENSHOT_SERVER=1 python scripts/take_screenshots.py

Optional isolated demo DB (15 fictional items) — separate from committed wardrobe:

  python scripts/seed_portfolio_demo.py
  ALLOW_DEFAULT_OVERRIDE=true WARDROBE_BACKEND=sqlite DB_PATH=data/portfolio_demo.db \\
    uvicorn api.main:app --host 127.0.0.1 --port 8000
  USE_DEMO_COOKIE=1 SKIP_SCREENSHOT_SERVER=1 python scripts/take_screenshots.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "screenshots"
RUNTIME_DIR = ROOT / "data" / "screenshot_runtime"
COMMITTED_WARDROBE = ROOT / "wardrobe" / "wardrobe.json"
BASE_URL = os.getenv("SCREENSHOT_BASE_URL", "http://127.0.0.1:8000")
VIEWPORT = {"width": 1440, "height": 900}

MODES = [
    ("my_wardrobe", "03-outfit-my-wardrobe.png"),
    ("wardrobe_plus_ai", "04-outfit-wardrobe-plus-ai.png"),
    ("ai_inspiration", "05-outfit-ai-inspiration.png"),
]


def _prepare_runtime_wardrobe_copy() -> None:
    """Copy committed seed JSON into gitignored runtime dir for screenshot sessions."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(COMMITTED_WARDROBE, RUNTIME_DIR / "wardrobe.json")
    saved = RUNTIME_DIR / "saved_outfits.json"
    prefs = RUNTIME_DIR / "preferences.json"
    if not saved.exists():
        saved.write_text("[]", encoding="utf-8")
    if not prefs.exists():
        prefs.write_text("{}", encoding="utf-8")


def _wait_for_health(url: str, timeout_sec: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Server not healthy at {url}: {last_error}")


def _start_isolated_server() -> subprocess.Popen:
    _prepare_runtime_wardrobe_copy()
    env = os.environ.copy()
    env["WARDROBE_BACKEND"] = "json"
    env["WARDROBE_JSON_PATH"] = str(RUNTIME_DIR / "wardrobe.json")
    env["SAVED_OUTFITS_JSON_PATH"] = str(RUNTIME_DIR / "saved_outfits.json")
    env["PREFERENCES_JSON_PATH"] = str(RUNTIME_DIR / "preferences.json")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    _wait_for_health(f"{BASE_URL.rstrip('/')}/health")
    return proc


def _capture_screenshots(failed_images: list[str]) -> None:
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        if os.getenv("USE_DEMO_COOKIE") == "1":
            context.add_cookies(
                [{"name": "stylescout_session", "value": "default", "url": BASE_URL}]
            )
        page = context.new_page()
        page.emulate_media(reduced_motion="reduce")

        page.goto(BASE_URL, wait_until="networkidle")
        page.screenshot(path=str(OUT_DIR / "01-home.png"), full_page=False)

        page.get_by_role("button", name="Open my wardrobe").first.click()
        page.wait_for_selector("#app.visible", timeout=15000)
        page.wait_for_function(
            """() => {
              const count = document.getElementById('count')?.textContent || '';
              if (count.includes('Could not load')) return false;
              const empty = document.getElementById('empty');
              if (empty?.classList.contains('show')) return false;
              return document.querySelectorAll('.gcard').length > 0;
            }""",
            timeout=20000,
        )
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_function(
            """() => {
              const imgs = [...document.querySelectorAll('.gcard img')];
              if (!imgs.length) return false;
              return imgs.every(img => img.complete && img.naturalWidth > 0);
            }""",
            timeout=30000,
        )
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT_DIR / "02-wardrobe.png"), full_page=False)

        broken = page.evaluate(
            """() => {
              const bad = [];
              document.querySelectorAll('.gcard img').forEach(img => {
                if (!img.complete || img.naturalWidth === 0) {
                  bad.push((img.alt || 'unknown') + ' | ' + (img.src || ''));
                }
              });
              return bad;
            }"""
        )
        failed_images.extend(broken)

        for mode, filename in MODES:
            page.locator(f'button.mode[data-mode="{mode}"]').click()
            page.wait_for_timeout(150)
            page.locator("#prompt").fill("Smart casual outfit for dinner")
            page.locator(".prompt-send").click()
            page.wait_for_selector("#boardWrap.show", timeout=30000)
            page.wait_for_function(
                """() => {
                  const empty = document.getElementById('outfitEmpty');
                  if (empty && !empty.hidden) return false;
                  return document.querySelectorAll('.bg-item').length > 0;
                }""",
                timeout=30000,
            )
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT_DIR / filename), full_page=False)
            page.locator(".session-close").click()
            page.wait_for_timeout(500)

        browser.close()


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("Install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    failed_images: list[str] = []
    server: subprocess.Popen | None = None
    manage_server = os.getenv("SKIP_SCREENSHOT_SERVER") != "1"

    try:
        if manage_server:
            server = _start_isolated_server()
        _capture_screenshots(failed_images)
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    print(f"Saved screenshots to {OUT_DIR}")
    for path in sorted(OUT_DIR.glob("*.png")):
        print(f"  - {path.name}")

    unique_failures = sorted(set(failed_images))
    if unique_failures:
        print("\nImage load issues detected:")
        for entry in unique_failures:
            print(f"  - {entry}")
        return 2

    print("\nAll checked wardrobe card images loaded.")
    if manage_server:
        print(f"Session data written only under {RUNTIME_DIR} (not committed wardrobe.json).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
