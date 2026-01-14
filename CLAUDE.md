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
| `.venv/bin/python src/main.py` | Run Facebook agent |
| `.venv/bin/python src/demo_tools.py` | Demo browser tools |
| `pytest tests/` | Run tests |
| `pytest tests/ -v` | Run tests with verbose output |
| `pytest tests/test_file.py` | Run single test file |
| `ruff check src/` | Lint code |
| `ruff check src/ --fix` | Fix lint issues |
| `mypy src/` | Type check |

## Architecture Overview

Python-based Facebook automation agent using Playwright with session management and MCP tools.

**Phased Development** (per [pyproject.toml](pyproject.toml)):
- Phase 1: Base tools + session management (current)
- Phase 2: DeepAgents/LangChain integration (`pip install -e ".[agent]"`)
- Phase 4: ChromaDB long-term memory (`pip install -e ".[memory]"`)

### Core Components

**Session Manager** (`src/session/manager.py`)
- Facebook authentication with persistent browser contexts stored in `./profiles/`
- Anti-bot detection with stealth browser arguments and human-like interaction
- Session validation and persistence
- Automatic cleanup of lock files

**Browser Tools** (`src/tools/`)
- Standardized browser automation tools
- Pydantic models for validation
- Registry pattern for tool discovery
- Direct Playwright execution

**Agent** (`src/agents/`)
- FacebookSurfer agent for autonomous navigation
- Tool orchestration and result handling
- State management and error recovery

### Development Workflow

1. **Setup**: Run `pip install -e .` and `playwright install chromium`
2. **Session**: Run `python src/main.py` to create/restore Facebook session
3. **Testing**: Use `pytest tests/` to validate functionality
4. **Tool Development**: Extend tools in `src/tools/` with proper type hints

### Testing Strategy

- **Unit Tests**: `pytest tests/` for tools and session management
- **Integration Tests**: `pytest tests/integration/` for end-to-end workflows
- **Demo Scripts**:
  - `src/demo_tools.py` - Browser tools demonstration
  - `src/main.py` - Full agent CLI

### Runtime Behavior

**Session Management**:
- Browser contexts persisted in `./profiles/facebook/`
- Automatic lock file cleanup on startup
- Account validation using DOM selectors
- Context isolation per agent instance

**Tool Execution**:
Input validation (Pydantic) → Playwright execution → result serialization → error handling