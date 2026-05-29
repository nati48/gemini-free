"""
Auth helper - opens a real Chromium window via Playwright, lets you sign in to
Google once, then dumps the cookies that gemini-webapi needs to a JSON file.

Run:
    python -m gemini_free.auth

It will:
  1. Launch a visible Chromium window pointed at https://gemini.google.com
  2. Wait for you to log in (you have up to 5 minutes)
  3. Read __Secure-1PSID and __Secure-1PSIDTS from the browser
  4. Save them to cookies.json (path overridable via COOKIES_FILE env)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

COOKIES_FILE = Path(os.getenv("COOKIES_FILE", "cookies.json"))
LOGIN_TIMEOUT_MS = 5 * 60 * 1000  # 5 minutes to log in
REQUIRED_COOKIES = ("__Secure-1PSID", "__Secure-1PSIDTS")


async def grab_cookies() -> dict[str, str]:
    async with async_playwright() as pw:
        print("🚀 Launching Chromium... a window will open shortly.")
        browser = await pw.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")

        print("👉 Please sign in to your Google account in the open window.")
        print("   Waiting for the Gemini app to fully load (chat UI)...")

        try:
            # Wait until we see the actual Gemini chat composer
            await page.wait_for_selector(
                'div[contenteditable="true"], rich-textarea',
                timeout=LOGIN_TIMEOUT_MS,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Timed out waiting for Gemini chat UI: {exc}")
            await browser.close()
            sys.exit(1)

        # Give the page a moment to set all cookies
        await asyncio.sleep(2)

        raw_cookies = await context.cookies("https://gemini.google.com")
        cookie_map = {c["name"]: c["value"] for c in raw_cookies}

        await browser.close()

    missing = [name for name in REQUIRED_COOKIES if not cookie_map.get(name)]
    if missing:
        print(f"❌ Missing required cookies: {missing}")
        print("   Make sure you're really signed in to Gemini, then re-run this.")
        sys.exit(1)

    return {name: cookie_map[name] for name in REQUIRED_COOKIES}


async def main() -> None:
    cookies = await grab_cookies()
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print(f"✅ Saved cookies to {COOKIES_FILE.resolve()}")
    print("   You can now run:  uvicorn gemini_free.server:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
