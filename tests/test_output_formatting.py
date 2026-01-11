"""Regression test for content formatting in main.py output display.

This test ensures that agent message content is properly formatted
when displayed to the user, regardless of whether it's a string or
a list of content blocks.

Root cause: LangChain messages can have content that is:
- A plain string: "Hello world"
- A list of content blocks: [{"type": "text", "text": "Hello"}]

When content is a list, click.echo() was displaying it as Python repr
which showed as [] or [{...}] instead of the actual text content.
"""

import pytest
from unittest.mock import Mock
from langchain_core.messages import AIMessage, ToolMessage


def format_content_for_display(content):
    """Format message content for CLI display.

    This is the logic from main.py that needed to be fixed.
    """
    if isinstance(content, list):
        result = []
        for block in content:
            if isinstance(block, dict):
                result.append(block.get("text", str(block)))
            elif isinstance(block, str):
                result.append(block)
            else:
                result.append(str(block))
        return "\n".join(result)
    elif content:
        return str(content)
    return ""


class TestContentFormatting:
    """Test content formatting for different message types."""

    def test_plain_string_content(self):
        """Plain string content should be returned as-is."""
        content = "This is a plain string result"
        result = format_content_for_display(content)
        assert result == content

    def test_list_of_text_blocks(self):
        """List of content blocks should extract text field."""
        content = [
            {"type": "text", "text": "First line"},
            {"type": "text", "text": "Second line"},
        ]
        result = format_content_for_display(content)
        assert result == "First line\nSecond line"

    def test_mixed_content_blocks(self):
        """Mixed content blocks (strings and dicts) should both work."""
        content = [
            "Plain string",
            {"type": "text", "text": "Structured content"},
        ]
        result = format_content_for_display(content)
        assert result == "Plain string\nStructured content"

    def test_empty_list_content(self):
        """Empty list should return empty string."""
        content = []
        result = format_content_for_display(content)
        assert result == ""

    def test_tool_result_content(self):
        """Tool results (typically strings) should display correctly."""
        content = "Navigated to https://www.facebook.com/"
        result = format_content_for_display(content)
        assert result == content

    def test_structured_tool_result(self):
        """Tool results with structured data should be displayed."""
        content = """Page snapshot:
{
  "role": "document",
  "name": "Facebook"
}"""
        result = format_content_for_display(content)
        assert "Page snapshot:" in result
        assert "Facebook" in result

    def test_dict_without_text_field(self):
        """Dict blocks without 'text' field should use str()."""
        content = [{"type": "image", "url": "https://example.com/image.png"}]
        result = format_content_for_display(content)
        assert "https://example.com/image.png" in result


def test_message_content_types():
    """Test that actual LangChain messages have expected content types."""

    # AIMessage with plain string
    msg1 = AIMessage(content="Plain text response")
    assert isinstance(msg1.content, str)
    assert format_content_for_display(msg1.content) == "Plain text response"

    # AIMessage with content blocks (list)
    msg2 = AIMessage(content=[{"type": "text", "text": "Structured response"}])
    assert isinstance(msg2.content, list)
    assert format_content_for_display(msg2.content) == "Structured response"

    # ToolMessage (always string content)
    msg3 = ToolMessage(content="Tool execution result", tool_call_id="123")
    assert isinstance(msg3.content, str)
    assert format_content_for_display(msg3.content) == "Tool execution result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
