# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

**CRITICAL:** Always use `.venv` for all Python commands, dependencies, and app runtime.

```bash
# First-time setup
python3 -m venv .venv
.venv/bin/pip install -e ".[agent,dev,memory]"
.venv/bin/python -m playwright install chromium
cp config/.env.example config/.env
# Edit config/.env with OPENROUTER_API_KEY and OPENAI_API_KEY

# Optional: Enable ref debug logging
export DEBUG_REFS=true
```

## Development Commands

| Command | Purpose |
|--------|---------|
| `.venv/bin/pip install -e .` | Install base dependencies |
| `.venv/bin/pip install -e ".[agent]"` | Install with DeepAgents/LangChain |
| `.venv/bin/pip install -e ".[dev]"` | Install dev tools (pytest, ruff, mypy) |
| `.venv/bin/pip install -e ".[memory]"` | Install Qdrant vector storage |
| `.venv/bin/python -m playwright install chromium` | Install browser |
| `.venv/bin/python -m facebook-surfer login` | Create Facebook session |
| `.venv/bin/python -m facebook-surfer run "task"` | Run single task |
| `.venv/bin/python -m facebook-surfer run` | Interactive mode |
| `.venv/bin/python -m facebook-surfer run --stream` | Stream mode with real-time output |
| `.venv/bin/python -m facebook-surfer run --debug` | Debug mode with detailed events |
| `.venv/bin/python -m facebook-surfer run --enable-metrics "task"` | Enable trajectory storage |
| `.venv/bin/python -m facebook-surfer run --enable-planning "task"` | Enable RAG-based planning |
| `.venv/bin/python scripts/seed_trajectories.py` | Seed initial trajectories for cold start |
| `.venv/bin/python -m pytest tests/` | Run tests |
| `.venv/bin/python -m pytest tests/ -v` | Run tests with verbose output |
| `.venv/bin/python -m pytest tests/test_file.py` | Run single test file |
| `.venv/bin/python -m pytest tests/metrics/` | Run metrics tests |
| `.venv/bin/python -m pytest tests/storage/` | Run storage tests |
| `.venv/bin/python -m pytest tests/agents/` | Run agent tests |
| `.venv/bin/python -m pytest tests/integration/` | Run integration tests |
| `ruff check src/` | Lint code |
| `ruff check src/ --fix` | Fix lint issues |
| `mypy src/` | Type check |

## Architecture Overview

Python-based Facebook automation agent using DeepAgents + LangChain + LangGraph with Playwright browser automation and adaptive learning via RAG-based trajectory storage and retrieval.

**Phased Development** (per [pyproject.toml](pyproject.toml)):
- Phase 1: Base tools + session management ✅
- Phase 2: DeepAgents/LangChain integration ✅
- Phase 3: Qdrant vector storage + learning ✅
- Phase 4: RAG-based planning agent ✅

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
- Security: [`security.py`](src/tools/security.py) wraps tool outputs for prompt injection defense

**Agent** ([`src/agents/`](src/agents/))
- **[`facebook_surfer.py`](src/agents/facebook_surfer.py)**: `FacebookSurferAgent` using DeepAgents framework
  - LangGraph orchestration with `MemorySaver` checkpointer
  - Skills middleware loads domain guidance from `skills/facebook-automation/`
  - System prompt enforces "Observe → Analyze → Act → Verify" workflow
  - Supports OpenRouter models via `openrouter/<model_name>` format
- **[`planner.py`](src/agents/planner.py)**: RAG-based workflow planning agent
  - Retrieves similar historical workflows from Qdrant
  - Generates success plans using Grok reasoning model
  - Uses shared `create_openrouter_llm()` utility
- **[`reflection.py`](src/agents/reflection.py)**: Trajectory analysis agent
  - Analyzes execution patterns to identify success/failure
  - Generates structured critiques with working/failed patterns
  - Uses shared utilities for OpenRouter and JSON parsing
- **[`utils.py`](src/agents/utils.py)**: Shared agent utilities
  - `create_openrouter_llm()`: Centralized OpenRouter ChatOpenAI configuration
  - `parse_json_with_fallback()`: JSON parsing with markdown code block support

**Learning System** ([`src/metrics/`](src/metrics/), [`src/storage/`](src/storage/))
- **Trajectory Capture** ([`trajectory_callback.py`](src/metrics/trajectory_callback.py)): LangChain callback handler that captures all tool calls with timing, success/failure, and token usage
- **Scoring** ([`scoring.py`](src/metrics/scoring.py)): Weighted multi-dimensional scoring (40% tool success, 20% latency, 20% tokens, 20% outcome)
- **PII Redaction** ([`pii_redaction.py`](src/metrics/pii_redaction.py)): Removes emails, phones, SSN, credit cards, API keys before storage
- **Qdrant Storage** ([`trajectory_store.py`](src/storage/trajectory_store.py)): Vector database with OpenAI embeddings for semantic retrieval
- **Planning Agent** ([`planner.py`](src/agents/planner.py)): Retrieves similar workflows and generates success plans
- **Reflection Agent** ([`reflection.py`](src/agents/reflection.py)): Analyzes trajectories to identify successful/failed patterns

**Data Flow:**
```
Task → Planning Agent (if enabled) → Execution Agent → Trajectory Capture → Scoring → PII Redaction → Qdrant Storage
                                                                  ↓
                                              Similarity Retrieval for Future Tasks
```

### CLI Commands ([`src/main.py`](src/main.py))

- `login` - Start 3-minute manual login flow
- `run [--stream] [--debug] [--thread ID] [--model MODEL] [--enable-metrics] [--enable-planning] [task]`
  - `--stream`: Real-time tool call visualization
  - `--debug`: Full event streaming (nodes, tools, LLM calls)
  - `--enable-metrics`: Capture trajectory and store in Qdrant (requires `OPENAI_API_KEY`)
  - `--enable-planning`: Retrieve similar workflows and inject success plan (requires prior metrics)
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

## Learning & Planning System

The agent can learn from past executions and improve future performance via trajectory capture, scoring, and RAG-based planning.

### Enable Learning

```bash
# Enable trajectory capture and storage
.venv/bin/python -m facebook-surfer run --enable-metrics "Post to group"

# Enable RAG-based planning from historical workflows
.venv/bin/python -m facebook-surfer run --enable-planning "Post to group"

# Full learning loop (plan + store)
.venv/bin/python -m facebook-surfer run --enable-planning --enable-metrics "Post to group"
```

### How It Works

1. **Trajectory Capture** (`--enable-metrics`)
   - `TrajectoryCallbackHandler` intercepts all tool calls via LangChain callbacks
   - Records: tool name, input, output, success/failure, latency, token usage
   - Thread-safe for concurrent executions

2. **Scoring** (weighted formula)
   - Tool Success (40%): Ratio of successful tool calls
   - Latency (20%): Normalized against 30s target
   - Token Cost (20%): Normalized against 5000 token target
   - Outcome Match (20%): User feedback (currently defaults to 0.5)

3. **PII Redaction**
   - Removes: emails, phones, SSN, credit cards, API keys
   - Applied BEFORE embedding (security critical)

4. **Qdrant Storage**
   - Stores trajectories with OpenAI `text-embedding-3-small` embeddings
   - Local persistent storage in `./qdrant_db/` (gitignored)
   - Cosine similarity search for retrieval

5. **RAG-Based Planning** (`--enable-planning`)
   - Retrieves top-3 similar workflows by semantic similarity
   - `PlanningAgent` generates success plan from historical patterns
   - Plan injected into agent context for better execution

6. **Reflection** (automatic)
   - `ReflectionAgent` analyzes trajectories to identify patterns
   - Stores critique, successful/failed patterns in trajectory metadata

### Cold Start

Before planning can work, you need historical trajectories:

```bash
# Option 1: Run with metrics enabled several times
.venv/bin/python -m facebook-surfer run --enable-metrics "Post to group"
# Repeat 3-5 times with different tasks

# Option 2: Use seed script
.venv/bin/python scripts/seed_trajectories.py
```

### Configuration

Requires `OPENAI_API_KEY` in [`config/.env`](config/.env) for embeddings and planning.

See [plan/agent-metrics-rag-learning-20260123-003053/README.md](plan/agent-metrics-rag-learning-20260123-003053/README.md) for full details.

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

---

## Agent Development Patterns

### Shared Utilities ([`src/agents/utils.py`](src/agents/utils.py))

All agent modules use shared utilities to avoid code duplication:

**`create_openrouter_llm()`** - OpenRouter ChatOpenAI configuration
```python
from src.agents.utils import create_openrouter_llm

llm = create_openrouter_llm(
    model="x-ai/grok-4.1-fast",
    temperature=0.0,
    api_key=None,  # Uses OPENROUTER_API_KEY env var
    app_title="MyAgent",
    extra_body={"reasoning": {"effort": "medium"}},  # Optional
)
```

**`parse_json_with_fallback()`** - Robust JSON parsing from LLM responses
```python
from src.agents.utils import parse_json_with_fallback

# Handles raw JSON, markdown code blocks, and provides fallback
result = parse_json_with_fallback(
    llm_response,
    fallback={"error": "parse failed", "raw_text": llm_response}
)
```

### Creating New Agents

```python
from deepagents import create_deep_agent
from src.agents.utils import create_openrouter_llm, parse_json_with_fallback

class MyAgent:
    def __init__(self, model: str = "openrouter/model"):
        self.llm = create_openrouter_llm(model, app_title="MyAgent")
        self.agent = create_deep_agent(
            model=self.llm,
            system_prompt="Your prompt here",
            tools=[],
        )

    def _parse_response(self, text: str) -> dict:
        return parse_json_with_fallback(text, fallback={})
```