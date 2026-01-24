"""Integration tests for planning flow end-to-end.

Tests the full loop: plan → execute → store → retrieve.
"""

import asyncio

from src.agents.planner import PlanningAgent
from src.storage.qdrant_client import QdrantManager
from src.storage.retrieval import count_trajectories, retrieve_similar_trajectories
from src.storage.trajectory_store import store_trajectory


class TestPlanningFlow:
    """Integration tests for planning flow."""

    async def test_full_learning_loop(self):
        """Test complete loop: seed → retrieve → plan."""
        # Setup
        client = await QdrantManager.get_client()

        # Store a trajectory
        point_id = await store_trajectory(
            task="Post message to Facebook group",
            trajectory_summary="browser_navigate -> browser_click -> browser_type -> browser_click",
            score=0.95,
            tool_calls=[
                {
                    "tool": "browser_navigate",
                    "input": '{"url": "https://facebook.com/groups/test"}',
                    "success": True,
                    "latency": 2.0,
                },
                {
                    "tool": "browser_click",
                    "input": '{"ref": "e15", "force": true}',
                    "success": True,
                    "latency": 0.3,
                },
                {
                    "tool": "browser_type",
                    "input": '{"text": "Test message", "ref": "e16"}',
                    "success": True,
                    "latency": 0.5,
                },
                {
                    "tool": "browser_click",
                    "input": '{"ref": "e50", "force": true}',
                    "success": True,
                    "latency": 0.3,
                },
            ],
            client=client,
        )

        assert point_id is not None

        # Retrieve similar trajectory
        similar = await retrieve_similar_trajectories(
            task="Post a message to my Facebook group",
            top_k=1,
            min_score=0.7,
            client=client,
        )

        assert len(similar) > 0
        assert similar[0]["score"] >= 0.7

        # Generate plan
        planner = PlanningAgent(qdrant_client=client)
        plan = await planner.craft_success_plan("Post a message to my Facebook group")

        assert plan is not None
        assert "No similar historical workflows" not in plan  # Should find the stored trajectory

    async def test_cold_start_to_learning_progression(self):
        """Test progression from cold start to having learned workflows."""
        client = await QdrantManager.get_client()

        # Step 1: Cold start (no trajectories)
        planner = PlanningAgent(qdrant_client=client)
        plan1 = await planner.craft_success_plan("Comment on a post")

        assert "No similar historical workflows" in plan1

        # Step 2: Store a trajectory
        await store_trajectory(
            task="Comment on Facebook post",
            trajectory_summary="browser_navigate -> browser_click -> browser_type -> browser_click",
            score=0.90,
            tool_calls=[
                {"tool": "browser_navigate", "input": "{}", "success": True, "latency": 1.5},
                {"tool": "browser_click", "input": '{"ref": "e20"}', "success": True, "latency": 0.3},
                {"tool": "browser_type", "input": '{"text": "Nice!"}', "success": True, "latency": 0.5},
                {"tool": "browser_click", "input": '{"ref": "e25"}', "success": True, "latency": 0.3},
            ],
            client=client,
        )

        # Step 3: Now planner should find similar workflow
        plan2 = await planner.craft_success_plan("Comment on a post")

        # Should have a plan now (not cold start message)
        assert "No similar historical workflows" not in plan2

    async def test_retrieve_filters_by_score(self):
        """Test that retrieval filters by minimum score."""
        client = await QdrantManager.get_client()

        # Store high-quality trajectory
        await store_trajectory(
            task="Like Facebook post",
            trajectory_summary="browser_navigate -> browser_click",
            score=0.95,
            tool_calls=[
                {"tool": "browser_navigate", "input": "{}", "success": True, "latency": 1.5},
                {"tool": "browser_click", "input": '{"aria_label": "Like"}', "success": True, "latency": 0.3},
            ],
            client=client,
        )

        # Store low-quality trajectory
        await store_trajectory(
            task="Like Facebook post",
            trajectory_summary="browser_navigate -> browser_click -> browser_click (failed retry)",
            score=0.50,
            tool_calls=[
                {"tool": "browser_navigate", "input": "{}", "success": True, "latency": 1.5},
                {"tool": "browser_click", "input": '{"ref": "e10"}', "success": False, "latency": 0.3},
                {"tool": "browser_click", "input": '{"ref": "e12"}', "success": True, "latency": 0.3},
            ],
            client=client,
        )

        # Retrieve with min_score=0.7 should only return high-quality
        similar = await retrieve_similar_trajectories(
            task="Like a post",
            top_k=10,
            min_score=0.7,
            client=client,
        )

        # All results should have score >= 0.7
        for result in similar:
            assert result["score"] >= 0.7

    async def test_plan_quality_uses_historical_patterns(self):
        """Test that generated plans incorporate historical patterns."""
        client = await QdrantManager.get_client()

        # Store successful workflow with specific pattern
        await store_trajectory(
            task="Share post to Facebook group",
            trajectory_summary="browser_navigate -> browser_click (share) -> browser_click (to group) -> browser_click (post)",
            score=0.92,
            tool_calls=[
                {"tool": "browser_navigate", "input": "{}", "success": True, "latency": 1.8},
                {"tool": "browser_click", "input": '{"button": "Share"}', "success": True, "latency": 0.4},
                {"tool": "browser_click", "input": '{"button": "Share to group"}', "success": True, "latency": 0.5},
                {"tool": "browser_click", "input": '{"button": "Post"}', "success": True, "latency": 0.4},
            ],
            client=client,
        )

        # Generate plan for similar task
        planner = PlanningAgent(qdrant_client=client)
        plan = await planner.craft_success_plan("Share this post to my group")

        # Plan should reference historical patterns
        # (actual content depends on LLM, but should be non-empty)
        assert plan is not None
        assert len(plan) > 0

    async def test_count_trajectories(self):
        """Test trajectory counting functionality."""
        client = await QdrantManager.get_client()

        # Get initial count
        initial_count = await count_trajectories(client=client)

        # Store a trajectory
        await store_trajectory(
            task="Test task for counting",
            trajectory_summary="browser_navigate -> browser_click",
            score=0.85,
            tool_calls=[
                {"tool": "browser_navigate", "input": "{}", "success": True, "latency": 1.5},
                {"tool": "browser_click", "input": '{"ref": "e10"}', "success": True, "latency": 0.3},
            ],
            client=client,
        )

        # Count should increase
        new_count = await count_trajectories(client=client)
        assert new_count > initial_count

        # Count with score filter
        high_quality_count = await count_trajectories(min_score=0.8, client=client)
        assert high_quality_count >= 1  # At least our 0.85 score trajectory

    async def test_planner_with_multiple_similar_workflows(self):
        """Test planner with multiple similar workflows available."""
        client = await QdrantManager.get_client()

        # Store multiple similar workflows
        for i in range(3):
            await store_trajectory(
                task=f"Post message {i} to group",
                trajectory_summary="browser_navigate -> browser_click -> browser_type -> browser_click",
                score=0.88 + (i * 0.02),  # 0.88, 0.90, 0.92
                tool_calls=[
                    {"tool": "browser_navigate", "input": "{}", "success": True, "latency": 2.0},
                    {"tool": "browser_click", "input": '{"ref": "e15"}', "success": True, "latency": 0.3},
                    {"tool": "browser_type", "input": '{"text": "Message"}', "success": True, "latency": 0.5},
                    {"tool": "browser_click", "input": '{"ref": "e50"}', "success": True, "latency": 0.3},
                ],
                client=client,
            )

        # Retrieve should return multiple (default top_k=3)
        similar = await retrieve_similar_trajectories(
            task="Post to group",
            top_k=3,
            min_score=0.7,
            client=client,
        )

        assert len(similar) >= 3

        # Plan should incorporate multiple patterns
        planner = PlanningAgent(qdrant_client=client)
        plan = await planner.craft_success_plan("Post to group")

        assert plan is not None


def run_tests():
    """Run all integration tests."""
    test_instance = TestPlanningFlow()

    asyncio.run(test_instance.test_full_learning_loop())
    print("✓ test_full_learning_loop passed")

    asyncio.run(test_instance.test_cold_start_to_learning_progression())
    print("✓ test_cold_start_to_learning_progression passed")

    asyncio.run(test_instance.test_retrieve_filters_by_score())
    print("✓ test_retrieve_filters_by_score passed")

    asyncio.run(test_instance.test_plan_quality_uses_historical_patterns())
    print("✓ test_plan_quality_uses_historical_patterns passed")

    asyncio.run(test_instance.test_count_trajectories())
    print("✓ test_count_trajectories passed")

    asyncio.run(test_instance.test_planner_with_multiple_similar_workflows())
    print("✓ test_planner_with_multiple_similar_workflows passed")

    print("\nAll integration tests passed!")


if __name__ == "__main__":
    run_tests()
