# Research: Agent Trajectory Collection & RAG-Based Workflow Planning

**Date:** 2026-01-22
**Query:** How to collect agent workflow/tool calls as trajectories, set success/failed metrics, store in vector DB, and build planning agent for workflow retrieval

## Summary

LangGraph provides built-in trajectory collection via streaming callbacks with `stream_mode="debug"` and `subgraphs=True`. The [`agentevals`](https://github.com/langchain-ai/agentevals) library offers trajectory matching evaluators. For vector storage, **Qdrant** (Python 3.14+ compatible) enables semantic retrieval of similar workflows via cosine similarity, which can power a planning agent that crafts success plans from historical data.

## Key Concepts

- **Trajectory**: Sequence of nodes visited and tools called during agent execution
- **Callback Handler**: LangChain mechanism for capturing telemetry (tokens, metadata, scores)
- **Vector Embeddings**: Numerical representations of trajectories for semantic similarity search
- **RAG Planning**: Retrieval-Augmented Generation for workflow planning using historical success patterns
- **Weighted Scoring**: Multi-dimensional evaluation (tool success, latency, token cost, accuracy)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENT TRAJECTORY COLLECTION & RAG PLANNING                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                             EXECUTION FLOW (Forward)                                  ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────┐
  │   User Task  │  "Post a message to Facebook group"
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                    PLANNING AGENT                            │
  │  ┌────────────────────────────────────────────────────────┐ │
  │  │  1. Embed task → Query Qdrant                          │ │
  │  │     [OpenAI text-embedding-3-small]                    │ │
  │  └──────────────────────┬─────────────────────────────────┘ │
  │                         │                                    │
  │  ┌──────────────────────▼─────────────────────────────────┐ │
  │  │  2. Retrieve Top-3 Similar Workflows                   │ │
  │  │     Filter: score ≥ 0.7, cosine similarity             │ │
  │  │                                                         │ │
  │  │     ┌─────────────────────────────────────────────┐   │ │
  │  │     │ Workflow 1: score=0.92, similarity=0.89     │   │ │
  │  │     │   browser_snapshot → browser_click → ...    │   │ │
  │  │     ├─────────────────────────────────────────────┤   │ │
  │  │     │ Workflow 2: score=0.88, similarity=0.85     │   │ │
  │  │     │   browser_navigate → browser_type → ...     │   │ │
  │  │     └─────────────────────────────────────────────┘   │ │
  │  └──────────────────────┬─────────────────────────────────┘ │
  │                         │                                    │
  │  ┌──────────────────────▼─────────────────────────────────┐ │
  │  │  3. Craft Success Plan (LLM)                           │ │
  │  │     Input: task + historical_workflows                 │ │
  │  │     Output: Step-by-step execution plan                │ │
  │  └──────────────────────┬─────────────────────────────────┘ │
  └─────────────────────────┼────────────────────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────┐
         │  Enhanced Prompt (task + plan)       │
         │  "Post a message to Facebook group   │
         │   following these 3 steps..."        │
         └──────────────┬───────────────────────┘
                        │
                        ▼
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                        EXECUTION AGENT (LangGraph)                                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                                                                               │
  │  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐    │
  │  │    Agent    │───▶│    Tools     │───▶│   Browser   │───▶│  Result   │    │
  │  │  (Reasoning)│    │  (Actions)   │    │  (Playwright)│    │           │    │
  │  └─────────────┘    └──────────────┘    └─────────────┘    └───────────┘    │
  │         │                  │                   │                             │
  │         │                  ▼                   ▼                             │
  │         │         ┌────────────────────────────────┐                          │
  │         │         │  TrajectoryCallbackHandler     │                          │
  │         │         │  • on_tool_start()             │                          │
  │         │         │  • on_tool_end()  ◀────────────┼── CAPTURE METRICS       │
  │         │         │  • on_tool_error()             │                          │
  │         │         └────────────┬───────────────────┘                          │
  │         │                      │                                              │
  │         ▼                      ▼                                              │
  │  ┌──────────────────────────────────────────────────────────────────┐        │
  │  │                     Captured Trajectory                          │        │
  │  │  {                                                                │        │
  │  │    "trajectory": ["agent", "tools", "browser_click", ...],       │        │
  │  │    "tool_calls": [                                               │        │
  │  │      {"tool": "browser_click", "input": "...", "success": true},  │        │
  │  │      {"tool": "browser_type", "input": "...", "success": true}    │        │
  │  │    ],                                                            │        │
  │  │    "metrics": {                                                  │        │
  │  │      "tool_success": [1, 1],                                     │        │
  │  │      "latencies": [0.234, 1.567],                               │        │
  │  │      "token_usage": [{"total_tokens": 1234}]                    │        │
  │  │    }                                                             │        │
  │  │  }                                                              │        │
  │  └────────────────────────────┬─────────────────────────────────────┘        │
  └───────────────────────────────┼───────────────────────────────────────────────┘
                                  │
                                  ▼
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    METRICS MIDDLEWARE (Post-Processing)                                ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │  MetricsMiddleware                                                                │
  │                                                                                  │
  │  1. CALCULATE SCORE (Weighted: 40/20/20/20)                                      │
  │     ┌─────────────────────────────────────────────────────────────────┐          │
  │     │ tool_success: 100% → 0.40                                       │          │
  │     │ latency: 0.9s (< 30s target) → 0.20                             │          │
  │     │ tokens: 1234 (< 5000 target) → 0.20                             │          │
  │     │ outcome_match: 0.8 (user feedback) → 0.16                       │          │
  │     │ ─────────────────────────────────────                            │          │
  │     │ TOTAL SCORE: 0.96 ✅                                             │          │
  │     └─────────────────────────────────────────────────────────────────┘          │
  │                                       │                                            │
  │                                       ▼                                            │
  │  2. REDACT PII                                                                    │
  │     ┌─────────────────────────────────────────────────────────────────┐          │
  │     │ Tool Input Before: "user@example.com called (555) 123-4567"     │          │
  │     │ Tool Input After:  "[REDACTED_EMAIL] called [REDACTED_PHONE]"   │          │
  │     │                                                                 │          │
  │     │ Patterns: emails, phones, SSN, credit cards, API keys           │          │
  │     └─────────────────────────────────────────────────────────────────┘          │
  │                                       │                                            │
  │                                       ▼                                            │
  │  3. CREATE EMBEDDING                                                              │
  │     ┌─────────────────────────────────────────────────────────────────┐          │
  │     │ Text: "Post to Facebook group → browser_snapshot →               │          │
  │     │        browser_click → browser_type → success"                   │          │
  │     │                                                                 │          │
  │     │ Embedding: [0.1234, -0.5678, 0.9012, ...]  (1536 dimensions)    │          │
  │     └─────────────────────────────────────────────────────────────────┘          │
  │                                       │                                            │
  └───────────────────────────────┬───────┴──────────────────────────────────────────┘
                                  │
                                  ▼
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                          VECTOR STORAGE (Qdrant)                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │  Qdrant: agent_trajectories collection                                            │
  │                                                                                  │
  │  Point {                                                                         │
  │    id: "post_to_fb_group_2026-01-22T14:35:22",                                   │
  │    vector: [0.1234, -0.5678, ...],  // 1536-dim embedding                        │
  │    payload: {                                                                     │
  │      "task": "Post a message to Facebook group",                                  │
  │      "score": 0.96,                                                               │
  │      "trajectory": ["browser_snapshot", "browser_click", "browser_type"],        │
  │      "tool_calls": [...],                                                         │
  │      "timestamp": "2026-01-22T14:35:22"                                           │
  │    }                                                                              │
  │  }                                                                                │
  │                              │                                                     │
  │                              ▼                                                     │
  │                   ┌─────────────────┐                                            │
  │                   │  Indexed for:   │                                            │
  │                   │  • Similarity   │  (cosine distance)                         │
  │                   │  • Score filter │  (≥ 0.7 threshold)                         │
  │                   │  • Timestamp    │  (recency)                                 │
  │                   └─────────────────┘                                            │
  └──────────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
           ┌────────────────┐      ┌──────────────┐
           │   Future       │      │   Analytics  │
           │   Retrieval    │      │   Dashboard  │
           └────────────────┘      └──────────────┘


╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                              COMPLETE DATAFLOW SUMMARY                                 ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

  1. USER TASK
     │
     ├────▶ PLANNING AGENT
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
     ├────▶ METRICS MIDDLEWARE
     │       ├─ Calculate weighted score (40/20/20/20)
     │       ├─ Redact PII (emails, phones, SSN, CC, keys)
     │       └─ Create embedding (task + trajectory)
     │
     └────▶ QDRANT STORAGE
             ├─ Store point (vector + metadata)
             ├─ Index for similarity search
             └─ Available for future retrieval


╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                         KEY OPTIMIZATION POINTS                                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

  ⚡ Async QdrantClient for non-blocking I/O
  ⚡ Batch embeddings for multiple trajectories
  ⚡ Score threshold (0.7) filters low-quality workflows
  ⚡ PII redaction BEFORE embedding (security)
  ⚡ Separate collections per task domain (scalability)

```

## Best Practices

1. **Use LangGraph streaming with `debug` mode** for comprehensive trajectory capture
2. **Implement custom callback handlers** extending `BaseCallbackHandler` for metrics collection
3. **Store trajectories as structured JSON** with embeddings of task description + tool sequence
4. **Use cosine similarity retrieval** to find historically successful workflows
5. **Apply weighted scoring**: tool_success (40%), latency (20%), token_cost (20%), outcome_match (20%)
6. **PII redaction** critical before storing trajectories in vector DB

## Security Considerations

- ⚠️ **PII in trajectories**: Tool inputs/outputs may contain user data - must redact before storage
- ⚠️ **API keys in prompts**: Sanitize prompts before embedding
- ⚠️ **Vector DB access control**: Qdrant collections need authentication (API keys) in production
- ⚠️ **Prompt injection via retrieval**: Validate retrieved workflows before feeding to agent

## Implementation Approaches

### Approach 1: LangGraph Streaming + Custom Callback

**Pros:** Built-in support, minimal overhead, captures subgraphs
**Cons:** Requires manual parsing of debug chunks, no automatic scoring

```python
import time
from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List

class TrajectoryCallbackHandler(BaseCallbackHandler):
    """Capture tool calls and metrics for trajectory storage."""

    def __init__(self):
        self.trajectory = []
        self.tool_calls = []
        self.metrics = {
            "tool_success": [],
            "latencies": [],
            "token_usage": []
        }

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Track tool invocation start."""
        self.tool_calls.append({
            "tool": serialized["name"],
            "input": input_str,
            "start_time": time.time()
        })

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Track tool completion and success."""
        if self.tool_calls:
            self.tool_calls[-1]["output"] = output
            self.tool_calls[-1]["success"] = True
            self.metrics["tool_success"].append(1)

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Track tool failures."""
        if self.tool_calls:
            self.tool_calls[-1]["success"] = False
            self.metrics["tool_success"].append(0)

# Usage with LangGraph
async def run_graph_with_trajectory(task: str) -> dict:
    """Run graph and capture trajectory with metrics."""
    callback = TrajectoryCallbackHandler()
    trajectory = []

    async for namespace, chunk in graph.astream(
        {"messages": [{"role": "user", "content": task}]},
        subgraphs=True,
        stream_mode="debug",
        config={"callbacks": [callback]}
    ):
        if chunk['type'] == 'task':
            trajectory.append(chunk['payload']['name'])
            if chunk['payload']['name'] == 'tools':
                for tc in chunk['payload']['input']['messages'][-1].tool_calls:
                    trajectory.append(tc['name'])

    return {
        "trajectory": trajectory,
        "tool_calls": callback.tool_calls,
        "metrics": callback.metrics,
        "task": task
    }
```

### Approach 2: LangSmith/Langfuse Integration

**Pros:** Automatic tracing, UI visualization, scoring APIs, production-ready
**Cons:** External dependency, costs for hosted version

```python
from langfuse.langchain import CallbackHandler
from langchain_openai import OpenAIEmbeddings

langfuse_handler = CallbackHandler()

# Run with automatic tracing
result = await graph.ainvoke(
    {"messages": [HumanMessage(content=task)]},
    config={"callbacks": [langfuse_handler]}
)

# Score the run
langfuse_handler.score(
    name="workflow_success",
    value=calculate_weighted_score(metrics),
    comment="Based on tool success rate and outcome"
)
```

### Approach 3: Custom Metrics Middleware

**Pros:** Full control, custom scoring logic, PII redaction built-in
**Cons:** More code to maintain, need to handle edge cases

```python
import json
import time
from datetime import datetime
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

class MetricsMiddleware:
    """Collect and score agent trajectories with PII redaction."""

    def __init__(self, storage_path: str = "./trajectories", qdrant_path: str = "./qdrant_db"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(path=qdrant_path)

        # Create collection if it doesn't exist
        collections = self.qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]

        if "agent_trajectories" not in collection_names:
            self.qdrant_client.create_collection(
                collection_name="agent_trajectories",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

        self.emb = OpenAIEmbeddings()

    def calculate_score(self, metrics: dict) -> float:
        """Weighted scoring: success(40%), latency(20%), cost(20%), outcome(20%)."""
        tool_success = sum(metrics["tool_success"]) / max(len(metrics["tool_success"]), 1)

        # Normalize latency (lower is better, target < 30s)
        avg_latency = sum(metrics["latencies"]) / max(len(metrics["latencies"]), 1)
        latency_score = max(0, 1 - (avg_latency / 30))

        # Token cost (lower is better, target < 5000)
        total_tokens = sum(m["total_tokens"] for m in metrics["token_usage"])
        cost_score = max(0, 1 - (total_tokens / 5000))

        # Outcome match (placeholder - needs user feedback)
        outcome_score = metrics.get("outcome_match", 0.5)

        return 0.4 * tool_success + 0.2 * latency_score + 0.2 * cost_score + 0.2 * outcome_score

    def redact_pii(self, trajectory: dict) -> dict:
        """Remove sensitive data before storage."""
        import re

        trajectory_copy = json.loads(json.dumps(trajectory))

        for tool_call in trajectory_copy.get("tool_calls", []):
            if "input" in tool_call:
                input_str = str(tool_call["input"])

                # Redact emails
                input_str = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', input_str)

                # Redact US phone numbers
                input_str = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[REDACTED_PHONE]', input_str)

                # Redact SSN
                input_str = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', input_str)

                # Redact credit cards (basic pattern)
                input_str = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[REDACTED_CC]', input_str)

                # Redact API keys (basic heuristic)
                input_str = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[REDACTED_KEY]', input_str)

                tool_call["input"] = input_str

        return trajectory_copy

    async def store_trajectory(self, trajectory: dict, task_label: str):
        """Store scored trajectory in vector DB."""
        score = self.calculate_score(trajectory["metrics"])
        clean_trajectory = self.redact_pii(trajectory)

        # Create embedding from task + trajectory summary
        trajectory_text = f"{task_label} -> {clean_trajectory['trajectory']}"
        embedding = await self.emb.aembed_text(trajectory_text)

        # Store with metadata
        record = {
            "id": f"{task_label}_{datetime.now().isoformat()}",
            "embedding": embedding,
            "metadata": {
                "task": task_label,
                "score": score,
                "trajectory": clean_trajectory['trajectory'],
                "tool_calls": clean_trajectory['tool_calls'],
                "timestamp": datetime.now().isoformat()
            },
            "document": trajectory_text
        }

        # Add to Qdrant
        self.qdrant_client.upsert(
            collection_name="agent_trajectories",
            points=[PointStruct(
                id=record["id"],
                vector=record["embedding"],
                payload=record["metadata"]
            )]
        )
```

## Vector Storage with Qdrant

### Setup

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# In-memory (for development)
client = QdrantClient(":memory:")

# Or persistent storage
client = QdrantClient(path="./qdrant_db")

# Create collection
client.create_collection(
    collection_name="agent_trajectories",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)
```

### Async Setup (Recommended for LangGraph)

```python
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

# Async client for better performance with LangGraph
async_client = AsyncQdrantClient(path="./qdrant_db")

# Collection creation is same API
await async_client.create_collection(
    collection_name="agent_trajectories",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# Use async methods
await async_client.upsert(
    collection_name="agent_trajectories",
    points=[PointStruct(...)]
)
```

### Retrieval for Planning

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, Range
from langchain_openai import OpenAIEmbeddings

def retrieve_similar_workflows(
    task: str,
    top_k: int = 3,
    min_score: float = 0.7,
    client: QdrantClient = None
) -> list:
    """Retrieve historically successful workflows via cosine similarity.

    Args:
        task: User task description
        top_k: Number of results to return
        min_score: Minimum workflow score threshold (0.0-1.0)
        client: Qdrant client instance (optional)

    Returns:
        List of similar workflows with metadata
    """
    try:
        emb = OpenAIEmbeddings()
        query_embedding = emb.embed_query(task)

        results = client.search(
            collection_name="agent_trajectories",
            query_vector=query_embedding,
            query_filter=Filter(
                must=[{
                    "key": "score",
                    "range": Range(gte=min_score)
                }]
            ),
            limit=top_k
        )

        return [
            {
                "trajectory": r.payload["trajectory"],
                "tool_calls": r.payload["tool_calls"],
                "score": r.payload["score"],
                "similarity": r.score,
                "metadata": r.payload
            }
            for r in results
        ]

    except Exception as e:
        print(f"Error retrieving workflows: {e}")
        return []  # Return empty list on failure
```

## Planning Agent Architecture

### Agent Structure

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

planning_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a workflow planning agent. Your task is to craft a success plan based on historical workflows.

Historical successful workflows:
{historical_workflows}

User task: {task}

Analyze the historical workflows and craft a step-by-step plan that combines the best patterns.
Focus on:
1. Tool call sequences that worked
2. Parameter patterns
3. Error handling approaches

Output the plan as a numbered list of steps."""),
    ("user", "{task}")
])

planner_llm = ChatOpenAI(model="gpt-4o")
planner_chain = planning_prompt | planner_llm

def craft_success_plan(task: str, client: QdrantClient = None) -> str:
    """Retrieve similar workflows and generate plan."""
    similar = retrieve_similar_workflows(task, client=client)

    if not similar:
        return "No similar workflows found. Proceed with standard execution."

    historical_context = "\n\n".join([
        f"Workflow (score: {w['score']:.2f}, similarity: {w['similarity']:.2f}):\n{' -> '.join(w['trajectory'])}"
        for w in similar
    ])

    plan = planner_chain.invoke({
        "task": task,
        "historical_workflows": historical_context
    })

    return plan.content
```

### Integration with Execution Agent

```python
from qdrant_client import QdrantClient

class PlanningAgent:
    """Determines next task and crafts success plan."""

    def __init__(self, execution_agent, qdrant_client: QdrantClient):
        self.execution_agent = execution_agent
        self.qdrant_client = qdrant_client

    async def determine_next_task(self, context: dict) -> tuple[str, list]:
        """Retrieve similar workflows and craft plan for execution agent."""
        current_task = context.get("task")

        # Craft success plan (includes retrieval)
        plan = craft_success_plan(current_task, client=self.qdrant_client)

        # Get similar workflows for context
        similar_workflows = retrieve_similar_workflows(current_task, client=self.qdrant_client)

        # Feed to execution agent with context
        enhanced_prompt = f"""Task: {current_task}

Success Plan (based on {len(similar_workflows)} similar historical workflows):
{plan}

Execute this task following the success plan above."""

        return enhanced_prompt, similar_workflows
```

## Recommended Stack

| Purpose | Package | Why |
|---------|---------|-----|
| Trajectory capture | LangGraph `astream(debug)` | Built-in, subgraph support |
| Scoring | Custom + `agentevals` | Full control over weighted metrics |
| Vector DB | **Qdrant** (NOT ChromaDB) | Python 3.14+ compatible, fast, filtering support |
| Embeddings | OpenAI `text-embedding-3-small` | Cost-effective, good quality |
| Tracing (optional) | Langfuse or LangSmith | Production observability |
| PII redaction | Microsoft Presidio | Production-grade entity recognition |

### ⚠️ **CRITICAL: ChromaDB NOT Compatible with Python 3.14**

**Issue**: ChromaDB only supports Python ≤3.12. Fails with `lz4` build errors on 3.14+ ([GitHub #5643](https://github.com/chroma-core/chroma/issues/5643))

**Alternatives for Python 3.14+**:
- **Qdrant** ✅ (Recommended) - Rust-based, 1GB free tier, excellent filtering
- **FAISS** ✅ - Meta's library, pure in-memory (no persistence by default)
- **pgvector** ✅ - Postgres extension, if already using Postgres
- **Weaviate** ✅ - Docker-based, good for production

**Qdrant Setup Example**:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# In-memory (for development)
client = QdrantClient(":memory:")

# Or persistent
client = QdrantClient(path="./qdrant_db")

# Create collection
client.create_collection(
    collection_name="agent_trajectories",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)  # OpenAI embedding size
)

# Store trajectory
client.upsert(
    collection_name="agent_trajectories",
    points=[PointStruct(
        id=f"{task_label}_{datetime.now().timestamp()}",
        vector=embedding,
        payload={
            "task": task_label,
            "score": score,
            "trajectory": clean_trajectory['trajectory'],
            "tool_calls": clean_trajectory['tool_calls']
        }
    )]
)

# Retrieve similar workflows
results = client.search(
    collection_name="agent_trajectories",
    query_vector=embedding,
    query_filter={"must": [{"key": "score", "range": {"gte": 0.7}}]},
    limit=3
)
```

## Common Pitfalls

1. **❌ Not redacting PII** — Tool inputs/outputs often contain emails, phones, addresses. Use Presidio or regex patterns.

2. **❌ Ignoring ref staleness** — In LangGraph, state changes make previous references invalid. Always get fresh refs.

3. **❌ Storing raw trajectories** — Too large for embeddings. Summarize to: task + tool sequence + outcome.

4. **❌ No weighted scoring** — Binary success/failure loses nuance. Include latency, cost, accuracy dimensions.

5. **❌ Cold start problem** — Vector DB empty initially. Seed with successful manual workflows first.

6. **❌ Retrieval without validation** — Retrieved workflows may not match. Validate task similarity threshold (>0.7 cosine).

## References

- [LangChain Trajectory Evaluation Docs](https://docs.langchain.com/langsmith/trajectory-evals)
- [agentevals Library](https://github.com/langchain-ai/agentevals)
- [LangGraph Streaming Tutorial](https://langchain-ai.github.io/langgraph/how-tos/streaming-subgraphs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant Python Client](https://github.com/qdrant/qdrant-client)
- [Langfuse LangGraph Integration](https://langfuse.com/guides/cookbook/example_langgraph_agents)
- [ChromaDB Python 3.14 Issue #5643](https://github.com/chroma-core/chroma/issues/5643)
- [Vector Database Comparison 2025](https://www.firecrawl.dev/blog/best-vector-databases-2025)

## Next Steps

1. **Implement `TrajectoryCallbackHandler`** extending `BaseCallbackHandler`
2. **Add `MetricsMiddleware`** with weighted scoring and PII redaction
3. **Set up Qdrant** (NOT ChromaDB - incompatible with Python 3.14):
   ```bash
   .venv/bin/pip install qdrant-client
   ```
4. **Build `PlanningAgent`** that retrieves and feeds plans to execution agent
5. **Seed vector DB** with 5-10 successful manual workflows for cold start
6. **Test retrieval quality** with different task variations

## Unresolved Questions

- Weight formula for scoring: should outcome_match be higher than 20%?
- Embed strategy: task-only vs task+trajectory vs trajectory-only?
- Retrieval threshold: cosine similarity cutoff (0.7 too strict/lenient)?
- Plan injection: prepend to system prompt or user message?
- Cold start: minimum trajectories before reliable retrieval?
