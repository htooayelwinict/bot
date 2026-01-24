
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

Be SPECIFIC. Include actual refs/selectors that worked or failed.
Example: "browser_click(ref=e42) worked for privacy" is useful.
"Clicking worked" is NOT useful.
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
        """Format trajectory log for LLM analysis.
        
        CRITICAL FIX: Preserves full input parameters (especially selectors/refs)
        to enable accurate failure pattern identification.
        """
        formatted = []
        for i, event in enumerate(trajectory, 1):
            # Handle both "tool_start" (from callback) and "tool_call" (legacy)
            event_type = event.get("type", "")
            if event_type not in ["tool_start", "tool_call"]:
                continue

            status = event.get("status", "unknown")
            tool = event.get("tool", "unknown")
            success = event.get("success", status != "failed")

            # PRESERVE CRITICAL PARAMETERS (P1 FIX - no more 100 char truncation)
            args = event.get("input", {})
            
            # Handle case where args is a string instead of dict
            if isinstance(args, str):
                arg_summary = args[:500] + "..." if len(args) > 500 else args
            elif isinstance(args, dict):
                # Extract key parameters that matter for failure analysis
                key_params = {}
                
                # Always preserve: ref, element, url, text (critical for debugging)
                for key in ["ref", "element", "url", "selector"]:
                    if key in args:
                        key_params[key] = args[key]
                
                # Preserve text but truncate very long content
                if "text" in args:
                    text_val = args["text"]
                    key_params["text"] = text_val[:200] + "..." if len(str(text_val)) > 200 else text_val
                
                # For snapshots, just note they exist (don't dump the content)
                if tool in ["get_snapshot", "snapshot", "browser_snapshot"]:
                    arg_summary = "(page snapshot captured)"
                elif key_params:
                    # Format preserved parameters
                    arg_summary = ", ".join([f'{k}="{v}"' for k, v in key_params.items()])
                else:
                    # Fallback: show full args but with 500 char limit (was 100)
                    arg_summary = str(args)[:500] + "..." if len(str(args)) > 500 else str(args)
            else:
                # Fallback for other types
                arg_summary = str(args)[:500] + "..." if len(str(args)) > 500 else str(args)

            # Status markers for clear identification
            status_marker = "✓" if success else "✗ FAILED"
            error_info = ""
            if not success:
                error_output = event.get("output", event.get("error", ""))
                if error_output:
                    error_preview = str(error_output)[:150]
                    error_info = f" | Error: {error_preview}"

            formatted.append(f"{i}. [{status_marker}] {tool}({arg_summary}){error_info}")

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
