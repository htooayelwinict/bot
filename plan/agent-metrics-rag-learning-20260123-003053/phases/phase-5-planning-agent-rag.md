# Phase 5: Planning Agent with RAG

## Status
**✅ Completed** - All tasks implemented and tested.

## Objective
Implement planning agent that retrieves similar historical workflows and crafts success plans to guide execution agent.

## Prerequisites
- Phase 4 complete (storage and retrieval working)
- Phase 3 complete (semantic search functional)
- At least 5-10 manual trajectories seeded in Qdrant

## Tasks

### 5.1 Planning Prompt Template
- **File:** `src/agents/prompts.py` (new)
- Create planning prompt template
- Instruct LLM to analyze historical workflows
- Output step-by-step execution plan

**Template:**
```python
from langchain_core.prompts import ChatPromptTemplate

PLANNING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a workflow planning agent. Analyze historical successful workflows and craft execution plans.

Historical successful workflows:
{historical_workflows}

User task: {task}

Analyze the workflows and create a step-by-step execution plan that combines proven patterns.
Focus on:
1. Tool call sequences that succeeded
2. Parameter patterns from successful executions
3. Error handling approaches

Output the plan as a numbered list of steps.
Be concise and actionable."""),
    ("user", "{task}")
])
```

### 5.2 Planning Agent Implementation
- **File:** `src/agents/planner.py` (new)
- Create `PlanningAgent` class
- Initialize with Qdrant client and LLM
- Implement `craft_success_plan()` method
- Handle cold start (no similar workflows found)

**Implementation:**
```python
from langchain_openai import ChatOpenAI
from src.storage.retrieval import retrieve_similar_trajectories

class PlanningAgent:
    """Retrieve similar workflows and craft success plans."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",  # Cost-effective for planning
        qdrant_client: AsyncQdrantClient | None = None
    ):
        self.model_name = model
        self.qdrant_client = qdrant_client
        self.llm = ChatOpenAI(model=model)
        self.chain = PLANNING_PROMPT | self.llm

    async def craft_success_plan(
        self,
        task: str,
        top_k: int = 3
    ) -> str:
        """Retrieve similar workflows and generate plan."""
        # Ensure Qdrant client initialized
        if not self.qdrant_client:
            from src.storage.qdrant_client import QdrantManager
            self.qdrant_client = await QdrantManager.get_client()

        # Retrieve similar workflows
        similar = await retrieve_similar_trajectories(
            task=task,
            top_k=top_k,
            min_score=0.7,
            client=self.qdrant_client
        )

        # Cold start: no similar workflows
        if not similar:
            return "No similar historical workflows found. Proceed with standard execution based on best practices."

        # Format historical context
        historical_context = self._format_workflows(similar)

        # Generate plan
        result = await self.chain.ainvoke({
            "task": task,
            "historical_workflows": historical_context
        })

        return result.content

    def _format_workflows(self, workflows: list[dict]) -> str:
        """Format workflows for prompt."""
        formatted = []
        for w in workflows:
            formatted.append(
                f"Workflow (score: {w['score']:.2f}, similarity: {w['similarity']:.2f}):\n"
                f"Task: {w['task']}\n"
                f"Steps: {' -> '.join(w['trajectory'])}\n"
            )
        return "\n\n".join(formatted)
```

### 5.3 FacebookSurferAgent Integration
- **File:** `src/agents/facebook_surfer.py`
- Add `PlanningAgent` as optional dependency
- Modify `invoke()` to retrieve plan before execution
- Inject plan into task prompt

**Integration:**
```python
class FacebookSurferAgent:
    def __init__(
        self,
        ...,
        enable_planning: bool = False
    ):
        ...
        self.enable_planning = enable_planning
        self.planner: PlanningAgent | None = None
        if enable_planning:
            self.planner = PlanningAgent()

    async def invoke(self, task: str, thread_id: str = "default") -> dict:
        # 1. Retrieve success plan (if planning enabled)
        if self.enable_planning:
            plan = await self.planner.craft_success_plan(task)

            # Enhance task with plan
            if plan and "No similar historical workflows" not in plan:
                enhanced_task = f"""Task: {task}

Success Plan (based on similar historical workflows):
{plan}

Execute this task following the success plan above."""
            else:
                enhanced_task = task
        else:
            enhanced_task = task

        # 2. Execute with callbacks (metrics)
        callbacks = []
        if self.enable_metrics:
            from src.metrics.trajectory_callback import TrajectoryCallbackHandler
            callback = TrajectoryCallbackHandler()
            callbacks.append(callback)

        # 3. Process metrics after execution
        # ... (existing code)

        return result
```

### 5.4 CLI Integration
- **File:** `src/main.py`
- Add `--enable-planning` flag
- Document interaction with `--enable-metrics`

**Usage:**
```bash
# Planning + Metrics (full learning loop)
facebook-surfer run --enable-planning --enable-metrics "task"

# Planning only (no storage)
facebook-surfer run --enable-planning "task"
```

### 5.5 Cold Start Seeding
- **File:** `scripts/seed_trajectories.py` (new)
- Create script to seed Qdrant with manual workflows
- Add 5-10 successful Facebook automation examples
- Run once before using planning agent

**Examples to Seed:**
```python
SEED_TRAJECTORIES = [
    {
        "task": "Post a message to Facebook group",
        "trajectory": ["browser_navigate", "browser_get_snapshot", "browser_click", "browser_type", "browser_click"],
        "score": 0.95,
        "tool_calls": [...]
    },
    {
        "task": "Like a post on Facebook",
        "trajectory": ["browser_navigate", "browser_get_snapshot", "browser_click"],
        "score": 0.92,
        "tool_calls": [...]
    },
    # ... add 8 more
]
```

### 5.6 Unit Tests
- **File:** `tests/agents/test_planner.py` (new)
- Test planning agent initialization
- Test plan generation with mock workflows
- Test cold start handling (no similar workflows)
- Test plan formatting and injection

### 5.7 Integration Tests
- **File:** `tests/integration/test_planning_flow.py` (new)
- Test full loop: plan → execute → store
- Test plan quality (agent uses plan)
- Test cold start to learning progression

### 5.8 Documentation
- **File:** `README.md`
- Add "Learning & Planning" section
- Document planning agent usage
- Explain cold start seeding process

## Files

| File | Action | Description |
|------|--------|-------------|
| `src/agents/prompts.py` | Create | Planning prompt template |
| `src/agents/planner.py` | Create | Planning agent implementation |
| `src/agents/facebook_surfer.py` | Modify | Integrate planning agent |
| `src/main.py` | Modify | Add --enable-planning flag |
| `scripts/seed_trajectories.py` | Create | Cold start seeding script |
| `tests/agents/test_planner.py` | Create | Planning agent tests |
| `tests/integration/test_planning_flow.py` | Create | End-to-end planning tests |
| `README.md` | Modify | Document learning system |

## Verification

```bash
# Seed initial trajectories
.venv/bin/python scripts/seed_trajectories.py

# Run planning agent tests
.venv/bin/python -m pytest tests/agents/test_planner.py -v

# Run integration tests
.venv/bin/python -m pytest tests/integration/test_planning_flow.py -v

# Manual test with planning enabled
.venv/bin/python -m facebook-surfer run --enable-planning "Post a message to my Facebook group"

# Test full learning loop
.venv/bin/python -m facebook-surfer run --enable-planning --enable-metrics "Post a message to my Facebook group"
# Run again - should use previous success!
.venv/bin/python -m facebook-surfer run --enable-planning --enable-metrics "Post a message to my Facebook group"
```

## Deliverables
- ✅ Planning agent retrieves similar workflows
- ✅ Success plans generated from historical data
- ✅ Plans injected into agent context
- ✅ Cold start handled gracefully
- ✅ Full learning loop: plan → execute → store → retrieve
- ✅ Unit and integration tests passing

## Notes

**Planning Agent Model:**
- Use `gpt-4o-mini` (cost-effective, fast)
- Fallback to `gpt-4o` for complex tasks
- Temperature: 0.0 (deterministic plans)

**Retrieval Parameters:**
- `top_k=3`: Get top 3 similar workflows
- `min_score=0.7`: Only high-quality trajectories
- Similarity threshold prevents irrelevant plans

**Cold Start Problem:**
- Seed with 5-10 manual trajectories
- Fallback to "proceed with standard execution"
- Agent learns after first successful executions

**Plan Quality Indicators:**
- Agent follows plan steps
- Reduced tool call failures
- Lower latency (proven paths)
- Higher success scores

**Future Enhancements:**
- Multi-agent planning (specialized planners per domain)
- Plan validation before execution
- A/B testing of plan effectiveness
- Plan versioning and rollback

## Estimate
**5-7 hours**
- 1.5h: Planning agent implementation
- 1h: FacebookSurferAgent integration
- 1h: CLI integration
- 1h: Cold start seeding script
- 1.5h: Testing and validation
- 1h: Documentation

## Dependencies
- Phase 4 must be complete (Qdrant retrieval working)
- At least 5-10 seed trajectories for testing
- OpenAI API key configured (for planning LLM)

## Success Criteria
**End-to-End Learning Loop:**
1. **Task 1 (Cold Start):** Agent executes without historical context
2. **Metrics:** Trajectory stored with score
3. **Task 2 (Similar):** Agent retrieves and uses plan from Task 1
4. **Improvement:** Higher success score or lower latency

**Measurable Impact:**
- 20% reduction in failed tool calls
- 15% reduction in task latency
- 10% increase in success scores
