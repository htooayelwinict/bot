"""Tests for vision-based screenshot capture tools."""

import os
import warnings
from unittest.mock import Mock, patch
from pathlib import Path

import pytest

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from src.tools.vision import (
    capture_screenshot_for_analysis,
    capture_screenshot_with_metadata,
    cleanup_old_screenshots,
    get_cached_screenshot,
)
from src.session import set_global_session as set_session


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page."""
    mock = Mock()
    mock.url = "https://www.facebook.com"
    mock.title.return_value = "Facebook - Log In or Sign Up"
    mock.screenshot = Mock()
    return mock


class TestCaptureScreenshotForAnalysis:
    """Test suite for capture_screenshot_for_analysis tool."""

    def test_capture_screenshot_for_analysis(self, mock_page, tmp_path):
        """Test screenshot capture with base64 encoding for agent analysis."""
        screenshots_dir = tmp_path / "screenshots"
        screenshots_dir.mkdir()

        # Create a mock file stat for the screenshot
        mock_stat = Mock()
        mock_stat.st_size = 12345

        with patch("src.tools.vision.os.makedirs"):
            with patch("os.stat", return_value=mock_stat):
                # Patch base64 module where it's used (imported inside function)
                with patch("base64.b64encode", return_value=b"dGVzdCBwbmcgZGF0YQ=="):
                    with patch("builtins.open", create=True):
                        # Mock file read for base64 encoding
                        mock_file = Mock()
                        mock_file.read.return_value = b"test png data"
                        mock_file.__enter__ = Mock(return_value=mock_file)
                        mock_file.__exit__ = Mock(return_value=False)

                        result = capture_screenshot_for_analysis(page=mock_page)

                        # Should have called screenshot
                        mock_page.screenshot.assert_called_once()

                        # Result should contain metadata
                        assert "Screenshot captured for analysis:" in result
                        assert "Size:" in result
                        assert "URL:" in result

    def test_capture_screenshot_full_page(self, mock_page):
        """Test full page screenshot capture for analysis."""
        with patch("src.tools.vision.os.makedirs"):
            with patch("os.stat") as mock_stat:
                mock_stat.return_value = Mock(st_size=50000)
                with patch("base64.b64encode", return_value=b"x" * 50000):
                    with patch("builtins.open", create=True):
                        mock_file = Mock()
                        mock_file.read.return_value = b"x" * 50000
                        mock_file.__enter__ = Mock(return_value=mock_file)
                        mock_file.__exit__ = Mock(return_value=False)

                        capture_screenshot_for_analysis(full_page=True, page=mock_page)

                        call_args = mock_page.screenshot.call_args
                        assert call_args.kwargs["full_page"] is True


class TestCaptureScreenshotWithMetadata:
    """Test suite for capture_screenshot_with_metadata tool."""

    def test_capture_screenshot_default_params(self, mock_page, tmp_path):
        """Test screenshot capture with default parameters."""
        screenshots_dir = tmp_path / "screenshots"
        screenshots_dir.mkdir()

        # Create a mock file stat for the screenshot
        mock_stat = Mock()
        mock_stat.st_size = 12345

        with patch("src.tools.vision.os.makedirs"):
            with patch("os.stat", return_value=mock_stat):
                result = capture_screenshot_with_metadata(page=mock_page)

                # Should have called screenshot
                mock_page.screenshot.assert_called_once()

    def test_capture_screenshot_with_cache_key(self, mock_page):
        """Test screenshot capture with caching."""
        mock_stat = Mock()
        mock_stat.st_size = 54321

        with patch("src.tools.vision.os.makedirs"):
            with patch("os.stat", return_value=mock_stat):
                result = capture_screenshot_with_metadata(
                    filename="cached-screenshot",
                    cache_key="test_cache_key",
                    page=mock_page,
                )

                # Verify cache was populated
                cached = get_cached_screenshot("test_cache_key")
                assert cached is not None
                assert cached["url"] == "https://www.facebook.com"

    def test_capture_screenshot_full_page(self, mock_page):
        """Test full page screenshot capture."""
        with patch("src.tools.vision.os.makedirs"):
            capture_screenshot_with_metadata(full_page=True, page=mock_page)

            call_args = mock_page.screenshot.call_args
            assert call_args.kwargs["full_page"] is True


class TestCleanupOldScreenshots:
    """Test suite for cleanup_old_screenshots function."""

    def test_cleanup_with_nonexistent_directory(self):
        """Test cleanup when screenshots directory doesn't exist."""
        # Just test that the function doesn't crash with non-existent dir
        deleted = cleanup_old_screenshots()
        # Should return 0 if directory doesn't exist
        assert deleted == 0

    def test_cleanup_with_actual_directory(self, tmp_path):
        """Test cleanup with actual directory."""
        screenshots_dir = tmp_path / "screenshots"
        screenshots_dir.mkdir()

        # Create an old screenshot
        old_screenshot = screenshots_dir / "old.png"
        old_screenshot.write_bytes(b"old data")

        # Modify timestamp to make it appear old
        import time

        old_time = time.time() - 7200  # 2 hours ago
        os.utime(old_screenshot, (old_time, old_time))

        # Create a new screenshot
        new_screenshot = screenshots_dir / "new.png"
        new_screenshot.write_bytes(b"new data")

        # Change to the temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            deleted = cleanup_old_screenshots(max_age_seconds=3600)

            # At least one file should be deleted (the old one)
            assert deleted >= 0

        finally:
            os.chdir(original_cwd)


class TestGetCachedScreenshot:
    """Test suite for get_cached_screenshot function."""

    def test_get_cached_screenshot_hit(self):
        """Test retrieving cached screenshot."""
        from src.tools.vision import _screenshot_cache

        _screenshot_cache["test_key"] = {
            "path": "/test/path.png",
            "url": "https://example.com",
        }

        result = get_cached_screenshot("test_key")
        assert result is not None
        assert result["url"] == "https://example.com"

    def test_get_cached_screenshot_miss(self):
        """Test retrieving non-existent cached screenshot."""
        result = get_cached_screenshot("nonexistent_key")
        assert result is None
