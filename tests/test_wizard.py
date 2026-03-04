"""Tests for intent wizard."""

import json
from unittest.mock import patch, MagicMock
import pytest
from openexec_orchestration.wizard import (
    IntentWizard, 
    IntentState, 
    ProjectFlow, 
    AppType,
    Platform,
    Goal,
    Constraint,
    Entity
)


class TestIntentWizard:
    """Tests for IntentWizard."""

    @patch("openexec_orchestration.llm_generator.LLMStoryGenerator")
    def test_process_message(self, mock_gen_class):
        """Test processing a message through the wizard with mock LLM."""
        # Setup mock
        mock_gen = MagicMock()
        mock_gen_class.return_value = mock_gen
        
        # Mock response from LLM
        mock_response = {
            "updated_state": {
                "project_name": "Test App",
                "flow": "greenfield",
                "app_type": "web",
                "problem_statement": "Need a test app"
            },
            "next_question": "What are your primary goals?",
            "is_complete": False
        }
        mock_gen._call_llm.return_value = "raw response"
        mock_gen._extract_json_from_response.return_value = mock_response
        
        wizard = IntentWizard()
        response = wizard.process_message("I want to build a web app")
        
        assert response.updated_state.project_name == "Test App"
        assert response.updated_state.flow == ProjectFlow.GREENFIELD
        assert response.next_question == "What are your primary goals?"
        assert wizard.state.project_name == "Test App"

    def test_intent_state_ready_checks(self):
        """Test the is_ready logic for different configurations."""
        state = IntentState()
        assert not state.is_ready()
        
        # Partially fill
        state.flow = ProjectFlow.GREENFIELD
        state.app_type = AppType.WEB
        state.problem_statement = "Test problem"
        assert not state.is_ready() # Missing goals, constraints, entities
        
        # Add goals and constraints
        state.primary_goals = [Goal(id="G1", description="Test goal")]
        state.constraints = [Constraint(id="C1", description="Test constraint")]
        assert not state.is_ready() # Missing entities
        
        # Add entity with data source
        state.entities = [Entity(name="User", data_source="Postgres")]
        assert state.is_ready()

        # Mobile requirement check
        state.app_type = AppType.MOBILE
        assert not state.is_ready() # Needs platform
        state.platforms = [Platform.IOS]
        assert state.is_ready()

        # Refactor requirement check
        state.flow = ProjectFlow.REFACTOR
        assert not state.is_ready() # Needs legacy path
        state.legacy_repo_path = "/path/to/repo"
        assert state.is_ready()


    def test_render_intent_md(self):
        """Test rendering state to markdown."""
        wizard = IntentWizard()
        wizard.state.project_name = "Markdown Test"
        wizard.state.problem_statement = "A test for rendering"
        wizard.state.primary_goals = [Goal(id="G1", description="Test Goal")]
        
        md = wizard.render_intent_md()
        assert "# Intent: Markdown Test" in md
        assert "A test for rendering" in md
        assert "G1: Test Goal" in md

    def test_scan_for_files(self, tmp_path):
        """Test scanning message for file paths."""
        # Create a dummy file
        test_file = tmp_path / "context.py"
        test_file.write_text("print('hello')")
        
        wizard = IntentWizard()
        
        # We need to be in the same dir for safe_resolve_path to work if we use relative paths
        with patch("os.getcwd", return_value=str(tmp_path)):
            files = wizard._scan_for_files(f"Check out {test_file.name}")
            assert test_file.name in files
            assert "print('hello')" in files[test_file.name]
