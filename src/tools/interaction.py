"""Interaction tools for browser automation.

Ported from src/mcp-tools/tools/interaction.ts
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field
from playwright.sync_api import Page

from src.tools.base import session_tool, ToolResult


# ============= Tool Argument Schemas =============


class ClickArgs(BaseModel):
    """Arguments for browser_click tool."""

    selector: str = Field(description="CSS selector, XPath, or text content to find the element")
    button: Literal["left", "right", "middle"] = Field(
        default="left",
        description="Mouse button to click",
    )
    modifiers: list[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]] = Field(
        default_factory=list,
        description="Modifier keys to hold during click",
    )
    double_click: bool = Field(
        default=False,
        description="Whether to perform a double click",
    )
    force: bool = Field(
        default=False,
        description="Whether to bypass visibility checks",
    )
    timeout: int = Field(
        default=5000,
        ge=0,
        le=60000,
        description="Maximum time to wait for element in milliseconds",
    )


# ============= Tool Functions =============


@session_tool
def browser_click(
    selector: str,
    button: str = "left",
    modifiers: list[str] = None,
    double_click: bool = False,
    force: bool = False,
    timeout: int = 5000,
    page: Page = None,
) -> str:
    """Click on a web page element using CSS selector or text content.

    Args:
        selector: CSS selector, XPath, or text content to find the element
        button: Mouse button to click (left, right, middle)
        modifiers: Modifier keys to hold during click (Alt, Control, Meta, Shift)
        double_click: Whether to perform a double click
        force: Whether to bypass visibility checks
        timeout: Maximum time to wait for element in milliseconds
        page: Playwright Page object (injected by decorator)

    Returns:
        Success message confirming the click action
    """
    if modifiers is None:
        modifiers = []

    # Locate element
    element = page.locator(selector).first
    element.wait_for(state="visible", timeout=timeout)

    # Build click options
    click_options = {
        "button": button,
        "modifiers": modifiers,
        "force": force,
    }

    # Perform click
    if double_click:
        element.dblclick(**click_options)
    else:
        element.click(**click_options)

    return ToolResult(
        success=True,
        content=f"Clicked on element: {selector}",
        data={"selector": selector, "button": button, "double_click": double_click},
    ).to_string()
