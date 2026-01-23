"""Tests for PlanningAgent."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.planner import PlanningAgent


class TestPlanningAgent:
    """Test PlanningAgent initialization and plan generation."""

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_init_default_model(self, mock_chat_openai, mock_create_deep_agent):
        """Test PlanningAgent initialization with default model."""
        mock_agent = MagicMock()
        mock_create_deep_agent.return_value = mock_agent

        agent = PlanningAgent()

        assert agent.model == "x-ai/grok-4.1-fast"
        assert agent.agent is not None
        assert agent.qdrant_client is None
        assert agent.api_key == "test-key"

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_init_custom_model(self, mock_chat_openai, mock_create_deep_agent):
        """Test PlanningAgent initialization with custom model."""
        mock_agent = MagicMock()
        mock_create_deep_agent.return_value = mock_agent

        agent = PlanningAgent(model="gpt-4o")

        assert agent.model == "gpt-4o"

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    def test_init_with_qdrant_client(self, mock_chat_openai, mock_create_deep_agent):
        """Test PlanningAgent initialization with Qdrant client."""
        mock_agent = MagicMock()
        mock_create_deep_agent.return_value = mock_agent
        mock_client = MagicMock()

        agent = PlanningAgent(qdrant_client=mock_client, api_key="test-key")

        assert agent.qdrant_client is mock_client

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_craft_success_plan_with_similar_workflows(self, mock_chat_openai, mock_create_deep_agent):
        """Test plan generation when similar workflows exist."""
        # Mock similar workflows
        mock_workflows = [
            {
                "task": "Post to Facebook group",
                "trajectory": "browser_navigate -> browser_click -> browser_type",
                "score": 0.95,
                "similarity": 0.88,
                "tool_calls": [
                    {"tool": "browser_navigate", "success": True},
                    {"tool": "browser_click", "success": True},
                ],
            },
            {
                "task": "Post message to group",
                "trajectory": "browser_navigate -> browser_click -> browser_type",
                "score": 0.90,
                "similarity": 0.82,
                "tool_calls": [],
            },
        ]

        # Mock agent
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "1. Navigate to group\n2. Click post button\n3. Type message\n4. Submit"
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [mock_message]}
        )
        mock_create_deep_agent.return_value = mock_agent

        # Mock Qdrant client
        mock_client = AsyncMock()

        # Mock retrieve_similar_trajectories
        with patch("src.agents.planner.retrieve_similar_trajectories", new=AsyncMock(return_value=mock_workflows)):
            agent = PlanningAgent(qdrant_client=mock_client)

            # Test
            plan = await agent.craft_success_plan("Post to my Facebook group")

            # Verify
            assert "Navigate" in plan or "Post" in plan
            mock_agent.ainvoke.assert_called_once()

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_craft_success_plan_cold_start(self, mock_chat_openai, mock_create_deep_agent):
        """Test plan generation when no similar workflows exist (cold start)."""
        # Mock empty retrieval
        with patch("src.agents.planner.retrieve_similar_trajectories", new=AsyncMock(return_value=[])):
            agent = PlanningAgent()

            plan = await agent.craft_success_plan("Post to my Facebook group")

            assert "No similar historical workflows" in plan

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_craft_success_plan_initializes_client(self, mock_chat_openai, mock_create_deep_agent):
        """Test that Qdrant client is initialized if not provided."""
        # Mock get_client
        mock_client = AsyncMock()
        with patch("src.agents.planner.QdrantManager.get_client", new=AsyncMock(return_value=mock_client)):
            with patch("src.agents.planner.retrieve_similar_trajectories", new=AsyncMock(return_value=[])):
                agent = PlanningAgent(qdrant_client=None)

                await agent.craft_success_plan("Test task")

                # Client should be initialized
                assert agent.qdrant_client is not None

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_format_workflows(self, mock_chat_openai, mock_create_deep_agent):
        """Test workflow formatting for LLM context."""
        mock_workflows = [
            {
                "task": "Post to Facebook",
                "trajectory": "nav -> click -> type",
                "score": 0.95,
                "similarity": 0.88,
                "tool_calls": [
                    {"tool": "browser_navigate"},
                    {"tool": "browser_click"},
                ],
            }
        ]

        agent = PlanningAgent()
        formatted = agent._format_workflows(mock_workflows)

        assert "0.95" in formatted
        assert "0.88" in formatted
        assert "Post to Facebook" in formatted
        assert "nav -> click -> type" in formatted
        assert "browser_navigate" in formatted
        assert "browser_click" in formatted

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_format_fallback_plan(self, mock_chat_openai, mock_create_deep_agent):
        """Test fallback plan formatting when LLM fails."""
        mock_workflows = [
            {
                "task": "Post to Facebook",
                "trajectory": "nav -> click",
                "score": 0.95,
                "similarity": 0.88,
            }
        ]

        agent = PlanningAgent()
        fallback = agent._format_fallback_plan(mock_workflows)

        assert "similar historical workflows" in fallback
        assert "Post to Facebook" in fallback
        assert "0.95" in fallback

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_craft_success_plan_with_top_k(self, mock_chat_openai, mock_create_deep_agent):
        """Test plan generation with custom top_k parameter."""
        # Mock 5 workflows
        mock_workflows = [
            {
                "task": f"Task {i}",
                "trajectory": "tool1 -> tool2",
                "score": 0.8 + (i * 0.01),
                "similarity": 0.8 - (i * 0.05),
                "tool_calls": [],
            }
            for i in range(1, 6)
        ]

        with patch("src.agents.planner.retrieve_similar_trajectories", new=AsyncMock()) as mock_retrieve:
            mock_retrieve.return_value = mock_workflows[:2]  # Return only 2

            agent = PlanningAgent()

            # Test with top_k=2
            await agent.craft_success_plan("Test task", top_k=2)

            # Verify retrieve was called with top_k=2
            mock_retrieve.assert_called_once_with(
                task="Test task",
                top_k=2,
                min_score=0.7,
                client=agent.qdrant_client,
            )

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_craft_success_plan_graceful_llm_failure(self, mock_chat_openai, mock_create_deep_agent):
        """Test that LLM failure falls back to formatted workflow data."""
        mock_workflows = [
            {
                "task": "Post to Facebook",
                "trajectory": "nav -> click -> type",
                "score": 0.95,
                "similarity": 0.88,
                "tool_calls": [],
            }
        ]

        with patch("src.agents.planner.retrieve_similar_trajectories", new=AsyncMock(return_value=mock_workflows)):
            # Mock agent to raise exception
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
            mock_create_deep_agent.return_value = mock_agent

            agent = PlanningAgent()

            plan = await agent.craft_success_plan("Post to group")

            # Should return fallback plan
            assert "similar historical workflows" in plan

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    async def test_format_workflows_with_empty_tool_calls(self, mock_chat_openai, mock_create_deep_agent):
        """Test formatting workflows with no tool calls."""
        mock_workflows = [
            {
                "task": "Simple task",
                "trajectory": "tool1 -> tool2",
                "score": 0.90,
                "similarity": 0.85,
                "tool_calls": [],
            }
        ]

        agent = PlanningAgent()
        formatted = agent._format_workflows(mock_workflows)

        assert "Simple task" in formatted
        assert "Tools used:" in formatted

    @patch("src.agents.planner.create_deep_agent")
    @patch("src.agents.planner.ChatOpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_openrouter_config_with_reasoning(self, mock_chat_openai, mock_create_deep_agent):
        """Test that ChatOpenAI is configured with OpenRouter and reasoning tokens."""
        PlanningAgent()

        # Verify ChatOpenAI was called with correct config
        mock_chat_openai.assert_called_once()
        call_kwargs = mock_chat_openai.call_args

        assert "base_url" in call_kwargs[1]
        assert call_kwargs[1]["base_url"] == "https://openrouter.ai/api/v1"
        assert "default_headers" in call_kwargs[1]
        assert "extra_body" in call_kwargs[1]
        assert "reasoning" in call_kwargs[1]["extra_body"]
        assert call_kwargs[1]["extra_body"]["reasoning"]["effort"] == "medium"


@patch("src.agents.planner.create_deep_agent")
@patch("src.agents.planner.ChatOpenAI")
@patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
def test_planning_agent_sync(mock_chat_openai, mock_create_deep_agent):
    """Run sync tests."""
    test_instance = TestPlanningAgent()

    # Basic init tests
    test_instance.test_init_default_model()
    test_instance.test_init_custom_model()
    test_instance.test_init_with_qdrant_client()
    test_instance.test_format_workflows()
    test_instance.test_format_fallback_plan()
    test_instance.test_format_workflows_with_empty_tool_calls()
    test_instance.test_openrouter_config_with_reasoning()

    # Run async tests
    asyncio.run(test_instance.test_craft_success_plan_with_similar_workflows())
    asyncio.run(test_instance.test_craft_success_plan_cold_start())
    asyncio.run(test_instance.test_craft_success_plan_initializes_client())
    asyncio.run(test_instance.test_craft_success_plan_with_top_k())
    asyncio.run(test_instance.test_craft_success_plan_graceful_llm_failure())
