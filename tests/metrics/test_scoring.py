"""Tests for scoring algorithm and trajectory summarization."""

from datetime import datetime, timezone

from src.metrics.models import ScoreBreakdown, ToolCall
from src.metrics.scoring import calculate_score
from src.metrics.trajectory import summarize_trajectory


class TestCalculateScore:
    """Test weighted scoring algorithm."""

    def test_perfect_score(self):
        """Test trajectory with all successful tools, low latency, low tokens."""
        result = calculate_score(
            tool_success=[True, True, True],
            latencies=[0.5, 1.0, 0.3],
            token_usage=[{"total_tokens": 1000}],
            outcome_match=1.0,
        )

        assert result.total > 0.9
        assert result.components["tool_success"] == 1.0
        assert result.components["latency"] > 0.95
        assert result.components["token_cost"] >= 0.8
        assert result.components["outcome_match"] == 1.0

    def test_failed_trajectory(self):
        """Test trajectory with failures and poor metrics."""
        result = calculate_score(
            tool_success=[False, True],
            latencies=[45.0, 30.0],
            token_usage=[{"total_tokens": 10000}],
            outcome_match=0.0,
        )

        assert result.total < 0.5
        assert result.components["tool_success"] == 0.5
        assert result.components["latency"] == 0.0  # Over 30s target
        assert result.components["token_cost"] == 0.0  # Over 5000 target
        assert result.components["outcome_match"] == 0.0

    def test_empty_trajectory(self):
        """Test empty trajectory returns zero score."""
        result = calculate_score(
            tool_success=[],
            latencies=[],
            token_usage=[],
        )

        assert result.total == 0.0
        assert all(v == 0.0 for v in result.components.values())

    def test_weight_distribution(self):
        """Test that weights sum to 1.0."""
        result = calculate_score(
            tool_success=[True],
            latencies=[15.0],  # Exactly half of target
            token_usage=[{"total_tokens": 2500}],  # Exactly half of target
            outcome_match=1.0,
        )

        # tool_success: 1.0 * 0.4 = 0.4
        # latency: 0.5 * 0.2 = 0.1
        # token_cost: 0.5 * 0.2 = 0.1
        # outcome_match: 1.0 * 0.2 = 0.2
        # total = 0.8
        assert abs(result.total - 0.8) < 0.01

    def test_latency_normalization(self):
        """Test latency score normalization against 30s target."""
        # 0s latency = 1.0 score
        result = calculate_score(
            tool_success=[True],
            latencies=[0.0],
            token_usage=[],
            outcome_match=0.0,
        )
        assert result.components["latency"] == 1.0

        # 15s latency = 0.5 score
        result = calculate_score(
            tool_success=[True],
            latencies=[15.0],
            token_usage=[],
            outcome_match=0.0,
        )
        assert result.components["latency"] == 0.5

        # 30s latency = 0.0 score
        result = calculate_score(
            tool_success=[True],
            latencies=[30.0],
            token_usage=[],
            outcome_match=0.0,
        )
        assert result.components["latency"] == 0.0

        # 60s latency = 0.0 score (clamped)
        result = calculate_score(
            tool_success=[True],
            latencies=[60.0],
            token_usage=[],
            outcome_match=0.0,
        )
        assert result.components["latency"] == 0.0

    def test_token_normalization(self):
        """Test token score normalization against 5000 target."""
        # 0 tokens = 1.0 score
        result = calculate_score(
            tool_success=[True],
            latencies=[],
            token_usage=[{"total_tokens": 0}],
            outcome_match=0.0,
        )
        assert result.components["token_cost"] == 1.0

        # 2500 tokens = 0.5 score
        result = calculate_score(
            tool_success=[True],
            latencies=[],
            token_usage=[{"total_tokens": 2500}],
            outcome_match=0.0,
        )
        assert result.components["token_cost"] == 0.5

        # 5000 tokens = 0.0 score
        result = calculate_score(
            tool_success=[True],
            latencies=[],
            token_usage=[{"total_tokens": 5000}],
            outcome_match=0.0,
        )
        assert result.components["token_cost"] == 0.0

    def test_missing_token_usage(self):
        """Test handling of missing total_tokens in dict."""
        result = calculate_score(
            tool_success=[True],
            latencies=[],
            token_usage=[{"other_key": "value"}],
            outcome_match=0.0,
        )
        assert result.components["token_cost"] == 1.0  # 0 tokens = 1.0

    def test_multiple_llm_calls(self):
        """Test aggregation of multiple token usage records."""
        result = calculate_score(
            tool_success=[True],
            latencies=[],
            token_usage=[
                {"total_tokens": 1000},
                {"total_tokens": 1500},
                {"total_tokens": 500},
            ],
            outcome_match=0.0,
        )
        # Total: 3000 tokens
        # Score: 1 - (3000 / 5000) = 0.4
        assert abs(result.components["token_cost"] - 0.4) < 0.01


class TestSummarizeTrajectory:
    """Test trajectory summarization for embedding."""

    def test_basic_summary(self):
        """Test basic trajectory summary format."""
        tool_calls = [
            {"tool": "browser_snapshot", "success": True},
            {"tool": "browser_click", "success": True},
            {"tool": "browser_type", "success": True},
        ]

        summary = summarize_trajectory("Post to group", [], tool_calls)

        assert "Post to group" in summary
        assert "browser_snapshot" in summary
        assert "browser_click" in summary
        assert "browser_type" in summary
        assert "success" in summary

    def test_partial_success_summary(self):
        """Test summary with partial success."""
        tool_calls = [
            {"tool": "browser_snapshot", "success": True},
            {"tool": "browser_click", "success": True},
            {"tool": "browser_type", "success": False},
        ]

        summary = summarize_trajectory("Post to group", [], tool_calls)

        assert "partial success" in summary
        assert "2/3" in summary

    def test_failed_summary(self):
        """Test summary with mostly failures."""
        tool_calls = [
            {"tool": "browser_snapshot", "success": True},
            {"tool": "browser_click", "success": False},
            {"tool": "browser_type", "success": False},
        ]

        summary = summarize_trajectory("Post to group", [], tool_calls)

        assert "failed" in summary
        assert "1/3" in summary

    def test_empty_trajectory(self):
        """Test summary with no tool calls."""
        summary = summarize_trajectory("Do nothing", [], [])

        assert "Do nothing" in summary
        assert "no tools executed" in summary

    def test_long_summary_truncation(self):
        """Test that long summaries are truncated to 500 chars."""
        # Create a very long task
        long_task = "Post " * 100  # ~500 chars
        tool_calls = [{"tool": "browser_click", "success": True}]

        summary = summarize_trajectory(long_task, [], tool_calls)

        assert len(summary) <= 500
        assert summary.endswith("...")

    def test_unknown_tool_names(self):
        """Test handling of missing tool names."""
        tool_calls = [
            {"success": True},  # No "tool" key
            {"tool": "browser_click", "success": True},
        ]

        summary = summarize_trajectory("Test task", [], tool_calls)

        assert "unknown" in summary
        assert "browser_click" in summary


class TestScoreBreakdown:
    """Test ScoreBreakdown model."""

    def test_score_breakdown_creation(self):
        """Test creating ScoreBreakdown instance."""
        breakdown = ScoreBreakdown(
            total=0.85,
            components={
                "tool_success": 1.0,
                "latency": 0.9,
                "token_cost": 0.8,
                "outcome_match": 0.7,
            },
        )

        assert breakdown.total == 0.85
        assert breakdown.components["tool_success"] == 1.0
        assert len(breakdown.components) == 4


class TestToolCall:
    """Test ToolCall model."""

    def test_tool_call_creation(self):
        """Test creating ToolCall instance."""
        call = ToolCall(
            tool="browser_click",
            input='{"ref": "e42"}',
            output='{"success": true}',
            success=True,
            latency=0.5,
            timestamp=datetime.now(timezone.utc),
        )

        assert call.tool == "browser_click"
        assert call.success is True
        assert call.latency == 0.5
        assert call.error is None

    def test_tool_call_with_error(self):
        """Test ToolCall with error."""
        call = ToolCall(
            tool="browser_click",
            input='{"ref": "e42"}',
            success=False,
            latency=1.0,
            timestamp=datetime.now(timezone.utc),
            error="Element not found",
        )

        assert call.success is False
        assert call.error == "Element not found"
        assert call.output is None
