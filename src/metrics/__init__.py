"""Metrics collection for agent trajectory tracking.

This module provides callback handlers for capturing tool calls, LLM usage,
scoring, and trajectory summarization during agent runs.
"""

from src.metrics.models import ScoreBreakdown, ToolCall, Trajectory, TrajectoryMetrics
from src.metrics.scoring import calculate_score
from src.metrics.trajectory import summarize_trajectory
from src.metrics.trajectory_callback import TrajectoryCallbackHandler

__all__ = [
    "TrajectoryCallbackHandler",
    "calculate_score",
    "summarize_trajectory",
    "ScoreBreakdown",
    "ToolCall",
    "Trajectory",
    "TrajectoryMetrics",
]
