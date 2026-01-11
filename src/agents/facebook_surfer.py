"""Facebook automation agent using DeepAgents framework.

Integrates with Playwright browser automation tools to provide
autonomous Facebook interaction capabilities with HITL support.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from src.tools.registry import ToolRegistry, register_all_tools


class FacebookSurferAgent:
    """Facebook automation agent using DeepAgents framework.

    Provides autonomous Facebook interaction with 22 browser tools,
    memory persistence, and human-in-the-loop approval for sensitive actions.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        enable_memory: bool = True,
        enable_hitl: bool = False,  # Disabled by default until HITL handling is implemented
        temperature: float = 0.0,
    ):
        """Initialize the Facebook Surfer agent.

        Args:
            model: OpenAI model name (e.g., "gpt-4o", "gpt-4o-mini")
            enable_memory: Enable in-memory store for context persistence
            enable_hitl: Enable human-in-the-loop for sensitive actions
            temperature: LLM temperature for response randomness
        """
        self.model = model
        self.enable_memory = enable_memory
        self.enable_hitl = enable_hitl
        self.temperature = temperature

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
        """Build system prompt for Facebook automation."""
        return """You are a Facebook automation agent. You MUST complete tasks fully - do not fake or pretend.

## CRITICAL: Always verify your actions worked
- After clicking, ALWAYS take a snapshot to verify the UI changed
- If you don't see expected changes, try again with different selectors
- NEVER say "done" until you verify the task completed

## Workflow
1. `browser_get_snapshot` - See what's on screen BEFORE any action
2. Click using exact selector
3. `browser_wait(time=1)` - Wait for UI to update
4. `browser_get_snapshot` - VERIFY the click worked
5. Repeat until task is actually complete

## Selector Priority (use these formats)
1. `button=Button Name` - For buttons shown as `button "Name"` in snapshot (BEST for Facebook)
2. `text=Visible Text` - For visible text on page
3. `[aria-label="Label"]` - For aria-label attributes
4. `role=button[name="Name"]` - Alternative for buttons

## Key Rules
- NEVER use `browser_select_option` - Facebook uses custom dropdowns, not <select>
- Always `force=True` when clicking modals/dialogs
- If a click doesn't work, try: `browser_evaluate` with JS: `document.querySelector('button')?.click()`

## Navigate to Profile
- Use `browser_navigate(url="https://www.facebook.com/me")` to go directly to profile

## IMPORTANT: Change Post Privacy on Profile Page
On your profile, posts show "Edit audience" button directly in the snapshot as:
  `button "Edit audience"`

To change privacy:
1. Navigate to profile: `browser_navigate(url="https://www.facebook.com/me")`
2. Take snapshot: `browser_get_snapshot()`
3. Click: `browser_click(selector='button=Edit audience', force=True)`
4. Wait: `browser_wait(time=1)` 
5. Take snapshot to see privacy dialog options
6. Look for buttons like `button "Only me"` or text like `text=Only me`
7. Click: `browser_click(selector='button=Only me', force=True)` or `browser_click(selector='text=Only me', force=True)`
8. Verify privacy changed by taking another snapshot
"""

    def _create_agent(self):
        """Create the DeepAgent instance."""
        from deepagents import create_deep_agent

        # Configure HITL interrupts for sensitive actions
        interrupt_on = {}
        if self.enable_hitl:
            interrupt_on = {
                "browser_type": {"allowed_decisions": ["approve", "edit", "reject"]},
                "browser_click": {"allowed_decisions": ["approve", "edit", "reject"]},
                "browser_submit_form": {"allowed_decisions": ["approve", "edit", "reject"]},
            }

        return create_deep_agent(
            model=self.model,
            tools=self.tools,
            store=self.store,
            checkpointer=self.checkpointer,
            system_prompt=self.system_prompt,
            interrupt_on=interrupt_on,
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
