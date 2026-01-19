# Plugin Architecture: Implementation Guide (Updated 2025)

**Last Updated:** 2025-01-19
**Status:** Ready for Implementation
**Stack:** Python 3.11+, LangChain, LangGraph, Playwright, Pydantic V2

---

## Quick Start: Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MultiSiteAgent                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         LangGraph Workflow                            │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐       │  │
│  │  │ Detect   │───▶│ Switch   │───▶│ Crawl    │       │  │
│  │  │ Site     │    │ Adapter  │    │ Page     │       │  │
│  │  └──────────┘    └──────────┘    └──────────┘       │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         PluginLoader (entry points + importlib)       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │   Facebook   │  │   Twitter    │  │  Generic   │ │  │
│  │  │   Adapter    │  │   Adapter    │  │  Adapter   │ │  │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         ToolRegistry (LangChain tools)                │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │  Universal Tools + Site-Specific Tools           │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**

1. **Protocol-based interfaces** - Type-safe without requiring inheritance
2. **Dual loading strategy** - Entry points for external plugins + importlib for bundled
3. **Pydantic V2 config** - Multi-source loading (env, .env, YAML, programmatic)
4. **Async-first lifecycle** - Using `asyncio.TaskGroup` for structured concurrency
5. **LangGraph orchestration** - State management with checkpointer for persistence

---

## 1. Core Protocols

```python
# src/core/protocols.py
from typing import Protocol, runtime_checkable, Self
from pydantic import BaseModel, HttpUrl
from playwright.async_api import Page, BrowserContext

# Configuration Models
class CrawlConfig(BaseModel):
    """Base configuration - Pydantic V2 for validation."""
    base_url: HttpUrl
    timeout: int = 30000
    headless: bool = True
    user_agent: str | None = None
    viewport: dict = {"width": 1920, "height": 1080}


class AuthResult(BaseModel):
    """Authentication result."""
    success: bool
    message: str
    session_data: dict | None = None


# Site Adapter Protocol (Core Interface)
@runtime_checkable
class SiteAdapter(Protocol):
    """Protocol for site-specific crawler adapters.

    Any class with these methods is compatible - no inheritance required.
    Enables duck-typing with static type checking.
    """

    # Identification
    @property
    def site_name(self) -> str: ...

    @property
    def site_domain(self) -> str: ...

    # Configuration
    def get_default_config(self) -> CrawlConfig: ...

    def get_config_schema(self) -> type[BaseModel]: ...

    # Authentication
    async def login(self, page: Page, username: str, password: str) -> AuthResult: ...

    def is_logged_in(self, page: Page) -> bool: ...

    def get_login_url(self) -> str: ...

    # Selectors
    def get_selectors(self) -> dict[str, str]: ...

    # Tools (LangChain)
    def get_tools(self) -> list[Any]: ...

    # Lifecycle
    async def setup(self, context: BrowserContext) -> None: ...

    async def teardown(self, context: BrowserContext) -> None: ...


# Fluent Interface Protocol (Optional Enhancement)
@runtime_checkable
class ConfigurableAdapter(Protocol):
    """Protocol for adapters with fluent configuration (PEP 673 Self)."""

    def with_config(self, config: CrawlConfig) -> Self: ...

    def with_timeout(self, timeout: int) -> Self: ...

    def with_headless(self, headless: bool) -> Self: ...
```

---

## 2. Plugin Loader

```python
# src/core/plugin_loader.py
from importlib.metadata import entry_points
from pathlib import Path
from typing import Type, Any
import importlib
import pkgutil

from src.core.protocols import SiteAdapter


class PluginLoader:
    """Discover and load site adapter plugins.

    Supports:
    - Entry points (pyproject.toml) for external plugins
    - Directory scanning for bundled plugins
    """

    def __init__(
        self,
        entry_point_group: str = "webcrawler.adapters",
        plugins_package: str = "src.plugins"
    ):
        self.entry_point_group = entry_point_group
        self.plugins_package = plugins_package
        self._plugins: dict[str, Type[SiteAdapter]] = {}

        # Auto-discover on init
        self._load_from_entrypoints()
        self._load_from_directory()

    def _load_from_entrypoints(self) -> None:
        """Load plugins from installed packages via entry points."""
        try:
            eps = entry_points(group=self.entry_point_group)
            for ep in eps:
                try:
                    adapter_class = ep.load()
                    self._plugins[ep.name] = adapter_class
                    print(f"✓ Loaded entry point: {ep.name}")
                except Exception as e:
                    print(f"✗ Failed to load {ep.name}: {e}")
        except Exception:
            # No entry points found - not an error
            pass

    def _load_from_directory(self) -> None:
        """Load plugins from local src/plugins/ directory."""
        plugins_path = Path(__file__).parent.parent / "plugins"

        if not plugins_path.exists():
            return

        for finder, name, ispkg in pkgutil.iter_modules([plugins_path]):
            if name.startswith("_"):
                continue

            try:
                module = importlib.import_module(f"{self.plugins_package}.{name}.adapter")
                adapter_class = self._find_adapter_class(module)
                if adapter_class:
                    self._plugins[name] = adapter_class
                    print(f"✓ Loaded local plugin: {name}")
            except ImportError as e:
                print(f"✗ Failed to import {name}: {e}")

    def _find_adapter_class(self, module: Any) -> Type[SiteAdapter] | None:
        """Find adapter class in module."""
        for attr_name in dir(module):
            if "Adapter" in attr_name:
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and self._implements_site_adapter(attr):
                    return attr
        return None

    def _implements_site_adapter(self, cls: Type) -> bool:
        """Check if class implements SiteAdapter protocol."""
        required = ["site_name", "site_domain", "login", "is_logged_in", "get_tools"]
        return all(hasattr(cls, name) for name in required)

    def get(self, name: str) -> Type[SiteAdapter] | None:
        """Get adapter class by name."""
        return self._plugins.get(name)

    def create(self, name: str, config: CrawlConfig | None = None) -> SiteAdapter:
        """Create adapter instance."""
        adapter_class = self.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown plugin: {name}")

        if config is None:
            # Get default config from adapter
            config = adapter_class.get_default_config()

        return adapter_class(config)

    def list_all(self) -> list[str]:
        """List all available plugin names."""
        return list(self._plugins.keys())

    def __contains__(self, name: str) -> bool:
        """Support 'name in loader' syntax."""
        return name in self._plugins
```

---

## 3. Configuration with Pydantic V2

```python
# src/core/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from typing import Literal, Optional


class ScraperSettings(BaseSettings):
    """Scraper settings loaded from environment/.env/file."""
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    target_domain: HttpUrl
    max_pages: int = Field(10, ge=1, le=1000)
    headless: bool = True
    concurrency_limit: int = Field(5, ge=1, le=20)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    screenshot_on_error: bool = False
    retry_attempts: int = Field(3, ge=0, le=10)


class PluginSettings(BaseSettings):
    """Plugin-specific settings."""
    model_config = SettingsConfigDict(
        env_prefix="PLUGIN_",
        env_file=".env",
    )

    enabled: bool = True
    api_key: Optional[str] = Field(None, min_length=10)
    timeout: int = Field(30, ge=5, le=300)
    debug_mode: bool = False


# Usage:
# settings = ScraperSettings()  # Auto-loads from env/.env
# or
# settings = ScraperSettings(
#     target_domain="https://example.com",
#     max_pages=50
# )
```

### Dynamic Configuration for Plugins

```python
# src/core/config/dynamic.py
from pydantic import create_model, Field
from typing import Any, Dict


class DynamicConfigMixin:
    """Mixin for plugins with dynamic config schemas."""

    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        """Define plugin-specific config schema.

        Returns:
            Dict mapping field names to (type, default) tuples
        """
        raise NotImplementedError


def create_plugin_config(
    plugin_name: str,
    schema: Dict[str, Any],
    values: Dict[str, Any]
) -> BaseModel:
    """Create dynamic config model from schema.

    Args:
        plugin_name: Name for the model class
        schema: Field schema from get_config_schema()
        values: Actual values to validate

    Returns:
        Validated Pydantic model instance
    """
    ConfigModel = create_model(
        f"{plugin_name}Config",
        __base__=BaseModel,
        **schema
    )
    return ConfigModel(**values)


# Example plugin:
class FacebookAdapter(DynamicConfigMixin):
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {
            "login_timeout": (int, Field(180, ge=60, le=600)),
            "manual_login": (bool, True),
            "screenshot_path": (str, Field(default="./screenshots/fb")),
            "anti_bot_detection": (bool, True),
        }

# Usage:
# schema = FacebookAdapter.get_config_schema()
# config = create_plugin_config("Facebook", schema, {"login_timeout": 300})
```

---

## 4. Async Lifecycle Management

```python
# src/core/lifecycle.py
import asyncio
from enum import Enum, auto
from typing import Any, Dict
from playwright.async_api import async_playwright

from src.core.protocols import SiteAdapter


class PluginState(Enum):
    """Plugin lifecycle states."""
    LOADED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class AsyncLifecycleManager:
    """Manage async plugin lifecycle with structured concurrency.

    Uses Python 3.11+ asyncio.TaskGroup for safer concurrent operations.
    """

    def __init__(self):
        self._states: Dict[str, PluginState] = {}
        self._contexts: Dict[str, Any] = {}
        self._playwright = None

    async def initialize_all(
        self,
        adapters: Dict[str, SiteAdapter],
        configs: Dict[str, Any]
    ) -> None:
        """Initialize all plugins concurrently using TaskGroup."""
        self._playwright = await async_playwright().start()

        async with asyncio.TaskGroup() as tg:
            for name, adapter in adapters.items():
                config = configs.get(name)
                tg.create_task(self._initialize_one(name, adapter, config))

    async def _initialize_one(
        self,
        name: str,
        adapter: SiteAdapter,
        config: Any
    ) -> None:
        """Initialize single plugin with error isolation."""
        try:
            self._states[name] = PluginState.INITIALIZING

            # Create browser context
            browser = await self._playwright.chromium.launch(
                headless=config.headless if config else True
            )
            context = await browser.new_context(
                viewport=config.viewport if config else {"width": 1920, "height": 1080},
                user_agent=config.user_agent if config else None
            )

            # Setup adapter
            await adapter.setup(context)

            # Store context
            self._contexts[name] = {
                "browser": browser,
                "context": context,
                "adapter": adapter
            }

            self._states[name] = PluginState.READY
            print(f"✓ Initialized: {name}")

        except Exception as e:
            self._states[name] = PluginState.ERROR
            print(f"✗ Failed to initialize {name}: {e}")
            # Note: TaskGroup will cancel other tasks if we don't handle
            # For production, consider whether to continue or abort

    async def shutdown_all(self) -> None:
        """Shutdown all plugins concurrently."""
        async with asyncio.TaskGroup() as tg:
            for name, context in self._contexts.items():
                tg.create_task(self._shutdown_one(name, context))

        if self._playwright:
            await self._playwright.stop()

    async def _shutdown_one(self, name: str, context: Dict) -> None:
        """Shutdown single plugin."""
        try:
            adapter = context["adapter"]
            browser = context["browser"]

            await adapter.teardown(context["context"])
            await browser.close()

            self._states[name] = PluginState.STOPPED
            print(f"✓ Shutdown: {name}")

        except Exception as e:
            print(f"✗ Error shutting down {name}: {e}")

    def get_context(self, name: str) -> Any | None:
        """Get browser context for plugin."""
        return self._contexts.get(name)

    def get_state(self, name: str) -> PluginState:
        """Get plugin state."""
        return self._states.get(name, PluginState.LOADED)
```

---

## 5. Tool Registry

```python
# src/core/tool_registry.py
from typing import Any, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ToolRegistry:
    """Registry for LangChain tools.

    Manages:
    - Universal tools (work on all sites)
    - Site-specific tools (only work on certain sites)
    """

    def __init__(self):
        self._universal: List[StructuredTool] = []
        self._by_site: Dict[str, List[StructuredTool]] = {}

    def register_universal(self, tool: StructuredTool) -> None:
        """Register tool available to all sites."""
        self._universal.append(tool)

    def register_for_site(self, site: str, tool: StructuredTool) -> None:
        """Register site-specific tool."""
        if site not in self._by_site:
            self._by_site[site] = []
        self._by_site[site].append(tool)

    def get_tools_for_site(self, site: str) -> List[StructuredTool]:
        """Get all tools for specific site.

        Returns universal tools + site-specific tools.
        """
        tools = self._universal.copy()
        if site in self._by_site:
            tools.extend(self._by_site[site])
        return tools

    def get_all_tools(self) -> List[StructuredTool]:
        """Get all registered tools."""
        all_tools = self._universal.copy()
        for site_tools in self._by_site.values():
            all_tools.extend(site_tools)
        return all_tools

    def list_sites(self) -> List[str]:
        """List sites with registered tools."""
        return list(self._by_site.keys())


# Example: Creating a tool
def create_facebook_post_tool() -> StructuredTool:
    """Create Facebook post tool with Pydantic schema."""

    class FBPostInput(BaseModel):
        text: str = Field(description="Post content")
        privacy: str = Field(
            default="Public",
            description="Privacy setting: Public, Friends, Only Me"
        )

    def fb_post(text: str, privacy: str = "Public") -> str:
        """Create a Facebook post."""
        # Implementation would use Playwright
        return f"Posted to Facebook: {text} (Privacy: {privacy})"

    return StructuredTool.from_function(
        name="facebook_post",
        description="Create a Facebook post with privacy settings",
        func=fb_post,
        args_schema=FBPostInput,
    )
```

---

## 6. Example Adapter Implementation

```python
# src/plugins/facebook/adapter.py
from typing import Any, List
from playwright.async_api import Page, BrowserContext

from src.core.protocols import SiteAdapter, CrawlConfig, AuthResult
from src.core.config.dynamic import DynamicConfigMixin


class FacebookAdapter(DynamicConfigMixin):
    """Facebook-specific crawler adapter.

    Implements SiteAdapter protocol without inheritance.
    """

    # Static properties
    site_name: str = "Facebook"
    site_domain: str = "facebook.com"
    __version__ = "1.0.0"

    # Configuration
    LOGIN_URL = "https://www.facebook.com/login"

    def __init__(self, config: CrawlConfig):
        self.config = config
        self._selectors = self._build_selectors()

    @staticmethod
    def get_config_schema() -> dict:
        """Facebook-specific config schema."""
        from src.core.config.dynamic import Field
        return {
            "login_timeout": (int, Field(180, ge=60, le=600)),
            "manual_login": (bool, True),
            "anti_bot_detection": (bool, True),
        }

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
        }

    # Protocol implementation
    def get_default_config(self) -> CrawlConfig:
        """Get default Facebook configuration."""
        return CrawlConfig(
            base_url="https://www.facebook.com",
            timeout=30000,
            headless=False,  # FB often requires non-headless for login
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        )

    async def login(
        self,
        page: Page,
        username: str,
        password: str
    ) -> AuthResult:
        """Perform Facebook login."""
        try:
            await page.goto(self.LOGIN_URL)

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
        """Check if logged into Facebook."""
        # Check for absence of login form
        try:
            login_form = page.locator(self._selectors["email_input"])
            return not login_form.is_visible()
        except:
            return False

    def get_login_url(self) -> str:
        """Return Facebook login URL."""
        return self.LOGIN_URL

    def get_selectors(self) -> dict[str, str]:
        """Return Facebook-specific selectors."""
        return self._selectors.copy()

    def get_tools(self) -> List[Any]:
        """Return Facebook-specific LangChain tools."""
        from src.core.tool_registry import create_facebook_post_tool
        return [
            create_facebook_post_tool(),
            # Add more FB-specific tools here
        ]

    async def setup(self, context: BrowserContext) -> None:
        """Setup Facebook browser context."""
        await context.set_viewport_size(
            self.config.viewport["width"],
            self.config.viewport["height"]
        )

        if self.config.user_agent:
            await context.set_extra_http_headers({
                "User-Agent": self.config.user_agent
            })

    async def teardown(self, context: BrowserContext) -> None:
        """Cleanup Facebook session."""
        await context.clear_cookies()
```

---

## 7. Multi-Site Agent

```python
# src/agents/multi_site_agent.py
from typing import Any
from pathlib import Path
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware

from src.core.plugin_loader import PluginLoader
from src.core.protocols import SiteAdapter, CrawlConfig
from src.core.tool_registry import ToolRegistry
from src.core.lifecycle import AsyncLifecycleManager


class MultiSiteAgent:
    """Agent that crawls multiple sites using plugin adapters."""

    def __init__(
        self,
        model: str = "openrouter/mistralai/devstral-2512:free",
        config_path: str = "config/sites.yaml"
    ):
        self.model = model
        self.plugin_loader = PluginLoader()
        self.tool_registry = ToolRegistry()
        self.lifecycle = AsyncLifecycleManager()

        # Load enabled sites from config
        self.enabled_sites = self._load_enabled_sites(config_path)
        self.adapters = self._create_adapters()

        # Register tools
        self._register_tools()

        # Create LangGraph agent
        self.agent = self._create_agent()

    def _load_enabled_sites(self, config_path: str) -> dict:
        """Load enabled site configurations."""
        # Implementation: load from YAML/ENV
        # For now, return all available plugins
        return {name: True for name in self.plugin_loader.list_all()}

    def _create_adapters(self) -> dict[str, SiteAdapter]:
        """Create adapter instances."""
        adapters = {}
        for site_name in self.enabled_sites:
            try:
                adapter = self.plugin_loader.create(site_name)
                adapters[site_name] = adapter
            except Exception as e:
                print(f"Failed to create {site_name} adapter: {e}")
        return adapters

    def _register_tools(self) -> None:
        """Register all tools from adapters."""
        # Register universal tools first
        # (from src/tools/registry.py)

        # Register site-specific tools
        for site_name, adapter in self.adapters.items():
            site_tools = adapter.get_tools()
            for tool in site_tools:
                self.tool_registry.register_for_site(site_name, tool)

    def _create_agent(self):
        """Create DeepAgent with LangGraph."""
        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Skills middleware
        skills_backend = FilesystemBackend(root_dir="skills")
        skills_middleware = SkillsMiddleware(
            backend=skills_backend,
            sources=[f"/{name}-automation/" for name in self.adapters.keys()],
        )

        # Create agent
        return create_deep_agent(
            model=self.model,
            tools=self.tool_registry.get_all_tools(),
            system_prompt=system_prompt,
            middleware=[skills_middleware],
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt with site context."""
        sites_list = ", ".join(self.adapters.keys())

        return f"""You are a multi-site web automation agent.

**Supported Sites:** {sites_list}

## Core Workflow
1. Detect target site from task
2. Use site-specific tools and selectors
3. Get snapshot before acting
4. Verify actions with new snapshot

## Critical Rules
- Always use fresh refs after each action
- Use site-specific selectors from get_tools()
- Follow site authentication flows

## Site-Specific Notes
{self._build_site_notes()}
"""

    def _build_site_notes(self) -> str:
        """Build site-specific guidance."""
        notes = []
        for adapter in self.adapters.values():
            notes.append(f"""
### {adapter.site_name}
- Domain: {adapter.site_domain}
- Login: {adapter.get_login_url()}
""")
        return "\n".join(notes)

    async def start(self) -> None:
        """Initialize all adapters."""
        configs = {name: adapter.get_default_config() for name, adapter in self.adapters.items()}
        await self.lifecycle.initialize_all(self.adapters, configs)

    async def stop(self) -> None:
        """Shutdown all adapters."""
        await self.lifecycle.shutdown_all()

    async def run(self, task: str, thread_id: str = "default") -> dict:
        """Execute a task."""
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return result
```

---

## 8. pyproject.toml Configuration

```toml
[project]
name = "webcrawler-core"
version = "0.1.0"
description = "Multi-site web crawler with plugin architecture"
requires-python = ">=3.11"
dependencies = [
    "langchain>=0.1.0",
    "langgraph>=0.0.20",
    "playwright>=1.40.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

# Entry points for plugins
[project.entry-points."webcrawler.adapters"]
facebook = "src.plugins.facebook.adapter:FacebookAdapter"
twitter = "src.plugins.twitter.adapter:TwitterAdapter"
generic = "src.plugins.generic.adapter:GenericAdapter"

[project.entry-points."webcrawler.middlewares"]
rate_limit = "src.middlewares.rate_limit:RateLimitMiddleware"

# CLI scripts
[project.scripts]
webcrawler = "src.main:cli"
```

---

## 9. Testing Strategy

```python
# tests/test_plugin_loader.py
import pytest
from src.core.plugin_loader import PluginLoader
from src.core.protocols import SiteAdapter


class TestPluginLoader:
    """Test plugin loading and discovery."""

    def test_load_from_entrypoints(self):
        """Test loading from entry points."""
        loader = PluginLoader()
        plugins = loader.list_all()
        assert "facebook" in plugins

    def test_create_adapter(self):
        """Test creating adapter instance."""
        loader = PluginLoader()
        adapter = loader.create("facebook")

        # Check protocol implementation
        assert hasattr(adapter, "site_name")
        assert hasattr(adapter, "login")
        assert adapter.site_name == "Facebook"

    def test_unknown_plugin_raises(self):
        """Test that unknown plugin raises error."""
        loader = PluginLoader()
        with pytest.raises(ValueError, match="Unknown plugin"):
            loader.create("nonexistent")


# tests/test_facebook_adapter.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.core.protocols import CrawlConfig
from src.plugins.facebook.adapter import FacebookAdapter


class TestFacebookAdapter:
    """Test Facebook adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        config = CrawlConfig(base_url="https://www.facebook.com")
        return FacebookAdapter(config)

    def test_site_properties(self, adapter):
        """Test site identification."""
        assert adapter.site_name == "Facebook"
        assert adapter.site_domain == "facebook.com"

    def test_get_selectors(self, adapter):
        """Test selector definitions."""
        selectors = adapter.get_selectors()
        assert "email_input" in selectors
        assert "login_button" in selectors
        assert "post_button" in selectors

    @pytest.mark.asyncio
    async def test_login_success(self, adapter):
        """Test successful login flow."""
        # Mock page
        page = Mock()
        page.goto = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[{"name": "session"}])

        # Mock is_logged_in
        adapter.is_logged_in = Mock(return_value=True)

        result = await adapter.login(page, "user@test.com", "password")

        assert result.success is True
        assert "session" in str(result)

    def test_get_tools(self, adapter):
        """Test tool registration."""
        tools = adapter.get_tools()
        assert len(tools) > 0
        assert any(t.name == "facebook_post" for t in tools)
```

---

## 10. Migration Guide

### From FacebookSurferAgent to Multi-Site

**Phase 1: Extract Interface**
```python
# Before: src/agents/facebook_surfer.py
class FacebookSurferAgent:
    # Monolithic implementation

# After: src/plugins/facebook/adapter.py
class FacebookAdapter:
    # Implements SiteAdapter protocol
    # Contains only FB-specific logic
```

**Phase 2: Move Tools**
```python
# Before: Tools defined inline in agent
# After: src/plugins/facebook/tools.py
# Adapter.get_tools() returns list of LangChain tools
```

**Phase 3: Update Agent**
```python
# Before:
agent = FacebookSurferAgent()

# After:
loader = PluginLoader()
adapter = loader.create("facebook")
agent = MultiSiteAgent()
agent.adapters["facebook"] = adapter
```

---

## 11. Troubleshooting

### Common Issues

**Issue:** Plugin not discovered
```bash
# Check entry points are registered
python -c "from importlib.metadata import entry_points; print(list(entry_points(group='webcrawler.adapters')))"

# Check module structure
ls -la src/plugins/facebook/
```

**Issue:** Protocol validation fails
```python
# Use mypy to catch static type errors
mypy src/plugins/facebook/adapter.py

# Runtime check
isinstance(adapter, SiteAdapter)  # Requires @runtime_checkable
```

**Issue:** Async lifecycle hangs
```python
# Add timeouts
async with asyncio.timeout(30):
    await adapter.login(page, user, pass)

# Use TaskGroup for concurrent ops
async with asyncio.TaskGroup() as tg:
    tg.create_task(adapter.setup(context))
```

---

## References

- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [PEP 621 - pyproject.toml](https://peps.python.org/pep-0621/)
- [Pydantic V2 Docs](https://docs.pydantic.dev/latest/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Python 3.11 asyncio.TaskGroup](https://docs.python.org/3/library/asyncio.html#taskgroups)
