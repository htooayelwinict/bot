# Plan: Agent Trajectory Collection & RAG-Based Workflow Planning

**Created:** 2026-01-23
**Status:** In Progress - Phase 4 of 5
**Version:** 1.0

## Context

Enable the FacebookSurferAgent to learn from past executions by:
1. Capturing tool-level metrics during agent execution
2. Scoring trajectories with weighted multi-dimensional evaluation
3. Storing trajectories in Qdrant vector database with embeddings
4. Retrieving similar workflows via semantic search
5. Generating success plans from historical data

**Why:** Transform the agent from a static executor into an adaptive system that improves performance over time by learning from successful workflow patterns.

## Code Patterns to Follow

### From Existing Codebase

1. **Decorator Pattern** (`src/tools/base.py:session_tool`)
   - Wrap functions to inject context
   - Use `@wraps` to preserve metadata
   - Apply to all tools via registry

2. **Context Management** (`src/tools/base.py`)
   - Use ContextVars for thread-safe state
   - Fall back to global session when needed
   - Support both sync and async

3. **Tool Result Pattern** (`src/tools/base.py:ToolResult`)
   - Pydantic BaseModel for validation
   - Success/content/data structure
   - Extend for metrics (add metrics field)

4. **LangGraph Callbacks** (new pattern)
   - Extend `BaseCallbackHandler`
   - Implement `on_tool_*` methods
   - Pass via `config["callbacks"]`

### From Research

1. **Weighted Scoring** ([research.md:114-122](plan/research-agent-metrics-20260122-164610/research.md#L114-L122))
   - Tool success: 40%, Latency: 20%, Tokens: 20%, Outcome: 20%
   - Normalize to 0.0-1.0 before weighting

2. **Qdrant Integration** ([research.md:267-308](plan/research-agent-metrics-20260122-164610/research.md#L267-L308))
   - Use AsyncQdrantClient for non-blocking I/O
   - Filter by score threshold (≥ 0.7)
   - Return top-k similar workflows

3. **PII Redaction** ([research.md:183-210](plan/research-agent-metrics-20260122-164610/research.md#L183-L210))
   - 5 patterns: email, phone, SSN, CC, API key
   - Redact BEFORE embedding
   - Preserve trajectory structure

## Phases Overview

| Phase | Name | Objective | Est. Effort | Dependencies |
|-------|------|-----------|------------|--------------|
| 1 | Tool-Level Metrics Capture | Capture all tool calls with timing and success/failure | 4-6h | Agent deps |
| 2 | Success Scoring & Trajectory | Calculate weighted scores and create summaries | 3-4h | Phase 1 |
| 3 | Qdrant Vector Storage | Store trajectories with embeddings for retrieval | 5-7h | Phase 2 |
| 4 | Metrics Middleware & PII | Orchestrate scoring → redaction → storage | 4-5h | Phase 3 |
| 5 | Planning Agent with RAG | Retrieve similar workflows and craft success plans | 5-7h | Phase 4 |

**Total Estimated Effort:** 21-29 hours (3-4 days)

---

## Phase 1: Tool-Level Metrics Capture

### Objective
Implement `TrajectoryCallbackHandler` to capture all tool invocations, timing, success/failure, and token usage during agent execution.

### Tasks
- [ ] Create `src/metrics/trajectory_callback.py` with callback handler
  - Extend `BaseCallbackHandler`
  - Implement `on_tool_start()`, `on_tool_end()`, `on_tool_error()`
  - Implement `on_llm_start()`, `on_llm_end()` for token usage
  - Store trajectory in memory (list of tool calls)
- [ ] Modify `src/agents/facebook_surfer.py`
  - Add optional `callbacks` parameter to `invoke()`
  - Pass callbacks to `agent.ainvoke()`
- [ ] Create `src/metrics/__init__.py` package
- [ ] Write unit tests in `tests/metrics/test_trajectory_callback.py`

### Files
| File | Action |
|------|--------|
| `src/metrics/__init__.py` | Create |
| `src/metrics/trajectory_callback.py` | Create |
| `src/agents/facebook_surfer.py` | Modify |
| `tests/metrics/test_trajectory_callback.py` | Create |

### Verification
```bash
.venv/bin/pip install -e ".[agent,dev]"
.venv/bin/python -m pytest tests/metrics/test_trajectory_callback.py -v
```

---

## Phase 2: Success Scoring & Trajectory Summarization

### Objective
Implement weighted scoring algorithm to evaluate trajectory execution quality and create summaries for embedding.

### Tasks
- [ ] Create `src/metrics/scoring.py`
  - Implement `calculate_score()` with weighted formula
  - Normalize metrics to 0.0-1.0 scale
  - Return score + component breakdown
- [ ] Create `src/metrics/trajectory.py`
  - Implement `summarize_trajectory()` for embedding
  - Format: `task -> tool1 -> tool2 -> ... -> outcome`
- [ ] Create `src/metrics/models.py`
  - Define Pydantic models: `Trajectory`, `ToolCall`, `TrajectoryMetrics`
- [ ] Integrate scoring with callback handler
- [ ] Write unit tests in `tests/metrics/test_scoring.py`

### Files
| File | Action |
|------|--------|
| `src/metrics/scoring.py` | Create |
| `src/metrics/trajectory.py` | Create |
| `src/metrics/models.py` | Create |
| `src/metrics/trajectory_callback.py` | Modify |
| `tests/metrics/test_scoring.py` | Create |

### Verification
```bash
.venv/bin/python -m pytest tests/metrics/test_scoring.py -v
```

---

## Phase 3: Qdrant Vector Storage

### Objective
Set up Qdrant vector database and implement trajectory storage with OpenAI embeddings for semantic retrieval.

### Tasks
- [ ] Create `src/storage/qdrant_client.py`
  - Initialize AsyncQdrantClient with persistent storage
  - Create `agent_trajectories` collection (1536 dims, COSINE)
  - Singleton pattern for client reuse
- [ ] Create `src/storage/embeddings.py`
  - Wrap OpenAI embeddings (`text-embedding-3-small`)
  - Implement `embed_trajectory()` async function
- [ ] Create `src/storage/trajectory_store.py`
  - Implement `store_trajectory()` with embedding
  - Store with metadata (score, tool calls, timestamp)
- [ ] Create `src/storage/retrieval.py`
  - Implement `retrieve_similar_trajectories()`
  - Filter by score ≥ 0.7
  - Return top-k results
- [ ] Add `OPENAI_API_KEY` to `config/.env.example`
- [ ] Write tests in `tests/storage/test_qdrant.py`

### Files
| File | Action |
|------|--------|
| `src/storage/__init__.py` | Create |
| `src/storage/qdrant_client.py` | Create |
| `src/storage/embeddings.py` | Create |
| `src/storage/trajectory_store.py` | Create |
| `src/storage/retrieval.py` | Create |
| `config/.env.example` | Modify |
| `tests/storage/test_qdrant.py` | Create |

### Verification
```bash
.venv/bin/pip install -e ".[memory]"
export OPENAI_API_KEY="sk-test..."
.venv/bin/python -m pytest tests/storage/test_qdrant.py -v
```

---

## Phase 4: Metrics Middleware & PII Redaction

### Objective
Create middleware to orchestrate scoring, PII redaction, and trajectory storage. End-to-end integration with agent execution.

### Tasks
- [ ] Create `src/metrics/pii_redaction.py`
  - Implement 5 redaction patterns (email, phone, SSN, CC, API key)
  - Create `redact_trajectory()` function
  - Deep copy before redaction
- [ ] Create `src/metrics/middleware.py`
  - Create `MetricsMiddleware` class
  - Orchestrate: capture → score → redact → embed → store
  - Handle errors gracefully
- [ ] Integrate with FacebookSurferAgent
  - Add `enable_metrics` flag to `__init__()`
  - Initialize middleware
  - Process trajectory after execution
- [ ] Add `--enable-metrics` flag to CLI (`src/main.py`)
- [ ] Write tests: `tests/metrics/test_pii_redaction.py`
- [ ] Write integration test: `tests/integration/test_metrics_flow.py`

### Files
| File | Action |
|------|--------|
| `src/metrics/pii_redaction.py` | Create |
| `src/metrics/middleware.py` | Create |
| `src/metrics/trajectory_callback.py` | Modify (add get_trajectory) |
| `src/agents/facebook_surfer.py` | Modify |
| `src/main.py` | Modify |
| `tests/metrics/test_pii_redaction.py` | Create |
| `tests/integration/test_metrics_flow.py` | Create |

### Verification
```bash
.venv/bin/python -m pytest tests/metrics/test_pii_redaction.py -v
.venv/bin/python -m pytest tests/integration/test_metrics_flow.py -v
.venv/bin/python -m facebook-surfer run --enable-metrics "test task"
```

---

## Phase 5: Planning Agent with RAG

### Objective
Implement planning agent that retrieves similar historical workflows and crafts success plans to guide execution agent.

### Tasks
- [ ] Create `src/agents/prompts.py`
  - Define planning prompt template
  - Instruct LLM to analyze historical workflows
- [ ] Create `src/agents/planner.py`
  - Create `PlanningAgent` class
  - Implement `craft_success_plan()` method
  - Handle cold start (no similar workflows)
- [ ] Integrate with FacebookSurferAgent
  - Add `enable_planning` flag to `__init__()`
  - Retrieve plan before execution
  - Inject plan into task prompt
- [ ] Add `--enable-planning` flag to CLI
- [ ] Create `scripts/seed_trajectories.py`
  - Seed 5-10 manual successful workflows
  - Run once before using planning agent
- [ ] Write tests: `tests/agents/test_planner.py`
- [ ] Write integration test: `tests/integration/test_planning_flow.py`
- [ ] Update `README.md` with documentation

### Files
| File | Action |
|------|--------|
| `src/agents/prompts.py` | Create |
| `src/agents/planner.py` | Create |
| `src/agents/facebook_surfer.py` | Modify |
| `src/main.py` | Modify |
| `scripts/seed_trajectories.py` | Create |
| `tests/agents/test_planner.py` | Create |
| `tests/integration/test_planning_flow.py` | Create |
| `README.md` | Modify |

### Verification
```bash
# Seed initial trajectories
.venv/bin/python scripts/seed_trajectories.py

# Test planning
.venv/bin/python -m pytest tests/agents/test_planner.py -v
.venv/bin/python -m pytest tests/integration/test_planning_flow.py -v

# Full learning loop
.venv/bin/python -m facebook-surfer run --enable-planning --enable-metrics "Post to Facebook group"
```

---

## Summary

### Total Phases
5 phases, independently testable, sequentially dependent

### Estimated Effort
**21-29 hours** (3-4 days of focused development)
- Phase 1: 4-6h (Tool capture)
- Phase 2: 3-4h (Scoring)
- Phase 3: 5-7h (Qdrant storage)
- Phase 4: 4-5h (Middleware & PII)
- Phase 5: 5-7h (Planning agent)

### Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Python 3.14 compatibility** | High | Use Qdrant (not ChromaDB), verified compatible |
| **PII leakage** | Critical | Redact before embedding, test all 5 patterns |
| **Performance overhead** | Medium | Async operations, < 150ms overhead target |
| **Cold start problem** | Medium | Seed 5-10 manual trajectories before planning |
| **Qdrant dependency** | Low | Graceful degradation if storage fails |
| **OpenAI API costs** | Low | Use `text-embedding-3-small`, cache embeddings |

### Rollback Strategy
- All features behind feature flags (`--enable-metrics`, `--enable-planning`)
- Can disable metrics/planning without breaking core agent
- Qdrant storage is local, can delete `./qdrant_db` to reset
- No database migrations required

### Success Metrics
- **Trajectory Capture Rate:** 100% of tool calls captured
- **Storage Success:** > 99% of trajectories stored successfully
- **Retrieval Latency:** < 500ms for Qdrant queries
- **Plan Quality:** Measured by improved task success rate
- **PII Redaction:** 0% PII leakage in stored trajectories

### Expected Impact
After full implementation:
- **20% reduction** in failed tool calls (proven workflows)
- **15% reduction** in task latency (optimized paths)
- **10% increase** in success scores (learning from success)
- **Adaptive behavior:** Agent improves with each execution

### Unresolved Questions

From research ([research.md:368-372](plan/research-agent-metrics-20260122-164610/research.md#L368-L372)):
1. Weight formula: should outcome_match be higher than 20%?
2. Embed strategy: task-only vs task+trajectory vs trajectory-only?
3. Cold start: minimum trajectories before reliable retrieval?
4. Plan injection: prepend to system prompt or user message?
5. Cosine similarity threshold: 0.7 too strict/lenient?

**Decision:** Implement with proposed defaults, adjust based on real-world performance.

### Next Steps

1. **Review this plan** and approve approach
2. **Run `/code plan/agent-metrics-rag-learning-20260123-003053`** to start Phase 1
3. **Verify each phase** with provided commands before proceeding
4. **Seed trajectories** after Phase 3 to enable Phase 5 testing
5. **Monitor metrics** in production to tune scoring weights and thresholds
