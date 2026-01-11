"""Facebook session management with HITL login.

Consolidated session module providing persistent browser profiles,
session persistence (cookies/storage state), and restoration.

Matches HumanInLoopLogin behavior from human-in-loop-login.ts:
- 3-minute manual login with progress polling
- SingletonLock cleanup for persistent contexts
- Cookie and storage state persistence
- Login status detection via DOM selectors
"""

import json
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, BrowserType


# =============================================================================
# Configuration (matches human-in-loop-login.ts)
# =============================================================================

DEFAULT_PROFILE_DIR = Path("./profiles/facebook")
BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-extensions-file-access-check",
    "--disable-extensions-http-throttling",
    "--disable-ipc-flooding-protection",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
]

LOGIN_SELECTORS = [
    'input[type="email"]',
    'input[type="password"]',
    'input[name="email"]',
    'input[name="pass"]',
    '[data-testid="royal_email"]',
]

LOGGED_IN_SELECTORS = [
    '[aria-label*="Account"]',
    '[data-testid="bluebar_profile_root"]',
    'a[href*="/me"][role="link"]',
    '[data-visualcompletion="ignore-dynamic"] svg[aria-label="Account"]',
    '[role="complementary"]',
    '[role="main"]',
]


# =============================================================================
# Session Manager
# =============================================================================

class FacebookSessionManager:
    """Manages Facebook profile persistence and restoration.

    Matches HumanInLoopLogin behavior from human-in-loop-login.ts:
    - 3-minute manual login with progress polling
    - SingletonLock cleanup for persistent contexts
    - Cookie and storage state persistence
    - Login status detection via DOM selectors
    """

    def __init__(
        self,
        profile_dir: Path = DEFAULT_PROFILE_DIR,
        headless: bool = False,
    ):
        self.profile_dir = Path(profile_dir)
        self.headless = headless
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    # -------------------------------------------------------------------------
    # Public API (matches human-in-loop-login.ts interface)
    # -------------------------------------------------------------------------

    def get_or_create_session(self, browser_type: BrowserType) -> tuple[BrowserContext, Page, bool]:
        """Get existing session or create new one.

        Args:
            browser_type: Playwright BrowserType (e.g., playwright.chromium)

        Returns:
            (context, page, was_restored) - was_restored is True if session was restored
        """
        if self._has_saved_session():
            context, page, restored = self._restore_session(browser_type)
            if restored:
                return context, page, True

        return self._create_new_session(browser_type)

    def start_login(self) -> bool:
        """Start manual login flow (3-minute timeout).

        Returns:
            True if login successful, False if timeout
        """
        from playwright.sync_api import sync_playwright

        print("🚀 Starting human-in-the-loop login process...")
        print("⏱️  You have 3 minutes to log in manually")

        with sync_playwright() as p:
            self.context, self.page, _ = self._create_new_session(p.chromium)

            if not self._go_to_facebook():
                return False

            login_success = self._wait_for_login()

            if login_success:
                print("✅ Login successful! Saving session...")
                self.save_session()
                return True
            else:
                print("❌ Login timeout or failed")
                return False

    def restore_session(self, browser_type: BrowserType) -> bool:
        """Restore saved session.

        Args:
            browser_type: Playwright BrowserType

        Returns:
            True if session valid and logged in, False otherwise
        """
        print("🔄 Attempting to restore saved session...")

        if not self._has_saved_session():
            print("❌ No saved session found")
            return False

        self.context, self.page, _ = self._restore_session(browser_type)

        if not self._go_to_facebook():
            self.close()
            return False

        if self._is_logged_in():
            print("✅ Successfully restored logged-in session")
            return True
        else:
            print("❌ Session expired - need to log in again")
            self.close()
            return False

    def save_session(self) -> None:
        """Save current session (cookies and storage state)."""
        if not self.context:
            return

        self.profile_dir.mkdir(parents=True, exist_ok=True)

        cookies = self.context.cookies()
        cookies_file = self.profile_dir / "cookies.json"
        cookies_file.write_text(json.dumps(cookies, indent=2))
        print(f"💾 Saved {len(cookies)} cookies to {cookies_file}")

        state = self.context.storage_state()
        state_file = self.profile_dir / "state.json"
        state_file.write_text(json.dumps(state, indent=2))
        print(f"💾 Saved storage state to {state_file}")

    def close(self) -> None:
        """Close browser context."""
        if self.page:
            self.page.close()
            self.page = None

        if self.context:
            self.context.close()
            self.context = None

    def get_page(self) -> Optional[Page]:
        """Get the current page."""
        return self.page

    def get_context(self) -> Optional[BrowserContext]:
        """Get the current browser context."""
        return self.context

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _has_saved_session(self) -> bool:
        """Check if there's a saved session."""
        cookies_file = self.profile_dir / "cookies.json"
        state_file = self.profile_dir / "state.json"
        return cookies_file.exists() or state_file.exists()

    def _launch_context(self, browser_type: BrowserType, *, restored: bool) -> tuple[BrowserContext, Page, bool]:
        """Launch browser context with persistent profile."""
        if not restored:
            print("🚀 Creating new browser session...")

        self._cleanup_lock_files()

        self.context = browser_type.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=BROWSER_ARGS,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation", "notifications"],
            ignore_https_errors=True,
        )

        pages = self.context.pages
        self.page = pages[0] if pages else self.context.new_page()

        return self.context, self.page, restored

    def _create_new_session(self, browser_type: BrowserType) -> tuple[BrowserContext, Page, bool]:
        """Create a new browser session with persistent context."""
        return self._launch_context(browser_type, restored=False)

    def _restore_session(self, browser_type: BrowserType) -> tuple[BrowserContext, Page, bool]:
        """Restore existing session from profile directory."""
        return self._launch_context(browser_type, restored=True)

    def _cleanup_lock_files(self) -> None:
        """Clean up Chrome lock files (prevents SingletonLock errors)."""
        for lock_file in ["SingletonLock", "SingletonSocket"]:
            try:
                (self.profile_dir / lock_file).unlink(missing_ok=True)
            except Exception:
                pass

    def _go_to_facebook(self) -> bool:
        """Navigate to Facebook with retry logic."""
        if not self.page:
            return False

        print("📍 Navigating to Facebook...")
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                print(f"   Attempt {attempt} of {max_attempts}...")
                self.page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=60000)
                time.sleep(2)

                page_title = self.page.title()
                if "Facebook" in page_title or "Log In" in page_title:
                    print("✅ Facebook page loaded successfully")
                    return True
            except Exception as e:
                print(f"   ⚠️ Navigation attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    time.sleep(3)

        print("❌ Failed to navigate to Facebook")
        return False

    def _wait_for_login(self) -> bool:
        """Wait for user to complete manual login (3-minute timeout)."""
        if not self.page:
            return False

        max_wait_time = 180000  # 3 minutes in milliseconds
        check_interval = 2000
        elapsed = 0

        print("⏳ Waiting for you to log in...")
        print("   Browser window is open - please log in manually")

        while elapsed < max_wait_time:
            if self._is_logged_in():
                return True

            remaining_seconds = (max_wait_time - elapsed) // 1000
            if elapsed % 10000 == 0:
                print(f"   ⏰ Time remaining: {remaining_seconds}s")

            time.sleep(check_interval / 1000)
            elapsed += check_interval

        return False

    def _is_logged_in(self) -> bool:
        """Check if user is logged in to Facebook."""
        return _check_login_status(self.page)


# =============================================================================
# Standalone Functions (for test fixtures)
# =============================================================================

def _check_login_status(page: Optional[Page]) -> bool:
    """Check if user is logged in to Facebook."""
    if not page:
        return False

    # Check for login form (means NOT logged in)
    for selector in LOGIN_SELECTORS:
        try:
            if page.query_selector(selector):
                return False
        except Exception:
            continue

    # Check for logged-in indicators
    for selector in LOGGED_IN_SELECTORS:
        try:
            if page.query_selector(selector):
                return True
        except Exception:
            continue

    return False


def check_login_status(page: Page) -> bool:
    """Check if user is logged in to Facebook."""
    return _check_login_status(page)


def wait_for_login(page: Page, max_wait_seconds: int = 180) -> bool:
    """Wait for user to complete Facebook login.

    Args:
        page: Playwright page object
        max_wait_seconds: Maximum time to wait (default 180s)

    Returns:
        True if login detected, False if timeout
    """
    print("\n" + "=" * 60)
    print("⚠️  NOT LOGGED IN TO FACEBOOK")
    print("=" * 60)
    print("\nPlease log in manually:")
    print("1. Browser window should be visible")
    print("2. Complete Facebook login in the browser")
    print("3. Script will continue automatically after login\n")
    print(f"Waiting for login (max {max_wait_seconds} seconds)...")
    print("=" * 60 + "\n")

    elapsed = 0
    check_interval = 2

    while elapsed < max_wait_seconds:
        if check_login_status(page):
            print("✅ Login detected!\n")
            return True

        time.sleep(check_interval)
        elapsed += check_interval

        if elapsed % 10 == 0:
            remaining = max_wait_seconds - elapsed
            print(f"   ⏰ Still waiting... ({remaining}s remaining)")

    print("❌ Login timeout\n")
    return False


# =============================================================================
# Global Session Management (for tool decorators)
# =============================================================================

_global_session: Optional[FacebookSessionManager] = None


def set_global_session(session: Optional[FacebookSessionManager]) -> None:
    """Set the global session manager for tool access."""
    global _global_session
    _global_session = session


def get_global_session() -> Optional[FacebookSessionManager]:
    """Get the current global session manager."""
    return _global_session


def get_current_page() -> Optional[Page]:
    """Get the current page from the global session."""
    return getattr(_global_session, "page", None)


def get_current_context() -> Optional[BrowserContext]:
    """Get the current context from the global session."""
    return getattr(_global_session, "context", None)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Alias for backward compatibility
FacebookProfileManager = FacebookSessionManager
PlaywrightSession = FacebookSessionManager


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FacebookSessionManager",
    "FacebookProfileManager",
    "PlaywrightSession",
    "check_login_status",
    "wait_for_login",
    "set_global_session",
    "get_global_session",
    "get_current_page",
    "get_current_context",
    "DEFAULT_PROFILE_DIR",
    "BROWSER_ARGS",
    "LOGIN_SELECTORS",
    "LOGGED_IN_SELECTORS",
]
