"""Tests for LLM story generator."""

import json
from unittest.mock import patch, MagicMock
import pytest
from openexec_orchestration.llm_generator import LLMStoryGenerator


class TestLLMStoryGenerator:
    """Tests for LLMStoryGenerator."""

    @patch("subprocess.Popen")
    def test_call_cli_claude(self, mock_popen):
        """Test calling Claude CLI."""
        # Mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Generated story content", None)
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        generator = LLMStoryGenerator(model="sonnet", use_api=False)
        output = generator._call_cli("Test prompt")

        assert output == "Generated story content"
        mock_popen.assert_called_once()
        args, _ = mock_popen.call_args
        assert args[0] == ["claude", "--print"]

    def test_clean_output(self):
        """Test stripping diagnostic lines from LLM output."""
        raw_output = """
YOLO mode is enabled
Loading extension: axon
--------
{
  "stories": []
}
tokens used: 500
"""
        generator = LLMStoryGenerator()
        cleaned = generator._clean_output(raw_output)
        
        expected = '{\n  "stories": []\n}'
        assert cleaned == expected

    def test_extract_json_from_response(self):
        """Test extracting JSON from conversational LLM response."""
        response = """
I have generated the stories for you:

```json
{
  "stories": [{"id": "US-001"}]
}
```

Let me know if you need anything else.
"""
        generator = LLMStoryGenerator()
        data = generator._extract_json_from_response(response)
        
        assert data["stories"][0]["id"] == "US-001"

    @patch.object(LLMStoryGenerator, "_call_llm")
    def test_generate_workflow(self, mock_call):
        """Test full generation workflow with mock LLM."""
        mock_response = json.dumps({
            "stories": [
                {"id": "US-001", "title": "Test", "tasks": []}
            ]
        })
        mock_call.return_value = mock_response

        generator = LLMStoryGenerator()
        # Intent content must be string, not path, to avoid parse errors in this test
        result = generator.generate("# My Project\n\n## Goals\n- Test goal")

        assert "stories" in result
        assert len(result["stories"]) >= 1
        # The first story from our mock response should be there
        assert result["stories"][0]["id"] == "US-001"
