# Phase 1: Async Infrastructure

**Status:** Complete
**Priority:** Critical (blocks all other phases)
**Completed:** 2025-01-12

## Overview

Convert core infrastructure to async. This creates the foundation for all async tools.

## Tasks

### 1. Update `src/tools/base.py`

**File:** `src/tools/base.py`

**Changes:**
1. Import from `playwright.async_api` instead of `playwright.sync_api`
2. Create `@async_session_tool` decorator (parallel to `@session_tool`)
3. Update context helpers for async (keep sync versions for backward compatibility)

**Before:**
```python
from playwright.sync_api import BrowserContext, Page

def session_tool(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        # ... sync wrapper
```

**After:**
```python
from playwright.async_api import BrowserContext, Page

def async_session_tool(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        # ... async wrapper with await
```

### 2. Update `src/session/__init__.py`

**File:** `src/session/__init__.py`

**Changes:**
1. Import from `playwright.async_api` instead of `playwright.sync_api`
2. Convert all methods to async: `async def ...`
3. Add `await` to all Playwright operations
4. Update context managers to `async with`

**Methods to convert:**
- `start_login()` → `async def start_login()`
- `restore_session()` → `async def restore_session()`
- `_launch_context()` → `async def _launch_context()`
- `_go_to_facebook()` → `async def _go_to_facebook()`
- `_wait_for_login()` → `async def _wait_for_login()`
- `_is_logged_in()` → `async def _is_logged_in()`

**Before:**
```python
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

def start_login(self) -> bool:
    with sync_playwright() as p:
        self.context, self.page, _ = self._create_new_session(p.chromium)
```

**After:**
```python
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

async def start_login(self) -> bool:
    async with async_playwright() as p:
        self.context, self.page, _ = await self._create_new_session(p.chromium)
```

## Verification

```bash
# Check imports work
python -c "from playwright.async_api import async_playwright; print('Async imports OK')"

# Check base module loads
python -c "from src.tools.base import async_session_tool; print('Async decorator OK')"

# Check session module loads
python -c "from src.session import FacebookSessionManager; print('Async session OK')"
```

## Acceptance Criteria

- [ ] `src/tools/base.py` has `@async_session_tool` decorator
- [ ] `src/session/__init__.py` uses `playwright.async_api`
- [ ] All session methods are async (`async def`)
- [ ] All Playwright operations use `await`
- [ ] Module imports without errors
