"""Tests for navigation tools."""

import pytest
from unittest.mock import Mock, MagicMock

from src.tools.navigation import (
    browser_navigate,
    browser_navigate_back,
    browser_screenshot,
    browser_get_page_info,
)


class TestBrowserNavigate:
    """Test suite for browser_navigate tool."""

    def test_navigate_with_defaults(self):
        """Test navigation with default parameters."""
        mock_page = Mock()
        mock_page.title.return_value = "Test Page"
        mock_page.url = "https://example.com"

        result = browser_navigate(url="https://example.com", page=mock_page)

        mock_page.goto.assert_called_once_with("https://example.com", wait_until="load", timeout=30000)
        assert "Navigated to https://example.com" in result
        assert "Test Page" in result
        assert "https://example.com" in result

    def test_navigate_with_custom_wait(self):
        """Test navigation with custom wait_until."""
        mock_page = Mock()
        mock_page.title.return_value = "Test Page"
        mock_page.url = "https://example.com"

        result = browser_navigate(url="https://example.com", wait_until="domcontentloaded", page=mock_page)

        mock_page.goto.assert_called_once_with("https://example.com", wait_until="domcontentloaded", timeout=30000)

    def test_navigate_with_custom_timeout(self):
        """Test navigation with custom timeout."""
        mock_page = Mock()
        mock_page.title.return_value = "Test Page"
        mock_page.url = "https://example.com"

        result = browser_navigate(url="https://example.com", timeout=60000, page=mock_page)

        mock_page.goto.assert_called_once_with("https://example.com", wait_until="load", timeout=60000)


class TestBrowserNavigateBack:
    """Test suite for browser_navigate_back tool."""

    def test_navigate_back(self):
        """Test navigating back."""
        mock_page = Mock()
        mock_page.url = "https://example.com/back"

        result = browser_navigate_back(page=mock_page)

        mock_page.go_back.assert_called_once()
        assert "Navigated back" in result
        assert "https://example.com/back" in result


class TestBrowserScreenshot:
    """Test suite for browser_screenshot tool."""

    def test_screenshot_with_defaults(self, tmp_path):
        """Test screenshot with default parameters."""
        from unittest.mock import patch

        mock_page = Mock()
        mock_page.screenshot = Mock()

        # Mock Path.stat() to return a fake file size
        mock_stat = Mock()
        mock_stat.st_size = 12345

        with patch("pathlib.Path.stat", return_value=mock_stat):
            result = browser_screenshot(page=mock_page)

            # Check screenshot was called
            mock_page.screenshot.assert_called_once()
            call_args = mock_page.screenshot.call_args

            assert "path" in call_args.kwargs
            assert call_args.kwargs["type"] == "png"
            assert call_args.kwargs["full_page"] is False
            assert "Screenshot saved" in result
            assert "12 KB" in result

    def test_screenshot_jpeg_with_quality(self, tmp_path):
        """Test JPEG screenshot with quality setting."""
        from unittest.mock import patch

        mock_page = Mock()
        mock_page.screenshot = Mock()

        # Mock Path.stat() to return a fake file size
        mock_stat = Mock()
        mock_stat.st_size = 50000

        with patch("pathlib.Path.stat", return_value=mock_stat):
            result = browser_screenshot(type="jpeg", quality=90, page=mock_page)

            call_args = mock_page.screenshot.call_args
            assert call_args.kwargs["type"] == "jpeg"
            assert call_args.kwargs["quality"] == 90


class TestBrowserGetPageInfo:
    """Test suite for browser_get_page_info tool."""

    def test_get_page_info(self):
        """Test getting page information."""
        mock_page = Mock()

        # Mock evaluate to return page info
        mock_page.evaluate.return_value = {
            "url": "https://example.com",
            "title": "Test Page",
            "domain": "example.com",
            "path": "/test",
            "readyState": "complete",
            "scrollX": 0,
            "scrollY": 100,
            "viewport": {"width": 1920, "height": 1080},
        }

        result = browser_get_page_info(page=mock_page)

        mock_page.evaluate.assert_called_once()
        assert "https://example.com" in result
        assert "Test Page" in result
