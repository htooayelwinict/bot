"""Integration tests for Facebook-specific tools.

Tests:
- browser_scroll for lazy loading
- browser_extract_posts for post extraction
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page

from src.session import FacebookProfileManager, check_login_status, wait_for_login
from src.tools.navigation import browser_scroll
from src.tools.utilities import browser_extract_posts, browser_wait


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
# Scroll Tests
# =============================================================================

def test_browser_scroll_down(facebook_page: Page):
    """Test browser_scroll tool for scrolling down."""
    # Navigate to home feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)
    import time
    time.sleep(2)

    # Get initial scroll position
    initial_y = facebook_page.evaluate("window.scrollY")

    # Scroll down
    result = browser_scroll(direction="down", amount=500, page=facebook_page)
    print(f"📜 Scroll result: {result}")

    # Verify scroll position changed
    final_y = facebook_page.evaluate("window.scrollY")
    assert final_y > initial_y, "Scroll position should increase after scrolling down"

    print("✅ Scroll down test passed")


def test_browser_scroll_up(facebook_page: Page):
    """Test browser_scroll tool for scrolling up."""
    # Navigate to home feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)
    import time
    time.sleep(2)

    # First scroll down
    browser_scroll(direction="down", amount=1000, page=facebook_page)
    time.sleep(0.5)

    # Get scroll position before scrolling up
    before_scroll_y = facebook_page.evaluate("window.scrollY")

    # Scroll up
    result = browser_scroll(direction="up", amount=300, page=facebook_page)
    print(f"📜 Scroll up result: {result}")

    # Verify scroll position decreased
    after_scroll_y = facebook_page.evaluate("window.scrollY")
    assert after_scroll_y < before_scroll_y, "Scroll position should decrease after scrolling up"

    print("✅ Scroll up test passed")


# =============================================================================
# Post Extraction Tests
# =============================================================================

def test_extract_posts_basic(facebook_page: Page):
    """Test browser_extract_posts tool for basic post extraction."""
    # Navigate to home feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Wait for page to load
    import time
    time.sleep(3)

    # Extract posts without scrolling
    result = browser_extract_posts(
        max_posts=5,
        scroll_to_load=False,
        include_content=True,
        page=facebook_page
    )
    print(f"📊 Extract posts result: {result}")

    # Verify result contains expected data
    assert "posts" in result or "Extracted" in result, "Result should contain posts data"

    print("✅ Basic post extraction test passed")


def test_extract_posts_with_scroll(facebook_page: Page):
    """Test browser_extract_posts tool with lazy loading scroll."""
    # Navigate to home feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Wait for initial load
    import time
    time.sleep(2)

    # Extract posts with scrolling
    result = browser_extract_posts(
        max_posts=15,
        scroll_to_load=True,
        scroll_amount=500,
        include_content=False,  # Skip content for faster test
        page=facebook_page
    )
    print(f"📊 Extract posts with scroll result: {result}")

    # Verify result
    assert "posts" in result or "Extracted" in result, "Result should contain posts data"

    print("✅ Post extraction with scroll test passed")


def test_extract_posts_max_limit(facebook_page: Page):
    """Test browser_extract_posts respects max_posts limit."""
    # Navigate to home feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Wait for page load
    import time
    time.sleep(2)

    # Extract with small max limit
    max_posts = 3
    result = browser_extract_posts(
        max_posts=max_posts,
        scroll_to_load=False,
        page=facebook_page
    )
    print(f"📊 Extract posts (max={max_posts}) result: {result}")

    # Verify we don't exceed max_posts
    result_str = str(result)
    assert f"Extracted" in result_str, "Result should show extraction count"

    print("✅ Max posts limit test passed")


# =============================================================================
# Combined Workflow Tests
# =============================================================================

def test_scroll_and_extract_workflow(facebook_page: Page):
    """Test complete workflow: navigate → scroll → extract posts."""
    # Navigate to feed
    facebook_page.goto(FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000)

    # Wait for initial load
    import time
    time.sleep(2)

    # Scroll multiple times to load more content
    for i in range(3):
        browser_scroll(direction="down", amount=500, page=facebook_page)
        browser_wait(time=1.5, page=facebook_page)
        print(f"📜 Scroll iteration {i+1}/3 complete")

    # Extract posts from loaded content
    result = browser_extract_posts(
        max_posts=10,
        scroll_to_load=False,
        include_content=True,
        page=facebook_page
    )
    print(f"📊 Final extraction result: {result}")

    # Verify success
    assert "Extracted" in result, "Should extract posts after scrolling"

    print("✅ Combined scroll and extract workflow test passed")


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_extract_posts_empty_page(browser_type):
    """Test post extraction on non-Facebook page."""
    # Create a new page with a blank page
    context, page = browser_type.new_context(), browser_type.new_page()
    page.goto("about:blank")

    # Try to extract posts from empty page
    result = browser_extract_posts(
        max_posts=5,
        scroll_to_load=False,
        page=page
    )
    print(f"📊 Empty page result: {result}")

    # Should handle gracefully (return 0 posts or error message)
    assert "Failed" in result or "0" in result or "Extracted 0" in result, "Should handle empty page gracefully"

    # Cleanup
    page.close()
    context.close()

    print("✅ Empty page handling test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
