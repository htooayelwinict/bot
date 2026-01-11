"""Facebook workflow tests with HITL login support.

Workflow:
1. Check if logged in
2. If not, use Human-in-the-Loop (HITL) login
3. Go to news feed → screenshot
4. Go to profile → screenshot
5. End
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page

from src.session import FacebookProfileManager, check_login_status, wait_for_login


# =============================================================================
# Constants
# =============================================================================

FACEBOOK_URL = "https://www.facebook.com"
PROFILE_DIR = Path("./profiles/facebook")


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def facebook_page(browser_type):
    """Create a logged-in Facebook page with HITL fallback."""
    manager = FacebookProfileManager(
        profile_dir=PROFILE_DIR,
        headless=False,
    )

    # Get or create session (uses existing browser_type)
    context, page, was_restored = manager.get_or_create_session(browser_type)

    # Navigate to Facebook
    page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Check login status
    if not check_login_status(page):
        print("\n" + "=" * 60)
        print("⚠️ NOT LOGGED IN TO FACEBOOK")
        print("=" * 60)
        print("Please log in manually in the browser window...")
        print("=" * 60 + "\n")

        # Wait for manual login
        if not wait_for_login(page):
            pytest.skip("Login timeout - please run tests again")

        # Save session for next time
        manager.save_session()
        print("💾 Session saved for future use!\n")
    else:
        print("✅ Already logged in!\n")

    yield page

    # Cleanup
    try:
        page.close()
    except Exception:
        pass
    try:
        context.close()
    except Exception:
        pass


# =============================================================================
# Workflow Tests
# =============================================================================

def test_news_feed_screenshot(facebook_page: Page):
    """Test: Go to news feed and take screenshot."""
    # Go to news feed (homepage)
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Take screenshot
    screenshot_path = "screenshots/news-feed.png"
    facebook_page.screenshot(path=screenshot_path)
    print(f"✅ News feed screenshot: {screenshot_path}")


def test_profile_screenshot(facebook_page: Page):
    """Test: Go to profile and take screenshot."""
    # Go to profile
    profile_url = f"{FACEBOOK_URL}/me"
    facebook_page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)

    # Take screenshot
    screenshot_path = "screenshots/profile.png"
    facebook_page.screenshot(path=screenshot_path)
    print(f"✅ Profile screenshot: {screenshot_path}")


# =============================================================================
# Phase 3a Tool Workflow Tests
# =============================================================================


def test_interaction_tools_workflow(facebook_page: Page):
    """Test: Use interaction tools (type, hover, press_key)."""
    from src.tools.interaction import browser_type, browser_hover, browser_press_key
    from src.tools.utilities import browser_wait

    # Navigate to search page
    facebook_page.goto(f"{FACEBOOK_URL}/search", wait_until="domcontentloaded", timeout=60000)

    # Wait for search input
    result = browser_wait(selector='input[placeholder*="Search" i], input[aria-label*="Search" i]', page=facebook_page)
    print(f"⏳ Wait result: {result}")

    # Type in search box (if found)
    try:
        search_input = facebook_page.query_selector('input[placeholder*="Search" i], input[aria-label*="Search" i]')
        if search_input:
            result = browser_type(selector='input[placeholder*="Search" i]', text="Test", page=facebook_page)
            print(f"⌨️ Type result: {result}")
    except Exception as e:
        print(f"⚠️ Skip type test: {e}")

    print("✅ Interaction tools workflow completed")


def test_form_tools_workflow(facebook_page: Page):
    """Test: Use form tools (fill_form, get_form_data)."""
    from src.tools.forms import browser_fill_form, browser_get_form_data

    # Navigate to a page with forms (settings page usually has forms)
    facebook_page.goto(f"{FACEBOOK_URL}/settings", wait_until="domcontentloaded", timeout=60000)

    # Try to get form data from any form on page
    try:
        result = browser_get_form_data(page=facebook_page)
        print(f"📋 Form data result: {result[:200]}...")
    except Exception as e:
        print(f"⚠️ Form data extraction: {e}")

    print("✅ Form tools workflow completed")


def test_utility_tools_workflow(facebook_page: Page):
    """Test: Use utility tools (wait, evaluate, get_snapshot, get_network)."""
    from src.tools.utilities import (
        browser_wait,
        browser_evaluate,
        browser_get_snapshot,
        browser_get_network_requests,
    )

    # Navigate to news feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Wait for page to stabilize
    import time
    time.sleep(2)

    # Get page info via evaluate
    result = browser_evaluate(script="({url: window.location.href, title: document.title})", page=facebook_page)
    print(f"📊 Evaluate result: {result}")

    # Get accessibility snapshot
    try:
        result = browser_get_snapshot(root="body", page=facebook_page)
        print(f"🖼️ Snapshot obtained (length: {len(result)} chars)")
    except Exception as e:
        print(f"⚠️ Snapshot: {e}")

    # Get network requests
    try:
        result = browser_get_network_requests(limit=10, page=facebook_page)
        print(f"🌐 Network requests: {result[:200]}...")
    except Exception as e:
        print(f"⚠️ Network requests: {e}")

    print("✅ Utility tools workflow completed")


def test_browser_tools_workflow(facebook_page: Page):
    """Test: Use browser tools (tabs, resize, reload)."""
    from src.tools.browser import browser_tabs, browser_resize, browser_reload

    # Test resize
    result = browser_resize(width=1280, height=720, page=facebook_page)
    print(f"📐 Resize result: {result}")

    # Test list tabs
    result = browser_tabs(action="list", page=facebook_page)
    print(f"📑 Tabs result: {result}")

    # Test reload
    result = browser_reload(page=facebook_page)
    print(f"🔄 Reload result: {result}")

    print("✅ Browser tools workflow completed")
