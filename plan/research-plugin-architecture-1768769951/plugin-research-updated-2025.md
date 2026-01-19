# Research: Plugin Architecture for Multi-Purpose Web Crawler (Updated 2025-01-19)

**Date:** 2025-01-19
**Context:** Python 3.11+, LangChain, LangGraph, Playwright, Pydantic v2, DeepAgents
**Purpose:** Evolve FacebookSurferAgent into multi-site crawler with plugin architecture

---

## Executive Summary

Updated research for 2025-2026 Python plugin patterns. Key developments:

1. **Pydantic V2** - Major performance improvements, `pydantic-settings` for config
2. **Python 3.11+ `asyncio.TaskGroup`** - Better structured concurrency for plugins
3. **PEP 621 maturity** - `pyproject.toml` standard for entry points
4. **Type system evolution** - `Self` type (PEP 673), enhanced Protocol support

**Recommendation:** Protocol-based adapters with `pydantic-settings` config, async lifecycles using `TaskGroup`, entry points for external plugins.

---

## 1. Type-Safe Plugin Interfaces (2025 Update)

### Protocol vs ABC Decision Matrix

| Criteria | Protocol (PEP 544) | ABC (PEP 3119) |
|----------|-------------------|----------------|
| Type checking | Structural (static) | Nominal (runtime) |
| Inheritance required | No | Yes |
| `isinstance()` support | With `@runtime_checkable` | Native |
| Best for | Flexibility, third-party | Strict enforcement, shared logic |
| LangChain compatibility | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**2025 Recommendation:** Use `Protocol` as primary interface, ABC for shared base implementations.

### Modern Protocol Definition with `Self` (PEP 673)

```python
# src/core/protocols.py
from typing import Protocol, runtime_checkable, Self
from pydantic import BaseModel, HttpUrl
from playwright.async_api import Page, BrowserContext

class CrawlConfig(BaseModel):
    """Base configuration - Pydantic V2 for performance."""
    base_url: HttpUrl
    timeout: int = 30000
    headless: bool = True
    user_agent: str | None = None
    viewport: dict = {"width": 1920, "height": 1080}


class AuthResult(BaseModel):
    """Authentication result with type-safe validation."""
    success: bool
    message: str
    session_data: dict | None = None


@runtime_checkable
class SiteAdapter(Protocol):
    """Protocol for site-specific crawler adapters.

    Using Protocol (structural subtyping) allows any class with matching
    methods to work, without requiring explicit inheritance.
    """

    @property
    def site_name(self) -> str: ...

    @property
    def site_domain(self) -> str: ...

    def get_default_config(self) -> CrawlConfig: ...

    async def login(self, page: Page, username: str, password: str) -> AuthResult: ...

    def is_logged_in(self, page: Page) -> bool: ...

    def get_selectors(self) -> dict[str, str]: ...

    def get_tools(self) -> list[Any]: ...

    async def setup(self, context: BrowserContext) -> None: ...

    async def teardown(self, context: BrowserContext) -> None: ...


# 2025: Use Self type for fluent chaining
@runtime_checkable
class ConfigurableAdapter(Protocol):
    """Protocol for adapters with fluent configuration."""

    def with_config(self, config: CrawlConfig) -> Self: ...
    def with_timeout(self, timeout: int) -> Self: ...
```

---

## 2. Plugin Discovery (2025 Standards)

### Entry Points (PEP 621 - pyproject.toml)

**Standard for distributed plugins:**

```toml
# pyproject.toml (core package)
[project]
name = "webcrawler-core"
version = "0.1.0"
requires-python = ">=3.11"

[project.entry-points."webcrawler.adapters"]
# Built-in adapters
facebook = "src.plugins.facebook:FacebookAdapter"
twitter = "src.plugins.twitter:TwitterAdapter"

[project.entry-points."webcrawler.middlewares"]
rate_limit = "src.middlewares.rate_limit:RateLimitMiddleware"
anti_bot = "src.middlewares.anti_bot:AntiBotMiddleware"
```

**Loading (Python 3.10+ API):**

```python
# src/core/plugin_loader.py
from importlib.metadata import entry_points
from typing import Type, Any
from pathlib import Path

class PluginLoader:
    """Load plugins using modern entry_points API."""

    def __init__(self, entry_point_group: str = "webcrawler.adapters"):
        self.group = entry_point_group
        self._plugins: dict[str, Type[SiteAdapter]] = {}
        self._load_from_entrypoints()
        self._load_from_directory()

    def _load_from_entrypoints(self) -> None:
        """Load plugins from installed packages."""
        try:
            eps = entry_points(group=self.group)
            for ep in eps:
                try:
                    adapter_class = ep.load()
                    self._plugins[ep.name] = adapter_class
                    print(f"Loaded plugin: {ep.name}")
                except Exception as e:
                    print(f"Failed to load {ep.name}: {e}")
        except Exception as e:
            print(f"No entry points found: {e}")

    def _load_from_directory(self) -> None:
        """Load plugins from local src/plugins/ directory."""
        import importlib
        import pkgutil

        plugins_path = Path(__file__).parent.parent / "plugins"
        if not plugins_path.exists():
            return

        for finder, name, ispkg in pkgutil.iter_modules([plugins_path]):
            if name.startswith("_"):
                continue

            try:
                module = importlib.import_module(f"src.plugins.{name}.adapter")
                adapter_class = self._find_adapter_class(module)
                if adapter_class:
                    self._plugins[name] = adapter_class
            except ImportError as e:
                print(f"Failed to import {name}: {e}")

    def _find_adapter_class(self, module: Any) -> Type[SiteAdapter] | None:
        """Find adapter class in module."""
        for attr_name in dir(module):
            if "Adapter" in attr_name:
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and self._is_site_adapter(attr):
                    return attr
        return None

    def _is_site_adapter(self, cls: Type) -> bool:
        """Check if class implements SiteAdapter protocol."""
        required = ["site_name", "site_domain", "login", "is_logged_in"]
        return all(hasattr(cls, name) for name in required)

    def get(self, name: str) -> Type[SiteAdapter] | None:
        return self._plugins.get(name)

    def list_all(self) -> list[str]:
        return list(self._plugins.keys())
```

---

## 3. Configuration with Pydantic V2 (2025)

### Using `pydantic-settings`

**New in Pydantic V2:** dedicated settings library for multi-source config.

```python
# pip install pydantic-settings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from typing import Literal

class ScraperSettings(BaseSettings):
    """Plugin settings with multi-source loading."""
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    target_domain: HttpUrl
    max_pages: int = Field(10, ge=1)
    headless: bool = True
    concurrency_limit: int = Field(5, ge=1)
    log_level: Literal["DEBUG", "INFO", "WARNING"] = "INFO"


class PluginConfig(BaseSettings):
    """Configuration loaded from env vars, .env, or direct init."""
    model_config = SettingsConfigDict(
        env_prefix="PLUGIN_",
        env_file=".env",
    )

    api_key: str = Field(..., min_length=10)
    enabled: bool = True
    scraper: ScraperSettings  # Nested settings


# Usage: config = PluginConfig()  # Auto-loads from env/.env
# Or: config = PluginConfig(api_key="key", scraper={...})
```

### Dynamic Config Schemas

```python
from pydantic import create_model

class PluginWithDynamicConfig:
    """Plugin that defines its own config schema."""

    @staticmethod
    def get_config_schema() -> dict[str, tuple[type, Any]]:
        return {
            "custom_setting_1": (str, "default"),
            "custom_setting_2": (int, Field(..., ge=0)),
        }


def create_plugin_config(plugin_name: str, config_data: dict) -> BaseModel:
    """Create dynamic config model from plugin schema."""
    schema = PluginWithDynamicConfig.get_config_schema()
    DynamicConfig = create_model(
        f"{plugin_name}Config",
        **schema
    )
    return DynamicConfig(**config_data)
```

---

## 4. Async Lifecycle with `TaskGroup` (Python 3.11+)

### Structured Concurrency for Plugins

**2025 Feature:** `asyncio.TaskGroup` for safer concurrent task management.

```python
# src/core/lifecycle.py
import asyncio
from enum import Enum, auto
from typing import Any

class PluginState(Enum):
    LOADED = auto()
    INITIALIZED = auto()
    STARTED = auto()
    STOPPED = auto()
    ERROR = auto()


class AsyncLifecycleManager:
    """Manage async plugin lifecycle with TaskGroup."""

    def __init__(self):
        self._states: dict[str, PluginState] = {}
        self._contexts: dict[str, Any] = {}

    async def initialize_all(self, adapters: dict[str, SiteAdapter]) -> None:
        """Initialize all plugins concurrently using TaskGroup."""
        async with asyncio.TaskGroup() as tg:
            for name, adapter in adapters.items():
                tg.create_task(self._initialize_one(name, adapter))

    async def _initialize_one(self, name: str, adapter: SiteAdapter) -> None:
        """Initialize single plugin with error handling."""
        try:
            # Setup phase
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()

            await adapter.setup(context)

            self._states[name] = PluginState.INITIALIZED
            self._contexts[name] = {"browser": browser, "context": context}
            print(f"Initialized: {name}")

        except Exception as e:
            self._states[name] = PluginState.ERROR
            print(f"Failed to initialize {name}: {e}")
            # Cancel other tasks if critical failure
            raise

    async def shutdown_all(self) -> None:
        """Shutdown all plugins concurrently."""
        async with asyncio.TaskGroup() as tg:
            for name, context in self._contexts.items():
                tg.create_task(self._shutdown_one(name, context))

    async def _shutdown_one(self, name: str, context: dict) -> None:
        """Shutdown single plugin."""
        try:
            await context["browser"].close()
            self._states[name] = PluginState.STOPPED
        except Exception as e:
            print(f"Error shutting down {name}: {e}")
```

---

## 5. Integration with LangChain/LangGraph (2025)

### Dynamic Tool Registration

```python
# src/core/tool_registry.py
from typing import Any
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class ToolRegistry:
    """Registry for universal and plugin-specific tools."""

    def __init__(self):
        self._universal: list[StructuredTool] = []
        self._by_site: dict[str, list[StructuredTool]] = {}

    def register_universal(self, tool: StructuredTool) -> None:
        """Register tool available to all sites."""
        self._universal.append(tool)

    def register_for_site(self, site: str, tool: StructuredTool) -> None:
        """Register site-specific tool."""
        if site not in self._by_site:
            self._by_site[site] = []
        self._by_site[site].append(tool)

    def get_tools_for_site(self, site: str) -> list[StructuredTool]:
        """Get all tools for specific site."""
        tools = self._universal.copy()
        tools.extend(self._by_site.get(site, []))
        return tools

    def get_all_tools(self) -> list[StructuredTool]:
        """Get all registered tools."""
        all_tools = self._universal.copy()
        for site_tools in self._by_site.values():
            all_tools.extend(site_tools)
        return all_tools


# Usage in adapter
class FacebookAdapter:
    def get_tools(self) -> list[StructuredTool]:
        """Return Facebook-specific LangChain tools."""

        class FBPostInput(BaseModel):
            text: str = Field(description="Post content")
            privacy: str = Field(default="Public")

        def fb_post(text: str, privacy: str = "Public") -> str:
            return f"Posted: {text} ({privacy})"

        return [
            StructuredTool.from_function(
                name="facebook_post",
                description="Create Facebook post",
                func=fb_post,
                args_schema=FBPostInput,
            )
        ]
```

### LangGraph Custom Nodes with Plugins

```python
# src/agents/multi_site_agent.py
from typing import Any, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class CrawlerState(TypedDict):
    messages: list[dict]
    current_site: str | None
    active_adapter: Any | None
    urls_to_visit: list[str]
    visited_urls: list[str]
    extracted_data: list[dict]


async def fetch_node(state: CrawlerState, config: dict) -> CrawlerState:
    """LangGraph node: fetch page using active adapter."""
    adapter = state.get("active_adapter")
    if not adapter or not state.get("urls_to_visit"):
        return state

    url = state["urls_to_visit"].pop(0)

    # Use adapter's tools (simplified)
    page_content = f"Fetched {url} using {adapter.site_name}"
    state["extracted_data"].append({"url": url, "content": page_content})
    state["visited_urls"].append(url)

    return state


async def switch_site_node(state: CrawlerState, site_name: str) -> CrawlerState:
    """LangGraph node: switch to different site adapter."""
    loader = config.get("plugin_loader")
    adapter = loader.create_adapter(site_name)

    state["current_site"] = site_name
    state["active_adapter"] = adapter

    return state


def build_multi_site_graph() -> StateGraph:
    """Build LangGraph workflow for multi-site crawling."""
    workflow = StateGraph(CrawlerState)

    workflow.add_node("fetch", fetch_node)
    workflow.add_node("switch_site", switch_site_node)

    workflow.add_edge("switch_site", "fetch")
    workflow.add_edge("fetch", END)

    workflow.set_entry_point("switch_site")

    return workflow.compile(checkpointer=MemorySaver())
```

---

## 6. Hot-Reloading for Development (2025)

### Recommended Approach: Process Restart

**For Playwright-based crawlers, full restart is most reliable:**

```python
# src/dev/hotreload.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import os

class PluginReloadHandler(FileSystemEventHandler):
    """Watch for plugin changes and trigger restart."""

    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
        self._debounce_timer = None

    def on_modified(self, event):
        """Handle file modification with debouncing."""
        if event.src_path.endswith(".py"):
            # Debounce rapid changes
            if self._debounce_timer:
                self._debounce_timer.cancel()

            import threading
            self._debounce_timer = threading.Timer(1.0, self._trigger_restart)
            self._debounce_timer.start()

    def _trigger_restart(self):
        """Trigger application restart."""
        print("\nPlugin changed. Restarting...")
        self.restart_callback()


def setup_dev_watcher(plugins_dir: str = "src/plugins"):
    """Setup file watcher for development."""
    handler = PluginReloadHandler(restart_app)
    observer = Observer()
    observer.schedule(handler, plugins_dir, recursive=True)
    observer.start()
    return observer


def restart_app():
    """Restart the application."""
    os.execv(sys.executable, [sys.executable] + sys.argv)
```

**Alternative:** Use tools like `Reloadium` or `Jurigued` for in-place patching (less reliable with stateful apps).

---

## 7. Security Best Practices (2025)

### Process Isolation for Untrusted Plugins

```python
# src/core/isolated_runner.py
import asyncio
import multiprocessing as mp
from typing import Any

def run_plugin_in_process(
    plugin_module: str,
    function: str,
    args: tuple = (),
    timeout: int = 30
) -> Any:
    """Run plugin function in separate process with timeout."""

    def worker(queue, module, func, args):
        """Worker process function."""
        try:
            import importlib
            module = importlib.import_module(module)
            result = getattr(module, func)(*args)
            queue.put(("success", result))
        except Exception as e:
            queue.put(("error", str(e)))

    queue = mp.Queue()
    process = mp.Process(
        target=worker,
        args=(queue, plugin_module, function, args)
    )
    process.start()
    process.join(timeout=timeout)

    if process.is_alive():
        process.terminate()
        raise TimeoutError(f"Plugin {plugin_module} timed out")

    if not queue.empty():
        status, result = queue.get()
        if status == "error":
            raise RuntimeError(f"Plugin error: {result}")
        return result

    raise RuntimeError("Plugin process failed silently")
```

### Resource Limits

```python
# src/core/resource_limits.py
import resource
import psutil

def set_process_limits():
    """Set resource limits for plugin processes."""
    # Limit memory (2GB)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, hard))

    # Limit CPU time (60 seconds)
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    resource.setrlimit(resource.RLIMIT_CPU, (60, hard))

    # Limit file descriptors
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, hard))


def monitor_resources():
    """Monitor and log resource usage."""
    process = psutil.Process()
    return {
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "num_fds": process.num_fds(),
        "num_threads": process.num_threads(),
    }
```

---

## 8. Version Compatibility (2025)

### Semantic Versioning for Plugins

```python
# src/core/version.py
from packaging import version
from typing import Protocol

class VersionedPlugin(Protocol):
    """Protocol for versioned plugins."""

    @property
    def plugin_version(self) -> str: ...

    @property
    def min_core_version(self) -> str: ...

    @property
    def max_core_version(self) -> str | None: ...
    # None = no upper limit


class VersionChecker:
    """Check plugin-core version compatibility."""

    CORE_VERSION = "0.1.0"

    def is_compatible(self, plugin: VersionedPlugin) -> tuple[bool, str]:
        """Check if plugin is compatible with core version."""
        core_ver = version.parse(self.CORE_VERSION)
        min_ver = version.parse(plugin.min_core_version)

        if core_ver < min_ver:
            return False, f"Core {self.CORE_VERSION} < minimum {plugin.min_core_version}"

        if plugin.max_core_version:
            max_ver = version.parse(plugin.max_core_version)
            if core_ver > max_ver:
                return False, f"Core {self.CORE_VERSION} > maximum {plugin.max_core_version}"

        return True, "Compatible"
```

### API Versioning Strategy

```python
# Support multiple API versions concurrently
class AdapterFactory:
    """Factory that handles multiple API versions."""

    def create_adapter(self, name: str, api_version: str = "v2") -> SiteAdapter:
        """Create adapter for specific API version."""
        if api_version == "v2":
            return self._create_v2_adapter(name)
        elif api_version == "v1":
            return self._create_v1_adapter(name)
        else:
            raise ValueError(f"Unknown API version: {api_version}")

    def _create_v2_adapter(self, name: str) -> SiteAdapter:
        """Create V2 adapter with async support."""
        module = importlib.import_module(f"src.plugins.{name}.adapter_v2")
        return getattr(module, f"{name.capitalize()}AdapterV2")()

    def _create_v1_adapter(self, name: str) -> SiteAdapter:
        """Create V1 adapter (legacy support)."""
        module = importlib.import_module(f"src.plugins.{name}.adapter")
        return getattr(module, f"{name.capitalize()}Adapter")()
```

---

## 9. Performance Optimization (2025)

### Lazy Plugin Loading

```python
class LazyPluginLoader:
    """Load plugins only when needed."""

    def __init__(self):
        self._plugin_factories: dict[str, callable] = {}
        self._instances: dict[str, SiteAdapter] = {}

    def register_factory(self, name: str, factory: callable) -> None:
        """Register plugin factory (not instance)."""
        self._plugin_factories[name] = factory

    def get_plugin(self, name: str) -> SiteAdapter:
        """Get or create plugin instance."""
        if name not in self._instances:
            if name not in self._plugin_factories:
                raise ValueError(f"Unknown plugin: {name}")

            print(f"Lazy loading plugin: {name}")
            self._instances[name] = self._plugin_factories[name]()

        return self._instances[name]
```

### Caching Strategies

```python
from functools import lru_cache
from typing import Optional
import hashlib
import json

class CachedAdapter:
    """Adapter with caching for expensive operations."""

    def __init__(self, base_adapter: SiteAdapter):
        self._adapter = base_adapter
        self._cache: dict[str, Any] = {}

    @lru_cache(maxsize=128)
    def get_selectors(self) -> dict[str, str]:
        """Cache selectors (immutable data)."""
        return self._adapter.get_selectors()

    async def cached_fetch(self, url: str, ttl: int = 300) -> dict:
        """Fetch with TTL-based caching."""
        cache_key = hashlib.md5(url.encode()).hexdigest()

        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < ttl:
                print(f"Cache hit: {url}")
                return cached_data

        # Fetch and cache
        data = await self._adapter.fetch(url)
        self._cache[cache_key] = (data, time.time())
        return data
```

---

## 10. Directory Structure (2025)

```
src/
├── core/
│   ├── __init__.py
│   ├── protocols.py              # Protocol definitions
│   ├── plugin_loader.py          # Entry points + directory scanning
│   ├── registry.py               # Plugin registry
│   ├── lifecycle.py              # Async lifecycle with TaskGroup
│   ├── tool_registry.py          # LangChain tool registry
│   ├── version.py                # Version checking
│   └── config/
│       ├── settings.py           # pydantic-settings configs
│       └── schemas.py            # Dynamic schema generation
│
├── plugins/
│   ├── __init__.py
│   ├── facebook/
│   │   ├── __init__.py
│   │   ├── adapter.py            # FacebookAdapter (implements SiteAdapter)
│   │   ├── adapter_v2.py         # V2 API version
│   │   ├── config.py             # FB-specific settings
│   │   └── tools.py              # FB-specific LangChain tools
│   ├── twitter/
│   │   └── ...
│   └── generic/
│       └── ...
│
├── agents/
│   ├── __init__.py
│   ├── facebook_surfer.py        # Original (keep for compatibility)
│   └── multi_site_agent.py       # New multi-site agent
│
├── tools/                        # Universal tools (unchanged)
│   └── ...
│
└── session/                      # Session management (unchanged)
    └── ...

config/
├── sites.yaml                    # Site configurations
├── plugins.yaml                  # Plugin settings
└── .env.example                  # Environment template

skills/
├── facebook-automation/
├── twitter-automation/
└── linkedin-automation/

tests/
├── test_protocols.py
├── test_plugin_loader.py
└── test_adapters/
    ├── test_facebook.py
    └── test_twitter.py

pyproject.toml                    # Add entry points
```

---

## 11. pyproject.toml Entry Points (Complete)

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
    "deepagents",  # Custom framework
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "watchdog>=3.0.0",  # For hot-reload
]

[project.entry-points."webcrawler.adapters"]
# Built-in site adapters
facebook = "src.plugins.facebook.adapter:FacebookAdapter"
twitter = "src.plugins.twitter.adapter:TwitterAdapter"
linkedin = "src.plugins.linkedin.adapter:LinkedInAdapter"
generic = "src.plugins.generic.adapter:GenericAdapter"

[project.entry-points."webcrawler.middlewares"]
# Middleware components
rate_limit = "src.middlewares.rate_limit:RateLimitMiddleware"
anti_bot = "src.middlewares.anti_bot:AntiBotMiddleware"
cache = "src.middlewares.cache:CacheMiddleware"

[project.scripts]
# CLI commands
webcrawler = "src.main:cli"
webcrawler-login = "src.main:login_command"
```

---

## 12. Implementation Checklist

### Phase 1: Core Architecture (Week 1-2)
- [ ] Define `SiteAdapter` protocol in `src/core/protocols.py`
- [ ] Implement `PluginLoader` with entry points + directory scanning
- [ ] Create `ToolRegistry` for LangChain tools
- [ ] Set up `pydantic-settings` configuration
- [ ] Add unit tests for plugin loading

### Phase 2: Facebook Migration (Week 3)
- [ ] Create `FacebookAdapter` class implementing `SiteAdapter`
- [ ] Move existing FB logic to adapter methods
- [ ] Register FB tools in `get_tools()`
- [ ] Update `FacebookSurferAgent` to use adapter
- [ ] Add integration tests

### Phase 3: Multi-Site Agent (Week 4)
- [ ] Implement `MultiSiteCrawlerAgent`
- [ ] Add LangGraph workflow nodes
- [ ] Implement site detection and switching
- [ ] Add Skills middleware for multiple sites
- [ ] Test multi-site workflows

### Phase 4: Additional Plugins (Week 5+)
- [ ] Create `TwitterAdapter`
- [ ] Create `GenericAdapter` (fallback)
- [ ] Add plugin development documentation
- [ ] Create plugin template
- [ ] Add CLI for plugin management

---

## 13. Key Differences from 2024 Research

| Area | 2024 Approach | 2025 Recommendation |
|------|---------------|---------------------|
| Config | Pydantic V1 + YAML | Pydantic V2 + `pydantic-settings` |
| Async concurrency | `asyncio.gather()` | `asyncio.TaskGroup` (Python 3.11+) |
| Type hints | Standard Protocol | Protocol + `Self` type (PEP 673) |
| Hot reload | `importlib.reload()` | Process restart (more reliable) |
| Entry points | Setup tools | `pyproject.toml` (PEP 621) |
| Validation | Manual checks | `pydantic-settings` multi-source |
| Isolation | Basic try/except | Process-level isolation for untrusted |

---

## 14. References (Updated)

### Official Documentation
- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [PEP 621 - pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 673 - Self Type](https://peps.python.org/pep-0673/)
- [importlib.metadata](https://docs.python.org/3/library/importlib.metadata.html)
- [Python 3.11 asyncio.TaskGroup](https://docs.python.org/3/library/asyncio.html#asyncio.TaskGroup)
- [Pydantic V2 Docs](https://docs.pydantic.dev/latest/)
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

### Articles & Resources
- [Modern Python Plugin Systems (2025)](https://medium.com/@avantika0/build-a-pluggable-architecture-in-python-2025)
- [Python Plugin System - Blue Book](https://lyz-code.github.io/blue-book/python_plugin_system/)
- [LangChain Tools Guide](https://python.langchain.com/docs/modules/tools/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Playwright for Python](https://playwright.dev/python/)

### Related Projects
- [pytest plugin system](https://docs.pytest.org/en/stable/how-to/plugins.html)
- [Scrapy middleware](https://docs.scrapy.org/en/latest/topics/architecture.html)
- [Pluggy](https://pluggy.readthedocs.io/)

---

## 15. Unresolved Questions

1. **State persistence**: How to handle browser context persistence across plugin reloads?
2. **Tool name collisions**: What if two plugins register tools with the same name?
3. **Cross-plugin dependencies**: Should plugins depend on other plugins? How to resolve?
4. **Error recovery**: How to recover from plugin failures mid-crawl?
5. **Metrics/observability**: Standardized metrics format for plugins?

---

## Raw Gemini Research

<details>
<summary>Full Gemini CLI output (2025-01-19)</summary>

The Gemini research provided comprehensive insights on:
- Protocol vs ABC tradeoffs with modern type hints
- Python 3.11+ features (TaskGroup, Self type)
- Pydantic V2 and pydantic-settings
- Updated entry points API
- Async lifecycle patterns
- LangChain/LangGraph integration
- Security and isolation strategies
- Performance optimization techniques
- Version compatibility strategies

Full response captured in consultation with gemini-2.5-flash model.

</details>
