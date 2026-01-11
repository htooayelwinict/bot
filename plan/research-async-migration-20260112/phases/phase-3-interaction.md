# Phase 3: Interaction Tools

**Status:** Complete
**Depends:** Phase 1 (Async Infrastructure)
**Completed:** 2025-01-12

## Overview

Convert 5 interaction tools to async.

## Tasks

### Update `src/tools/interaction.py`

**File:** `src/tools/interaction.py`

**Changes:**
1. Import from `playwright.async_api` instead of `playwright.sync_api`
2. Change `@session_tool` to `@async_session_tool`
3. Convert all functions to `async def`
4. Add `await` to all Playwright operations
5. Replace `time.sleep()` with `await asyncio.sleep()`

**Tools to convert:**
- `browser_click()`
- `browser_type()`
- `browser_select_option()`
- `browser_hover()`
- `browser_press_key()`

**Before:**
```python
from playwright.sync_api import Page
import time

@session_tool
def browser_click(selector: str, button: str = "left", page: Page = None) -> str:
    page.click(selector, button=button)
    time.sleep(0.5)  # Wait for action
    return ToolResult(success=True, content=f"Clicked {selector}").to_string()
```

**After:**
```python
from playwright.async_api import Page
import asyncio

@async_session_tool
async def browser_click(selector: str, button: str = "left", page: Page = None) -> str:
    await page.click(selector, button=button)
    await asyncio.sleep(0.5)  # Wait for action
    return ToolResult(success=True, content=f"Clicked {selector}").to_string()
```

## Verification

```bash
# Check module loads
python -c "from src.tools.interaction import browser_click; print('Interaction tools OK')"

# Run basic import test
python -c "
from src.tools.interaction import (
    browser_click,
    browser_type,
    browser_select_option,
    browser_hover,
    browser_press_key,
)
print('All 5 interaction tools imported')
"
```

## Acceptance Criteria

- [ ] `src/tools/interaction.py` uses `playwright.async_api`
- [ ] All 5 functions use `@async_session_tool`
- [ ] All functions are `async def`
- [ ] All Playwright operations use `await`
- [ ] `time.sleep()` replaced with `await asyncio.sleep()`
- [ ] Module imports without errors
