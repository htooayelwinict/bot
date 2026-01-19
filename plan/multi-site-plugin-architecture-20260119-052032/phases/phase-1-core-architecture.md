# Phase 1: Core Architecture

**Duration:** 3-4 days
**Status:** Pending
**Dependencies:** None

## Objective

Establish the plugin infrastructure foundation without breaking any existing functionality. This phase creates the core abstractions and interfaces that all subsequent phases will build upon.

## Prerequisites

- Python 3.11+ installed
- Existing development environment set up
- Access to research files for reference

## Tasks

### 1.1 Create Protocol Definitions

**File:** `src/core/protocols.py`
**Effort:** 2-3 hours

**Implementation Steps:**
1. Create `src/core/` directory
2. Define `CrawlConfig` Pydantic model
   - base_url: HttpUrl
   - timeout: int (default 30000)
   - headless: bool (default True)
   - user_agent: str | None
   - viewport: dict
3. Define `AuthResult` Pydantic model
   - success: bool
   - message: str
   - session_data: dict | None
4. Define `SiteAdapter` Protocol with @runtime_checkable
   - Properties: site_name, site_domain
   - Methods: get_default_config(), login(), is_logged_in(), etc.
5. Add comprehensive docstrings
6. Add type hints throughout

**Acceptance Criteria:**
- [ ] File created at `src/core/protocols.py`
- [ ] CrawlConfig validates correctly
- [ ] AuthResult validates correctly
- [ ] SiteAdapter protocol defined with all required methods
- [ ] @runtime_checkable decorator applied
- [ ] All methods have type hints
- [ ] Docstrings complete

**Verification:**
```bash
mypy src/core/protocols.py
python -c "from src.core.protocols import SiteAdapter, CrawlConfig; print('✓ Protocols imported')"
```

---

### 1.2 Implement Plugin Loader

**File:** `src/core/plugin_loader.py`
**Effort:** 3-4 hours

**Implementation Steps:**
1. Create `PluginLoader` class with __init__
   - Accept entry_point_group parameter
   - Accept plugins_package parameter
   - Initialize _plugins dict
2. Implement `_load_from_entrypoints()`
   - Use importlib.metadata.entry_points()
   - Load each entry point with error handling
   - Log successful/failed loads
3. Implement `_load_from_directory()`
   - Use pkgutil.iter_modules() to discover plugins
   - Import each plugin module
   - Find adapter classes
   - Handle import errors gracefully
4. Implement `_find_adapter_class()`
   - Scan module for classes ending in "Adapter"
   - Check if class implements SiteAdapter
   - Return first matching class
5. Implement `_is_site_adapter()`
   - Check for required protocol methods
   - Return bool
6. Implement public methods:
   - get(name) -> Type[SiteAdapter] | None
   - create(name, config) -> SiteAdapter
   - list_all() -> list[str]
7. Add comprehensive error handling
8. Add logging for debugging

**Acceptance Criteria:**
- [ ] PluginLoader class created
- [ ] Loads from entry points successfully
- [ ] Loads from directory scanning successfully
- [ ] Returns None for unknown plugins
- [ ] Raises ValueError for create() with unknown name
- [ ] Handles plugin load errors gracefully
- [ ] Logs all operations

**Verification:**
```python
# Test in REPL
from src.core.plugin_loader import PluginLoader
loader = PluginLoader()
plugins = loader.list_all()
print(f"Found {len(plugins)} plugins: {plugins}")

# Should find no plugins initially (will add in Phase 2)
assert isinstance(plugins, list)
```

---

### 1.3 Configuration System

**File:** `src/core/config/settings.py`
**Effort:** 2-3 hours

**Implementation Steps:**
1. Install pydantic-settings:
   ```bash
   pip install pydantic-settings>=2.0.0
   ```
2. Create `ScraperSettings` class extending BaseSettings
   - Add SettingsConfigDict
   - env_prefix="SCRAPER_"
   - env_file=".env"
   - extra="forbid"
3. Define fields:
   - target_domain: HttpUrl
   - max_pages: int (Field with ge=1, le=1000)
   - headless: bool
   - concurrency_limit: int (Field with ge=1, le=20)
   - log_level: Literal["DEBUG", "INFO", "WARNING"]
4. Create `PluginSettings` class
   - Similar setup
   - Fields: enabled, api_key, timeout, debug_mode
5. Create example .env file
6. Add validation tests

**Acceptance Criteria:**
- [ ] pydantic-settings installed
- [ ] ScraperSettings validates correctly
- [ ] PluginSettings validates correctly
- [ ] Loads from environment variables
- [ ] Loads from .env file
- [ ] Raises ValidationError on invalid input
- [ ] Example .env file created

**Verification:**
```bash
cp config/.env.example config/.env
# Edit config/.env with test values
python -c "from src.core.config.settings import ScraperSettings; s = ScraperSettings(); print(s.target_domain)"
```

---

### 1.4 Async Lifecycle Manager

**File:** `src/core/lifecycle.py`
**Effort:** 4-5 hours

**Implementation Steps:**
1. Define `PluginState` enum
   - LOADED, INITIALIZING, READY, RUNNING, STOPPING, STOPPED, ERROR
2. Create `AsyncLifecycleManager` class
   - __init__: Initialize states and contexts dicts
3. Implement `initialize_all()`
   - Create async_playwright instance
   - Use asyncio.TaskGroup for concurrent init
   - Create tasks for each adapter
4. Implement `_initialize_one()`
   - Create browser context
   - Call adapter.setup()
   - Handle errors
   - Update state
5. Implement `shutdown_all()`
   - Use asyncio.TaskGroup for concurrent shutdown
   - Create tasks for each context
6. Implement `_shutdown_one()`
   - Call adapter.teardown()
   - Close browser
   - Update state
7. Add timeout handling
8. Add error isolation
9. Add state tracking

**Acceptance Criteria:**
- [ ] PluginState enum defined
- [ ] AsyncLifecycleManager created
- [ ] initialize_all() uses TaskGroup
- [ ] shutdown_all() uses TaskGroup
- [ ] Browser contexts created correctly
- [ ] Errors isolated per adapter
- [ ] States tracked correctly
- [ ] Resources cleaned up properly

**Verification:**
```bash
pytest tests/test_lifecycle.py -v
# Tests will verify concurrent initialization and error handling
```

---

### 1.5 Update pyproject.toml

**File:** `pyproject.toml`
**Effort:** 30 minutes

**Implementation Steps:**
1. Add pydantic-settings to dependencies:
   ```toml
   dependencies = [
       # ... existing
       "pydantic>=2.0.0",
       "pydantic-settings>=2.0.0",
   ]
   ```
2. Add entry points section:
   ```toml
   [project.entry-points."webcrawler.adapters"]
   facebook = "src.plugins.facebook.adapter:FacebookAdapter"
   twitter = "src.plugins.twitter.adapter:TwitterAdapter"
   generic = "src.plugins.generic.adapter:GenericAdapter"
   ```
3. Update Python version requirement to >=3.11

**Acceptance Criteria:**
- [ ] pydantic-settings added to dependencies
- [ ] Entry points section added
- [ ] Python version >=3.11
- [ ] Package installs successfully

**Verification:**
```bash
pip install -e .
python -c "from importlib.metadata import entry_points; eps = list(entry_points(group='webcrawler.adapters')); print(f'Entry points: {len(eps)}')"
# Should show 3 entry points (adapters not created yet, but entry points defined)
```

---

### 1.6 Create Tests

**Files:**
- `tests/test_protocols.py`
- `tests/test_plugin_loader.py`
- `tests/test_lifecycle.py`
- `tests/test_config.py`

**Effort:** 4-5 hours

**Implementation Steps:**
1. Create `tests/test_protocols.py`
   - Test CrawlConfig validation
   - Test AuthResult validation
   - Test Protocol with mock class
2. Create `tests/test_plugin_loader.py`
   - Test entry points loading
   - Test directory scanning
   - Test create() method
   - Test error handling
3. Create `tests/test_lifecycle.py`
   - Test PluginState enum
   - Test initialize_all() with mocks
   - Test shutdown_all() with mocks
   - Test error isolation
4. Create `tests/test_config.py`
   - Test ScraperSettings validation
   - Test PluginSettings validation
   - Test .env loading
   - Test validation errors
5. Add fixtures for Playwright mocks
6. Achieve >80% coverage

**Acceptance Criteria:**
- [ ] All test files created
- [ ] Tests cover main scenarios
- [ ] Tests cover edge cases
- [ ] Tests cover error paths
- [ ] Coverage >80%
- [ ] All tests pass

**Verification:**
```bash
pytest tests/test_protocols.py tests/test_plugin_loader.py tests/test_lifecycle.py tests/test_config.py -v
pytest tests/ --cov=src/core --cov-report=term-missing
```

---

## Deliverables

### Code
- [ ] `src/core/protocols.py` - Protocol definitions
- [ ] `src/core/plugin_loader.py` - Plugin loader
- [ ] `src/core/config/settings.py` - Configuration models
- [ ] `src/core/lifecycle.py` - Async lifecycle manager
- [ ] `src/core/__init__.py` - Package init
- [ ] `src/core/config/__init__.py` - Config package init

### Configuration
- [ ] Updated `pyproject.toml` - Entry points, dependencies
- [ ] `config/.env.example` - Environment template

### Tests
- [ ] `tests/test_protocols.py`
- [ ] `tests/test_plugin_loader.py`
- [ ] `tests/test_lifecycle.py`
- [ ] `tests/test_config.py`

### Documentation
- [ ] Docstrings in all code
- [ ] Code comments for complex logic

## Verification Steps

### 1. Type Checking
```bash
mypy src/core/
```
**Expected:** No errors

### 2. Linting
```bash
ruff check src/core/ --fix
```
**Expected:** No errors (or auto-fixed)

### 3. Import Test
```bash
python -c "from src.core.protocols import SiteAdapter; from src.core.plugin_loader import PluginLoader; from src.core.config.settings import ScraperSettings; from src.core.lifecycle import AsyncLifecycleManager; print('✓ All imports successful')"
```
**Expected:** No import errors

### 4. Unit Tests
```bash
pytest tests/test_protocols.py tests/test_plugin_loader.py tests/test_lifecycle.py tests/test_config.py -v
```
**Expected:** All tests pass

### 5. Coverage
```bash
pytest tests/ --cov=src/core --cov-report=term-missing
```
**Expected:** >80% coverage

## Success Criteria

### Must Have
- ✅ All type checks pass (mypy)
- ✅ All lint checks pass (ruff)
- ✅ All unit tests pass
- ✅ Test coverage >80%
- ✅ No breaking changes to existing code
- ✅ Documentation complete

### Should Have
- ✅ Performance acceptable (plugin loading <1s)
- ✅ Error handling comprehensive
- ✅ Logging for debugging

### Could Have
- ✅ Benchmarks vs baseline
- ✅ Additional validation rules
- ✅ More test scenarios

## Rollback Plan

If this phase fails:
1. Delete `src/core/` directory
2. Revert `pyproject.toml` changes
3. Investigate failure
4. Adjust approach
5. Retry phase

## Notes

### Key Design Decisions
1. **Protocol over ABC** - Flexibility for third-party developers
2. **Dual loading** - Support both bundled and external plugins
3. **Pydantic V2** - Performance and validation improvements
4. **TaskGroup** - Safer than asyncio.gather()

### Dependencies
- Python 3.11+ required for TaskGroup
- pydantic-settings new dependency
- No other new dependencies

### Next Phase
After this phase completes, proceed to **Phase 2: Facebook Adapter Migration**
