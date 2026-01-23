# Plan: Agent Trajectory Collection & RAG-Based Workflow Planning

**Created:** 2026-01-23
**Status:** ✅ Complete - All 5 Phases
**Version:** 1.0

## Summary

Transform the FacebookSurferAgent from a static executor into an adaptive learning system that:

1. **Captures** every tool call with timing and success metrics during execution
2. **Scores** trajectories using weighted multi-dimensional evaluation (40/20/20/20)
3. **Stores** trajectories in Qdrant vector database with OpenAI embeddings
4. **Retrieves** similar historical workflows via semantic cosine similarity search
5. **Generates** success plans from proven patterns to guide future executions

**Goal:** Enable the agent to learn from past executions and continuously improve performance by avoiding failed approaches and reusing successful workflows.

---

## Progress

- [x] Phase 1: Tool-Level Metrics Capture ✅
- [x] Phase 2: Success Scoring & Trajectory Summarization ✅
- [x] Phase 3: Qdrant Vector Storage ✅
- [x] Phase 4: Metrics Middleware & PII Redaction ✅
- [x] Phase 5: Planning Agent with RAG ✅

---

---

## Goals

### Primary Goals
- ✅ **100% trajectory capture** - Every tool call logged with metrics
- ✅ **Automated scoring** - Weighted evaluation of execution quality
- ✅ **Semantic retrieval** - Find similar workflows via cosine similarity
- ✅ **PII protection** - Redact sensitive data before storage
- ✅ **Adaptive planning** - Generate success plans from historical data

### Secondary Goals
- Reduce tool call failures by 20%
- Reduce task latency by 15%
- Increase success scores by 10%
- Create feedback loop: execute → learn → improve

---

## Scope

### In Scope
- Tool-level metrics capture (timing, success, tokens)
- Weighted scoring algorithm (40/20/20/20 formula)
- Qdrant vector storage with OpenAI embeddings
- PII redaction (email, phone, SSN, credit card, API keys)
- Planning agent with RAG retrieval
- CLI flags for enabling features (`--enable-metrics`, `--enable-planning`)
- Integration with existing FacebookSurferAgent
- Unit and integration tests

### Out of Scope (Future Work)
- User feedback mechanism for outcome_match metric
- Multi-task domain separation (separate Qdrant collections)
- Real-time trajectory visualization dashboard
- Batch trajectory import/export tools
- A/B testing of scoring weights
- Distributed Qdrant deployment (cloud hosting)
- Multi-agent planning (specialized planners per domain)

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Python 3.14 incompatibility** | High | Low | Use Qdrant (verified compatible), NOT ChromaDB |
| **PII leakage in storage** | Critical | Medium | Redact before embedding, test all 5 patterns |
| **Performance overhead** | Medium | Low | Async operations, target < 150ms per task |
| **Cold start problem** | Medium | High | Seed 5-10 manual trajectories before planning |
| **OpenAI API rate limits** | Low | Low | Use `text-embedding-3-small`, cache embeddings |
| **Qdrant storage failure** | Low | Low | Graceful degradation, continue without storage |

---

## Phases Overview

| Phase | Name | Description | Est. Effort |
|-------|------|-------------|-------------|
| 1 | Tool-Level Metrics Capture | Capture all tool calls with timing and success/failure | 4-6h |
| 2 | Success Scoring & Trajectory | Calculate weighted scores and create summaries for embedding | 3-4h |
| 3 | Qdrant Vector Storage | Store trajectories with embeddings for semantic retrieval | 5-7h |
| 4 | Metrics Middleware & PII | Orchestrate scoring → redaction → storage pipeline | 4-5h |
| 5 | Planning Agent with RAG | Retrieve similar workflows and craft success plans | 5-7h |

**Total Estimated Effort:** 21-29 hours (3-4 days)

---

## Files to Modify

### New Files (Create)
- `src/metrics/__init__.py` - Metrics package
- `src/metrics/trajectory_callback.py` - Callback handler for capture
- `src/metrics/scoring.py` - Weighted scoring algorithm
- `src/metrics/trajectory.py` - Trajectory summarization
- `src/metrics/models.py` - Pydantic data models
- `src/metrics/pii_redaction.py` - PII redaction patterns
- `src/metrics/middleware.py` - Orchestration layer
- `src/storage/__init__.py` - Storage package
- `src/storage/qdrant_client.py` - Qdrant client manager
- `src/storage/embeddings.py` - OpenAI embeddings wrapper
- `src/storage/trajectory_store.py` - Trajectory storage
- `src/storage/retrieval.py` - Semantic search
- `src/agents/prompts.py` - Planning prompt templates
- `src/agents/planner.py` - Planning agent implementation
- `scripts/seed_trajectories.py` - Cold start seeding
- Tests: `tests/metrics/*`, `tests/storage/*`, `tests/agents/*`, `tests/integration/*`

### Modify Existing Files
- `src/agents/facebook_surfer.py` - Integrate metrics and planning
- `src/main.py` - Add CLI flags
- `config/.env.example` - Add OpenAI API key
- `pyproject.toml` - Already has `qdrant-client>=1.12.0` in memory dependencies
- `README.md` - Document learning system

---

## Architecture Overview

### Data Flow (From Research)

```
1. USER TASK
   │
   ├────▶ PLANNING AGENT (if enabled)
   │       ├─ Query Qdrant (embed task)
   │       ├─ Retrieve similar workflows (top-k, score ≥ 0.7)
   │       ├─ Craft success plan (LLM with historical context)
   │       └─ Enhance prompt (task + plan)
   │
   ├────▶ EXECUTION AGENT (LangGraph)
   │       ├─ Run graph with tools
   │       └─ TrajectoryCallbackHandler captures:
   │           • Tool calls (name, input, output)
   │           • Success/failure
   │           • Latencies
   │           • Token usage
   │
   ├────▶ METRICS MIDDLEWARE (if enabled)
   │       ├─ Calculate weighted score (40/20/20/20)
   │       ├─ Redact PII (emails, phones, SSN, CC, keys)
   │       └─ Create embedding (task + trajectory)
   │
   └────▶ QDRANT STORAGE
           ├─ Store point (vector + metadata)
           ├─ Index for similarity search
           └─ Available for future retrieval
```

### Weighted Scoring Formula

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

### PII Redaction Patterns

1. **Email:** `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
2. **Phone:** `\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`
3. **SSN:** `\b\d{3}-\d{2}-\d{4}\b`
4. **Credit Card:** `\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b`
5. **API Key:** `\b[A-Za-z0-9]{32,}\b`

---

## Key Features

### 1. Trajectory Capture
- Intercepts all tool invocations via LangChain callbacks
- Records: tool name, input, output, success, latency
- Tracks LLM token usage
- Maintains execution order

### 2. Multi-Dimensional Scoring
- **Tool Success (40%)** - Ratio of successful tool calls
- **Latency (20%)** - Normalized against 30s target
- **Token Cost (20%)** - Normalized against 5000 token target
- **Outcome Match (20%)** - User feedback (future enhancement)

### 3. Vector Storage with Qdrant
- Python 3.14+ compatible (NOT ChromaDB)
- Persistent local storage (`./qdrant_db`)
- Cosine similarity search
- Score filtering (≥ 0.7 threshold)
- Async API for non-blocking I/O

### 4. PII Redaction
- 5 patterns: email, phone, SSN, credit card, API key
- Applied BEFORE embedding (security)
- Preserves trajectory structure
- Regex-based (fast, no dependencies)

### 5. RAG-Based Planning
- Retrieves top-3 similar workflows
- Uses LLM to synthesize success plan
- Injects plan into agent context
- Handles cold start gracefully

---

## Usage

### Enable Metrics Collection
```bash
facebook-surfer run --enable-metrics "Post a message to my Facebook group"
```

### Enable Planning Agent
```bash
facebook-surfer run --enable-planning "Post a message to my Facebook group"
```

### Full Learning Loop
```bash
# First execution (cold start)
facebook-surfer run --enable-planning --enable-metrics "Post a message to my Facebook group"

# Second execution (uses previous success)
facebook-surfer run --enable-planning --enable-metrics "Post a message to my Facebook group"
```

### Seed Initial Trajectories
```bash
python scripts/seed_trajectories.py
```

---

## Verification Commands

### Phase 1: Tool Capture
```bash
.venv/bin/python -m pytest tests/metrics/test_trajectory_callback.py -v
```

### Phase 2: Scoring
```bash
.venv/bin/python -m pytest tests/metrics/test_scoring.py -v
```

### Phase 3: Qdrant Storage
```bash
export OPENAI_API_KEY="sk-test..."
.venv/bin/python -m pytest tests/storage/test_qdrant.py -v
```

### Phase 4: Middleware & PII
```bash
.venv/bin/python -m pytest tests/metrics/test_pii_redaction.py -v
.venv/bin/python -m pytest tests/integration/test_metrics_flow.py -v
```

### Phase 5: Planning Agent
```bash
.venv/bin/python scripts/seed_trajectories.py
.venv/bin/python -m pytest tests/agents/test_planner.py -v
.venv/bin/python -m pytest tests/integration/test_planning_flow.py -v
```

---

## Expected Impact

After full implementation:
- **20% reduction** in failed tool calls (proven workflows)
- **15% reduction** in task latency (optimized paths)
- **10% increase** in success scores (learning from success)
- **Adaptive behavior** - Agent improves with each execution

---

## Dependencies

### Required
- Python 3.14+ (Qdrant compatible)
- OpenAI API key (for embeddings and planning)
- Existing agent dependencies (LangChain, LangGraph)

### Installed
```bash
# Memory dependencies (already in pyproject.toml)
pip install -e ".[memory]"

# Dev dependencies
pip install -e ".[dev]"
```

---

## Next Steps

1. **Review research document:** `plan/research-agent-metrics-20260122-164610/research.md`
2. **Review consolidated plan:** `plan/agent-metrics-rag-learning-20260123-003053/plan.md`
3. **Start Phase 1 implementation:**
   ```bash
   /code plan/agent-metrics-rag-learning-20260123-003053 --phase 1
   ```
4. **Verify each phase** before proceeding to next
5. **Monitor metrics** and tune weights/thresholds based on performance

---

## Related Documentation

- **Research:** [research.md](plan/research-agent-metrics-20260122-164610/research.md)
- **Existing Code:** [existing-code.md](plan/agent-metrics-rag-learning-20260123-003053/research/existing-code.md)
- **Requirements:** [requirements.md](plan/agent-metrics-rag-learning-20260123-003053/research/requirements.md)
- **References:** [references.md](plan/agent-metrics-rag-learning-20260123-003053/research/references.md)
- **Consolidated Plan:** [plan.md](plan/agent-metrics-rag-learning-20260123-003053/plan.md)

---

## Unresolved Questions

1. Should `outcome_match` weight be higher than 20%?
2. Embed strategy: task-only vs task+trajectory vs trajectory-only?
3. Minimum trajectories before reliable retrieval (5? 10? 20?)?
4. Plan injection: prepend to system prompt or user message?
5. Cosine similarity threshold: 0.7 too strict/lenient?

**Decision:** Implement with proposed defaults, adjust based on real-world performance.
