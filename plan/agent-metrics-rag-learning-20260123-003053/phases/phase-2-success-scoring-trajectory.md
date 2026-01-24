# Phase 2: Success Scoring & Trajectory Summarization

**Status:** ✅ Completed
**Completed:** 2026-01-23

## Objective
Implement weighted scoring algorithm to evaluate trajectory execution quality and create trajectory summaries for embedding.

## Prerequisites
- Phase 1 complete (callback handler captures metrics)
- Trajectory data structure defined

## Tasks

### 2.1 Create Scoring Module
- **File:** `src/metrics/scoring.py` (new)
- Implement `calculate_score()` function with weighted formula:
  - Tool success (40%) - ratio of successful tool calls
  - Latency (20%) - normalized against 30s target
  - Token cost (20%) - normalized against 5000 token target
  - Outcome match (20%) - placeholder (user feedback in future)
- Normalize each metric to 0.0-1.0 range
- Return final score and component breakdown

**Implementation:**
```python
def calculate_score(
    tool_success: list[bool],
    latencies: list[float],
    token_usage: list[dict],
    outcome_match: float = 0.5
) -> dict:
    """Calculate weighted trajectory score.

    Returns:
        {
            "total": 0.96,
            "components": {
                "tool_success": 0.40,
                "latency": 0.20,
                "token_cost": 0.20,
                "outcome_match": 0.16
            }
        }
    """
```

### 2.2 Trajectory Summarization
- **File:** `src/metrics/trajectory.py` (new)
- Create `summarize_trajectory()` function
- Format trajectory as string: `task -> tool1 -> tool2 -> ... -> outcome`
- Include tool sequence and success/failure indicators
- Keep summary under 500 chars for embedding limits

**Implementation:**
```python
def summarize_trajectory(
    task: str,
    trajectory: list[str],
    tool_calls: list[dict]
) -> str:
    """Create text summary for embedding.

    Example:
        "Post to Facebook group -> browser_snapshot -> browser_click
         -> browser_type -> success (3/3 tools succeeded)"
    """
```

### 2.3 Metrics Data Structure
- **File:** `src/metrics/models.py` (new)
- Define Pydantic models for type safety:
  - `Trajectory` - Complete execution record
  - `ToolCall` - Individual tool invocation
  - `TrajectoryMetrics` - Captured metrics
  - `ScoreBreakdown` - Scoring results

**Models:**
```python
class ToolCall(BaseModel):
    tool: str
    input: str
    output: str | None
    success: bool
    latency: float
    timestamp: datetime

class TrajectoryMetrics(BaseModel):
    tool_success: list[bool]
    latencies: list[float]
    token_usage: list[dict]
    outcome_match: float = 0.5
```

### 2.4 Integrate with Callback Handler
- **File:** `src/metrics/trajectory_callback.py`
- Import scoring functions
- Add `get_score()` method to callback
- Calculate score on-demand (not in callback hot path)

### 2.5 Unit Tests
- **File:** `tests/metrics/test_scoring.py` (new)
- Test score calculation with various metrics
- Test normalization edge cases (empty lists, zero values)
- Test weight distribution (sums to 1.0)
- Test trajectory summarization format

## Files

| File | Action | Description |
|------|--------|-------------|
| `src/metrics/scoring.py` | Create | Scoring algorithm |
| `src/metrics/trajectory.py` | Create | Trajectory summarization |
| `src/metrics/models.py` | Create | Pydantic data models |
| `src/metrics/trajectory_callback.py` | Modify | Add scoring integration |
| `tests/metrics/test_scoring.py` | Create | Scoring tests |

## Verification

```bash
# Run tests
.venv/bin/python -m pytest tests/metrics/test_scoring.py -v

# Test scoring manually
.venv/bin/python -c "
from src.metrics.scoring import calculate_score

# Test perfect score
result = calculate_score(
    tool_success=[True, True, True],
    latencies=[0.5, 1.0, 0.3],
    token_usage=[{'total_tokens': 1000}],
    outcome_match=1.0
)
print(f'Perfect score: {result[\"total\"]:.2f}')
assert result['total'] > 0.9

# Test failed trajectory
result = calculate_score(
    tool_success=[False, True],
    latencies=[45.0, 30.0],
    token_usage=[{'total_tokens': 10000}],
    outcome_match=0.0
)
print(f'Failed score: {result[\"total\"]:.2f}')
assert result['total'] < 0.5
"
```

## Deliverables
- ✅ Weighted scoring algorithm implemented
- ✅ All metrics normalized to 0.0-1.0
- ✅ Trajectory summarization for embedding
- ✅ Pydantic models for type safety
- ✅ Unit tests for edge cases

## Notes

**Scoring Formula:**
```
tool_success_score = sum(success) / len(success)
latency_score = max(0, 1 - (avg_latency / 30))
token_score = max(0, 1 - (total_tokens / 5000))
outcome_score = outcome_match (0.0-1.0)

total = 0.4 * tool_success_score
      + 0.2 * latency_score
      + 0.2 * token_score
      + 0.2 * outcome_score
```

**Edge Cases:**
- Empty tool list → score = 0.0
- All tools failed → score depends on other factors
- Extreme latency (> 60s) → latency contribution = 0
- High token usage (> 10k) → token contribution = 0

**Future Enhancements:**
- Configurable weights via environment variables
- Per-tool scoring (some tools more critical)
- User feedback mechanism for outcome_match

## Estimate
**3-4 hours**
- 1.5h: Implement scoring algorithm
- 1h: Trajectory summarization
- 0.5h: Pydantic models
- 1h: Testing and validation
