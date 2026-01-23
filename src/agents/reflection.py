
import os
import logging
import json
import re
from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class ReflectionAgent:
    """Agent that analyzes execution trajectories to learn lessons."""

    def __init__(
        self,
        model: str = "openrouter/x-ai/grok-4.1-fast",
        temperature: float = 0.0,
        api_key: str | None = None,
    ):
        # Configure model manually to handle OpenRouter
        if model.startswith("openrouter/"):
            model_name = model.replace("openrouter/", "")
            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
                default_headers={
                    "HTTP-Referer": "https://github.com/htooayelwinict/bot",
                    "X-Title": "ReflectionAgent",
                },
            )
        else:
            llm = model

        self.agent = create_deep_agent(
            model=llm,
            system_prompt=self._build_system_prompt(),
            tools=[],  # No tools needed for pure analysis
        )

    def _build_system_prompt(self) -> str:
        return """You are a senior QA engineer and AI behavior analyst.
Your goal is to analyze agent execution logs to identify:
1. What went wrong (failures, timeouts, loops)
2. What went right (critical steps for success)
3. Inefficiencies (needless steps)

You must be critical and specific. "Tried X and failed" is better than "Failed."
"""

    async def analyze_trajectory(self, task: str, trajectory: list[dict], score: float) -> dict[str, Any]:
        """Analyze a trajectory and return a structured critique."""
        
        # Format trajectory for the LLM
        log_str = self._format_trajectory(trajectory)
        
        prompt = f"""ANALYZE THIS EXECUTION:

TASK: {task}
FINAL SCORE: {score:.2f}

TRAJECTORY LOG:
{log_str}

INSTRUCTIONS:
Analyze the log above. Identify patterns of failure and success.
Output a JSON object with this structure:
{{
    "critique": "Overall summary of performance",
    "successful_patterns": ["List of specific actions/selectors that worked"],
    "failed_patterns": ["List of actions/selectors that failed or caused loops"],
    "efficiency_warning": "Warning about wasteful steps (if any)"
}}

Do NOT output markdown. Output RAW JSON only.
"""

        try:
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": "reflection"}},
            )
            
            content = result["messages"][-1].content
            return self._parse_json(content)
            
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return {
                "critique": "Reflection failed",
                "successful_patterns": [],
                "failed_patterns": [],
                "efficiency_warning": None
            }

    def _format_trajectory(self, trajectory: list[dict]) -> str:
        """Compact log format for LLM analysis."""
        formatted = []
        for i, event in enumerate(trajectory, 1):
            # Handle both "tool_start" (from callback) and "tool_call" (legacy)
            event_type = event.get("type", "")
            if event_type not in ["tool_start", "tool_call"]:
                continue

            status = event.get("status", "unknown")
            tool = event.get("tool", "unknown")

            # Summarize arguments (avoid huge snapshots)
            args = event.get("input", {})
            arg_summary = str(args)[:100] + "..." if len(str(args)) > 100 else str(args)

            # Check for error output in the event if available
            error_info = ""
            if status == "failed":
                error_info = " [FAILED]"

            formatted.append(f"{i}. {tool}({arg_summary}){error_info}")

        return "\n".join(formatted)

    def _parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                return json.loads(match.group(1))
            return {
                "critique": text, 
                "successful_patterns": [], 
                "failed_patterns": []
            }
