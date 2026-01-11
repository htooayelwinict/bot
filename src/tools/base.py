"""Base tool classes and utilities for LangChain tool integration."""

import json
import os
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field
from playwright.sync_api import Page

from src.session import get_current_page


class ToolResult(BaseModel):
    """Standardized tool result."""

    success: bool = Field(description="Whether the tool execution succeeded")
    content: str = Field(description="Human-readable result description")
    data: Optional[dict[str, Any]] = Field(default=None, description="Structured output data")

    def to_string(self) -> str:
        """Convert to string for LangChain consumption."""
        if self.data:
            return f"{self.content}\n{json.dumps(self.data, indent=2)}"
        return self.content


def session_tool(func: Callable) -> Callable:
    """Decorator to inject current page into tool calls.

    This decorator automatically retrieves the current Playwright Page
    from the global session and passes it as the 'page' kwarg to the
    decorated function. If no page is available, it returns an error result.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        # Check if page is already provided in kwargs (for testing)
        if "page" not in kwargs:
            page = get_current_page()
            if not page:
                return ToolResult(
                    success=False,
                    content="Error: No active browser session. Please restore or start a session first.",
                ).to_string()
            kwargs["page"] = page

        try:
            result = func(*args, **kwargs)
            # If result is already a string, return it
            if isinstance(result, str):
                return result
            # If result is a ToolResult, convert to string
            if isinstance(result, ToolResult):
                return result.to_string()
            # Otherwise convert to string
            return str(result)
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error executing {func.__name__}: {str(e)}",
            ).to_string()

    return wrapper


def create_tool_description(
    name: str,
    description: str,
    args_schema: type[BaseModel],
) -> dict[str, Any]:
    """Create a tool definition dictionary for LangChain.

    Args:
        name: Tool name
        description: Tool description
        args_schema: Pydantic BaseModel for arguments

    Returns:
        Dictionary with tool definition
    """
    return {
        "name": name,
        "description": description,
        "args_schema": args_schema,
    }


def with_screenshot(func: Callable) -> Callable:
    """Decorator to capture screenshot before tool execution.

    This decorator captures a screenshot before the decorated function executes.
    Screenshots are stored in ./screenshots/ with automatic cleanup of old files.

    Args:
        func: Function to decorate

    Returns:
        Wrapped function that captures screenshots before execution
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        # Get page for screenshot
        page = get_current_page()
        if page:
            timestamp = int(time.time())
            tool_name = func.__name__
            screenshot_dir = Path("./screenshots")
            screenshot_dir.mkdir(exist_ok=True)

            screenshot_path = screenshot_dir / f"pre-{tool_name}-{timestamp}.png"

            try:
                page.screenshot(path=str(screenshot_path))
            except Exception:
                pass  # Screenshot is optional, don't fail on error

        # Execute tool
        result = func(*args, **kwargs)

        # Clean up old screenshots (> 1 hour)
        _cleanup_old_screenshots()

        return result

    return wrapper


def _cleanup_old_screenshots(max_age_seconds: int = 3600) -> int:
    """Remove screenshots older than specified age.

    Args:
        max_age_seconds: Maximum age in seconds (default: 1 hour)

    Returns:
        Number of screenshots deleted
    """
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
