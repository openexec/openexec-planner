"""Tests for intent parser."""

import pytest
from openexec_planner import IntentParser


class TestIntentParser:
    """Tests for IntentParser."""

    def test_parse_extracts_title(self, tmp_path):
        """Test that parser extracts document title."""
        doc = tmp_path / "intent.md"
        doc.write_text("# My Project\n\nSome content")

        parser = IntentParser()
        result = parser.parse(doc)

        assert result["title"] == "My Project"

    def test_parse_returns_raw_content(self, tmp_path):
        """Test that parser includes raw content."""
        content = "# Test\n\nContent here"
        doc = tmp_path / "intent.md"
        doc.write_text(content)

        parser = IntentParser()
        result = parser.parse(doc)

        assert result["raw_content"] == content
