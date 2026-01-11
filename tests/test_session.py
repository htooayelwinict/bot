"""Tests for Playwright session management."""

import warnings
import pytest
from pathlib import Path

# Suppress deprecation warnings for this test file
warnings.filterwarnings("ignore", category=DeprecationWarning)

from src.session import (
    FacebookSessionManager,
    set_global_session,
    get_current_page,
    get_current_context,
    get_global_session,
)

# Alias for backward compatibility with tests
PlaywrightSession = FacebookSessionManager
set_session = set_global_session
get_current_session = get_global_session


class TestPlaywrightSession:
    """Test suite for PlaywrightSession class."""

    def test_session_initialization(self):
        """Test that session initializes with correct defaults."""
        session = PlaywrightSession()
        assert session.profile_dir == Path("./profiles/facebook")
        assert session.headless is False

    def test_session_with_custom_profile(self, tmp_path):
        """Test session initialization with custom profile path."""
        custom_path = tmp_path / "custom-profile"
        session = PlaywrightSession(profile_dir=custom_path)
        assert session.profile_dir == custom_path

    def test_cleanup_lock_files(self, tmp_path):
        """Test lock file cleanup."""
        # Create mock lock files
        profile_path = tmp_path / "test-profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        (profile_path / "SingletonLock").touch()
        (profile_path / "SingletonSocket").touch()

        session = PlaywrightSession(profile_dir=profile_path)
        session._cleanup_lock_files()

        assert not (profile_path / "SingletonLock").exists()
        assert not (profile_path / "SingletonSocket").exists()

    def test_getters_before_login(self):
        """Test that getters return None before login."""
        session = PlaywrightSession()
        assert session.get_page() is None
        assert session.get_context() is None


class TestGlobalSessionManagement:
    """Test suite for global session management."""

    def test_set_and_get_session(self):
        """Test setting and getting global session."""
        # Clear any existing session
        set_session(None)

        session = PlaywrightSession()
        set_session(session)

        assert get_current_session() is session

    def test_get_current_page_without_session(self):
        """Test getting current page without session."""
        set_session(None)
        assert get_current_page() is None

    def test_get_current_context_without_session(self):
        """Test getting current context without session."""
        set_session(None)
        assert get_current_context() is None
