"""Tests for interaction tools."""

import pytest
from unittest.mock import Mock, MagicMock

from src.tools.interaction import browser_click


class TestBrowserClick:
    """Test suite for browser_click tool."""

    def test_click_with_defaults(self):
        """Test click with default parameters."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_click(selector="button.submit", page=mock_page)

        mock_page.locator.assert_called_once_with("button.submit")
        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=5000)
        mock_locator.click.assert_called_once_with(button="left", modifiers=[], force=False)
        assert "Clicked on element: button.submit" in result

    def test_click_with_right_button(self):
        """Test right-click."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_click(selector="button.context", button="right", page=mock_page)

        mock_locator.click.assert_called_once_with(button="right", modifiers=[], force=False)

    def test_click_with_modifiers(self):
        """Test click with modifier keys."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_click(
            selector="a.link",
            modifiers=["Control", "Shift"],
            page=mock_page,
        )

        mock_locator.click.assert_called_once_with(button="left", modifiers=["Control", "Shift"], force=False)

    def test_double_click(self):
        """Test double click."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_click(selector="button.dbl", double_click=True, page=mock_page)

        mock_locator.dblclick.assert_called_once_with(button="left", modifiers=[], force=False)

    def test_click_with_force(self):
        """Test click with force option."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_click(selector="button.hidden", force=True, page=mock_page)

        mock_locator.click.assert_called_once_with(button="left", modifiers=[], force=True)

    def test_click_with_custom_timeout(self):
        """Test click with custom timeout."""
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value.first = mock_locator

        result = browser_click(selector="button.slow", timeout=10000, page=mock_page)

        mock_locator.wait_for.assert_called_once_with(state="visible", timeout=10000)
