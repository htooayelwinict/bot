# Existing Code Analysis

## Agent Architecture

### FacebookSurferAgent (`src/agents/facebook_surfer.py`)
**Key Components:**

1. **Initialization Flow:**
   - Registers tools via `ToolRegistry`
   - Sets up LangGraph checkpointer (`MemorySaver`)
   - Configures Skills middleware for domain guidance
   - Creates DeepAgent with OpenRouter model support

2. **Execution Methods:**
   - `invoke()` - Execute task with result return
   - `stream()` - Stream values for real-time feedback
   - `stream_events()` - Stream detailed events for debugging
   - `get_state()` / `update_state()` - State management for HITL

3. **Tool Integration Points:**
   - Tools registered in `self.tools` list
   - Passed to `create_deep_agent()`
   - HITL interrupts configured per-tool

**Integration Opportunities:**
- Add `TrajectoryCallbackHandler` to agent invocation
- Wrap `create_deep_agent()` with metrics middleware
- Inject planning results via system prompt modification

### Tool Registry (`src/tools/registry.py`)
**Current Pattern:**
```python
ToolSpec(
    name="browser_click",
    category=ToolCategory.interaction,
    description="Click element on page",
    func=browser_click,
    args_schema=BrowserClickInput,
)
```

**Integration Opportunities:**
- Wrap tool functions with metric collection decorator
- Add callback parameter to tool spec

### Base Tool Classes (`src/tools/base.py`)
**Key Infrastructure:**

1. **Session Management:**
   - `get_current_page()` / `get_current_async_page()`
   - Global session state via ContextVars
   - `session_tool` / `async_session_tool` decorators

2. **Tool Result Pattern:**
   ```python
   class ToolResult(BaseModel):
       success: bool
       content: str
       data: Optional[dict[str, Any]]
   ```

3. **Decorators:**
   - `session_tool` - Inject page from global session
   - `with_screenshot` - Capture screenshots before execution

**Integration Opportunities:**
- Add `@with_metrics` decorator for automatic collection
- Extend `ToolResult` to include metrics field

## LangGraph Integration Points

### Current Stream Usage
```python
# In FacebookSurferAgent.stream_events()
async for event in self.agent.astream_events(
    {"messages": [{"role": "user", "content": task}]},
    config=config,
    version="v2",
):
    yield event
```

**Event Types Available:**
- `on_tool_start` - Tool invocation begins
- `on_tool_end` - Tool invocation completes
- `on_llm_start` / `on_llm_end` - LLM calls
- `on_chain_start` / `on_chain_end` - Graph nodes

### Checkpointer Pattern
```python
from langgraph.checkpoint.memory import MemorySaver
self.checkpointer = MemorySaver()
```

**Checkpoint Data Structure:**
- Channel values (messages, state)
- Metadata (step count, timestamps)
- Configurable state (thread_id)

## File Structure Analysis

```
src/
├── agents/
│   └── facebook_surfer.py        # Main agent class (347 lines)
├── tools/
│   ├── base.py                    # Tool decorators & utilities (312 lines)
│   ├── registry.py                # Tool registration & discovery
│   ├── browser.py                 # Browser snapshot/navigation
│   ├── interaction.py             # Click/type/fill operations
│   ├── forms.py                   # Form submission
│   ├── vision.py                  # OCR/screenshot tools
│   ├── security.py                # Prompt injection defense
│   └── utilities.py               # Helper functions
└── session/
    └── __init__.py                # Session management (login, validation)
```

## Dependencies Analysis

### Current (pyproject.toml)
```toml
[project.optional-dependencies]
agent = [
    "deepagents>=0.1.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langgraph>=0.2.0",
    "openai>=1.54.0",
]
memory = [
    "qdrant-client>=1.12.0",  # ✅ Already added!
]
```

### Additional Dependencies Needed
- `presidio` (optional, for production PII redaction)
- No additional LangChain packages needed!

## Code Patterns to Follow

### 1. Decorator Pattern (from `session_tool`)
```python
@wraps(func)
def wrapper(*args, **kwargs):
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        success = True
    except Exception as e:
        success = False
        result = str(e)
    finally:
        record_metric(func.__name__, success, time.time() - start_time)
    return result
```

### 2. Context Management (from session tools)
```python
# Use ContextVars for thread-safe state
_current_trajectory: ContextVar[dict] = ContextVar("current_trajectory")

def get_current_trajectory() -> dict:
    try:
        return _current_trajectory.get()
    except LookupError:
        return {}
```

### 3. Tool Result Pattern (from `ToolResult`)
```python
# Extend this pattern for metric collection
class ToolResult(BaseModel):
    success: bool
    content: str
    data: Optional[dict[str, Any]]
    metrics: Optional[dict[str, Any]] = None  # ADD THIS
```

## Testing Infrastructure

### Current Setup (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Test Patterns Used
```python
# Async tool tests
@pytest.mark.asyncio
async def test_browser_click():
    result = await browser_click(...)

# Pydantic validation
def test_tool_result_validation():
    result = ToolResult(success=True, content="Test")
    assert result.success is True
```

## Potential Integration Points

### 1. FacebookSurferAgent.invoke()
**Current:**
```python
async def invoke(self, task: str, thread_id: str = "default") -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = await self.agent.ainvoke(
        {"messages": [{"role": "user", "content": task}]},
        config=config,
    )
    return result
```

**Proposed Integration:**
```python
async def invoke(self, task: str, thread_id: str = "default") -> dict:
    # 1. Retrieve similar workflows (Planning)
    plan = await self.planner.craft_success_plan(task)

    # 2. Add callbacks for metrics capture
    callback = TrajectoryCallbackHandler()
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [callback],
    }

    # 3. Execute with enhanced prompt
    enhanced_task = f"{task}\n\nSuccess Plan:\n{plan}"
    result = await self.agent.ainvoke(
        {"messages": [{"role": "user", "content": enhanced_task}]},
        config=config,
    )

    # 4. Store trajectory with metrics
    await self.metrics.store_trajectory(
        trajectory=callback.get_trajectory(),
        task_label=task,
    )

    return result
```

### 2. Tool Registration
**Current:**
```python
self.registry: ToolRegistry = register_all_tools()
self.tools = self.registry.get_all()
```

**Proposed Integration:**
```python
# Wrap tools with metrics decorator
tools_with_metrics = [
    wrap_tool_with_metrics(tool) for tool in self.tools
]
```

## Gaps & Risks

### Gaps
1. **No callback infrastructure:** LangGraph callbacks not currently used
2. **No metrics storage:** No persistence layer for trajectory data
3. **No planning logic:** No historical workflow retrieval

### Risks
1. **Performance overhead:** Callbacks may slow tool execution
2. **Async complexity:** Mixing sync/async metrics collection
3. **Context propagation:** Trajectory context across LangGraph tasks

## Recommended Approach

**Incremental Integration:**
1. **Phase 1:** Add callback handler to `invoke()` method
2. **Phase 2:** Implement metrics calculation separately
3. **Phase 3:** Add Qdrant client initialization
4. **Phase 4:** Integrate PII redaction before storage
5. **Phase 5:** Add planning agent as wrapper around execution

**Minimal Changes:**
- Avoid modifying core tool implementations
- Use decorators and middleware patterns
- Leverage LangGraph callback system
