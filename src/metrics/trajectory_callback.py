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
        self._loop_detected = False  # Flag for infinite loop detection
        self._consecutive_empty_results = 0  # Track empty/useless results
        self._same_tool_streak = {"tool": None, "count": 0}  # Track same tool repetition

    def check_infinite_loop(self, max_repeated_calls: int = 5) -> bool:
        """Detect infinite loops by checking for repeated tool calls.
        
        Checks if the same tool is being called repeatedly with similar inputs.
        This helps detect stuck agents.
        
        Args:
            max_repeated_calls: Max times same tool can repeat before flagging as loop (default: 5)
        
        Returns:
            True if infinite loop detected, False otherwise
        """
        if self._loop_detected:
            return True  # Already detected
            
        with self._lock:
            # Look at last N tool calls
            tool_calls = [e for e in self.trajectory if e.get("type") == "tool_start"]
            
            if len(tool_calls) < max_repeated_calls:
                return False
            
            # Check last N calls
            last_calls = tool_calls[-max_repeated_calls:]
            
            # All same tool?
            tools = [c.get("tool") for c in last_calls]
            if len(set(tools)) == 1:
                # Same tool repeated
                same_tool = tools[0]
                
                # Check if inputs are similar (not just same tool, but same params)
                inputs = [c.get("input", "") for c in last_calls]
                if len(set(str(i)[:100] for i in inputs)) == 1:
                    # Same tool with same/similar inputs = LOOP!
                    self._loop_detected = True
                    return True
        
        return False

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
            
            # Detect empty/useless results that indicate stuck behavior
            is_empty = self._is_empty_result(output)
            
            # Find matching tool_start event
            tool_name = None
            for event in reversed(self.trajectory):
                if (
                    event.get("type") == "tool_start"
                    and event.get("status") == "in_progress"
                    and event.get("run_id") == str(run_id)
                ):
                    tool_name = event.get("tool")
                    event["output"] = output
                    event["end_time"] = end_time
                    event["latency"] = end_time - event["start_time"]
                    # Mark as failed if error OR consistently empty
                    event["status"] = "failed" if (is_error or is_empty) else "success"
                    # Track metrics
                    self.tool_metrics["tool_success"].append(not (is_error or is_empty))
                    self.tool_metrics["latencies"].append(event["latency"])
                    break
            
            if tool_name is None:
                # Orphaned tool_end (shouldn't happen)
                self.trajectory.append(
                    {
                        "type": "tool_end_orphan",
                        "output": output,
                        "end_time": end_time,
                        "status": "failed" if (is_error or is_empty) else "success",
                        "run_id": str(run_id),
                    }
                )
                return
            
            # RUNTIME LOOP DETECTION: Check for stuck patterns
            # Track empty results
            if is_empty:
                self._consecutive_empty_results += 1
            else:
                self._consecutive_empty_results = 0
            
            # Track same tool repetition
            if tool_name == self._same_tool_streak["tool"]:
                self._same_tool_streak["count"] += 1
            else:
                self._same_tool_streak = {"tool": tool_name, "count": 1}
            
            # ABORT CRITERIA: Raise exception to stop agent execution
            # 1. Same tool with empty results 4+ times in a row
            if self._consecutive_empty_results >= 5:
                self._loop_detected = True
                raise RuntimeError(
                    f"🛑 INFINITE LOOP DETECTED: Tool '{tool_name}' returned empty/useless results "
                    f"{self._consecutive_empty_results} times consecutively. Aborting execution to prevent waste."
                )
            
            # 2. Same tool called 6+ times in a row (regardless of output)
            if self._same_tool_streak["count"] >= 6:
                self._loop_detected = True
                raise RuntimeError(
                    f"🛑 INFINITE LOOP DETECTED: Tool '{tool_name}' called "
                    f"{self._same_tool_streak['count']} times in a row. Aborting execution."
                )
            
            # 3. Check for repeated identical calls (original check)
            if len(self.trajectory) >= 5:
                recent_tools = [e.get("tool") for e in self.trajectory[-5:] if e.get("type") == "tool_start"]
                recent_inputs = [str(e.get("input", ""))[:100] for e in self.trajectory[-5:] if e.get("type") == "tool_start"]
                
                if len(recent_tools) >= 5 and len(set(recent_tools)) == 1 and len(set(recent_inputs)) == 1:
                    self._loop_detected = True
                    raise RuntimeError(
                        f"🛑 INFINITE LOOP DETECTED: Same tool '{tool_name}' with identical inputs "
                        f"repeated 5+ times. Aborting execution."
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
    
    def _is_empty_result(self, output: str | dict | Any) -> bool:
        """Detect if tool output is empty/useless (indicates stuck behavior).
        
        Args:
            output: Tool output string or dict
            
        Returns:
            True if output is empty, None, [], {}, or other useless result
        """
        if output is None:
            return True
        
        # Handle dict outputs
        if isinstance(output, dict):
            result = output.get("result")
            # Check if result field is empty
            if result is None or result == [] or result == {} or result == "":
                return True
            # Check full dict
            if not output or output == {}:
                return True
            return False
        
        # Handle list outputs
        if isinstance(output, list):
            return len(output) == 0
        
        # Handle string outputs
        if isinstance(output, str):
            output_stripped = output.strip()
            # Empty or just whitespace
            if not output_stripped:
                return True
            # Common empty result patterns
            empty_patterns = [
                "none",
                "null",
                "[]",
                "{}",
                "result: none",
                "result: null",
                "result: []",
                "<<<js_result_start>>>\nnone\n<<<js_result_end>>>",
                "<<<js_result_start>>>\nnull\n<<<js_result_end>>>",
                "<<<js_result_start>>>\n[]\n<<<js_result_end>>>",
            ]
            output_lower = output_stripped.lower()
            for pattern in empty_patterns:
                if pattern in output_lower:
                    return True
        
        return False


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
