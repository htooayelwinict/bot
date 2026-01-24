# References & External Documentation

## LangChain / LangGraph

### Callback Handlers
**Official Docs:** https://python.langchain.com/docs/modules/callbacks/

**Key Concepts:**
- `BaseCallbackHandler` - Base class for custom callbacks
- `callbacks` parameter - Pass to invoke/astream/stream
- Event types: `on_tool_start`, `on_tool_end`, `on_llm_start`, `on_llm_end`

**Example:**
```python
from langchain_core.callbacks import BaseCallbackHandler

class MyCallback(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"Tool {serialized['name']} started with input: {input_str}")

    def on_tool_end(self, output, **kwargs):
        print(f"Tool ended with output: {output}")
```

### LangGraph Streaming
**Official Docs:** https://langchain-ai.github.io/langgraph/how-tos/streaming-subgraphs/

**Stream Modes:**
- `values` - Stream state values
- `updates` - Stream node updates
- `debug` - Full debug info with subgraphs

**Example:**
```python
async for chunk in agent.astream(
    input_data,
    stream_mode="debug",
    subgraphs=True,
):
    print(chunk)
```

### LangSmith Trajectory Evaluation
**Docs:** https://docs.langchain.com/langsmith/trajectory-evals

**Library:** https://github.com/langchain-ai/agentevals

**Usage:**
```python
from agentevals import TrajectoryEvaluator

evaluator = TrajectoryEvaluator()
result = evaluator.evaluate(
    trajectory=trajectory,
    expected_tools=["browser_click", "browser_type"],
)
```

## Qdrant Vector Database

### Python Client
**GitHub:** https://github.com/qdrant/qdrant-client
**Docs:** https://python-client.qdrant.tech/

**Installation:**
```bash
pip install qdrant-client>=1.12.0
```

**Basic Usage:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Initialize
client = QdrantClient(path="./qdrant_db")

# Create collection
client.create_collection(
    collection_name="agent_trajectories",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# Insert points
client.upsert(
    collection_name="agent_trajectories",
    points=[PointStruct(
        id="trajectory_1",
        vector=[0.1, 0.2, ...],
        payload={"task": "post to facebook", "score": 0.92}
    )]
)

# Search
results = client.search(
    collection_name="agent_trajectories",
    query_vector=[0.1, 0.2, ...],
    limit=3
)
```

### Async Client
**Important for LangGraph:**
```python
from qdrant_client import AsyncQdrantClient

client = AsyncQdrantClient(path="./qdrant_db")

# Use await
await client.upsert(...)
results = await client.search(...)
```

### Filtering
**Docs:** https://qdrant.tech/documentation/concepts/filtering/

**Example:**
```python
from qdrant_client.models import Filter, Range

results = client.search(
    collection_name="agent_trajectories",
    query_vector=[...],
    query_filter=Filter(
        must=[{
            "key": "score",
            "range": Range(gte=0.7)
        }]
    ),
    limit=10
)
```

## OpenAI Embeddings

### LangChain Integration
**Docs:** https://python.langchain.com/docs/integrations/text_embedding/openai/

**Recommended Model:** `text-embedding-3-small` (1536 dimensions)

**Cost:** $0.00002 / 1K tokens (very cost-effective)

**Example:**
```python
from langchain_openai import OpenAIEmbeddings

emb = OpenAIEmbeddings(model="text-embedding-3-small")
vector = emb.embed_query("Post a message to Facebook group")
```

## PII Redaction

### Microsoft Presidio
**GitHub:** https://github.com/microsoft/presidio
**Docs:** https://microsoft.github.io/presidio/

**Installation:**
```bash
pip install presidio
```

**Example:**
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

text = "Call me at (555) 123-4567 or email user@example.com"
results = analyzer.analyze(text=text, language='en')
anonymized = anonymizer.anonymize(text=text, analyzer_results=results)

# Output: "Call me at <PHONE_NUMBER> or email <EMAIL>"
```

### Regex Patterns (Fallback)
**Python `re` module:**
```python
import re

# Email
r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# US Phone
r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'

# SSN
r'\b\d{3}-\d{2}-\d{4}\b'

# Credit Card
r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'

# API Key (heuristic)
r'\b[A-Za-z0-9]{32,}\b'
```

## Python 3.14 Compatibility

### ChromaDB Issue
**GitHub Issue:** https://github.com/chroma-core/chroma/issues/5643

**Summary:** ChromaDB does NOT support Python > 3.12 due to `lz4` build errors.

**Workaround:** Use Qdrant, FAISS, or pgvector instead.

### Qdrant Compatibility
**Status:** ✅ Fully compatible with Python 3.14+
**Tested:** Qdrant client 1.12.0+ on Python 3.14

## Testing Patterns

### Pytest Async
**Docs:** https://pytest-asyncio.readthedocs.io/

**Example:**
```python
@pytest.mark.asyncio
async def test_trajectory_capture():
    callback = TrajectoryCallbackHandler()
    # Test async execution
    result = await agent.ainvoke(task, config={"callbacks": [callback]})
    assert len(callback.trajectory) > 0
```

### Mock Qdrant
**Example:**
```python
@pytest.fixture
def mock_qdrant():
    with patch("qdrant_client.QdrantClient") as mock:
        client = mock.return_value
        client.search.return_value = [
            Mock(payload={"trajectory": ["tool1", "tool2"]})
        ]
        yield client
```

## Best Practices

### LangGraph Callbacks
1. **Use `BaseCallbackHandler`** for custom callbacks
2. **Async callbacks** use `AsyncCallbackHandler` base
3. **Pass via config** not direct parameter
4. **Thread-safe** operations only (use ContextVars)

### Qdrant Performance
1. **Batch operations** with `upsert()` multiple points
2. **Use async client** for non-blocking I/O
3. **Persistent storage** for production (`path=` not `:memory:`)
4. **Filter early** to reduce search space

### PII Redaction
1. **Redact before embedding** (security)
2. **Preserve structure** for trajectory analysis
3. **Test edge cases** (over-redaction, false positives)
4. **Consider Presidio** for production (regex only catches common patterns)

### Scoring Metrics
1. **Normalize to 0.0-1.0** before weighting
2. **Log raw values** for debugging
3. **Configurable weights** via env vars
4. **Handle missing metrics** gracefully

## External Libraries Comparison

### Vector DBs (Python 3.14 Compatible)
| Database | Pros | Cons | Recommended For |
|----------|------|------|------------------|
| **Qdrant** | Rust-based, fast, filtering, 1GB free | Learning curve | ✅ This project |
| FAISS | In-memory, fast, Meta-backed | No persistence, no filtering | Research only |
| pgvector | Postgres integration, SQL queries | Requires Postgres | Existing Postgres users |
| Weaviate | Docker-based, production-ready | Heavier setup | Large-scale deployments |

### PII Redaction Libraries
| Library | Pros | Cons | Recommended For |
|---------|------|------|------------------|
| **Presidio** | Production-grade, ML-based, extensible | Slower, requires models | ✅ Production |
| Regex | Fast, simple, no dependencies | Limited patterns, false positives | ✅ Development/MVP |

## Code Examples from Research

### Research Source
**File:** [research.md](plan/research-agent-metrics-20260122-164610/research.md)

**Key Sections:**
- Lines 42-95: LangGraph streaming + custom callback
- Lines 130-209: Custom metrics middleware with Qdrant
- Lines 267-308: Retrieval for planning
- Lines 312-323: Planning agent integration

**Reference Implementation:**
```python
# From research.md:267-308
def retrieve_similar_workflows(
    task: str,
    top_k: int = 3,
    min_score: float = 0.7,
    client: QdrantClient = None
) -> list:
    """Retrieve historically successful workflows via cosine similarity."""
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
        return []
```
