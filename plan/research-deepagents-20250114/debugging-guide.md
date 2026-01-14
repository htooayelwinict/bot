# DeepAgents Debugging Guide

## Debug Stream Events

The `stream_events()` method in `FacebookSurferAgent` provides detailed debugging information:

```python
async for event in agent.stream_events(task, thread_id):
    event_type = event.get("event", "")
    event_name = event.get("name", "")
    
    # Filter for tool calls
    if "tool" in event_type:
        print(f"[TOOL] {event_name}")
        print(f"  Input: {event['data'].get('input')}")
        if "output" in event['data']:
            print(f"  Output: {event['data']['output'][:200]}...")
```

## Common Event Patterns

### 1. Browser Tool Call Flow

```
on_chat_model_start (agent thinking)
  ↓
on_tool_start (browser_click)
  ↓
browser_click executes
  ↓
on_tool_end (returns ref/snapshot)
  ↓
on_chat_model_start (next decision)
```

### 2. Skill Loading

```
before_agent (SkillsMiddleware)
  ↓
loads skills_metadata from filesystem
  ↓
wrap_model_call (injects skills into prompt)
  ↓
agent receives skills in context
```

### 3. Subagent Spawning

```
on_tool_start (task tool)
  ↓
subagent executes with isolated context
  ↓
returns condensed result
  ↓
main agent receives summary
```

## Debugging Tips

### Enable Debug Mode

```python
# In FacebookSurferAgent._create_agent()
agent = create_deep_agent(
    ...,
    debug=True,  # Adds verbose logging
)
```

### Check Agent State

```python
# Get current state
state = await agent.get_state(thread_id)

# Check for pending actions
if state.get("next"):
    print("Agent interrupted, pending:", state["next"])

# Check messages
for msg in state["messages"]:
    print(f"{msg['role']}: {msg['content'][:100]}")
```

### Stream Specific Event Types

```python
# Only tool events
async for event in agent.stream_events(task):
    if "tool" in event["event"]:
        print(event)

# Only LLM events  
async for event in agent.stream_events(task):
    if "llm" in event["event"] or "chat_model" in event["event"]:
        print(f"LLM: {event['name']}")

# Only errors
async for event in agent.stream_events(task):
    if "error" in event.get("data", {}):
        print(f"ERROR: {event}")
```

## Common Issues

### Issue: Agent "hangs" or loops

**Symptoms:** Multiple tool calls without progress

**Debug:**
```python
# Check tool call sequence
tool_calls = []
async for event in agent.stream_events(task):
    if event["event"] == "on_tool_start":
        tool_calls.append(event["name"])
        if len(tool_calls) > 10:
            print("Possible loop detected!")
            print("Sequence:", tool_calls[-10:])
```

**Solution:** Add system prompt guidance or use `interrupt_on`

### Issue: Skills not loading

**Symptoms:** Agent doesn't follow skill instructions

**Debug:**
```python
# Check skills_metadata in state
state = await agent.get_state(thread_id)
skills = state.get("skills_metadata", [])
print(f"Loaded {len(skills)} skills:")
for skill in skills:
    print(f"  - {skill['name']}: {skill['description']}")
```

**Solution:** Verify FilesystemBackend path and SKILL.md format

### Issue: Tool call failures

**Symptoms:** Tools return errors or wrong results

**Debug:**
```python
async for event in agent.stream_events(task):
    if event["event"] == "on_tool_end":
        output = event["data"].get("output", "")
        if "Error:" in str(output):
            print(f"Tool {event['name']} failed:")
            print(f"  Input: {event['data'].get('input')}")
            print(f"  Output: {output}")
```

## Event Structure Reference

```python
{
    "event": "on_tool_start",           # Event type
    "name": "browser_click",            # Tool/node name
    "data": {
        "input": {                      # Tool input
            "ref": "e42",
            "force": True,
        }
    },
    "metadata": {
        "parent_id": "...",             # Parent trace ID
        "checkpoint_ns": "...",         # Checkpoint namespace
    },
}
```

## Stream Mode Comparison

| Mode | Use Case | Output |
|------|----------|--------|
| `values` | Monitor agent progress | Full state after each node |
| `updates` | See what changed | State deltas per node |
| `events` | Debug tool/LLM calls | Detailed event stream |

**Example:**
```python
# Progress monitoring
async for state in agent.stream(task, thread_id):
    latest_msg = state["messages"][-1]
    print(f"Step: {latest_msg['role']} - {latest_msg['content'][:50]}")

# Detailed debugging
async for event in agent.stream_events(task, thread_id):
    if event["event"] == "on_tool_end":
        print(f"Tool {event['name']} completed")
```

## Performance Monitoring

```python
import time

start = time.time()
tool_times = {}

async for event in agent.stream_events(task, thread_id):
    if event["event"] == "on_tool_start":
        tool_times[event["name"]] = time.time()
    elif event["event"] == "on_tool_end":
        name = event["name"]
        if name in tool_times:
            duration = time.time() - tool_times[name]
            print(f"{name}: {duration:.2f}s")
```
