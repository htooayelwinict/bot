# Existing Code Analysis

**Date:** 2025-01-19
**Analyzed:** src/agents/facebook_surfer.py, src/session/__init__.py, src/tools/registry.py

## Current Architecture

### Component Overview

```
┌─────────────────────────────────────────────┐
│         FacebookSurferAgent                 │
│  - DeepAgent wrapper                        │
│  - System prompt with FB-specific logic     │
│  - Skills middleware (facebook-automation/) │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         ToolRegistry (22 tools)             │
│  - Navigation (4 tools)                     │
│  - Interaction (5 tools)                    │
│  - Forms (3 tools)                          │
│  - Utilities (5 tools)                      │
│  - Browser (5 tools)                        │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│      FacebookSessionManager                 │
│  - Persistent browser contexts              │
│  - HITL login (3-minute timeout)            │
│  - Cookie/storage state persistence         │
└─────────────────────────────────────────────┘
```

### Key Files

#### 1. src/agents/facebook_surfer.py (313 lines)
**Purpose:** DeepAgent wrapper for Facebook automation

**Key Components:**
- `FacebookSurferAgent.__init__()` - Registers tools, creates agent
- `_build_system_prompt()` - Long FB-specific system prompt (160 lines)
- `_create_agent()` - Configures DeepAgent with skills middleware
- `invoke()`, `stream()`, `stream_events()` - Execution methods

**Dependencies:**
- deepagents (create_deep_agent)
- langgraph (MemorySaver, InMemoryStore)
- src.tools.registry (ToolRegistry)

**Tight Coupling Issues:**
- System prompt hardcodes Facebook-specific workflows
- Skills path hardcoded to `/facebook-automation/`
- No abstraction for other sites

#### 2. src/session/__init__.py (724 lines)
**Purpose:** Facebook session management with persistent profiles

**Key Components:**
- `FacebookSessionManager` - Main session manager class
- Sync and async APIs for all methods
- HITL login with 3-minute timeout
- Cookie/storage state persistence
- Login status detection via selectors

**Facebook-Specific Elements:**
```python
DEFAULT_PROFILE_DIR = Path("./profiles/facebook")
LOGIN_SELECTORS = [...Facebook-specific selectors...]
LOGGED_IN_SELECTORS = [...Facebook-specific selectors...]
```

**Good Practices to Preserve:**
- Dual sync/async API
- Persistent browser contexts
- Selector-based login detection
- SingletonLock cleanup

#### 3. src/tools/registry.py (457 lines)
**Purpose:** Centralized tool registration for LangChain

**Key Components:**
- `ToolCategory` enum - Categories for tools
- `ToolSpec` dataclass - Tool specification
- `ToolRegistry` class - Registry with get/register methods
- `register_all_tools()` - Registers 22 tools

**Tool Categories:**
1. navigation (4 tools)
2. interaction (5 tools)
3. forms (3 tools)
4. utilities (5 tools)
5. browser (5 tools)

**Strengths:**
- Clean separation of concerns
- LangChain StructuredTool integration
- Category-based organization
- Async function handling

**Extension Points:**
- Add site-specific tools to registry
- Filter tools by category
- Get tools for specific site

## Refactoring Strategy

### Phase 1: Extract Core (Non-Breaking)

**Create new modules without modifying existing code:**

1. **src/core/protocols.py** (NEW)
   - Define SiteAdapter Protocol
   - Define CrawlConfig, AuthResult models
   - No changes to existing code

2. **src/core/plugin_loader.py** (NEW)
   - Implement PluginLoader class
   - Entry points + directory scanning
   - No changes to existing code

3. **src/core/config/settings.py** (NEW)
   - pydantic-settings configuration
   - No changes to existing code

### Phase 2: Migrate Facebook (Additive)

**Create FacebookAdapter alongside existing code:**

1. **src/plugins/facebook/adapter.py** (NEW)
   - Extract FB-specific logic from FacebookSurferAgent
   - Implement SiteAdapter protocol
   - Keep FacebookSurferAgent unchanged

2. **src/plugins/facebook/config.py** (NEW)
   - FB-specific configuration schema
   - Migrate constants from session module

3. **src/session/base.py** (NEW - optional)
   - Extract generic session logic
   - Keep FacebookSessionManager for backward compatibility

### Phase 3: Create Multi-Site Agent (Additive)

**New agent without replacing existing:**

1. **src/agents/multi_site_agent.py** (NEW)
   - Use PluginLoader to discover adapters
   - Support multiple sites
   - Keep FacebookSurferAgent for backward compatibility

2. **Update CLI** (MODIFY - additive)
   - Add `--site` flag to specify target
   - Default to Facebook if not specified
   - Route to appropriate agent

### Phase 4: Deprecate Old (Future)

**Only after multi-site agent proven:**

1. Add deprecation warnings to FacebookSurferAgent
2. Document migration path
3. Remove in future major version

## Code Quality Observations

### Strengths
1. **Clean tool registry** - Well-organized, extensible
2. **Dual sync/async APIs** - Supports both use cases
3. **Persistent sessions** - Good UX for manual login
4. **Skills middleware** - Domain guidance separation
5. **Type hints** - Good type coverage

### Areas for Improvement
1. **Monolithic system prompt** - 160 lines of FB-specific logic
2. **Hardcoded paths** - Skills directory, profile path
3. **No site abstraction** - All logic in one agent
4. **Global session** - Uses _global_session singleton
5. **Limited configurability** - Many hardcoded values

## Migration Complexity Assessment

### Low Complexity (Keep as-is)
- Browser tools (src/tools/)
- Tool registry (src/tools/registry.py)
- LangGraph integration patterns
- DeepAgents framework usage

### Medium Complexity (Extract & Abstract)
- Facebook selectors → adapter.get_selectors()
- Authentication flow → adapter.login()
- System prompt → agent._build_system_prompt()
- Session logic → Generic base class

### High Complexity (Requires Care)
- Global session management → Adapter lifecycle
- HITL login → Adapter-specific login
- Skills middleware → Multi-site skills
- CLI commands → Support both agents

## Dependencies Analysis

### Current Dependencies
```python
# Core
playwright>=1.40.0
langchain>=0.1.0
langgraph>=0.0.20
deepagents  # Custom framework

# Existing
pydantic (version unspecified - check pyproject.toml)
```

### New Dependencies Required
```python
pydantic>=2.0.0  # Upgrade if needed
pydantic-settings>=2.0.0  # NEW
```

### No Additional Heavy Dependencies
- No new frameworks needed
- Use stdlib (importlib, asyncio)
- Minimal overhead

## Testing Considerations

### Existing Test Coverage
- Check for existing tests in tests/
- Identify what's covered
- Ensure refactoring doesn't break tests

### Test Strategy for Refactoring
1. **Characterization tests** - Document current behavior
2. **Integration tests** - Test plugin loading
3. **Mock adapters** - Test without real sites
4. **Contract tests** - Verify Protocol compliance

## Performance Implications

### Current Performance
- Single agent = single initialization
- All tools loaded at startup
- One browser context

### Expected Performance with Plugins
- Plugin loading adds < 1 second
- Lazy loading can defer adapter creation
- Multiple browser contexts (one per site)
- Overall: Minimal overhead if well-implemented

### Optimization Opportunities
1. Lazy plugin loading
2. Shared browser contexts (if safe)
3. Caching of adapter instances
4. Plugin unloading for memory management

## Backward Compatibility Plan

### Keep Working
1. FacebookSurferAgent class
2. CLI commands (`login`, `run`)
3. Configuration format
4. Session persistence
5. Skills directory structure

### Add New
1. MultiSiteAgent class
2. New CLI flags (`--site`, `--adapter`)
3. Plugin configuration
4. Adapter classes

### Deprecate Later
1. Direct FacebookSurferAgent usage
2. Hardcoded system prompt
3. Global session singleton
4. Monolithic agent structure

## Risk Mitigation

### Risk: Breaking existing functionality
**Mitigation:**
- Keep FacebookSurferAgent untouched initially
- Create parallel MultiSiteAgent
- Run both agents in tests
- Gradual migration path

### Risk: Performance regression
**Mitigation:**
- Profile before and after
- Benchmark plugin loading
- Lazy loading where appropriate
- Optimization phase in plan

### Risk: Complex async lifecycle
**Mitigation:**
- Use Python 3.11+ TaskGroup
- Timeout handling
- Error isolation
- Comprehensive testing

### Risk: Configuration errors
**Mitigation:**
- Pydantic validation
- Clear error messages
- Configuration examples
- Schema documentation

## Files to Modify

### Modify (Additive changes)
1. `pyproject.toml` - Add entry points
2. `src/main.py` - Add CLI flags for multi-site
3. `src/agents/__init__.py` - Export MultiSiteAgent

### Keep Unchanged
1. `src/tools/*` - All browser tools
2. `src/tools/registry.py` - Tool registry (maybe extend)
3. `src/agents/facebook_surfer.py` - Keep for compatibility
4. `src/session/__init__.py` - Keep for compatibility

### Create New
1. `src/core/*.py` - Plugin architecture
2. `src/plugins/*/adapter.py` - Site adapters
3. `src/agents/multi_site_agent.py` - Multi-site agent
4. `tests/test_*.py` - New tests
5. `docs/*.md` - Documentation
