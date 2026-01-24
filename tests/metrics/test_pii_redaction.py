"""Unit tests for PII redaction functionality.

Tests that all PII patterns are correctly detected and redacted
from trajectory data.
"""

import pytest

from src.metrics.pii_redaction import (
    PII_PATTERNS,
    PII_REPLACEMENTS,
    redact_string,
    redact_trajectory,
)


class TestRedactString:
    """Tests for redacting PII from simple strings."""

    def test_redact_email(self):
        """Test email redaction."""
        input_text = "Contact me at user@example.com for details"
        result = redact_string(input_text)
        assert "[REDACTED_EMAIL]" in result
        assert "user@example.com" not in result
        assert "Contact me at" in result  # Preserve non-PII text

    def test_redact_multiple_emails(self):
        """Test redacting multiple emails in one string."""
        input_text = "Email admin@test.com or user@example.com"
        result = redact_string(input_text)
        assert result.count("[REDACTED_EMAIL]") == 2

    def test_redact_phone(self):
        """Test phone number redaction."""
        # US format with dashes
        result = redact_string("Call me at 555-123-4567")
        assert "[REDACTED_PHONE]" in result
        assert "555-123-4567" not in result

        # US format with dots
        result = redact_string("Call 555.123.4567")
        assert "[REDACTED_PHONE]" in result

        # Plain format
        result = redact_string("Call 5551234567")
        assert "[REDACTED_PHONE]" in result

    def test_redact_ssn(self):
        """Test SSN redaction."""
        input_text = "My SSN is 123-45-6789"
        result = redact_string(input_text)
        assert "[REDACTED_SSN]" in result
        assert "123-45-6789" not in result

    def test_redact_credit_card(self):
        """Test credit card redaction."""
        # With dashes
        result = redact_string("Card: 4111-1111-1111-1111")
        assert "[REDACTED_CC]" in result
        assert "4111-1111-1111-1111" not in result

        # With spaces
        result = redact_string("Card: 4111 1111 1111 1111")
        assert "[REDACTED_CC]" in result

        # Plain format
        result = redact_string("Card: 4111111111111111")
        assert "[REDACTED_CC]" in result

    def test_redact_api_key(self):
        """Test API key redaction (32+ char alphanumeric)."""
        # Exactly 32 chars
        result = redact_string("Key: abc123def456789abc123def456789xyz")
        assert "[REDACTED_KEY]" in result

        # More than 32 chars
        result = redact_string("Token: abc123def456789abc123def456789xyz1234567890")
        assert "[REDACTED_KEY]" in result

        # Less than 32 chars should NOT be redacted
        result = redact_string("Short: abc123def456789")
        assert "[REDACTED_KEY]" not in result

    def test_no_false_positives(self):
        """Test that safe data is not redacted."""
        safe_text = "Hello world, testing 123, normal text"
        result = redact_string(safe_text)
        assert "[REDACTED_" not in result

    def test_case_insensitive(self):
        """Test that patterns are case-insensitive."""
        result = redact_string("Email: USER@EXAMPLE.COM")
        assert "[REDACTED_EMAIL]" in result


class TestRedactTrajectory:
    """Tests for redacting PII from trajectory data structures."""

    def test_redact_tool_input(self):
        """Test redaction in tool input field."""
        trajectory = {
            "tool_calls": [
                {
                    "tool": "type",
                    "input": "Send email to user@example.com",
                    "output": "Success",
                }
            ]
        }

        result = redact_trajectory(trajectory)

        # Original should be unchanged
        assert trajectory["tool_calls"][0]["input"] == "Send email to user@example.com"

        # Result should be redacted
        assert "[REDACTED_EMAIL]" in result["tool_calls"][0]["input"]
        assert "user@example.com" not in result["tool_calls"][0]["input"]

    def test_redact_tool_output(self):
        """Test redaction in tool output field."""
        trajectory = {
            "tool_calls": [
                {
                    "tool": "search",
                    "input": "Find contact",
                    "output": "Found: admin@test.com, 555-123-4567",
                }
            ]
        }

        result = redact_trajectory(trajectory)

        output = result["tool_calls"][0]["output"]
        assert "[REDACTED_EMAIL]" in output
        assert "[REDACTED_PHONE]" in output

    def test_redact_tool_error(self):
        """Test redaction in tool error field."""
        trajectory = {
            "tool_calls": [
                {
                    "tool": "login",
                    "input": "user",
                    "error": "Failed for user@bad.com",
                }
            ]
        }

        result = redact_trajectory(trajectory)
        assert "[REDACTED_EMAIL]" in result["tool_calls"][0]["error"]

    def test_redact_nested_dict(self):
        """Test redaction in nested dictionary structures."""
        trajectory = {
            "tool_calls": [
                {
                    "tool": "submit",
                    "input": {
                        "email": "user@example.com",
                        "phone": "555-123-4567",
                        "message": "Hello",
                    },
                }
            ]
        }

        result = redact_trajectory(trajectory)
        input_data = result["tool_calls"][0]["input"]

        assert "[REDACTED_EMAIL]" in str(input_data)
        assert "[REDACTED_PHONE]" in str(input_data)
        assert "Hello" in str(input_data)  # Non-PII preserved

    def test_redact_from_list(self):
        """Test redaction in list values."""
        trajectory = {
            "tool_calls": [
                {
                    "tool": "batch",
                    "input": ["user1@example.com", "user2@example.com"],
                }
            ]
        }

        result = redact_trajectory(trajectory)
        input_data = result["tool_calls"][0]["input"]

        # Both emails should be redacted
        assert str(input_data).count("[REDACTED_EMAIL]") == 2

    def test_multiple_tool_calls(self):
        """Test redaction across multiple tool calls."""
        trajectory = {
            "tool_calls": [
                {"tool": "type", "input": "email: user1@example.com"},
                {"tool": "click", "input": "button"},
                {"tool": "type", "input": "phone: 555-123-4567"},
            ]
        }

        result = redact_trajectory(trajectory)

        assert "[REDACTED_EMAIL]" in result["tool_calls"][0]["input"]
        assert "[REDACTED_PHONE]" in result["tool_calls"][2]["input"]
        # Middle tool call should be unchanged
        assert result["tool_calls"][1]["input"] == "button"

    def test_preserves_non_string_types(self):
        """Test that non-string types are preserved."""
        trajectory = {
            "tool_calls": [
                {
                    "tool": "test",
                    "input": "user@example.com",
                    "count": 42,
                    "flag": True,
                    "value": 3.14,
                }
            ]
        }

        result = redact_trajectory(trajectory)

        # String should be redacted
        assert "[REDACTED_EMAIL]" in result["tool_calls"][0]["input"]

        # Other types preserved
        assert result["tool_calls"][0]["count"] == 42
        assert result["tool_calls"][0]["flag"] is True
        assert result["tool_calls"][0]["value"] == 3.14

    def test_empty_trajectory(self):
        """Test redaction of empty trajectory."""
        trajectory = {"tool_calls": []}
        result = redact_trajectory(trajectory)
        assert result == {"tool_calls": []}

    def test_trajectory_without_tool_calls(self):
        """Test trajectory without tool_calls key."""
        trajectory = {"some_key": "some_value"}
        result = redact_trajectory(trajectory)
        assert result == trajectory


class TestPIIPatterns:
    """Tests for PII pattern definitions."""

    def test_all_patterns_have_replacements(self):
        """Test that every pattern has a corresponding replacement."""
        assert set(PII_PATTERNS.keys()) == set(PII_REPLACEMENTS.keys())

    def test_replacements_are_unique(self):
        """Test that all replacements are unique."""
        replacements = list(PII_REPLACEMENTS.values())
        assert len(replacements) == len(set(replacements))

    def test_patterns_are_valid_regex(self):
        """Test that all patterns compile as valid regex."""
        import re

        for pattern_name, pattern in PII_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Pattern '{pattern_name}' is invalid regex: {e}")
