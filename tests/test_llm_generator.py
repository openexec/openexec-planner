"""Tests for LLM story generator."""

import json
from unittest.mock import patch, MagicMock
import pytest
from openexec_planner.llm_generator import LLMStoryGenerator


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

    def test_parse_review_response_approved(self):
        """Test parsing an approved review response."""
        generator = LLMStoryGenerator()
        response = '{"approved": true, "assessment": "All good"}'
        result = generator._parse_review_response(response)
        assert result["approved"] is True
        assert result["assessment"] == "All good"

    def test_parse_review_response_invalid(self):
        """Test parsing an invalid review response falls back to rejection."""
        generator = LLMStoryGenerator()
        response = "Not JSON"
        result = generator._parse_review_response(response)
        assert result["approved"] is False
        assert "Failed to parse" in result["assessment"]

    @patch.object(LLMStoryGenerator, "_call_llm")
    def test_get_review(self, mock_call):
        """Test getting review from LLM."""
        mock_call.return_value = '{"approved": true}'
        generator = LLMStoryGenerator()
        result = generator._get_review([{"id": "US-001"}], "intent", "reviewer")
        assert result["approved"] is True
        mock_call.assert_called_once()

    @patch.object(LLMStoryGenerator, "_call_llm")
    def test_fix_stories(self, mock_call):
        """Test fixing stories based on feedback."""
        mock_call.return_value = '{"stories": [{"id": "US-001", "fixed": true}]}'
        generator = LLMStoryGenerator()
        result = generator._fix_stories([{"id": "US-001"}], "intent", {"approved": False})
        assert result[0]["fixed"] is True
        mock_call.assert_called_once()

    def test_detect_provider(self):
        """Test provider detection from model names."""
        generator = LLMStoryGenerator()
        assert generator._detect_provider("sonnet") == "anthropic"
        assert generator._detect_provider("gpt-5.3") == "openai"
        assert generator._detect_provider("gemini-3.1-pro-preview") == "google"
        assert generator._detect_provider("unknown") == "anthropic" # Default

    @patch("openexec_planner.llm_generator.LLMStoryGenerator._get_review")
    @patch("openexec_planner.llm_generator.LLMStoryGenerator._fix_stories")
    def test_review_loop_approval(self, mock_fix, mock_get_review):
        """Test the review loop with immediate approval."""
        generator = LLMStoryGenerator()
        mock_get_review.return_value = {"approved": True, "assessment": "Good"}
        
        initial_data = {"stories": [{"id": "US-001"}]}
        result = generator.review(initial_data, "intent", "reviewer-model")
        
        assert result == initial_data
        mock_get_review.assert_called_once()
        mock_fix.assert_not_called()

    @patch("openexec_planner.llm_generator.LLMStoryGenerator._get_review")
    @patch("openexec_planner.llm_generator.LLMStoryGenerator._fix_stories")
    def test_review_loop_fix(self, mock_fix, mock_get_review):
        """Test the review loop with one rejection and then approval (implicit)."""
        generator = LLMStoryGenerator()
        # First call rejected, second iteration reached but loop finishes
        mock_get_review.side_effect = [
            {"approved": False, "assessment": "Bad", "key_issues": []},
            {"approved": True, "assessment": "Fixed"}
        ]
        mock_fix.return_value = [{"id": "US-001", "fixed": True}]
        
        initial_data = {"stories": [{"id": "US-001"}]}
        # We need max_iterations >= 2
        result = generator.review(initial_data, "intent", "reviewer-model", max_iterations=2)
        
        assert result["stories"][0].get("fixed") is True
        assert mock_get_review.call_count == 2
        mock_fix.assert_called_once()

    @patch("openexec_planner.llm_generator.LLMStoryGenerator._get_review")
    @patch("openexec_planner.llm_generator.LLMStoryGenerator._fix_stories")
    def test_review_loop_with_feedback_output(self, mock_fix, mock_get_review, capsys):
        """Test the review loop with complex rejection feedback to trigger print paths."""
        generator = LLMStoryGenerator()
        mock_get_review.return_value = {
            "approved": False, 
            "assessment": "Bad", 
            "key_issues": [
                {"category": "Logic", "description": "Broken", "examples": ["Ex1"]}
            ],
            "refactoring_plan": {
                "goal": "Refactor",
                "proposed_stories": [
                    {"story": "NewS", "maps_to": "REQ1", "tasks": ["T1"]}
                ]
            }
        }
        # Force exit after 1st iter to avoid infinite loop in test
        mock_fix.side_effect = Exception("Stop loop")
        
        with pytest.raises(Exception, match="Stop loop"):
            generator.review({"stories": []}, "intent", "reviewer")
            
        captured = capsys.readouterr()
        assert "Key Issues Found" in captured.out
        assert "Proposed Refactoring Plan" in captured.out
        assert "NewS (REQ1)" in captured.out

    @patch("subprocess.Popen")
    def test_call_cli_failure(self, mock_popen):
        """Test CLI call failure."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "CLI Error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        generator = LLMStoryGenerator()
        with pytest.raises(RuntimeError, match="CLI command failed"):
            generator._call_cli("prompt")


    def test_extract_json_mismatched_brackets(self):
        """Test JSON extraction with extra text and mismatched brackets."""
        response = "Here is some text before { \"key\": \"value\" } and after"
        generator = LLMStoryGenerator()
        data = generator._extract_json_from_response(response)
        assert data == {"key": "value"}

    def test_parse_response_array_fallback(self):
        """Test that _parse_response handles raw arrays by wrapping them."""
        generator = LLMStoryGenerator()
        # LLM might return just the list
        response = '[{"id": "US-001", "title": "Test"}]'
        result = generator._parse_response(response)
        assert "stories" in result
        assert result["stories"][0]["id"] == "US-001"

    @patch("anthropic.Anthropic")
    def test_call_anthropic(self, mock_anthropic):
        """Test calling Anthropic API."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Anthropic response")]
        mock_client.messages.create.return_value = mock_message

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            generator = LLMStoryGenerator(model="sonnet", use_api=True)
            output = generator._call_anthropic("prompt")
            assert output == "Anthropic response"

    @patch("openai.OpenAI")
    def test_call_openai(self, mock_openai):
        """Test calling OpenAI API."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="OpenAI response"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            generator = LLMStoryGenerator(model="gpt-5.3", use_api=True)
            output = generator._call_openai("prompt")
            assert output == "OpenAI response"

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_call_google(self, mock_configure, mock_model_class):
        """Test calling Google Gemini API."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = "Google response"
        mock_model.generate_content.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            generator = LLMStoryGenerator(model="gemini-3.1-pro-preview", use_api=True)
            output = generator._call_google("prompt")
            assert output == "Google response"
            mock_configure.assert_called_once_with(api_key="test-key")

    def test_call_anthropic_missing_key(self):
        """Test Anthropic call fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            generator = LLMStoryGenerator(model="sonnet", use_api=True)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                generator._call_anthropic("prompt")

    def test_call_openai_missing_key(self):
        """Test OpenAI call fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            generator = LLMStoryGenerator(model="gpt-5.3", use_api=True)
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                generator._call_openai("prompt")

    def test_call_google_missing_key(self):
        """Test Google call fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            generator = LLMStoryGenerator(model="gemini-3.1-pro-preview", use_api=True)
            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                generator._call_google("prompt")

    def test_call_anthropic_missing_package(self):
        """Test Anthropic call fails when package is not installed."""
        with patch.dict("sys.modules", {"anthropic": None}):
            generator = LLMStoryGenerator(model="sonnet", use_api=True)
            with pytest.raises(ImportError, match="anthropic package not installed"):
                generator._call_anthropic("prompt")

    def test_call_openai_missing_package(self):
        """Test OpenAI call fails when package is not installed."""
        with patch.dict("sys.modules", {"openai": None}):
            generator = LLMStoryGenerator(model="gpt-5.3", use_api=True)
            with pytest.raises(ImportError, match="openai package not installed"):
                generator._call_openai("prompt")

    def test_call_google_missing_package(self):
        """Test Google call fails when package is not installed."""
        with patch.dict("sys.modules", {"google.generativeai": None}):
            generator = LLMStoryGenerator(model="gemini-3.1-pro-preview", use_api=True)
            with pytest.raises(ImportError, match="google-generativeai package not installed"):
                generator._call_google("prompt")

    @patch("shutil.which")


    @patch.object(LLMStoryGenerator, "_call_cli")
    @patch.object(LLMStoryGenerator, "_call_anthropic")
    def test_call_llm_cli_success(self, mock_anthropic, mock_call_cli, mock_which):
        """Test _call_llm uses CLI when available."""
        mock_which.return_value = "/usr/bin/claude"
        mock_call_cli.return_value = "CLI result"
        
        generator = LLMStoryGenerator(model="sonnet", use_api=False)
        result = generator._call_llm("prompt")
        
        assert result == "CLI result"
        mock_call_cli.assert_called_once()
        mock_anthropic.assert_not_called()

    @patch("shutil.which")
    @patch.object(LLMStoryGenerator, "_call_cli")
    @patch.object(LLMStoryGenerator, "_call_anthropic")
    def test_call_llm_api_fallback(self, mock_anthropic, mock_call_cli, mock_which):
        """Test _call_llm falls back to API when CLI is missing."""
        mock_which.return_value = None # CLI missing
        mock_anthropic.return_value = "API result"
        
        generator = LLMStoryGenerator(model="sonnet", use_api=False)
        result = generator._call_llm("prompt")
        
        assert result == "API result"
        mock_anthropic.assert_called_once()
        mock_call_cli.assert_not_called()



