# Facebook Surfer - AI Automation Agent

Facebook automation agent using DeepAgents + LangChain + Playwright with persistent session management.

## Quick Start

```bash
# Install dependencies
pip install -e ".[agent,dev]"

# Install Playwright browser
.venv/bin/python -m playwright install chromium

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with OPENROUTER_API_KEY

# Create Facebook session (first time only)
.venv/bin/python -m facebook-surfer login

# Run a task
.venv/bin/python -m facebook-surfer run "Post hello world to Facebook"

# Interactive mode
.venv/bin/python -m facebook-surfer run
```

## Documentation

| Doc | Description |
|-----|-------------|
| [CLAUDE.md](CLAUDE.md) | Development commands and architecture |
| [docs/codebase-summary.md](docs/codebase-summary.md) | File structure and key files |
| [docs/code-standards.md](docs/code-standards.md) | Python conventions and patterns |
| [docs/system-architecture.md](docs/system-architecture.md) | Design and data flow |

## Tech Stack

- **Backend:** Python 3.11+, Playwright
- **Agent Framework:** DeepAgents, LangChain, LangGraph
- **Testing:** Pytest, pytest-asyncio
- **Linting:** Ruff, mypy

## Commands

| Command | Purpose |
|---------|---------|
| `pip install -e ".[agent]"` | Install with agent dependencies |
| `python -m facebook-surfer login` | Create Facebook session |
| `python -m facebook-surfer run "task"` | Run single task |
| `python -m facebook-surfer run --stream` | Stream mode |
| `python -m facebook-surfer run --debug` | Debug mode |
| `pytest tests/` | Run tests |

## Project Structure

- `src/session/` - Facebook session management with HITL login
- `src/tools/` - Browser automation tools with registry pattern
- `src/agents/` - DeepAgents integration with skills middleware
- `skills/` - Domain-specific guidance for workflows
- `profiles/` - Persistent browser contexts (gitignored)

## License

MIT
