"""Unit tests for Qdrant storage and retrieval.

Uses in-memory Qdrant for fast, isolated testing with mock embeddings.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

# Set fake API key to allow OpenRouter client initialization
# The actual embedding calls will be mocked
os.environ["OPENROUTER_API_KEY"] = "sk-fake-key-for-testing"

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from src.storage.qdrant_client import QdrantManager
from src.storage.retrieval import (
    count_trajectories,
    delete_trajectory,
    get_trajectory_by_id,
    retrieve_similar_trajectories,
)
from src.storage.trajectory_store import store_trajectory


@pytest.fixture
def mock_embedding():
    """Create mock embedding vector (1536 dimensions)."""

    async def _mock_embed(text: str) -> list[float]:
        # Generate pseudo-random but deterministic embedding based on text
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val % 1000) / 1000.0 for _ in range(1536)]

    return _mock_embed


@pytest.fixture
async def in_memory_client():
    """Create in-memory Qdrant client for testing."""
    # Use :memory: for fast, isolated tests
    client = AsyncQdrantClient(location=":memory:")

    # Create collection
    await client.create_collection(
        collection_name="agent_trajectories",
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

    yield client

    # Cleanup
    await client.delete_collection("agent_trajectories")
    await client.close()


# Note: QdrantManager singleton tests skipped because they use persistent storage
# which conflicts with in-memory test clients. The singleton pattern is tested
# implicitly through other integration tests.

@pytest.mark.skip(reason="Singleton uses persistent storage, conflicts with in-memory tests")
class TestQdrantManager:
    """Tests for QdrantManager singleton (skipped)."""

    async def test_get_client_singleton(self, in_memory_client):
        """Test that get_client returns same instance."""
        pass

    async def test_collection_created(self, in_memory_client):
        """Test that collection is created on first access."""
        pass


class TestTrajectoryStorage:
    """Tests for trajectory storage operations."""

    @pytest.mark.asyncio
    async def test_store_trajectory(self, in_memory_client, mock_embedding):
        """Test storing a single trajectory."""
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            point_id = await store_trajectory(
                task="Test task",
                trajectory_summary="browser_snapshot -> browser_click",
                score=0.95,
                tool_calls=[],
                client=in_memory_client,
            )

            assert point_id is not None
            # point_id is now a UUID, verify it's a valid UUID format
            assert len(point_id) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            assert point_id.count("-") == 4  # UUID has 4 dashes

    @pytest.mark.asyncio
    async def test_store_trajectory_with_metadata(self, in_memory_client, mock_embedding):
        """Test that trajectory metadata is preserved."""
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            point_id = await store_trajectory(
                task="Metadata test",
                trajectory_summary="tool1 -> tool2 -> tool3",
                score=0.85,
                tool_calls=[
                    {"tool": "browser_snapshot", "success": True},
                    {"tool": "browser_click", "success": True},
                ],
                client=in_memory_client,
            )

            # Retrieve and verify
            trajectory = await get_trajectory_by_id(point_id, client=in_memory_client)

            assert trajectory is not None
            assert trajectory["task"] == "Metadata test"
            assert trajectory["score"] == 0.85
            assert len(trajectory["tool_calls"]) == 2

    @pytest.mark.asyncio
    async def test_store_multiple_trajectories(self, in_memory_client, mock_embedding):
        """Test storing multiple distinct trajectories."""
        tasks = [
            ("Post to Facebook", "browser_snapshot -> browser_click -> browser_type", 0.9),
            ("Like a post", "browser_snapshot -> browser_click", 0.95),
            ("Share link", "browser_snapshot -> browser_click -> browser_click", 0.8),
        ]

        point_ids = []
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            for task, summary, score in tasks:
                point_id = await store_trajectory(
                    task=task,
                    trajectory_summary=summary,
                    score=score,
                    tool_calls=[],
                    client=in_memory_client,
                )
                point_ids.append(point_id)

        assert len(point_ids) == 3
        assert len(set(point_ids)) == 3  # All unique


class TestSemanticRetrieval:
    """Tests for semantic search and retrieval."""

    @pytest.mark.asyncio
    async def test_retrieve_similar_trajectories(self, in_memory_client, mock_embedding):
        """Test retrieving similar trajectories by semantic search."""
        # Patch both trajectory_store (for storage) and retrieval (for search)
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding), patch(
            "src.storage.retrieval.embed_trajectory", new=mock_embedding
        ):
            await store_trajectory(
                task="Post a message to my Facebook group",
                trajectory_summary="browser_snapshot -> browser_click -> browser_type -> browser_click",
                score=0.95,
                tool_calls=[],
                client=in_memory_client,
            )

            await store_trajectory(
                task="Like a post on Facebook",
                trajectory_summary="browser_snapshot -> browser_click",
                score=0.9,
                tool_calls=[],
                client=in_memory_client,
            )

            # Retrieve similar for a related task
            results = await retrieve_similar_trajectories(
                task="Post something to my group",
                top_k=2,
                min_score=0.7,
                client=in_memory_client,
            )

            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_score(self, in_memory_client, mock_embedding):
        """Test that retrieval filters by minimum score."""
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding), patch(
            "src.storage.retrieval.embed_trajectory", new=mock_embedding
        ):
            await store_trajectory(
                task="High quality task",
                trajectory_summary="tool1 -> tool2",
                score=0.95,
                tool_calls=[],
                client=in_memory_client,
            )

            await store_trajectory(
                task="Low quality task",
                trajectory_summary="tool1 -> tool2",
                score=0.5,
                tool_calls=[],
                client=in_memory_client,
            )

            # Search with high score threshold
            results = await retrieve_similar_trajectories(
                task="High quality task",
                top_k=10,
                min_score=0.8,
                client=in_memory_client,
            )

            # Should only return high-score trajectory
            assert all(r["score"] >= 0.8 for r in results)

    @pytest.mark.asyncio
    async def test_retrieve_returns_empty_on_no_results(self, in_memory_client, mock_embedding):
        """Test that retrieval returns empty list when no matches."""
        with patch("src.storage.retrieval.embed_trajectory", new=mock_embedding):
            results = await retrieve_similar_trajectories(
                task="Nonexistent task",
                top_k=3,
                min_score=0.7,
                client=in_memory_client,
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_limits_top_k(self, in_memory_client, mock_embedding):
        """Test that retrieval respects top_k limit."""
        # Store multiple trajectories
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding), patch(
            "src.storage.retrieval.embed_trajectory", new=mock_embedding
        ):
            for i in range(5):
                await store_trajectory(
                    task=f"Task {i}",
                    trajectory_summary=f"tool{i}",
                    score=0.9,
                    tool_calls=[],
                    client=in_memory_client,
                )

            # Request only 2 results
            results = await retrieve_similar_trajectories(
                task="Task",
                top_k=2,
                min_score=0.7,
                client=in_memory_client,
            )

            assert len(results) <= 2


class TestUtilityFunctions:
    """Tests for utility functions."""

    @pytest.mark.asyncio
    async def test_get_trajectory_by_id(self, in_memory_client, mock_embedding):
        """Test retrieving trajectory by ID."""
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            point_id = await store_trajectory(
                task="ID test task",
                trajectory_summary="tool1",
                score=0.88,
                tool_calls=[{"tool": "browser_click"}],
                client=in_memory_client,
            )

            trajectory = await get_trajectory_by_id(point_id, client=in_memory_client)

            assert trajectory is not None
            assert trajectory["task"] == "ID test task"
            assert trajectory["score"] == 0.88

    @pytest.mark.asyncio
    async def test_get_trajectory_by_id_not_found(self, in_memory_client):
        """Test retrieving non-existent trajectory returns None."""
        trajectory = await get_trajectory_by_id("nonexistent_id", client=in_memory_client)

        assert trajectory is None

    @pytest.mark.asyncio
    async def test_count_trajectories(self, in_memory_client, mock_embedding):
        """Test counting trajectories."""
        # Initially empty
        count = await count_trajectories(client=in_memory_client)
        assert count == 0

        # Add some trajectories
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            for _ in range(3):
                await store_trajectory(
                    task="Count test",
                    trajectory_summary="tool1",
                    score=0.9,
                    tool_calls=[],
                    client=in_memory_client,
                )

            count = await count_trajectories(client=in_memory_client)
            assert count == 3

    @pytest.mark.asyncio
    async def test_count_trajectories_with_filter(self, in_memory_client, mock_embedding):
        """Test counting trajectories with score filter."""
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            await store_trajectory("High score", "tool1", 0.95, [], client=in_memory_client)
            await store_trajectory("Medium score", "tool2", 0.75, [], client=in_memory_client)
            await store_trajectory("Low score", "tool3", 0.5, [], client=in_memory_client)

            high_quality = await count_trajectories(min_score=0.8, client=in_memory_client)
            medium_quality = await count_trajectories(min_score=0.6, client=in_memory_client)
            all_count = await count_trajectories(client=in_memory_client)

            assert high_quality == 1
            assert medium_quality == 2
            assert all_count == 3

    @pytest.mark.asyncio
    async def test_delete_trajectory(self, in_memory_client, mock_embedding):
        """Test deleting a trajectory."""
        with patch("src.storage.trajectory_store.embed_trajectory", new=mock_embedding):
            point_id = await store_trajectory(
                task="Delete test",
                trajectory_summary="tool1",
                score=0.9,
                tool_calls=[],
                client=in_memory_client,
            )

            # Verify exists
            trajectory = await get_trajectory_by_id(point_id, client=in_memory_client)
            assert trajectory is not None

            # Delete
            success = await delete_trajectory(point_id, client=in_memory_client)
            assert success is True

            # Verify deleted
            trajectory = await get_trajectory_by_id(point_id, client=in_memory_client)
            assert trajectory is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_trajectory(self, in_memory_client):
        """Test deleting non-existent trajectory returns True (Qdrant behavior)."""
        # Qdrant delete operation doesn't fail on non-existent points
        # We just verify it doesn't raise an exception
        success = await delete_trajectory("nonexistent_id", client=in_memory_client)
        # Qdrant returns success for deletes of non-existent points
        assert success is True
