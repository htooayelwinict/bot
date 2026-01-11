# Phase 4: Forms, Utilities, and Browser Tools

**Status:** Complete
**Depends:** Phase 1 (Async Infrastructure)
**Completed:** 2025-01-12

## Overview

Convert remaining 13 tools to async across 3 modules.

## Tasks

### 1. Update `src/tools/forms.py`

**File:** `src/tools/forms.py`

**Tools to convert:**
- `browser_fill_form()`
- `browser_get_form_data()`
- `browser_submit_form()`

**Before:**
```python
from playwright.sync_api import Locator, Page

@session_tool
def browser_fill_form(fields: list[FormFieldArgs], page: Page = None) -> str:
    for field in fields:
        locator = page.locator(selector)
        locator.fill(str(value))
    return ToolResult(success=True, content="Form filled").to_string()
```

**After:**
```python
from playwright.async_api import Locator, Page

@async_session_tool
async def browser_fill_form(fields: list[FormFieldArgs], page: Page = None) -> str:
    for field in fields:
        locator = page.locator(selector)
        await locator.fill(str(value))
    return ToolResult(success=True, content="Form filled").to_string()
```

### 2. Update `src/tools/utilities.py`

**File:** `src/tools/utilities.py`

**Tools to convert:**
- `browser_wait()`
- `browser_evaluate()`
- `browser_get_snapshot()`
- `browser_get_network_requests()`
- `browser_get_console_messages()`

**Key change:** Replace `time.sleep()` with `await asyncio.sleep()`

**Before:**
```python
@session_tool
def browser_wait(time: int = 5, page: Page = None) -> str:
    time.sleep(time)
    return ToolResult(success=True, content=f"Waited {time}s").to_string()
```

**After:**
```python
@async_session_tool
async def browser_wait(time: int = 5, page: Page = None) -> str:
    await asyncio.sleep(time)
    return ToolResult(success=True, content=f"Waited {time}s").to_string()
```

### 3. Update `src/tools/browser.py`

**File:** `src/tools/browser.py`

**Tools to convert:**
- `browser_tabs()`
- `browser_resize()`
- `browser_handle_dialog()`
- `browser_reload()`
- `browser_close()`

**Before:**
```python
from playwright.sync_api import BrowserContext

@session_tool
def browser_resize(width: int, height: int, page: Page = None) -> str:
    page.set_viewport_size({"width": width, "height": height})
    return ToolResult(success=True, content=f"Resized to {width}x{height}").to_string()
```

**After:**
```python
from playwright.async_api import BrowserContext

@async_session_tool
async def browser_resize(width: int, height: int, page: Page = None) -> str:
    await page.set_viewport_size({"width": width, "height": height})
    return ToolResult(success=True, content=f"Resized to {width}x{height}").to_string()
```

### 4. Update `src/tools/vision.py` (if exists)

**File:** `src/tools/vision.py`

**Tools to convert:**
- `capture_screenshot_for_analysis()`
- `capture_screenshot_with_metadata()`

Same pattern: async def, await operations.

## Verification

```bash
# Forms
python -c "from src.tools.forms import browser_fill_form; print('Forms OK')"

# Utilities
python -c "from src.tools.utilities import browser_wait; print('Utilities OK')"

# Browser
python -c "from src.tools.browser import browser_resize; print('Browser OK')"

# All 13 tools
python -c "
from src.tools.forms import browser_fill_form, browser_get_form_data, browser_submit_form
from src.tools.utilities import browser_wait, browser_evaluate, browser_get_snapshot, browser_get_network_requests, browser_get_console_messages
from src.tools.browser import browser_tabs, browser_resize, browser_handle_dialog, browser_reload, browser_close
print('All 13 remaining tools imported')
"
```

## Acceptance Criteria

- [ ] `src/tools/forms.py` uses `playwright.async_api`
- [ ] `src/tools/utilities.py` uses `playwright.async_api`
- [ ] `src/tools/browser.py` uses `playwright.async_api`
- [ ] `src/tools/vision.py` uses `playwright.async_api` (if exists)
- [ ] All 13 functions use `@async_session_tool`
- [ ] All functions are `async def`
- [ ] All Playwright operations use `await`
- [ ] All `time.sleep()` replaced with `await asyncio.sleep()`
- [ ] All modules import without errors
