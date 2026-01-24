"""Tests for TrajectoryCallbackHandler."""


from langchain_core.outputs import LLMResult

from src.metrics.trajectory_callback import TrajectoryCallbackHandler


class TestTrajectoryCallbackHandler:
    """Test suite for TrajectoryCallbackHandler."""

    def test_initialization(self) -> None:
        """Test callback handler initializes correctly."""
        callback = TrajectoryCallbackHandler()
        assert callback.trajectory == []
        assert callback.tool_metrics["tool_success"] == []
        assert callback.tool_metrics["latencies"] == []
        assert callback.tool_metrics["token_usage"] == []

    def test_on_tool_start(self) -> None:
        """Test tool start event is recorded."""
        callback = TrajectoryCallbackHandler()

        serialized = {"name": "test_tool"}
        callback.on_tool_start(serialized, "test input", run_id="run1")

        assert len(callback.trajectory) == 1
        event = callback.trajectory[0]
        assert event["type"] == "tool_start"
        assert event["tool"] == "test_tool"
        assert event["input"] == "test input"
        assert event["status"] == "in_progress"
        assert "start_time" in event

    def test_on_tool_end(self) -> None:
        """Test tool end event updates matching start event."""
        callback = TrajectoryCallbackHandler()

        # Start tool
        serialized = {"name": "test_tool"}
        callback.on_tool_start(serialized, "test input", run_id="run1")

        # End tool
        callback.on_tool_end("test output", run_id="run1")

        assert len(callback.trajectory) == 1
        event = callback.trajectory[0]
        assert event["status"] == "success"
        assert event["output"] == "test output"
        assert "end_time" in event
        assert "latency" in event
        assert event["latency"] >= 0

    def test_on_tool_error(self) -> None:
        """Test tool error marks tool as failed."""
        callback = TrajectoryCallbackHandler()

        # Start tool
        serialized = {"name": "test_tool"}
        callback.on_tool_start(serialized, "test input", run_id="run1")

        # Tool error
        error = Exception("Test error")
        callback.on_tool_error(error, run_id="run1")

        assert len(callback.trajectory) == 1
        event = callback.trajectory[0]
        assert event["status"] == "failed"
        assert "error" in event
        assert event["error"] == "Test error"

    def test_multiple_tool_calls(self) -> None:
        """Test multiple tool calls are tracked in order."""
        callback = TrajectoryCallbackHandler()

        # Tool 1
        callback.on_tool_start({"name": "tool1"}, "input1", run_id="run1")
        callback.on_tool_end("output1", run_id="run1")

        # Tool 2
        callback.on_tool_start({"name": "tool2"}, "input2", run_id="run2")
        callback.on_tool_end("output2", run_id="run2")

        # Tool 3 (error)
        callback.on_tool_start({"name": "tool3"}, "input3", run_id="run3")
        callback.on_tool_error(Exception("error3"), run_id="run3")

        assert len(callback.trajectory) == 3
        assert callback.trajectory[0]["tool"] == "tool1"
        assert callback.trajectory[1]["tool"] == "tool2"
        assert callback.trajectory[2]["tool"] == "tool3"
        assert callback.trajectory[0]["status"] == "success"
        assert callback.trajectory[1]["status"] == "success"
        assert callback.trajectory[2]["status"] == "failed"

    def test_on_llm_start(self) -> None:
        """Test LLM start event is recorded."""
        callback = TrajectoryCallbackHandler()

        callback.on_llm_start(["test prompt"], run_id="llm1")

        assert len(callback.trajectory) == 1
        event = callback.trajectory[0]
        assert event["type"] == "llm_start"
        assert event["prompts"] == ["test prompt"]
        assert "start_time" in event

    def test_on_llm_end(self) -> None:
        """Test LLM end event captures token usage."""
        callback = TrajectoryCallbackHandler()

        # Create mock LLM result
        llm_result = LLMResult(
            generations=[],
            llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 20}},
        )

        callback.on_llm_end(llm_result, run_id="llm1")

        assert len(callback.trajectory) == 1
        event = callback.trajectory[0]
        assert event["type"] == "llm_end"
        assert event["token_usage"] == {"prompt_tokens": 10, "completion_tokens": 20}

    def test_on_chat_model_start(self) -> None:
        """Test chat model start event is recorded."""
        callback = TrajectoryCallbackHandler()

        from langchain_core.messages import HumanMessage

        messages = [[HumanMessage(content="Hello")]]

        callback.on_chat_model_start({"name": "gpt-4"}, messages, run_id="chat1")

        assert len(callback.trajectory) == 1
        event = callback.trajectory[0]
        assert event["type"] == "chat_model_start"
        assert event["model"] == "gpt-4"
        assert event["messages"] == [["Hello"]]

    def test_get_trajectory(self) -> None:
        """Test get_trajectory returns a copy."""
        callback = TrajectoryCallbackHandler()

        callback.on_tool_start({"name": "tool1"}, "input", run_id="run1")
        trajectory1 = callback.get_trajectory()

        # Modify returned trajectory
        trajectory1.append({"test": "modification"})

        # Original should be unchanged
        trajectory2 = callback.get_trajectory()
        assert len(callback.trajectory) == 1
        assert len(trajectory2) == 1

    def test_get_metrics(self) -> None:
        """Test get_metrics returns captured metrics."""
        callback = TrajectoryCallbackHandler()

        # Simulate some tool calls
        callback.on_tool_start({"name": "tool1"}, "input", run_id="run1")
        callback.on_tool_end("output", run_id="run1")

        callback.on_tool_start({"name": "tool2"}, "input", run_id="run2")
        callback.on_tool_error(Exception("error"), run_id="run2")

        metrics = callback.get_metrics()
        assert metrics["tool_success"] == [True, False]
        assert len(metrics["latencies"]) == 2
        assert all(lat >= 0 for lat in metrics["latencies"])

    def test_clear(self) -> None:
        """Test clear resets all data."""
        callback = TrajectoryCallbackHandler()

        callback.on_tool_start({"name": "tool1"}, "input", run_id="run1")
        callback.on_tool_end("output", run_id="run1")

        assert len(callback.trajectory) > 0
        assert len(callback.tool_metrics["tool_success"]) > 0

        callback.clear()

        assert callback.trajectory == []
        assert callback.tool_metrics["tool_success"] == []
        assert callback.tool_metrics["latencies"] == []
        assert callback.tool_metrics["token_usage"] == []

    def test_thread_safety(self) -> None:
        """Test callback handler is thread-safe."""
        import threading

        callback = TrajectoryCallbackHandler()

        def record_tools(thread_id: int) -> None:
            for i in range(10):
                callback.on_tool_start(
                    {"name": f"tool_{thread_id}_{i}"}, f"input_{i}", run_id=f"run_{thread_id}_{i}"
                )
                callback.on_tool_end(f"output_{i}", run_id=f"run_{thread_id}_{i}")

        threads = [threading.Thread(target=record_tools, args=(i,)) for i in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 30 events (3 threads * 10 tools)
        assert len(callback.trajectory) == 30
