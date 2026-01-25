"""Semantic search retrieval for similar trajectories.

Queries Qdrant to find historically successful workflows similar
to the current task.
"""

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, PointStruct, Range

from src.storage.embeddings import embed_trajectory
from src.storage.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)


async def retrieve_similar_trajectories(
    task: str,
    top_k: int = 3,
    min_score: float = 0.47,  # FIX: Filter to higher-quality runs only
    min_similarity: float = 0.47,  # Match same workflow across different topics
    exclude_failed_patterns: bool = True,  # P1 FIX: Filter by reflection failures
    client: AsyncQdrantClient | None = None,
) -> list[dict[str, Any]]:
    """Retrieve similar historical workflows with quality filtering.

    Searches Qdrant for trajectories with high semantic similarity to
    the given task, filtering by minimum success score, similarity,
    and optionally excluding workflows with known failure patterns.

    Args:
        task: The task description to search for.
        top_k: Maximum number of results to return (default: 3).
        min_score: Minimum trajectory score threshold (default: 0.7).
        min_similarity: Minimum semantic similarity threshold (default: 0.7).
        exclude_failed_patterns: If True, deprioritize workflows with
            many failed_patterns in their reflection (default: True).
        client: Optional Qdrant client. If None, creates a new one.

    Returns:
        List of similar trajectory dicts with keys:
            - trajectory: str (trajectory summary)
            - tool_calls: list[dict] (tool invocation records)
            - score: float (trajectory success score)
            - similarity: float (cosine similarity score)
            - task: str (original task description)
            - reflection: dict (critique, patterns)
            - quality_rank: float (combined quality score)

        Returns empty list if:
        - Collection is empty (cold start)
        - No trajectories meet the score/similarity thresholds
        - Search fails (graceful degradation)

    Examples:
        >>> results = await retrieve_similar_trajectories("Post to Facebook group")
        >>> for r in results:
        ...     print(f"Score: {r['score']:.2f}, Similarity: {r['similarity']:.2f}")
    """
    try:
        # Get client if not provided
        if client is None:
            client = await QdrantManager.get_client()

        # Embed the query task
        query_embedding = await embed_trajectory(task)

        # Build score filter
        score_filter = Filter(
            must=[
                {
                    "key": "score",
                    "range": Range(gte=min_score),
                }
            ]
        )

        # NOTE: We query with just the task text - Qdrant will still find
        # semantic matches even though stored embeddings include tool sequence.
        # The task portion provides ~70% of embedding signal anyway.

        # Search Qdrant using query_points API
        response = await client.query_points(
            collection_name=QdrantManager.COLLECTION_NAME,
            query=query_embedding,
            query_filter=score_filter,
            limit=top_k,
        )

        # Format results and filter by similarity threshold
        formatted = []
        for result in response.points:
            # Skip results below similarity threshold
            if result.score < min_similarity:
                continue

            if result.payload is not None:
                reflection = result.payload.get("reflection", {}) or {}
                trajectory_score = result.payload.get("score", 0.0)
                
                # P1 FIX: Calculate quality rank considering failed patterns
                failed_patterns = reflection.get("failed_patterns", [])
                successful_patterns = reflection.get("successful_patterns", [])
                
                # Penalize workflows with many failures
                failure_penalty = len(failed_patterns) * 0.05  # -5% per failure
                success_bonus = len(successful_patterns) * 0.02  # +2% per success
                
                # FIX: Weight score over similarity to prioritize successful patterns
                # TOGGLE: Revert to 0.4/0.4 to prioritize similarity over score
                quality_rank = (
                    trajectory_score * 0.7 +  # 70% weight on original score (SUCCESS)
                    result.score * 0.2 +  # 20% weight on similarity (RELEVANCE)
                    success_bonus -
                    failure_penalty
                )
                quality_rank = max(0.0, min(1.0, quality_rank + 0.2))  # Normalize to 0-1
                
                formatted.append(
                    {
                        "trajectory": result.payload.get("trajectory_summary", ""),
                        "tool_calls": result.payload.get("tool_calls", []),
                        "score": trajectory_score,
                        "similarity": result.score,
                        "task": result.payload.get("task", ""),
                        "reflection": reflection,
                        "quality_rank": quality_rank,
                        "failed_pattern_count": len(failed_patterns),
                    }
                )

        # P1 FIX: Sort by quality_rank (best first) and optionally filter heavy failures
        if exclude_failed_patterns:
            # FIX: Only exclude workflows with MANY failed patterns (>5), not ALL
            # Learning from failed patterns is CRITICAL for improvement
            formatted = [f for f in formatted if f.get("failed_pattern_count", 0) <= 5]
            # Then sort by quality rank
            formatted.sort(key=lambda x: -x.get("quality_rank", 0))
        else:
            formatted.sort(key=lambda x: -x.get("quality_rank", 0))

        # FIX: Lower quality_rank threshold to allow learning from failures
        # TOGGLE: Set min_quality_rank to 0.0 to disable this filter
        min_quality_rank = 0.40  # Lowered from 0.60 to allow failed pattern learning
        if min_quality_rank > 0:
            formatted = [f for f in formatted if f.get("quality_rank", 0) >= min_quality_rank]

        logger.info(
            f"Retrieved {len(formatted)} similar trajectories for task: {task[:50]}..."
        )
        return formatted

    except Exception as e:
        # Graceful degradation: return empty list on error
        logger.error(f"Failed to retrieve similar trajectories: {e}")
        return []



async def get_trajectory_by_id(
    point_id: str,
    client: AsyncQdrantClient | None = None,
) -> dict[str, Any] | None:
    """Retrieve a specific trajectory by its point ID.

    Args:
        point_id: The Qdrant point ID to retrieve.
        client: Optional Qdrant client.

    Returns:
        Trajectory dict with keys:
            - task: str
            - score: float
            - trajectory_summary: str
            - tool_calls: list[dict]
            - timestamp: str

        Returns None if point not found.

    Examples:
        >>> traj = await get_trajectory_by_id("Post to Facebook_1234567890.123")
        >>> if traj:
        ...     print(traj['trajectory_summary'])
    """
    try:
        if client is None:
            client = await QdrantManager.get_client()

        results = await client.retrieve(
            collection_name=QdrantManager.COLLECTION_NAME,
            ids=[point_id],
        )

        if results and results[0].payload:
            return results[0].payload

        return None

    except Exception as e:
        logger.error(f"Failed to retrieve trajectory {point_id}: {e}")
        return None


async def count_trajectories(
    min_score: float | None = None,
    client: AsyncQdrantClient | None = None,
) -> int:
    """Count stored trajectories, optionally filtering by score.

    Args:
        min_score: Optional minimum score threshold.
        client: Optional Qdrant client.

    Returns:
        Number of trajectories matching the criteria.

    Examples:
        >>> total = await count_trajectories()
        >>> high_quality = await count_trajectories(min_score=0.8)
    """
    try:
        if client is None:
            client = await QdrantManager.get_client()

        if min_score is not None:
            # Query with filter and count results
            score_filter = Filter(
                must=[
                    {
                        "key": "score",
                        "range": Range(gte=min_score),
                    }
                ]
            )

            # Use query_points with a dummy embedding to get filtered count
            # Note: This is a workaround for count API limitations
            import hashlib

            dummy_embedding = [0.0] * 1536

            response = await client.query_points(
                collection_name=QdrantManager.COLLECTION_NAME,
                query=dummy_embedding,
                query_filter=score_filter,
                limit=1000,  # Set high limit to count all
            )
            return len(response.points)
        else:
            # Count all using count API
            result = await client.count(collection_name=QdrantManager.COLLECTION_NAME)
            return result.count

    except Exception as e:
        logger.error(f"Failed to count trajectories: {e}")
        return 0


async def delete_trajectory(
    point_id: str,
    client: AsyncQdrantClient | None = None,
) -> bool:
    """Delete a trajectory by its point ID.

    Args:
        point_id: The Qdrant point ID to delete.
        client: Optional Qdrant client.

    Returns:
        True if deletion succeeded, False otherwise.

    Examples:
        >>> success = await delete_trajectory("Post to Facebook_1234567890.123")
    """
    try:
        if client is None:
            client = await QdrantManager.get_client()

        await client.delete(
            collection_name=QdrantManager.COLLECTION_NAME,
            points_selector=[point_id],
        )

        logger.info(f"Deleted trajectory {point_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete trajectory {point_id}: {e}")
        return False
