# Implementation Plan: Multi-Site Plugin Architecture

**Created:** 2025-01-19
**Status:** Ready for Implementation
**Estimated Duration:** 11-15 days

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Phase 1: Core Architecture](#phase-1-core-architecture)
4. [Phase 2: Facebook Adapter Migration](#phase-2-facebook-adapter-migration)
5. [Phase 3: Multi-Site Agent](#phase-3-multi-site-agent)
6. [Phase 4: Additional Adapters](#phase-4-additional-adapters)
7. [Phase 5: Testing & Documentation](#phase-5-testing--documentation)
8. [Rollout Strategy](#rollout-strategy)

---

## Overview

### Objective
Refactor FacebookSurferAgent into a multi-site web crawler with plugin architecture while maintaining 100% backward compatibility.

### Success Criteria
- ✅ All existing Facebook functionality works unchanged
- ✅ New MultiSiteAgent supports Facebook + Twitter + generic sites
- ✅ Plugin loading from entry points and directory scanning
- ✅ Type-safe Protocol-based interfaces
- ✅ Async lifecycle with TaskGroup
- ✅ Configuration via pydantic-settings
- ✅ Test coverage > 80%

### Technical Approach
**Protocol-based adapters** - Type-safe interfaces without inheritance
**Dual plugin loading** - Entry points (external) + directory scanning (bundled)
**Async-first lifecycle** - Python 3.11+ TaskGroup for structured concurrency
**Pydantic V2 config** - Multi-source configuration with validation

---

## Architecture

### Target Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    MultiSiteAgent                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LangGraph Workflow                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │ │
│  │  │ Detect   │─▶│ Switch   │─▶│ Crawl    │           │ │
│  │  │ Site     │  │ Adapter  │  │ Page     │           │ │
│  │  └──────────┘  └──────────┘  └──────────┘           │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              PluginLoader                               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │   Facebook   │  │   Twitter    │  │  Generic   │ │ │
│  │  │   Adapter    │  │   Adapter    │  │  Adapter   │ │ │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              ToolRegistry                               │ │
│  │  ┌─────────────────────────────────────────────────┐  │ │
│  │  │  Universal Tools (22 existing)                   │  │ │
│  │  │  + Site-Specific Tools from each adapter        │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Protocol over ABC** - Structural typing, no inheritance required
2. **Additive migration** - Keep FacebookSurferAgent, add MultiSiteAgent
3. **Entry points + importlib** - Support both external and bundled plugins
4. **Pydantic V2** - Type-safe configuration with multi-source loading
5. **TaskGroup lifecycle** - Safe concurrent initialization
6. **Backward compatibility** - Zero breaking changes

---

## Phase 1: Core Architecture

**Duration:** 3-4 days
**Goal:** Establish plugin infrastructure without breaking existing code

### 1.1 Create Protocol Definitions

**File:** `src/core/protocols.py`

```python
from typing import Protocol, runtime_checkable, Self
from pydantic import BaseModel, HttpUrl
from playwright.async_api import Page, BrowserContext

class CrawlConfig(BaseModel):
    """Base crawler configuration."""
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

@runtime_checkable
class SiteAdapter(Protocol):
    """Protocol for site-specific crawler adapters."""

    @property
    def site_name(self) -> str: ...

    @property
    def site_domain(self) -> str: ...

    def get_default_config(self) -> CrawlConfig: ...

    async def login(self, page: Page, username: str, password: str) -> AuthResult: ...

    def is_logged_in(self, page: Page) -> bool: ...

    def get_login_url(self) -> str: ...

    def get_selectors(self) -> dict[str, str]: ...

    def get_tools(self) -> list[Any]: ...

    async def setup(self, context: BrowserContext) -> None: ...

    async def teardown(self, context: BrowserContext) -> None: ...
```

**Tasks:**
- [ ] Create `src/core/` directory
- [ ] Define CrawlConfig, AuthResult models
- [ ] Define SiteAdapter protocol with all methods
- [ ] Add type hints and docstrings
- [ ] Add @runtime_checkable for isinstance() support

**Verification:**
```bash
mypy src/core/protocols.py
python -c "from src.core.protocols import SiteAdapter; print('OK')"
```

---

### 1.2 Implement Plugin Loader

**File:** `src/core/plugin_loader.py`

```python
from importlib.metadata import entry_points
from pathlib import Path
import importlib
import pkgutil

class PluginLoader:
    """Discover and load site adapter plugins."""

    def __init__(
        self,
        entry_point_group: str = "webcrawler.adapters",
        plugins_package: str = "src.plugins"
    ):
        self.entry_point_group = entry_point_group
        self.plugins_package = plugins_package
        self._plugins: dict[str, Type[SiteAdapter]] = {}
        self._load_from_entrypoints()
        self._load_from_directory()

    def _load_from_entrypoints(self) -> None:
        """Load from installed packages."""
        try:
            eps = entry_points(group=self.entry_point_group)
            for ep in eps:
                try:
                    adapter_class = ep.load()
                    self._plugins[ep.name] = adapter_class
                except Exception as e:
                    print(f"Failed to load {ep.name}: {e}")
        except Exception:
            pass  # No entry points found

    def _load_from_directory(self) -> None:
        """Load from local src/plugins/."""
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
            except ImportError as e:
                print(f"Failed to import {name}: {e}")

    def get(self, name: str) -> Type[SiteAdapter] | None:
        return self._plugins.get(name)

    def create(self, name: str, config: CrawlConfig | None = None) -> SiteAdapter:
        adapter_class = self.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown plugin: {name}")

        if config is None:
            config = adapter_class.get_default_config()

        return adapter_class(config)

    def list_all(self) -> list[str]:
        return list(self._plugins.keys())
```

**Tasks:**
- [ ] Implement PluginLoader class
- [ ] Add entry points loading
- [ ] Add directory scanning
- [ ] Add adapter class detection
- [ ] Add error handling
- [ ] Add logging

**Verification:**
```python
# Test in Python REPL
from src.core.plugin_loader import PluginLoader
loader = PluginLoader()
print(loader.list_all())
```

---

### 1.3 Configuration System

**File:** `src/core/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from typing import Literal

class ScraperSettings(BaseSettings):
    """Scraper settings from env/.env."""
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        extra="forbid",
    )

    target_domain: HttpUrl
    max_pages: int = Field(10, ge=1, le=1000)
    headless: bool = True
    concurrency_limit: int = Field(5, ge=1, le=20)
    log_level: Literal["DEBUG", "INFO", "WARNING"] = "INFO"
```

**Tasks:**
- [ ] Install pydantic-settings: `pip install pydantic-settings>=2.0.0`
- [ ] Create ScraperSettings model
- [ ] Create PluginSettings model
- [ ] Add validation rules
- [ ] Add example .env file

**Verification:**
```bash
cp config/.env.example config/.env
python -c "from src.core.config.settings import ScraperSettings; print('OK')"
```

---

### 1.4 Async Lifecycle Manager

**File:** `src/core/lifecycle.py`

```python
import asyncio
from enum import Enum, auto

class PluginState(Enum):
    LOADED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()

class AsyncLifecycleManager:
    """Manage async plugin lifecycle with TaskGroup."""

    def __init__(self):
        self._states: dict[str, PluginState] = {}
        self._contexts: dict[str, Any] = {}
        self._playwright = None

    async def initialize_all(self, adapters: dict[str, SiteAdapter], configs: dict[str, Any]) -> None:
        """Initialize all plugins concurrently."""
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()

        async with asyncio.TaskGroup() as tg:
            for name, adapter in adapters.items():
                config = configs.get(name)
                tg.create_task(self._initialize_one(name, adapter, config))

    async def shutdown_all(self) -> None:
        """Shutdown all plugins concurrently."""
        async with asyncio.TaskGroup() as tg:
            for name, context in self._contexts.items():
                tg.create_task(self._shutdown_one(name, context))

        if self._playwright:
            await self._playwright.stop()
```

**Tasks:**
- [ ] Define PluginState enum
- [ ] Implement AsyncLifecycleManager
- [ ] Use asyncio.TaskGroup for concurrency
- [ ] Add timeout handling
- [ ] Add error isolation

**Verification:**
```bash
pytest tests/test_lifecycle.py -v
```

---

### 1.5 Update pyproject.toml

**File:** `pyproject.toml`

Add entry points section:

```toml
[project.entry-points."webcrawler.adapters"]
facebook = "src.plugins.facebook.adapter:FacebookAdapter"
twitter = "src.plugins.twitter.adapter:TwitterAdapter"
generic = "src.plugins.generic.adapter:GenericAdapter"
```

**Tasks:**
- [ ] Add entry points section
- [ ] Add pydantic-settings to dependencies
- [ ] Update dependencies if needed

**Verification:**
```bash
pip install -e .
python -c "from importlib.metadata import entry_points; print(list(entry_points(group='webcrawler.adapters')))"
```

---

### Phase 1 Deliverables

- [ ] `src/core/protocols.py` - Protocol definitions
- [ ] `src/core/plugin_loader.py` - Plugin loading
- [ ] `src/core/config/settings.py` - Configuration models
- [ ] `src/core/lifecycle.py` - Async lifecycle
- [ ] Updated `pyproject.toml` - Entry points
- [ ] Tests for all components
- [ ] Documentation

**Success Criteria:**
- ✅ All type checks pass (mypy)
- ✅ Plugin loader discovers from both sources
- [ ] Configuration validates correctly
- [ ] Lifecycle manager handles errors gracefully

---

## Phase 2: Facebook Adapter Migration

**Duration:** 2-3 days
**Goal:** Extract Facebook logic into adapter without breaking existing agent

### 2.1 Create Facebook Adapter

**File:** `src/plugins/facebook/adapter.py`

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

    def _build_selectors(self) -> dict[str, str]:
        return {
            "email_input": "#email",
            "password_input": "#pass",
            "login_button": "button[name='login']",
            # ... all FB selectors
        }

    def get_default_config(self) -> CrawlConfig:
        return CrawlConfig(
            base_url="https://www.facebook.com",
            timeout=30000,
            headless=False,
        )

    async def login(self, page: Page, username: str, password: str) -> AuthResult:
        # Migrate from FacebookSessionManager
        ...

    def is_logged_in(self, page: Page) -> bool:
        # Migrate login detection logic
        ...

    def get_login_url(self) -> str:
        return self.LOGIN_URL

    def get_selectors(self) -> dict[str, str]:
        return self._selectors.copy()

    def get_tools(self) -> List[Any]:
        # Return FB-specific tools
        ...

    async def setup(self, context: BrowserContext) -> None:
        # Setup browser context
        ...

    async def teardown(self, context: BrowserContext) -> None:
        await context.clear_cookies()
```

**Tasks:**
- [ ] Create `src/plugins/facebook/` directory
- [ ] Implement FacebookAdapter class
- [ ] Migrate selectors from session module
- [ ] Migrate login logic
- [ ] Implement get_tools() method
- [ ] Add FB-specific tools

**Verification:**
```bash
python -c "from src.plugins.facebook.adapter import FacebookAdapter; print('OK')"
mypy src/plugins/facebook/adapter.py
```

---

### 2.2 Create Facebook Tools

**File:** `src/plugins/facebook/tools.py`

Extract FB-specific tools (if any) from main codebase.

**Tasks:**
- [ ] Identify FB-specific tools
- [ ] Create tool definitions
- [ ] Add Pydantic schemas
- [ ] Register in adapter

---

### 2.3 Create Facebook Configuration

**File:** `src/plugins/facebook/config.py`

```python
from pydantic import Field
from src.core.config.dynamic import DynamicConfigMixin

class FacebookConfig(DynamicConfigMixin):
    @staticmethod
    def get_config_schema() -> dict:
        return {
            "login_timeout": (int, Field(180, ge=60, le=600)),
            "manual_login": (bool, True),
            "screenshot_path": (str, "./screenshots/fb"),
        }
```

**Tasks:**
- [ ] Define FB config schema
- [ ] Add validation rules
- [ ] Add defaults

---

### 2.4 Create Plugin Package Init

**File:** `src/plugins/__init__.py` and `src/plugins/facebook/__init__.py`

**Tasks:**
- [ ] Create package structure
- [ ] Add __init__.py files
- [ ] Export adapter classes

---

### Phase 2 Deliverables

- [ ] `src/plugins/facebook/adapter.py` - Facebook adapter
- [ ] `src/plugins/facebook/tools.py` - FB-specific tools
- [ ] `src/plugins/facebook/config.py` - FB configuration
- [ ] Tests for Facebook adapter
- [ ] Documentation

**Success Criteria:**
- ✅ Facebook adapter implements SiteAdapter
- ✅ All existing FB functionality accessible through adapter
- ✅ Type checks pass
- ✅ Tests cover main scenarios

---

## Phase 3: Multi-Site Agent

**Duration:** 2-3 days
**Goal:** Create agent that uses plugins

### 3.1 Create Multi-Site Agent

**File:** `src/agents/multi_site_agent.py`

```python
from typing import Any
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware

from src.core.plugin_loader import PluginLoader
from src.core.lifecycle import AsyncLifecycleManager
from src.core.tool_registry import ToolRegistry

class MultiSiteAgent:
    """Agent that crawls multiple sites using plugins."""

    def __init__(
        self,
        model: str = "openrouter/mistralai/devstral-2512:free",
        config_path: str = "config/sites.yaml"
    ):
        self.model = model
        self.plugin_loader = PluginLoader()
        self.tool_registry = ToolRegistry()
        self.lifecycle = AsyncLifecycleManager()

        # Load adapters
        self.enabled_sites = self._load_enabled_sites(config_path)
        self.adapters = self._create_adapters()

        # Register tools
        self._register_tools()

        # Create agent
        self.agent = self._create_agent()

    def _load_enabled_sites(self, config_path: str) -> dict:
        # Load from config or default to all
        return {name: True for name in self.plugin_loader.list_all()}

    def _create_adapters(self) -> dict:
        adapters = {}
        for site_name in self.enabled_sites:
            try:
                adapter = self.plugin_loader.create(site_name)
                adapters[site_name] = adapter
            except Exception as e:
                print(f"Failed to create {site_name}: {e}")
        return adapters

    def _register_tools(self) -> None:
        # Register universal tools (existing 22 tools)
        from src.tools.registry import register_all_tools
        universal_registry = register_all_tools()
        for tool in universal_registry.get_all():
            self.tool_registry.register_universal(tool)

        # Register site-specific tools
        for site_name, adapter in self.adapters.items():
            for tool in adapter.get_tools():
                self.tool_registry.register_for_site(site_name, tool)

    def _create_agent(self):
        system_prompt = self._build_system_prompt()

        # Skills middleware
        skills_backend = FilesystemBackend(root_dir="skills")
        skills_middleware = SkillsMiddleware(
            backend=skills_backend,
            sources=[f"/{name}-automation/" for name in self.adapters.keys()],
        )

        return create_deep_agent(
            model=self.model,
            tools=self.tool_registry.get_all_tools(),
            system_prompt=system_prompt,
            middleware=[skills_middleware],
        )

    def _build_system_prompt(self) -> str:
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
"""

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

**Tasks:**
- [ ] Create MultiSiteAgent class
- [ ] Implement site detection
- [ ] Implement adapter switching
- [ ] Add skills middleware for multiple sites
- [ ] Add lifecycle management

**Verification:**
```bash
python -c "from src.agents.multi_site_agent import MultiSiteAgent; agent = MultiSiteAgent(); print(agent.adapters.keys())"
```

---

### 3.2 Update CLI

**File:** `src/main.py`

Add support for multi-site agent:

```python
@app.command()
def run(
    task: str = typer.Argument(None),
    site: str = typer.Option("facebook", help="Site to automate"),
    stream: bool = typer.Option(False, "--stream"),
    debug: bool = typer.Option(False, "--debug"),
    thread: str = typer.Option("default", "--thread"),
    model: str = typer.Option("openrouter/mistralai/devstral-2512:free", "--model"),
):
    """Run automation task."""
    if site == "facebook" and not MULTI_SITE_ENABLED:
        # Use existing FacebookSurferAgent
        agent = FacebookSurferAgent(model=model)
    else:
        # Use MultiSiteAgent
        agent = MultiSiteAgent(model=model)
        asyncio.run(agent.start())

    # Execute task
    result = asyncio.run(agent.run(task, thread_id=thread))
    print(result)
```

**Tasks:**
- [ ] Add --site flag
- [ ] Add multi-site agent option
- [ ] Keep backward compatibility
- [ ] Update help text

---

### Phase 3 Deliverables

- [ ] `src/agents/multi_site_agent.py` - Multi-site agent
- [ ] Updated `src/main.py` - CLI with site selection
- [ ] Integration tests
- [ ] Documentation

**Success Criteria:**
- ✅ MultiSiteAgent crawls Facebook using FacebookAdapter
- ✅ CLI supports --site flag
- ✅ Backward compatibility maintained
- ✅ Integration tests pass

---

## Phase 4: Additional Adapters

**Duration:** 2 days
**Goal:** Demonstrate extensibility with new adapters

### 4.1 Create Generic Adapter

**File:** `src/plugins/generic/adapter.py`

```python
class GenericAdapter:
    """Generic/fallback adapter for unknown sites."""

    site_name: str = "Generic"
    site_domain: str = "*"

    def __init__(self, config: CrawlConfig):
        self.config = config

    def get_default_config(self) -> CrawlConfig:
        return CrawlConfig(
            base_url="https://example.com",
            timeout=30000,
            headless=True,
        )

    async def login(self, page: Page, username: str, password: str) -> AuthResult:
        return AuthResult(
            success=False,
            message="Generic adapter does not support automatic login"
        )

    def is_logged_in(self, page: Page) -> bool:
        return True  # Assume logged in

    def get_login_url(self) -> str:
        return ""

    def get_selectors(self) -> dict[str, str]:
        return {}  # No site-specific selectors

    def get_tools(self) -> List[Any]:
        return []  # No site-specific tools

    async def setup(self, context: BrowserContext) -> None:
        pass

    async def teardown(self, context: BrowserContext) -> None:
        pass
```

**Tasks:**
- [ ] Create generic adapter
- [ ] Implement all protocol methods
- [ ] Add tests

---

### 4.2 Create Twitter Adapter (Template)

**File:** `src/plugins/twitter/adapter.py`

```python
class TwitterAdapter:
    """Twitter-specific crawler adapter."""

    site_name: str = "Twitter"
    site_domain: str = "twitter.com"
    __version__ = "1.0.0"

    def __init__(self, config: CrawlConfig):
        self.config = config
        self._selectors = self._build_selectors()

    def _build_selectors(self) -> dict[str, str]:
        return {
            "tweet_button": "[data-testid='SideNav_NewTweet_Button']",
            "tweet_textbox": "[data-testid='tweetTextarea_0']",
            # ... more selectors
        }

    # ... implement all protocol methods
```

**Tasks:**
- [ ] Create Twitter adapter structure
- [ ] Define Twitter selectors
- [ ] Implement basic methods
- [ ] Add placeholder login
- [ ] Add tests

**Note:** Full Twitter automation not required - just demonstrate plugin structure

---

### 4.3 Create Plugin Development Guide

**File:** `docs/PLUGIN_DEVELOPMENT.md`

Sections:
1. Overview
2. Quick Start
3. Adapter Implementation
4. Configuration
5. Tools
6. Testing
7. Best Practices
8. Example: Creating a LinkedIn Adapter

**Tasks:**
- [ ] Write plugin development guide
- [ ] Include code examples
- [ ] Include troubleshooting section
- [ ] Include template code

---

### Phase 4 Deliverables

- [ ] `src/plugins/generic/adapter.py` - Generic adapter
- [ ] `src/plugins/twitter/adapter.py` - Twitter template
- [ ] `docs/PLUGIN_DEVELOPMENT.md` - Development guide
- [ ] Tests for new adapters

**Success Criteria:**
- ✅ Generic adapter loads successfully
- ✅ Twitter adapter structure complete
- ✅ Plugin guide is clear and comprehensive

---

## Phase 5: Testing & Documentation

**Duration:** 2-3 days
**Goal:** Comprehensive test coverage and documentation

### 5.1 Unit Tests

**Files:**
- `tests/test_protocols.py`
- `tests/test_plugin_loader.py`
- `tests/test_lifecycle.py`
- `tests/test_config.py`

**Coverage Targets:**
- Core modules: > 90%
- Adapters: > 80%
- Overall: > 80%

**Tasks:**
- [ ] Test protocol definitions
- [ ] Test plugin loading (entry points + directory)
- [ ] Test lifecycle manager
- [ ] Test configuration validation
- [ ] Test adapter implementations
- [ ] Add mock fixtures

---

### 5.2 Integration Tests

**File:** `tests/test_multi_site_agent.py`

```python
@pytest.mark.asyncio
async def test_multi_site_facebook():
    """Test Facebook crawling through multi-site agent."""
    agent = MultiSiteAgent()
    await agent.start()

    result = await agent.run("Navigate to Facebook", thread_id="test")

    assert result is not None
    await agent.stop()

@pytest.mark.asyncio
async def test_site_detection():
    """Test automatic site detection."""
    agent = MultiSiteAgent()
    site = agent._detect_site_from_task("Post to Facebook")
    assert site == "facebook"
```

**Tasks:**
- [ ] Test multi-site agent initialization
- [ ] Test site detection
- [ ] Test adapter switching
- [ ] Test tool registration
- [ ] Add Playwright fixtures

---

### 5.3 Documentation

**Files:**
- `docs/MIGRATION_GUIDE.md` - How to migrate from FacebookSurferAgent
- `docs/ARCHITECTURE.md` - System architecture overview
- Update `README.md` - Multi-site support

**Tasks:**
- [ ] Write migration guide
- [ ] Document architecture
- [ ] Update README with multi-site examples
- [ ] Add API documentation
- [ ] Create troubleshooting guide

---

### 5.4 Examples

**File:** `examples/multi_site_example.py`

```python
import asyncio
from src.agents.multi_site_agent import MultiSiteAgent

async def main():
    agent = MultiSiteAgent()
    await agent.start()

    # Crawl Facebook
    result = await agent.run("Post to Facebook with text 'Hello World'")
    print(result)

    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Tasks:**
- [ ] Create multi-site example
- [ ] Create plugin development example
- [ ] Create configuration examples
- [ ] Add comments and explanations

---

### Phase 5 Deliverables

- [ ] Comprehensive test suite (>80% coverage)
- [ ] Integration tests
- [ ] Migration guide
- [ ] Architecture documentation
- [ ] Updated README
- [ ] Working examples

**Success Criteria:**
- ✅ All tests pass
- ✅ Test coverage > 80%
- ✅ Documentation complete
- ✅ Examples run successfully

---

## Rollout Strategy

### Phase-by-Phase Rollout

**Phase 1 (Week 1):**
- Deploy core architecture (no user-facing changes)
- Verify no breaking changes
- Monitor performance

**Phase 2 (Week 1-2):**
- Deploy Facebook adapter alongside existing agent
- Test internally
- Gather feedback

**Phase 3 (Week 2):**
- Deploy MultiSiteAgent as beta feature
- Document migration path
- Support both agents in parallel

**Phase 4 (Week 3):**
- Add additional adapters
- Refine plugin development guide
- Community testing

**Phase 5 (Week 3-4):**
- Complete testing and documentation
- Stable release
- Deprecation notice for FacebookSurferAgent

### Backward Compatibility

**Keep Working:**
- FacebookSurferAgent class
- All CLI commands
- Configuration format
- Session persistence

**Deprecation Timeline:**
- v1.x: Both agents supported
- v2.0: FacebookSurferAgent deprecated (warnings)
- v3.0: FacebookSurferAgent removed

### Monitoring

**Metrics to Track:**
- Plugin load time
- Adapter initialization time
- Task execution time (vs baseline)
- Error rates per adapter
- Memory usage

**Success Indicators:**
- < 5% performance overhead
- < 1% error rate increase
- No breaking change reports
- Positive community feedback

---

## Risk Management

### High-Risk Areas

**1. Async Lifecycle Complexity**
- **Risk:** Deadlocks, resource leaks
- **Mitigation:** Use TaskGroup, timeouts, comprehensive testing

**2. Breaking Changes**
- **Risk:** Regressing existing functionality
- **Mitigation:** Keep FacebookSurferAgent, extensive testing

**3. Performance Regression**
- **Risk:** Slower than current implementation
- **Mitigation:** Profile before/after, lazy loading, optimization

### Contingency Plans

**If Phase 1 Fails:**
- Revert to simpler protocol design
- Reduce scope of plugin system
- Extend timeline

**If Phase 2 Fails:**
- Keep FacebookSurferAgent as primary
- Defer multi-site support
- Simplify adapter interface

**If Phase 3 Fails:**
- Release plugin system without multi-site agent
- Document manual adapter usage
- Revisit agent design

---

## Definition of Done

### Code Complete
- ✅ All phases implemented
- ✅ All tests passing
- ✅ Type checking passes (mypy)
- ✅ Linting passes (ruff)

### Documentation Complete
- ✅ Plugin development guide
- ✅ Migration guide
- ✅ Architecture documentation
- ✅ API documentation
- ✅ Working examples

### Quality Gates
- ✅ Test coverage > 80%
- ✅ No critical bugs
- ✅ Performance overhead < 5%
- ✅ Backward compatibility verified
- ✅ Documentation reviewed

### Approval Required
- [ ] Technical review complete
- [ ] Security review complete
- [ ] Performance review complete
- [ ] Documentation review complete

---

## Next Steps

1. **Review Plan** - Ensure all stakeholders agree
2. **Setup Environment** - Install dependencies, create branches
3. **Start Phase 1** - Begin with core architecture
4. **Daily Standups** - Track progress, blockers
5. **Phase Gates** - Review and approve each phase
6. **Final Testing** - Comprehensive test suite
7. **Documentation** - Complete all guides
8. **Release** - Deploy with monitoring

---

## Appendix

### File Structure After Implementation

```
src/
├── core/
│   ├── __init__.py
│   ├── protocols.py              # NEW
│   ├── plugin_loader.py          # NEW
│   ├── lifecycle.py              # NEW
│   └── config/
│       ├── __init__.py           # NEW
│       └── settings.py           # NEW
│
├── plugins/                      # NEW
│   ├── __init__.py
│   ├── facebook/
│   │   ├── __init__.py
│   │   ├── adapter.py            # NEW
│   │   ├── tools.py              # NEW
│   │   └── config.py             # NEW
│   ├── twitter/
│   │   └── adapter.py            # NEW
│   └── generic/
│       └── adapter.py            # NEW
│
├── agents/
│   ├── __init__.py
│   ├── facebook_surfer.py        # KEEP (existing)
│   └── multi_site_agent.py       # NEW
│
├── tools/                        # KEEP (existing)
├── session/                      # KEEP (existing)
└── main.py                       # MODIFY (add --site flag)

tests/
├── test_protocols.py             # NEW
├── test_plugin_loader.py         # NEW
├── test_lifecycle.py             # NEW
├── test_adapters/                # NEW
│   ├── test_facebook.py
│   └── test_twitter.py
└── test_multi_site_agent.py      # NEW

docs/
├── PLUGIN_DEVELOPMENT.md         # NEW
├── MIGRATION_GUIDE.md            # NEW
└── ARCHITECTURE.md               # NEW

config/
├── sites.yaml                    # NEW
└── .env.example                  # MODIFY

pyproject.toml                    # MODIFY (add entry points)
```

### Dependencies

**Add:**
```toml
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

**Existing (keep):**
- playwright>=1.40.0
- langchain>=0.1.0
- langgraph>=0.0.20
- deepagents

### Commands

**Installation:**
```bash
pip install -e ".[agent,dev]"
```

**Development:**
```bash
mypy src/
ruff check src/ --fix
pytest tests/ -v
```

**Testing:**
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_plugin_loader.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Running:**
```bash
# Old way (still works)
python -m facebook-surfer run "Post to Facebook"

# New way (multi-site)
python -m facebook-surfer run "Post to Facebook" --site facebook
python -m facebook-surfer run "Tweet hello" --site twitter
```
