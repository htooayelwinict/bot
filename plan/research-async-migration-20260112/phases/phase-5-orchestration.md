# Phase 5: Registry, Agent, CLI, and Tests

**Status:** Complete
**Depends:** Phases 1-4 (All tools converted)
**Completed:** 2025-01-12

## Overview

Update orchestration layer to use async tools. This is the final phase that ties everything together.

## Tasks

### 1. Update `src/tools/registry.py`

**File:** `src/tools/registry.py`

**Changes:**
1. Update `ToolSpec.to_langchain_tool()` to use `StructuredTool.from_async()` for async functions
2. Import async tools (they should already be async from previous phases)

**Before:**
```python
from langchain.tools import StructuredTool

@dataclass(frozen=True)
class ToolSpec:
    func: Callable[..., str]

    def to_langchain_tool(self) -> StructuredTool:
        return StructuredTool.from_function(
            func=self.func,
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
        )
```

**After:**
```python
from langchain.tools import StructuredTool
import inspect

@dataclass(frozen=True)
class ToolSpec:
    func: Callable[..., str]

    def to_langchain_tool(self) -> StructuredTool:
        # Use from_async for async functions
        if inspect.iscoroutinefunction(self.func):
            return StructuredTool.from_async(
                coroutine=self.func,
                name=self.name,
                description=self.description,
                args_schema=self.args_schema,
            )
        else:
            return StructuredTool.from_function(
                func=self.func,
                name=self.name,
                description=self.description,
                args_schema=self.args_schema,
            )
```

### 2. Update `src/agents/facebook_surfer.py`

**File:** `src/agents/facebook_surfer.py`

**Changes:**
1. Convert `invoke()` to `async def`
2. Convert `stream()` to `async def`
3. Convert `get_state()` to `async def`
4. Convert `update_state()` to `async def`
5. Use `await agent.ainvoke()` instead of `agent.invoke()`

**Before:**
```python
class FacebookSurferAgent:
    def invoke(self, task: str, thread_id: str = "default") -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return result
```

**After:**
```python
class FacebookSurferAgent:
    async def invoke(self, task: str, thread_id: str = "default") -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return result
```

### 3. Update `src/main.py`

**File:** `src/main.py`

**Changes:**
1. Convert `init_session()` to async context manager
2. Convert `run_single_task()` to `async def`
3. Convert `run_interactive()` to `async def`
4. Update Click commands to use `asyncio.run()`

**Before:**
```python
from playwright.sync_api import sync_playwright

@contextmanager
def init_session(login: bool = False, profile: str = "./profiles/facebook"):
    session = FacebookSessionManager(profile_dir=Path(profile))
    with sync_playwright() as p:
        # ...
        yield session

@cli.command()
def run(task: str | None, ...):
    with init_session(login=False) as session:
        agent = FacebookSurferAgent(model=model)
        if task:
            run_single_task(agent, task, ...)
```

**After:**
```python
from playwright.async_api import async_playwright
import asyncio

@contextmanager
def init_session(login: bool = False, profile: str = "./profiles/facebook"):
    # This stays sync for Click compatibility
    # But we need async version for actual use
    pass

async def async_init_session(login: bool = False, profile: str = "./profiles/facebook"):
    session = FacebookSessionManager(profile_dir=Path(profile))
    async with async_playwright() as p:
        # ...
        yield session

@cli.command()
def run(task: str | None, ...):
    async def _run():
        async with async_init_session(login=False) as session:
            agent = FacebookSurferAgent(model=model)
            if task:
                await run_single_task(agent, task, ...)
    asyncio.run(_run())
```

### 4. Update `src/tools/__init__.py`

**File:** `src/tools/__init__.py`

**Changes:** Update exports to include `async_session_tool` if needed.

### 5. Update `tests/test_facebook_surfer.py`

**File:** `tests/test_facebook_surfer.py`

**Changes:**
1. Add `@pytest.mark.asyncio` to async tests
2. Use `pytest-asyncio` for async test support
3. Update mock functions to be async where needed

**Before:**
```python
def test_agent_creation(monkeypatch):
    agent = FacebookSurferAgent(model="gpt-4o")
    assert agent.tool_count == 22
```

**After:**
```python
@pytest.mark.asyncio
async def test_agent_creation(monkeypatch):
    agent = FacebookSurferAgent(model="gpt-4o")
    assert agent.tool_count == 22
```

### 6. Add pytest-asyncio to dependencies

**File:** `pyproject.toml` or `requirements.txt`

Add:
```
pytest-asyncio>=0.23.0
```

Create/update `pytest.ini` or `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Verification

```bash
# Registry test
python -c "from src.tools.registry import register_all_tools; r = register_all_tools(); print(f'Registered {r.count()} tools')"

# Agent test (with mock)
python -c "
from src.agents.facebook_surfer import FacebookSurferAgent
import inspect
print('Agent methods async:', inspect.iscoroutinefunction(FacebookSurferAgent.invoke))
"

# Import test
python -c "from src.main import cli; print('CLI imports OK')"

# Run tests
python -m pytest tests/test_facebook_surfer.py -v
```

## Integration Test

```bash
# Full smoke test (requires OpenAI API key)
python -m src.main run --help
python -m src.main run --no-banner "Navigate to google.com"
```

## Acceptance Criteria

- [ ] `src/tools/registry.py` uses `from_async()` for async functions
- [ ] `src/agents/facebook_surfer.py` has all async methods
- [ ] `src/main.py` has async execution path
- [ ] `tests/test_facebook_surfer.py` uses `@pytest.mark.asyncio`
- [ ] `pytest-asyncio` added to dependencies
- [ ] All tests pass
- [ ] Agent can be instantiated
- [ ] CLI help works
