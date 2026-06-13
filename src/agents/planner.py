"""Planning agent for RAG-based workflow planning.

Retrieves similar historical workflows and crafts success plans
to guide the execution agent using DeepAgents framework with Grok reasoning model.
"""

import json
import logging
from typing import Any

import click
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from qdrant_client import AsyncQdrantClient

from src.agents.utils import create_openrouter_llm, parse_json_with_fallback
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
        model: str = "x-ai/grok-4.3",  # Reasoning model
        qdrant_client: AsyncQdrantClient | None = None,
        api_key: str | None = None,
    ):
        """Initialize the planning agent.

        Args:
            model: Model name for planning (default: x-ai/grok-4.3).
            qdrant_client: Optional Qdrant client for retrieval.
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
        """
        self.model = model
        self.qdrant_client = qdrant_client
        self.api_key = api_key  # create_openrouter_llm handles env fallback
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
2. Highlight parameter patterns from successful executions (especially refs and selectors)
3. Note any error handling approaches used
4. Provide specific, actionable steps

## Output Format

Always output your plan as a numbered list of clear, actionable steps.
Be concise and focus on proven patterns that worked.

## Important Guidelines

- Focus on the tool sequences and parameters that worked
- PRESERVE specific refs/selectors from successful workflows (e.g., ref="e42")
- Note any failed patterns to AVOID
- Keep steps actionable and specific
"""

    def _create_agent(self):
        """Create the DeepAgent instance for planning."""
        # Configure ChatOpenAI with OpenRouter and reasoning tokens
        model_config = create_openrouter_llm(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
            app_title="FacebookSurferPlanningAgent",
            extra_body={
                "reasoning": {
                    "effort": "medium",  # Allocate ~50% of tokens for reasoning
                }
            },
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

        # Retrieve similar workflows with quality filtering
        similar = await retrieve_similar_trajectories(
            task=task,
            top_k=top_k,
            min_score=0.4,  # Allow learning from lower-scored runs
            min_similarity=0.4,  # Match same workflow across different topics
            exclude_failed_patterns=True,  # P1 FIX: Deprioritize failed workflows
            client=self.qdrant_client,
        )

        # Show retrieved patterns (debug output)
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
    "working_selectors": {{
        "element_name": "selector or ref that worked"
    }},
    "avoid_patterns": ["patterns that failed"]
}}
"""

    def _parse_json_result(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown blocks."""
        return parse_json_with_fallback(
            text,
            fallback={
                "analysis": "Failed to parse structured plan",
                "suggested_plan": [line for line in text.split('\n') if line.strip()],
                "similar_patterns": [],
            },
        )

    def _format_workflows(self, workflows: list[dict[str, Any]]) -> str:
        """Format workflows for prompt injection with full tool parameters.

        CRITICAL: Preserves input parameters (selectors, refs, text) for LLM consumption.
        This enables the execution agent to reuse working selectors instead of trial-and-error.
        """
        formatted = []
        for i, w in enumerate(workflows, 1):
            task = w.get("task", "Unknown")
            score = w.get("score", 0.0)

            # Extract tool calls with FULL parameters (P0 FIX)
            tool_calls = w.get("tool_calls", [])

            # Extract working selectors from successful tool calls
            working_selectors = []
            detailed_steps = []

            for j, tc in enumerate(tool_calls[:20], 1):  # Limit to 20 most relevant
                # Handle case where tc might be a string instead of dict
                if isinstance(tc, str):
                    detailed_steps.append(f"{j}. {tc}")
                    continue
                if not isinstance(tc, dict):
                    detailed_steps.append(f"{j}. {str(tc)}")
                    continue

                tool_name = tc.get("tool", "unknown").replace("browser_", "")
                inputs = tc.get("input", {})
                success = tc.get("success", True)

                # Handle case where inputs is a string instead of dict
                if isinstance(inputs, str):
                    status_marker = "✓" if success else "✗"
                    detailed_steps.append(f"{j}. {status_marker} {tool_name}({inputs[:100]})")
                    continue
                if not isinstance(inputs, dict):
                    detailed_steps.append(f"{j}. {tool_name}()")
                    continue

                # Build detailed step with parameters
                if inputs:
                    # Extract key parameters for different tool types
                    param_parts = []

                    # Selector/ref (critical for click, type, etc.)
                    if "ref" in inputs:
                        param_parts.append(f'ref="{inputs["ref"]}"')
                        if success:
                            working_selectors.append({
                                "tool": tool_name,
                                "ref": inputs["ref"],
                                "element": inputs.get("element", "unknown")
                            })

                    # URL for navigation
                    if "url" in inputs:
                        param_parts.append(f'url="{inputs["url"]}"')

                    # Text content (truncate if long)
                    if "text" in inputs:
                        text_val = inputs.get("text", "")
                        text_preview = str(text_val)[:50] + "..." if len(str(text_val)) > 50 else str(text_val)
                        param_parts.append(f'text="{text_preview}"')

                    # Element description
                    if "element" in inputs:
                        param_parts.append(f'element="{inputs["element"]}"')

                    params_str = ", ".join(param_parts) if param_parts else "..."
                    status_marker = "✓" if success else "✗"
                    detailed_steps.append(f"{j}. {status_marker} {tool_name}({params_str})")
                else:
                    detailed_steps.append(f"{j}. {tool_name}()")

            # Format working selectors section
            selectors_section = ""
            if working_selectors:
                selectors_section = "\n🎯 WORKING SELECTORS (reuse these):\n"
                for sel in working_selectors[:10]:  # Top 10 selectors
                    selectors_section += f"  - {sel['tool']}: ref=\"{sel['ref']}\" ({sel['element']})\n"

            # Format reflection data with failed patterns
            reflection = w.get("reflection", {}) or {}
            critique = reflection.get("critique", "N/A")
            failed_patterns = reflection.get("failed_patterns", [])
            successful_patterns = reflection.get("successful_patterns", [])

            warnings = ""
            if failed_patterns:
                warnings = "\n⚠️ AVOID THESE FAILED PATTERNS:\n" + "\n".join([f"  - {p}" for p in failed_patterns[:5]])

            successes = ""
            if successful_patterns:
                successes = "\n✅ SUCCESSFUL PATTERNS:\n" + "\n".join([f"  - {p}" for p in successful_patterns[:5]])

            formatted.append(
                f"═══════════════════════════════════════════════════════\n"
                f"WORKFLOW #{i} (Score: {score:.2f})\n"
                f"═══════════════════════════════════════════════════════\n"
                f"Task: {task}\n"
                f"{selectors_section}"
                f"\n📋 DETAILED EXECUTION TRACE:\n" + "\n".join(detailed_steps) + "\n"
                f"\n📝 LESSONS LEARNED: {critique}{successes}{warnings}\n"
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
