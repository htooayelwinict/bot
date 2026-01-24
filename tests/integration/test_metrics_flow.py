"""Integration tests for metrics collection pipeline.

Tests end-to-end flow: capture → score → redact → store.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

# Set fake API key for testing
os.environ["OPENROUTER_API_KEY"] = "sk-fake-key-for-testing"

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from src.metrics.middleware import MetricsMiddleware
from src.metrics.trajectory_callback import TrajectoryCallbackHandler
from src.storage.qdrant_client import QdrantManager


@pytest.fixture
async def in_memory_client():
    """Create in-memory Qdrant client for testing."""
    client = AsyncQdrantClient(location=":memory:")

    # Create collection
    await client.create_collection(
        collection_name="agent_trajectories",
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

    yield client

    # Cleanup (only if not already closed)
    try:
        await client.delete_collection("agent_trajectories")
    except RuntimeError:
        # Client already closed by test
        pass
    try:
        await client.close()
    except RuntimeError:
        # Client already closed
        pass


@pytest.fixture
def mock_embedding():
    """Create mock embedding function."""

    async def _mock_embed(text: str) -> list[float]:
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val % 1000) / 1000.0 for _ in range(1536)]

    return _mock_embed


@pytest.mark.asyncio
class TestMetricsMiddleware:
    """Tests for metrics middleware orchestration."""

    async def test_initialize(self, in_memory_client):
        """Test middleware initialization."""
        middleware = MetricsMiddleware()

        with patch.object(QdrantManager, "get_client", return_value=in_memory_client):
            await middleware.initialize()

            assert middleware._initialized is True
            assert middleware._client is not None

    async def test_process_execution(self, in_memory_client, mock_embedding):
        """Test complete execution processing pipeline."""
        middleware = MetricsMiddleware()

        # Create mock callback with sample data
        callback = TrajectoryCallbackHandler()

        # Simulate tool calls
        callback.trajectory.append(
            {
                "type": "tool_start",
                "tool": "browser_snapshot",
                "input": "{}",
                "start_time": 0.0,
                "status": "success",
                "run_id": "test-1",
                "end_time": 0.5,
                "latency": 0.5,
            }
        )
        callback.trajectory.append(
            {
                "type": "tool_start",
                "tool": "browser_click",
                "input": '{"ref": "e42"}',
                "start_time": 0.5,
                "status": "success",
                "run_id": "test-2",
                "end_time": 1.0,
                "latency": 0.5,
            }
        )

        # Set metrics
        callback.tool_metrics = {
            "tool_success": [True, True],
            "latencies": [0.5, 0.5],
            "token_usage": [{"total_tokens": 1000}],
        }

        trajectory_data = {"trajectory": callback.get_trajectory()}

        with patch.object(QdrantManager, "get_client", return_value=in_memory_client), patch(
            "src.storage.trajectory_store.embed_trajectory", new=mock_embedding
        ):
            await middleware.initialize()

            result = await middleware.process_execution(
                task="Test task",
                trajectory_data=trajectory_data,
                callback=callback,
            )

            assert result["score"] > 0
            assert result["stored"] is True
            assert result["point_id"] is not None
            assert "components" in result

    async def test_process_execution_with_pii(self, in_memory_client, mock_embedding):
        """Test that PII is redacted before storage."""
        middleware = MetricsMiddleware()

        callback = TrajectoryCallbackHandler()

        # Simulate tool call with PII
        callback.trajectory.append(
            {
                "type": "tool_start",
                "tool": "browser_type",
                "input": "user@example.com",
                "start_time": 0.0,
                "status": "success",
                "run_id": "test-1",
                "end_time": 0.5,
                "latency": 0.5,
            }
        )

        callback.tool_metrics = {
            "tool_success": [True],
            "latencies": [0.5],
            "token_usage": [],
        }

        trajectory_data = {"trajectory": callback.get_trajectory()}

        with patch.object(QdrantManager, "get_client", return_value=in_memory_client), patch(
            "src.storage.trajectory_store.embed_trajectory", new=mock_embedding
        ):
            await middleware.initialize()

            result = await middleware.process_execution(
                task="Test with PII",
                trajectory_data=trajectory_data,
                callback=callback,
            )

            assert result["stored"] is True

            # Verify stored data has redacted PII
            from src.storage.retrieval import get_trajectory_by_id

            stored = await get_trajectory_by_id(result["point_id"], client=in_memory_client)
            assert stored is not None

            tool_calls = stored.get("tool_calls", [])
            if tool_calls:
                input_data = str(tool_calls[0].get("input", ""))
                assert "[REDACTED_EMAIL]" in input_data or "user@example.com" not in input_data

    async def test_graceful_failure_on_no_client(self):
        """Test graceful handling when Qdrant client is unavailable."""
        middleware = MetricsMiddleware()

        callback = TrajectoryCallbackHandler()
        callback.trajectory.append(
            {
                "type": "tool_start",
                "tool": "test",
                "input": "{}",
                "start_time": 0.0,
                "status": "success",
                "run_id": "test-1",
            }
        )
        callback.tool_metrics = {
            "tool_success": [True],
            "latencies": [0.1],
            "token_usage": [],
        }

        trajectory_data = {"trajectory": callback.get_trajectory()}

        # Don't initialize - client should be None
        result = await middleware.process_execution(
            task="Test task",
            trajectory_data=trajectory_data,
            callback=callback,
        )

        assert result["stored"] is False
        assert result["point_id"] is None

    async def test_close(self, in_memory_client):
        """Test middleware cleanup."""
        middleware = MetricsMiddleware()

        with patch.object(QdrantManager, "get_client", return_value=in_memory_client):
            await middleware.initialize()
            assert middleware._initialized is True

            await middleware.close()

            assert middleware._initialized is False
            assert middleware._client is None


@pytest.mark.asyncio
class TestEndToEndFlow:
    """Tests for complete end-to-end metrics flow."""

    async def test_full_pipeline_with_redaction(self, in_memory_client, mock_embedding):
        """Test complete pipeline: callback → score → redact → store."""
        # Create middleware
        middleware = MetricsMiddleware()

        # Create callback and simulate execution
        callback = TrajectoryCallbackHandler()

        # Simulate multiple tool calls with PII
        callback.trajectory.extend(
            [
                {
                    "type": "tool_start",
                    "tool": "browser_snapshot",
                    "input": "{}",
                    "start_time": 0.0,
                    "status": "success",
                    "run_id": "1",
                    "end_time": 0.3,
                    "latency": 0.3,
                },
                {
                    "type": "tool_start",
                    "tool": "browser_type",
                    "input": "email: user@example.com, phone: 555-123-4567",
                    "start_time": 0.3,
                    "status": "success",
                    "run_id": "2",
                    "end_time": 1.0,
                    "latency": 0.7,
                },
                {
                    "type": "tool_start",
                    "tool": "browser_click",
                    "input": '{"ref": "e42"}',
                    "start_time": 1.0,
                    "status": "success",
                    "run_id": "3",
                    "end_time": 1.3,
                    "latency": 0.3,
                },
            ]
        )

        callback.tool_metrics = {
            "tool_success": [True, True, True],
            "latencies": [0.3, 0.7, 0.3],
            "token_usage": [{"total_tokens": 1500}],
        }

        trajectory_data = {"trajectory": callback.get_trajectory()}

        # Process with mocks
        with patch.object(QdrantManager, "get_client", return_value=in_memory_client), patch(
            "src.storage.trajectory_store.embed_trajectory", new=mock_embedding
        ):
            await middleware.initialize()

            result = await middleware.process_execution(
                task="Test full pipeline",
                trajectory_data=trajectory_data,
                callback=callback,
            )

            # Verify results
            assert result["score"] > 0
            assert result["stored"] is True
            assert result["point_id"] is not None

            # Verify stored data has redacted PII
            from src.storage.retrieval import get_trajectory_by_id

            stored = await get_trajectory_by_id(result["point_id"], client=in_memory_client)
            assert stored is not None
            assert stored["score"] == result["score"]

            # Check PII redaction in stored tool calls
            tool_calls = stored.get("tool_calls", [])
            found_pii = False
            for tc in tool_calls:
                input_str = str(tc.get("input", ""))
                if "user@example.com" in input_str or "555-123-4567" in input_str:
                    found_pii = True
                    break

            assert not found_pii, "PII should be redacted in stored data"
