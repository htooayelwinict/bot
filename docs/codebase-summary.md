# Codebase Summary

## Directory Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── facebook_surfer.py      # DeepAgents integration
│   ├── planner.py              # RAG-based workflow planning agent
│   ├── reflection.py           # Trajectory analysis agent
│   └── utils.py                # Shared utilities (LLM, JSON parsing)
├── session/
│   └── __init__.py              # Facebook session management
├── tools/
├── metrics/
│   ├── trajectory_callback.py  # LangChain callback for trajectory capture
│   ├── scoring.py              # Multi-dimensional trajectory scoring
│   ├── pii_redaction.py        # PII redaction before storage
│   └── models.py               # Pydantic models for metrics
├── storage/
│   ├── trajectory_store.py     # Qdrant vector storage
│   ├── embeddings.py           # OpenAI embedding wrappers
│   ├── retrieval.py            # Semantic similarity search
│   └── qdrant_client.py        # Qdrant client manager
├── tools/
│   ├── __init__.py
│   ├── base.py                  # Base tool class with global context
│   ├── registry.py              # Tool auto-discovery & LangChain StructuredTool
│   ├── navigation.py            # URL navigation, page info, screenshots
│   ├── interaction.py           # Click, type, hover, press_key, select_option
│   ├── forms.py                 # Form filling, get/submit form
│   ├── vision.py                # Screenshot capture (legacy)
│   ├── utilities.py             # Snapshot, wait, evaluate, console/network logs
│   ├── browser.py               # Browser control (tabs, resize, dialog, reload, close)
│   ├── security.py              # Prompt injection defense (wrap_untrusted, detect)
│   └── ref_registry.py          # Ref-based tool resolution
├── main.py                      # CLI entry point (Click)
├── demo_tools.py                # Tool demonstration
├── facebook_post_tools.py       # Facebook-specific tools
└── facebook_post_onlyme.py      # "Only me" posting script

tests/                            # Test files
├── test_facebook_surfer.py      # Agent tests
├── test_interaction_tools.py    # Tool tests
├── metrics/                      # Metrics tests
└── storage/                      # Storage tests

qdrant_db/                        # Local Qdrant storage (gitignored)

scripts/                          # Utility scripts
└── seed_trajectories.py          # Cold start seeding

skills/
└── facebook-automation/
    └── SKILL.md                 # Domain-specific guidance & workflows

profiles/                        # Persistent browser contexts (gitignored)
└── facebook/

config/
└── .env.example                 # Environment template
```

## Key Files

| File | Purpose |
|------|---------|
| [`src/session/__init__.py`](src/session/__init__.py) | FacebookSessionManager with HITL login, persistent contexts |
| [`src/tools/registry.py`](src/tools/registry.py) | Auto-discovers & registers tools, converts to LangChain StructuredTool |
| [`src/tools/base.py`](src/tools/base.py) | BaseTool with global session/page context |
| [`src/tools/security.py`](src/tools/security.py) | Prompt injection defense (wrap_untrusted, detect, sanitize) |
| [`src/agents/facebook_surfer.py`](src/agents/facebook_surfer.py) | DeepAgents + LangGraph agent with skills middleware |
| [`src/agents/planner.py`](src/agents/planner.py) | RAG-based workflow planning agent |
| [`src/agents/reflection.py`](src/agents/reflection.py) | Trajectory analysis for patterns |
| [`src/agents/utils.py`](src/agents/utils.py) | Shared LLM and JSON utilities |
| [`src/metrics/trajectory_callback.py`](src/metrics/trajectory_callback.py) | LangChain callback for trajectory capture |
| [`src/metrics/scoring.py`](src/metrics/scoring.py) | Multi-dimensional trajectory scoring |
| [`src/storage/trajectory_store.py`](src/storage/trajectory_store.py) | Qdrant vector storage |
| [`src/storage/retrieval.py`](src/storage/retrieval.py) | Semantic similarity search |
| [`src/main.py`](src/main.py) | Click CLI: login, run, test commands |
| [`pyproject.toml`](pyproject.toml) | Dependencies, extras (agent, dev, memory) |

## Tools Registry

All tools in [`src/tools/`](src/tools/) are registered via [`ToolRegistry`](src/tools/registry.py):

```python
registry.register(
    ToolSpec(
        name="browser_click",
        category=ToolCategory.interaction,
        description="Click on an element",
        func=browser_click,
        args_schema=ClickArgs,  # Pydantic BaseModel
    )
)
```

Registered tools (22 total):
- **Navigation** (4): `browser_navigate`, `browser_navigate_back`, `browser_screenshot`, `browser_get_page_info`
- **Interaction** (5): `browser_click`, `browser_type`, `browser_select_option`, `browser_hover`, `browser_press_key`
- **Forms** (3): `browser_fill_form`, `browser_get_form_data`, `browser_submit_form`
- **Utilities** (5): `browser_wait`, `browser_evaluate`, `browser_get_snapshot`, `browser_get_network_requests`, `browser_get_console_messages`
- **Browser** (5): `browser_tabs`, `browser_resize`, `browser_handle_dialog`, `browser_reload`, `browser_close`

## Session Management

[`FacebookSessionManager`](src/session/__init__.py) provides:
- 3-minute human-in-the-loop login with progress polling
- Persistent browser contexts in `./profiles/facebook/`
- Cookie and storage state persistence (`cookies.json`, `state.json`)
- Automatic `SingletonLock` cleanup for Chrome profiles
- Login status detection via DOM selectors
- Both sync and async APIs

## Agent Architecture

[`FacebookSurferAgent`](src/agents/facebook_surfer.py):
- Uses DeepAgents `create_deep_agent()` with LangGraph backend
- Skills middleware loads domain guidance from `skills/` filesystem
- `MemorySaver` checkpointer for conversation state
- `InMemoryStore` for context persistence
- OpenRouter model support via `openrouter/<model>` format

## CLI Commands

| Command | Description |
|---------|-------------|
| `login` | Start 3-minute manual login flow |
| `run [task]` | Execute task or enter interactive mode |
| `--stream` | Real-time tool call visualization |
| `--debug` | Full event streaming (nodes, tools, LLM) |
| `--model` | Model selection (default: `openrouter/mistralai/devstral-2512:free`) |
| `--thread` | Conversation thread ID for memory |
| `--enable-metrics` | Capture trajectory and store in Qdrant |
| `--enable-planning` | Retrieve similar workflows and inject plan |

## Learning & Planning System

**Trajectory Capture** (`--enable-metrics`):
- `TrajectoryCallbackHandler` intercepts all tool calls
- Records timing, success/failure, token usage
- Calculates weighted score (40% tool success, 20% latency, 20% tokens, 20% outcome)
- PII redaction before storage

**RAG-Based Planning** (`--enable-planning`):
- Retrieves top-k similar workflows via semantic search
- `PlanningAgent` generates success plan from patterns
- Plan injected into agent context

Requires `OPENAI_API_KEY` for embeddings and planning.
