# Code Standards

## General Principles

1. Follow existing patterns in the codebase
2. Use type hints for all function signatures
3. Write self-documenting code with clear naming
4. Prefer composition over inheritance
5. Use async/await for Playwright operations

## Python Conventions

### Naming

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `FacebookSessionManager`, `BaseTool` |
| Functions/Methods | snake_case | `get_snapshot()`, `restore_session()` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_PROFILE_DIR`, `LOGIN_SELECTORS` |
| Modules | snake_case | `facebook_surfer.py`, `interaction.py` |
| Private | _leading_underscore | `_wait_for_login()`, `_has_saved_session()` |

### Type Hints

All functions must have type hints:

```python
from pathlib import Path
from typing import Optional

def start_login(self, profile: str = "./profiles/facebook") -> bool:
    """Start manual login flow.

    Returns:
        True if login successful, False if timeout
    """
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def browser_click(element: str, ref: str, force: bool = False) -> dict:
    """Click an element on the page.

    Args:
        element: Human-readable element description
        ref: Exact target element reference from snapshot
        force: Whether to bypass Playwright checks

    Returns:
        Success status with message
    """
```

## File Organization

| Location | Purpose |
|----------|---------|
| `src/session/` | Facebook session management |
| `src/tools/` | Browser automation tools |
| `src/agents/` | Agent implementations |
| `tests/` | Unit and integration tests |
| `skills/` | Domain-specific guidance (Markdown) |

## Tool Development

Tools must extend [`BaseTool`](src/tools/base.py):

```python
from src.tools.base import BaseTool, register_tool

@register_tool
class MyCustomTool(BaseTool):
    """Description of what this tool does."""

    def _execute(self, **kwargs) -> dict:
        # Implementation here
        return {"success": True, "data": ...}
```

Use Pydantic for input validation:

```python
from pydantic import BaseModel, Field

class ClickInput(BaseModel):
    element: str = Field(description="Human-readable element name")
    ref: str = Field(description="Element reference from snapshot")
    force: bool = Field(default=False, description="Bypass checks")
```

## Testing

- Test files: `tests/test_<module>.py`
- Use pytest fixtures for setup
- Mock external dependencies (Playwright, network)

```python
import pytest

def test_browser_click_with_valid_ref(page_mock):
    result = browser_click(element="Submit", ref="e42", force=True)
    assert result["success"] is True
```

## Commands

| Command | Purpose |
|---------|---------|
| `ruff check src/` | Lint code |
| `ruff check src/ --fix` | Auto-fix lint issues |
| `mypy src/` | Type check |
| `pytest tests/` | Run tests |
| `pytest tests/ -v` | Verbose test output |
| `pytest tests/test_file.py` | Run single test file |

## Import Order

1. Standard library
2. Third-party imports
3. Local imports

```python
import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext
from pydantic import BaseModel

from src.session import FacebookSessionManager
```

## Async Patterns

Use async/await for all Playwright operations:

```python
async def _go_to_facebook_async(self) -> bool:
    await self.async_page.goto("https://www.facebook.com", timeout=60000)
    await asyncio.sleep(2)
    return True
```

Both sync and async APIs are provided for session management.
