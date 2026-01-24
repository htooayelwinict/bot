"""Shared utilities for agent modules.

Provides common configuration and parsing functions used across
planning and reflection agents.
"""

import json
import os
import re
from typing import Any

from langchain_openai import ChatOpenAI


def create_openrouter_llm(
    model: str,
    temperature: float = 0.0,
    api_key: str | None = None,
    app_title: str = "FacebookSurferAgent",
    extra_body: dict | None = None,
) -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for OpenRouter.

    Args:
        model: Model name (with or without 'openrouter/' prefix).
        temperature: Sampling temperature (default: 0.0).
        api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
        app_title: Application title for OpenRouter headers.
        extra_body: Optional extra body parameters (e.g., reasoning config).

    Returns:
        Configured ChatOpenAI instance for OpenRouter.
    """
    # Strip openrouter/ prefix if present
    model_name = model.replace("openrouter/", "")

    config = {
        "model": model_name,
        "temperature": temperature,
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": api_key or os.getenv("OPENROUTER_API_KEY"),
        "default_headers": {
            "HTTP-Referer": "https://github.com/htooayelwinict/bot",
            "X-Title": app_title,
        },
    }

    if extra_body:
        config["extra_body"] = extra_body

    return ChatOpenAI(**config)


def parse_json_with_fallback(
    text: str,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks.

    Attempts direct JSON parsing first, then falls back to extracting
    JSON from markdown code blocks (```json ... ```).

    Args:
        text: Raw text that may contain JSON.
        fallback: Default dict to return on parse failure.
            If None, returns {"raw_text": text}.

    Returns:
        Parsed JSON dict, or fallback on failure.
    """
    # First try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract from code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Return fallback
    if fallback is not None:
        return fallback
    return {"raw_text": text}
