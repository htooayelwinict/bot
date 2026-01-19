# Phase 3: Multi-Site Agent

**Duration:** 2-3 days
**Status:** Pending
**Dependencies:** Phase 1, Phase 2 complete

## Objective

Create the MultiSiteAgent that uses the plugin architecture to support multiple websites. This agent will be the primary interface for multi-site automation while keeping FacebookSurferAgent available for backward compatibility.

## Prerequisites

- Phase 1 complete (core architecture)
- Phase 2 complete (Facebook adapter working)
- PluginLoader functional
- Configuration system ready

## Tasks

### 3.1 Create Tool Registry Extension

**File:** `src/core/tool_registry.py`
**Effort:** 2-3 hours

**Implementation Steps:**

1. **Extend existing ToolRegistry:**
   ```python
   from src.tools.registry import ToolRegistry as BaseRegistry

   class ToolRegistry(BaseRegistry):
       """Extended registry with site-specific tool support."""

       def __init__(self):
           super().__init__()
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
           if site in self._by_site:
               tools.extend(self._by_site[site])
           return tools
   ```

**Acceptance Criteria:**
- [ ] ToolRegistry extends existing registry
- [ ] register_universal() works
- [ ] register_for_site() works
- [ ] get_tools_for_site() returns universal + site-specific
- [ ] Backward compatible with existing code

**Verification:**
```bash
python -c "
from src.core.tool_registry import ToolRegistry
from langchain_core.tools import StructuredTool

registry = ToolRegistry()
tool = StructuredTool(name='test', func=lambda: 'ok', description='test')
registry.register_universal(tool)
print('✓ Tool registry extension works')
"
```

---

### 3.2 Create MultiSiteAgent Class

**File:** `src/agents/multi_site_agent.py`
**Effort:** 4-5 hours

**Implementation Steps:**

#### Step 1: Basic Structure
```python
from typing import Any
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware

from src.core.plugin_loader import PluginLoader
from src.core.lifecycle import AsyncLifecycleManager
from src.core.tool_registry import ToolRegistry
from src.core.protocols import SiteAdapter

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
```

#### Step 2: Configuration Loading
```python
def _load_enabled_sites(self, config_path: str) -> dict:
    """Load enabled site configurations."""
    # For now, enable all discovered plugins
    # TODO: Load from YAML file
    return {name: True for name in self.plugin_loader.list_all()}

def _create_adapters(self) -> dict[str, SiteAdapter]:
    """Create adapter instances."""
    adapters = {}
    for site_name in self.enabled_sites:
        try:
            adapter = self.plugin_loader.create(site_name)
            adapters[site_name] = adapter
            print(f"✓ Loaded adapter: {site_name}")
        except Exception as e:
            print(f"✗ Failed to load {site_name}: {e}")
    return adapters
```

#### Step 3: Tool Registration
```python
def _register_tools(self) -> None:
    """Register all tools from adapters and universal tools."""
    # Register universal tools (existing 22 tools)
    from src.tools.registry import register_all_tools
    universal_registry = register_all_tools()
    for tool in universal_registry.get_all():
        self.tool_registry.register_universal(tool)

    # Register site-specific tools from each adapter
    for site_name, adapter in self.adapters.items():
        for tool in adapter.get_tools():
            self.tool_registry.register_for_site(site_name, tool)
```

#### Step 4: Agent Creation
```python
def _create_agent(self):
    """Create the DeepAgent instance."""
    from langchain_openai import ChatOpenAI

    # Build system prompt
    system_prompt = self._build_system_prompt()

    # Configure OpenRouter if needed
    model_config = None
    model_name = self.model

    if self.model.startswith("openrouter/"):
        model_name = self.model.replace("openrouter/", "")
        model_config = ChatOpenAI(
            model=model_name,
            temperature=0.0,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    # Skills middleware
    skills_backend = FilesystemBackend(root_dir="skills")
    skills_middleware = SkillsMiddleware(
        backend=skills_backend,
        sources=[f"/{name}-automation/" for name in self.adapters.keys()],
    )

    return create_deep_agent(
        model=model_config if model_config else model_name,
        tools=self.tool_registry.get_all_tools(),
        system_prompt=system_prompt,
        middleware=[skills_middleware],
    )
```

#### Step 5: System Prompt
```python
def _build_system_prompt(self) -> str:
    """Build system prompt with site context."""
    sites_list = ", ".join(self.adapters.keys())

    return f"""You are a multi-site web automation agent.

**Supported Sites:** {sites_list}

## Core Workflow
1. Detect target site from task description
2. Use site-specific tools and selectors
3. Get snapshot before acting
4. Verify actions with new snapshot

## Critical Rules
- Always use fresh refs after each action
- Use site-specific selectors from get_tools()
- Follow site authentication flows
- Detect site automatically from task

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
- Selectors: {len(adapter.get_selectors())} defined
""")
    return "\n".join(notes)
```

#### Step 6: Site Detection
```python
def _detect_site_from_task(self, task: str) -> str | None:
    """Detect which site to use from task description."""
    task_lower = task.lower()

    for name, adapter in self.adapters.items():
        if adapter.site_name.lower() in task_lower:
            return name
        if adapter.site_domain in task_lower:
            return name

    return None  # Let agent decide
```

#### Step 7: Lifecycle Methods
```python
async def start(self) -> None:
    """Initialize all adapters."""
    configs = {
        name: adapter.get_default_config()
        for name, adapter in self.adapters.items()
    }
    await self.lifecycle.initialize_all(self.adapters, configs)

async def stop(self) -> None:
    """Shutdown all adapters."""
    await self.lifecycle.shutdown_all()
```

#### Step 8: Execution Methods
```python
async def run(self, task: str, thread_id: str = "default") -> dict:
    """Execute a task."""
    config = {"configurable": {"thread_id": thread_id}}
    result = await self.agent.ainvoke(
        {"messages": [{"role": "user", "content": task}]},
        config=config,
    )
    return result

async def stream(self, task: str, thread_id: str = "default"):
    """Stream agent execution."""
    config = {"configurable": {"thread_id": thread_id}}
    async for event in self.agent.astream(
        {"messages": [{"role": "user", "content": task}]},
        config=config,
        stream_mode="values",
    ):
        yield event
```

**Acceptance Criteria:**
- [ ] MultiSiteAgent class created
- [ ] Loads plugins via PluginLoader
- [ ] Creates adapters successfully
- [ ] Registers universal and site-specific tools
- [ ] Creates DeepAgent successfully
- [ ] System prompt includes site context
- [ ] Detects site from task
- [ ] Lifecycle methods work

**Verification:**
```bash
mypy src/agents/multi_site_agent.py
python -c "
from src.agents.multi_site_agent import MultiSiteAgent
agent = MultiSiteAgent()
print(f'Adapters: {list(agent.adapters.keys())}')
print(f'Tools: {agent.tool_registry.count()}')
"
```

---

### 3.3 Update CLI

**File:** `src/main.py`
**Effort:** 2 hours

**Implementation Steps:**

1. **Add site selection:**
   ```python
   @app.command()
   def run(
       task: str = typer.Argument(None),
       site: str = typer.Option("auto", help="Site to automate (auto, facebook, twitter, etc.)"),
       stream: bool = typer.Option(False, "--stream"),
       debug: bool = typer.Option(False, "--debug"),
       thread: str = typer.Option("default", "--thread"),
       model: str = typer.Option("openrouter/mistralai/devstral-2512:free", "--model"),
   ):
       """Run automation task."""
       if site == "facebook" and not MULTI_SITE_ENABLED:
           # Use existing FacebookSurferAgent for backward compatibility
           agent = FacebookSurferAgent(model=model)
       else:
           # Use MultiSiteAgent
           agent = MultiSiteAgent(model=model)
           asyncio.run(agent.start())

       # Execute task
       if task:
           result = asyncio.run(agent.run(task, thread_id=thread))
           print(result)

       # Cleanup
       if hasattr(agent, 'stop'):
           asyncio.run(agent.stop())
   ```

2. **Add list-sites command:**
   ```python
   @app.command()
   def list_sites():
       """List available site adapters."""
       from src.core.plugin_loader import PluginLoader

       loader = PluginLoader()
       sites = loader.list_all()

       print("Available site adapters:")
       for site in sites:
           print(f"  - {site}")
   ```

**Acceptance Criteria:**
- [ ] --site flag added
- [ ] Default behavior maintains backward compatibility
- [ ] MultiSiteAgent used when site specified
- [ ] FacebookSurferAgent used for site=facebook
- [ ] list-sites command works
- [ ] Help text updated

**Verification:**
```bash
python -m facebook-surfer run --help
python -m facebook-surfer list-sites
python -m facebook-surfer run "test" --site facebook
```

---

### 3.4 Create Configuration File

**File:** `config/sites.yaml`
**Effort:** 1 hour

**Implementation Steps:**

1. **Create YAML config:**
   ```yaml
   # Site-specific plugin configurations
   facebook:
     enabled: true
     base_url: "https://www.facebook.com"
     timeout: 30000
     headless: false
     login_timeout: 180
     manual_login: true

   twitter:
     enabled: false  # Not implemented yet
     base_url: "https://twitter.com"
     timeout: 30000
     headless: true

   generic:
     enabled: true
     base_url: "https://example.com"
     timeout: 30000
     headless: true
   ```

2. **Create config loader (optional):**
   ```python
   # src/core/config/loader.py
   import yaml
   from pathlib import Path

   def load_site_config(config_path: str = "config/sites.yaml") -> dict:
       """Load site configurations from YAML."""
       path = Path(config_path)
       if not path.exists():
           return {}

       with open(path) as f:
           return yaml.safe_load(f)
   ```

**Acceptance Criteria:**
- [ ] sites.yaml created
- [ ] YAML format valid
- [ ] Contains all supported sites
- [ ] Configuration documented

**Verification:**
```bash
python -c "
import yaml
from pathlib import Path
config = yaml.safe_load(Path('config/sites.yaml'))
print('Sites:', list(config.keys()))
"
```

---

### 3.5 Create Integration Tests

**File:** `tests/test_multi_site_agent.py`
**Effort:** 3-4 hours

**Implementation Steps:**

1. **Test agent initialization:**
   ```python
   @pytest.mark.asyncio
   async def test_multi_site_agent_init():
       """Test MultiSiteAgent initialization."""
       agent = MultiSiteAgent()

       # Should have adapters
       assert len(agent.adapters) > 0
       assert "facebook" in agent.adapters

       # Should have tools
       assert agent.tool_registry.count() > 0
   ```

2. **Test site detection:**
   ```python
   def test_site_detection():
       """Test automatic site detection."""
       agent = MultiSiteAgent()

       # Test Facebook detection
       site = agent._detect_site_from_task("Post to Facebook")
       assert site == "facebook"
   ```

3. **Test tool registration:**
   ```python
   def test_tool_registration():
       """Test tool registration."""
       agent = MultiSiteAgent()

       # Should have universal tools
       universal_tools = agent.tool_registry._universal
       assert len(universal_tools) > 0

       # Should have site-specific tools
       fb_tools = agent.tool_registry._by_site.get("facebook", [])
       # May be empty initially, will grow
       assert isinstance(fb_tools, list)
   ```

4. **Test adapter creation:**
   ```python
   def test_adapter_creation():
       """Test adapter creation."""
       agent = MultiSiteAgent()

       # Facebook adapter should exist
       assert "facebook" in agent.adapters
       fb_adapter = agent.adapters["facebook"]

       # Should have correct properties
       assert fb_adapter.site_name == "Facebook"
       assert fb_adapter.site_domain == "facebook.com"
   ```

5. **Test system prompt:**
   ```python
   def test_system_prompt():
       """Test system prompt generation."""
       agent = MultiSiteAgent()
       prompt = agent._build_system_prompt()

       # Should mention supported sites
       assert "facebook" in prompt.lower()

       # Should have workflow instructions
       assert "workflow" in prompt.lower()
   ```

**Acceptance Criteria:**
- [ ] Integration tests created
- [ ] Agent initialization tested
- [ ] Site detection tested
- [ ] Tool registration tested
- [ ] System prompt tested
- [ ] Coverage >70%

**Verification:**
```bash
pytest tests/test_multi_site_agent.py -v
pytest tests/test_multi_site_agent.py --cov=src/agents/multi_site_agent --cov-report=term-missing
```

---

### 3.6 End-to-End Test

**File:** `tests/test_e2e_multi_site.py`
**Effort:** 2 hours

**Implementation Steps:**

1. **Create simple E2E test:**
   ```python
   @pytest.mark.asyncio
   async def test_facebook_through_multi_site():
       """Test Facebook automation through MultiSiteAgent."""
       agent = MultiSiteAgent()
       await agent.start()

       try:
           # Run simple task
           result = await agent.run("Navigate to Facebook", thread_id="test")

           # Should complete without error
           assert result is not None
       finally:
           await agent.stop()
   ```

**Acceptance Criteria:**
- [ ] E2E test created
- [ ] Tests real workflow
- [ ] Cleanup handles errors

**Verification:**
```bash
pytest tests/test_e2e_multi_site.py -v -s
```

---

## Deliverables

### Code
- [ ] `src/core/tool_registry.py` - Extended tool registry
- [ ] `src/agents/multi_site_agent.py` - Multi-site agent
- [ ] Updated `src/main.py` - CLI with site selection
- [ ] `config/sites.yaml` - Site configurations

### Tests
- [ ] `tests/test_multi_site_agent.py` - Integration tests
- [ ] `tests/test_e2e_multi_site.py` - E2E tests

### Documentation
- [ ] Docstrings in MultiSiteAgent
- [ ] CLI help text updated
- [ ] Configuration documented

## Verification Steps

### 1. Import Test
```bash
python -c "from src.agents.multi_site_agent import MultiSiteAgent; print('✓ MultiSiteAgent imports')"
```
**Expected:** No errors

### 2. Type Check
```bash
mypy src/agents/multi_site_agent.py
```
**Expected:** No errors

### 3. Agent Creation
```bash
python -c "
from src.agents.multi_site_agent import MultiSiteAgent
agent = MultiSiteAgent()
print(f'Adapters: {list(agent.adapters.keys())}')
print(f'Tools: {agent.tool_registry.count()}')
print(f'System prompt length: {len(agent._build_system_prompt())}')
"
```
**Expected:** Adapters include facebook, tools > 0, prompt has content

### 4. CLI Test
```bash
python -m facebook-surfer list-sites
```
**Expected:** Lists available sites

### 5. Integration Tests
```bash
pytest tests/test_multi_site_agent.py -v
```
**Expected:** All tests pass

### 6. Backward Compatibility
```bash
python -c "from src.agents.facebook_surfer import FacebookSurferAgent; agent = FacebookSurferAgent(); print(f'✓ FacebookSurferAgent still works: {agent.tool_count} tools')"
```
**Expected:** FacebookSurferAgent works unchanged

## Success Criteria

### Must Have
- ✅ MultiSiteAgent creates successfully
- ✅ Loads adapters via PluginLoader
- ✅ Registers universal and site-specific tools
- ✅ Creates DeepAgent with correct tools
- ✅ Site detection works
- ✅ CLI supports --site flag
- ✅ Backward compatibility maintained
- ✅ Integration tests pass

### Should Have
- ✅ Configuration file support
- ✅ Site-specific skills loading
- ✅ Lifecycle management works
- ✅ E2E tests pass

### Could Have
- ✅ Performance optimizations
- ✅ Additional CLI features
- ✅ More configuration options

## Rollback Plan

If this phase fails:
1. Keep MultiSiteAgent code but don't use in CLI
2. Investigate issues with integration
3. Simplify agent implementation
4. Reduce scope (e.g., skip site detection)
5. Retry with smaller feature set

## Notes

### Key Design Decisions
1. **Parallel agents** - MultiSiteAgent alongside FacebookSurferAgent
2. **Auto site detection** - Agent figures out which site from task
3. **Lazy evaluation** - Adapters created when needed
4. **Shared tools** - Universal tools + site-specific tools

### Architecture Benefits
1. **Extensibility** - Easy to add new sites
2. **Type safety** - Protocol ensures compliance
3. **Testability** - Each component testable
4. **Flexibility** - Can use single or multiple sites

### Next Phase
After this phase completes, proceed to **Phase 4: Additional Adapters** where we'll add Twitter and Generic adapters to demonstrate extensibility.
