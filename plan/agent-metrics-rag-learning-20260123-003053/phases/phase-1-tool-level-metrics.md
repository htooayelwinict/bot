# Phase 1: Tool-Level Metrics Capture

**Status:** ✅ Completed
**Completed:** 2026-01-23

## Objective
Implement `TrajectoryCallbackHandler` to capture all tool invocations, timing, success/failure, and token usage during agent execution.

## Prerequisites
- Agent dependencies installed (`pip install -e ".[agent]"`)
- Existing tests pass

## Tasks

### 1.1 Create Callback Handler
- **File:** `src/metrics/trajectory_callback.py` (new)
- Create `TrajectoryCallbackHandler` extending `BaseCallbackHandler`
- Implement `on_tool_start()` - capture tool name, input, start time
- Implement `on_tool_end()` - capture output, success, latency
- Implement `on_tool_error()` - capture exception, mark as failed
- Implement `on_llm_start()` / `on_llm_end()` - capture token usage
- Store trajectory in memory (list of tool calls)

**Code Structure:**
```python
class TrajectoryCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.trajectory = []
        self.tool_calls = []
        self.metrics = {
            "tool_success": [],
            "latencies": [],
            "token_usage": []
        }
```

### 1.2 Integrate with FacebookSurferAgent
- **File:** `src/agents/facebook_surfer.py`
- Modify `invoke()` method to accept optional `callbacks` parameter
- Pass callback handler to `agent.ainvoke()`
- Add `get_trajectory()` helper method to retrieve captured data

**Integration:**
```python
async def invoke(
    self,
    task: str,
    thread_id: str = "default",
    callbacks: list = None
) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    if callbacks:
        config["callbacks"] = callbacks
    result = await self.agent.ainvoke(
        {"messages": [{"role": "user", "content": task}]},
        config=config,
    )
    return result
```

### 1.3 Add Metrics Package
- **File:** `src/metrics/__init__.py` (new)
- Export `TrajectoryCallbackHandler`

### 1.4 Unit Tests
- **File:** `tests/metrics/test_trajectory_callback.py` (new)
- Test callback captures tool start/end
- Test metrics recorded (latency, success)
- Test trajectory order preserved
- Test token usage captured for LLM calls

## Files

| File | Action | Description |
|------|--------|-------------|
| `src/metrics/__init__.py` | Create | Metrics package init |
| `src/metrics/trajectory_callback.py` | Create | Callback handler implementation |
| `src/agents/facebook_surfer.py` | Modify | Add callbacks parameter to invoke() |
| `tests/metrics/__init__.py` | Create | Test package |
| `tests/metrics/test_trajectory_callback.py` | Create | Callback handler tests |

## Verification

```bash
# Install dependencies
.venv/bin/pip install -e ".[agent,dev]"

# Run unit tests
.venv/bin/python -m pytest tests/metrics/test_trajectory_callback.py -v

# Test integration with agent
.venv/bin/python -c "
from src.agents.facebook_surfer import FacebookSurferAgent
from src.metrics.trajectory_callback import TrajectoryCallbackHandler

callback = TrajectoryCallbackHandler()
agent = FacebookSurferAgent()

# Test callback capture
print('Callback handler created successfully')
print(f'Agent has {agent.tool_count} tools registered')
"
```

## Deliverables
- ✅ `TrajectoryCallbackHandler` captures all tool calls
- ✅ Metrics recorded: tool name, input, output, success, latency
- ✅ Token usage tracked for LLM calls
- ✅ Unit tests with > 80% coverage
- ✅ Integration test with agent execution

## Notes

**Design Decisions:**
- Use `BaseCallbackHandler` from `langchain_core.callbacks`
- Store trajectory in memory (not yet persisted)
- Use `time.time()` for latency measurement (not `time.perf_counter()` for simplicity)

**Potential Issues:**
- Callbacks not executed if agent crashes mid-execution
- Token usage may not be available for all LLM providers
- Trajectory context may be lost across LangGraph task boundaries

**Next Phase Dependencies:**
- Phase 2 will use captured trajectory for scoring
- Phase 4 will add PII redaction before persistence

## Estimate
**4-6 hours**
- 2h: Implement callback handler
- 1h: Integrate with agent
- 1h: Write unit tests
- 1h: Debug and integration testing
