#!/usr/bin/env python3
"""Standalone trajectory analysis - no external dependencies required.

This script demonstrates how verification rules will filter failed trajectories
before storing them in RAG.
"""

import json
from dataclasses import dataclass
from typing import Any

# Scoring weights (from scoring.py)
TOOL_SUCCESS_WEIGHT = 0.40
LATENCY_WEIGHT = 0.20
TOKEN_WEIGHT = 0.20
OUTCOME_WEIGHT = 0.20


@dataclass
class ScoreBreakdown:
    total: float
    components: dict[str, float]


def calculate_score(
    tool_success: list[bool],
    latencies: list[float],
    outcome_match: float = 0.0,  # Default to 0 (unverified)
) -> ScoreBreakdown:
    """Calculate weighted trajectory score."""
    if not tool_success:
        return ScoreBreakdown(total=0.0, components={})
    
    tool_success_score = sum(tool_success) / len(tool_success)
    latency_score = max(0.0, 1.0 - (sum(latencies) / len(latencies) / 30.0)) if latencies else 0.0
    
    total = (
        TOOL_SUCCESS_WEIGHT * tool_success_score
        + LATENCY_WEIGHT * latency_score
        + OUTCOME_WEIGHT * outcome_match
    )
    
    return ScoreBreakdown(
        total=total,
        components={
            "tool_success": tool_success_score,
            "latency": latency_score,
            "outcome_match": outcome_match,
        }
    )


def should_store_trajectory(metrics: dict[str, Any]) -> tuple[bool, str | None]:
    """Determine if a trajectory should be stored in RAG.
    
    This implements the verification rules to filter out failed trajectories.
    
    Args:
        metrics: Dict with tool_success list, latencies list
        
    Returns:
        Tuple of (should_store, rejection_reason)
    """
    tool_success = metrics.get("tool_success", [])
    latencies = metrics.get("latencies", [])
    
    if not tool_success:
        return False, "No tool calls recorded"
    
    # Calculate basic stats
    total_tools = len(tool_success)
    successful_tools = sum(tool_success)
    failed_tools = total_tools - successful_tools
    success_rate = successful_tools / total_tools
    
    # Rule 1: Success rate threshold (< 50% = reject)
    if success_rate < 0.5:
        return False, f"Tool success rate too low ({success_rate:.1%})"
    
    # Rule 2: Terminal failure check (last tool(s) failed = likely incomplete)
    last_n = min(3, len(tool_success))
    if False in tool_success[-last_n:]:
        # Check if there are ANY failures in last 3 tools
        last_failures = tool_success[-last_n:].count(False)
        if last_failures > 0 and failed_tools > 0:
            return False, f"Task ended with {last_failures} failure(s) - likely incomplete"
    
    # Rule 3: Consecutive failures check (>= 3 in a row = fundamental problem)
    max_consecutive = 0
    current_consecutive = 0
    for success in tool_success:
        if not success:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    if max_consecutive >= 3:
        return False, f"Too many consecutive failures ({max_consecutive})"
    
    # Rule 4: Calculate score and check minimum
    score_result = calculate_score(tool_success, latencies)
    if score_result.total < 0.5:
        return False, f"Score too low ({score_result.total:.2f} < 0.5)"
    
    return True, None


def main():
    """Test verification rules with different scenarios."""
    print("=" * 70)
    print("TRAJECTORY VERIFICATION ANALYSIS")
    print("=" * 70)
    print()
    
    # Test scenarios
    scenarios = [
        {
            "name": "✅ Successful Trajectory",
            "tool_success": [True, True, True, True],
            "latencies": [2.0, 0.3, 0.5, 0.3],
        },
        {
            "name": "❌ Failed Trajectory (mostly failures)",
            "tool_success": [True, False, False, False],
            "latencies": [2.0, 0.3, 0.5, 0.3],
        },
        {
            "name": "⚠️ Terminal Failure (ended with error)",
            "tool_success": [True, True, True, False],
            "latencies": [2.0, 0.3, 0.5, 5.0],
        },
        {
            "name": "✅ Recovery (failure then success)",
            "tool_success": [True, False, True, True],
            "latencies": [2.0, 0.3, 0.5, 0.3],
        },
        {
            "name": "❌ Three Consecutive Failures",
            "tool_success": [True, False, False, False, True],
            "latencies": [2.0, 0.3, 0.5, 0.3, 0.4],
        },
        {
            "name": "✅ Two Consecutive Failures (allowed)",
            "tool_success": [True, False, False, True, True],
            "latencies": [2.0, 0.3, 0.5, 0.3, 0.4],
        },
    ]
    
    for scenario in scenarios:
        name = scenario["name"]
        metrics = {
            "tool_success": scenario["tool_success"],
            "latencies": scenario["latencies"],
        }
        
        should_store, reason = should_store_trajectory(metrics)
        score = calculate_score(
            scenario["tool_success"],
            scenario["latencies"],
        )
        
        success_rate = sum(scenario["tool_success"]) / len(scenario["tool_success"])
        
        print(f"📊 {name}")
        print("-" * 50)
        print(f"   Tool Success: {scenario['tool_success']}")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Score: {score.total:.3f}")
        
        if should_store:
            print(f"   📦 Decision: STORE in RAG ✅")
        else:
            print(f"   🚫 Decision: REJECT ❌")
            print(f"      Reason: {reason}")
        print()
    
    print("=" * 70)
    print("VERIFICATION RULES")
    print("=" * 70)
    print("""
Rules implemented in should_store_trajectory():

1. SUCCESS RATE: Reject if < 50% of tools succeeded
2. TERMINAL FAILURE: Reject if any of last 3 tools failed
3. CONSECUTIVE FAILURES: Reject if >= 3 consecutive failures
4. MINIMUM SCORE: Reject if total score < 0.5 (based on tool success + latency)

These rules prevent storing:
- Workflows that mostly failed
- Workflows that didn't complete (ended with errors)
- Workflows with fundamental problems (repeated failures)
- Low-quality workflows

This ensures the RAG only learns from actually successful patterns!
""")


if __name__ == "__main__":
    main()
