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
