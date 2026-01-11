"""Navigation tools for browser automation.

Ported from src/mcp-tools/tools/navigation.ts
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Literal, Optional

from playwright.async_api import Page
from pydantic import BaseModel, Field

from src.tools.base import ToolResult, async_session_tool

# ============= Tool Argument Schemas =============


class NavigateArgs(BaseModel):
    """Arguments for browser_navigate tool."""

    url: str = Field(description="The URL to navigate to")
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = Field(
        default="load",
        description="When to consider navigation successful",
    )
    timeout: int = Field(
        default=30000,
        ge=0,
        le=300000,
        description="Maximum navigation time in milliseconds",
    )


class ScreenshotArgs(BaseModel):
    """Arguments for browser_screenshot tool."""

    filename: str = Field(
        default="screenshot-{timestamp}",
        description="Screenshot filename (without extension). Use {timestamp} for current time.",
    )
    type: Literal["png", "jpeg"] = Field(
        default="png",
        description="Screenshot image format",
    )
    full_page: bool = Field(
        default=False,
        description="Whether to capture the full scrollable page",
    )
    quality: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Image quality (1-100 for jpeg only)",
    )


class NavigateBackArgs(BaseModel):
    """Arguments for browser_navigate_back tool."""

    pass  # No arguments needed


class GetPageInfoArgs(BaseModel):
    """Arguments for browser_get_page_info tool."""

    pass  # No arguments needed


# ============= Tool Functions =============


@async_session_tool
async def browser_navigate(url: str, wait_until: str = "load", timeout: int = 30000, page: Page = None) -> str:
    """Navigate to a specific URL. Waits for the page to load before returning.

    Args:
        url: The URL to navigate to
        wait_until: When to consider navigation successful (load, domcontentloaded, networkidle)
        timeout: Maximum navigation time in milliseconds
        page: Playwright Page object (injected by decorator)

    Returns:
        Success message with page title and final URL
    """
    await page.goto(url, wait_until=wait_until, timeout=timeout)

    return ToolResult(
        success=True,
        content=f"Navigated to {url}\nPage title: {await page.title()}\nFinal URL: {page.url}",
        data={"url": page.url, "title": await page.title()},
    ).to_string()


@async_session_tool
async def browser_navigate_back(page: Page = None) -> str:
    """Go back to the previous page in browser history.

    Args:
        page: Playwright Page object (injected by decorator)

    Returns:
        Success message with current URL
    """
    await page.go_back()
    await asyncio.sleep(0.5)  # Small wait for navigation to complete

    return ToolResult(
        success=True,
        content=f"Navigated back. Current URL: {page.url}",
        data={"url": page.url},
    ).to_string()


@async_session_tool
async def browser_screenshot(
    filename: str = "screenshot-{timestamp}",
    type: str = "png",
    full_page: bool = False,
    quality: Optional[int] = None,
    page: Page = None,
) -> str:
    """Take a screenshot of the current page or a specific element.

    Args:
        filename: Screenshot filename (without extension). Use {timestamp} for current time.
        type: Screenshot image format (png or jpeg)
        full_page: Whether to capture the full scrollable page
        quality: Image quality (1-100 for jpeg only)
        page: Playwright Page object (injected by decorator)

    Returns:
        Success message with file path and size
    """
    # Create screenshots directory
    screenshot_dir = Path("./screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Replace {timestamp} placeholder
    if "{timestamp}" in filename:
        filename = filename.replace("{timestamp}", str(int(time.time() * 1000)))

    file_path = screenshot_dir / f"{filename}.{type}"

    # Build screenshot options
    screenshot_options = {
        "path": str(file_path),
        "full_page": full_page,
        "type": type,
    }

    if type == "jpeg" and quality is not None:
        screenshot_options["quality"] = quality

    await page.screenshot(**screenshot_options)

    # Get file size
    file_size = file_path.stat().st_size
    file_size_kb = round(file_size / 1024)

    return ToolResult(
        success=True,
        content=f"Screenshot saved to {file_path} ({file_size_kb} KB)",
        data={
            "file_path": str(file_path),
            "file_size": file_size,
            "type": type,
            "full_page": full_page,
        },
    ).to_string()


@async_session_tool
async def browser_get_page_info(page: Page = None) -> str:
    """Get information about the current page including URL, title, and meta information.

    Args:
        page: Playwright Page object (injected by decorator)

    Returns:
        JSON string with page information
    """
    info = await page.evaluate(
        """() => ({
        url: window.location.href,
        title: document.title,
        domain: window.location.hostname,
        path: window.location.pathname,
        readyState: document.readyState,
        scrollX: window.scrollX,
        scrollY: window.scrollY,
        viewport: { width: window.innerWidth, height: window.innerHeight }
    })"""
    )

    return ToolResult(
        success=True,
        content=json.dumps(info, indent=2),
        data=info,
    ).to_string()
