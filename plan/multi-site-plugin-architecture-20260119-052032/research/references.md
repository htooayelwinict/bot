# References and Best Practices

**Date:** 2025-01-19
**Sources:** Python documentation, research files, external articles

## Python Documentation

### PEP 544 - Protocols: Structural Subtyping (Static Duck Typing)
**URL:** https://peps.python.org/pep-0544/
**Relevance:** Core to plugin interface design

**Key Points:**
- Enables structural typing - any class with matching methods compatible
- `@runtime_checkable` decorator enables isinstance() checks
- One-way dependency: Core → Protocol ← Plugin
- Preferable to ABC for flexibility

**Example from Research:**
```python
@runtime_checkable
class SiteAdapter(Protocol):
    @property
    def site_name(self) -> str: ...
    async def login(self, page: Page, ...) -> AuthResult: ...
```

### PEP 621 - Storing Project Metadata in pyproject.toml
**URL:** https://peps.python.org/pep-0621/
**Relevance:** Entry points configuration

**Key Points:**
- Standard for project metadata
- Replaces setup.py
- Defines entry points for plugins

**Example:**
```toml
[project.entry-points."webcrawler.adapters"]
facebook = "src.plugins.facebook:FacebookAdapter"
```

### PEP 673 - Self Type
**URL:** https://peps.python.org/pep-0673/
**Relevance:** Fluent interfaces in adapters

**Example:**
```python
def with_config(self, config: CrawlConfig) -> Self:
    self.config = config
    return self
```

### importlib.metadata - Accessing Package Metadata
**URL:** https://docs.python.org/3/library/importlib.metadata.html
**Relevance:** Plugin discovery from entry points

**Key Points:**
- Python 3.10+ API: `entry_points(group=group)`
- Returns EntryPoint objects with `.load()` method
- Auto-discovers installed packages

### asyncio.TaskGroup (Python 3.11+)
**URL:** https://docs.python.org/3/library/asyncio.html#taskgroups
**Relevance:** Structured concurrency for plugin lifecycle

**Key Points:**
- Safer than asyncio.gather()
- Automatically handles exceptions
- Cancels remaining tasks on error
- Preferred for concurrent initialization

**Example:**
```python
async with asyncio.TaskGroup() as tg:
    for adapter in adapters:
        tg.create_task(adapter.initialize())
```

## Pydantic Documentation

### Pydantic V2
**URL:** https://docs.pydantic.dev/latest/
**Relevance:** Configuration validation

**Key Improvements over V1:**
- 5-50x faster validation
- Better error messages
- Improved type hints

### pydantic-settings
**URL:** https://docs.pydantic.dev/latest/concepts/pydantic_settings/
**Relevance:** Multi-source configuration

**Key Features:**
- Load from env vars, .env files, CLI
- Type validation
- Nested models support

**Example:**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")
    api_key: str
    timeout: int = 30
```

## LangChain Documentation

### Tools
**URL:** https://python.langchain.com/docs/modules/tools/
**Relevance:** Tool registration pattern

**Key Concepts:**
- StructuredTool for typed tools
- Async function support via coroutine parameter
- args_schema for Pydantic validation

### LangGraph
**URL:** https://langchain-ai.github.io/langgraph/
**Relevance:** State management for multi-site agent

**Key Features:**
- StateGraph for workflow definition
- Checkpointer for persistence
- MemorySaver for in-memory state

## Research Sources

### Updated Research Files
1. **plugin-research-updated-2025.md**
   - Comprehensive 2025 plugin patterns
   - Pydantic V2 integration
   - Python 3.11+ features

2. **plugin-architecture-updated.md**
   - Implementation guide with code examples
   - Complete adapter examples
   - Testing strategies

3. **Original Research**
   - plugin-architecture.md
   - plugin-research.md

### External Articles

#### Build a Pluggable Architecture in Python (2025)
**URL:** https://medium.com/@avantika0/build-a-pluggable-architecture-in-python-2025
**Key Takeaways:**
- Entry points for production
- Protocol for type safety
- Graceful error handling
- Version compatibility gates

#### Python Plugin System - Blue Book
**URL:** https://lyz-code.github.io/blue-book/python_plugin_system/
**Key Takeaways:**
- Comprehensive plugin patterns
- Security considerations
- Hot-reloading challenges

## Best Practices from Research

### 1. Interface Design
**✅ DO:**
- Use Protocol for flexibility
- Define clear method signatures
- Document all methods
- Use type hints

**❌ DON'T:**
- Use ABC unless you need inheritance
- Mix interface with implementation
- Create overly complex protocols

### 2. Plugin Discovery
**✅ DO:**
- Support both entry points and directory scanning
- Validate plugins at load time
- Provide clear error messages
- Log all plugin operations

**❌ DON'T:**
- Crash on invalid plugin
- Hardcode plugin paths
- Skip validation

### 3. Configuration
**✅ DO:**
- Use Pydantic for validation
- Support multiple sources (env, file, programmatic)
- Provide sensible defaults
- Document all options

**❌ DON'T:**
- Use raw dicts for config
- Skip validation
- Require manual config editing

### 4. Async Lifecycle
**✅ DO:**
- Use asyncio.TaskGroup for concurrency
- Implement timeout handling
- Clean up resources properly
- Handle asyncio.CancelledError

**❌ DON'T:**
- Use asyncio.gather() for initialization
- Forget to close browser contexts
- Block the event loop

### 5. Error Handling
**✅ DO:**
- Isolate plugin failures
- Log errors with context
- Provide recovery mechanisms
- Return error messages to users

**❌ DON'T:**
- Let one plugin crash everything
- Suppress errors silently
- Return cryptic error messages

### 6. Testing
**✅ DO:**
- Mock external dependencies
- Test plugin loading
- Test Protocol compliance
- Use pytest-asyncio

**❌ DON'T:**
- Test against real sites in unit tests
- Skip edge cases
- Forget error conditions

## Security Considerations

### Plugin Isolation
**Reference:** Research document section 8

**Best Practices:**
1. Process isolation for untrusted plugins
2. Resource limits (CPU, memory)
3. Timeout enforcement
4. Input validation at boundaries

### Credential Handling
**Best Practices:**
1. Never hardcode credentials
2. Use environment variables
3. Validate credential format
4. Clear sensitive data after use

### Rate Limiting
**Best Practices:**
1. Per-site rate limits
2. Respect robots.txt
3. Implement backoff
4. Monitor for abuse

## Performance Optimization

### From Research: Section 10

**Strategies:**
1. **Lazy Loading** - Load plugins when needed
2. **Caching** - Cache immutable data
3. **Async I/O** - Use await for network operations
4. **Resource Reuse** - Share browser contexts safely

**Anti-Patterns:**
❌ Loading all plugins at startup (unless needed)
❌ Synchronous I/O in async functions
❌ Creating new browser for each request
❌ Not caching validation results

## Common Pitfalls

### 1. Import Cycles
**Problem:** Core imports Plugin, Plugin imports Core
**Solution:** Use Protocol - one-way dependency

### 2. Stale References
**Problem:** Caching adapter instances across reloads
**Solution:** Use factory pattern, always create fresh

### 3. Missing Protocol Methods
**Problem:** Adapter missing required methods
**Solution:** Use mypy to catch at type-check time

### 4. Config Validation
**Problem:** Invalid config causes runtime errors
**Solution:** Pydantic validation at load time

### 5. Async Blocking
**Problem:** Blocking calls in async functions
**Solution:** Use asyncio.to_thread for CPU work

## Migration Guides

### pytest Plugin System
**Reference:** https://docs.pytest.org/en/stable/how-to/plugins.html
**Lessons:**
- Entry points work well
- Clear hook names important
- Graceful degradation critical

### Scrapy Middleware
**Reference:** https://docs.scrapy.org/en/latest/topics/architecture.html
**Lessons:**
- Middleware chain pattern powerful
- Order matters
- Process methods standard

## Tool Versions

### Python
- **Minimum:** Python 3.11
- **Recommended:** Python 3.12+
- **Reason:** asyncio.TaskGroup, Self type

### Pydantic
- **Minimum:** Pydantic 2.0.0
- **Recommended:** Latest 2.x
- **Reason:** Performance, pydantic-settings

### Playwright
- **Current:** >=1.40.0
- **No change needed**

### LangChain
- **Current:** >=0.1.0
- **No change needed**

## Code Examples

See `plugin-architecture-updated.md` for complete working examples of:
- Protocol definitions
- Plugin loader implementation
- Adapter implementation
- Configuration with pydantic-settings
- Async lifecycle with TaskGroup
- Tool registry
- Multi-site agent

## Further Reading

### Plugin Architecture
- [Plugin Patterns in Python](https://www.youtube.com/watch?v=MPRfHTqSMnk) - PyCon talk
- [Architecture Patterns with Python](https://www.youtube.com/watch?v=SzMpfORl0Vc) - talk on patterns

### Async Programming
- [asyncio — Asynchronous I/O](https://docs.python.org/3/library/asyncio.html)
- [Python Async Await Crash Course](https://www.youtube.com/watch?v=niDQ0L_h4WY)

### Type Hints
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [Protocols and Structural Subtyping](https://www.youtube.com/watch?v=pCYQt2Lu_DM)
