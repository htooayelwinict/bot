"""Trajectory summarization for embedding generation.

Formats trajectory data into text summaries suitable for embedding
and semantic search.
"""


def summarize_trajectory(
    task: str,
    trajectory: list[str],
    tool_calls: list[dict],
) -> str:
    """Create text summary of trajectory for embedding.

    Format: "task -> tool1 -> tool2 -> ... -> outcome"
    Include success/failure indicators and statistics.

    Args:
        task: User task description
        trajectory: List of trajectory event types (for compatibility)
        tool_calls: List of tool call records

    Returns:
        Text summary under 500 characters

    Examples:
        >>> calls = [
        ...     {"tool": "browser_snapshot", "success": True},
        ...     {"tool": "browser_click", "success": True},
        ... ]
        >>> summary = summarize_trajectory("Post to group", [], calls)
        >>> print(summary)
    """
    # Count tool results
    successful = sum(1 for tc in tool_calls if tc.get("success", True))
    total = len(tool_calls)

    # Build tool sequence
    tools = []
    for tc in tool_calls:
        tool_name = tc.get("tool", "unknown")
        tools.append(tool_name)

    # Build summary
    parts = [task]
    if tools:
        parts.append(" -> ".join(tools))

    # Add outcome
    if total > 0:
        success_rate = successful / total
        if success_rate >= 1.0:
            outcome = "success"
        elif success_rate >= 0.5:
            outcome = f"partial success ({successful}/{total})"
        else:
            outcome = f"failed ({successful}/{total})"
        parts.append(outcome)
    else:
        parts.append("no tools executed")

    summary = " -> ".join(parts)

    # Truncate to 500 chars for embedding limits
    if len(summary) > 500:
        summary = summary[:497] + "..."

    return summary
