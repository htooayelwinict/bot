# Codebase Summary

## Directory Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── facebook_surfer.py      # Main execution agent
│   ├── planner.py              # RAG-based workflow planning
│   ├── reflection.py           # Trajectory analysis agent
│   └── utils.py                # Shared agent utilities
├── session/
│   └── __init__.py              # Facebook session management
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

tests/                            # 10 test files
├── test_facebook_surfer.py      # Agent tests
└── test_interaction_tools.py    # Tool tests

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
| [`src/agents/facebook_surfer.py`](src/agents/facebook_surfer.py) | Main execution agent with DeepAgents + LangGraph |
| [`src/agents/planner.py`](src/agents/planner.py) | RAG-based workflow planning with Grok reasoning |
| [`src/agents/reflection.py`](src/agents/reflection.py) | Trajectory analysis for pattern learning |
| [`src/agents/utils.py`](src/agents/utils.py) | Shared utilities (OpenRouter config, JSON parsing) |
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

**Shared Utilities** ([`src/agents/utils.py`](src/agents/utils.py)):
- `create_openrouter_llm()`: Centralized OpenRouter ChatOpenAI configuration
- `parse_json_with_fallback()`: JSON parsing with markdown code block support

**Main Execution Agent** ([`facebook_surfer.py`](src/agents/facebook_surfer.py)):
- Uses DeepAgents `create_deep_agent()` with LangGraph backend
- Skills middleware loads domain guidance from `skills/` filesystem
- `MemorySaver` checkpointer for conversation state
- `InMemoryStore` for context persistence
- OpenRouter model support via `openrouter/<model>` format

**Planning Agent** ([`planner.py`](src/agents/planner.py)):
- RAG-based workflow planning using Qdrant vector retrieval
- Generates success plans from historical patterns
- Uses shared `create_openrouter_llm()` with Grok reasoning model

**Reflection Agent** ([`reflection.py`](src/agents/reflection.py)):
- Analyzes execution trajectories to identify patterns
- Generates structured critiques with successful/failed patterns
- Uses shared utilities for OpenRouter and JSON parsing

## CLI Commands

| Command | Description |
|---------|-------------|
| `login` | Start 3-minute manual login flow |
| `run [task]` | Execute task or enter interactive mode |
| `--stream` | Real-time tool call visualization |
| `--debug` | Full event streaming (nodes, tools, LLM) |
| `--model` | Model selection (default: `openrouter/mistralai/devstral-2512:free`) |
| `--thread` | Conversation thread ID for memory |
