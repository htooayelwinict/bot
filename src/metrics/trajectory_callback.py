"""Trajectory callback handler for LangChain agents.

Captures tool invocations, timing, success/failure, and token usage
during agent execution for metrics collection and analysis.
"""

import threading
import time
from typing import Any, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class TrajectoryCallbackHandler(BaseCallbackHandler):
    """Callback handler for capturing agent trajectory metrics.

    Records tool calls with timing and success/failure, plus LLM token usage.
    Thread-safe for concurrent agent executions.
    """

    def __init__(self) -> None:
        """Initialize the trajectory callback handler."""
        self.trajectory: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self.tool_metrics: dict[str, Any] = {
            "tool_success": [],
            "latencies": [],
            "token_usage": [],
        }

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Record tool start with input and timestamp.

        Args:
            serialized: Serialized tool representation
            input_str: Tool input parameters
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            tags: Tags for this run
            metadata: Metadata for this run
            **kwargs: Additional arguments
        """
        tool_name = serialized.get("name", "unknown")
        with self._lock:
            self.trajectory.append(
                {
                    "type": "tool_start",
                    "tool": tool_name,
                    "input": input_str,
                    "start_time": time.time(),
                    "status": "in_progress",
                    "run_id": str(run_id),
                }
            )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Record tool end with output and latency.

        Args:
            output: Tool output
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            **kwargs: Additional arguments
        """
        with self._lock:
            end_time = time.time()

            # Detect if output indicates an error (tools return error strings)
            is_error = self._is_error_output(output)

            # Find matching tool_start event
            for event in reversed(self.trajectory):
                if (
                    event.get("type") == "tool_start"
                    and event.get("status") == "in_progress"
                    and event.get("run_id") == str(run_id)
                ):
                    event["output"] = output
                    event["end_time"] = end_time
                    event["latency"] = end_time - event["start_time"]
                    event["status"] = "failed" if is_error else "success"
                    # Track metrics
                    self.tool_metrics["tool_success"].append(not is_error)
                    self.tool_metrics["latencies"].append(event["latency"])
                    return

            # Orphaned tool_end (shouldn't happen)
            self.trajectory.append(
                {
                    "type": "tool_end_orphan",
                    "output": output,
                    "end_time": end_time,
                    "status": "failed" if is_error else "success",
                    "run_id": str(run_id),
                }
            )

    def _is_error_output(self, output: str | dict | Any) -> bool:
        """Detect if tool output indicates an error.

        Args:
            output: Tool output string or dict

        Returns:
            True if output indicates an error/failure
        """
        if not output:
            return False

        # Handle dict outputs (common in our tools)
        if isinstance(output, dict):
            # specific key checks
            if "error" in output:
                return True
            # Convert to string for pattern matching
            output = str(output)

        if not isinstance(output, str):
            output = str(output)

        output_lower = output.lower()

        # Error patterns from tool decorators and common failures
        error_patterns = [
            "error executing",  # From async_session_tool decorator
            "error:",  # General error prefix
            "failed",  # Click failed, navigation failed, etc.
            "timeout",  # Timeout errors
            "stale element",  # Stale ref errors
            "cannot read properties of null",  # JS null errors
            "typeerror:",  # JavaScript type errors
            "locator.click:",  # Playwright locator errors
            "page.goto:",  # Navigation errors
            "ref resolution failed",  # Ref resolution errors
        ]

        return any(pattern in output_lower for pattern in error_patterns)


    def on_tool_error(
        self,
        error: Exception,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Record tool error and mark as failed.

        Args:
            error: Exception that occurred
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            **kwargs: Additional arguments
        """
        with self._lock:
            end_time = time.time()
            # Find matching tool_start event
            for event in reversed(self.trajectory):
                if (
                    event.get("type") == "tool_start"
                    and event.get("status") == "in_progress"
                    and event.get("run_id") == str(run_id)
                ):
                    event["error"] = str(error)
                    event["end_time"] = end_time
                    if "start_time" in event:
                        event["latency"] = end_time - event["start_time"]
                    event["status"] = "failed"
                    # Track metrics
                    self.tool_metrics["tool_success"].append(False)
                    self.tool_metrics["latencies"].append(event.get("latency", 0))
                    return

            # Orphaned tool_error (shouldn't happen)
            self.trajectory.append(
                {
                    "type": "tool_error_orphan",
                    "error": str(error),
                    "end_time": end_time,
                    "status": "failed",
                    "run_id": str(run_id),
                }
            )

    def on_llm_start(
        self,
        prompts: list[str],
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Record LLM start.

        Args:
            prompts: List of prompts sent to LLM
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            **kwargs: Additional arguments
        """
        with self._lock:
            self.trajectory.append(
                {
                    "type": "llm_start",
                    "prompts": prompts,
                    "start_time": time.time(),
                    "run_id": str(run_id),
                }
            )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Record LLM end with token usage.

        Args:
            response: LLM result with token usage
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            **kwargs: Additional arguments
        """
        with self._lock:
            token_usage: dict[str, Any] = {}
            if response.llm_output and isinstance(response.llm_output, dict):
                token_usage = response.llm_output.get("token_usage", {})

            self.trajectory.append(
                {
                    "type": "llm_end",
                    "token_usage": token_usage,
                    "end_time": time.time(),
                    "run_id": str(run_id),
                }
            )

            # Track token usage metrics
            if token_usage:
                self.tool_metrics["token_usage"].append(token_usage)

    def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM emits a new token (streaming).

        Args:
            token: The new token
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            **kwargs: Additional arguments
        """
        # Not tracking individual tokens for now
        pass

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Record chat model start.

        Args:
            serialized: Serialized model representation
            messages: Messages sent to model
            run_id: Unique identifier for this run
            parent_run_id: Parent run identifier
            **kwargs: Additional arguments
        """
        with self._lock:
            self.trajectory.append(
                {
                    "type": "chat_model_start",
                    "model": serialized.get("name", "unknown"),
                    "messages": [[msg.content for msg in msg_list] for msg_list in messages],
                    "start_time": time.time(),
                    "run_id": str(run_id),
                }
            )

    def get_trajectory(self) -> list[dict[str, Any]]:
        """Return a copy of captured trajectory data.

        Returns:
            List of trajectory events (tool calls, LLM calls, etc.)
        """
        with self._lock:
            return list(self.trajectory)

    def get_metrics(self) -> dict[str, Any]:
        """Return captured metrics summary.

        Returns:
            Dictionary with tool_success list, latencies list, token_usage list
        """
        with self._lock:
            return dict(self.tool_metrics)

    def get_score(
        self, outcome_match: float = 0.5
    ) -> dict[str, Any] | None:
        """Calculate weighted score from captured metrics.

        Args:
            outcome_match: User feedback on outcome match (0.0-1.0), default 0.5

        Returns:
            ScoreBreakdown dict with total and components, or None if no metrics
        """
        from src.metrics.scoring import calculate_score

        with self._lock:
            if not self.tool_metrics["tool_success"]:
                return None

            result = calculate_score(
                tool_success=self.tool_metrics["tool_success"],
                latencies=self.tool_metrics["latencies"],
                token_usage=self.tool_metrics["token_usage"],
                outcome_match=outcome_match,
            )
            return {
                "total": result.total,
                "components": result.components,
            }

    def clear(self) -> None:
        """Clear all captured trajectory data and metrics."""
        with self._lock:
            self.trajectory.clear()
            self.tool_metrics = {
                "tool_success": [],
                "latencies": [],
                "token_usage": [],
            }
