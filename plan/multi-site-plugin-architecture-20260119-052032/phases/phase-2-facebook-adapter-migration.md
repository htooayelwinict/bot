# Phase 2: Facebook Adapter Migration

**Duration:** 2-3 days
**Status:** Pending
**Dependencies:** Phase 1 complete

## Objective

Extract Facebook-specific logic into a standalone adapter implementing the SiteAdapter protocol. This migrates functionality from the monolithic FacebookSurferAgent and FacebookSessionManager into the plugin architecture while maintaining full backward compatibility.

## Prerequisites

- Phase 1 complete (core architecture in place)
- SiteAdapter protocol defined
- PluginLoader working
- Configuration system ready

## Tasks

### 2.1 Create Facebook Adapter Structure

**Files:**
- `src/plugins/facebook/__init__.py`
- `src/plugins/facebook/adapter.py`

**Effort:** 1 hour

**Implementation Steps:**
1. Create `src/plugins/` directory
2. Create `src/plugins/facebook/` directory
3. Create `__init__.py` files:
   ```python
   # src/plugins/__init__.py
   """Site-specific crawler plugins."""

   # src/plugins/facebook/__init__.py
   """Facebook crawler plugin."""
   from src.plugins.facebook.adapter import FacebookAdapter

   __all__ = ["FacebookAdapter"]
   ```
4. Create adapter.py with stub class
5. Verify imports work

**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] __init__.py files created
- [ ] Imports work correctly

**Verification:**
```bash
python -c "from src.plugins.facebook import FacebookAdapter; print('✓ Facebook adapter imports')"
```

---

### 2.2 Implement FacebookAdapter Class

**File:** `src/plugins/facebook/adapter.py`
**Effort:** 4-5 hours

**Implementation Steps:**

#### Step 1: Basic Structure
```python
from typing import Any, List
from playwright.async_api import Page, BrowserContext

from src.core.protocols import SiteAdapter, CrawlConfig, AuthResult

class FacebookAdapter:
    """Facebook-specific crawler adapter."""

    site_name: str = "Facebook"
    site_domain: str = "facebook.com"
    __version__ = "1.0.0"

    LOGIN_URL = "https://www.facebook.com/login"

    def __init__(self, config: CrawlConfig):
        self.config = config
        self._selectors = self._build_selectors()
```

#### Step 2: Selector Definitions
```python
def _build_selectors(self) -> dict[str, str]:
    """Build Facebook-specific CSS selectors."""
    return {
        # Authentication
        "email_input": "#email",
        "password_input": "#pass",
        "login_button": "button[name='login']",

        # Navigation
        "search_input": "input[placeholder*='Search']",
        "home_link": "a[aria-label='Home']",

        # Posting
        "composer_button": "div[role='button']:has-text('What\\'s on your mind')",
        "composer_textbox": "div[contenteditable='true'][role='textbox']",
        "post_button": "div[role='button']:has-text('Post')",

        # Privacy
        "privacy_button": "div[role='button'][aria-label*='Friends'], div[role='button'][aria-label*='Public']",
        "privacy_option_radio": "input[type='radio'][value='{option}']",
        "done_button": "div[role='button']:has-text('Done')",

        # Feed
        "feed_container": "div[role='feed']",
        "post_item": "div[role='article']",
    }
```

#### Step 3: Configuration Methods
```python
def get_default_config(self) -> CrawlConfig:
    """Get default Facebook configuration."""
    return CrawlConfig(
        base_url="https://www.facebook.com",
        timeout=30000,
        headless=False,  # FB often requires non-headless
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        viewport={"width": 1920, "height": 1080},
    )

def get_login_url(self) -> str:
    """Return Facebook login URL."""
    return self.LOGIN_URL

def get_selectors(self) -> dict[str, str]:
    """Return Facebook-specific selectors."""
    return self._selectors.copy()
```

#### Step 4: Authentication Methods
```python
async def login(
    self,
    page: Page,
    username: str,
    password: str
) -> AuthResult:
    """Perform Facebook login.

    Migrated from FacebookSessionManager.start_login()
    """
    try:
        # Navigate to login
        await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")

        # Fill credentials
        await page.fill(self._selectors["email_input"], username)
        await page.fill(self._selectors["password_input"], password)

        # Click login
        await page.click(self._selectors["login_button"])

        # Wait for navigation
        await page.wait_for_load_state("networkidle")

        # Check success
        if self.is_logged_in(page):
            return AuthResult(
                success=True,
                message="Successfully logged into Facebook",
                session_data={"cookies": await page.context.cookies()},
            )
        else:
            return AuthResult(
                success=False,
                message="Login failed - check credentials",
            )

    except Exception as e:
        return AuthResult(
            success=False,
            message=f"Login error: {e}"
        )

def is_logged_in(self, page: Page) -> bool:
    """Check if logged into Facebook.

    Migrated from FacebookSessionManager._is_logged_in()
    """
    # Check for login form - if present, not logged in
    try:
        email_input = page.locator(self._selectors["email_input"])
        return not email_input.is_visible()
    except:
        return False
```

#### Step 5: Lifecycle Methods
```python
async def setup(self, context: BrowserContext) -> None:
    """Setup Facebook browser context."""
    # Set viewport
    await context.set_viewport_size(
        self.config.viewport["width"],
        self.config.viewport["height"]
    )

    # Set user agent
    if self.config.user_agent:
        await context.set_extra_http_headers({
            "User-Agent": self.config.user_agent
        })

    # Set locale and timezone
    await context.set_extra_http_headers({
        "Accept-Language": "en-US,en",
    })

async def teardown(self, context: BrowserContext) -> None:
    """Cleanup Facebook session."""
    await context.clear_cookies()
```

#### Step 6: Tools Method
```python
def get_tools(self) -> List[Any]:
    """Return Facebook-specific LangChain tools.

    Currently returns empty list - will populate in next tasks.
    """
    return []
```

**Acceptance Criteria:**
- [ ] FacebookAdapter class created
- [ ] All SiteAdapter protocol methods implemented
- [ ] Selectors migrated from session module
- [ ] Login logic migrated from session module
- [ ] Type hints complete
- [ ] Docstrings complete

**Verification:**
```bash
mypy src/plugins/facebook/adapter.py
python -c "from src.plugins.facebook.adapter import FacebookAdapter; from src.core.protocols import SiteAdapter; adapter = FacebookAdapter(config=None); print(isinstance(adapter, SiteAdapter))"
```

---

### 2.3 Create Facebook Tools

**File:** `src/plugins/facebook/tools.py`
**Effort:** 2-3 hours

**Implementation Steps:**

1. **Analyze existing FB-specific tools:**
   - Review existing tools in src/tools/
   - Identify any FB-specific functionality
   - Note: Most tools are universal, keep in main registry

2. **Create FB-specific tools (if needed):**
   ```python
   from langchain_core.tools import StructuredTool
   from pydantic import BaseModel, Field

   class FBPostArgs(BaseModel):
       text: str = Field(description="Post text content")
       privacy: str = Field(default="Public", description="Privacy: Public, Friends, Only me")

   def fb_post(text: str, privacy: str = "Public") -> str:
       """Create a Facebook post with specified privacy."""
       # This would use browser tools internally
       return f"Posted to Facebook: {text} (Privacy: {privacy})"

   def create_facebook_post_tool() -> StructuredTool:
       return StructuredTool.from_function(
           name="facebook_post",
           description="Create a Facebook post",
           func=fb_post,
           args_schema=FBPostArgs,
       )
   ```

3. **Update adapter to use tools:**
   ```python
   def get_tools(self) -> List[Any]:
       """Return Facebook-specific LangChain tools."""
       from src.plugins.facebook.tools import create_facebook_post_tool
       return [create_facebook_post_tool()]
   ```

**Acceptance Criteria:**
- [ ] tools.py created
- [ ] FB-specific tools defined
- [ ] Tools use Pydantic schemas
- [ ] adapter.get_tools() returns tools
- [ ] Tools integrate with LangChain

**Verification:**
```bash
python -c "from src.plugins.facebook.adapter import FacebookAdapter; from src.core.protocols import CrawlConfig; config = CrawlConfig(base_url='https://facebook.com'); adapter = FacebookAdapter(config); tools = adapter.get_tools(); print(f'Found {len(tools)} tools')"
```

---

### 2.4 Create Facebook Configuration

**File:** `src/plugins/facebook/config.py`
**Effort:** 1-2 hours

**Implementation Steps:**

1. **Create config schema:**
   ```python
   from pydantic import Field
   from src.core.config.dynamic import DynamicConfigMixin

   class FacebookConfig(DynamicConfigMixin):
       """Facebook-specific configuration."""

       @staticmethod
       def get_config_schema() -> dict:
           return {
               "login_timeout": (int, Field(180, ge=60, le=600, description="Login timeout in seconds")),
               "manual_login": (bool, Field(True, description="Require manual login")),
               "screenshot_path": (str, Field("./screenshots/fb", description="Screenshot save path")),
               "anti_bot_detection": (bool, Field(True, description="Enable anti-bot measures")),
               "wait_for_selector_timeout": (int, Field(5000, ge=1000, le=30000)),
           }
   ```

2. **Create YAML config example:**
   ```yaml
   # config/sites.yaml
   facebook:
     enabled: true
     base_url: "https://www.facebook.com"
     timeout: 30000
     headless: false
     login_timeout: 180
     manual_login: true
     screenshot_path: "./screenshots/fb"
   ```

**Acceptance Criteria:**
- [ ] FacebookConfig class created
- [ ] Config schema defined
- [ ] Validation rules applied
- [ ] YAML example created
- [ ] Integration with pydantic-settings works

**Verification:**
```bash
python -c "from src.plugins.facebook.config import FacebookConfig; from src.core.config.dynamic import create_plugin_config; schema = FacebookConfig.get_config_schema(); config = create_plugin_config('Facebook', schema, {'login_timeout': 300}); print(config)"
```

---

### 2.5 Create Tests

**File:** `tests/test_adapters/test_facebook.py`
**Effort:** 2-3 hours

**Implementation Steps:**

1. **Test protocol compliance:**
   ```python
   def test_facebook_adapter_protocol():
       """Test FacebookAdapter implements SiteAdapter."""
       from src.plugins.facebook.adapter import FacebookAdapter
       from src.core.protocols import SiteAdapter

       config = CrawlConfig(base_url="https://facebook.com")
       adapter = FacebookAdapter(config)

       # Check protocol compliance
       assert hasattr(adapter, "site_name")
       assert hasattr(adapter, "login")
       assert isinstance(adapter, SiteAdapter)
   ```

2. **Test selector definitions:**
   ```python
   def test_selectors():
       """Test FB selectors are defined."""
       adapter = FacebookAdapter(config=None)
       selectors = adapter.get_selectors()

       assert "email_input" in selectors
       assert "password_input" in selectors
       assert "login_button" in selectors
   ```

3. **Test configuration:**
   ```python
   def test_default_config():
       """Test default config."""
       adapter = FacebookAdapter(config=None)
       config = adapter.get_default_config()

       assert str(config.base_url) == "https://www.facebook.com"
       assert config.headless is False
   ```

4. **Test login detection (with mock):**
   ```python
   @pytest.mark.asyncio
   async def test_is_logged_in():
       """Test login detection."""
       from unittest.mock import Mock

       adapter = FacebookAdapter(config=None)
       page = Mock()

       # Mock page to return no login form
       page.query_selector.return_value = None
       assert adapter.is_logged_in(page) is True
   ```

**Acceptance Criteria:**
- [ ] Test file created
- [ ] Protocol compliance tested
- [ ] Selectors tested
- [ ] Configuration tested
- [ ] Login detection tested
- [ ] Coverage >80% for adapter

**Verification:**
```bash
pytest tests/test_adapters/test_facebook.py -v
pytest tests/test_adapters/test_facebook.py --cov=src/plugins/facebook --cov-report=term-missing
```

---

### 2.6 Verify Backward Compatibility

**Effort:** 1 hour

**Implementation Steps:**

1. **Test FacebookSurferAgent still works:**
   ```python
   # Existing code should still work
   from src.agents.facebook_surfer import FacebookSurferAgent

   agent = FacebookSurferAgent()
   assert agent.tool_count > 0
   ```

2. **Test existing CLI commands:**
   ```bash
   # These should still work
   python -m facebook-surfer login
   python -m facebook-surfer run "test task"
   ```

3. **Test session manager:**
   ```python
   # Existing session manager should work
   from src.session import FacebookSessionManager

   manager = FacebookSessionManager()
   assert manager is not None
   ```

**Acceptance Criteria:**
- [ ] FacebookSurferAgent imports successfully
- [ ] Existing CLI commands work
- [ ] Session manager works unchanged
- [ ] No import errors
- [ ] No runtime errors

**Verification:**
```bash
# Quick smoke test
python -c "from src.agents.facebook_surfer import FacebookSurferAgent; print('✓ FacebookSurferAgent works')"
python -c "from src.session import FacebookSessionManager; print('✓ FacebookSessionManager works')"
```

---

## Deliverables

### Code
- [ ] `src/plugins/facebook/__init__.py`
- [ ] `src/plugins/facebook/adapter.py` - Facebook adapter
- [ ] `src/plugins/facebook/tools.py` - FB-specific tools
- [ ] `src/plugins/facebook/config.py` - FB configuration

### Configuration
- [ ] `config/sites.yaml` - Site configurations
- [ ] Updated example configs

### Tests
- [ ] `tests/test_adapters/test_facebook.py`
- [ ] Backward compatibility tests

### Documentation
- [ ] Docstrings in adapter
- [ ] Comments on migration

## Verification Steps

### 1. Import Test
```bash
python -c "from src.plugins.facebook import FacebookAdapter; print('✓ Imports OK')"
```
**Expected:** No errors

### 2. Type Check
```bash
mypy src/plugins/facebook/
```
**Expected:** No errors

### 3. Protocol Check
```bash
python -c "
from src.plugins.facebook.adapter import FacebookAdapter
from src.core.protocols import SiteAdapter
from src.core.protocols import CrawlConfig

config = CrawlConfig(base_url='https://facebook.com')
adapter = FacebookAdapter(config)
print(f'Site name: {adapter.site_name}')
print(f'Site domain: {adapter.site_domain}')
print(f'Implements SiteAdapter: {isinstance(adapter, SiteAdapter)}')
"
```
**Expected:** All fields correct, protocol check True

### 4. Unit Tests
```bash
pytest tests/test_adapters/test_facebook.py -v
```
**Expected:** All tests pass

### 5. Backward Compatibility
```bash
python -c "from src.agents.facebook_surfer import FacebookSurferAgent; agent = FacebookSurferAgent(); print(f'Tools: {agent.tool_count}')"
```
**Expected:** FacebookSurferAgent works, has tools

## Success Criteria

### Must Have
- ✅ FacebookAdapter implements SiteAdapter
- ✅ All existing FB functionality available through adapter
- ✅ FacebookSurferAgent still works unchanged
- ✅ Type checks pass
- ✅ Tests cover main scenarios
- ✅ No breaking changes

### Should Have
- ✅ FB-specific tools created
- ✅ Configuration system works
- ✅ Tests cover edge cases
- ✅ Documentation complete

### Could Have
- ✅ Additional FB tools
- ✅ More configuration options
- ✅ Performance optimizations

## Migration Notes

### What Was Migrated
1. **Selectors** - From `src/session/__init__.py` to adapter
2. **Login logic** - From session manager to adapter
3. **Configuration** - From hardcoded to adapter methods
4. **Session setup** - From session manager to adapter

### What Was NOT Changed
1. **FacebookSurferAgent** - Kept as-is for backward compatibility
2. **Browser tools** - Remain universal in src/tools/
3. **Session manager** - Kept for existing users
4. **CLI interface** - Still works with FacebookSurferAgent

### Next Steps
After adapter is complete and tested, can start using it in **Phase 3: Multi-Site Agent**

## Rollback Plan

If this phase fails:
1. Delete `src/plugins/facebook/` directory
2. Keep FacebookSurferAgent as primary
3. Investigate migration issues
4. Simplify adapter if needed
5. Retry with smaller scope

## Notes

### Key Design Decisions
1. **Keep existing code** - No deletion, only addition
2. **Adapter as wrapper** - Uses same underlying mechanisms
3. **Gradual migration** - Can adopt incrementally
4. **Parallel existence** - Both agent and adapter can coexist

### Lessons Learned
- Migration easier when keeping original intact
- Protocol compliance straightforward
- Testing critical for maintaining functionality
- Documentation important for future adapters

### Next Phase
After this phase completes, proceed to **Phase 3: Multi-Site Agent** where we'll create the multi-site agent that uses the Facebook adapter.
