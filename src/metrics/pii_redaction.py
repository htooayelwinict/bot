"""PII redaction for trajectory data.

Removes personally identifiable information from trajectory data before
storage in the vector database to protect user privacy.
"""

import json
import re
from typing import Any

# PII patterns and replacements
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "api_key": r"\b[A-Za-z0-9]{32,}\b",
}

PII_REPLACEMENTS = {
    "email": "[REDACTED_EMAIL]",
    "phone": "[REDACTED_PHONE]",
    "ssn": "[REDACTED_SSN]",
    "credit_card": "[REDACTED_CC]",
    "api_key": "[REDACTED_KEY]",
}


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for objects not serializable by default.

    Handles LangChain message objects (ToolMessage, AIMessage, etc.)
    and other non-serializable types.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable representation
    """
    # Handle LangChain message objects
    if hasattr(obj, "content"):
        return str(obj.content)

    # Handle objects with dict() method
    if hasattr(obj, "dict"):
        return obj.dict()

    # Handle objects with __dict__
    if hasattr(obj, "__dict__"):
        return str(obj)

    # Fallback to string representation
    return str(obj)

def redact_trajectory(trajectory: dict[str, Any]) -> dict[str, Any]:
    """Remove PII from trajectory before storage.

    Creates a deep copy of the trajectory and applies all PII patterns
    to string values in tool call inputs and outputs.

    Args:
        trajectory: Raw trajectory data with potential PII

    Returns:
        Redacted trajectory copy with PII replaced by placeholders

    Examples:
        >>> raw = {
        ...     "tool_calls": [
        ...         {"tool": "type", "input": "Email: user@example.com"}
        ...     ]
        ... }
        >>> clean = redact_trajectory(raw)
        >>> "[REDACTED_EMAIL]" in str(clean)
        True
    """
    # Deep copy with custom serialization to handle LangChain objects
    trajectory_copy = json.loads(json.dumps(trajectory, default=_json_serializer))

    # Redact from tool_calls
    for tool_call in trajectory_copy.get("tool_calls", []):
        # Redact from input field
        if "input" in tool_call:
            input_value = tool_call["input"]
            tool_call["input"] = _redact_value(input_value)

        # Redact from output field
        if "output" in tool_call and tool_call["output"]:
            output_value = tool_call["output"]
            tool_call["output"] = _redact_value(output_value)

        # Redact from error field
        if "error" in tool_call and tool_call["error"]:
            error_value = tool_call["error"]
            tool_call["error"] = _redact_value(error_value)

    return trajectory_copy


def _redact_value(value: Any) -> Any:
    """Recursively redact PII from a value.

    Args:
        value: Any value (str, dict, list, or other)

    Returns:
        Redacted value with same structure
    """
    if isinstance(value, str):
        # Apply all PII patterns
        result = value
        for pattern_name, pattern in PII_PATTERNS.items():
            result = re.sub(
                pattern,
                PII_REPLACEMENTS[pattern_name],
                result,
                flags=re.IGNORECASE,
            )
        return result

    elif isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [_redact_value(item) for item in value]

    else:
        # Keep other types as-is
        return value


def redact_string(text: str) -> str:
    """Redact PII from a single string.

    Convenience function for redacting simple strings without
    the full trajectory structure.

    Args:
        text: String that may contain PII

    Returns:
        String with PII redacted

    Examples:
        >>> redact_string("Contact me at user@example.com or 555-123-4567")
        'Contact me at [REDACTED_EMAIL] or [REDACTED_PHONE]'
    """
    result = text
    for pattern_name, pattern in PII_PATTERNS.items():
        result = re.sub(
            pattern,
            PII_REPLACEMENTS[pattern_name],
            result,
            flags=re.IGNORECASE,
        )
    return result
