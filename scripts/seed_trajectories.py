#!/usr/bin/env python3
"""Seed Qdrant with initial successful trajectories.

This script populates the vector database with example successful
workflows to enable the planning agent to work from the start.

Run this once before using the planning agent for the first time.
"""

import asyncio
import logging

from src.storage.qdrant_client import QdrantManager
from src.storage.trajectory_store import store_trajectory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Seed trajectories based on real Facebook automation workflows
SEED_TRAJECTORIES = [
    {
        "task": "Post a message to Facebook group",
        "trajectory_summary": (
            "browser_navigate -> browser_get_snapshot -> browser_click -> "
            "browser_type -> browser_click -> browser_click"
        ),
        "score": 0.95,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/groups/GROUP_ID"}',
                "success": True,
                "latency": 2.1,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.5,
            },
            {
                "tool": "browser_click",
                "input": '{"ref": "e15", "force": true}',
                "success": True,
                "latency": 0.3,
            },
            {
                "tool": "browser_type",
                "input": '{"element": "textbox", "ref": "e16", "text": "Test message"}',
                "success": True,
                "latency": 0.8,
            },
            {
                "tool": "browser_click",
                "input": '{"ref": "e50", "force": true}',
                "success": True,
                "latency": 0.4,
            },
        ],
    },
    {
        "task": "Like a post on Facebook",
        "trajectory_summary": "browser_navigate -> browser_get_snapshot -> browser_click",
        "score": 0.92,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/posts/POST_ID"}',
                "success": True,
                "latency": 1.8,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.4,
            },
            {
                "tool": "browser_click",
                "input": '{"aria_label": "Like", "force": true}',
                "success": True,
                "latency": 0.3,
            },
        ],
    },
    {
        "task": "Comment on a Facebook post",
        "trajectory_summary": (
            "browser_navigate -> browser_get_snapshot -> "
            "browser_click -> browser_type -> browser_click"
        ),
        "score": 0.90,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/posts/POST_ID"}',
                "success": True,
                "latency": 1.9,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.5,
            },
            {
                "tool": "browser_click",
                "input": '{"aria_label": "Comment", "force": true}',
                "success": True,
                "latency": 0.4,
            },
            {
                "tool": "browser_type",
                "input": '{"element": "textbox", "text": "Great post!"}',
                "success": True,
                "latency": 0.7,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Comment", "force": true}',
                "success": True,
                "latency": 0.3,
            },
        ],
    },
    {
        "task": "Share a Facebook post to group",
        "trajectory_summary": (
            "browser_navigate -> browser_get_snapshot -> browser_click -> "
            "browser_click -> browser_click -> browser_type -> browser_click"
        ),
        "score": 0.88,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/posts/POST_ID"}',
                "success": True,
                "latency": 2.0,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.5,
            },
            {
                "tool": "browser_click",
                "input": '{"aria_label": "Share", "force": true}',
                "success": True,
                "latency": 0.4,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Share to group"}',
                "success": True,
                "latency": 0.5,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Search"}',
                "success": True,
                "latency": 0.3,
            },
            {
                "tool": "browser_type",
                "input": '{"element": "textbox", "text": "Group Name"}',
                "success": True,
                "latency": 0.6,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Post"}',
                "success": True,
                "latency": 0.4,
            },
        ],
    },
    {
        "task": "React to Facebook post with love",
        "trajectory_summary": (
            "browser_navigate -> browser_get_snapshot -> "
            "browser_click -> browser_click"
        ),
        "score": 0.91,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/posts/POST_ID"}',
                "success": True,
                "latency": 1.8,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.4,
            },
            {
                "tool": "browser_click",
                "input": '{"aria_label": "React", "force": true}',
                "success": True,
                "latency": 0.3,
            },
            {
                "tool": "browser_click",
                "input": '{"aria_label": "Love", "force": true}',
                "success": True,
                "latency": 0.3,
            },
        ],
    },
    {
        "task": "Navigate to Facebook group",
        "trajectory_summary": "browser_navigate -> browser_get_snapshot",
        "score": 0.96,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/groups/GROUP_ID"}',
                "success": True,
                "latency": 2.0,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.5,
            },
        ],
    },
    {
        "task": "Search for Facebook group",
        "trajectory_summary": (
            "browser_navigate -> browser_get_snapshot -> "
            "browser_click -> browser_type -> browser_wait"
        ),
        "score": 0.89,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com"}',
                "success": True,
                "latency": 1.5,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.5,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Search"}',
                "success": True,
                "latency": 0.3,
            },
            {
                "tool": "browser_type",
                "input": '{"element": "textbox", "text": "Group Name"}',
                "success": True,
                "latency": 0.6,
            },
            {
                "tool": "browser_wait",
                "input": '{"time": 1}',
                "success": True,
                "latency": 1.0,
            },
        ],
    },
    {
        "task": "Create Facebook poll in group",
        "trajectory_summary": (
            "browser_navigate -> browser_get_snapshot -> browser_click -> "
            "browser_click -> browser_type -> browser_type -> browser_click"
        ),
        "score": 0.87,
        "tool_calls": [
            {
                "tool": "browser_navigate",
                "input": '{"url": "https://www.facebook.com/groups/GROUP_ID"}',
                "success": True,
                "latency": 2.1,
            },
            {
                "tool": "browser_get_snapshot",
                "input": "{}",
                "success": True,
                "latency": 0.5,
            },
            {
                "tool": "browser_click",
                "input": '{"ref": "e15", "force": true}',
                "success": True,
                "latency": 0.3,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Poll"}',
                "success": True,
                "latency": 0.4,
            },
            {
                "tool": "browser_type",
                "input": '{"element": "textbox", "text": "Question?"}',
                "success": True,
                "latency": 0.7,
            },
            {
                "tool": "browser_type",
                "input": '{"element": "textbox", "text": "Option 1"}',
                "success": True,
                "latency": 0.6,
            },
            {
                "tool": "browser_click",
                "input": '{"button": "Post"}',
                "success": True,
                "latency": 0.4,
            },
        ],
    },
]


async def main():
    """Seed Qdrant with initial trajectories."""
    logger.info("Starting trajectory seeding...")

    # Initialize Qdrant client
    client = await QdrantManager.get_client()
    logger.info("Qdrant client initialized")

    # Store each trajectory
    success_count = 0
    for i, traj_data in enumerate(SEED_TRAJECTORIES, 1):
        try:
            logger.info(f"[{i}/{len(SEED_TRAJECTORIES)}] Seeding: {traj_data['task']}")

            point_id = await store_trajectory(
                task=traj_data["task"],
                trajectory_summary=traj_data["trajectory_summary"],
                score=traj_data["score"],
                tool_calls=traj_data["tool_calls"],
                client=client,
            )

            logger.info(f"  ✓ Stored as {point_id}")
            success_count += 1

        except Exception as e:
            logger.error(f"  ✗ Failed to store trajectory: {e}")

    logger.info(f"\nSeeding complete: {success_count}/{len(SEED_TRAJECTORIES)} trajectories stored")

    # Show collection stats
    from src.storage.retrieval import count_trajectories

    total = await count_trajectories(client=client)
    high_quality = await count_trajectories(min_score=0.8, client=client)

    logger.info("\nCollection stats:")
    logger.info(f"  Total trajectories: {total}")
    logger.info(f"  High quality (≥0.8): {high_quality}")

    await QdrantManager.close()
    logger.info("Qdrant client closed")


if __name__ == "__main__":
    print("=" * 60)
    print("  Facebook Surfer - Trajectory Seeding Script")
    print("=" * 60)
    print("")
    print("This script will seed Qdrant with initial successful trajectories.")
    print("Run this once before using the planning agent for the first time.")
    print("")

    # Check for OpenAI API key
    import os

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not set!")
        print("   Embeddings will fail. Set the key in config/.env")
        print("")

    response = input("Continue? (y/N): ")
    if response.lower() == "y":
        asyncio.run(main())
    else:
        print("Aborted.")
