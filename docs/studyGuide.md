# Facebook Surfer - Implementation Study Guide

A deep dive into how this project successfully implements an autonomous AI agent using **DeepAgents**, **LangChain**, and **LangGraph** for browser automation.

---

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [How DeepAgents Works](#how-deepagents-works)
3. [LangGraph Runtime Deep Dive](#langgraph-runtime-deep-dive)
4. [LangChain Tool System](#langchain-tool-system)
5. [Agent Success Patterns](#agent-success-patterns)
6. [Skills Middleware System](#skills-middleware-system)
7. [Session & State Management](#session--state-management)
8. [Why This Implementation Succeeds](#why-this-implementation-succeeds)

---

## Technology Stack

### Core Dependencies

| Library | Version | Role |
|---------|---------|------|
| **DeepAgents** | ≥0.1.0 | High-level agent framework with middleware support |
| **LangChain** | ≥0.3.0 | LLM orchestration and tool integration |
| **LangGraph** | ≥0.2.0 | Stateful agent graph execution |
| **LangChain-OpenAI** | ≥0.2.0 | OpenAI/OpenRouter model integration |
| **Playwright** | ≥1.49.0 | Browser automation engine |
| **Pydantic** | ≥2.0.0 | Tool argument validation |

### Installation

```bash
# Base + Agent dependencies
pip install -e ".[agent]"

# Development tools
pip install -e ".[dev]"
```

---

## How DeepAgents Works

### The `create_deep_agent()` Factory

DeepAgents provides a high-level factory that internally constructs a LangGraph agent with best practices:

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    model=model_config,           # ChatOpenAI instance
    tools=tools,                  # List[StructuredTool]
    store=InMemoryStore(),        # Context persistence
    checkpointer=MemorySaver(),   # Conversation state
    system_prompt=system_prompt,  # Agent instructions
    interrupt_on={...},           # HITL configuration
    middleware=[skills_middleware], # Pre/post processing
)
```

### What DeepAgents Provides

| Feature | Description |
|---------|-------------|
| **Graph Construction** | Automatically builds LangGraph nodes and edges |
| **Tool Binding** | Properly binds sync/async tools to agent |
| **Middleware Pipeline** | Hooks for pre/post processing (skills injection) |
| **HITL Integration** | Built-in interrupt handling for human approval |
| **Streaming Support** | Full event streaming via `astream_events` |

### Agent Lifecycle

```
create_deep_agent() ──▶ CompiledGraph
                              │
                              ▼
┌─────────────────────────────────────────────┐
│ agent.ainvoke() / agent.astream()           │
│                                             │
│  1. Middleware pre-processing               │
│     - Skills loaded from filesystem         │
│     - Context injected into state           │
│                                             │
│  2. LangGraph execution loop                │
│     - Agent node (LLM) ◀──────────┐         │
│        ↓                          │         │
│     - Tool selection              │         │
│        ↓                          │         │
│     - Tools node (execution) ─────┘         │
│        ↓                                    │
│     - END (or interrupt)                    │
│                                             │
│  3. Middleware post-processing              │
│     - Result formatting                     │
└─────────────────────────────────────────────┘
```

---

## LangGraph Runtime Deep Dive

### State Machine Architecture

LangGraph models the agent as a **directed graph** where:
- **Nodes** = Processing steps (LLM calls, tool execution)
- **Edges** = Transitions between nodes (conditional or fixed)
- **State** = Shared context passed through the graph

```
┌──────────────────────────────────────────────────────────┐
│                   LangGraph Agent                         │
│                                                          │
│   START ──▶ __call_model__ ──▶ __should_continue__       │
│                  (Agent)          (Conditional)          │
│                    │                   │                 │
│                    │      ┌────────────┴───────────┐     │
│                    │      ▼                        ▼     │
│                    │   "tools"                   "end"   │
│                    │      │                              │
│                    │      ▼                              │
│                    │  __call_tools__                     │
│                    │    (Tools)                          │
│                    │      │                              │
│                    └──────┘ (loop back)                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Checkpointing with MemorySaver

**Why it matters**: Enables conversation continuity and replay.

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

# Each thread_id gets isolated state
config = {"configurable": {"thread_id": "user-session-1"}}

# First invocation
result1 = await agent.ainvoke({"messages": [...]}, config)

# Second invocation - remembers context
result2 = await agent.ainvoke({"messages": [...]}, config)

# State can be inspected/modified
state = await agent.aget_state(config)
await agent.aupdate_state(config, updates={...})
```

### InMemoryStore for Context

**Purpose**: Persist structured data between invocations.

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# Agent can read/write to store during execution
# Example: Caching webpage snapshots, user preferences
```

---

### State Flow Deep Dive

#### Initialization & Wiring

```python
# src/agents/facebook_surfer.py:56-57
self.store = InMemoryStore() if enable_memory else None
self.checkpointer = MemorySaver()

# Passed to create_deep_agent() - lines 210-218
agent = create_deep_agent(
    model=model_config,
    tools=self.tools,
    store=self.store,           # Cross-thread memory
    checkpointer=self.checkpointer,  # Thread checkpointing
    system_prompt=self.system_prompt,
    interrupt_on=interrupt_on,
    middleware=[skills_middleware],
)
```

#### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. INPUT                                                   │
│     task: "Post hello"                                      │
│     config: {"configurable": {"thread_id": "session-1"}}    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  2. CHECKPOINTER LOAD                                       │
│     MemorySaver.get(config)                                 │
│     → Loads checkpoint for thread_id="session-1"            │
│     → Returns previous state OR new state                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  3. STATE MACHINE LOOP                                      │
│     ┌──────────────────────────────────────────────┐        │
│     │  AGENT NODE (LLM)                            │        │
│     │  Input: Current state (messages, skills)     │        │
│     │  Process: LLM decides action                 │        │
│     │  Output: AIMessage with tool_calls           │        │
│     └──────────────────┬───────────────────────────┘        │
│                        │                                     │
│           ┌────────────┴────────────┐                        │
│           ▼                         ▼                        │
│     ┌─────────────┐          ┌───────────┐                  │
│     │  Tool Call  │          │   END     │                  │
│     │  Detected?  │          │ (Response)│                  │
│     └──────┬──────┘          └───────────┘                  │
│            │ YES                                               │
│            ▼                                                  │
│     ┌──────────────────────────────────────────────┐        │
│     │  TOOLS NODE (Execution)                      │        │
│     │  browser_get_snapshot() → Playwright exec    │        │
│     │  Returns: ToolMessage with observation       │        │
│     └──────────────────┬───────────────────────────┘        │
│                        │                                     │
│                        ▼                                     │
│              Update state.messages.append(                    │
│                AIMessage, ToolMessage                        │
│              )                                               │
│                        │                                     │
│                        └──► LOOP BACK TO AGENT                │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  4. CHECKPOINTER SAVE                                       │
│     After each node execution:                              │
│     MemorySaver.put(config, state)                          │
│     → Persists for thread_id="session-1"                    │
└─────────────────────────────────────────────────────────────┘
```

#### State Structure

```python
state = {
  "messages": [
    # 1. HumanMessage (iteration 0)
    {"role": "user", "content": "Post hello"},

    # 2. AIMessage (iteration 1)
    {"role": "assistant",
     "content": "",
     "tool_calls": [
       {"id": "call_123",
        "name": "browser_get_snapshot"}
     ]},

    # 3. ToolMessage (iteration 1)
    {"role": "tool",
     "tool_call_id": "call_123",
     "content": "- button \"Post\" [ref=e50]\n..."},

    # 4. AIMessage (iteration 2)
    {"tool_calls": [{"name": "browser_click", ...}]},

    # 5. ToolMessage (iteration 2)
    ...

    # N. AIMessage (final)
    {"role": "assistant",
     "content": "Done! Posted hello."}
  ]
}
```

#### Persistence Comparison

| Component | Scope | Purpose | Usage in Code |
|-----------|-------|---------|---------------|
| **MemorySaver** | Per `thread_id` | Conversation state | `config={"configurable": {"thread_id": "..."}}` |
| **InMemoryStore** | Cross-thread | Structured context | Optional, not actively used yet |

**MemorySaver Example:**
```python
# Same thread_id = continuous conversation
await agent.invoke("Post hello", thread_id="session-1")
await agent.invoke("Check if posted", thread_id="session-1")  # Remembers!

# Different thread = fresh context
await agent.invoke("New task", thread_id="session-2")  # No memory
```

**InMemoryStore Potential Use:**
```python
# Could store across threads:
# - User preferences (privacy settings)
# - Learned selectors (login button locators)
# - Cached snapshots (page templates)
```

---

### Streaming Modes

The implementation supports three streaming approaches:

```python
# 1. Values mode - State snapshots
async for event in agent.astream(inputs, config, stream_mode="values"):
    print(event["messages"][-1])

# 2. Updates mode - Incremental changes
async for event in agent.astream(inputs, config, stream_mode="updates"):
    print(event)

# 3. Events mode - Detailed debugging
async for event in agent.astream_events(inputs, config, version="v2"):
    print(event["event"], event["name"], event["data"])
```

---

## LangChain Tool System

### StructuredTool Architecture

Tools are defined using Pydantic models for type-safe arguments:

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

# 1. Define argument schema
class ClickArgs(BaseModel):
    ref: str | None = Field(None, description="Element ref from snapshot")
    selector: str | None = Field(None, description="CSS/role selector")
    force: bool = Field(False, description="Bypass overlays")

# 2. Implement tool function (async for Playwright)
async def browser_click(ref: str | None, selector: str | None, force: bool) -> str:
    page = get_current_async_page()
    element = page.locator(f"[ref={ref}]" if ref else selector)
    await element.click(force=force)
    return "Clicked successfully"

# 3. Create StructuredTool
tool = StructuredTool.from_function(
    coroutine=browser_click,  # Use 'coroutine' for async
    name="browser_click",
    description="Click on an element",
    args_schema=ClickArgs,
)
```

### Tool Registry Pattern

Centralized registration ensures consistency:

```python
# src/tools/registry.py
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}
    
    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec
    
    def get_all(self) -> list[StructuredTool]:
        return [spec.to_langchain_tool() for spec in self._tools.values()]

# Auto-register all tools
def register_all_tools() -> ToolRegistry:
    registry = ToolRegistry()
    
    # Navigation tools
    registry.register(ToolSpec(
        name="browser_navigate",
        category=ToolCategory.navigation,
        description="Navigate to URL",
        func=browser_navigate,
        args_schema=NavigateArgs,
    ))
    # ... more tools
    
    return registry
```

### Async/Sync Detection

Tools are intelligently bound based on function type:

```python
import inspect

def to_langchain_tool(self) -> StructuredTool:
    if inspect.iscoroutinefunction(self.func):
        return StructuredTool.from_function(
            coroutine=self.func,  # Async path
            name=self.name,
            args_schema=self.args_schema,
        )
    else:
        return StructuredTool.from_function(
            func=self.func,       # Sync path
            name=self.name,
            args_schema=self.args_schema,
        )
```

---

## Agent Success Patterns

### 1. Comprehensive System Prompt

The system prompt enforces a structured workflow:

```python
"""
## MANDATORY WORKFLOW (Observe → Think → Act → Verify)

**Step 1: OBSERVE** - Get FRESH snapshot
browser_get_snapshot()

**Step 2: THINK** - List elements before clicking
# CURRENT SNAPSHOT shows:
# - button "Close" [ref=e31] ← NOT what I want
# - button "Friends" [ref=e42] ← Privacy button!

**Step 3: ACT** - Use ref from THIS snapshot
browser_click(ref="e42", force=True)

**Step 4: VERIFY** - Get NEW snapshot (refs are stale!)
browser_get_snapshot()
"""
```

### 2. Ref-Based Element Targeting

The ARIA snapshot system provides reliable element identification:

```yaml
# browser_get_snapshot() output
- navigation "Facebook":
  - link "Home" [ref=e0]
  - button "Search" [ref=e1]
- main:
  - button "What's on your mind?" [ref=e15]
  - dialog "Create post":
    - textbox [ref=e20]
    - button "Public" [ref=e21]
    - button "Post" [ref=e25]
```

**Why refs work:**
- Unique per element in snapshot
- Accessible name + role for disambiguation
- Forces agent to observe before acting

### 3. Skill-Injected Domain Knowledge

Skills provide tested workflows without code changes:

```yaml
# skills/facebook-automation/SKILL.md
---
name: facebook-automation
allowed-tools: browser_navigate browser_click browser_type ...
---

## Critical Rules
### ⚠️ REFS BECOME STALE AFTER EVERY ACTION

## Core Workflows
### Create Post with Privacy Setting
1. browser_navigate(url="https://www.facebook.com")
2. browser_get_snapshot()
3. browser_click(selector='button=What's on your mind', force=True)
4. browser_get_snapshot()  # Get fresh refs!
...
```

### 4. Human-in-the-Loop (HITL) Integration

Sensitive actions can require human approval:

```python
interrupt_on = {
    "browser_type": {"allowed_decisions": ["approve", "edit", "reject"]},
    "browser_click": {"allowed_decisions": ["approve", "edit", "reject"]},
    "browser_submit_form": {"allowed_decisions": ["approve", "edit", "reject"]},
}

agent = create_deep_agent(..., interrupt_on=interrupt_on)
```

---

## Skills Middleware System

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Skills Middleware                       │
│                                                          │
│  ┌────────────────────┐    ┌─────────────────────────┐   │
│  │ FilesystemBackend  │───▶│    skills/              │   │
│  │ (root_dir)         │    │    ├── facebook-auto/   │   │
│  └────────────────────┘    │    │   └── SKILL.md     │   │
│           │                │    └── other-skill/     │   │
│           ▼                │        └── SKILL.md     │   │
│  ┌────────────────────┐    └─────────────────────────┘   │
│  │ SkillsMiddleware   │                                  │
│  │ sources=["/..."]   │                                  │
│  └────────────────────┘                                  │
│           │                                              │
│           ▼                                              │
│  Skill content injected into agent context               │
└──────────────────────────────────────────────────────────┘
```

### Skill File Format

```yaml
---
name: skill-name
description: What this skill provides
allowed-tools: tool1 tool2 tool3
---

# Skill Content (Markdown)

## When to Use
- Condition 1
- Condition 2

## Critical Rules
...

## Workflows
### Workflow Name
1. Step 1
2. Step 2
```

### Runtime Injection

```python
# Agent receives skill content in context
# This happens automatically via middleware

# Equivalent to adding to system prompt:
"""
## SKILLS CONTEXT
When you receive a SKILL file, it provides:
- Tested selectors for that domain
- Complete workflows with exact steps
- Known UI quirks and workarounds
FOLLOW SKILL WORKFLOWS EXACTLY.
"""
```

---

## Session & State Management

### FacebookSessionManager

**Global session pattern** for tool access:

```python
# src/session/__init__.py

_global_session: FacebookSessionManager | None = None

def set_global_session(session: FacebookSessionManager) -> None:
    global _global_session
    _global_session = session

def get_current_async_page() -> AsyncPage | None:
    if _global_session is None:
        return None
    return _global_session.async_page
```

**Why global?** LangGraph tasks run in separate contexts where `ContextVar` doesn't propagate. The global pattern ensures tools can always access the browser page.

### Session Lifecycle

```python
@asynccontextmanager
async def async_init_session(login: bool = False, profile: str = "./profiles/facebook"):
    session = FacebookSessionManager(profile_dir=Path(profile))
    
    async with async_playwright() as p:
        if session._has_saved_session() and not login:
            context, page, restored = await session._restore_session_async(p.chromium)
        else:
            context, page, restored = await session._create_new_session_async(p.chromium)
        
        set_global_session(session)  # Make available to tools
        
        try:
            yield session
        finally:
            await session.close_async()
            set_global_session(None)
```

### Persistence Layer

| File | Contents | Purpose |
|------|----------|---------|
| `profiles/facebook/cookies.json` | Session cookies | Maintain login |
| `profiles/facebook/state.json` | localStorage, sessionStorage | App state |
| Browser profile directory | IndexedDB, cache | Full context |

---

## Why This Implementation Succeeds

### 1. **Separation of Concerns**

```
LangChain (Tools)     → HOW to click, type, navigate
LangGraph (State)     → WHEN to execute, memory
DeepAgents (Glue)     → Wire everything together
Skills (Knowledge)    → WHAT workflow to follow
Playwright (Engine)   → Browser execution
```

### 2. **Observe-Think-Act-Verify Loop**

The system prompt enforces discipline:
- Must call `browser_get_snapshot()` before acting
- Must list visible elements before clicking
- Must verify with snapshot before saying "done"
- Refs become stale after every action (forced re-observation)

### 3. **Skill-Driven Workflows**

- Tested selectors stored externally
- Workflows updated without code changes
- Domain experts can contribute without Python knowledge
- Multiple skill domains can coexist

### 4. **Robust Session Management**

- Persistent login via cookies/storage state
- SingletonLock cleanup prevents Chrome conflicts
- HITL login fallback for expired sessions
- Stealth browser args for anti-detection

### 5. **Async-First Architecture**

- All browser tools are async
- LangGraph natively supports async execution
- Proper async/sync detection in tool binding
- Non-blocking streaming for real-time feedback

### 6. **Memory Across Sessions**

- `MemorySaver` persists conversation state
- Thread IDs enable multi-session continuity
- State inspection/modification for debugging
- `InMemoryStore` for structured context

---

## Quick Reference

### Running the Agent

```bash
# Login (first time)
python -m facebook-surfer login

# Run task
python -m facebook-surfer run "Post hello world to Facebook"

# Interactive mode with streaming
python -m facebook-surfer run --stream

# Debug mode (full event output)
python -m facebook-surfer run --debug
```

### Key Code Locations

| File | Purpose |
|------|---------|
| `src/agents/facebook_surfer.py` | Agent definition with DeepAgents |
| `src/tools/registry.py` | Tool registration (22+ tools) |
| `src/session/__init__.py` | Session management (724 lines) |
| `src/main.py` | CLI entry point |
| `skills/facebook-automation/SKILL.md` | Domain knowledge |

### Testing

```bash
pytest tests/ -v
pytest tests/test_facebook_surfer.py  # Agent tests
pytest tests/test_interaction_tools.py  # Tool tests
```
