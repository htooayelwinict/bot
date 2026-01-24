"""Trajectory storage in Qdrant vector database.

Handles storing scored trajectories with embeddings for semantic retrieval.
"""

import logging
import uuid
from datetime import datetime, timezone

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from src.storage.embeddings import embed_trajectory
from src.storage.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)


async def store_trajectory(
    task: str,
    trajectory_summary: str,
    score: float,
    tool_calls: list[dict],
    reflection: dict | None = None,
    client: AsyncQdrantClient | None = None,
) -> str:
    """Store trajectory in Qdrant with embedding.

    Args:
        task: The user task description.
        trajectory_summary: Formatted trajectory summary for embedding.
        score: Calculated trajectory score (0.0-1.0).
        tool_calls: List of tool call records (as dicts).
        reflection: Optional reflection analysis (critique, patterns).
        client: Optional Qdrant client. If None, creates a new one.
    """
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Get client if not provided
            if client is None:
                client = await QdrantManager.get_client()

            # IMPROVED EMBEDDING STRATEGY (P1 FIX)
            # Embed task + successful tool sequence for better pattern matching
            # This enables matching on EXECUTION PATTERNS, not just task intent
            
            # Extract successful tool sequence
            successful_tools = []
            for tc in tool_calls:
                # Handle case where tc might be a string instead of dict
                if isinstance(tc, str):
                    successful_tools.append(tc)
                    continue
                if not isinstance(tc, dict):
                    continue
                    
                if tc.get("success", True):  # Include successful calls
                    tool_name = tc.get("tool", "")
                    inputs = tc.get("input", {})
                    
                    # Handle case where inputs is a string
                    if isinstance(inputs, str):
                        successful_tools.append(tool_name)
                        continue
                    if not isinstance(inputs, dict):
                        successful_tools.append(tool_name)
                        continue
                    
                    # Include key context for certain tools
                    if tool_name in ["browser_navigate", "navigate"]:
                        url = inputs.get("url", "")
                        if url:
                            # Extract domain for pattern matching
                            domain = url.split("//")[-1].split("/")[0]
                            successful_tools.append(f"{tool_name}({domain})")
                        else:
                            successful_tools.append(tool_name)
                    elif tool_name in ["browser_click", "click", "browser_type", "type"]:
                        element = inputs.get("element", "")
                        if element:
                            successful_tools.append(f"{tool_name}({element[:30]})")
                        else:
                            successful_tools.append(tool_name)
                    else:
                        successful_tools.append(tool_name)
            
            # Combine task with tool sequence (limit to key tools)
            tool_sequence = " -> ".join(successful_tools[:15])
            text_to_embed = f"{task} | Execution: {tool_sequence}" if tool_sequence else task
            
            embedding = await embed_trajectory(text_to_embed)

            # Generate unique point ID (UUID v4 for uniqueness)
            point_id = str(uuid.uuid4())

            # Store point with metadata
            payload = {
                "task": task,
                "score": score,
                "trajectory_summary": trajectory_summary,
                "tool_calls": tool_calls,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if reflection:
                payload["reflection"] = reflection

            await client.upsert(
                collection_name=QdrantManager.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )

            logger.info(f"Stored trajectory {point_id} with score {score:.3f}")
            return point_id

        except Exception as e:
            retry_count += 1
            logger.warning(
                f"Failed to store trajectory (attempt {retry_count}/{max_retries}): {e}"
            )

            if retry_count >= max_retries:
                raise RuntimeError(f"Failed to store trajectory after {max_retries} attempts: {e}") from e

            # Exponential backoff
            import asyncio

            await asyncio.sleep(2**retry_count)

    # Should never reach here, but satisfy type checker
    raise RuntimeError("Unexpected error in trajectory storage")


async def store_trajectory_batch(
    trajectories: list[dict],
    client: AsyncQdrantClient | None = None,
) -> list[str]:
    """Store multiple trajectories in a single batch operation.

    More efficient for bulk storage operations.

    Args:
        trajectories: List of trajectory dicts with keys:
            - task: str
            - trajectory_summary: str
            - score: float
            - tool_calls: list[dict]
        client: Optional Qdrant client.

    Returns:
        List of point IDs that were created.

    Raises:
        RuntimeError: If storage fails.

    Examples:
        >>> trajectories = [
        ...     {"task": "Post to FB", "trajectory_summary": "...", "score": 0.9, "tool_calls": []},
        ...     {"task": "Like post", "trajectory_summary": "...", "score": 0.95, "tool_calls": []},
        ... ]
        >>> ids = await store_trajectory_batch(trajectories)
    """
    if client is None:
        client = await QdrantManager.get_client()

    # Prepare texts for batch embedding (task only)
    texts = [
        t['task']
        for t in trajectories
    ]

    # Batch embed
    from src.storage.embeddings import embed_trajectories_batch

    embeddings = await embed_trajectories_batch(texts)

    # Create points
    points = []
    point_ids = []

    for i, traj in enumerate(trajectories):
        point_id = str(uuid.uuid4())
        point_ids.append(point_id)

        points.append(
            PointStruct(
                id=point_id,
                vector=embeddings[i],
                payload={
                    "task": traj["task"],
                    "score": traj["score"],
                    "trajectory_summary": traj["trajectory_summary"],
                    "tool_calls": traj["tool_calls"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

    # Batch upsert
    try:
        await client.upsert(
            collection_name=QdrantManager.COLLECTION_NAME,
            points=points,
        )
        logger.info(f"Stored {len(points)} trajectories in batch")
        return point_ids

    except Exception as e:
        raise RuntimeError(f"Failed to store trajectory batch: {e}") from e
