#!/usr/bin/env python3
"""
Headless Mode Test Script
Verify browser automation works correctly in headless mode
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ["HEADLESS"] = "True"  # Force headless mode

from patchright.async_api import async_playwright
from security.session_manager import SecureSessionManager


async def test_headless_browser():
    """Test basic headless browser functionality"""

    print("=" * 60)
    print("HEADLESS MODE TEST")
    print("=" * 60)

    async with async_playwright() as p:
        # ====================
        # TEST 1: Browser Launch
        # ====================
        print("\n🚀 TEST 1: Launching headless browser...")

        try:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--window-size=1920,1080',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            print("✅ Browser launched successfully")
        except Exception as e:
            print(f"❌ Browser launch failed: {e}")
            return False

        # ====================
        # TEST 2: Context and Page
        # ====================
        print("\n📄 TEST 2: Creating context and page...")

        try:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                locale="ko-KR",
                timezone_id="Asia/Seoul"
            )
            page = await context.new_page()
            print("✅ Context and page created")
        except Exception as e:
            print(f"❌ Context creation failed: {e}")
            await browser.close()
            return False

        # ====================
        # TEST 3: Navigate to Naver
        # ====================
        print("\n🌐 TEST 3: Navigating to Naver Blog...")

        try:
            await page.goto("https://blog.naver.com", wait_until="networkidle")
            print(f"✅ Navigation successful")
            print(f"   Page title: {await page.title()}")
            print(f"   URL: {page.url}")
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            await browser.close()
            return False

        # ====================
        # TEST 4: Session Loading
        # ====================
        print("\n🔐 TEST 4: Testing session load...")

        session_name = "wncksdid0750_clipboard"
        session_file = Path(f"data/sessions/{session_name}.session.encrypted")

        if session_file.exists():
            try:
                manager = SecureSessionManager()
                session_data = manager.load_session(session_name)

                # Apply session
                await context.add_cookies(session_data["cookies"])

                # Test if logged in
                await page.goto("https://blog.naver.com", wait_until="networkidle")
                await asyncio.sleep(2)

                # Check for profile icon (login indicator)
                profile_selectors = [
                    'a[class*="profile"]',
                    'button[class*="profile"]',
                    '.area_profile',
                ]

                logged_in = False
                for selector in profile_selectors:
                    if await page.locator(selector).count() > 0:
                        logged_in = True
                        break

                if logged_in:
                    print("✅ Session loaded - Logged in successfully")
                else:
                    print("⚠️  Session loaded but login status unclear")

            except Exception as e:
                print(f"❌ Session load failed: {e}")
        else:
            print(f"⚠️  Session file not found: {session_file}")
            print(f"   Run: python manual_login_clipboard.py")

        # ====================
        # TEST 5: Screenshot Test
        # ====================
        print("\n📸 TEST 5: Taking screenshot...")

        try:
            screenshot_path = "logs/headless_test.png"
            Path("logs").mkdir(exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"✅ Screenshot saved: {screenshot_path}")
        except Exception as e:
            print(f"❌ Screenshot failed: {e}")

        # ====================
        # TEST 6: Element Finding
        # ====================
        print("\n🔍 TEST 6: Testing element selectors...")

        try:
            # Test finding common elements
            test_selectors = [
                ('body', 'Page body'),
                ('a', 'Links'),
                ('button', 'Buttons'),
            ]

            for selector, name in test_selectors:
                count = await page.locator(selector).count()
                print(f"   {name}: {count} found")

            print("✅ Element finding works correctly")
        except Exception as e:
            print(f"❌ Element finding failed: {e}")

        # Cleanup
        await browser.close()

        print("\n" + "=" * 60)
        print("HEADLESS MODE TEST COMPLETE")
        print("=" * 60)

        return True


if __name__ == "__main__":
    success = asyncio.run(test_headless_browser())
    sys.exit(0 if success else 1)
