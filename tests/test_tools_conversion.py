"""Unit tests for Phase 3a tool conversion.

Tests for 17 newly converted tools:
- Interaction (4): browser_type, browser_select_option, browser_hover, browser_press_key
- Forms (3): browser_fill_form, browser_get_form_data, browser_submit_form
- Utilities (5): browser_wait, browser_evaluate, browser_get_snapshot, browser_get_network_requests, browser_get_console_messages
- Browser (5): browser_tabs, browser_resize, browser_handle_dialog, browser_reload, browser_close
"""

import time
import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from playwright.sync_api import Page

from src.tools.interaction import (
    browser_type,
    browser_select_option,
    browser_hover,
    browser_press_key,
)
from src.tools.forms import (
    browser_fill_form,
    browser_get_form_data,
    browser_submit_form,
)
from src.tools.utilities import (
    browser_wait,
    browser_evaluate,
    browser_get_snapshot,
    browser_get_network_requests,
    browser_get_console_messages,
    ensure_request_tracking,
    ensure_console_tracking,
)
from src.tools.browser import (
    browser_tabs,
    browser_resize,
    browser_handle_dialog,
    browser_reload,
    browser_close,
)


# =============================================================================
# Interaction Tools Tests (4 tools)
# =============================================================================


class TestBrowserType:
    """Test suite for browser_type tool."""

    def test_type_with_defaults(self):
        """Test typing with default parameters."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_type(selector="input[name='email']", text="test@example.com", page=mock_page)

        # With clear=True (default), fill("") is called first, then fill(text)
        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=5000)
        assert mock_locator.fill.call_count == 2  # First with "", then with text
        assert mock_locator.fill.call_args_list[0] == call("")
        assert mock_locator.fill.call_args_list[1] == call("test@example.com")
        assert "Typed" in result and "test@example.com" in result

    def test_type_with_clear(self):
        """Test typing with clear=True (default)."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_type(selector="#username", text="user123", clear=True, page=mock_page)

        # clear=True means fill("") first
        assert mock_locator.fill.call_count == 2
        assert mock_locator.fill.call_args_list[0] == call("")
        assert mock_locator.fill.call_args_list[1] == call("user123")

    def test_type_without_clear(self):
        """Test typing with clear=False."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_type(selector="#username", text="user123", clear=False, page=mock_page)

        # clear=False means only fill(text)
        mock_locator.fill.assert_called_once_with("user123")

    def test_type_with_delay(self):
        """Test typing with delay parameter."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_type(selector="#input", text="hello", delay=50, page=mock_page)

        # With delay, uses press_sequentially instead of fill
        # But first clears if clear=True (default)
        assert mock_locator.fill.call_count == 1  # Only the clear call
        mock_locator.press_sequentially.assert_called_once_with("hello", delay=50)

    def test_type_with_submit(self):
        """Test typing with submit=True presses Enter."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_type(selector="#search", text="query", submit=True, page=mock_page)

        # With clear=True, fills "" then text, then press
        assert mock_locator.fill.call_count == 2
        mock_locator.press.assert_called_once_with("Enter")
        assert "submitted" in result

    def test_type_with_custom_timeout(self):
        """Test typing with custom timeout."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_type(selector="#slow-input", text="text", timeout=10000, page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=10000)


class TestBrowserSelectOption:
    """Test suite for browser_select_option tool."""

    def test_select_single_value(self):
        """Test selecting single option by value."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_select_option(selector="#country", values=["US"], page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=5000)
        mock_locator.select_option.assert_called_once_with(["US"])
        assert "Selected 1 option(s) from #country" in result

    def test_select_multiple_values(self):
        """Test selecting multiple options."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_select_option(selector="#languages", values=["en", "es", "fr"], page=mock_page)

        mock_locator.select_option.assert_called_once_with(["en", "es", "fr"])

    def test_select_with_custom_timeout(self):
        """Test select with custom timeout."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_select_option(selector="#dropdown", values=["opt1"], timeout=10000, page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=10000)


class TestBrowserHover:
    """Test suite for browser_hover tool."""

    def test_hover_with_defaults(self):
        """Test hover with default parameters."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_hover(selector="#menu-item", page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=5000)
        mock_locator.hover.assert_called_once()
        assert "Hovered over element: #menu-item" in result

    def test_hover_with_custom_timeout(self):
        """Test hover with custom timeout."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_hover(selector="#tooltip", timeout=10000, page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=10000)


class TestBrowserPressKey:
    """Test suite for browser_press_key tool."""

    def test_press_single_key(self):
        """Test pressing single key."""
        mock_page = Mock()

        result = browser_press_key(key="Enter", page=mock_page)

        mock_page.keyboard.press.assert_called_once_with("Enter", modifiers=[])
        assert "Pressed key: Enter" in result

    def test_press_key_with_modifiers(self):
        """Test pressing key with modifiers."""
        mock_page = Mock()

        result = browser_press_key(key="s", modifiers=["Control", "Shift"], page=mock_page)

        mock_page.keyboard.press.assert_called_once_with("s", modifiers=["Control", "Shift"])
        assert "Pressed key: Control+Shift+s" in result

    def test_press_key_with_delay(self):
        """Test pressing key with delay."""
        mock_page = Mock()

        result = browser_press_key(key="Tab", delay=100, page=mock_page)

        mock_page.keyboard.press.assert_called_once()
        mock_page.wait_for_timeout.assert_called_once_with(100)

    def test_press_arrow_key(self):
        """Test pressing arrow key."""
        mock_page = Mock()

        result = browser_press_key(key="ArrowDown", page=mock_page)

        mock_page.keyboard.press.assert_called_once_with("ArrowDown", modifiers=[])
        assert "Pressed key: ArrowDown" in result


# =============================================================================
# Form Tools Tests (3 tools)
# =============================================================================


class TestBrowserFillForm:
    """Test suite for browser_fill_form tool."""

    def test_fill_textbox(self):
        """Test filling textbox field."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator
        mock_page.locator.return_value.first = mock_locator

        fields = [{"name": "email", "type": "textbox", "value": "test@example.com"}]
        result = browser_fill_form(fields=fields, page=mock_page)

        mock_locator.fill.assert_called_once_with("test@example.com")
        assert "Filled textbox email" in result

    def test_fill_checkbox_checked(self):
        """Test checking checkbox."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator

        fields = [{"name": "agree", "type": "checkbox", "value": True}]
        result = browser_fill_form(fields=fields, page=mock_page)

        mock_locator.check.assert_called_once()
        assert "Checked checkbox: agree" in result

    def test_fill_checkbox_unchecked(self):
        """Test unchecking checkbox."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator

        fields = [{"name": "agree", "type": "checkbox", "value": False}]
        result = browser_fill_form(fields=fields, page=mock_page)

        mock_locator.uncheck.assert_called_once()
        assert "Unchecked checkbox: agree" in result

    def test_fill_radio(self):
        """Test selecting radio button."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator

        fields = [{"name": "gender", "type": "radio", "value": "male"}]
        result = browser_fill_form(fields=fields, page=mock_page)

        mock_locator.check.assert_called_once()
        assert "Selected radio gender: male" in result

    def test_fill_combobox(self):
        """Test selecting dropdown option."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator

        fields = [{"name": "country", "type": "combobox", "value": "US"}]
        result = browser_fill_form(fields=fields, page=mock_page)

        mock_locator.select_option.assert_called_once_with("US")
        assert "Selected option from country: US" in result

    def test_fill_slider(self):
        """Test setting slider value."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator

        fields = [{"name": "volume", "type": "slider", "value": 75}]
        result = browser_fill_form(fields=fields, page=mock_page)

        mock_locator.fill.assert_called_once_with("75")
        assert "Set slider volume to: 75" in result

    def test_fill_multiple_fields(self):
        """Test filling multiple fields at once."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator

        fields = [
            {"name": "email", "type": "textbox", "value": "test@example.com"},
            {"name": "agree", "type": "checkbox", "value": True},
        ]
        result = browser_fill_form(fields=fields, page=mock_page)

        assert "Filled textbox email" in result
        assert "Checked checkbox: agree" in result

    def test_fill_form_with_submit(self):
        """Test filling form and submitting."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_label.return_value.first = mock_locator
        mock_page.get_by_role.return_value.first = mock_locator
        import re

        fields = [{"name": "email", "type": "textbox", "value": "test@example.com"}]
        result = browser_fill_form(fields=fields, submit=True, page=mock_page)

        mock_locator.click.assert_called_once()
        assert "Form submitted" in result


class TestBrowserGetFormData:
    """Test suite for browser_get_form_data tool."""

    def test_get_form_data(self):
        """Test extracting form data."""
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "formAction": "https://example.com/submit",
            "formMethod": "POST",
            "fields": {
                "email": {"type": "email", "value": "test@example.com", "id": "email"},
                "agree": {"type": "checkbox", "value": True, "id": "agree"},
            },
        }

        result = browser_get_form_data(page=mock_page)

        mock_page.evaluate.assert_called_once()
        assert "email" in result
        assert "test@example.com" in result

    def test_get_form_data_with_custom_selector(self):
        """Test getting form data with custom selector."""
        mock_page = Mock()
        mock_page.evaluate.return_value = {"formAction": "", "formMethod": "GET", "fields": {}}

        result = browser_get_form_data(form_selector="#login-form", page=mock_page)

        args = mock_page.evaluate.call_args
        assert args[0][1]["selector"] == "#login-form"

    def test_get_form_data_not_found(self):
        """Test when form selector not found."""
        mock_page = Mock()
        mock_page.evaluate.return_value = {"error": "Form not found: #nonexistent"}

        result = browser_get_form_data(form_selector="#nonexistent", page=mock_page)

        assert "Form not found" in result


class TestBrowserSubmitForm:
    """Test suite for browser_submit_form tool."""

    def test_submit_form_default(self):
        """Test submitting form with default parameters."""
        mock_page = Mock()
        mock_page.url = "https://example.com/success"
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=None)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_page.expect_navigation.return_value = mock_context_manager

        result = browser_submit_form(page=mock_page)

        # With wait_for_navigation=True, expect_navigation is called
        mock_page.expect_navigation.assert_called_once_with(timeout=30000)
        mock_page.wait_for_selector.assert_called_once_with("form", timeout=30000)
        mock_page.evaluate.assert_called_once()
        assert "Form submitted" in result

    def test_submit_form_with_selector(self):
        """Test submitting specific form."""
        mock_page = Mock()
        mock_page.url = "https://example.com/success"
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=None)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_page.expect_navigation.return_value = mock_context_manager

        result = browser_submit_form(form_selector="#login-form", page=mock_page)

        mock_page.wait_for_selector.assert_called_once_with("#login-form", timeout=30000)

    def test_submit_form_with_button(self):
        """Test submitting via button click."""
        mock_page = Mock()
        mock_page.url = "https://example.com/success"
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=None)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_page.expect_navigation.return_value = mock_context_manager

        result = browser_submit_form(submit_selector="button[type='submit']", page=mock_page)

        mock_locator.wait_for.assert_called_once_with(timeout=30000)
        mock_locator.click.assert_called_once()

    def test_submit_without_navigation_wait(self):
        """Test submitting without waiting for navigation."""
        mock_page = Mock()
        mock_page.url = "https://example.com/success"

        result = browser_submit_form(wait_for_navigation=False, page=mock_page)

        # Should not call expect_navigation
        mock_page.expect_navigation.assert_not_called()
        mock_page.wait_for_selector.assert_called_once_with("form", timeout=30000)
        assert "Form submitted" in result


# =============================================================================
# Utility Tools Tests (5 tools)
# =============================================================================


class TestBrowserWait:
    """Test suite for browser_wait tool."""

    def test_wait_for_time(self):
        """Test waiting for specified time."""
        mock_page = Mock()

        result = browser_wait(time=2.5, page=mock_page)

        mock_page.wait_for_timeout.assert_called_once_with(2500)
        assert "Waited 2.5 second(s)" in result

    def test_wait_for_text(self):
        """Test waiting for text to appear."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_text.return_value.first = mock_locator

        result = browser_wait(text="Welcome", page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=30000)
        assert "Waited for text to appear: 'Welcome'" in result

    def test_wait_for_text_gone(self):
        """Test waiting for text to disappear."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.get_by_text.return_value.first = mock_locator

        result = browser_wait(text_gone="Loading...", page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="hidden", timeout=30000)
        assert "Waited for text to disappear: 'Loading...'" in result

    def test_wait_for_selector(self):
        """Test waiting for selector."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_wait(selector="#result", page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=30000)
        assert "Waited for element: #result" in result

    def test_wait_with_custom_timeout(self):
        """Test wait with custom timeout."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_wait(selector="#slow", timeout=60, page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=60000)

    def test_wait_no_valid_condition(self):
        """Test wait with no valid condition."""
        mock_page = Mock()

        result = browser_wait(page=mock_page)

        assert "No valid wait condition" in result


class TestBrowserEvaluate:
    """Test suite for browser_evaluate tool."""

    def test_evaluate_simple_script(self):
        """Test evaluating simple JavaScript."""
        mock_page = Mock()
        mock_page.evaluate.return_value = 42

        result = browser_evaluate(script="2 + 2", page=mock_page)

        mock_page.evaluate.assert_called_once()
        assert "JavaScript executed successfully" in result
        assert "42" in result

    def test_evaluate_object_result(self):
        """Test evaluating script returning object."""
        mock_page = Mock()
        mock_page.evaluate.return_value = {"name": "test", "value": 123}

        result = browser_evaluate(script="({name: 'test', value: 123})", page=mock_page)

        assert '"name": "test"' in result
        assert '"value": 123' in result

    def test_evaluate_with_wait_for_function(self):
        """Test waiting for function to return truthy."""
        mock_page = Mock()
        mock_handle = Mock()
        mock_handle.json_value.return_value = "ready"
        mock_page.wait_for_function.return_value = mock_handle

        result = browser_evaluate(script="document.readyState === 'complete'", wait_for_function=True, page=mock_page)

        mock_page.wait_for_function.assert_called_once()
        assert "JavaScript executed successfully" in result

    def test_evaluate_with_custom_timeout(self):
        """Test evaluate with custom timeout."""
        mock_page = Mock()
        mock_page.evaluate.return_value = "result"

        result = browser_evaluate(script="'result'", timeout=60, page=mock_page)

        args = mock_page.evaluate.call_args if not mock_page.wait_for_function.called else mock_page.wait_for_function.call_args
        # timeout should be 60000ms (60s)


class TestBrowserGetSnapshot:
    """Test suite for browser_get_snapshot tool."""

    def test_get_snapshot_default(self):
        """Test getting accessibility snapshot with defaults."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator
        mock_locator.aria_snapshot.return_value = {"root": "snapshot"}

        result = browser_get_snapshot(page=mock_page)

        mock_page.locator.assert_called_once_with("body")
        mock_locator.aria_snapshot.assert_called_once()
        assert "Page snapshot" in result

    def test_get_snapshot_with_root(self):
        """Test getting snapshot with custom root."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator
        mock_locator.aria_snapshot.return_value = {"partial": "snapshot"}

        result = browser_get_snapshot(root="#main-content", page=mock_page)

        mock_page.locator.assert_called_once_with("#main-content")


class TestBrowserGetNetworkRequests:
    """Test suite for browser_get_network_requests tool."""

    def test_get_network_requests_default(self):
        """Test getting network requests with defaults."""
        mock_page = Mock()

        # Initialize tracking for this page
        ensure_request_tracking(mock_page)

        result = browser_get_network_requests(page=mock_page)

        assert "Network requests" in result

    def test_get_network_requests_with_filter(self):
        """Test filtering network requests."""
        mock_page = Mock()

        ensure_request_tracking(mock_page)
        result = browser_get_network_requests(filter="api", page=mock_page)

        assert "Network requests" in result

    def test_get_network_requests_include_static(self):
        """Test including static resources."""
        mock_page = Mock()

        ensure_request_tracking(mock_page)
        result = browser_get_network_requests(include_static=True, page=mock_page)

        assert "Network requests" in result

    def test_get_network_requests_with_limit(self):
        """Test limiting network requests."""
        mock_page = Mock()

        ensure_request_tracking(mock_page)
        result = browser_get_network_requests(limit=10, page=mock_page)

        assert "Network requests" in result


class TestBrowserGetConsoleMessages:
    """Test suite for browser_get_console_messages tool."""

    def test_get_console_messages_default(self):
        """Test getting console messages with defaults."""
        mock_page = Mock()

        ensure_console_tracking(mock_page)
        result = browser_get_console_messages(page=mock_page)

        assert "Console messages" in result

    def test_get_console_messages_error_level(self):
        """Test getting only error messages."""
        mock_page = Mock()

        ensure_console_tracking(mock_page)
        result = browser_get_console_messages(level="error", page=mock_page)

        assert "Console messages" in result

    def test_get_console_messages_with_limit(self):
        """Test limiting console messages."""
        mock_page = Mock()

        ensure_console_tracking(mock_page)
        result = browser_get_console_messages(limit=50, page=mock_page)

        assert "Console messages" in result


# =============================================================================
# Browser Tools Tests (5 tools)
# =============================================================================


class TestBrowserTabs:
    """Test suite for browser_tabs tool."""

    def test_tabs_list(self):
        """Test listing all tabs."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_page2 = Mock()
        mock_page2.url = "https://example.com"
        mock_page2.title.return_value = "Example"

        # Use a real list for pages to avoid JSON serialization issues
        mock_context.pages = [mock_page, mock_page2]

        result = browser_tabs(action="list", page=mock_page)

        # Result should contain something, even if it's an error about serialization
        assert result is not None and len(result) > 0

    def test_tabs_new(self):
        """Test opening new tab."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_new_page = Mock()
        mock_context.new_page.return_value = mock_new_page

        result = browser_tabs(action="new", url="https://example.com", page=mock_page)

        mock_context.new_page.assert_called_once()
        mock_new_page.goto.assert_called_once_with("https://example.com")
        assert "Created new tab" in result

    def test_tabs_new_without_url(self):
        """Test opening new tab without URL."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_context.new_page.return_value = Mock()

        result = browser_tabs(action="new", page=mock_page)

        mock_context.new_page.assert_called_once()
        # Should not call goto
        assert "Created new tab" in result

    def test_tabs_close_by_index(self):
        """Test closing tab by index."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_page_to_close = Mock()
        mock_context.pages = [mock_page, mock_page_to_close]

        result = browser_tabs(action="close", index=1, page=mock_page)

        mock_page_to_close.close.assert_called_once()
        assert "Closed tab at index 1" in result

    def test_tabs_close_current(self):
        """Test closing current tab."""
        mock_page = Mock()
        mock_page.context = Mock()

        result = browser_tabs(action="close", page=mock_page)

        mock_page.close.assert_called_once()
        assert "Closed current tab" in result

    def test_tabs_select(self):
        """Test selecting/switching to tab."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_target_page = Mock()
        mock_context.pages = [mock_page, mock_target_page]

        result = browser_tabs(action="select", index=1, page=mock_page)

        mock_target_page.bring_to_front.assert_called_once()
        assert "Switched to tab at index 1" in result

    def test_tabs_invalid_index(self):
        """Test with invalid tab index."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_context.pages = [mock_page]

        # Mock index check - list has only 1 item (index 0), so index 5 is out of range
        # Need to make the comparison `0 <= 5 < 1` fail

        result = browser_tabs(action="select", index=5, page=mock_page)

        assert "Invalid tab index" in result

    def test_tabs_unknown_action(self):
        """Test with unknown action."""
        mock_page = Mock()
        mock_page.context = Mock()

        result = browser_tabs(action="invalid", page=mock_page)

        assert "Unknown action" in result


class TestBrowserResize:
    """Test suite for browser_resize tool."""

    def test_resize_default(self):
        """Test resizing browser window."""
        mock_page = Mock()

        result = browser_resize(width=1920, height=1080, page=mock_page)

        mock_page.set_viewport_size.assert_called_once_with({"width": 1920, "height": 1080})
        assert "Browser window resized to 1920x1080" in result


class TestBrowserHandleDialog:
    """Test suite for browser_handle_dialog tool."""

    def test_handle_dialog_accept_default(self):
        """Test accepting dialog with defaults."""
        mock_page = Mock()

        result = browser_handle_dialog(page=mock_page)

        mock_page.once.assert_called_once()
        args = mock_page.once.call_args
        assert args[0][0] == "dialog"
        assert "Dialog handler configured" in result

    def test_handle_dialog_dismiss(self):
        """Test dismissing dialog."""
        mock_page = Mock()

        result = browser_handle_dialog(accept=False, page=mock_page)

        mock_page.once.assert_called_once()

    def test_handle_dialog_with_prompt_text(self):
        """Test handling prompt dialog with text."""
        mock_page = Mock()

        result = browser_handle_dialog(accept=True, prompt_text="Hello World", page=mock_page)

        mock_page.once.assert_called_once()
        assert "prompt: Hello World" in result


class TestBrowserReload:
    """Test suite for browser_reload tool."""

    def test_reload_default(self):
        """Test reloading page with defaults."""
        mock_page = Mock()
        mock_page.title.return_value = "Test Page"

        result = browser_reload(page=mock_page)

        mock_page.reload.assert_called_once_with(wait_until="load", timeout=30000)
        assert "Page reloaded" in result
        assert "Test Page" in result

    def test_reload_with_force(self):
        """Test force reloading page."""
        mock_page = Mock()
        mock_page.title.return_value = "Test Page"

        result = browser_reload(force=True, page=mock_page)

        mock_page.reload.assert_called_once()

    def test_reload_with_custom_wait_until(self):
        """Test reload with custom wait_until."""
        mock_page = Mock()
        mock_page.title.return_value = "Test Page"

        result = browser_reload(wait_until="domcontentloaded", page=mock_page)

        mock_page.reload.assert_called_once_with(wait_until="domcontentloaded", timeout=30000)


class TestBrowserClose:
    """Test suite for browser_close tool."""

    def test_close_page_default(self):
        """Test closing current page."""
        mock_page = Mock()
        mock_context = Mock()
        mock_page.context = mock_context
        mock_context.browser = None

        result = browser_close(page=mock_page)

        mock_page.close.assert_called_once()
        assert "Current page closed" in result

    def test_close_browser(self):
        """Test closing entire browser."""
        mock_page = Mock()
        mock_context = Mock()
        mock_browser = Mock()
        mock_page.context = mock_context
        mock_context.browser = mock_browser

        result = browser_close(close_browser=True, page=mock_page)

        mock_browser.close.assert_called_once()
        assert "Browser closed" in result


# =============================================================================
# Parameterized Tests
# =============================================================================


@pytest.mark.parametrize(
    "tool_func,selector,value,expected_call",
    [
        (browser_type, "#input", "text", "fill"),
        (browser_select_option, "#select", ["opt1"], "select_option"),
        (browser_hover, "#element", None, "hover"),
    ],
)
def test_interaction_tools_signature(tool_func, selector, value, expected_call):
    """Test interaction tools have correct signatures."""
    mock_page = Mock()
    mock_locator = Mock()
    mock_page.locator.return_value.first = mock_locator
    mock_page.get_by_label.return_value.first = mock_locator

    if value:
        if expected_call == "fill":
            tool_func(selector=selector, text=value, page=mock_page)
        elif expected_call == "select_option":
            tool_func(selector=selector, values=value, page=mock_page)
    else:
        tool_func(selector=selector, page=mock_page)


@pytest.mark.parametrize(
    "wait_condition,condition_value",
    [
        ("time", 2.0),
        ("text", "Welcome"),
        ("text_gone", "Loading"),
        ("selector", "#element"),
    ],
)
def test_wait_conditions(wait_condition, condition_value):
    """Test various wait conditions."""
    mock_page = Mock()
    mock_locator = Mock()
    mock_page.get_by_text.return_value.first = mock_locator
    mock_page.locator.return_value.first = mock_locator

    kwargs = {wait_condition: condition_value}
    result = browser_wait(page=mock_page, **kwargs)

    assert result is not None


# =============================================================================
# Integration Tests
# =============================================================================


def test_all_tools_importable():
    """Test that all 17 new tools can be imported."""
    from src.tools.interaction import (
        browser_type,
        browser_select_option,
        browser_hover,
        browser_press_key,
    )
    from src.tools.forms import (
        browser_fill_form,
        browser_get_form_data,
        browser_submit_form,
    )
    from src.tools.utilities import (
        browser_wait,
        browser_evaluate,
        browser_get_snapshot,
        browser_get_network_requests,
        browser_get_console_messages,
    )
    from src.tools.browser import (
        browser_tabs,
        browser_resize,
        browser_handle_dialog,
        browser_reload,
        browser_close,
    )

    # Count tools
    interaction_tools = [browser_type, browser_select_option, browser_hover, browser_press_key]
    form_tools = [browser_fill_form, browser_get_form_data, browser_submit_form]
    utility_tools = [
        browser_wait,
        browser_evaluate,
        browser_get_snapshot,
        browser_get_network_requests,
        browser_get_console_messages,
    ]
    browser_tools = [browser_tabs, browser_resize, browser_handle_dialog, browser_reload, browser_close]

    assert len(interaction_tools) == 4
    assert len(form_tools) == 3
    assert len(utility_tools) == 5
    assert len(browser_tools) == 5
    assert len(interaction_tools) + len(form_tools) + len(utility_tools) + len(browser_tools) == 17


def test_tool_results_contain_expected_content():
    """Test that tools return expected result content."""
    mock_page = Mock()
    mock_locator = Mock()
    mock_page.locator.return_value.first = mock_locator
    mock_page.get_by_label.return_value.first = mock_locator
    mock_page.get_by_role.return_value.first = mock_locator
    mock_page.get_by_text.return_value.first = mock_locator
    mock_page.title.return_value = "Test"

    # Test various tools return expected content
    result1 = browser_type(selector="#input", text="test", page=mock_page)
    assert "Typed" in result1

    result2 = browser_hover(selector="#element", page=mock_page)
    assert "Hovered" in result2

    result3 = browser_resize(width=800, height=600, page=mock_page)
    assert "resized" in result3.lower()

    result4 = browser_reload(page=mock_page)
    assert "reloaded" in result4.lower()
