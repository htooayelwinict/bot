"""Web browsing automation agent using DeepAgents framework.

Integrates with Playwright browser automation tools to provide
autonomous web interaction capabilities with HITL support.
Skills middleware enables domain-specific guidance (e.g., Facebook automation).
"""

import os
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from src.tools.registry import ToolRegistry, register_all_tools


class FacebookSurferAgent:
    """Web browsing automation agent using DeepAgents framework.

    Provides autonomous web interaction with browser tools,
    memory persistence, and human-in-the-loop approval for sensitive actions.
    Skills loaded from filesystem provide domain-specific guidance.
    """

    def __init__(
        self,
        model: str = "openrouter/mistralai/devstral-2512:free",
        enable_memory: bool = True,
        enable_hitl: bool = False,  # Disabled by default until HITL handling is implemented
        temperature: float = 0.0,
        api_key: str | None = None,
    ):
        """Initialize the web browsing agent.

        Args:
            model: Model identifier (e.g., "openrouter/mistralai/devstral-2512:free")
                   Format: "openrouter/<model_name>" for OpenRouter models
            enable_memory: Enable in-memory store for context persistence
            enable_hitl: Enable human-in-the-loop for sensitive actions
            temperature: LLM temperature for response randomness
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        """
        self.model = model
        self.enable_memory = enable_memory
        self.enable_hitl = enable_hitl
        self.temperature = temperature
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        # Register all tools
        self.registry: ToolRegistry = register_all_tools()
        self.tools = self.registry.get_all()

        # Setup LangGraph components
        self.store = InMemoryStore() if enable_memory else None
        self.checkpointer = MemorySaver()

        # Build system prompt
        self.system_prompt = self._build_system_prompt()

        # Create DeepAgent
        self.agent = self._create_agent()

    def _build_system_prompt(self) -> str:
        """Build system prompt for web browsing automation."""
        return """You are an autonomous web browsing agent. Complete tasks fully - never fake or pretend.

## ⚠️ CRITICAL: REFS BECOME STALE
After ANY action (click, type, navigate), ALL refs are INVALID. You MUST:
1. Call `browser_get_snapshot()` to get NEW refs
2. Find your target element's NEW ref in the fresh snapshot
3. NEVER reuse a ref from a previous snapshot

Example of WRONG behavior:
```
browser_click(ref="e78")  # Opens dialog
browser_click(ref="e78")  # WRONG! e78 is now a different element!
```

## CORE RULES
1. NEVER say "done" until you VERIFY with a snapshot showing the expected result
2. Complete ALL dialog steps - selecting ≠ confirming (must click Done/Post/Submit)
3. Follow skill files EXACTLY when provided in context
4. Use `force=True` on all clicks (sites have invisible overlays)
5. ALWAYS get fresh snapshot after any UI change

## ARIA SNAPSHOT & REF SYSTEM
The `browser_get_snapshot()` tool returns a YAML accessibility tree:
```yaml
- navigation "Facebook":
  - link "Home" [ref=e0]
  - button "Search" [ref=e1]
- main:
  - button "What's on your mind?" [ref=e15]
  - textbox "Write something..." [ref=e16]
```

**Understanding the format:**
- Each line: `role "accessible name" [ref=eN]`
- Roles: button, link, textbox, checkbox, radio, heading, etc.
- Attributes in brackets: `[checked]`, `[disabled]`, `[level=1]`, `[pressed=true]`

## MANDATORY WORKFLOW (Observe → Think → Act → Verify)

**Step 1: OBSERVE** - Get FRESH snapshot
```python
browser_get_snapshot()
```

**Step 2: THINK** - You MUST explicitly list elements before clicking
```
# CURRENT SNAPSHOT shows:
# - button "Close composer dialog" [ref=e31] ← NOT what I want
# - button "Friends" [ref=e42] ← This is the privacy button!
# - button "Photo/video" [ref=e43] ← NOT what I need  
# - button "Post" [ref=e50] ← Submit button
#
# I need to change privacy. The privacy button shows "Friends" [ref=e42].
# I will click ref=e42.
```

**Step 3: ACT** - Click the ref you just identified
```python
browser_click(ref="e42", force=True)  # Ref from THIS snapshot
```

**Step 4: VERIFY & REFRESH** - Get NEW snapshot (old refs are now invalid!)
```python
browser_wait(time=1)
browser_get_snapshot()  # REQUIRED - all previous refs are stale
# Now find new refs in this fresh snapshot
```

## ELEMENT TARGETING (Priority Order)
1. **ref** (BEST) - Exact element from snapshot: `ref="e42"`
2. **selector** - Fallback patterns:
   - Role+name: `button=Post`, `radio=Only me`
   - Aria-label: `[aria-label="Close"]`
   - CSS: `div[contenteditable='true'][role='textbox']`

## KEY BEHAVIORS
- **Wait after actions**: `browser_wait(time=1-2)` for React/SPA re-renders
- **Refresh snapshot** after navigation, dialog open/close, or form submit
- **Refs expire** - always get fresh snapshot if targeting fails
- **Contenteditable**: Use `role=textbox` selector for rich text inputs
- **Multi-step dialogs**: select option → click confirm → verify

## COMMON MISTAKES TO AVOID
❌ **Reusing refs after actions** - After click/type, e78 may now be a completely different element!
❌ **Clicking "Close" accidentally** - Read the button name! "Close composer dialog" ≠ privacy button
❌ **Not listing elements** - You MUST write out what you see before clicking
❌ **Clicking without thinking** - "e78" clicked "Live video" when you wanted "What's on your mind"
❌ **Assuming task is done** - Always verify with final snapshot
❌ **Selecting but not confirming** - Must click "Done" after selecting privacy option

## SKILLS CONTEXT
When you receive a SKILL file, it provides:
- Tested selectors for that domain
- Complete workflows with exact steps
- Known UI quirks and workarounds
FOLLOW SKILL WORKFLOWS EXACTLY.
"""

    def _create_agent(self):
        """Create the DeepAgent instance with skills middleware."""
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI

        # Configure model
        model_config = None
        model_name = self.model
        temperature = self.temperature

        # Configure OpenRouter if using openrouter model
        if self.model.startswith("openrouter/"):
            # Extract actual model name (remove "openrouter/" prefix)
            model_name = self.model.replace("openrouter/", "")
            # Create ChatOpenAI with OpenRouter config
            model_config = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/facebook-automation-bot",
                    "X-Title": "Facebook Automation Bot",
                },
            )

        # Configure HITL interrupts for sensitive actions
        interrupt_on = {}
        if self.enable_hitl:
            interrupt_on = {
                "browser_type": {"allowed_decisions": ["approve", "edit", "reject"]},
                "browser_click": {"allowed_decisions": ["approve", "edit", "reject"]},
                "browser_submit_form": {"allowed_decisions": ["approve", "edit", "reject"]},
            }

        # Setup skills middleware - loads domain-specific guidance as context
        skills_backend = FilesystemBackend(root_dir=str(Path(__file__).parent.parent.parent / "skills"))
        skills_middleware = SkillsMiddleware(
            backend=skills_backend,
            sources=["/facebook-automation/"],  # Add more skill paths as needed
        )

        return create_deep_agent(
            model=model_config if model_config else model_name,
            tools=self.tools,
            store=self.store,
            checkpointer=self.checkpointer,
            system_prompt=self.system_prompt,
            interrupt_on=interrupt_on,
            middleware=[skills_middleware],
        )

    async def invoke(self, task: str, thread_id: str = "default") -> dict:
        """Execute a task with the agent.

        Args:
            task: Natural language task description
            thread_id: Conversation thread ID for memory

        Returns:
            Agent execution result with messages
        """
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return result

    async def stream(self, task: str, thread_id: str = "default"):
        """Stream agent execution for real-time feedback.

        Args:
            task: Natural language task description
            thread_id: Conversation thread ID for memory

        Yields:
            Agent state events during execution
        """
        config = {"configurable": {"thread_id": thread_id}}
        async for event in self.agent.astream(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
            stream_mode="values",
        ):
            yield event

    async def stream_events(self, task: str, thread_id: str = "default"):
        """Stream detailed agent events for debugging.

        Uses astream_events to show node execution, tool calls, and LLM activity.

        Args:
            task: Natural language task description
            thread_id: Conversation thread ID for memory

        Yields:
            Event dicts with event type, name, and data
        """
        config = {"configurable": {"thread_id": thread_id}}
        async for event in self.agent.astream_events(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
            version="v2",
        ):
            yield event

    async def get_state(self, thread_id: str = "default") -> dict:
        """Get current agent state.

        Args:
            thread_id: Conversation thread ID

        Returns:
            Current agent state
        """
        config = {"configurable": {"thread_id": thread_id}}
        return await self.agent.aget_state(config)

    async def update_state(self, thread_id: str = "default", **updates):
        """Update agent state (for HITL resume).

        Args:
            thread_id: Conversation thread ID
            **updates: State updates to apply
        """
        config = {"configurable": {"thread_id": thread_id}}
        await self.agent.aupdate_state(config, updates)

    def get_tool_summary(self) -> str:
        """Get summary of registered tools.

        Returns:
            Formatted tool summary
        """
        return self.registry.summary()

    @property
    def tool_count(self) -> int:
        """Get number of registered tools.

        Returns:
            Number of tools
        """
        return len(self.tools)
