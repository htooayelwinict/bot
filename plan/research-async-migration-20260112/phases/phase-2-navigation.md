# Phase 2: Navigation Tools

**Status:** Complete
**Depends:** Phase 1 (Async Infrastructure)
**Completed:** 2025-01-12

## Overview

Convert 4 navigation tools to async.

## Tasks

### Update `src/tools/navigation.py`

**File:** `src/tools/navigation.py`

**Changes:**
1. Import from `playwright.async_api` instead of `playwright.sync_api`
2. Change `@session_tool` to `@async_session_tool`
3. Convert all functions to `async def`
4. Add `await` to all Playwright operations

**Tools to convert:**
- `browser_navigate()`
- `browser_navigate_back()`
- `browser_screenshot()`
- `browser_get_page_info()`

**Before:**
```python
from playwright.sync_api import Page

@session_tool
def browser_navigate(url: str, wait_until: str = "load", timeout: int = 30000, page: Page = None) -> str:
    page.goto(url, wait_until=wait_until, timeout=timeout)
    return ToolResult(
        success=True,
        content=f"Navigated to {url}\nPage title: {page.title()}",
        data={"url": page.url, "title": page.title()},
    ).to_string()
```

**After:**
```python
from playwright.async_api import Page

@async_session_tool
async def browser_navigate(url: str, wait_until: str = "load", timeout: int = 30000, page: Page = None) -> str:
    await page.goto(url, wait_until=wait_until, timeout=timeout)
    return ToolResult(
        success=True,
        content=f"Navigated to {url}\nPage title: {await page.title()}",
        data={"url": page.url, "title": await page.title()},
    ).to_string()
```

## Verification

```bash
# Check module loads
python -c "from src.tools.navigation import browser_navigate; print('Navigation tools OK')"

# Run basic import test
python -c "
from src.tools.navigation import (
    browser_navigate,
    browser_navigate_back,
    browser_screenshot,
    browser_get_page_info,
)
print('All 4 navigation tools imported')
"
```

## Acceptance Criteria

- [ ] `src/tools/navigation.py` uses `playwright.async_api`
- [ ] All 4 functions use `@async_session_tool`
- [ ] All functions are `async def`
- [ ] All Playwright operations use `await`
- [ ] Module imports without errors
