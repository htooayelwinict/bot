"""Metrics middleware for orchestrating trajectory processing.

Coordinates scoring, PII redaction, and storage of trajectory data
after agent execution.
"""

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient

from src.metrics.trajectory_callback import TrajectoryCallbackHandler
from src.metrics.scoring import calculate_score
from src.metrics.trajectory import summarize_trajectory
from src.storage.qdrant_client import QdrantManager
from src.storage.trajectory_store import store_trajectory

from .pii_redaction import redact_trajectory

logger = logging.getLogger(__name__)


class MetricsMiddleware:
    """Orchestrate trajectory capture, scoring, and storage.

    Coordinates the complete metrics pipeline:
    1. Extract trajectory from callback handler
    2. Calculate weighted score
    3. Summarize trajectory for embedding
    4. Redact PII from data
    5. Store in Qdrant with embedding

    Handles errors gracefully at each step to avoid breaking
    agent execution if metrics processing fails.
    """

    def __init__(self) -> None:
        """Initialize the metrics middleware."""
        self._client: AsyncQdrantClient | None = None
        self._initialized = False

        try:
            from src.agents.reflection import ReflectionAgent
            self.reflection_agent: ReflectionAgent | None = ReflectionAgent()
        except Exception as e:
            logger.warning(f"Failed to initialize ReflectionAgent: {e}")
            self.reflection_agent = None

    async def initialize(self) -> None:
        """Initialize Qdrant client connection.

        Should be called before process_execution.
        """
        if not self._initialized:
            try:
                self._client = await QdrantManager.get_client()
                self._initialized = True
                logger.info("MetricsMiddleware initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Qdrant client: {e}")
                self._client = None

    async def process_execution(
        self,
        task: str,
        trajectory_data: dict[str, Any],
        callback: TrajectoryCallbackHandler,
    ) -> dict[str, Any]:
        """Process complete execution: score → redact → store.

        Args:
            task: The user task description
            trajectory_data: Raw trajectory data from callback
            callback: TrajectoryCallbackHandler with metrics

        Returns:
            Dict with processing results:
                - score: Total trajectory score (0.0-1.0)
                - stored: Whether trajectory was stored successfully
                - point_id: Qdrant point ID if stored

        Examples:
            >>> middleware = MetricsMiddleware()
            >>> await middleware.initialize()
            >>> result = await middleware.process_execution(
            ...     task="Post to Facebook",
            ...     trajectory_data=callback.get_trajectory(),
            ...     callback=callback
            ... )
        """
        try:
            # Note: Runtime loop detection now happens in callback's on_tool_end
            # This is a backup check for edge cases
            if callback._loop_detected:
                logger.warning(
                    "⚠️  Loop was detected during execution. Processing for RAG storage..."
                )
            
            # 1. Calculate score
            metrics = callback.get_metrics()
            score_result = calculate_score(
                tool_success=metrics["tool_success"],
                latencies=metrics["latencies"],
                token_usage=metrics["token_usage"],
            )

            # 2. Verify trajectory is worth storing
            should_store, rejection_reason = self._verify_trajectory(
                tool_success=metrics["tool_success"],
                score=score_result.total,
            )

            if not should_store:
                logger.info(
                    f"Trajectory rejected: {rejection_reason}. "
                    f"Score: {score_result.total:.3f}"
                )
                return {
                    "score": score_result.total,
                    "components": score_result.components,
                    "stored": False,
                    "point_id": None,
                    "rejected": True,
                    "rejection_reason": rejection_reason,
                }

            # 3. Summarize trajectory for embedding
            # Extract tool calls from trajectory data (trajectory_data is a list)
            tool_calls = self._extract_tool_calls(trajectory_data)
            logger.info(f"🔍 Extracted {len(tool_calls)} tool calls from {len(trajectory_data)} trajectory events")

            summary = summarize_trajectory(
                task=task,
                trajectory=[],
                tool_calls=tool_calls,
            )

            # 3b. Reflect on trajectory (Negative Learning)
            reflection = None
            if self.reflection_agent:
                try:
                    logger.info("🤔 Reflecting on execution...")
                    # Add timeout to prevent reflection agent from looping
                    import asyncio
                    
                    # We reconstruct a simple trajectory list from tool_calls for now
                    # since full logic requires parsing raw trajectory_data structure
                    reflection = await asyncio.wait_for(
                        self.reflection_agent.analyze_trajectory(
                            task=task,
                            trajectory=tool_calls,
                            score=score_result.total
                        ),
                        timeout=30.0  # 30 second timeout for reflection
                    )
                    # Validate reflection result
                    if not reflection or not isinstance(reflection, dict):
                        logger.warning("Reflection returned invalid/empty result")
                        reflection = None
                    elif not reflection.get('critique'):
                        logger.warning("Reflection missing required 'critique' field")
                        reflection = None
                    else:
                        # FIX: Add max_iterations flag to reflection if loop was detected
                        if callback._loop_detected:
                            reflection["max_iterations_exceeded"] = True
                            reflection["failure_reason"] = "Infinite loop: repeated identical tool calls"
                            reflection["critique"] = (
                                f"[INFINITE LOOP DETECTED] {reflection['critique']}\n\n"
                                f"⚠️ CRITICAL: Agent stuck in infinite loop (same tool repeated consecutively). "
                                f"This was likely caused by: 1) Wrong selector returning empty results, "
                                f"2) Retrying same approach without changing strategy, "
                                f"3) Not recognizing empty results as failures. "
                                f"Planner should avoid this exact selector/approach."
                            )
                        logger.info(f"✅ Reflection complete: {reflection.get('critique', '')[:80]}...")
                except asyncio.TimeoutError:
                    logger.error("❌ Reflection timed out after 30 seconds (possible nested loop)")
                    reflection = None
                except Exception as e:
                    logger.error(f"❌ Reflection failed: {e}", exc_info=True)
                    reflection = None
            else:
                logger.warning("⚠️  ReflectionAgent not initialized - skipping reflection")

            # 4. Redact PII from trajectory (for logging/debugging only)
            # Note: tool_calls are already extracted above
            _ = redact_trajectory(trajectory_data)

            # 5. Store in Qdrant
            point_id = None
            stored = False

            if self._client is not None:
                try:
                    point_id = await store_trajectory(
                        task=task,
                        trajectory_summary=summary,
                        score=score_result.total,
                        tool_calls=tool_calls,  # Use extracted tool_calls directly
                        reflection=reflection,
                        client=self._client,
                    )
                    stored = True
                    logger.info(
                        f"Stored trajectory {point_id} with score {score_result.total:.3f}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to store trajectory: {e}")
                    stored = False
            else:
                logger.warning("Qdrant client not available, skipping storage")

            return {
                "score": score_result.total,
                "components": score_result.components,
                "stored": stored,
                "point_id": point_id,
                "reflection": reflection,
            }

        except Exception as e:
            logger.error(f"Error processing execution metrics: {e}")
            return {
                "score": 0.0,
                "components": {},
                "stored": False,
                "point_id": None,
            }

    def _verify_trajectory(
        self,
        tool_success: list[bool],
        score: float,
    ) -> tuple[bool, str | None]:
        """Verify if trajectory should be stored in RAG.

        Applies rules to filter out failed or incomplete trajectories
        to prevent polluting the RAG with bad patterns.

        Args:
            tool_success: List of tool success/failure indicators.
            score: Calculated trajectory score.

        Returns:
            Tuple of (should_store, rejection_reason).
            If should_store is False, rejection_reason explains why.
        """
        if not tool_success:
            return False, "No tool calls recorded"

        # Calculate basic stats
        total_tools = len(tool_success)
        successful_tools = sum(tool_success)
        success_rate = successful_tools / total_tools

        # Rule 1: Success rate threshold (< 50% = reject)
        if success_rate < 0.5:
            return False, f"Tool success rate too low ({success_rate:.1%})"

        # Rule 2: Terminal failure (last tool failed = task likely incomplete)
        # Only reject if the FINAL tool failed (not just any recent failure)
        if not tool_success[-1]:
            return False, "Task ended with failure - likely incomplete"

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

        # Rule 4: Minimum score threshold
        if score < 0.5:
            return False, f"Score too low ({score:.2f} < 0.5)"

        return True, None

    def _extract_tool_calls(self, trajectory_data: dict[str, Any]) -> list[dict]:
        """Extract tool calls from trajectory data.

        Args:
            trajectory_data: Raw trajectory from callback handler

        Returns:
            List of tool call dicts suitable for summarization
        """
        tool_calls = []
        trajectory = trajectory_data.get("trajectory", [])

        # Log event type distribution for debugging
        event_types = {}
        for event in trajectory:
            etype = event.get("type", "unknown")
            event_types[etype] = event_types.get(etype, 0) + 1

        if event_types:
            logger.debug(f"📊 Event types in trajectory: {event_types}")

        for event in trajectory:
            if event.get("type") == "tool_start":
                tool_call = {
                    "type": "tool_start",  # Include type for reflection filtering
                    "tool": event.get("tool", "unknown"),
                    "input": event.get("input", {}),  # Include input for reflection analysis
                    "success": event.get("status") == "success",
                }
                if "latency" in event:
                    tool_call["latency"] = event["latency"]
                tool_calls.append(tool_call)

        logger.debug(f"🔧 Extracted {len(tool_calls)} tool_start events from {len(trajectory)} total events")
        return tool_calls

    async def close(self) -> None:
        """Close Qdrant client connection.

        Should be called on shutdown to clean up resources.
        """
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("MetricsMiddleware closed")
