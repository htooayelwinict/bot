"""Tool registry for LangChain StructuredTool integration.

Provides centralized registration and management of all browser automation
tools with category metadata and LangChain compatibility.
"""

import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel


class ToolCategory(str, Enum):
    """Tool categories for organization."""

    navigation = "navigation"
    interaction = "interaction"
    forms = "forms"
    utilities = "utilities"
    browser = "browser"
    vision = "vision"


@dataclass(frozen=True)
class ToolSpec:
    """Specification for a tool in the registry."""

    name: str
    category: ToolCategory
    description: str
    func: Callable[..., str]
    args_schema: type[BaseModel]

    def to_langchain_tool(self) -> StructuredTool:
        """Convert to LangChain StructuredTool.

        Properly handles async functions by using coroutine parameter.
        Uses function docstring as description if available.
        """
        # Prefer function docstring over brief description
        tool_description = self.description
        if self.func.__doc__:
            # Clean up docstring: remove leading/trailing whitespace and empty lines
            docstring = self.func.__doc__.strip()
            # Remove "Args:" and "Returns:" sections for cleaner tool descriptions
            if "\n\nArgs:" in docstring:
                docstring = docstring.split("\n\nArgs:")[0].strip()
            elif "\nArgs:" in docstring:
                docstring = docstring.split("\nArgs:")[0].strip()
            tool_description = docstring

        # Detect if function is async
        if inspect.iscoroutinefunction(self.func):
            return StructuredTool.from_function(
                coroutine=self.func,
                name=self.name,
                description=tool_description,
                args_schema=self.args_schema,
            )
        else:
            return StructuredTool.from_function(
                func=self.func,
                name=self.name,
                description=tool_description,
                args_schema=self.args_schema,
            )


class ToolRegistry:
    """Registry for browser automation tools.

    Stores tool metadata and provides methods for retrieving tools
    as LangChain StructuredTool instances for use with DeepAgents.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Register a tool specification.

        Args:
            spec: ToolSpec to register

        Raises:
            ValueError: If tool with same name already registered
        """
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> StructuredTool | None:
        """Get tool by name as LangChain StructuredTool.

        Args:
            name: Tool name

        Returns:
            StructuredTool or None if not found
        """
        spec = self._tools.get(name)
        return spec.to_langchain_tool() if spec else None

    def get_all(self) -> list[StructuredTool]:
        """Get all registered tools as LangChain StructuredTools.

        Returns:
            List of StructuredTool instances
        """
        return [spec.to_langchain_tool() for spec in self._tools.values()]

    def get_by_category(self, category: ToolCategory) -> list[StructuredTool]:
        """Get tools by category as LangChain StructuredTools.

        Args:
            category: ToolCategory filter

        Returns:
            List of StructuredTool instances in category
        """
        return [
            spec.to_langchain_tool()
            for spec in self._tools.values()
            if spec.category == category
        ]

    def list_names(self) -> list[str]:
        """List all tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def list_by_category(self) -> dict[str, list[str]]:
        """List tool names grouped by category.

        Returns:
            Dict mapping category to list of tool names
        """
        grouped: dict[str, list[str]] = {}
        for spec in self._tools.values():
            cat = spec.category.value
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(spec.name)
        return grouped

    def count(self) -> int:
        """Count total registered tools.

        Returns:
            Number of registered tools
        """
        return len(self._tools)

    def summary(self) -> str:
        """Get registry summary as formatted string.

        Returns:
            Formatted summary string
        """
        lines = ["Tool Registry Summary:", f"Total Tools: {self.count()}"]
        for cat, names in sorted(self.list_by_category().items()):
            lines.append(f"\n{cat.capitalize()} ({len(names)}):")
            for name in sorted(names):
                lines.append(f"  - {name}")
        return "\n".join(lines)


# Global registry instance
registry = ToolRegistry()


def register_all_tools() -> ToolRegistry:
    """Register all browser automation tools.

    Imports and registers all 22 tools with their categories.
    Also binds the current page to each tool to avoid threading issues.

    Returns:
        The populated registry instance
    """
    # Navigation tools
    from src.tools.navigation import (
        GetPageInfoArgs,
        NavigateArgs,
        NavigateBackArgs,
        ScreenshotArgs,
        browser_get_page_info,
        browser_navigate,
        browser_navigate_back,
        browser_screenshot,
    )

    registry.register(
        ToolSpec(
            name="browser_navigate",
            category=ToolCategory.navigation,
            description="Navigate to a URL",
            func=browser_navigate,
            args_schema=NavigateArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_navigate_back",
            category=ToolCategory.navigation,
            description="Navigate back to the previous page",
            func=browser_navigate_back,
            args_schema=NavigateBackArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_screenshot",
            category=ToolCategory.navigation,
            description="Capture a screenshot of the current page",
            func=browser_screenshot,
            args_schema=ScreenshotArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_get_page_info",
            category=ToolCategory.navigation,
            description="Get information about the current page",
            func=browser_get_page_info,
            args_schema=GetPageInfoArgs,
        )
    )

    # Interaction tools
    from src.tools.interaction import (
        ClickArgs,
        HoverArgs,
        PressKeyArgs,
        SelectOptionArgs,
        TypeArgs,
        browser_click,
        browser_hover,
        browser_press_key,
        browser_select_option,
        browser_type,
    )

    registry.register(
        ToolSpec(
            name="browser_click",
            category=ToolCategory.interaction,
            description="Click on an element",
            func=browser_click,
            args_schema=ClickArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_type",
            category=ToolCategory.interaction,
            description="Type text into an element",
            func=browser_type,
            args_schema=TypeArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_select_option",
            category=ToolCategory.interaction,
            description="Select an option from a dropdown",
            func=browser_select_option,
            args_schema=SelectOptionArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_hover",
            category=ToolCategory.interaction,
            description="Hover over an element",
            func=browser_hover,
            args_schema=HoverArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_press_key",
            category=ToolCategory.interaction,
            description="Press a keyboard key",
            func=browser_press_key,
            args_schema=PressKeyArgs,
        )
    )

    # Forms tools
    from src.tools.forms import (
        FillFormArgs,
        GetFormDataArgs,
        SubmitFormArgs,
        browser_fill_form,
        browser_get_form_data,
        browser_submit_form,
    )

    registry.register(
        ToolSpec(
            name="browser_fill_form",
            category=ToolCategory.forms,
            description="Fill multiple form fields at once",
            func=browser_fill_form,
            args_schema=FillFormArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_get_form_data",
            category=ToolCategory.forms,
            description="Get form field data",
            func=browser_get_form_data,
            args_schema=GetFormDataArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_submit_form",
            category=ToolCategory.forms,
            description="Submit a form",
            func=browser_submit_form,
            args_schema=SubmitFormArgs,
        )
    )

    # Utilities tools
    from src.tools.utilities import (
        EvaluateArgs,
        GetConsoleMessagesArgs,
        GetNetworkRequestsArgs,
        GetSnapshotArgs,
        browser_evaluate,
        browser_get_console_messages,
        browser_get_network_requests,
        browser_get_snapshot,
        browser_wait,
    )
    from src.tools.utilities import (
        WaitArgs as UtilWaitArgs,
    )

    registry.register(
        ToolSpec(
            name="browser_wait",
            category=ToolCategory.utilities,
            description="Wait for a condition or time",
            func=browser_wait,
            args_schema=UtilWaitArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_evaluate",
            category=ToolCategory.utilities,
            description="Evaluate JavaScript in the page",
            func=browser_evaluate,
            args_schema=EvaluateArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_get_snapshot",
            category=ToolCategory.utilities,
            description="Get accessibility snapshot of the page",
            func=browser_get_snapshot,
            args_schema=GetSnapshotArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_get_network_requests",
            category=ToolCategory.utilities,
            description="Get network requests made by the page",
            func=browser_get_network_requests,
            args_schema=GetNetworkRequestsArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_get_console_messages",
            category=ToolCategory.utilities,
            description="Get console messages from the page",
            func=browser_get_console_messages,
            args_schema=GetConsoleMessagesArgs,
        )
    )

    # Browser tools
    from src.tools.browser import (
        CloseArgs,
        HandleDialogArgs,
        ReloadArgs,
        ResizeArgs,
        TabsArgs,
        browser_close,
        browser_handle_dialog,
        browser_reload,
        browser_resize,
        browser_tabs,
    )

    registry.register(
        ToolSpec(
            name="browser_tabs",
            category=ToolCategory.browser,
            description="Manage browser tabs",
            func=browser_tabs,
            args_schema=TabsArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_resize",
            category=ToolCategory.browser,
            description="Resize browser viewport",
            func=browser_resize,
            args_schema=ResizeArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_handle_dialog",
            category=ToolCategory.browser,
            description="Handle alerts and dialogs",
            func=browser_handle_dialog,
            args_schema=HandleDialogArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_reload",
            category=ToolCategory.browser,
            description="Reload the current page",
            func=browser_reload,
            args_schema=ReloadArgs,
        )
    )
    registry.register(
        ToolSpec(
            name="browser_close",
            category=ToolCategory.browser,
            description="Close the browser",
            func=browser_close,
            args_schema=CloseArgs,
        )
    )

    return registry
