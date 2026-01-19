# Phase 4: Additional Adapters

**Duration:** 2 days
**Status:** Pending
**Dependencies:** Phase 1, Phase 2, Phase 3 complete

## Objective

Demonstrate the extensibility of the plugin architecture by creating additional site adapters. This validates that the architecture supports multiple sites and provides templates for third-party developers.

## Prerequisites

- Phase 1 complete (core architecture)
- Phase 2 complete (Facebook adapter working)
- Phase 3 complete (MultiSiteAgent working)
- Plugin loading functional

## Tasks

### 4.1 Create Generic Adapter

**File:** `src/plugins/generic/adapter.py`
**Effort:** 2-3 hours

**Purpose:** Fallback adapter for unknown sites with minimal functionality

**Implementation Steps:**

#### Step 1: Basic Structure
```python
from typing import Any, List
from playwright.async_api import Page, BrowserContext

from src.core.protocols import SiteAdapter, CrawlConfig, AuthResult

class GenericAdapter:
    """Generic/fallback adapter for unknown sites.

    Provides minimal functionality:
    - Basic navigation
    - No automatic login
    - No site-specific tools
    - Universal selectors only
    """

    site_name: str = "Generic"
    site_domain: str = "*"
    __version__ = "1.0.0"

    def __init__(self, config: CrawlConfig):
        self.config = config
```

#### Step 2: Configuration Methods
```python
def get_default_config(self) -> CrawlConfig:
    """Get default generic configuration."""
    return CrawlConfig(
        base_url="https://example.com",
        timeout=30000,
        headless=True,
        user_agent=None,
        viewport={"width": 1920, "height": 1080},
    )
```

#### Step 3: Authentication Methods
```python
async def login(
    self,
    page: Page,
    username: str,
    password: str
) -> AuthResult:
    """Generic adapter does not support automatic login.

    User must handle login manually or implement custom adapter.
    """
    return AuthResult(
        success=False,
        message="Generic adapter does not support automatic login. Please log in manually or implement a custom adapter.",
        session_data=None,
    )

def is_logged_in(self, page: Page) -> bool:
    """Generic adapter assumes logged in.

    Custom adapters should implement proper login detection.
    """
    return True

def get_login_url(self) -> str:
    """No specific login URL for generic adapter."""
    return ""
```

#### Step 4: Selectors
```python
def get_selectors(self) -> dict[str, str]:
    """Return generic/universal selectors.

    Custom adapters should override with site-specific selectors.
    """
    return {
        # Very basic selectors
        "link": "a",
        "button": "button",
        "input": "input",
        "form": "form",
    }
```

#### Step 5: Tools
```python
def get_tools(self) -> List[Any]:
    """Generic adapter has no site-specific tools.

    All browser tools (universal) are still available.
    """
    return []
```

#### Step 6: Lifecycle
```python
async def setup(self, context: BrowserContext) -> None:
    """Setup browser context for generic site."""
    await context.set_viewport_size(
        self.config.viewport["width"],
        self.config.viewport["height"]
    )

async def teardown(self, context: BrowserContext) -> None:
    """Cleanup after generic site."""
    await context.clear_cookies()
```

**Acceptance Criteria:**
- [ ] GenericAdapter class created
- [ ] Implements SiteAdapter protocol
- [ ] Handles all methods gracefully
- [ ] Provides clear error messages
- [ ] Documented limitations

**Verification:**
```bash
mypy src/plugins/generic/adapter.py
python -c "from src.plugins.generic.adapter import GenericAdapter; from src.core.protocols import SiteAdapter; print('✓ GenericAdapter implements SiteAdapter')"
```

---

### 4.2 Create Twitter Adapter (Template)

**File:** `src/plugins/twitter/adapter.py`
**Effort:** 3-4 hours

**Purpose:** Demonstrate adapter pattern with a real site (even if not fully functional)

**Implementation Steps:**

#### Step 1: Basic Structure
```python
from typing import Any, List
from playwright.async_api import Page, BrowserContext

from src.core.protocols import SiteAdapter, CrawlConfig, AuthResult

class TwitterAdapter:
    """Twitter/X crawler adapter.

    NOTE: This is a template/example. Full Twitter automation
    would require more implementation and testing.
    """

    site_name: str = "Twitter"
    site_domain: str = "twitter.com"
    __version__ = "0.1.0"  # Alpha version

    def __init__(self, config: CrawlConfig):
        self.config = config
        self._selectors = self._build_selectors()
```

#### Step 2: Selector Definitions
```python
def _build_selectors(self) -> dict[str, str]:
    """Build Twitter-specific CSS selectors.

    NOTE: Selectors are examples and may need updates.
    Twitter changes their DOM frequently.
    """
    return {
        # Authentication (examples)
        "username_input": "input[autocomplete='username']",
        "password_input": "input[autocomplete='current-password']",
        "login_button": "div[data-testid='LoginForm'] button",

        # Navigation
        "tweet_button": "[data-testid='SideNav_NewTweet_Button']",
        "home_timeline": "[data-testid='PrimaryColumn']",

        # Posting
        "tweet_textbox": "[data-testid='tweetTextarea_0']",
        "post_tweet_button": "[data-testid='tweetButton']",

        # Profile
        "profile_button": "[data-testid='AppTabBar_Profile_Link']",
    }
```

#### Step 3: Configuration
```python
def get_default_config(self) -> CrawlConfig:
    """Get default Twitter configuration."""
    return CrawlConfig(
        base_url="https://twitter.com",
        timeout=30000,
        headless=True,  # Twitter allows headless
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    )

def get_login_url(self) -> str:
    """Return Twitter login URL."""
    return "https://twitter.com/i/flow/login"
```

#### Step 4: Authentication (Placeholder)
```python
async def login(
    self,
    page: Page,
    username: str,
    password: str
) -> AuthResult:
    """Attempt Twitter login.

    NOTE: This is a placeholder. Twitter login is complex
    and may require additional steps (2FA, etc.).
    """
    try:
        await page.goto(self.get_login_url())

        # Twitter login flow is complex - this is simplified
        # Real implementation would handle multiple steps
        await page.fill(self._selectors["username_input"], username)
        await page.press_key(self._selectors["username_input"], "Enter")

        # Wait for password screen
        await page.wait_for_timeout(2000)

        # Would continue with password...
        # NOTE: This is not a complete implementation

        return AuthResult(
            success=False,
            message="Twitter login not fully implemented. This is a template/example.",
        )
    except Exception as e:
        return AuthResult(
            success=False,
            message=f"Login error: {e}"
        )

def is_logged_in(self, page: Page) -> bool:
    """Check if logged into Twitter.

    NOTE: Simplified check. Real implementation would be more robust.
    """
    try:
        # Check for tweet button (only visible when logged in)
        tweet_button = page.locator(self._selectors["tweet_button"])
        return tweet_button.is_visible()
    except:
        return False
```

#### Step 5: Tools (Placeholder)
```python
def get_tools(self) -> List[Any]:
    """Return Twitter-specific tools.

    NOTE: These are placeholders. Real implementation would
    create actual LangChain tools.
    """
    # Would return Twitter-specific tools here
    return []
```

#### Step 6: Lifecycle
```python
async def setup(self, context: BrowserContext) -> None:
    """Setup Twitter browser context."""
    await context.set_viewport_size(
        self.config.viewport["width"],
        self.config.viewport["height"]
    )

async def teardown(self, context: BrowserContext) -> None:
    """Cleanup Twitter session."""
    await context.clear_cookies()
```

**Acceptance Criteria:**
- [ ] TwitterAdapter class created
- [ ] Implements SiteAdapter protocol
- [ ] Selectors defined (even if placeholders)
- [ ] Clear documentation of limitations
- [ ] Follows same pattern as FacebookAdapter

**Verification:**
```bash
mypy src/plugins/twitter/adapter.py
python -c "from src.plugins.twitter.adapter import TwitterAdapter; print('✓ TwitterAdapter created')"
```

---

### 4.3 Create Plugin Package Files

**Files:**
- `src/plugins/generic/__init__.py`
- `src/plugins/twitter/__init__.py`

**Effort:** 30 minutes

**Implementation:**
```python
# src/plugins/generic/__init__.py
"""Generic/fallback crawler plugin."""
from src.plugins.generic.adapter import GenericAdapter

__all__ = ["GenericAdapter"]

# src/plugins/twitter/__init__.py
"""Twitter/X crawler plugin (template/example)."""
from src.plugins.twitter.adapter import TwitterAdapter

__all__ = ["TwitterAdapter"]
```

**Acceptance Criteria:**
- [ ] Both packages created
- [ ] Exports correct
- [ ] Importable

---

### 4.4 Create Plugin Development Guide

**File:** `docs/PLUGIN_DEVELOPMENT.md`
**Effort:** 3-4 hours

**Sections:**

#### 1. Overview
```markdown
# Plugin Development Guide

This guide explains how to create custom site adapters for the web automation framework.
```

#### 2. Quick Start
```markdown
## Quick Start

Create a new adapter in 3 steps:

1. Create adapter directory: `src/plugins/yoursite/`
2. Implement adapter class
3. Test with MultiSiteAgent

See example below.
```

#### 3. Adapter Template
```markdown
## Adapter Template

```python
from typing import Any, List
from playwright.async_api import Page, BrowserContext
from src.core.protocols import SiteAdapter, CrawlConfig, AuthResult

class YourSiteAdapter:
    """YourSite crawler adapter."""

    site_name: str = "YourSite"
    site_domain: str = "yoursite.com"
    __version__ = "1.0.0"

    def __init__(self, config: CrawlConfig):
        self.config = config
        self._selectors = self._build_selectors()

    # Implement all SiteAdapter methods...
```

#### 4. Protocol Methods
```markdown
## Required Methods

### site_name
Human-readable site name.

### site_domain
Primary domain (e.g., "facebook.com").

### get_default_config()
Return default CrawlConfig for this site.

### login(page, username, password)
Perform authentication. Return AuthResult.

### is_logged_in(page)
Check authentication status.

### get_login_url()
Return login page URL.

### get_selectors()
Return dict of CSS selectors.

### get_tools()
Return list of LangChain tools.

### setup(context)
Initialize browser context.

### teardown(context)
Cleanup resources.
```

#### 5. Testing
```markdown
## Testing Your Adapter

```python
# Test adapter loads
from src.core.plugin_loader import PluginLoader
loader = PluginLoader()
adapter = loader.create("yoursite")

# Test protocol compliance
from src.core.protocols import SiteAdapter
assert isinstance(adapter, SiteAdapter)

# Test with agent
from src.agents.multi_site_agent import MultiSiteAgent
agent = MultiSiteAgent()
result = await agent.run("Task for YourSite")
```
```

#### 6. Best Practices
```markdown
## Best Practices

1. **Use Protocol** - No inheritance needed
2. **Type hints** - Add to all methods
3. **Error handling** - Handle failures gracefully
4. **Selectors** - Document all selectors
5. **Testing** - Test each method
6. **Documentation** - Document limitations

#### 7. Common Patterns
```markdown
## Common Patterns

### Selector Discovery
```python
# Use browser DevTools to find selectors
# Test with: browser_get_snapshot() tool

### Authentication
```python
# Start with manual login
# Then observe what changes
# Detect via selector presence

### Tools
```python
# Create Pydantic schema for args
# Return StructuredTool
# Register in get_tools()
```
```

#### 8. Troubleshooting
```markdown
## Troubleshooting

### Plugin not loading
- Check entry_points in pyproject.toml
- Verify adapter class name matches
- Check for import errors

### Selectors not working
- Site DOM may have changed
- Use browser_get_snapshot() to inspect
- Try multiple selectors as fallback

### Login failing
- Site may require additional steps
- Check for 2FA, CAPTCHA
- Consider manual login + session persistence
```

**Acceptance Criteria:**
- [ ] Guide created
- [ ] Clear structure
- [ ] Code examples throughout
- [ ] Template adapter included
- [ ] Testing section complete
- [ ] Troubleshooting section included

---

### 4.5 Create LinkedIn Adapter Example

**File:** `examples/linkedin_adapter.py`
**Effort:** 2 hours

**Purpose:** Complete working example in docs/examples

**Implementation:**
- Show full adapter implementation
- Include comments explaining each part
- Demonstrate common patterns
- Show testing approach

**Acceptance Criteria:**
- [ ] Example adapter created
- [ ] Well-commented
- [ ] Demonstrates all protocol methods
- [ ] Includes selector strategies

---

### 4.6 Create Tests

**Files:**
- `tests/test_adapters/test_generic.py`
- `tests/test_adapters/test_twitter.py`

**Effort:** 2 hours

**Generic Adapter Tests:**
```python
def test_generic_adapter_protocol():
    """Test GenericAdapter implements SiteAdapter."""
    from src.plugins.generic.adapter import GenericAdapter
    from src.core.protocols import SiteAdapter

    adapter = GenericAdapter(config=None)
    assert isinstance(adapter, SiteAdapter)

def test_generic_adapter_no_login():
    """Test GenericAdapter login returns error."""
    from src.plugins.generic.adapter import GenericAdapter

    adapter = GenericAdapter(config=None)
    result = await adapter.login(None, "user", "pass")

    assert result.success is False
    assert "does not support" in result.message
```

**Twitter Adapter Tests:**
```python
def test_twitter_adapter_structure():
    """Test TwitterAdapter has correct structure."""
    from src.plugins.twitter.adapter import TwitterAdapter

    adapter = TwitterAdapter(config=None)

    assert adapter.site_name == "Twitter"
    assert adapter.site_domain == "twitter.com"
    assert len(adapter.get_selectors()) > 0
```

**Acceptance Criteria:**
- [ ] Test files created
- [ ] Protocol compliance tested
- [ ] Limitations documented
- [ ] Tests pass

**Verification:**
```bash
pytest tests/test_adapters/test_generic.py tests/test_adapters/test_twitter.py -v
```

---

### 4.7 Update Documentation

**Files:**
- Update `README.md`
- Update `CLAUDE.md`

**Effort:** 1 hour

**Add to README:**
```markdown
## Multi-Site Support

The agent supports multiple websites through a plugin architecture:

### Supported Sites
- Facebook (fully implemented)
- Twitter (template/example)
- Generic (fallback for any site)

### Creating Custom Adapters

See [PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) for guide.

### Usage

```bash
# Use Facebook
python -m facebook-surfer run "Post to Facebook" --site facebook

# Use Generic
python -m facebook-surfer run "Navigate to example.com" --site generic

# List available sites
python -m facebook-surfer list-sites
```
```

**Acceptance Criteria:**
- [ ] README updated
- [ ] Multi-site support documented
- [ ] Plugin development guide linked
- [ ] Examples provided

---

## Deliverables

### Code
- [ ] `src/plugins/generic/adapter.py` - Generic adapter
- [ ] `src/plugins/twitter/adapter.py` - Twitter template
- [ ] `src/plugins/generic/__init__.py`
- [ ] `src/plugins/twitter/__init__.py`

### Documentation
- [ ] `docs/PLUGIN_DEVELOPMENT.md` - Development guide
- [ ] `examples/linkedin_adapter.py` - Complete example
- [ ] Updated `README.md`

### Tests
- [ ] `tests/test_adapters/test_generic.py`
- [ ] `tests/test_adapters/test_twitter.py`

## Verification Steps

### 1. Plugin Discovery
```bash
python -c "
from src.core.plugin_loader import PluginLoader
loader = PluginLoader()
sites = loader.list_all()
print(f'Discovered sites: {sites}')
assert 'facebook' in sites
assert 'twitter' in sites
assert 'generic' in sites
"
```
**Expected:** All 3 adapters discovered

### 2. Adapter Creation
```bash
python -c "
from src.core.plugin_loader import PluginLoader
loader = PluginLoader()

# Create each adapter
for site in ['facebook', 'twitter', 'generic']:
    adapter = loader.create(site)
    print(f'{site}: {adapter.site_name}')
"
```
**Expected:** All adapters create successfully

### 3. Type Checking
```bash
mypy src/plugins/generic/ src/plugins/twitter/
```
**Expected:** No errors

### 4. Tests
```bash
pytest tests/test_adapters/test_generic.py tests/test_adapters/test_twitter.py -v
```
**Expected:** All tests pass

### 5. Documentation
```bash
ls -la docs/PLUGIN_DEVELOPMENT.md examples/linkedin_adapter.py
```
**Expected:** Files exist

## Success Criteria

### Must Have
- ✅ Generic adapter created and working
- ✅ Twitter adapter template created
- ✅ Plugin development guide complete
- ✅ Tests for new adapters pass
- ✅ Documentation updated
- ✅ Examples provided

### Should Have
- ✅ LinkedIn adapter example
- ✅ Troubleshooting guide
- ✅ Code comments throughout
- ✅ Common patterns documented

### Could Have
- ✅ Additional adapter examples
- ✅ Video tutorial
- ✅ Plugin generator script

## Rollback Plan

If this phase fails:
1. Keep GenericAdapter (it's simple)
2. Remove TwitterAdapter if problematic
3. Simplify plugin development guide
4. Focus on documentation vs implementation

## Notes

### Key Design Decisions
1. **Generic adapter** - Provides fallback for unknown sites
2. **Twitter as template** - Shows pattern without full implementation
3. **Documentation focus** - Guide more important than working Twitter adapter
4. **Examples over features** - Clear examples better than many features

### Lessons Learned
- Template adapters help developers
- Documentation critical for adoption
- Generic adapter provides safety net
- Examples reduce learning curve

### Next Phase
After this phase completes, proceed to **Phase 5: Testing & Documentation** for final polish and comprehensive testing.
