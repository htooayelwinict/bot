# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

| Command | Purpose |
|--------|---------|
| `pip install -e .` | Install base dependencies |
| `pip install -e ".[agent]"` | Install with DeepAgents/LangChain |
| `pip install -e ".[dev]"` | Install dev tools (pytest, ruff, mypy) |
| `.venv/bin/python -m playwright install chromium` | Install browser |
| `cp config/.env.example config/.env` | Configure environment |
| `.venv/bin/python -m facebook-surfer login` | Create Facebook session |
| `.venv/bin/python -m facebook-surfer run "task"` | Run single task |
| `.venv/bin/python -m facebook-surfer run` | Interactive mode |
| `.venv/bin/python -m facebook-surfer run --stream` | Stream mode with real-time output |
| `.venv/bin/python -m facebook-surfer run --debug` | Debug mode with detailed events |
| `pytest tests/` | Run tests |
| `pytest tests/ -v` | Run tests with verbose output |
| `pytest tests/test_file.py` | Run single test file |
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