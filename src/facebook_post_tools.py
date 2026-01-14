"""
Facebook Post Creator - Using Existing Tools
Creates a Facebook post with "Only me" privacy setting using existing browser tools.
"""

import asyncio
from src.session import FacebookSessionManager, set_global_session
from src.tools.navigation import browser_navigate
from src.tools.interaction import browser_click, browser_type
from src.tools.utilities import browser_wait, browser_get_snapshot


async def create_facebook_post_onlyme_with_tools(message: str = "Test post - only me"):
    """
    Create a Facebook post with 'Only me' privacy using existing tools.

    Args:
        message: The post content to create
    """

    # Set up session manager
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        mgr = FacebookSessionManager()
        context, page, _ = await mgr.get_or_create_session_async(p.chromium)

        # Set global session for tools
        set_global_session(mgr)

        # Step 1: Navigate to Facebook
        result = await browser_navigate(url="https://www.facebook.com", page=page)
        print(result)

        # Wait for page to load
        await asyncio.sleep(2)

        # Step 2: Close notification dialog if present
        try:
            result = await browser_click(selector="text=Close", page=page, timeout=3000, force=True)
            print(result)
        except Exception:
            print("No notification dialog to close")

        # Step 3: Click "What's on your mind" button
        result = await browser_click(
            selector='button="What\'s on your mind, Htoo?"',
            page=page,
            timeout=10000,
            force=True
        )
        print(result)

        await asyncio.sleep(1)

        # Step 4: Click privacy button
        result = await browser_click(
            selector='button="Edit privacy. Sharing with"',
            page=page,
            timeout=5000,
            force=True
        )
        print(result)

        await asyncio.sleep(0.5)

        # Step 5: Select "Only me"
        result = await browser_click(
            selector='text="Only me"',
            page=page,
            timeout=5000,
            force=True
        )
        print(result)

        await asyncio.sleep(0.5)

        # Step 6: Click Done
        result = await browser_click(
            selector='button="Done"',
            page=page,
            timeout=5000,
            force=True
        )
        print(result)

        await asyncio.sleep(0.5)

        # Step 7: Type the post content
        result = await browser_type(
            selector="role=textbox",
            text=message,
            page=page,
            timeout=5000
        )
        print(result)

        # Step 8: Wait for Next button
        await asyncio.sleep(1)

        # Step 9: Click Next to open post settings dialog
        result = await browser_click(
            selector='button="Next"',
            page=page,
            timeout=10000,
            force=True
        )
        print(result)

        # Wait longer for post settings dialog to appear
        await asyncio.sleep(2)

        # Step 10: Click Post (in settings dialog)
        # Use [exact] modifier to match only buttons named exactly "Post"
        result = await browser_click(
            selector='role=button[name="Post"][exact]',
            page=page,
            timeout=15000,
            force=True
        )
        print(result)

        # Wait for post to complete
        await asyncio.sleep(3)

        return True
