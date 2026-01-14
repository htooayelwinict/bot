# Codebase Summary

## Directory Structure

```
src/
├── agents/
│   ├── __init__.py
│   └── facebook_surfer.py      # DeepAgents integration
├── session/
│   └── __init__.py              # Facebook session management
├── tools/
│   ├── __init__.py
│   ├── base.py                  # Base tool class with global context
│   ├── registry.py              # Tool auto-discovery
│   ├── navigation.py            # URL navigation
│   ├── interaction.py           # Click, type, form actions
│   ├── forms.py                 # Form filling
│   ├── vision.py                # Screenshots and snapshots
│   ├── utilities.py             # Wait, extract, evaluate
│   └── ref_registry.py          # Ref-based tool resolution
├── main.py                      # CLI entry point (Click)
├── demo_tools.py                # Tool demonstration
├── facebook_post_tools.py       # Facebook-specific tools
└── facebook_post_onlyme.py      # "Only me" posting script

tests/
├── test_facebook_surfer.py      # Agent tests
└── test_interaction_tools.py    # Tool tests

skills/
└── facebook-automation/
    └── SKILL.md                 # Domain-specific guidance

profiles/                        # Persistent browser contexts (gitignored)
└── facebook/

config/
└── .env.example                 # Environment template
```

## Key Files

| File | Purpose |
|------|---------|
| [`src/session/__init__.py`](src/session/__init__.py) | FacebookSessionManager with HITL login, persistent contexts |
| [`src/tools/registry.py`](src/tools/registry.py) | Auto-discovers and registers all tools |
| [`src/tools/base.py`](src/tools/base.py) | BaseTool with global session/page context |
| [`src/agents/facebook_surfer.py`](src/agents/facebook_surfer.py) | DeepAgents + LangGraph agent with skills middleware |
| [`src/main.py`](src/main.py) | Click CLI: login, run, test commands |
| [`pyproject.toml`](pyproject.toml) | Dependencies, extras (agent, dev, memory) |

## Tools Registry

All tools in [`src/tools/`](src/tools/) are auto-discovered via decorator pattern:

```python
@register_tool
class SomeTool(BaseTool):
    ...
```

Registered tools:
- **Navigation**: `browser_navigate`, `browser_go_back`
- **Interaction**: `browser_click`, `browser_type`, `browser_hover`, `browser_press_key`
- **Forms**: `browser_fill_form`, `browser_select_option`, `browser_file_upload`
- **Vision**: `browser_get_snapshot`, `browser_take_screenshot`
- **Utilities**: `browser_wait`, `browser_evaluate`, `browser_extract_text`

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
