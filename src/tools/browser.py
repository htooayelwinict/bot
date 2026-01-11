"""Browser management tools.

Ported from src/mcp-tools/tools/browser.ts
"""

from typing import Any, Literal, Optional

from playwright.async_api import Page
from pydantic import BaseModel, Field

from src.tools.base import ToolResult, async_session_tool

# ============= Tool Argument Schemas =============


class TabsArgs(BaseModel):
    """Arguments for browser_tabs tool."""

    action: Literal["list", "new", "close", "select"] = Field(
        description="Tab operation to perform"
    )
    index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Tab index for close/select operations",
    )
    url: Optional[str] = Field(
        default=None,
        description="URL for new tab",
    )


class ResizeArgs(BaseModel):
    """Arguments for browser_resize tool."""

    width: int = Field(
        ge=100,
        le=10000,
        description="Window width in pixels",
    )
    height: int = Field(
        ge=100,
        le=10000,
        description="Window height in pixels",
    )


class HandleDialogArgs(BaseModel):
    """Arguments for browser_handle_dialog tool."""

    accept: bool = Field(
        default=True,
        description="Whether to accept (OK) or dismiss (Cancel) the dialog",
    )
    prompt_text: Optional[str] = Field(
        default=None,
        description="Text to enter for prompt dialogs",
    )


class ReloadArgs(BaseModel):
    """Arguments for browser_reload tool."""

    force: bool = Field(
        default=False,
        description="Whether to force reload from server (bypass cache)",
    )
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = Field(
        default="load",
        description="When to consider reload complete",
    )


class CloseArgs(BaseModel):
    """Arguments for browser_close tool."""

    close_browser: bool = Field(
        default=False,
        description="Whether to close entire browser (true) or just current page (false)",
    )


# ============= Tool Functions =============


@async_session_tool
async def browser_tabs(
    action: str,
    index: Optional[int] = None,
    url: Optional[str] = None,
    page: Page = None,
) -> str:
    """List, create, close, or select browser tabs."""
    try:
        browser_context = page.context

        if action == "list":
            pages = browser_context.pages
            current_index = pages.index(page)
            tabs = []
            for i, p in enumerate(pages):
                tabs.append(
                    {
                        "index": i,
                        "url": p.url,
                        "title": await p.title(),
                        "active": i == current_index,
                    }
                )
            return ToolResult(
                success=True,
                content=f"Browser tabs ({len(tabs)} total):\n{tabs}",
                data={"tabs": tabs},
            ).to_string()

        if action == "new":
            new_page = await browser_context.new_page()
            if url:
                await new_page.goto(url)
            return ToolResult(
                success=True,
                content=f"Created new tab{f' and navigated to {url}' if url else ''}",
                data={"url": url},
            ).to_string()

        if action == "close":
            if index is not None:
                pages = browser_context.pages
                if 0 <= index < len(pages):
                    await pages[index].close()
                    return ToolResult(
                        success=True,
                        content=f"Closed tab at index {index}",
                        data={"index": index},
                    ).to_string()
                return ToolResult(
                    success=False,
                    content=f"Invalid tab index: {index}",
                ).to_string()
            await page.close()
            return ToolResult(success=True, content="Closed current tab").to_string()

        if action == "select":
            if index is None:
                return ToolResult(
                    success=False,
                    content="Tab index required for select action",
                ).to_string()
            pages = browser_context.pages
            if 0 <= index < len(pages):
                await pages[index].bring_to_front()
                return ToolResult(
                    success=True,
                    content=f"Switched to tab at index {index}",
                    data={"index": index},
                ).to_string()
            return ToolResult(
                success=False,
                content=f"Invalid tab index: {index}",
            ).to_string()

        return ToolResult(success=False, content=f"Unknown action: {action}").to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Tab action failed: {exc}",
        ).to_string()


@async_session_tool
async def browser_resize(width: int, height: int, page: Page = None) -> str:
    """Resize the browser window to specified dimensions."""
    try:
        await page.set_viewport_size({"width": width, "height": height})
        return ToolResult(
            success=True,
            content=f"Browser window resized to {width}x{height}",
            data={"width": width, "height": height},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to resize browser window: {exc}",
        ).to_string()


@async_session_tool
async def browser_handle_dialog(
    accept: bool = True,
    prompt_text: Optional[str] = None,
    page: Page = None,
) -> str:
    """Handle JavaScript dialogs (alert, confirm, prompt)."""
    try:
        def handler(dialog: Any) -> None:
            if prompt_text and dialog.type == "prompt":
                dialog.accept(prompt_text)
            elif accept:
                dialog.accept()
            else:
                dialog.dismiss()

        page.once("dialog", handler)

        return ToolResult(
            success=True,
            content=(
                f"Dialog handler configured (accept: {accept}"
                f"{f', prompt: {prompt_text}' if prompt_text else ''})"
            ),
            data={"accept": accept, "prompt_text": prompt_text},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to configure dialog handler: {exc}",
        ).to_string()


@async_session_tool
async def browser_reload(
    force: bool = False,
    wait_until: str = "load",
    page: Page = None,
) -> str:
    """Reload the current page."""
    try:
        await page.reload(wait_until=wait_until, timeout=30000)
        page_title = await page.title()
        return ToolResult(
            success=True,
            content=f"Page reloaded{' (forced)' if force else ''}. Title: {page_title}",
            data={"title": page_title, "force": force},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to reload page: {exc}",
        ).to_string()


@async_session_tool
async def browser_close(close_browser: bool = False, page: Page = None) -> str:
    """Close the browser or current page."""
    try:
        if close_browser:
            browser = page.context.browser
            if browser:
                await browser.close()
                return ToolResult(success=True, content="Browser closed").to_string()
            await page.context.close()
            return ToolResult(success=True, content="Browser context closed").to_string()
        await page.close()
        return ToolResult(success=True, content="Current page closed").to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to close browser/page: {exc}",
        ).to_string()
