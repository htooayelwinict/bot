# Phase 4: LOT Memory (Learning Over Time)

**Objective:** Implement ChromaDB-based pattern storage and semantic recall for agent learning

---

## Prerequisites

- Phase 3b complete (agent assembled with all tools)
- ChromaDB installed
- Agent successfully executing tasks

---

## Tasks

### 4.1 ChromaDB Setup

- [ ] Install ChromaDB dependency
- [ ] Create persistent storage directory
- [ ] Initialize ChromaDB client
- [ ] Create collections for patterns

**Files:**
- `src/memory/__init__.py`
- `src/memory/chroma_store.py`

**Implementation:**
```python
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pathlib import Path
import os

class ChromaStore:
    """ChromaDB-based memory store for LOT (Learning Over Time)."""

    def __init__(self, persist_dir: str = "./memory"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # OpenAI embeddings for semantic search
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        # Get or create collections with OpenAI embeddings
        self.patterns_collection = self.client.get_or_create_collection(
            name="task_patterns",
            embedding_function=self.openai_ef,
            metadata={"description": "Successful task patterns for reuse"}
        )

    def add_pattern(
        self,
        task: str,
        actions: list[dict],
        success_rate: float = 1.0,
        metadata: dict = None
    ) -> str:
        """Store a successful task pattern.

        Args:
            task: Natural language task description
            actions: List of actions taken (tool calls)
            success_rate: 0.0-1.0 success score
            metadata: Additional context

        Returns:
            Pattern ID
        """
        import uuid
        pattern_id = str(uuid.uuid4())

        # Create pattern document
        pattern = {
            "task": task,
            "actions": actions,
            "success_rate": success_rate,
            "timestamp": datetime.now().isoformat(),
            "usage_count": 0
        }

        # Add metadata
        if metadata:
            pattern.update(metadata)

        # Store in ChromaDB (OpenAI embeddings applied automatically)
        self.patterns_collection.add(
            ids=[pattern_id],
            documents=[task],
            metadatas=[pattern]
        )

        return pattern_id

    def search_patterns(
        self,
        query: str,
        n_results: int = 3,
        min_success_rate: float = 0.5
    ) -> list[dict]:
        """Search for similar patterns.

        Args:
            query: Task description to search for
            n_results: Max number of results
            min_success_rate: Minimum success rate threshold

        Returns:
            List of similar patterns with actions
        """
        results = self.patterns_collection.query(
            query_texts=[query],
            n_results=n_results
        )

        patterns = []
        for i, pattern_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            # Filter by success rate
            if metadata.get("success_rate", 0) >= min_success_rate:
                patterns.append({
                    "id": pattern_id,
                    "task": metadata["task"],
                    "actions": metadata["actions"],
                    "success_rate": metadata["success_rate"],
                    "usage_count": metadata.get("usage_count", 0),
                    "similarity": 1 - distance  # Convert to similarity
                })

        return sorted(patterns, key=lambda p: p["similarity"], reverse=True)

    def update_pattern_usage(self, pattern_id: str, success: bool):
        """Update pattern usage statistics.

        Args:
            pattern_id: Pattern to update
            success: Whether the pattern worked this time
        """
        # Get current pattern
        patterns = self.patterns_collection.get(ids=[pattern_id])
        if not patterns["ids"]:
            return

        metadata = patterns["metadatas"][0]

        # Update usage count
        metadata["usage_count"] = metadata.get("usage_count", 0) + 1

        # Update success rate using exponential moving average
        old_rate = metadata.get("success_rate", 0.5)
        alpha = 0.3  # Learning rate
        new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * old_rate
        metadata["success_rate"] = new_rate

        # Update timestamp
        metadata["last_used"] = datetime.now().isoformat()

        # Update in ChromaDB
        self.patterns_collection.update(
            ids=[pattern_id],
            metadatas=[metadata]
        )

    def get_pattern_stats(self) -> dict:
        """Get statistics about stored patterns."""
        count = self.patterns_collection.count()

        # Get all patterns
        all_patterns = self.patterns_collection.get()

        if not all_patterns["ids"]:
            return {"total_patterns": 0}

        # Calculate stats
        success_rates = [
            m.get("success_rate", 0)
            for m in all_patterns["metadatas"]
        ]

        usage_counts = [
            m.get("usage_count", 0)
            for m in all_patterns["metadatas"]
        ]

        return {
            "total_patterns": count,
            "avg_success_rate": sum(success_rates) / len(success_rates),
            "max_success_rate": max(success_rates),
            "total_usage": sum(usage_counts),
            "most_used_pattern": max(
                zip(all_patterns["ids"], usage_counts),
                key=lambda x: x[1]
            )[0] if usage_counts else None
        }

    def clear_all(self):
        """Clear all stored patterns (use with caution)."""
        self.client.delete_collection("task_patterns")
        # Recreate collection with OpenAI embeddings
        self.patterns_collection = self.client.get_or_create_collection(
            name="task_patterns",
            embedding_function=self.openai_ef
        )
```

### 4.2 Memory Tools

- [ ] Create `save_pattern` tool
- [ ] Create `recall_patterns` tool
- [ ] Create `get_pattern_stats` tool
- [ ] Integrate with agent execution

**Files:**
- `src/tools/memory.py`

**Implementation:**
```python
from pydantic import BaseModel, Field
from langchain.tools import tool
from src.memory.chroma_store import ChromaStore

# Global store instance
_memory_store: ChromaStore | None = None

def get_memory_store() -> ChromaStore:
    """Get or create global memory store."""
    global _memory_store
    if _memory_store is None:
        _memory_store = ChromaStore()
    return _memory_store

class SavePatternArgs(BaseModel):
    """Arguments for saving a successful pattern."""
    task: str = Field(description="Natural language task description")
    actions: list[dict] = Field(description="List of tool calls that succeeded")
    success_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Success rate (0.0-1.0)"
    )
    context: str = Field(
        default="",
        description="Additional context about when this pattern works"
    )

@tool
def save_pattern(args: SavePatternArgs) -> str:
    """Save a successful task pattern for future reuse.

    Call this tool after completing a task successfully to store the pattern.
    This enables the agent to learn and improve over time (LOT).
    """
    store = get_memory_store()

    pattern_id = store.add_pattern(
        task=args.task,
        actions=args.actions,
        success_rate=args.success_rate,
        metadata={"context": args.context}
    )

    return f"Saved pattern {pattern_id} for task: {args.task}"

class RecallPatternsArgs(BaseModel):
    """Arguments for recalling similar patterns."""
    task: str = Field(description="Task description to search for")
    max_results: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of patterns to recall"
    )
    min_success_rate: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum success rate threshold"
    )

@tool
def recall_patterns(args: RecallPatternsArgs) -> str:
    """Recall similar successful patterns from memory.

    Use this tool when starting a new task to see if similar tasks have been solved before.
    Returns a list of similar patterns with their actions and success rates.
    """
    store = get_memory_store()

    patterns = store.search_patterns(
        query=args.task,
        n_results=args.max_results,
        min_success_rate=args.min_success_rate
    )

    if not patterns:
        return f"No similar patterns found for task: {args.task}"

    # Format results
    results = [f"Found {len(patterns)} similar patterns:\n"]

    for i, pattern in enumerate(patterns, 1):
        results.append(f"\n{i}. Task: {pattern['task']}")
        results.append(f"   Similarity: {pattern['similarity']:.2%}")
        results.append(f"   Success Rate: {pattern['success_rate']:.2%}")
        results.append(f"   Times Used: {pattern['usage_count']}")
        results.append(f"   Actions:")
        for j, action in enumerate(pattern['actions'], 1):
            results.append(f"      {j}. {action.get('tool', 'unknown')}: {action.get('args', {})}")

    return "\n".join(results)

class GetPatternStatsArgs(BaseModel):
    """Arguments for getting pattern statistics."""

@tool
def get_pattern_stats(args: GetPatternStatsArgs) -> str:
    """Get statistics about stored patterns.

    Returns total patterns, average success rate, and usage statistics.
    """
    store = get_memory_store()
    stats = store.get_pattern_stats()

    return f"""Pattern Statistics:
- Total Patterns: {stats['total_patterns']}
- Average Success Rate: {stats.get('avg_success_rate', 0):.2%}
- Max Success Rate: {stats.get('max_success_rate', 0):.2%}
- Total Usage: {stats.get('total_usage', 0)}
- Most Used Pattern ID: {stats.get('most_used_pattern', 'N/A')}
"""
```

### 4.3 Agent Integration

- [ ] Modify `FacebookSurferAgent` to use memory
- [ ] Auto-save successful patterns
- [ ] Auto-recall similar patterns
- [ ] Update pattern usage statistics

**Files to Modify:**
- `src/agents/facebook_surfer.py`

**Changes:**
```python
from src.memory.chroma_store import ChromaStore
from src.tools.memory import save_pattern, recall_patterns

class FacebookSurferAgent:
    def __init__(
        self,
        model: str = "gpt-4o",
        enable_memory: bool = True,
        enable_hitl: bool = True
    ):
        # ... existing code ...

        # Add memory tools
        if enable_memory:
            self.store = ChromaStore()
            # Add memory tools to registry
            registry.register(save_pattern, "memory")
            registry.register(recall_patterns, "memory")
            registry.register(get_pattern_stats, "memory")
            # Refresh tools list
            self.tools = registry.get_all()

        # Update system prompt to use memory
        if enable_memory:
            self.system_prompt += """

**Learning Over Time (LOT):**
- Before starting a task, use recall_patterns to check for similar successful patterns
- If a similar pattern exists (> 70% similarity), consider reusing it
- After completing a task successfully, use save_pattern to store the pattern
- This enables the agent to learn and improve over time
"""

    def _create_agent(self):
        """Create the DeepAgent instance with memory."""
        return create_deep_agent(
            model=f"openai:{self.model}",
            tools=self.tools,
            store=self.store if self.enable_memory else None,
            checkpointer=self.checkpointer,
            system_prompt=self.system_prompt,
            interrupt_before=[] if not self.enable_hitl else ["human_login"]
        )

    def invoke_with_learning(self, task: str, thread_id: str = "default") -> dict:
        """Execute task with automatic learning."""
        # 1. Recall similar patterns
        if self.enable_memory:
            from src.tools.memory import recall_patterns, RecallPatternsArgs
            similar = recall_patterns.func(
                RecallPatternsArgs(task=task, max_results=3)
            )
            print(f"Recalled patterns:\n{similar}\n")

        # 2. Execute task
        result = self.invoke(task, thread_id)

        # 3. If successful, save pattern
        if self.enable_memory and result.get("success"):
            # Extract actions from result
            actions = self._extract_actions(result)
            from src.tools.memory import save_pattern, SavePatternArgs
            save_pattern.func(
                SavePatternArgs(
                    task=task,
                    actions=actions,
                    success_rate=1.0
                )
            )

        return result

    def _extract_actions(self, result: dict) -> list[dict]:
        """Extract tool calls from agent result."""
        # Parse result to extract tool calls
        actions = []
        # Implementation depends on DeepAgent response format
        return actions
```

### 4.4 Testing

- [ ] Test ChromaDB persistence
- [ ] Test pattern storage
- [ ] Test semantic search
- [ ] Test pattern recall
- [ ] Test agent learning loop

**Files:**
- `tests/test_memory.py`

**Test Cases:**
```python
def test_pattern_storage():
    """Test storing patterns in ChromaDB."""
    store = ChromaStore()

    pattern_id = store.add_pattern(
        task="Navigate to facebook.com",
        actions=[{"tool": "browser_navigate", "args": {"url": "https://facebook.com"}}],
        success_rate=1.0
    )

    assert pattern_id is not None

def test_pattern_search():
    """Test semantic search for patterns."""
    store = ChromaStore()

    # Add patterns
    store.add_pattern("Login to Facebook", [...], 1.0)
    store.add_pattern("Post on timeline", [...], 0.9)

    # Search
    results = store.search_patterns("Sign into FB", n_results=2)

    assert len(results) > 0
    assert results[0]["similarity"] > 0.7

def test_pattern_update():
    """Test updating pattern usage."""
    store = ChromaStore()

    pattern_id = store.add_pattern("Test task", [], 1.0)

    # Update usage
    store.update_pattern_usage(pattern_id, success=True)

    # Check stats
    stats = store.get_pattern_stats()
    assert stats["total_usage"] > 0
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/memory/__init__.py` | Memory module |
| `src/memory/chroma_store.py` | ChromaDB wrapper |
| `src/tools/memory.py` | Memory tools (save, recall, stats) |
| `tests/test_memory.py` | Memory tests |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/agents/facebook_surfer.py` | Add memory integration |
| `pyproject.toml` | Add chromadb dependency |

---

## Verification

```bash
# 1. Install ChromaDB
pip install chromadb

# 2. Test ChromaDB setup
python -c "
from src.memory.chroma_store import ChromaStore
store = ChromaStore()
print('ChromaDB initialized')
print(f'Collections: {store.client.list_collections()}')
"

# 3. Test pattern storage
python -c "
from src.memory.chroma_store import ChromaStore
store = ChromaStore()

pattern_id = store.add_pattern(
    task='Navigate to Facebook',
    actions=[{'tool': 'browser_navigate', 'args': {'url': 'https://facebook.com'}}],
    success_rate=1.0
)
print(f'Stored pattern: {pattern_id}')

# Search for similar
results = store.search_patterns('Go to FB', n_results=1)
print(f'Found: {results[0][\"task\"]} (similarity: {results[0][\"similarity\"]:.2%})')
"

# 4. Test memory tools
python -c "
from src.tools.memory import save_pattern, SavePatternArgs
result = save_pattern.func(SavePatternArgs(
    task='Test pattern',
    actions=[{'tool': 'test'}],
    success_rate=1.0
))
print(result)
"

# 5. Test agent with memory
python -c "
from src.agents.facebook_surfer import FacebookSurferAgent
agent = FacebookSurferAgent(enable_memory=True)
print(f'Agent has {len(agent.tools)} tools (including memory)')
stats = agent.invoke('Get pattern statistics')
print(stats)
"

# 6. Test persistence
python -c "
from src.memory.chroma_store import ChromaStore
store = ChromaStore()
store.add_pattern('Test', [], 1.0)
print('Patterns:', store.patterns_collection.count())
# Restart and verify
"
python -c "
from src.memory.chroma_store import ChromaStore
store = ChromaStore()
print('Patterns after restart:', store.patterns_collection.count())
"

# 7. Run memory tests
pytest tests/test_memory.py -v
```

**Expected Results:**
- ChromaDB initializes without errors
- Patterns store and retrieve correctly
- Semantic search returns similar patterns
- Agent uses memory tools
- Data persists across restarts
- Tests pass

---

## Estimated Effort

**1-2 days**

- ChromaDB setup: 2 hours
- Memory tools: 3 hours
- Agent integration: 3 hours
- Testing: 2 hours
- Documentation: 2 hours

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ChromaDB performance issues | Use in-memory for testing, persistent for prod |
| Poor pattern quality | Validate before storing, use success scoring |
| Semantic search irrelevant | Tune embeddings, add filtering |
| Memory bloat | Prune low-success patterns |

---

## Dependencies

- Phase 3b: Agent Assembly (required)
- Phase 5: Integration & Testing

---

## Exit Criteria

- [ ] ChromaDB stores patterns persistently
- [ ] Semantic search finds similar patterns
- [ ] Agent recalls patterns before tasks
- [ ] Agent saves patterns after success
- [ ] Pattern stats tracked correctly
- [ ] Memory persists across restarts
- [ ] Tests pass
