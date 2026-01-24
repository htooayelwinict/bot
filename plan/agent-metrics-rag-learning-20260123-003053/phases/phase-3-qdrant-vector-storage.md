# Phase 3: Qdrant Vector Storage

## Objective
Set up Qdrant vector database and implement trajectory storage with OpenAI embeddings for semantic retrieval.

## Prerequisites
- Phase 2 complete (scoring and summarization working)
- Qdrant client installed (`pip install -e ".[memory]"`)
- OpenAI API key available

## Tasks

### 3.1 Create Qdrant Client Manager
- **File:** `src/storage/qdrant_client.py` (new)
- Initialize AsyncQdrantClient with persistent storage
- Create `agent_trajectories` collection if not exists
- Configure vector params: 1536 dimensions, COSINE distance
- Singleton pattern for client reuse

**Implementation:**
```python
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

class QdrantManager:
    _instance: AsyncQdrantClient | None = None

    @classmethod
    async def get_client(cls) -> AsyncQdrantClient:
        if cls._instance is None:
            cls._instance = AsyncQdrantClient(path="./qdrant_db")
            await cls._ensure_collection(cls._instance)
        return cls._instance

    @staticmethod
    async def _ensure_collection(client: AsyncQdrantClient):
        collections = await client.get_collections()
        if not any(c.name == "agent_trajectories" for c in collections.collections):
            await client.create_collection(
                collection_name="agent_trajectories",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
```

### 3.2 Embedding Service
- **File:** `src/storage/embeddings.py` (new)
- Wrap OpenAI embeddings (`text-embedding-3-small`)
- Create `embed_trajectory()` function
- Handle API errors gracefully
- Cache embeddings (optional)

**Implementation:**
```python
from langchain_openai import OpenAIEmbeddings

_emb_instance: OpenAIEmbeddings | None = None

def get_embeddings() -> OpenAIEmbeddings:
    global _emb_instance
    if _emb_instance is None:
        _emb_instance = OpenAIEmbeddings(model="text-embedding-3-small")
    return _emb_instance

async def embed_trajectory(text: str) -> list[float]:
    """Create embedding from trajectory summary."""
    emb = get_embeddings()
    return await emb.aembed_query(text)
```

### 3.3 Trajectory Storage
- **File:** `src/storage/trajectory_store.py` (new)
- Implement `store_trajectory()` async function
- Create embedding from trajectory summary
- Insert into Qdrant with metadata (score, tool calls, timestamp)
- Use `PointStruct` for structured data

**Implementation:**
```python
from qdrant_client.models import PointStruct
from datetime import datetime

async def store_trajectory(
    task: str,
    trajectory_summary: str,
    score: float,
    tool_calls: list[dict],
    client: AsyncQdrantClient
):
    """Store trajectory in Qdrant with embedding."""
    # Create embedding
    embedding = await embed_trajectory(
        f"{task} -> {trajectory_summary}"
    )

    # Store point
    await client.upsert(
        collection_name="agent_trajectories",
        points=[PointStruct(
            id=f"{task}_{datetime.now().timestamp()}",
            vector=embedding,
            payload={
                "task": task,
                "score": score,
                "trajectory_summary": trajectory_summary,
                "tool_calls": tool_calls,
                "timestamp": datetime.now().isoformat()
            }
        )]
    )
```

### 3.4 Semantic Search
- **File:** `src/storage/retrieval.py` (new)
- Implement `retrieve_similar_trajectories()` function
- Embed task query
- Search Qdrant with score filter (≥ 0.7)
- Return top-k results with similarity scores

**Implementation:**
```python
from qdrant_client.models import Filter, Range

async def retrieve_similar_trajectories(
    task: str,
    top_k: int = 3,
    min_score: float = 0.7,
    client: AsyncQdrantClient
) -> list[dict]:
    """Retrieve similar historical workflows."""
    # Embed query
    query_embedding = await embed_trajectory(task)

    # Search with filter
    results = await client.search(
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

    # Format results
    return [
        {
            "trajectory": r.payload["trajectory_summary"],
            "tool_calls": r.payload["tool_calls"],
            "score": r.payload["score"],
            "similarity": r.score,
            "task": r.payload["task"]
        }
        for r in results
    ]
```

### 3.5 Environment Configuration
- **File:** `config/.env.example`
- Add `OPENAI_API_KEY` placeholder
- Add optional `QDRANT_PATH` (default: `./qdrant_db`)

### 3.6 Unit Tests
- **File:** `tests/storage/test_qdrant.py` (new)
- Test collection creation
- Test trajectory storage
- Test semantic retrieval
- Test score filtering
- Use in-memory Qdrant for tests

## Files

| File | Action | Description |
|------|--------|-------------|
| `src/storage/__init__.py` | Create | Storage package |
| `src/storage/qdrant_client.py` | Create | Qdrant client manager |
| `src/storage/embeddings.py` | Create | OpenAI embeddings wrapper |
| `src/storage/trajectory_store.py` | Create | Trajectory storage |
| `src/storage/retrieval.py` | Create | Semantic search |
| `config/.env.example` | Modify | Add OpenAI key |
| `tests/storage/` | Create | Test package |
| `tests/storage/test_qdrant.py` | Create | Storage tests |

## Verification

```bash
# Install memory dependencies
.venv/bin/pip install -e ".[memory,dev]"

# Set up OpenAI key
export OPENAI_API_KEY="sk-test..."

# Run tests
.venv/bin/python -m pytest tests/storage/test_qdrant.py -v

# Manual integration test
.venv/bin/python -c "
import asyncio
from src.storage.qdrant_client import QdrantManager
from src.storage.trajectory_store import store_trajectory

async def test():
    client = await QdrantManager.get_client()
    print('Qdrant client initialized')

    # Store test trajectory
    await store_trajectory(
        task='test task',
        trajectory_summary='browser_snapshot -> browser_click',
        score=0.95,
        tool_calls=[],
        client=client
    )
    print('Trajectory stored successfully')

asyncio.run(test())
"
```

## Deliverables
- ✅ Qdrant collection created
- ✅ Trajectories stored with embeddings
- ✅ Semantic search working
- ✅ Score filtering functional (≥ 0.7 threshold)
- ✅ Unit tests with mock Qdrant

## Notes

**Qdrant Configuration:**
- **Path:** `./qdrant_db` (persistent local storage)
- **Vector size:** 1536 (OpenAI `text-embedding-3-small`)
- **Distance:** COSINE (standard for semantic similarity)
- **Client:** AsyncQdrantClient (non-blocking)

**Error Handling:**
- Handle OpenAI API rate limits (429 errors)
- Retry failed Qdrant operations (3 attempts)
- Fall back to empty list on search failure

**Performance:**
- Batch embeddings for multiple trajectories (future)
- Reuse client instance (singleton pattern)
- Consider connection pooling for concurrent requests

**Security:**
- Store API key in `.env` (never commit)
- Add `.env` to `.gitignore`
- Add `qdrant_db/` to `.gitignore`

## Estimate
**5-7 hours**
- 1.5h: Qdrant client setup
- 1.5h: Embedding service
- 1.5h: Trajectory storage
- 1h: Semantic retrieval
- 1h: Testing and debugging

## Dependencies
- Phase 2 must be complete (scoring produces data to store)
- OpenAI API key configured
