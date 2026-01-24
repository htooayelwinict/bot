# Requirements Analysis

## Overview
Implement an agent trajectory collection and RAG-based workflow planning system to enable the FacebookSurferAgent to learn from past executions and improve future task performance.

## Core Requirements

### 1. Trajectory Capture
**Priority:** P0 (Critical)
**Description:** Capture all agent tool calls, intermediate states, and outcomes during task execution.

**Functional Requirements:**
- FR-1.1: Intercept all tool invocations during LangGraph execution
- FR-1.2: Record tool name, input parameters, output results, and success/failure status
- FR-1.3: Capture timing information (latency) for each tool call
- FR-1.4: Track token usage for LLM calls
- FR-1.5: Maintain sequence order of tool calls (trajectory)

**Non-Functional Requirements:**
- NFR-1.1: Minimal performance overhead (< 50ms per tool call)
- NFR-1.2: Thread-safe callback execution
- NFR-1.3: Support both sync and async tool execution

### 2. Metrics Scoring
**Priority:** P0 (Critical)
**Description:** Calculate weighted scores for each trajectory execution.

**Functional Requirements:**
- FR-2.1: Implement weighted scoring formula:
  - Tool success rate (40%)
  - Execution latency (20%)
  - Token cost (20%)
  - Outcome match (20%)
- FR-2.2: Normalize metrics to 0.0-1.0 scale
- FR-2.3: Store individual metric components for analysis

**Non-Functional Requirements:**
- NFR-2.1: Configurable weight parameters
- NFR-2.2: Extensible metric framework

### 3. Vector Storage (Qdrant)
**Priority:** P0 (Critical)
**Description:** Store scored trajectories as embeddings for semantic retrieval.

**Functional Requirements:**
- FR-3.1: Create embeddings from task + trajectory summary
- FR-3.2: Store in Qdrant with metadata (score, tool calls, timestamp)
- FR-3.3: Support cosine similarity search
- FR-3.4: Filter by score threshold (≥ 0.7)

**Non-Functional Requirements:**
- NFR-3.1: Python 3.14+ compatible (NOT ChromaDB)
- NFR-3.2: Persistent local storage
- NFR-3.3: Async API support for non-blocking I/O

### 4. PII Redaction
**Priority:** P0 (Critical - Security)
**Description:** Remove sensitive data before storing trajectories.

**Functional Requirements:**
- FR-4.1: Redact email addresses
- FR-4.2: Redact phone numbers (US format)
- FR-4.3: Redact SSN
- FR-4.4: Redact credit card numbers
- FR-4.5: Redact API keys (32+ char alphanumeric)

**Non-Functional Requirements:**
- NFR-4.1: Redaction happens BEFORE embedding
- NFR-4.2: Preserve trajectory structure

### 5. Planning Agent
**Priority:** P1 (High)
**Description:** Retrieve similar historical workflows and craft success plans.

**Functional Requirements:**
- FR-5.1: Query Qdrant for top-3 similar workflows
- FR-5.2: Use LLM to synthesize success plan from historical data
- FR-5.3: Inject plan into execution agent's context
- FR-5.4: Handle cold start (no similar workflows found)

**Non-Functional Requirements:**
- NFR-5.1: Planning adds < 2s latency
- NFR-5.2: Graceful degradation on retrieval failure

## Acceptance Criteria

### Phase 1: Tool-Level Metrics
- ✅ TrajectoryCallbackHandler captures all tool calls
- ✅ Metrics recorded: success, latency, tokens
- ✅ Unit tests for callback handler
- ✅ Integration test with agent execution

### Phase 2: Success Scoring
- ✅ MetricsMiddleware calculates weighted scores
- ✅ Score normalization verified
- ✅ Test with mock metrics (0.0-1.0 range)

### Phase 3: Qdrant Storage
- ✅ Collection created on initialization
- ✅ Trajectories stored with embeddings
- ✅ Semantic search returns similar workflows
- ✅ Score filtering works (≥ 0.7 threshold)

### Phase 4: PII Redaction
- ✅ All 5 PII types redacted in tests
- ✅ Original trajectory structure preserved
- ✅ No false positives (safe data not redacted)

### Phase 5: Planning Agent
- ✅ Retrieves and ranks similar workflows
- ✅ Generates success plans from historical data
- ✅ Plans injected into agent context
- ✅ End-to-end test: task → plan → execute → store

## Out of Scope (Future Work)
- User feedback mechanism for outcome_match metric
- Multi-task domain separation (separate Qdrant collections)
- Real-time trajectory visualization
- Batch trajectory import/export
- A/B testing of scoring weights
- Distributed Qdrant deployment

## Constraints
- **Python Version:** 3.14+ (ChromaDB incompatible, must use Qdrant)
- **Dependencies:** Must use existing LangChain/LangGraph patterns
- **Storage:** Local persistent Qdrant (no cloud services)
- **Testing:** pytest with asyncio support
- **Performance:** < 100ms overhead per tool call

## Success Metrics
- **Trajectory Capture Rate:** 100% of tool calls captured
- **Storage Success:** > 99% of trajectories stored successfully
- **Retrieval Latency:** < 500ms for Qdrant queries
- **Plan Quality:** Measured by improved task success rate
- **PII Redaction:** 0% PII leakage in stored trajectories
