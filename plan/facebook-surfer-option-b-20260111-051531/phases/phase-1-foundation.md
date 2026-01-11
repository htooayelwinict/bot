# Phase 1: Foundation

**Status:** ✅ Completed 2026-01-12

**Objective:** Set up Python project, implement session management, convert 5 core tools

---

## Prerequisites

- Existing TypeScript codebase analyzed
- Python 3.11+ installed
- Facebook credentials available

---

## Tasks

### 1.1 Project Setup

- [x] Create Python project structure
- [x] Configure dependencies in `pyproject.toml`
- [x] Set up virtual environment (`.venv`)
- [x] Configure environment variables (`.env.example`)

**Files:**
- `pyproject.toml` - Project metadata and dependencies
- `.env.example` - Environment template
- `.gitignore` - Python-specific ignores

**Dependencies:**
```txt
deepagents>=0.1.0
langchain>=0.3.0
langchain-openai>=0.2.0
langgraph>=0.2.0
playwright>=1.48.0
chromadb>=0.5.0
openai>=1.54.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

### 1.2 Session Management

- [x] Port `HumanInLoopLogin` to Python (`src/session/playwright_session.py`)
- [x] Implement lock file cleanup
- [x] Port browser stealth arguments
- [x] Implement login polling logic
- [x] Add session persistence (cookies.json, state.json)

**Reference:** `src/automation/human-in-loop-login.ts`

**Files:**
- `src/session/__init__.py`
- `src/session/playwright_session.py`

**Key Methods:**
```python
class PlaywrightSession:
    def __init__(self, profile_path: str = "./profiles/bot-facebook")
    def start_login(self) -> bool  # HITL flow
    def restore_session(self) -> bool  # Restore existing
    def _check_if_logged_in(self) -> bool  # Selector check
    def _navigate_to_facebook(self) -> bool
    def _save_session(self) -> None
    def get_page(self) -> Page
    def get_context(self) -> BrowserContext
    def close(self) -> None
```

### 1.3 Tool Base Classes

- [x] Create base Pydantic models for tool args
- [x] Create session-aware tool decorator
- [x] Implement tool registry pattern

**Files:**
- `src/tools/__init__.py`
- `src/tools/base.py`

**Pattern:**
```python
from functools import wraps
from playwright.sync_api import Page

def session_tool(func):
    """Decorator to inject current page into tool calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Inject page from session
        return func(*args, **kwargs)
    return wrapper
```

### 1.4 Core Tool Conversion (5 tools)

Convert from `src/mcp-tools/tools/`:

- [x] **Navigation:** `browser_navigate` (navigate.ts)
- [x] **Navigation:** `browser_navigate_back` (navigate.ts)
- [x] **Navigation:** `browser_screenshot` (navigate.ts)
- [x] **Navigation:** `browser_get_page_info` (navigate.ts)
- [x] **Interaction:** `browser_click` (interaction.ts)

**Files:**
- `src/tools/navigation.py` - Navigate, back, screenshot, page_info
- `src/tools/interaction.py` - Click

**Tool Pattern:**
```python
from pydantic import BaseModel, Field
from langchain.tools import tool

class NavigateArgs(BaseModel):
    url: str = Field(description="The URL to navigate to")
    wait_until: str = Field(
        default="load",
        enum=["load", "domcontentloaded", "networkidle"]
    )
    timeout: int = Field(default=30000, ge=0, le=300000)

@tool
def browser_navigate(args: NavigateArgs) -> str:
    """Navigate to a specific URL. Waits for the page to load before returning."""
    from src.session.playwright_session import get_current_page
    page = get_current_page()
    page.goto(args.url, wait_until=args.wait_until, timeout=args.timeout)
    return f"Navigated to {args.url}\nPage title: {page.title()}\nFinal URL: {page.url}"
```

### 1.5 Testing Core Tools

- [x] Unit test for each tool
- [ ] Integration test with Facebook (requires Facebook credentials)
- [x] Session management test

**Files:**
- `tests/test_session.py`
- `tests/test_navigation_tools.py`
- `tests/test_interaction_tools.py`

---

## Files to Create

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies & project config |
| `.env.example` | Environment template |
| `src/session/__init__.py` | Session module |
| `src/session/playwright_session.py` | HITL session management |
| `src/tools/__init__.py` | Tools module |
| `src/tools/base.py` | Base tool classes |
| `src/tools/navigation.py` | Navigate, back, screenshot, page_info |
| `src/tools/interaction.py` | Click tool |
| `tests/test_session.py` | Session tests |
| `tests/test_navigation_tools.py` | Navigation tool tests |
| `tests/test_interaction_tools.py` | Click tool tests |

---

## Verification

```bash
# 1. Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Install Playwright browser
playwright install chromium

# 3. Configure environment
cp .env.example config/.env
# Edit config/.env with credentials

# 4. Run session test
pytest tests/test_session.py -v

# 5. Test HITL login
python -m src.session.playwright_session

# 6. Test core tools
pytest tests/test_navigation_tools.py -v
pytest tests/test_interaction_tools.py -v

# 7. Manual verification
python -c "
from src.session.playwright_session import PlaywrightSession
from src.tools.navigation import browser_navigate

session = PlaywrightSession()
if session.restore_session():
    print('Session restored successfully')
    session.close()
"
```

**Expected Results:**
- All dependencies install without errors
- Chromium browser installs
- Session restores from `./profiles/bot-facebook/`
- 5 core tools execute successfully
- Tests pass with > 80% coverage

---

## Estimated Effort

**1-2 days**

- Project setup: 2 hours
- Session management: 4 hours
- Tool base classes: 2 hours
- Core tool conversion: 6 hours
- Testing: 2 hours

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Playwright Python API differences | Refer to Python docs, test early |
| Session persistence bugs | Reuse TS patterns exactly |
| Facebook login detection changes | Use multiple selectors, add fallbacks |

---

## Dependencies

- Phase 2: Vision Integration
- Phase 3: Agent Assembly

---

## Exit Criteria

- [x] Python project runs locally
- [ ] Session persists across restarts (requires Facebook credentials to test)
- [x] 5 core tools functional
- [x] Tests pass (20/20 passing)
- [ ] Can navigate to Facebook and take screenshot (requires Facebook credentials to test)

---

## Completion Summary

**Completed:** 2026-01-12

**Files Created:**
- `pyproject.toml` - Project metadata and dependencies
- `.env.example` - Environment template
- `src/main.py` - CLI entry point
- `src/session/__init__.py` - Session module exports
- `src/session/playwright_session.py` - HITL session management
- `src/tools/__init__.py` - Tools module exports
- `src/tools/base.py` - Base tool classes and decorators
- `src/tools/navigation.py` - Navigate, back, screenshot, page_info tools
- `src/tools/interaction.py` - Click tool
- `tests/__init__.py` - Test module
- `tests/test_session.py` - Session management tests (7/7 passing)
- `tests/test_navigation_tools.py` - Navigation tool tests (7/7 passing)
- `tests/test_interaction_tools.py` - Interaction tool tests (6/6 passing)

**Test Results:**
```
======================== 20 passed, 1 warning in 0.70s =========================
```

**Next Steps:**
- Phase 2: Vision Integration (GPT-4o vision tool, screenshot capture)
