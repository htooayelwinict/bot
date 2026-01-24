# Phase 4: Metrics Middleware & PII Redaction

**Status:** ✅ Completed
**Completed:** 2025-01-23

## Objective
Create middleware to orchestrate scoring, PII redaction, and trajectory storage. End-to-end integration with agent execution.

## Prerequisites
- ✅ Phase 3 complete (Qdrant storage working)
- ✅ Phase 2 complete (scoring implemented)
- ✅ OpenAI API key configured

## Tasks

### 4.1 PII Redaction Module
- **File:** `src/metrics/pii_redaction.py` (new)
- Implement redaction patterns:
  - Email addresses (regex)
  - US phone numbers (regex)
  - SSN (regex: `\d{3}-\d{2}-\d{4}`)
  - Credit cards (regex: 4 groups of 4 digits)
  - API keys (heuristic: 32+ char alphanumeric)
- Create `redact_trajectory()` function
- Deep copy trajectory before redaction (preserve original)
- Return redacted trajectory

**Implementation:**
```python
import re
import json

PII_PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
    "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
    "api_key": r'\b[A-Za-z0-9]{32,}\b',
}

PII_REPLACEMENTS = {
    "email": "[REDACTED_EMAIL]",
    "phone": "[REDACTED_PHONE]",
    "ssn": "[REDACTED_SSN]",
    "credit_card": "[REDACTED_CC]",
    "api_key": "[REDACTED_KEY]",
}

def redact_trajectory(trajectory: dict) -> dict:
    """Remove PII from trajectory before storage."""
    trajectory_copy = json.loads(json.dumps(trajectory))

    for tool_call in trajectory_copy.get("tool_calls", []):
        if "input" in tool_call:
            input_str = str(tool_call["input"])

            # Apply all patterns
            for pattern_name, pattern in PII_PATTERNS.items():
                input_str = re.sub(
                    pattern,
                    PII_REPLACEMENTS[pattern_name],
                    input_str
                )

            tool_call["input"] = input_str

    return trajectory_copy
```

### 4.2 Metrics Middleware
- **File:** `src/metrics/middleware.py` (new)
- Create `MetricsMiddleware` class
- Orchestrate: capture → score → redact → embed → store
- Handle errors gracefully
- Provide simple API for agent integration

**Implementation:**
```python
class MetricsMiddleware:
    """Orchestrate trajectory capture, scoring, and storage."""

    def __init__(self):
        self.qdrant_client: AsyncQdrantClient | None = None

    async def initialize(self):
        """Initialize Qdrant client."""
        from src.storage.qdrant_client import QdrantManager
        self.qdrant_client = await QdrantManager.get_client()

    async def process_execution(
        self,
        task: str,
        trajectory_data: dict,
        callback: TrajectoryCallbackHandler
    ) -> dict:
        """Process complete execution: score → redact → store."""
        # 1. Calculate score
        from src.metrics.scoring import calculate_score
        score_result = calculate_score(
            tool_success=callback.metrics["tool_success"],
            latencies=callback.metrics["latencies"],
            token_usage=callback.metrics["token_usage"],
        )

        # 2. Summarize trajectory
        from src.metrics.trajectory import summarize_trajectory
        summary = summarize_trajectory(
            task=task,
            trajectory=trajectory_data["trajectory"],
            tool_calls=trajectory_data["tool_calls"]
        )

        # 3. Redact PII
        clean_trajectory = redact_trajectory(trajectory_data)

        # 4. Store in Qdrant
        from src.storage.trajectory_store import store_trajectory
        await store_trajectory(
            task=task,
            trajectory_summary=summary,
            score=score_result["total"],
            tool_calls=clean_trajectory["tool_calls"],
            client=self.qdrant_client
        )

        return {
            "score": score_result["total"],
            "stored": True
        }
```

### 4.3 Agent Integration
- **File:** `src/agents/facebook_surfer.py`
- Add `MetricsMiddleware` as optional dependency
- Modify `invoke()` to process trajectory after execution
- Add middleware initialization to `__init__()`

**Integration:**
```python
class FacebookSurferAgent:
    def __init__(
        self,
        ...,
        enable_metrics: bool = False
    ):
        ...
        self.enable_metrics = enable_metrics
        self.metrics_middleware: MetricsMiddleware | None = None
        if enable_metrics:
            self.metrics_middleware = MetricsMiddleware()

    async def invoke(self, task: str, thread_id: str = "default") -> dict:
        # Setup callback if metrics enabled
        callbacks = []
        if self.enable_metrics:
            from src.metrics.trajectory_callback import TrajectoryCallbackHandler
            callback = TrajectoryCallbackHandler()
            callbacks.append(callback)
            await self.metrics_middleware.initialize()

        # Execute task
        config = {"configurable": {"thread_id": thread_id}}
        if callbacks:
            config["callbacks"] = callbacks

        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )

        # Process metrics if enabled
        if self.enable_metrics and callbacks:
            trajectory_data = callback.get_trajectory()
            await self.metrics_middleware.process_execution(
                task=task,
                trajectory_data=trajectory_data,
                callback=callback
            )

        return result
```

### 4.4 CLI Integration
- **File:** `src/main.py`
- Add `--enable-metrics` flag to run command
- Pass through to agent initialization

### 4.5 Unit Tests
- **File:** `tests/metrics/test_pii_redaction.py` (new)
- Test all 5 PII patterns redacted
- Test no false positives (safe data preserved)
- Test nested structures (dicts within tool calls)
- Test edge cases (empty strings, None values)

### 4.6 Integration Tests
- **File:** `tests/integration/test_metrics_flow.py` (new)
- Test end-to-end: execute → score → redact → store
- Test agent with metrics enabled
- Verify Qdrant contains stored trajectories

## Files

| File | Action | Description |
|------|--------|-------------|
| `src/metrics/pii_redaction.py` | Create | PII redaction patterns |
| `src/metrics/middleware.py` | Create | Metrics orchestration |
| `src/metrics/trajectory_callback.py` | Modify | Add get_trajectory() method |
| `src/agents/facebook_surfer.py` | Modify | Integrate middleware |
| `src/main.py` | Modify | Add --enable-metrics flag |
| `tests/metrics/test_pii_redaction.py` | Create | PII tests |
| `tests/integration/` | Create | Integration test package |
| `tests/integration/test_metrics_flow.py` | Create | End-to-end tests |

## Verification

```bash
# Run PII redaction tests
.venv/bin/python -m pytest tests/metrics/test_pii_redaction.py -v

# Run integration tests
.venv/bin/python -m pytest tests/integration/test_metrics_flow.py -v

# Manual test with agent
.venv/bin/python -m facebook-surfer run --enable-metrics "test task"

# Verify Qdrant storage
.venv/bin/python -c "
import asyncio
from src.storage.qdrant_client import QdrantManager

async def check():
    client = await QdrantManager.get_client()
    count = await client.count(
        collection_name='agent_trajectories'
    )
    print(f'Stored trajectories: {count.count}')

asyncio.run(check())
"
```

## Deliverables
- ✅ All 5 PII types redacted (email, phone, SSN, CC, API key)
- ✅ Middleware orchestrates scoring → redaction → storage
- ✅ Agent integration working
- ✅ CLI flag `--enable-metrics` functional
- ✅ End-to-end integration tests passing

## Notes

**PII Redaction Strategy:**
- **Order matters:** Apply patterns from most specific to least
- **Preserve structure:** Tool call structure unchanged
- **Deep copy:** Never mutate original trajectory
- **Placeholder format:** `[REDACTED_TYPE]` for clarity

**Middleware Flow:**
```
Agent Execution Complete
    ↓
Callback Handler → Captured Trajectory
    ↓
MetricsMiddleware.process_execution()
    ↓
1. Calculate Score (scoring.py)
2. Summarize Trajectory (trajectory.py)
3. Redact PII (pii_redaction.py)
4. Store in Qdrant (trajectory_store.py)
    ↓
Return Score to Agent
```

**Error Handling:**
- Continue on redaction errors (log warning)
- Retry Qdrant storage (3 attempts)
- Fail gracefully if Qdrant unavailable

**Performance:**
- Redaction adds ~10ms per trajectory
- Storage adds ~100ms (embedding + Qdrant)
- Total overhead: < 150ms per task

## Estimate
**4-5 hours**
- 1.5h: PII redaction implementation
- 1h: Middleware orchestration
- 1h: Agent integration
- 0.5h: CLI flag
- 1h: Testing and validation

## Dependencies
- Phase 3 must be complete (Qdrant storage functional)
- Phase 2 must be complete (scoring implemented)
