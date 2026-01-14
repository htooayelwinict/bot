# DeepAgents Quick Reference

## Create Agent

```python
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

# Custom model
model = ChatOpenAI(
    model="mistralai/devstral-2512:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt="You are a helpful agent",
    checkpointer=MemorySaver(),
    store=InMemoryStore(),
)
```

## Stream Execution

```python
# Values mode (full state)
async for state in agent.astream(input, config, stream_mode="values"):
    print(state["messages"][-1].content)

# Updates mode (deltas only)
async for update in agent.astream(input, config, stream_mode="updates"):
    print(update)

# Events mode (detailed debugging)
async for event in agent.astream_events(input, config, version="v2"):
    if "tool" in event["event"]:
        print(f"Tool: {event['name']}")
```

## Skills System

```python
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.backends.filesystem import FilesystemBackend

# Directory structure
# skills/
# └── my-skill/
#     └── SKILL.md

backend = FilesystemBackend(root_dir="./skills")
middleware = SkillsMiddleware(
    backend=backend,
    sources=["/my-skill/"],
)

agent = create_deep_agent(
    middleware=[middleware],
    ...
)
```

## Human-in-the-Loop

```python
agent = create_deep_agent(
    interrupt_on={
        "dangerous_tool": {"allowed_decisions": ["approve", "reject"]},
    },
    ...
)

# Check for interrupts
state = await agent.aget_state(config)
if state.next:
    # Interrupted - waiting for human input
    await agent.aupdate_state(config, command="approve")
```

## Subagents

```python
from deepagents import SubAgent

subagents = [
    SubAgent(
        name="researcher",
        description="Conduct research",
        system_prompt="You are a researcher",
        tools=[search_tool],
    ),
]

agent = create_deep_agent(subagents=subagents, ...)
```

## Common Patterns

```python
# Custom middleware
class MyMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        # Pre-process
        response = handler(request)
        # Post-process
        return response

# Memory middleware
from deepagents import MemoryMiddleware
agent = create_deep_agent(
    memory=["~/.deepagents/AGENTS.md"],
    backend=FilesystemBackend(root_dir="/"),
)

# State inspection
state = await agent.aget_state(config)
print(state.next)  # Pending nodes
print(state.values)  # Current state
```

## Event Types

- `on_chain_start` / `on_chain_end` - Node execution
- `on_tool_start` / `on_tool_end` - Tool calls
- `on_chat_model_start` / `on_chat_model_end` - LLM calls

## Backend Types

- `StateBackend` - In-memory (ephemeral)
- `FilesystemBackend` - Disk storage
- `StoreBackend` - LangGraph store (persistent)
- `SandboxBackend` - Isolated execution

## Debug Tips

```python
# Enable debug mode
agent = create_deep_agent(..., debug=True)

# Stream events for tool inspection
async for event in agent.astream_events(..., version="v2"):
    if "tool" in event["event"]:
        print(f"{event['name']}: {event['data']}")
```
