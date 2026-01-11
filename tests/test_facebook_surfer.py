"""Tests for FacebookSurferAgent and ToolRegistry."""

import pytest

from src.agents.facebook_surfer import FacebookSurferAgent
from src.tools.registry import ToolRegistry, ToolCategory, ToolSpec, register_all_tools, registry


def test_tool_registry_empty():
    """Test empty registry state."""
    empty_registry = ToolRegistry()
    assert empty_registry.count() == 0
    assert empty_registry.list_names() == []
    assert empty_registry.get_all() == []


def test_tool_register_spec():
    """Test registering a tool spec."""
    from pydantic import BaseModel
    from langchain_core.tools import StructuredTool

    class DummyArgs(BaseModel):
        name: str

    def dummy_func(name: str) -> str:
        return f"Hello {name}"

    spec = ToolSpec(
        name="dummy_tool",
        category=ToolCategory.interaction,
        description="A dummy tool",
        func=dummy_func,
        args_schema=DummyArgs,
    )

    test_registry = ToolRegistry()
    test_registry.register(spec)

    assert test_registry.count() == 1
    assert "dummy_tool" in test_registry.list_names()

    tool = test_registry.get("dummy_tool")
    assert tool is not None
    assert isinstance(tool, StructuredTool)


def test_tool_register_duplicate_raises():
    """Test registering duplicate tool raises ValueError."""
    from pydantic import BaseModel

    class DummyArgs(BaseModel):
        name: str

    def dummy_func(name: str) -> str:
        return f"Hello {name}"

    spec = ToolSpec(
        name="duplicate_tool",
        category=ToolCategory.interaction,
        description="A tool",
        func=dummy_func,
        args_schema=DummyArgs,
    )

    test_registry = ToolRegistry()
    test_registry.register(spec)

    with pytest.raises(ValueError, match="Tool already registered"):
        test_registry.register(spec)


def test_register_all_tools():
    """Test registering all browser automation tools."""
    # Clear global registry first
    global registry
    registry._tools.clear()

    result = register_all_tools()

    assert isinstance(result, ToolRegistry)
    assert result.count() == 22  # 22 tools total

    # Check categories
    by_cat = result.list_by_category()
    assert "navigation" in by_cat
    assert "interaction" in by_cat
    assert "forms" in by_cat
    assert "utilities" in by_cat
    assert "browser" in by_cat

    # Verify counts
    assert len(by_cat["navigation"]) == 4
    assert len(by_cat["interaction"]) == 5
    assert len(by_cat["forms"]) == 3
    assert len(by_cat["utilities"]) == 5
    assert len(by_cat["browser"]) == 5


def test_registry_get_by_category():
    """Test getting tools by category."""
    # Clear and register
    registry._tools.clear()
    register_all_tools()

    nav_tools = registry.get_by_category(ToolCategory.navigation)
    assert len(nav_tools) == 4

    interaction_tools = registry.get_by_category(ToolCategory.interaction)
    assert len(interaction_tools) == 5


def test_registry_summary():
    """Test registry summary output."""
    registry._tools.clear()
    register_all_tools()

    summary = registry.summary()
    assert "Tool Registry Summary" in summary
    assert "Total Tools: 22" in summary
    assert "Navigation" in summary  # Capitalized in summary
    assert "Interaction" in summary
    assert "browser_navigate" in summary


def test_agent_creation(monkeypatch):
    """Test agent initializes with all tools."""
    # Clear the global registry first
    from src.tools.registry import registry
    registry._tools.clear()

    # Mock the create_deep_agent to avoid requiring actual API key
    async def mock_invoke(*args, **kwargs):
        return {"messages": [{"content": "mocked"}]}

    async def mock_stream(*args, **kwargs):
        yield {"messages": [{"content": "mocked"}]}

    async def mock_get_state(*args, **kwargs):
        return {}

    async def mock_update_state(*args, **kwargs):
        pass

    def mock_create_deep_agent(*args, **kwargs):
        class MockAgent:
            invoke = mock_invoke
            ainvoke = mock_invoke
            stream = mock_stream
            astream = mock_stream
            get_state = mock_get_state
            aget_state = mock_get_state
            update_state = mock_update_state
            aupdate_state = mock_update_state

        return MockAgent()

    # Patch deepagents module where it's imported
    monkeypatch.setattr(
        "deepagents.create_deep_agent",
        mock_create_deep_agent,
    )

    agent = FacebookSurferAgent(model="gpt-4o")
    assert agent.tool_count == 22
    assert agent.agent is not None
    assert agent.model == "gpt-4o"
    assert agent.enable_memory is True
    assert agent.enable_hitl is True


def test_agent_system_prompt():
    """Test system prompt is set correctly."""
    from src.agents.facebook_surfer import FacebookSurferAgent

    # Check the prompt is defined by importing and checking the class
    prompt = FacebookSurferAgent._build_system_prompt(None)
    assert "Facebook" in prompt
    assert "ReAct" in prompt
    assert "Thought → Action → Observation" in prompt


def test_agent_get_tool_summary(monkeypatch):
    """Test getting tool summary from agent."""
    # Clear the global registry first
    from src.tools.registry import registry
    registry._tools.clear()

    async def mock_invoke(*args, **kwargs):
        return {"messages": [{"content": "mocked"}]}

    async def mock_stream(*args, **kwargs):
        yield {"messages": [{"content": "mocked"}]}

    async def mock_get_state(*args, **kwargs):
        return {}

    async def mock_update_state(*args, **kwargs):
        pass

    def mock_create_deep_agent(*args, **kwargs):
        class MockAgent:
            invoke = mock_invoke
            ainvoke = mock_invoke
            stream = mock_stream
            astream = mock_stream
            get_state = mock_get_state
            aget_state = mock_get_state
            update_state = mock_update_state
            aupdate_state = mock_update_state

        return MockAgent()

    monkeypatch.setattr(
        "deepagents.create_deep_agent",
        mock_create_deep_agent,
    )

    agent = FacebookSurferAgent(model="gpt-4o")
    summary = agent.get_tool_summary()
    assert "Tool Registry Summary" in summary
    assert "22" in summary


def test_base_context_helpers():
    """Test base.py context helpers."""
    from src.tools.base import (
        set_current_page,
        get_current_page,
        set_current_context,
        get_current_context,
    )
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        # Test page context
        set_current_page(page)
        assert get_current_page() is page

        # Test context
        set_current_context(context)
        assert get_current_context() is context

        browser.close()


def test_context_helpers_import():
    """Test context helpers are properly exported."""
    from src.tools import (
        set_current_page,
        get_current_page,
        set_current_context,
        get_current_context,
    )

    assert callable(set_current_page)
    assert callable(get_current_page)
    assert callable(set_current_context)
    assert callable(get_current_context)


def test_async_tools_properly_registered():
    """Regression test: async tools must use coroutine param not func.

    This test ensures that all async browser tools are properly registered
    using the coroutine parameter to avoid RuntimeWarning about unawaited coroutines.
    """
    import inspect
    from src.tools.registry import registry, register_all_tools

    # Clear and register all tools
    registry._tools.clear()
    register_all_tools()

    # Check all tools have coroutine set if they're async
    tools = registry.get_all()
    assert len(tools) == 22, f"Expected 22 tools, got {len(tools)}"

    for tool in tools:
        # All browser tools should be async
        assert tool.coroutine is not None, f"{tool.name}: coroutine should be set"
        assert inspect.iscoroutinefunction(tool.coroutine), \
            f"{tool.name}: coroutine should be an async function"

        # Verify the tool has async execution methods
        assert hasattr(tool, 'ainvoke'), f"{tool.name}: missing ainvoke method"
        assert hasattr(tool, 'arun'), f"{tool.name}: missing arun method"
        assert hasattr(tool, 'astream'), f"{tool.name}: missing astream method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
