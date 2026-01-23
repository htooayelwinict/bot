"""Planning agent for RAG-based workflow planning.

Retrieves similar historical workflows and crafts success plans
to guide the execution agent using DeepAgents framework with Grok reasoning model.
"""

import os
import logging
import json
import re
from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from qdrant_client import AsyncQdrantClient

from src.storage.qdrant_client import QdrantManager
from src.storage.retrieval import retrieve_similar_trajectories

logger = logging.getLogger(__name__)


class PlanningAgent:
    """Retrieve similar workflows and craft success plans.

    Uses semantic search to find historically successful trajectories
    similar to the current task, then generates an execution plan
    using DeepAgents framework with Grok reasoning model.
    """

    def __init__(
        self,
        model: str = "x-ai/grok-4.1-fast",  # Fast reasoning model
        qdrant_client: AsyncQdrantClient | None = None,
        api_key: str | None = None,
    ):
        """Initialize the planning agent.

        Args:
            model: Model name for planning (default: x-ai/grok-4.1-fast).
            qdrant_client: Optional Qdrant client for retrieval.
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
        """
        self.model = model
        self.qdrant_client = qdrant_client
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.temperature = 0.0

        # Build system prompt
        self.system_prompt = self._build_system_prompt()

        # Create DeepAgent
        self.agent = self._create_agent()

    def _build_system_prompt(self) -> str:
        """Build system prompt for workflow planning."""
        return """You are a workflow planning expert. Your job is to analyze successful historical workflows and create step-by-step execution plans for new tasks.

## Your Role

When given historical successful workflows and a current task, you must:
1. Identify key tool call sequences that led to success
2. Highlight parameter patterns from successful executions
3. Note any error handling approaches used
4. Provide specific, actionable steps

## Output Format

Always output your plan as a numbered list of clear, actionable steps.
Be concise and focus on proven patterns that worked.

## Important Guidelines

- Focus on the tool sequences and parameters that worked
- Note any specific selectors or strategies used
- Highlight error handling patterns
- Keep steps actionable and specific
"""

    def _create_agent(self):
        """Create the DeepAgent instance for planning."""
        # Configure ChatOpenAI with OpenRouter and reasoning tokens
        model_config = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/htooayelwinict/bot",
                "X-Title": "FacebookSurferPlanningAgent",
            },
            # Enable reasoning tokens for Grok
            extra_body={
                "reasoning": {
                    "effort": "medium",  # Allocate ~50% of tokens for reasoning
                }
            }
        )

        # Create DeepAgent (no tools needed for planning)
        return create_deep_agent(
            model=model_config,
            tools=[],  # Planning doesn't need tools
            checkpointer=MemorySaver(),
            system_prompt=self.system_prompt,
        )

    async def craft_success_plan(
        self,
        task: str,
        top_k: int = 3,
    ) -> str:
        """Retrieve similar workflows and generate success plan.

        Args:
            task: The task description to plan for.
            top_k: Number of similar workflows to retrieve (default: 3).

        Returns:
            Generated success plan as a string, or a fallback message
            if no similar workflows are found (cold start).

        Examples:
            >>> planner = PlanningAgent()
            >>> plan = await planner.craft_success_plan("Post to Facebook group")
            >>> print(plan)
        """
        # Ensure Qdrant client initialized
        if not self.qdrant_client:
            self.qdrant_client = await QdrantManager.get_client()

        # Retrieve similar workflows
        similar = await retrieve_similar_trajectories(
            task=task,
            top_k=top_k,
            min_score=0.5,
            client=self.qdrant_client,
        )

        # Show retrieved patterns (debug output)
        import click
        if similar:
            click.secho(f"   📚 Found {len(similar)} similar pattern(s):", fg="cyan")
            for i, pattern in enumerate(similar, 1):
                score = pattern.get('score', 0)
                similarity = pattern.get('similarity', 0)
                orig_task = pattern.get('task', 'unknown')[:50]
                tool_count = len(pattern.get('tool_calls', []))
                click.echo(f"      {i}. Score: {score:.2f} | Sim: {similarity:.2f} | Tools: {tool_count}")
                click.echo(f"         Task: \"{orig_task}...\"")
        else:
            click.secho("   📚 No similar patterns found in RAG", fg="yellow", dim=True)

        # Cold start: no similar workflows
        if not similar:
            logger.info(f"No similar historical workflows found for task: {task[:50]}...")
            return "No similar historical workflows found. Proceed with standard execution based on best practices."

        # Format historical context
        historical_context = self._format_workflows(similar)

        # Build planning message
        planning_message = self._build_planning_message(task, historical_context)

        try:
            # Invoke DeepAgent with planning task
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": planning_message}]},
                config={"configurable": {"thread_id": "planning"}},
            )

            # Extract plan from result
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                plan_content = getattr(last_message, "content", None)
                if plan_content:
                    # Parse JSON plan
                    plan_data = self._parse_json_result(plan_content)
                    
                    # Convert to string for legacy compatibility (we'll update consumer later)
                    # OR return the raw dict if we update the consumer first
                    # For now, let's keep the return type as "string" but containing JSON,
                    # or better: update the return type hint to Any or dict.
                    # Given the plan says "Inject plan as JSON object", we should return dict.
                    
                    logger.info(f"Generated structured success plan for task: {task[:50]}...")
                    return json.dumps(plan_data, indent=2)

            # Fallback if content is empty or structure is unexpected
            logger.warning("Unexpected response structure from planning agent")
            return self._format_fallback_plan(similar)

        except Exception as e:
            logger.error(f"Failed to generate success plan: {e}")
            # Fallback to raw workflow data
            return self._format_fallback_plan(similar)

    def _build_planning_message(self, task: str, historical_context: str) -> str:
        """Build the planning message with historical context.

        Args:
            task: The current task to plan for.
            historical_context: Formatted similar workflows.

        Returns:
            Complete message string for the agent.
        """
        return f"""You are a senior AI agent planner. Your goal is to create a deterministic execution plan based on successful historical workflows.

CURRENT TASK: "{task}"

SIMILAR HISTORICAL WORKFLOWS (RAG Context):
{historical_context}

INSTRUCTIONS:
1. Analyze the historical workflows to identify the winning pattern.
2. Extract the key sequence of actions (navigate, click, type, etc).
3. Create a step-by-step plan for the agent.

OUTPUT FORMAT:
You MUST respond with a raw JSON object only. Do NOT use markdown code blocks.
Structure:
{{
    "analysis": "Specific analysis of what tools worked",
    "suggested_plan": [
        "1. Navigate to...",
        "2. Click on [element]...",
        "3. Type 'text' into..."
    ],
    "similar_patterns": [
        {{
            "task": "Original task",
            "score": 0.95,
            "key_actions": ["navigate -> click -> type"]
        }}
    ]
}}
"""

    def _parse_json_result(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown blocks."""
        try:
            # First try direct parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract from code block
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Use raw fallback if needed
            return {
                "analysis": "Failed to parse structured plan",
                "suggested_plan": [line for line in text.split('\n') if line.strip()],
                "similar_patterns": []
            }

    def _format_workflows(self, workflows: list[dict[str, Any]]) -> str:
        """Format workflows for prompt injection."""
        formatted = []
        for i, w in enumerate(workflows, 1):
            task = w.get("task", "Unknown")
            score = w.get("score", 0.0)
            
            # Create a simplified tool sequence string
            tool_calls = w.get("tool_calls", [])
            tools = [t.get("tool", "unknown").replace("browser_", "") for t in tool_calls]
            
            # Collapse repeated tools (e.g. wait, wait, wait -> wait)
            clean_tools = []
            if tools:
                clean_tools = [tools[0]]
                for t in tools[1:]:
                    if t != clean_tools[-1]:
                        clean_tools.append(t)
            
            sequence = " -> ".join(clean_tools[:15])  # Limit length
            if len(clean_tools) > 15:
                sequence += f" -> ... ({len(clean_tools)-15} more)"

            # Format reflection data
            reflection = w.get("reflection", {}) or {}
            critique = reflection.get("critique", "N/A")
            failed_patterns = reflection.get("failed_patterns", [])
            warnings = ""
            if failed_patterns:
                warnings = "\n⚠️ AVOID REPEATING THESE MISTAKES:\n" + "\n".join([f"- {p}" for p in failed_patterns])

            formatted.append(
                f"WORKFLOW #{i}\n"
                f"Task: {task}\n"
                f"Score: {score:.2f}\n"
                f"Tool Sequence: {sequence}\n"
                f"LESSONS LEARNED: {critique}{warnings}\n"
            )

        return "\n".join(formatted)

    def _format_fallback_plan(self, workflows: list[dict[str, Any]]) -> str:
        """Format a basic fallback plan from workflow data.

        Used when LLM plan generation fails.

        Args:
            workflows: List of workflow dicts.

        Returns:
            Simple formatted plan.
        """
        lines = ["Based on similar historical workflows:\n"]

        for i, w in enumerate(workflows, 1):
            lines.append(f"{i}. {w['task']}")
            lines.append(f"   Steps: {w.get('trajectory', 'N/A')}")
            lines.append(f"   Success score: {w['score']:.2f}\n")

        return "\n".join(lines)
