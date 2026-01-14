# Research: DeepAgents Framework

**Date:** 2025-01-14
**Context:** Python-based Facebook automation agent using Playwright
**Stack:** DeepAgents 0.3.5, LangChain, LangGraph, Python 3.11+

## Executive Summary

DeepAgents is a high-level agent framework built on top of LangChain and LangGraph. It provides pre-configured agents with built-in middleware for planning, filesystem access, memory, skills, and subagents. The framework simplifies building autonomous agents by providing sensible defaults while remaining highly customizable.

## Key Findings

### 1. Core Concepts

**What is DeepAgents?**
- High-level agent framework built on LangChain/LangGraph
- Provides pre-built middleware stack for common agent patterns
- Defaults to Claude Sonnet 4.5 (20250929) with 20K max tokens
- Version: 0.3.5 (installed in project)

**Relationship to LangChain/LangGraph:**
- `create_agent()` from LangChain agents (core agent creation)
- `CompiledStateGraph` from LangGraph (state management)
- Middleware system extends LangChain's AgentMiddleware
- Uses LangGraph checkpointing and store for persistence

### 2. API Reference

#### `create_deep_agent()` Function

**Location:** `deepagents.graph.create_deep_agent()`

**Signature:**
```python
def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph
```

**Default Behavior:**
- Model: `claude-sonnet-4-5-20250929` (if None)
- System prompt: BASE_AGENT_PROMPT + custom prompt
- Tools: `write_todos`, `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute`, `task` (subagent spawner)
- Recursion limit: 1000

#### Available Middleware (Default Stack)

The framework automatically adds middleware in this order:

1. **TodoListMiddleware** - Todo list management
2. **MemoryMiddleware** (if `memory` param) - Load AGENTS.md files
3. **SkillsMiddleware** (if `skills` param) - Load skills from filesystem
4. **FilesystemMiddleware** - File operations (ls, read, write, edit, glob, grep)
5. **SubAgentMiddleware** - Subagent spawning with `task` tool
6. **SummarizationMiddleware** - Context compression when approaching token limits
7. **AnthropicPromptCachingMiddleware** - Prompt caching for Anthropic models
8. **PatchToolCallsMiddleware** - Tool call patching
9. **Custom middleware** (from `middleware` param)
10. **HumanInTheLoopMiddleware** (if `interrupt_on` param)

#### Checkpointer and Store Options

**Checkpointers** (state persistence):
- `MemorySaver` from `langgraph.checkpoint.memory` (in-memory)
- `SqliteSaver` from `langgraph.checkpoint.sqlite` (persistent)
- Custom checkpointers implementing `Checkpointer` protocol

**Store** (cross-thread memory):
- `InMemoryStore` from `langgraph.store.memory` (default)
- `PostgresStore` from `langgraph.store.postgres` (persistent)
- Required if backend uses `StoreBackend`

#### Stream Modes and Events

**Stream Modes** (via `astream()`):
- `"values"` - Stream full state after each node (default for values)
- `"updates"` - Stream only state updates from each node
- `"debug"` - Debug information

**Event Streaming** (via `astream_events()`):
```python
async for event in agent.astream_events(input, config, version="v2"):
    # event structure:
    {
        "event": str,  # Event type
        "name": str,   # Node/tool name
        "data": dict,  # Event-specific data
        "metadata": dict,
    }
```

**Event Types:**
- `on_chain_start` / `on_chain_end` - Node execution
- `on_tool_start` / `on_tool_end` - Tool calls
- `on_llm_start` / `on_llm_end` - LLM calls
- `on_chat_model_start` / `on_chat_model_end` - Chat model calls

### 3. Configuration

#### Custom LLM Configs

**ChatOpenAI with custom base_url:**
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="mistralai/devstral-2512:free",
    temperature=0.0,
    base_url="https://openrouter.ai/api/v1",
    api_key="your-api-key",
    default_headers={
        "HTTP-Referer": "https://github.com/your-repo",
        "X-Title": "Your App Name",
    },
)

agent = create_deep_agent(model=model, ...)
```

**String model specification:**
```python
# Uses LangChain's init_chat_model
agent = create_deep_agent(
    model="openai:gpt-4o",
    # or
    model="anthropic:claude-sonnet-4-5-20250929",
)
```

#### Model Configuration Options

- `max_tokens` - Default 20000 for Claude Sonnet
- `temperature` - Response randomness (0.0-1.0)
- `base_url` - Custom API endpoint
- `api_key` - API authentication
- `default_headers` - Custom HTTP headers

#### Tool Registration

**Direct tool list:**
```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """Tool description."""
    return f"Result: {param}"

agent = create_deep_agent(
    tools=[my_tool],
    ...
)
```

**From registry (project pattern):**
```python
from src.tools.registry import register_all_tools

registry = register_all_tools()
tools = registry.get_all()

agent = create_deep_agent(tools=tools, ...)
```

### 4. Streaming & Debugging

#### Stream Modes Available

**`astream()` - Values mode:**
```python
async for state in agent.astream(input, config, stream_mode="values"):
    # Full agent state after each node
    print(state["messages"][-1].content)
```

**`astream()` - Updates mode:**
```python
async for update in agent.astream(input, config, stream_mode="updates"):
    # Only updates from each node
    print(update)
```

**`astream_events()` - Detailed events:**
```python
async for event in agent.astream_events(input, config, version="v2"):
    event_type = event["event"]
    event_name = event["name"]
    
    if "tool" in event_type:
        print(f"Tool: {event_name}")
        print(f"Data: {event['data']}")
```

#### Event Structure

**Tool Call Event:**
```python
{
    "event": "on_tool_start",
    "name": "browser_click",
    "data": {
        "input": {"ref": "e42", "force": True},
    },
    "metadata": {...},
}
```

**LLM Call Event:**
```python
{
    "event": "on_chat_model_start",
    "name": "agent",
    "data": {
        "input": {
            "messages": [...],
        }
    },
}
```

#### Debugging Tips

1. **Enable debug mode:**
```python
agent = create_deep_agent(..., debug=True)
```

2. **Use astream_events for tool inspection:**
```python
async for event in agent.astream_events(..., version="v2"):
    if "tool" in event["event"]:
        print(f"Tool: {event['name']}, Input: {event['data'].get('input')}")
```

3. **Check agent state:**
```python
state = await agent.aget_state(config)
print(state.next)  # Pending nodes
print(state.tasks)  # Interrupted tasks
```

### 5. Skills System

#### How SkillsMiddleware Works

**Progressive Disclosure Pattern:**
1. Loads skill metadata (name, description, path) from SKILL.md files
2. Injects skill list into system prompt
3. Agent reads full skill content when needed (lazy loading)
4. Skills can include helper files (scripts, configs)

#### Load Skills from Filesystem

**Directory structure:**
```
skills/
└── facebook-automation/
    ├── SKILL.md          # Required: YAML frontmatter + markdown
    └── helpers.py        # Optional: supporting files
```

**SKILL.md format:**
```markdown
---
name: facebook-automation
description: Domain-specific workflows for Facebook automation
license: MIT
---

# Facebook Automation Skill

## When to Use
- User asks to automate Facebook interactions
- Need specific selectors for Facebook UI

## Workflows
...
```

#### Skill File Format

**YAML frontmatter fields:**
- `name` (required) - Skill identifier, max 64 chars, lowercase + hyphens
- `description` (required) - What skill does, max 1024 chars
- `license` (optional) - License name or reference
- `compatibility` (optional) - Environment requirements
- `metadata` (optional) - Key-value pairs
- `allowed-tools` (optional) - Pre-approved tools list

**Validation rules:**
- Name must match parent directory name
- Name: lowercase alphanumeric, single hyphens between segments
- Max 10MB file size (DoS protection)

#### Configuration Examples

**FilesystemBackend (disk):**
```python
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware

backend = FilesystemBackend(root_dir="/path/to/skills")
middleware = SkillsMiddleware(
    backend=backend,
    sources=["/facebook-automation/", "/web-research/"],
)
```

**StateBackend (in-memory):**
```python
from deepagents.middleware.skills import SkillsMiddleware

middleware = SkillsMiddleware(
    backend=lambda rt: StateBackend(rt),
    sources=["/skills/user/", "/skills/project/"],
)
```

**With create_deep_agent:**
```python
agent = create_deep_agent(
    skills=["/skills/facebook-automation/"],
    backend=FilesystemBackend(root_dir="./skills"),
    ...
)
```

### 6. Best Practices

#### Patterns for Building Agents

**1. Custom model configuration:**
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="your-model",
    base_url="https://api.example.com",
    api_key=os.getenv("API_KEY"),
)

agent = create_deep_agent(model=model, tools=tools)
```

**2. Add custom middleware:**
```python
from langchain.agents.middleware import AgentMiddleware

class CustomMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        # Pre-processing
        response = handler(request)
        # Post-processing
        return response

agent = create_deep_agent(
    middleware=[CustomMiddleware()],
    ...
)
```

**3. Subagents for complex tasks:**
```python
from deepagents import SubAgent

subagents = [
    SubAgent(
        name="researcher",
        description="Conduct web research",
        system_prompt="You are a researcher...",
        tools=[search_tool, scrape_tool],
    ),
]

agent = create_deep_agent(subagents=subagents, ...)
```

**4. Human-in-the-loop for sensitive actions:**
```python
agent = create_deep_agent(
    interrupt_on={
        "browser_click": {"allowed_decisions": ["approve", "reject"]},
        "browser_type": {"allowed_decisions": ["approve", "edit"]},
    },
    ...
)
```

#### Performance Considerations

- **Summarization**: Automatically compresses context at 85% of max tokens
- **Prompt caching**: AnthropicPromptCachingMiddleware reduces API costs
- **Subagents**: Isolate expensive operations to reduce main context
- **Skill lazy loading**: Only reads skill content when needed

#### Security Considerations

- **FilesystemBackend**: Allows full filesystem access (use sandbox or HIL)
- **Execute tool**: Only available with `SandboxBackendProtocol`
- **Interrupt on sensitive tools**: Add HIL for dangerous operations
- **Skill validation**: 10MB max file size, path validation

## Installation

```bash
# Base dependencies
pip install -e .

# With DeepAgents/agent support
pip install -e ".[agent]"

# With ChromaDB memory (Phase 4)
pip install -e ".[memory]"

# Development tools
pip install -e ".[dev]"
```

## Project Integration

The project uses DeepAgents for:
- Browser automation agent (FacebookSurferAgent)
- Skills middleware for domain-specific workflows
- Playwright tools for web interaction
- OpenRouter integration for custom LLM endpoints

See: `src/agents/facebook_surfer.py`

## References

- DeepAgents source: `.venv/lib/python3.14/site-packages/deepagents/`
- LangChain agents: https://python.langchain.com/docs/langgraph
- LangGraph: https://langchain-ai.github.io/langgraph
- Agent Skills spec: https://agentskills.io/specification
