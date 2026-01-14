# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User CLI                             │
│  (login / run [--stream] [--debug] [--thread] [--model])   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FacebookSurferAgent                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DeepAgents + LangGraph                              │  │
│  │  - MemorySaver (checkpointer)                        │  │
│  │  - InMemoryStore                                     │  │
│  │  - SkillsMiddleware (loads from skills/)             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Tool Registry                              │
│  (auto-discovers all @register_tool decorated classes)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Global Session Context                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FacebookSessionManager                              │  │
│  │  - Persistent context in ./profiles/facebook/        │  │
│  │  - SingletonLock cleanup                             │  │
│  │  - Cookie/storage state persistence                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Playwright                                │
│  (Chromium browser with stealth args)                       │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow

```
User Task → CLI → Agent.invoke(task)
                  │
                  ▼
            LLM decides action
                  │
                  ▼
            Tool call (via registry)
                  │
                  ▼
            Global session context
                  │
                  ▼
            Playwright execution
                  │
                  ▼
            Result → LLM → Next action or final response
```

## Key Patterns

### Session Management

**Singleton Pattern**: `FacebookSessionManager` provides global session/page context via module-level functions:
- `set_global_session()` - Set active session
- `get_current_async_page()` - Get page for tool execution
- Automatic cleanup of `SingletonLock` files

**Context Manager Pattern**: Session initialization uses async context managers:

```python
async with async_init_session(login=False) as session:
    agent = FacebookSurferAgent(model=model)
    await agent.invoke(task)
```

### Tool Registry

**Decorator Pattern**: Tools self-register via `@register_tool` decorator:

```python
@register_tool
class BrowserClick(BaseTool):
    name = "browser_click"
    description = "Click an element on the page"
```

**Auto-discovery**: `register_all_tools()` scans `src/tools/` and builds registry.

**Ref Resolution**: `ref_registry.py` resolves snapshot refs to actual DOM elements.

### Agent Architecture

**LangGraph State Machine**: Agent uses graph-based execution with:
- **Nodes**: LLM reasoning, tool execution, human approval
- **Edges**: Conditional routing based on results
- **Checkpointing**: MemorySaver persists conversation state

**Skills Middleware**: Domain-specific guidance loaded from filesystem:
- `skills/facebook-automation/SKILL.md` → injected as context
- Enables site-specific workflows without code changes

## Facebook-Specific Workflows

### Human-in-the-Loop Login

1. Navigate to facebook.com
2. Start 3-minute timer with progress polling
3. User manually completes login in visible browser
4. Poll for `LOGGED_IN_SELECTORS` to detect success
5. Save cookies.json and state.json to profile

### Privacy Selector Pattern

1. `browser_get_snapshot()` - Get current page state with refs
2. Analyze all buttons with refs to find privacy button
3. `browser_click(ref="eXX", force=True)` - Click privacy button
4. `browser_select_option(radio="Only me")` - Select option
5. `browser_click(button="Done")` - Confirm selection
6. `browser_get_snapshot()` - Verify change

## Security Considerations

- **Stealth Browser Args**: Anti-detection flags (`--disable-blink-features=AutomationControlled`)
- **Human-like Timing**: Random delays between actions
- **Force Clicks**: Uses `force=True` to bypass overlay detection
- **Profile Isolation**: Each agent instance gets isolated context

## State Persistence

| Location | Content | Purpose |
|----------|---------|---------|
| `profiles/facebook/cookies.json` | Session cookies | Login persistence |
| `profiles/facebook/state.json` | Storage state | LocalStorage, SessionStorage |
| `profiles/facebook/` | Browser profile | IndexedDB, cache, extensions |
| Thread checkpoint | Conversation history | Memory across sessions |

## Error Recovery

- **Session Validation**: Check `LOGGED_IN_SELECTORS` on restore
- **Retry Logic**: 3 attempts for Facebook navigation
- **Graceful Degradation**: Continue on non-critical tool failures
- **Interrupt Handling**: HITL can pause execution for human input
