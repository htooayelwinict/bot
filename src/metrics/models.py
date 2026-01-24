"""Pydantic data models for metrics and trajectory tracking.

Defines the data structures used throughout the metrics collection,
scoring, and storage pipeline.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Individual tool invocation record."""

    tool: str = Field(description="Name of the tool called")
    input: str = Field(description="Input parameters to the tool")
    output: str | None = Field(default=None, description="Tool output if successful")
    success: bool = Field(description="Whether the tool call succeeded")
    latency: float = Field(description="Execution time in seconds")
    timestamp: datetime = Field(description="When the tool was called")
    error: str | None = Field(default=None, description="Error message if failed")


class TrajectoryMetrics(BaseModel):
    """Captured execution metrics."""

    tool_success: list[bool] = Field(
        default_factory=list, description="Success status of each tool call"
    )
    latencies: list[float] = Field(
        default_factory=list, description="Latency of each tool call in seconds"
    )
    token_usage: list[dict[str, Any]] = Field(
        default_factory=list, description="Token usage from LLM calls"
    )
    outcome_match: float = Field(
        default=0.5, ge=0.0, le=1.0, description="User feedback on outcome match"
    )


class ScoreBreakdown(BaseModel):
    """Weighted scoring results."""

    total: float = Field(description="Final weighted score (0.0-1.0)")
    components: dict[str, float] = Field(description="Individual component scores")


class Trajectory(BaseModel):
    """Complete execution trajectory record."""

    task: str = Field(description="User task description")
    tool_calls: list[ToolCall] = Field(
        default_factory=list, description="Sequential tool invocations"
    )
    metrics: TrajectoryMetrics = Field(
        default_factory=TrajectoryMetrics, description="Execution metrics"
    )
    score: ScoreBreakdown | None = Field(
        default=None, description="Calculated score if available"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When execution occurred",
    )
