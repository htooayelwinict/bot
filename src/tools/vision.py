"""Vision tools for UI screenshot capture.

This module provides tools for capturing screenshots that the main agent
(with vision capabilities) can analyze. Vision analysis is done by
the main LLM, not by separate tool calls.
"""

import os
import time
from typing import Optional

from src.session import get_current_page
from src.tools.base import session_tool, ToolResult


# Screenshot cache for avoiding redundant captures
_screenshot_cache: dict[str, dict] = {}


@session_tool
def capture_screenshot_for_analysis(
    filename: str = "screenshot-{timestamp}",
    full_page: bool = False,
    page=None,
) -> str:
    """Capture a screenshot for the agent to analyze with vision.

    This tool takes a screenshot and returns the path and base64 encoding
    so the main agent (with vision capabilities) can analyze it.

    Args:
        filename: Screenshot filename (use {timestamp} for auto timestamp)
        full_page: Capture full scrollable page
        page: Playwright Page (injected by decorator)

    Returns:
        String with screenshot path, size, and context info for agent analysis
    """
    import base64
    from datetime import datetime

    # Ensure screenshots directory exists
    os.makedirs("./screenshots", exist_ok=True)

    # Generate filename with timestamp if needed
    timestamp = int(time.time())
    filename = filename.replace("{timestamp}", str(timestamp))

    # Ensure .png extension
    if not filename.endswith(".png"):
        filename = f"{filename}.png"

    path = f"./screenshots/{filename}"

    # Capture screenshot
    page.screenshot(path=path, full_page=full_page)

    # Get metadata
    stats = os.stat(path)

    # Encode to base64 for agent vision analysis
    with open(path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode()

    # Format size nicely
    size_kb = stats.st_size / 1024
    if size_kb < 1000:
        size_str = f"{size_kb:.1f} KB"
    else:
        size_mb = size_kb / 1024
        size_str = f"{size_mb:.1f} MB"

    return ToolResult(
        success=True,
        content=f"""Screenshot captured for analysis:
- Path: {path}
- Size: {size_str}
- URL: {page.url}
- Title: {page.title()}
- Timestamp: {datetime.now().isoformat()}

The screenshot is available at: {path}
Base64 encoded image available for vision analysis.""",
        data={
            "path": path,
            "base64": base64_image,
            "size": stats.st_size,
            "url": page.url,
            "title": page.title(),
        },
    ).to_string()


@session_tool
def capture_screenshot_with_metadata(
    filename: str = "screenshot-{timestamp}",
    full_page: bool = False,
    cache_key: Optional[str] = None,
    page=None,
) -> str:
    """Take a screenshot with metadata for caching and record-keeping.

    Args:
        filename: Screenshot filename (use {timestamp} for auto timestamp)
        full_page: Capture full scrollable page
        cache_key: Optional cache key to store/retrieve metadata
        page: Playwright Page (injected by decorator)

    Returns:
        String with screenshot metadata
    """
    from datetime import datetime

    # Ensure screenshots directory exists
    os.makedirs("./screenshots", exist_ok=True)

    # Generate filename with timestamp if needed
    timestamp = int(time.time())
    filename = filename.replace("{timestamp}", str(timestamp))

    # Ensure .png extension
    if not filename.endswith(".png"):
        filename = f"{filename}.png"

    path = f"./screenshots/{filename}"

    # Capture screenshot
    page.screenshot(path=path, full_page=full_page)

    # Get metadata
    stats = os.stat(path)
    metadata = {
        "path": path,
        "size": stats.st_size,
        "timestamp": datetime.now().isoformat(),
        "url": page.url,
        "title": page.title(),
    }

    # Format size nicely
    size_kb = stats.st_size / 1024
    if size_kb < 1000:
        size_str = f"{size_kb:.1f} KB"
    else:
        size_mb = size_kb / 1024
        size_str = f"{size_mb:.1f} MB"

    # Cache if key provided
    if cache_key:
        _screenshot_cache[cache_key] = metadata

    result = (
        f"Screenshot saved to {path}\n"
        f"Size: {size_str}\n"
        f"URL: {page.url}\n"
        f"Title: {page.title()}"
    )

    return ToolResult(success=True, content=result, data=metadata).to_string()


def cleanup_old_screenshots(max_age_seconds: int = 3600) -> int:
    """Remove screenshots older than specified age.

    Args:
        max_age_seconds: Maximum age in seconds (default: 1 hour)

    Returns:
        Number of screenshots deleted
    """
    from pathlib import Path

    screenshot_dir = Path("./screenshots")
    if not screenshot_dir.exists():
        return 0

    cutoff_time = time.time() - max_age_seconds
    deleted_count = 0

    for screenshot in screenshot_dir.glob("*.png"):
        if screenshot.stat().st_mtime < cutoff_time:
            try:
                screenshot.unlink()
                deleted_count += 1
            except Exception:
                pass  # Ignore cleanup errors

    return deleted_count


def get_cached_screenshot(cache_key: str) -> Optional[dict]:
    """Get cached screenshot metadata.

    Args:
        cache_key: Cache key to look up

    Returns:
        Metadata dict if found, None otherwise
    """
    return _screenshot_cache.get(cache_key)
