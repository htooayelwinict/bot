# Base tools and utilities
from .base import (
    ToolResult,
    get_current_context,
    get_current_page,
    session_tool,
    set_current_context,
    set_current_page,
    with_screenshot,
)

# Browser management tools
from .browser import (
    browser_close,
    browser_handle_dialog,
    browser_reload,
    browser_resize,
    browser_tabs,
)

# Form tools
from .forms import (
    browser_fill_form,
    browser_get_form_data,
    browser_submit_form,
)

# Interaction tools
from .interaction import (
    browser_click,
    browser_hover,
    browser_press_key,
    browser_select_option,
    browser_type,
)

# Navigation tools
from .navigation import (
    browser_get_page_info,
    browser_navigate,
    browser_navigate_back,
    browser_screenshot,
)

# Utility tools
from .utilities import (
    browser_evaluate,
    browser_get_console_messages,
    browser_get_network_requests,
    browser_get_snapshot,
    browser_wait,
)

# Vision tools
from .vision import (
    capture_screenshot_for_analysis,
    capture_screenshot_with_metadata,
    cleanup_old_screenshots,
    get_cached_screenshot,
)

__all__ = [
    # Base
    "session_tool",
    "ToolResult",
    "with_screenshot",
    "set_current_page",
    "get_current_page",
    "set_current_context",
    "get_current_context",
    # Navigation
    "browser_navigate",
    "browser_navigate_back",
    "browser_screenshot",
    "browser_get_page_info",
    # Interaction
    "browser_click",
    "browser_type",
    "browser_select_option",
    "browser_hover",
    "browser_press_key",
    # Forms
    "browser_fill_form",
    "browser_get_form_data",
    "browser_submit_form",
    # Utilities
    "browser_wait",
    "browser_evaluate",
    "browser_get_snapshot",
    "browser_get_network_requests",
    "browser_get_console_messages",
    # Browser
    "browser_tabs",
    "browser_resize",
    "browser_handle_dialog",
    "browser_reload",
    "browser_close",
    # Vision
    "capture_screenshot_for_analysis",
    "capture_screenshot_with_metadata",
    "cleanup_old_screenshots",
    "get_cached_screenshot",
]
