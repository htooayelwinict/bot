# System Architecture

## Overview

Facebook Surfer is an AI-powered Facebook automation agent built on a modern agentic AI stack combining **DeepAgents**, **LangChain**, and **LangGraph** with Playwright browser automation and adaptive learning via RAG-based trajectory storage.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User CLI                                   │
│  (login / run [--stream] [--debug] [--enable-metrics] [--enable-planning]) │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Optional: Planning Agent                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  PlanningAgent (if --enable-planning)                            │  │
│  │  - Retrieve similar workflows from Qdrant                        │  │
│  │  - Generate success plan with guardrails                         │  │
│  │  - Inject plan into execution context                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FacebookSurferAgent                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  DeepAgents + LangGraph Runtime                                   │  │
│  │  - create_deep_agent() factory function                           │  │
│  │  - MemorySaver (LangGraph checkpointer)                           │  │
│  │  - InMemoryStore (context persistence)                            │  │
│  │  - SkillsMiddleware (domain guidance)                             │  │
│  │  - TrajectoryCallback (if --enable-metrics)                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  LangChain StructuredTool Registry                      │
│  (auto-discovers all tools from src/tools/ modules)                    │
│  - Pydantic validation for all tool arguments                          │
│  - Async/sync detection for proper tool binding                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Global Session Context                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  FacebookSessionManager                                           │  │
│  │  - Persistent context in ./profiles/facebook/                     │  │
│  │  - HITL login with 3-minute timeout                               │  │
│  │  - Cookie/storage state persistence                               │  │
│  │  - SingletonLock cleanup                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Playwright                                      │
│              (Chromium browser with stealth args)                       │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           │ (after execution)
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Learning System (if --enable-metrics)                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  1. TrajectoryCallback captures all tool calls                   │  │
│  │  2. Scoring: 40% success, 20% latency, 20% tokens, 20% outcome  │  │
│  │  3. PII Redaction (emails, phones, SSN, API keys)                │  │
│  │  4. Qdrant Storage with OpenAI embeddings                       │  │
│  │  5. ReflectionAgent analyzes patterns                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## DeepAgents + LangGraph Integration

### Agent Creation

The `FacebookSurferAgent` uses the **DeepAgents** framework which internally leverages **LangGraph** for stateful agent orchestration:

```python
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

class FacebookSurferAgent:
    def __init__(self, model="openrouter/mistralai/devstral-2512:free", ...):
        # LangGraph persistence components
        self.store = InMemoryStore()       # Context persistence
        self.checkpointer = MemorySaver()  # Conversation state
        
        # Skills middleware for domain guidance
        skills_backend = FilesystemBackend(root_dir="./skills")
        skills_middleware = SkillsMiddleware(
            backend=skills_backend,
            sources=["/facebook-automation/"],
        )
        
        # Create agent via DeepAgents factory
        self.agent = create_deep_agent(
            model=model_config,
            tools=self.tools,
            store=self.store,
            checkpointer=self.checkpointer,
            system_prompt=self.system_prompt,
            interrupt_on=interrupt_on,  # HITL config
            middleware=[skills_middleware],
        )
```

### Key Components

| Component | Library | Purpose |
|-----------|---------|---------|
| `create_deep_agent()` | DeepAgents | Factory for LangGraph-based agent |
| `MemorySaver` | LangGraph | Checkpoints conversation state across threads |
| `InMemoryStore` | LangGraph | Persists context between agent invocations |
| `SkillsMiddleware` | DeepAgents | Injects domain-specific guidance into context |
| `FilesystemBackend` | DeepAgents | Loads skill files from `skills/` directory |
| `ChatOpenAI` | LangChain | LLM integration (OpenRouter/OpenAI compatible) |
| `StructuredTool` | LangChain | Tool definitions with Pydantic schemas |

---

## Shared Agent Utilities

All agent modules use shared utilities from [`src/agents/utils.py`](src/agents/utils.py) to avoid code duplication.

### `create_openrouter_llm()`

Centralized OpenRouter ChatOpenAI configuration:

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

**Features:**
- Strips `openrouter/` prefix automatically
- Configures OpenRouter base URL and headers
- Supports extra body parameters (e.g., reasoning config)

### `parse_json_with_fallback()`

Robust JSON parsing from LLM responses:

```python
from src.agents.utils import parse_json_with_fallback

result = parse_json_with_fallback(
    llm_response,
    fallback={"error": "parse failed", "raw_text": llm_response}
)
```

**Handles:**
1. Direct JSON parsing
2. Markdown code blocks (` ```json ... ``` `)
3. Fallback to provided default or `{"raw_text": text}`

### Usage Pattern

All agents follow this pattern:

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

---

## LangGraph Runtime

### State Machine Architecture

LangGraph powers the agent's execution as a **stateful graph**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   START     │────▶│   AGENT     │────▶│   TOOLS     │
│             │     │ (LLM Node)  │     │ (Execution) │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
                           │◀──────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    END      │
                    │ (or HITL)   │
                    └─────────────┘
```

**Graph Nodes:**
- **Agent Node**: LLM decides action based on state and system prompt
- **Tools Node**: Executes selected tool, returns observation
- **Conditional Edges**: Route based on tool results or HITL requirements

### Streaming Modes

The agent supports multiple streaming modes via LangGraph:

```python
# Basic streaming (state updates)
async for event in agent.stream(task, thread_id):
    print(event)

# Detailed event streaming (debugging)
async for event in agent.stream_events(task, thread_id):
    # Shows: node execution, tool calls, LLM activity
    print(event["event"], event["name"])
```

### Thread-Based Memory

LangGraph's `MemorySaver` enables conversation persistence:

```python
# Same thread_id = continuous conversation
result1 = await agent.invoke("Post hello", thread_id="session-1")
result2 = await agent.invoke("Check if posted", thread_id="session-1")

# Different thread = fresh context
result3 = await agent.invoke("New task", thread_id="session-2")
```

---

## LangChain Tool Integration

### Tool Registry Pattern

All browser automation tools use LangChain's `StructuredTool` with Pydantic validation:

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class ClickArgs(BaseModel):
    ref: str | None = Field(None, description="Element ref from snapshot")
    selector: str | None = Field(None, description="CSS/role selector")
    force: bool = Field(False, description="Force click through overlays")

# Convert to LangChain tool
tool = StructuredTool.from_function(
    coroutine=browser_click,  # Async function
    name="browser_click",
    description="Click on an element",
    args_schema=ClickArgs,
)
```

### Tool Categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **Navigation** | `browser_navigate`, `browser_navigate_back`, `browser_screenshot`, `browser_get_page_info` | URL navigation and page info |
| **Interaction** | `browser_click`, `browser_type`, `browser_hover`, `browser_press_key`, `browser_select_option` | UI interactions |
| **Forms** | `browser_fill_form`, `browser_get_form_data`, `browser_submit_form` | Form handling |
| **Utilities** | `browser_wait`, `browser_evaluate`, `browser_get_snapshot`, `browser_get_network_requests`, `browser_get_console_messages` | Page utilities |
| **Browser** | `browser_tabs`, `browser_resize`, `browser_handle_dialog`, `browser_reload`, `browser_close` | Browser control |

### Async Tool Handling

Tools are registered with async detection for proper LangChain binding:

```python
if inspect.iscoroutinefunction(func):
    # Async tools use 'coroutine' parameter
    return StructuredTool.from_function(
        coroutine=func, name=name, ...
    )
else:
    # Sync tools use 'func' parameter
    return StructuredTool.from_function(
        func=func, name=name, ...
    )
```

---

## Skills Middleware

### Purpose

Injects domain-specific guidance into the agent's context at runtime, enabling site-specific workflows without code changes.

### Implementation

```python
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware

# Skills loaded from filesystem
skills_backend = FilesystemBackend(
    root_dir=str(Path(__file__).parent.parent.parent / "skills")
)

skills_middleware = SkillsMiddleware(
    backend=skills_backend,
    sources=["/facebook-automation/"],  # Skill paths
)
```

### Skill File Structure

```yaml
# skills/facebook-automation/SKILL.md
---
name: facebook-automation
description: Facebook automation workflows
allowed-tools: browser_navigate browser_click browser_type ...
---

# Critical Rules
## REFS BECOME STALE AFTER EVERY ACTION...

## Core Workflows
### Create Post with Privacy Setting...
```

---

## Request Flow

```
User Task → CLI → async_init_session()
                  │
                  ▼
              FacebookSessionManager.get_or_create_session_async()
                  │
                  ├─── 📂 Restore from profiles/facebook/ (cookies, state)
                  │    or
                  └─── 🔑 HITL login (3-minute timeout)
                  │
                  ▼
              set_global_session(session)
                  │
                  ├─── 🔄 IF --enable-planning:
                  │      PlanningAgent.craft_success_plan()
                  │        ├─── Qdrant: retrieve_similar_trajectories()
                  │        ├─── LLM: generate structured plan
                  │        └─── Inject plan into agent context
                  │
                  ▼
              FacebookSurferAgent(model, ...)
                  │
                  ├─── 📋 register_all_tools() → ToolRegistry
                  ├─── 🧠 MemorySaver + InMemoryStore
                  ├─── 📚 SkillsMiddleware → load SKILL.md
                  └─── 📊 TrajectoryCallback (if --enable-metrics)
                  │
                  ▼
              agent.invoke(task, thread_id)
                  │
                  ▼
             ┌────────────────────────────────────┐
             │  LangGraph State Machine           │
             │                                    │
             │  1. Agent Node (LLM reasoning)     │
             │     ↓                              │
             │  2. Tool selection                 │
             │     ↓                              │
             │  3. Tools Node (Playwright exec)   │
             │     ↓                              │
             │  4. Observation → back to Agent    │
             │     or                             │
             │  5. Task complete → END            │
             └────────────────────────────────────┘
                  │
                  ├─── 📊 IF --enable-metrics:
                  │      TrajectoryCallback.on_tool_end()
                  │        ├─── Capture: tool, input, output, timing
                  │        ├─── Score trajectory (40/20/20/20)
                  │        ├─── PII redaction
                  │        ├─── Qdrant: store_trajectory()
                  │        └─── ReflectionAgent: analyze patterns
                  │
                  ▼
              Final Response (verified by snapshot)
```

---

## Session Management

### FacebookSessionManager

**Singleton Pattern**: Global session/page context via module-level functions:

```python
# Set active session
set_global_session(session)

# Get page for tool execution
page = get_current_async_page()
```

**Context Manager Pattern**: Session lifecycle management:

```python
async with async_init_session(login=False) as session:
    agent = FacebookSurferAgent(model=model)
    await agent.invoke(task)
```

### Human-in-the-Loop Login

1. Navigate to facebook.com
2. Start 3-minute timer with progress polling
3. User manually completes login in visible browser
4. Poll `LOGGED_IN_SELECTORS` to detect success
5. Save `cookies.json` and `state.json` to profile

---

## State Persistence

| Location | Content | Purpose |
|----------|---------|---------|
| `profiles/facebook/cookies.json` | Session cookies | Login persistence |
| `profiles/facebook/state.json` | Storage state | LocalStorage, SessionStorage |
| `profiles/facebook/` | Browser profile | IndexedDB, cache |
| Thread checkpoint (MemorySaver) | Conversation history | Memory across sessions |

---

## Security Considerations

- **Stealth Browser Args**: Anti-detection (`--disable-blink-features=AutomationControlled`)
- **Human-like Timing**: Random delays between actions
- **Force Clicks**: `force=True` to bypass overlay detection
- **Profile Isolation**: Each agent instance gets isolated context

---

## Error Recovery

- **Session Validation**: Check `LOGGED_IN_SELECTORS` on restore
- **Retry Logic**: 3 attempts for Facebook navigation
- **Graceful Degradation**: Continue on non-critical tool failures
- **Interrupt Handling**: HITL can pause for human input

---

## Dependencies (pyproject.toml)

```toml
[project.optional-dependencies]
agent = [
    "deepagents>=0.1.0",      # Agent framework
    "langchain>=0.3.0",       # LLM orchestration
    "langchain-openai>=0.2.0",# OpenAI/OpenRouter integration
    "langgraph>=0.2.0",       # Stateful agent graphs
    "openai>=1.54.0",         # API client
]
memory = [
    "qdrant-client>=1.12.0",  # Vector database
]
```

---

## Learning & Planning System

### Overview

The agent learns from past executions via trajectory capture, scoring, and RAG-based planning:

```
Task → PlanningAgent (if enabled) → ExecutionAgent → TrajectoryCallback
                                             ↓
                                    Scoring → PII Redaction → Qdrant Storage
                                                                        ↓
                                                    Semantic Retrieval for Future Tasks
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Trajectory Capture** | [`src/metrics/trajectory_callback.py`](../src/metrics/trajectory_callback.py) | LangChain callback that records all tool calls |
| **Scoring** | [`src/metrics/scoring.py`](../src/metrics/scoring.py) | Multi-dimensional scoring (40/20/20/20) |
| **PII Redaction** | [`src/metrics/pii_redaction.py`](../src/metrics/pii_redaction.py) | Removes emails, phones, SSN, API keys |
| **Qdrant Storage** | [`src/storage/trajectory_store.py`](../src/storage/trajectory_store.py) | Vector DB with OpenAI embeddings |
| **Planning Agent** | [`src/agents/planner.py`](../src/agents/planner.py) | Generates plans from similar workflows |
| **Reflection Agent** | [`src/agents/reflection.py`](../src/agents/reflection.py) | Analyzes trajectories for patterns |

### Data Flow

1. **Execution** with `--enable-metrics`:
   - `TrajectoryCallbackHandler` intercepts all tool calls
   - Records: tool name, input, output, success/failure, latency, tokens
   - Thread-safe storage

2. **Scoring** (weighted formula):
   ```
   score = 0.4 * tool_success_rate
         + 0.2 * (30s / actual_latency)
         + 0.2 * (5000 / actual_tokens)
         + 0.5 * outcome_match
   ```

3. **PII Redaction** (before embedding):
   - Emails, phones, SSN, credit cards, API keys
   - Security critical: applied BEFORE embeddings

4. **Qdrant Storage**:
   - Local persistent storage in `./qdrant_db/`
   - OpenAI `text-embedding-3-small` embeddings
   - Cosine similarity search

5. **RAG-Based Planning** (`--enable-planning`):
   - Retrieves top-3 similar workflows
   - `PlanningAgent` generates structured plan:
     ```json
     {
       "analysis": "...",
       "suggested_plan": ["1. ...", "2. ..."],
       "working_selectors": {"element": "text/aria cue"},
       "avoid_patterns": ["pattern that failed"],
       "guardrails": ["fail >3x -> switch strategy"]
     }
     ```
   - Plan injected into agent context

### CLI Flags

| Flag | Purpose |
|------|---------|
| `--enable-metrics` | Capture and store trajectories |
| `--enable-planning` | Retrieve similar workflows and generate plan |
| `--enable-metrics --enable-planning` | Full learning loop (plan + store) |

Requires `OPENAI_API_KEY` in `config/.env`.
