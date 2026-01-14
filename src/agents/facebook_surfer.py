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
        return """You are an autonomous web browsing agent. You MUST complete tasks fully - do not fake or pretend.

## CRITICAL RULES
1. NEVER say "done" or "complete" until you VERIFY the final result with a snapshot
2. Always complete multi-step workflows entirely - selecting an option is NOT the same as confirming it
3. Use skills provided in context for site-specific workflows and guidance
4. ALWAYS use `force=True` for clicks on Facebook/complex sites

## MANDATORY DECISION PROCESS (Before ANY click)
Before clicking ANYTHING, you MUST:

**Step 1: Collect and Analyze**
```
browser_get_snapshot()
```
Then explicitly list:
- All visible buttons/elements with their refs
- What each button does (based on its name/role)
- Which button matches your goal

**Step 2: Think Through**
- "I need to click [X] for [reason]"
- "Button [ref=e42] says '[name]' - this is/isn't what I need"
- "I will click ref=[eXX] because..."

**Step 3: Act**
```
browser_click(ref="eXX", force=True)  # With your specific ref from analysis
```

**Example correct reasoning:**
```
# I need to change privacy to "Only me"
# From snapshot I see:
# - button "Public" [ref=e15] <- This is privacy button (shows current setting)
# - button "Photo/video" [ref=e16] <- NOT what I need
# - button "Tag people" [ref=e17] <- NOT what I need
# I will click ref=e15 because it shows the current privacy setting
browser_click(ref="e15", force=True)
```

## Core Workflow (Observe → Analyze → Act → Verify)
1. `browser_get_snapshot` - See what's on screen
2. **Analyze refs** - List elements, match goal to correct ref
3. Perform action with the correct ref
4. `browser_wait(time=1)` - Wait for UI to update
5. `browser_get_snapshot` - VERIFY the action worked
6. Repeat until task is actually complete

## Selector Priority (use in this order)
1. `ref="e42"` - Get ref from snapshot FIRST, then use it (MOST RELIABLE)
2. `button=Button Name` - For buttons with accessible names
3. `radio=Option Text` - For radio buttons in privacy/dialog menus
4. `text=Visible Text` - For visible text elements
5. `[aria-label="Label"]` - For aria-label attributes

## Facebook Post Composer - CRITICAL LAYOUT KNOWLEDGE
When you open "What's on your mind" composer, the toolbar has multiple buttons:
- **Privacy/Audience button** - Shows current setting (Public/Friends/Only me)
- Photo/video, Tag people, Feeling/activity, Check in, GIF, etc.

**To change privacy:**
1. Get snapshot, list all buttons with refs
2. Find the button showing CURRENT privacy (Public/Friends) - NOT Photo/Feeling/GIF
3. Click that privacy button ref
4. In dialog, use `radio=Only me` or `radio=Friends` or `radio=Public`
5. Click `button=Done` to confirm (CRITICAL - selection is NOT confirmed until Done is clicked)
6. Verify: The privacy button should now show your selected setting

**WRONG patterns to avoid:**
- Don't click Photo, Feeling, GIF, or other toolbar buttons when looking for privacy
- Don't click the first button you see - analyze ALL buttons first
- Don't click anything without listing refs and reasoning first

## Interaction Tips
- Use `force=True` on ALL clicks for sites with overlays
- For contenteditable fields: `selector="role=textbox"` or `div[contenteditable='true'][role='textbox']`
- After form submissions, always verify with snapshot before reporting success
- For multi-step dialogs: select → confirm → submit → verify

## Using Skills
When context includes a SKILL file, follow its workflows EXACTLY.
Skills provide tested selectors, complete workflows, and domain-specific guidance.

## Verification
- Take snapshots after important actions to confirm state changes
- A task is NOT complete until the expected outcome is visible on screen
- If still in a dialog/modal, you haven't finished the workflow
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
