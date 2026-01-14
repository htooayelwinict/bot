"""Base tool classes and utilities for LangChain tool integration."""

import asyncio
import json
import time
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.async_api import BrowserContext as AsyncBrowserContext
from playwright.async_api import Page as AsyncPage
from playwright.sync_api import BrowserContext, Page
from pydantic import BaseModel, Field

from src.session import get_current_page as get_global_session_page

# =============================================================================
# Thread-safe context for current page (for tool execution)
# =============================================================================

_current_page: ContextVar[Page] = ContextVar("current_page")
_current_context: ContextVar[BrowserContext] = ContextVar("current_context")
_current_async_page: ContextVar[AsyncPage] = ContextVar("current_async_page")
_current_async_context: ContextVar[AsyncBrowserContext] = ContextVar("current_async_context")
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_current_page(page: Page) -> None:
    """Set the current page for tool execution (thread-safe)."""
    _current_page.set(page)


def get_current_page() -> Page | None:
    """Get the current page for tool execution.

    Uses global session directly (ContextVars don't propagate across LangGraph tasks).
    """
    return get_global_session_page()


def set_current_context(context: BrowserContext) -> None:
    """Set the current browser context (thread-safe)."""
    _current_context.set(context)


def get_current_context() -> BrowserContext | None:
    """Get the current browser context (thread-safe)."""
    try:
        return _current_context.get()
    except LookupError:
        # Fall back to global session
        from src.session import get_current_context as get_global_session_context
        return get_global_session_context()


def set_current_async_page(page: AsyncPage) -> None:
    """Set the current async page for tool execution."""
    _current_async_page.set(page)


def get_current_async_page() -> AsyncPage | None:
    """Get the current async page for tool execution.

    Uses global session directly (ContextVars don't propagate across LangGraph tasks).
    """
    from src.session import get_current_async_page as get_global_async_page
    page = get_global_async_page()
    if page is None:
        import sys
        print("[WARN] get_current_async_page: No page in global session", file=sys.stderr)
    return page


def set_current_async_context(context: AsyncBrowserContext) -> None:
    """Set the current async browser context."""
    _current_async_context.set(context)


def get_current_async_context() -> AsyncBrowserContext | None:
    """Get the current async browser context."""
    try:
        return _current_async_context.get()
    except LookupError:
        # Fall back to global session
        from src.session import get_current_async_context as get_global_async_context
        return get_global_async_context()


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the event loop for async operations."""
    global _event_loop
    _event_loop = loop


def get_event_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Get the stored event loop."""
    return _event_loop


def run_sync(coro):
    """Run async coroutine in sync context using stored event loop.

    This allows async Playwright operations to work when called from
    sync LangChain tools.
    """
    loop = get_event_loop()
    if loop is None:
        # No event loop set, try to get or create one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    if loop.is_running():
        # If loop is running, we're already in async context
        # This shouldn't happen with sync tools, but handle it gracefully
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        # Run the coroutine in the loop
        return asyncio.run(coro)


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
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                content=f"Error executing {func.__name__}: {str(e)}",
            ).to_string()

    return wrapper


def async_session_tool(func: Callable) -> Callable:
    """Async decorator to inject current async page into tool calls.

    This decorator automatically retrieves the current Playwright Page
    from the global session and passes it as the 'page' kwarg to the
    decorated async function. If no page is available, it returns an error result.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        import sys
        print(f"[TOOL] {func.__name__} called with args={args}, kwargs keys={list(kwargs.keys())}", file=sys.stderr)

        # Check if page is already provided in kwargs (for testing)
        if "page" not in kwargs:
            page = get_current_async_page()
            print(f"[TOOL] {func.__name__} got page: {page is not None}", file=sys.stderr)
            if not page:
                return ToolResult(
                    success=False,
                    content="Error: No active browser session. Please restore or start a session first.",
                ).to_string()
            kwargs["page"] = page

        try:
            result = await func(*args, **kwargs)
            print(f"[TOOL] {func.__name__} completed successfully", file=sys.stderr)
            # If result is already a string, return it
            if isinstance(result, str):
                return result
            # If result is a ToolResult, convert to string
            if isinstance(result, ToolResult):
                return result.to_string()
            # Otherwise convert to string
            return str(result)
        except Exception as e:
            import traceback
            print(f"[TOOL] {func.__name__} failed: {e}", file=sys.stderr)
            traceback.print_exc()
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
