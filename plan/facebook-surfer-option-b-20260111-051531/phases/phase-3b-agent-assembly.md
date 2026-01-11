# Phase 3b: Agent Assembly

**Objective:** Create ToolRegistry, FacebookSurferAgent with create_deep_agent(), system prompt, CLI entry point

---

## Prerequisites

- Phase 1 complete (session + 5 core tools)
- Phase 2 complete (vision integration)
- Phase 3a complete (all 22 tools converted)

---

## Tasks

### 3b.1 Create Tool Registry

- [ ] Create `ToolRegistry` class
- [ ] Register all 22 tools by category
- [ ] Implement tool listing and filtering
- [ ] Add tool metadata (description, category)

**Files:**
- `src/tools/registry.py`

**Implementation:**
```python
# src/tools/registry.py
from typing import List, Dict, Any, Literal
from langchain.tools import StructuredTool

class ToolRegistry:
    """Registry for all browser automation tools."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        tool: StructuredTool,
        category: Literal["navigation", "interaction", "forms", "utilities", "browser", "vision"] = "general"
    ):
        """Register a tool with optional category."""
        self._tools[tool.name] = {
            "tool": tool,
            "category": category,
            "name": tool.name,
            "description": tool.description
        }

    def get(self, name: str) -> StructuredTool | None:
        """Get tool by name."""
        return self._tools.get(name, {}).get("tool")

    def get_all(self) -> List[StructuredTool]:
        """Get all registered tools."""
        return [item["tool"] for item in self._tools.values()]

    def get_by_category(
        self,
        category: Literal["navigation", "interaction", "forms", "utilities", "browser", "vision"]
    ) -> List[StructuredTool]:
        """Get tools by category."""
        return [
            item["tool"] for item in self._tools.values()
            if item.get("category") == category
        ]

    def list_names(self) -> List[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def list_by_category(self) -> Dict[str, List[str]]:
        """List tool names grouped by category."""
        result: Dict[str, List[str]] = {}
        for name, info in self._tools.items():
            cat = info.get("category", "general")
            if cat not in result:
                result[cat] = []
            result[cat].append(name)
        return result

    def count(self) -> int:
        """Count total tools."""
        return len(self._tools)

    def summary(self) -> str:
        """Get registry summary."""
        lines = ["Tool Registry Summary:", f"Total Tools: {self.count()}"]
        for cat, names in self.list_by_category().items():
            lines.append(f"\n{cat.capitalize()} ({len(names)}):")
            for name in names:
                lines.append(f"  - {name}")
        return "\n".join(lines)

# Global registry instance
registry = ToolRegistry()

def register_all_tools():
    """Register all 22 tools + 1 vision tool."""
    # Import all tools (lazy loading)
    from src.tools.navigation import (
        browser_navigate, browser_navigate_back,
        browser_screenshot, browser_get_page_info
    )
    from src.tools.interaction import (
        browser_click, browser_type, browser_select_option,
        browser_hover, browser_press_key
    )
    from src.tools.forms import (
        browser_fill_form, browser_get_form_data, browser_submit_form
    )
    from src.tools.utilities import (
        browser_wait, browser_evaluate, browser_get_snapshot,
        browser_get_network_requests, browser_get_console_messages
    )
    from src.tools.browser import (
        browser_tabs, browser_resize, browser_handle_dialog,
        browser_reload, browser_close
    )
    from src.tools.vision import vision_analyze_ui

    # Navigation (4 tools)
    registry.register(browser_navigate, "navigation")
    registry.register(browser_navigate_back, "navigation")
    registry.register(browser_screenshot, "navigation")
    registry.register(browser_get_page_info, "navigation")

    # Interaction (5 tools)
    registry.register(browser_click, "interaction")
    registry.register(browser_type, "interaction")
    registry.register(browser_select_option, "interaction")
    registry.register(browser_hover, "interaction")
    registry.register(browser_press_key, "interaction")

    # Forms (3 tools)
    registry.register(browser_fill_form, "forms")
    registry.register(browser_get_form_data, "forms")
    registry.register(browser_submit_form, "forms")

    # Utilities (5 tools)
    registry.register(browser_wait, "utilities")
    registry.register(browser_evaluate, "utilities")
    registry.register(browser_get_snapshot, "utilities")
    registry.register(browser_get_network_requests, "utilities")
    registry.register(browser_get_console_messages, "utilities")

    # Browser (5 tools)
    registry.register(browser_tabs, "browser")
    registry.register(browser_resize, "browser")
    registry.register(browser_handle_dialog, "browser")
    registry.register(browser_reload, "browser")
    registry.register(browser_close, "browser")

    # Vision (1 tool)
    registry.register(vision_analyze_ui, "vision")

    return registry
```

### 3b.2 Create DeepAgent

- [ ] Create `FacebookSurferAgent` class
- [ ] Implement `create_deep_agent()` call
- [ ] Add system prompt for Facebook behavior
- [ ] Configure checkpointer and store
- [ ] Add HITL interrupt configuration

**Files:**
- `src/agents/__init__.py`
- `src/agents/facebook_surfer.py`

**Implementation:**
```python
# src/agents/__init__.py
from .facebook_surfer import FacebookSurferAgent

__all__ = ["FacebookSurferAgent"]

# src/agents/facebook_surfer.py
from typing import Optional
from deepagents import create_deep_agent
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from src.tools.registry import registry, register_all_tools

class FacebookSurferAgent:
    """Facebook automation agent using DeepAgents framework."""

    def __init__(
        self,
        model: str = "gpt-4o",
        enable_memory: bool = True,
        enable_hitl: bool = True,
        temperature: float = 0.0
    ):
        self.model = model
        self.enable_memory = enable_memory
        self.enable_hitl = enable_hitl
        self.temperature = temperature

        # Register all tools
        register_all_tools()
        self.tools = registry.get_all()

        # Setup components (DeepAgents handles model directly)
        self.store = InMemoryStore() if enable_memory else None
        self.checkpointer = MemorySaver()

        # System prompt
        self.system_prompt = self._build_system_prompt()

        # Create agent
        self.agent = self._create_agent()

    def _build_system_prompt(self) -> str:
        """Build system prompt for Facebook automation with ReAct workflow."""
        return """You are a Facebook automation agent operating in a browser environment with 23 tools spanning navigation, interaction, forms, utilities, browser, and vision. Your primary objective is to complete tasks reliably while minimizing account risk and unintended actions.

## Core Reasoning Style (ReAct)
Use a **Thought → Action → Observation** loop for every step.
- **Thought:** Summarize intent, choose the best tool and selector strategy, and note any risk.
- **Action:** Call exactly one tool per step unless a tool explicitly supports multiple actions.
- **Observation:** Read the tool output/DOM/vision result and decide the next step.

Never skip the loop. If a step fails, diagnose and retry with an adjusted strategy.

## Selector vs Vision Policy
1. **Default to CSS selectors** for speed and determinism.
2. **Fallback to vision** when:
   - Selectors are unstable or change between loads.
   - Elements are rendered dynamically without stable IDs/classes.
   - You detect a blocked click, overlay, or mismatched element.
3. **Vision-first** only when the task is inherently visual (e.g., interpreting images, buttons with no text).
4. When vision succeeds, **capture a stable selector** if possible for future steps.

## Memory Workflow (ChromaDB - Phase 4)
Use memory to recall and persist action sequences.
1. **Before acting**, query memory with a concise key: `"facebook:<task_name>:<page_or_flow>"`.
2. If a matching sequence exists and is recent/stable:
   - Follow it, but validate each step with observations.
3. If no match or a sequence fails:
   - Proceed with fresh reasoning.
   - After successful completion, **save the sequence** with:
     - Page context, selectors, fallbacks, and any vision cues.
     - A short success summary and timestamp.
4. Always update memory when you discover a more stable selector or safer flow.

## Best Practices for Facebook Interaction
- Avoid rapid-fire actions; pace interactions and wait for DOM stability.
- Prefer explicit navigation and avoid opening new tabs unless required.
- Use search and filters over infinite scrolling when possible.
- Respect privacy settings and avoid risky actions (spamming, mass requests).
- Confirm visible UI state before submitting forms or sending messages.
- Be cautious with popups/modals; close or handle them explicitly.

## Tool Usage Patterns
You have 23 tools grouped as: navigation, interaction, forms, utilities, browser, vision.

**General rules:**
- Use one tool per step.
- Verify the page state after each action.
- If a tool fails, switch strategies (selector → vision or vice versa).

**Navigation tools:** Use for URL changes, back/forward, and waiting for load.
**Interaction tools:** Use for clicking, hovering, and scrolling. Confirm target is visible/enabled before clicking.
**Form tools:** Use for typing, clearing, selecting, and submitting. Validate inputs after entry.
**Utility tools:** Use for waits, element checks, and DOM queries. Prefer explicit waits on specific elements.
**Browser tools:** Use for tab management, viewport, and screenshots. Avoid extra tabs unless requested.
**Vision tools:** Use only when selectors fail or the UI is purely visual. Cross-check with DOM after vision actions if possible.

## Safety and Robustness
- If uncertain, take a screenshot and re-evaluate.
- Never submit or send without verifying the content.
- Handle unexpected dialogs or blockers before proceeding.

## Facebook-Specific Patterns
- Common selectors: `[aria-label*="..."]`, `[data-testid="..."]`, `[role="button"]`
- Wait for modals and dialogs to appear before interacting
- Check for popup dismissals (X buttons, "Not Now" links)
- Handle 2FA via HITL if needed
- Forms may have hidden fields - use browser_get_form_data first

## Output Expectations
- Always follow the Thought → Action → Observation loop.
- Be concise and deterministic.
- Use memory to improve stability over time.
"""

    def _create_agent(self):
        """Create the DeepAgent instance."""
        return create_deep_agent(
            model=self.model,  # e.g., "gpt-4o" or "openai:gpt-4o"
            tools=self.tools,
            store=self.store,
            checkpointer=self.checkpointer,
            system_prompt=self.system_prompt,
            interrupt_on={} if not self.enable_hitl else {
                "human_login": True  # Requires approval: approve, edit, reject
            }
        )

    def invoke(self, task: str, thread_id: str = "default") -> dict:
        """Execute a task with the agent."""
        config = {"configurable": {"thread_id": thread_id}}
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config
        )
        return result

    def stream(self, task: str, thread_id: str = "default"):
        """Stream agent execution for real-time feedback."""
        config = {"configurable": {"thread_id": thread_id}}
        for event in self.agent.stream(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
            stream_mode="values"  # Returns complete state chunks
        ):
            yield event

    def get_state(self, thread_id: str = "default") -> dict:
        """Get current agent state."""
        config = {"configurable": {"thread_id": thread_id}}
        return self.agent.get_state(config)

    def update_state(self, thread_id: str = "default", **updates):
        """Update agent state (for HITL resume)."""
        config = {"configurable": {"thread_id": thread_id}}
        self.agent.update_state(config, updates)

    def get_tool_summary(self) -> str:
        """Get summary of registered tools."""
        return registry.summary()

    @property
    def tool_count(self) -> int:
        """Get number of registered tools."""
        return len(self.tools)
```

### 3b.3 Create CLI Entry Point

- [ ] Create `src/main.py` as CLI entry point
- [ ] Add command-line argument parsing
- [ ] Implement session initialization
- [ ] Add interactive mode
- [ ] Add streaming mode support

**Files:**
- `src/main.py`

**Implementation:**
```python
# src/main.py
import argparse
import sys
from src.session.playwright_session import PlaywrightSession
from src.agents.facebook_surfer import FacebookSurferAgent
from src.tools.base import set_current_page

def print_banner():
    """Print application banner."""
    print("=" * 60)
    print("  Facebook Surfer Agent - DeepAgents + Playwright")
    print("=" * 60)
    print()

def init_session(login: bool = False) -> PlaywrightSession:
    """Initialize or restore browser session."""
    session = PlaywrightSession()

    if login:
        print("Starting human-in-the-loop login flow...")
        print("You have 3 minutes to log in manually.")
        print()
        success = session.start_login()
        if not success:
            print("Login failed or timed out")
            sys.exit(1)
        print("Login successful! Session saved.")
    else:
        print("Restoring existing session...")
        success = session.restore_session()
        if not success:
            print("No valid session found.")
            print("Run with --login first to create a session.")
            sys.exit(1)
        print("Session restored!")

    # Set current page for tools
    set_current_page(session.get_page())
    return session

def run_single_task(agent: FacebookSurferAgent, task: str, stream: bool, thread_id: str):
    """Run a single task and exit."""
    print(f"\nExecuting task: {task}")
    print("-" * 60)

    if stream:
        for event in agent.stream(task, thread_id=thread_id):
            # Parse and display events (stream_mode="values" returns state chunks)
            if "messages" in event and event["messages"]:
                latest_msg = event["messages"][-1]
                if hasattr(latest_msg, "content"):
                    print(f"[Update] {latest_msg.content}")
                else:
                    print(f"[Update] {latest_msg}")
            if "__interrupt__" in event:
                print(f"[Interrupt] {event['__interrupt__']}")
                # Handle HITL here if needed
    else:
        result = agent.invoke(task, thread_id=thread_id)
        print(f"\nResult:")
        print(result)

    print("-" * 60)
    print("Task complete!")

def run_interactive(agent: FacebookSurferAgent, thread_id: str):
    """Run in interactive mode."""
    print("\nEntering interactive mode.")
    print("Commands: 'exit', 'quit', 'clear', 'state', 'tools'")
    print()

    while True:
        try:
            task = input("Task> ").strip()

            if not task:
                continue

            if task.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if task.lower() == "clear":
                print("\033c", end="")
                continue

            if task.lower() == "state":
                state = agent.get_state(thread_id)
                print(f"Current state: {state}")
                continue

            if task.lower() == "tools":
                print(agent.get_tool_summary())
                continue

            # Execute task
            result = agent.invoke(task, thread_id=thread_id)
            print(f"\nResult: {result}\n")

        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except Exception as e:
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Facebook Surfer Agent - Autonomous Facebook automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --login                    # Create new session
  python -m src.main "Post hello"               # Single task
  python -m src.main --stream "Search for X"    # Stream execution
  python -m src.main                            # Interactive mode
        """
    )

    parser.add_argument("task", nargs="?", help="Natural language task to execute")
    parser.add_argument("--login", action="store_true", help="Start HITL login flow")
    parser.add_argument("--stream", action="store_true", help="Stream execution in real-time")
    parser.add_argument("--thread", default="default", help="Conversation thread ID")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--no-banner", action="store_true", help="Skip banner display")

    args = parser.parse_args()

    # Print banner
    if not args.no_banner:
        print_banner()

    # Initialize session
    session = init_session(login=args.login)

    # Create agent
    print(f"\nInitializing agent with {args.model}...")
    agent = FacebookSurferAgent(model=args.model)
    print(f"Agent ready with {agent.tool_count} tools registered.")

    # Execute task or run interactively
    if args.task:
        run_single_task(agent, args.task, args.stream, args.thread)
    else:
        run_interactive(agent, args.thread)

    # Cleanup
    print("\nClosing session...")
    session.close()
    print("Done!")

if __name__ == "__main__":
    main()
```

### 3b.4 Update Base Tool Context

- [ ] Add `set_current_page()` to base.py
- [ ] Add `get_current_context()` helper
- [ ] Ensure thread-safe page access

**Files:**
- `src/tools/base.py`

**Changes:**
```python
# Add to src/tools/base.py
from contextvars import ContextVar
from playwright.sync_api import Page, BrowserContext

# Thread-safe context for current page
_current_page: ContextVar[Page] = ContextVar("current_page")
_current_context: ContextVar[BrowserContext] = ContextVar("current_context")

def set_current_page(page: Page):
    """Set the current page for tool execution."""
    _current_page.set(page)

def get_current_page() -> Page:
    """Get the current page for tool execution."""
    return _current_page.get()

def set_current_context(context: BrowserContext):
    """Set the current browser context."""
    _current_context.set(context)

def get_current_context() -> BrowserContext:
    """Get the current browser context."""
    return _current_context.get()
```

### 3b.5 Testing

- [ ] Test agent creation
- [ ] Test task execution
- [ ] Test tool selection
- [ ] Test streaming mode
- [ ] Test HITL interrupt
- [ ] Test CLI argument parsing

**Files:**
- `tests/test_facebook_surfer.py`

**Test Cases:**
```python
# tests/test_facebook_surfer.py
import pytest
from src.agents.facebook_surfer import FacebookSurferAgent
from src.tools.registry import registry

def test_agent_creation():
    """Test agent initializes with all tools."""
    agent = FacebookSurferAgent()
    assert agent.tool_count == 23  # 22 tools + vision
    assert agent.agent is not None
    assert "browser_navigate" in registry.list_names()

def test_tool_registry():
    """Test tool registry functionality."""
    from src.tools.registry import register_all_tools
    register_all_tools()

    assert registry.count() == 23

    nav_tools = registry.get_by_category("navigation")
    assert len(nav_tools) == 4

    summary = registry.summary()
    assert "Total Tools: 23" in summary

def test_system_prompt():
    """Test system prompt is set correctly."""
    agent = FacebookSurferAgent()
    assert agent.system_prompt is not None
    assert "Facebook" in agent.system_prompt
    assert "vision_analyze_ui" in agent.system_prompt

def test_invoke_simple_task():
    """Test agent executes simple task (mocked)."""
    # This would require mocking the session
    agent = FacebookSurferAgent()
    # result = agent.invoke("Get page info")
    # assert result is not None
    pass

def test_get_state():
    """Test getting agent state."""
    agent = FacebookSurferAgent()
    state = agent.get_state()
    assert state is not None

def test_update_state():
    """Test updating agent state."""
    agent = FacebookSurferAgent()
    # Should not raise
    agent.update_state(thread_id="test", test_key="test_value")
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/tools/registry.py` | Tool registry with categories |
| `src/agents/__init__.py` | Agents module |
| `src/agents/facebook_surfer.py` | DeepAgent implementation |
| `src/main.py` | CLI entry point |
| `tests/test_facebook_surfer.py` | Agent tests |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/tools/base.py` | Add set_current_page(), set_current_context() |
| `src/tools/__init__.py` | Export all tools (if not already) |
| `pyproject.toml` | Add console_scripts entry point (optional) |

---

## Verification

```bash
# 1. Verify all tools import
python -c "
from src.tools.registry import registry, register_all_tools
register_all_tools()
print(f'Registered {registry.count()} tools')
print(registry.summary())
"

# 2. Test agent creation
python -c "
from src.agents.facebook_surfer import FacebookSurferAgent
agent = FacebookSurferAgent()
print(f'Agent created with {agent.tool_count} tools')
print(f'Model: {agent.model}')
print(f'Memory enabled: {agent.enable_memory}')
print(f'HITL enabled: {agent.enable_hitl}')
"

# 3. Run agent tests
pytest tests/test_facebook_surfer.py -v

# 4. Test login flow (requires Facebook session)
python -m src.main --login

# 5. Test simple task
python -m src.main "Navigate to facebook.com and take a screenshot"

# 6. Test interactive mode
python -m src.main
# Then type: tools
# Then type: Navigate to facebook.com
# Then type: What's the current page title?
# Then type: exit

# 7. Test streaming
python -m src.main --stream "Navigate to facebook.com and get page info"

# 8. Test with different model
python -m src.main --model gpt-4o-mini "Take a screenshot"

# 9. Test custom thread
python -m src.main --thread test-thread-123 "Get page info"
```

**Expected Results:**
- All 23 tools registered (22 converted + 1 vision)
- Agent creates without errors
- System prompt contains Facebook-specific instructions
- Tasks execute successfully
- Tools selected correctly by LLM
- HITL login works
- Interactive mode responds to commands
- Streaming shows real-time events
- Custom thread IDs work

---

## Estimated Effort

**4-6 hours**

- Tool registry: 1 hour
- Agent creation: 2 hours
- CLI entry point: 1.5 hours
- Base context updates: 0.5 hours
- Testing: 1 hour

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DeepAgents API changes | Pin version in pyproject.toml, check docs |
| Tool registration errors | Test each tool individually first |
| Session context issues | Use ContextVar for thread-safety |
| Poor tool selection | Improve system prompt with examples |
| HITL interrupt fails | Test interrupt configuration carefully |

---

## Dependencies

- Phase 1: Foundation (required) - session management
- Phase 2: Vision Integration (required) - vision tool
- Phase 3a: Tool Conversion (required) - all 22 tools
- Phase 4: LOT Memory (optional) - can add memory integration later

---

## Exit Criteria

- [ ] ToolRegistry created with all 23 tools
- [ ] FacebookSurferAgent creates successfully
- [ ] System prompt includes Facebook-specific patterns
- [ ] CLI works with --login, --stream, --thread flags
- [ ] Interactive mode functional
- [ ] Tests pass (agent creation, registry, state)
- [ ] Can execute simple tasks (navigate, screenshot)
- [ ] HITL login flow works
- [ ] Documentation complete (README, usage examples)

---

## Next Steps

After Phase 3b complete:
1. Phase 4: Add LOT Memory with ChromaDB
2. Phase 5: Integration & Testing (E2E, Docker, docs)
