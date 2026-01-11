"""Demo script to test the core tools.

Usage:
    python -m src.demo_tools
"""

from unittest.mock import Mock
from src.tools.navigation import (
    browser_navigate,
    browser_navigate_back,
    browser_screenshot,
    browser_get_page_info,
)
from src.tools.interaction import browser_click


def demo_navigation_tools():
    """Demonstrate navigation tools with a mock page."""
    print("\n=== Navigation Tools Demo ===\n")

    # Create a mock Playwright Page
    mock_page = Mock()
    mock_page.title.return_value = "Example Domain"
    mock_page.url = "https://example.com"
    mock_page.evaluate.return_value = {
        "url": "https://example.com",
        "title": "Example Domain",
        "domain": "example.com",
        "path": "/",
        "readyState": "complete",
        "scrollX": 0,
        "scrollY": 0,
        "viewport": {"width": 1920, "height": 1080},
    }

    # Test browser_navigate
    print("1. browser_navigate:")
    result = browser_navigate(url="https://example.com", page=mock_page)
    print(f"   {result}\n")

    # Test browser_get_page_info
    print("2. browser_get_page_info:")
    result = browser_get_page_info(page=mock_page)
    print(f"   {result}\n")

    # Test browser_navigate_back
    mock_page.url = "https://example.com/back"
    print("3. browser_navigate_back:")
    result = browser_navigate_back(page=mock_page)
    print(f"   {result}\n")


def demo_interaction_tools():
    """Demonstrate interaction tools with a mock page."""
    print("\n=== Interaction Tools Demo ===\n")

    # Create a mock Playwright Page and Locator
    mock_page = Mock()
    mock_locator = Mock()
    mock_page.locator.return_value.first = mock_locator

    # Test browser_click
    print("1. browser_click:")
    result = browser_click(selector="button.submit", page=mock_page)
    print(f"   {result}\n")

    # Test right-click
    print("2. browser_click (right button):")
    result = browser_click(selector="button.context", button="right", page=mock_page)
    print(f"   {result}\n")

    # Test double-click
    print("3. browser_click (double click):")
    result = browser_click(selector="button.dbl", double_click=True, page=mock_page)
    print(f"   {result}\n")


def demo_screenshot_tool():
    """Demonstrate screenshot tool with a mock page."""
    print("\n=== Screenshot Tool Demo ===\n")

    from unittest.mock import patch

    mock_page = Mock()
    mock_page.screenshot = Mock()

    # Mock Path.stat() to return a fake file size
    mock_stat = Mock()
    mock_stat.st_size = 12345

    with patch("pathlib.Path.stat", return_value=mock_stat):
        print("1. browser_screenshot (default):")
        result = browser_screenshot(page=mock_page)
        print(f"   {result}\n")

        print("2. browser_screenshot (JPEG with quality):")
        result = browser_screenshot(type="jpeg", quality=90, page=mock_page)
        print(f"   {result}\n")


def demo_session_tool_decorator():
    """Demonstrate the session_tool decorator behavior."""
    print("\n=== Session Tool Decorator Demo ===\n")

    # Without session - should return error
    from src.session.profile_manager import set_global_session as set_session

    set_session(None)

    print("1. Calling tool without active session:")
    result = browser_navigate(url="https://example.com")
    print(f"   {result}\n")

    # With mock session
    print("2. Calling tool with mock session:")
    mock_page = Mock()
    mock_page.title.return_value = "Test Page"
    mock_page.url = "https://test.com"

    from src.session.profile_manager import FacebookProfileManager as PlaywrightSession
    session = PlaywrightSession()
    session._page = mock_page
    set_session(session)

    result = browser_navigate(url="https://test.com")
    print(f"   {result}\n")

    # Cleanup
    set_session(None)


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Facebook Surfer - Core Tools Demo")
    print("=" * 60)

    demo_navigation_tools()
    demo_interaction_tools()
    demo_screenshot_tool()
    demo_session_tool_decorator()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
