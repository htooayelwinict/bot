# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

**CRITICAL:** Always use `.venv` for all Python commands, dependencies, and app runtime.

```bash
# First-time setup
python3 -m venv .venv
.venv/bin/pip install -e ".[agent,dev]"
.venv/bin/python -m playwright install chromium
cp config/.env.example config/.env
# Edit config/.env with OPENROUTER_API_KEY
```

## Development Commands

| Command | Purpose |
|--------|---------|
| `.venv/bin/pip install -e .` | Install base dependencies |
| `.venv/bin/pip install -e ".[agent]"` | Install with DeepAgents/LangChain |
| `.venv/bin/pip install -e ".[dev]"` | Install dev tools (pytest, ruff, mypy) |
| `.venv/bin/python -m playwright install chromium` | Install browser |
| `.venv/bin/python -m facebook-surfer login` | Create Facebook session |
| `.venv/bin/python -m facebook-surfer run "task"` | Run single task |
| `.venv/bin/python -m facebook-surfer run` | Interactive mode |
| `.venv/bin/python -m facebook-surfer run --stream` | Stream mode with real-time output |
| `.venv/bin/python -m facebook-surfer run --debug` | Debug mode with detailed events |
| `.venv/bin/python -m pytest tests/` | Run tests |
| `.venv/bin/python -m pytest tests/ -v` | Run tests with verbose output |
| `.venv/bin/python -m pytest tests/test_file.py` | Run single test file |
| `ruff check src/` | Lint code |
| `ruff check src/ --fix` | Fix lint issues |
| `mypy src/` | Type check |

## Architecture Overview

Python-based Facebook automation agent using DeepAgents + LangChain + LangGraph with Playwright browser automation.

**Phased Development** (per [pyproject.toml](pyproject.toml)):
- Phase 1: Base tools + session management (current)
- Phase 2: DeepAgents/LangChain integration (`pip install -e ".[agent]"`)
- Phase 4: ChromaDB long-term memory (`pip install -e ".[memory]"`)

### Core Components

**Session Manager** ([`src/session/__init__.py`](src/session/__init__.py))
- Facebook authentication with persistent browser contexts in `./profiles/`
- Anti-bot detection with stealth browser args and 3-min human-in-the-loop login
- Session validation via DOM selectors (`LOGGED_IN_SELECTORS`, `LOGIN_SELECTORS`)
- Automatic `SingletonLock` cleanup for persistent contexts
- Both sync and async APIs supported

**Browser Tools** ([`src/tools/`](src/tools/))
- Standardized tools with Pydantic validation
- Registry pattern ([`registry.py`](src/tools/registry.py)) for auto-discovery
- Base tool class ([`base.py`](src/tools/base.py)) with global session/page context
- Categories: navigation, interaction, forms, vision, utilities

**Agent** ([`src/agents/facebook_surfer.py`](src/agents/facebook_surfer.py))
- `FacebookSurferAgent` using DeepAgents framework
- LangGraph for orchestration with `MemorySaver` checkpointer
- Skills middleware loads domain guidance from `skills/facebook-automation/`
- System prompt enforces "Observe → Analyze → Act → Verify" workflow
- Supports OpenRouter models via `openrouter/<model_name>` format

### CLI Commands ([`src/main.py`](src/main.py))

- `login` - Start 3-minute manual login flow
- `run [--stream] [--debug] [--thread ID] [--model MODEL] [task]` - Execute task or enter interactive mode
  - `--stream`: Real-time tool call visualization
  - `--debug`: Full event streaming (nodes, tools, LLM calls)
  - `--model`: Default `openrouter/mistralai/devstral-2512:free`

### Critical Workflow Patterns

**⚠️ REFS BECOME STALE AFTER EVERY ACTION**
After ANY click, type, or navigation: ALL refs from previous snapshot are INVALID. You MUST call `browser_get_snapshot()` to get fresh refs before the next action.

**Facebook Post Composer:**
1. Get snapshot, list ALL buttons with refs
2. Privacy button shows current state (Public/Friends) - NOT Photo/Feeling/GIF
3. Click privacy button ref → select option → Click Done → verify

**Selector Priority:**
1. `ref="e42"` from snapshot (most reliable)
2. `button=Name` for accessible names
3. `radio=Option` for radio buttons
4. `text=Text` for visible text
5. `[aria-label="X"]` for aria labels

Always use `force=True` for clicks on Facebook/complex sites with overlays.

---

## Tool Development

Tools use the registry pattern in [`src/tools/registry.py`](src/tools/registry.py):

```python
from src.tools.base import BaseTool
from src.tools.registry import ToolSpec, ToolCategory, registry

class MyTool(BaseTool):
    """Description of what this tool does."""

    def _execute(self, **kwargs) -> dict:
        return {"success": True, "data": ...}

# Register the tool
registry.register(
    ToolSpec(
        name="my_tool",
        category=ToolCategory.utilities,
        description="Brief description",
        func=my_tool_function,
        args_schema=MyInputSchema,  # Pydantic BaseModel
    )
)
```

All tools automatically get access to global session/page context via `get_current_async_page()`.

---

## Skills System

Domain-specific guidance lives in [`skills/facebook-automation/SKILL.md`](skills/facebook-automation/SKILL.md). The `SkillsMiddleware` (DeepAgents) injects this guidance into agent context at runtime, enabling site-specific workflows without code changes.

Key skill patterns:
- **Observe → Think → Act → Verify** workflow enforcement
- **Ref staleness rules** - critical for Facebook's React SPA
- **Selector priority** - ref → button= → radio= → aria-label
- **Dialog completion** - select option → confirm → verify

---

## Session Management Patterns

**Context Manager** (preferred):
```python
async with async_init_session(login=False) as session:
    agent = FacebookSurferAgent(model=model)
    await agent.invoke(task)
```

**Global Context** (tools use this internally):
```python
set_global_session(session)
page = get_current_async_page()
```

Both sync and async APIs are supported via `async_init_session()` / `init_session()`.