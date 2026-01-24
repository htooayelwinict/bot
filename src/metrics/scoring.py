"""Weighted scoring algorithm for trajectory evaluation.

Calculates multi-dimensional scores based on tool success, latency,
token cost, and outcome match using the 40/20/20/20 formula.
"""

from typing import Any

from src.metrics.models import ScoreBreakdown

# Scoring weights
TOOL_SUCCESS_WEIGHT = 0.40
LATENCY_WEIGHT = 0.20
TOKEN_WEIGHT = 0.20
OUTCOME_WEIGHT = 0.20

# Normalization targets
TARGET_LATENCY = 30.0  # seconds
TARGET_TOKENS = 5000  # total tokens


def calculate_score(
    tool_success: list[bool],
    latencies: list[float],
    token_usage: list[dict[str, Any]],
    outcome_match: float = 0.0,
) -> ScoreBreakdown:
    """Calculate weighted trajectory score.

    Args:
        tool_success: List of tool success/failure indicators
        latencies: List of tool latencies in seconds
        token_usage: List of token usage dicts with 'total_tokens' key
        outcome_match: User feedback on outcome (0.0-1.0), default 0.0 (unverified)

    Returns:
        ScoreBreakdown with total score and component breakdown

    Examples:
        >>> result = calculate_score(
        ...     tool_success=[True, True, True],
        ...     latencies=[0.5, 1.0, 0.3],
        ...     token_usage=[{'total_tokens': 1000}],
        ...     outcome_match=1.0
        ... )
        >>> print(f"Total: {result.total:.2f}")
    """
    # Handle empty trajectory
    if not tool_success:
        return ScoreBreakdown(
            total=0.0,
            components={
                "tool_success": 0.0,
                "latency": 0.0,
                "token_cost": 0.0,
                "outcome_match": 0.0,
            },
        )

    # Calculate tool success score (40% weight)
    tool_success_score = sum(tool_success) / len(tool_success)

    # Calculate latency score (20% weight)
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        latency_score = max(0.0, 1.0 - (avg_latency / TARGET_LATENCY))
    else:
        latency_score = 0.0

    # Calculate token score (20% weight)
    if token_usage:
        total_tokens = sum(
            usage.get("total_tokens", 0) for usage in token_usage if isinstance(usage, dict)
        )
        token_score = max(0.0, 1.0 - (total_tokens / TARGET_TOKENS))
    else:
        token_score = 0.0

    # Outcome match score (20% weight)
    outcome_score = outcome_match

    # Calculate weighted total
    total = (
        TOOL_SUCCESS_WEIGHT * tool_success_score
        + LATENCY_WEIGHT * latency_score
        + TOKEN_WEIGHT * token_score
        + OUTCOME_WEIGHT * outcome_score
    )

    return ScoreBreakdown(
        total=total,
        components={
            "tool_success": tool_success_score,
            "latency": latency_score,
            "token_cost": token_score,
            "outcome_match": outcome_score,
        },
    )
