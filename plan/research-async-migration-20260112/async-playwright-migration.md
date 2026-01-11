# Research: Async Playwright Migration for LangChain Tools

**Date:** 2025-01-12
**Query:** Option 1 - Async migration to fix threading issue
**Status:** Complete (All 5 phases implemented)

## Summary

The current codebase uses `playwright.sync_api` which is incompatible with LangChain's multi-threaded tool execution. LangChain executes tools from background threads, but Playwright's sync API uses greenlets that are thread-bound, causing `greenlet.error: Cannot switch to a different thread`. Migrating to `playwright.async_api` is the proper long-term solution.

## Root Cause Analysis

**The Problem:**
```
greenlet.error: Cannot switch to a different thread
```

**Why It Happens:**
- `playwright.sync_api` uses **greenlets** that are bound to the thread that created them
- LangChain/DeepAgents executes tools from **background thread pools**
- When a tool tries to execute Playwright operations, the greenlet detects it's in a different thread and fails

**Why Async Fixes It:**
- `async_playwright()` uses native Python asyncio, not greenlets
- Async coroutines can safely execute across different threads with an event loop
- LangChain supports async tools via `StructuredTool.from_async()`

## Key Concepts

### 1. `sync_playwright()` vs `async_playwright()`

| Aspect | sync_playwright() | async_playwright() |
|--------|------------------|-------------------|
| Thread Model | Greenlets (thread-bound) | Asyncio (event loop) |
| LangChain Compatible | No (thread issues) | Yes (via async tools) |
| Syntax | `page.goto()` | `await page.goto()` |
| Context Manager | `with sync_playwright() as p:` | `async with async_playwright() as p:` |
| Performance | Blocks thread | Non-blocking I/O |

### 2. LangChain Async Tool Integration

**Sync Tool (Current - Broken):**
```python
from langchain.tools import StructuredTool
from pydantic import BaseModel

class NavigateArgs(BaseModel):
    url: str

def navigate_tool(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)  # ← Fails in background thread
        browser.close()
    return "ok"

navigate = StructuredTool.from_function(
    func=navigate_tool,  # ← Sync, breaks with threading
    name="navigate",
    args_schema=NavigateArgs,
)
```

**Async Tool (Target - Works):**
```python
from langchain.tools import StructuredTool
from playwright.async_api import async_playwright

class NavigateArgs(BaseModel):
    url: str

async def navigate_tool(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)  # ← Works with async execution
        await browser.close()
    return "ok"

navigate = StructuredTool.from_async(
    coroutine=navigate_tool,  # ← Async, works with LangChain
    name="navigate",
    args_schema=NavigateArgs,
)
```

## Migration Strategy

### Phase 1: Update Session Management
**File:** `src/session/__init__.py`

**Before (Sync):**
```python
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

def start_login(self) -> bool:
    with sync_playwright() as p:
        self.context, self.page, _ = self._create_new_session(p.chromium)
        # ...
```

**After (Async):**
```python
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

async def start_login(self) -> bool:
    async with async_playwright() as p:
        self.context, self.page, _ = await self._create_new_session(p.chromium)
        # ...
```

### Phase 2: Convert Tool Functions
**Files:** `src/tools/*.py` (22 tools)

**Pattern:**

1. Change function signature:
   ```python
   def browser_navigate(...) -> str:  # Before
   async def browser_navigate(...) -> str:  # After
   ```

2. Add await to Playwright calls:
   ```python
   page.goto(url)  # Before
   await page.goto(url)  # After
   ```

3. Update decorator to handle async:
   ```python
   @session_tool  # Needs async variant
   async def browser_navigate(...) -> str:
   ```

### Phase 3: Update Tool Registry
**File:** `src/tools/registry.py`

**Before:**
```python
def register_all_tools() -> ToolRegistry:
    registry.register(ToolSpec(
        name="browser_navigate",
        func=browser_navigate,  # ← Sync function
        # ...
    ))
```

**After:**
```python
def register_all_tools() -> ToolRegistry:
    registry.register(ToolSpec(
        name="browser_navigate",
        func=browser_navigate,  # ← Async function
        # ...
    ))
    # ToolSpec.to_langchain_tool() needs to use from_async()
```

### Phase 4: Update Agent
**File:** `src/agents/facebook_surfer.py`

**Before:**
```python
def invoke(self, task: str, thread_id: str = "default") -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = self.agent.invoke(  # ← Sync invoke
        {"messages": [{"role": "user", "content": task}]},
        config=config,
    )
    return result
```

**After:**
```python
async def invoke(self, task: str, thread_id: str = "default") -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = await self.agent.ainvoke(  # ← Async invoke
        {"messages": [{"role": "user", "content": task}]},
        config=config,
    )
    return result
```

### Phase 5: Update CLI
**File:** `src/main.py`

**Before:**
```python
@cli.command()
def run(task: str | None, ...):
    with init_session(login=False) as session:
        agent = FacebookSurferAgent(model=model)
        if task:
            run_single_task(agent, task, ...)  # ← Sync
```

**After:**
```python
@cli.command()
async def run(task: str | None, ...):
    async with async_init_session(login=False) as session:
        agent = FacebookSurferAgent(model=model)
        if task:
            await run_single_task(agent, task, ...)  # ← Async
```

## Code Examples: Before/After

### Navigation Tool

**Before (Sync):**
```python
@session_tool
def browser_navigate(url: str, wait_until: str = "load", timeout: int = 30000, page: Page = None) -> str:
    page.goto(url, wait_until=wait_until, timeout=timeout)
    return ToolResult(
        success=True,
        content=f"Navigated to {url}\nPage title: {page.title()}",
    ).to_string()
```

**After (Async):**
```python
@async_session_tool
async def browser_navigate(url: str, wait_until: str = "load", timeout: int = 30000, page: Page = None) -> str:
    await page.goto(url, wait_until=wait_until, timeout=timeout)
    return ToolResult(
        success=True,
        content=f"Navigated to {url}\nPage title: {await page.title()}",
    ).to_string()
```

### Click Tool

**Before (Sync):**
```python
@session_tool
def browser_click(selector: str, button: str = "left", page: Page = None) -> str:
    page.click(selector, button=button)
    return ToolResult(success=True, content=f"Clicked {selector}").to_string()
```

**After (Async):**
```python
@async_session_tool
async def browser_click(selector: str, button: str = "left", page: Page = None) -> str:
    await page.click(selector, button=button)
    return ToolResult(success=True, content=f"Clicked {selector}").to_string()
```

### Screenshot Tool

**Before (Sync):**
```python
@session_tool
def browser_screenshot(filename: str = "screenshot-{timestamp}", page: Page = None) -> str:
    screenshot_dir = Path("./screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    file_path = screenshot_dir / f"{filename}.png"
    page.screenshot(path=str(file_path))
    return ToolResult(success=True, content=f"Screenshot saved to {file_path}").to_string()
```

**After (Async):**
```python
@async_session_tool
async def browser_screenshot(filename: str = "screenshot-{timestamp}", page: Page = None) -> str:
    screenshot_dir = Path("./screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    file_path = screenshot_dir / f"{filename}.png"
    await page.screenshot(path=str(file_path))
    return ToolResult(success=True, content=f"Screenshot saved to {file_path}").to_string()
```

## Implementation Checklist

### Core Infrastructure
- [ ] Convert `src/session/__init__.py` to async
  - [ ] Update imports to `playwright.async_api`
  - [ ] Convert `start_login()` to async
  - [ ] Convert `restore_session()` to async
  - [ ] Convert `_launch_context()` to async
  - [ ] Convert all `page.*` calls to await
  - [ ] Convert all `context.*` calls to await

- [ ] Convert `src/tools/base.py` to async
  - [ ] Create `@async_session_tool` decorator
  - [ ] Update context helpers for async
  - [ ] Add async event loop management

### Tool Functions (22 tools)
- [ ] **Navigation** (4 tools)
  - [ ] `browser_navigate`
  - [ ] `browser_navigate_back`
  - [ ] `browser_screenshot`
  - [ ] `browser_get_page_info`

- [ ] **Interaction** (5 tools)
  - [ ] `browser_click`
  - [ ] `browser_type`
  - [ ] `browser_select_option`
  - [ ] `browser_hover`
  - [ ] `browser_press_key`

- [ ] **Forms** (3 tools)
  - [ ] `browser_fill_form`
  - [ ] `browser_get_form_data`
  - [ ] `browser_submit_form`

- [ ] **Utilities** (5 tools)
  - [ ] `browser_wait`
  - [ ] `browser_evaluate`
  - [ ] `browser_get_snapshot`
  - [ ] `browser_get_network_requests`
  - [ ] `browser_get_console_messages`

- [ ] **Browser** (5 tools)
  - [ ] `browser_tabs`
  - [ ] `browser_resize`
  - [ ] `browser_handle_dialog`
  - [ ] `browser_reload`
  - [ ] `browser_close`

### Registry & Agent
- [ ] Update `src/tools/registry.py`
  - [ ] Modify `ToolSpec.to_langchain_tool()` to use `from_async()`
  - [ ] Ensure async functions are properly wrapped

- [ ] Update `src/agents/facebook_surfer.py`
  - [ ] Convert `invoke()` to async
  - [ ] Convert `stream()` to async
  - [ ] Convert `get_state()` to async
  - [ ] Convert `update_state()` to async

### CLI
- [ ] Update `src/main.py`
  - [ ] Convert `init_session()` to async context manager
  - [ ] Convert `run_single_task()` to async
  - [ ] Convert `run_interactive()` to async
  - [ ] Update Click commands to support async

### Tests
- [ ] Update `tests/test_facebook_surfer.py`
  - [ ] Convert test functions to async
  - [ ] Use pytest-asyncio fixtures
  - [ ] Update mocks for async functions

## Common Pitfalls

### 1. Missing `await` on Playwright Methods
❌ **Wrong:**
```python
async def browser_navigate(url: str, page: Page = None) -> str:
    page.goto(url)  # ← Missing await, returns coroutine instead of navigating
    return "done"
```

✅ **Right:**
```python
async def browser_navigate(url: str, page: Page = None) -> str:
    await page.goto(url)  # ← Properly awaited
    return "done"
```

### 2. Using `asyncio.run()` Inside Async Functions
❌ **Wrong:**
```python
async def some_tool() -> str:
    result = asyncio.run(other_async_func())  # ← Creates nested event loop
    return result
```

✅ **Right:**
```python
async def some_tool() -> str:
    result = await other_async_func()  # ← Proper await
    return result
```

### 3. Mixing Sync and Async Playwright
❌ **Wrong:**
```python
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

# Don't mix both in same process
```

✅ **Right:**
```python
# Use only async_api throughout
from playwright.async_api import async_playwright
```

### 4. Forgetting to Make Context Manager Async
❌ **Wrong:**
```python
def init_session():
    session = FacebookSessionManager()
    with sync_playwright() as p:  # ← Sync context manager
        yield session
```

✅ **Right:**
```python
async def async_init_session():
    session = FacebookSessionManager()
    async with async_playwright() as p:  # ← Async context manager
        yield session
```

## Best Practices

1. **Always await Playwright methods** - All browser operations are async
2. **Use `async with` for context managers** - Proper resource cleanup
3. **Avoid `time.sleep()`** - Use `await asyncio.sleep()` instead
4. **Handle async exceptions** - Use `try/except` with async operations
5. **Use `pytest-asyncio` for tests** - Enables async test functions
6. **Keep the event loop running** - Don't stop/restart loop during execution
7. **Reuse browser/context** - Avoid creating new browsers for each operation
8. **Use timeouts** - Set appropriate timeouts on async operations

## Pydantic v2 Considerations

- **Schema definition remains the same** - `BaseModel` doesn't change
- **Validators stay sync** - Keep I/O in the tool body, not validators
- **No special async handling needed** - Pydantic works fine with async

## Dependencies

Add to `requirements.txt` or `pyproject.toml`:
```
pytest-asyncio>=0.23.0  # For async test support
```

## References

- [Playwright Python Async Docs](https://playwright.dev/python/docs/api/class-playwrightasyncapi)
- [LangChain Async Tools](https://docs.langchain.com/oss/python/concepts/tools/#async-tools)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

## Raw Codex Response

<details>
<summary>Full Codex Research Response</summary>

```json
{
  "result": "# Async Playwright Migration for LangChain/LangGraph (Python)\\n\\n## 1. `async_playwright()` vs `sync_playwright()`\\n- **Thread model**: `sync_playwright()` uses **greenlets** bound to the thread that created them. Background-thread execution (common in LangChain) triggers `greenlet.error: Cannot switch to a different thread`.\\n- **Async API**: `async_playwright()` is true asyncio; no greenlets, safe with event loops and background task scheduling.\\n- **Lifecycle**: Both need explicit start/stop; async uses `async with async_playwright()` or `await pw.start()`/`await pw.stop()`.\\n- **I/O**: Async API awaits network and browser ops; sync blocks the thread.\\n\\n## 2. Migration Strategy (Sync \\u2192 Async)\\n1. **Inventory tools**: List all 22 tools and the Playwright methods each uses.\\n2. **Convert function signatures**: `def tool(...):` \\u2192 `async def tool(...)`.\\n3. **Replace sync calls**: `page.goto()` \\u2192 `await page.goto()`; same for click/type/screenshot.\\n4. **Replace context manager**: `with sync_playwright() as p:` \\u2192 `async with async_playwright() as p:`.\\n5. **Return values** remain the same; just ensure `await` for operations.\\n6. **LangChain**: Use `StructuredTool.from_async` or `StructuredTool` with `async def`.\\n7. **Testing**: Run a minimal async smoke test with a single tool.\\n\\n## 3. Integrate Async Tools with LangChain `StructuredTool`\\n```python\\nfrom langchain.tools import StructuredTool\\nfrom pydantic import BaseModel\\n\\nclass NavigateArgs(BaseModel):\\n    url: str\\n\\nasync def navigate_tool(url: str) -> str:\\n    async with async_playwright() as p:\\n        browser = await p.chromium.launch(headless=True)\\n        page = await browser.new_page()\\n        await page.goto(url)\\n        await browser.close()\\n    return \\\"ok\\\"\\n\\nnavigate = StructuredTool.from_async(\\n    name=\\\"navigate\\\",\\n    description=\\\"Open a URL in Playwright\\\",\\n    coroutine=navigate_tool,\\n    args_schema=NavigateArgs,\\n)\\n```\\n\\n## 4. Async LangChain Tools with DeepAgents/LangGraph\\n- **LangGraph** nodes can be async functions; they can call async tools directly.\\n- Ensure the **graph executor** is async (`await graph.ainvoke(...)`).\\n- For DeepAgents or custom planners, prefer async execution or wrap sync nodes with `asyncio.to_thread` only for *non-Playwright* work.\\n- Avoid running Playwright sync API inside tool threads.\\n\\n## 5. Before/After Examples (Playwright Ops)\\n\\n### Navigate\\n**Sync**\\n```python\\nwith sync_playwright() as p:\\n    browser = p.chromium.launch()\\n    page = browser.new_page()\\n    page.goto(\\\"https://example.com\\\")\\n```\\n\\n**Async**\\n```python\\nasync with async_playwright() as p:\\n    browser = await p.chromium.launch()\\n    page = await browser.new_page()\\n    await page.goto(\\\"https://example.com\\\")\\n```\\n\\n### Click\\n**Sync**\\n```python\\npage.click(\\\"text=Login\\\")\\n```\\n**Async**\\n```python\\nawait page.click(\\\"text=Login\\\")\\n```\\n\\n### Type\\n**Sync**\\n```python\\npage.fill(\\\"#email\\\", \\\"user@example.com\\\")\\n```\\n**Async**\\n```python\\nawait page.fill(\\\"#email\\\", \\\"user@example.com\\\")\\n```\\n\\n### Screenshot\\n**Sync**\\n```python\\npage.screenshot(path=\\\"shot.png\\\")\\n```\\n**Async**\\n```python\\nawait page.screenshot(path=\\\"shot.png\\\")\\n```\\n\\n## 6. Event Loop Management Patterns\\n- **Preferred**: Run tools inside an existing async loop (LangGraph\\u2019s `ainvoke`).\\n- **If no loop exists**: Create one at the top-level, not inside tools.\\n- **Avoid nested loops** (`asyncio.run` inside tools); instead expose async and let caller await.\\n- **Background tasks**: If LangChain is running tools in threads, register async tools so they run in the loop rather than thread workers.\\n\\n## 7. Best Practices for Async Tool Functions\\n- Keep tools **single-responsibility** and short.\\n- Reuse browser/context if possible (via injected Playwright manager) to reduce startup overhead.\\n- Use **timeouts** and `wait_for_*` to avoid hangs.\\n- Ensure **proper cleanup** with `async with` or `try/finally`.\\n\\n## 8. Common Pitfalls\\n- Calling async Playwright from sync tools \\u2192 still causes blocking or event-loop errors.\\n- Using `asyncio.run()` inside tools (breaks if already in a loop).\\n- Mixing sync Playwright and async Playwright in the same process.\\n- Forgetting to `await` Playwright methods (silent failures or coroutines returned).\\n- Running async tools in thread pools without an event loop.\\n\\n## 9. Pydantic v2 Considerations\\n- Use `BaseModel` from Pydantic v2; schema definition is the same.\\n- Keep tool signatures consistent with `args_schema` fields.\\n- For complex types, define **`model_config`** if you need custom validation.\\n- Avoid sync validators doing I/O; keep I/O in async tool body.\\n\\n---\\n\\n### Minimal Async Tool Skeleton\\n```python\\nfrom pydantic import BaseModel\\nfrom langchain.tools import StructuredTool\\nfrom playwright.async_api import async_playwright\\n\\nclass ScreenshotArgs(BaseModel):\\n    url: str\\n    path: str\\n\\nasync def screenshot_tool(url: str, path: str) -> str:\\n    async with async_playwright() as p:\\n        browser = await p.chromium.launch(headless=True)\\n        page = await browser.new_page()\\n        await page.goto(url)\\n        await page.screenshot(path=path)\\n        await browser.close()\\n    return path\\n\\nscreenshot = StructuredTool.from_async(\\n    name=\\\"screenshot\\\",\\n    description=\\\"Take a screenshot of a URL\\\",\\n    coroutine=screenshot_tool,\\n    args_schema=ScreenshotArgs,\\n)\\n```\\n\\nIf you want, share one of your existing sync tools and I can rewrite it to async with LangChain/LangGraph wiring."
}
```

</details>

## Raw Context7 Response

<details>
<summary>Playwright Async Documentation</summary>

### Connect to Playwright Server (Async API)
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect("ws://127.0.0.1:3000/")
```

### Make API Request and Assert Response (Python - Async)
```python
import asyncio
from playwright.async_api import async_playwright, Playwright

async def run(playwright: Playwright):
    context = await playwright.request.new_context()
    response = await context.get("https://example.com/user/repos")
    assert response.ok
    assert response.status == 200

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())
```

</details>

<details>
<summary>LangChain Async Tools Documentation</summary>

### Async Usage Pattern for Hyperbrowser Tools
```python
async def browse_website():
    tool = HyperbrowserBrowserUseTool()
    result = await tool.arun(
        {
            "task": "Go to npmjs.com, click the first visible package, and tell me when it was updated"
        }
    )
    return result

result = await browse_website()
```

### Async Web Operations with Hyperbrowser Tools
```python
async def web_operations():
    crawl_tool = HyperbrowserCrawlTool()
    crawl_result = await crawl_tool.arun(
        {
            "url": "https://example.com",
            "max_pages": 5,
        }
    )
    return crawl_result
```

</details>
