"""Tests for CLI entrypoint."""

import json
from unittest.mock import MagicMock, patch

from openexec_planner.__main__ import main


class TestCLI:
    """Tests for the CLI commands."""

    def test_version_command(self, capsys):
        """Test the version command."""
        with patch("sys.argv", ["openexec-planner", "version"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "openexec-planner" in captured.out

    def test_parse_command(self, tmp_path, capsys):
        """Test the parse command."""
        intent_file = tmp_path / "INTENT.md"
        intent_file.write_text("# My Project\n\n## Goals\n- Goal 1")

        with patch("sys.argv", ["openexec-planner", "parse", str(intent_file)]):
            with patch("os.getcwd", return_value=str(tmp_path)):
                result = main()
                assert result == 0
                captured = capsys.readouterr()
                assert "Title: My Project" in captured.out
                assert "Goal 1" in captured.out

    @patch("openexec_planner.llm_generator.LLMStoryGenerator")
    def test_generate_command(self, mock_gen_class, tmp_path, capsys):
        """Test the generate command."""
        intent_file = tmp_path / "INTENT.md"
        intent_file.write_text("# My Project")
        output_file = tmp_path / "stories.json"

        mock_gen = MagicMock()
        mock_gen_class.return_value = mock_gen
        mock_gen.generate.return_value = {"stories": []}

        with patch("sys.argv", ["openexec-planner", "generate", str(intent_file), "-o", str(output_file)]):
            with patch("os.getcwd", return_value=str(tmp_path)):
                # Mock shutil.which to bypass CLI check
                with patch("shutil.which", return_value="/usr/bin/claude"):
                    result = main()
                    assert result == 0
                    assert output_file.exists()
                    data = json.loads(output_file.read_text())
                    assert "stories" in data

    def test_schedule_command(self, tmp_path, capsys):
        """Test the schedule command."""
        stories_file = tmp_path / "stories.json"
        stories_file.write_text(json.dumps({"stories": []}))

        with patch("sys.argv", ["openexec-planner", "schedule", str(stories_file)]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "tasks" in captured.out

    @patch("openexec_planner.wizard.IntentWizard")
    def test_wizard_command(self, mock_wizard_class, capsys):
        """Test the wizard command (single turn)."""
        mock_wizard = MagicMock()
        mock_wizard_class.return_value = mock_wizard

        mock_resp = MagicMock()
        mock_resp.next_question = "Question 1"
        mock_resp.model_dump_json.return_value = '{"question": "Question 1"}'

        mock_wizard.process_message.return_value = mock_resp

        with patch("sys.argv", ["openexec-planner", "wizard", "-m", "Hello"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "Question 1" in captured.out
            mock_wizard.process_message.assert_called_once_with("Hello")

    @patch("openexec_planner.wizard.IntentWizard")
    def test_wizard_render(self, mock_wizard_class, capsys):
        """Test the wizard command with --render."""
        mock_wizard = MagicMock()
        mock_wizard_class.return_value = mock_wizard
        mock_wizard.render_intent_md.return_value = "# Rendered"

        with patch("sys.argv", ["openexec-planner", "wizard", "--render"]):
            result = main()
            assert result == 0
            captured = capsys.readouterr()
            assert "# Rendered" in captured.out

    def test_wizard_state_loading(self, tmp_path):
        """Test the wizard command with state file loading/saving."""
        state_file = tmp_path / "state.json"
        state_data = {"project_name": "Loaded Project"}
        state_file.write_text(json.dumps(state_data))

        with patch("openexec_planner.wizard.IntentWizard") as mock_wizard_class:
            mock_wizard = MagicMock()
            mock_wizard_class.return_value = mock_wizard
            # Mocking process_message to not crash
            mock_wizard.process_message.return_value = MagicMock()

            with patch("sys.argv", ["openexec-planner", "wizard", "--state-file", str(state_file), "-m", "msg"]):
                main()
                # Should have loaded the state
                assert mock_wizard.state.project_name == "Loaded Project"
                # Should have updated the file
                assert state_file.exists()


    def test_build_tree_output_file(self, tmp_path):
        """Test build-tree command with output file."""
        intent_file = tmp_path / "INTENT.md"
        intent_file.write_text("# Title")
        output_file = tmp_path / "tree.json"

        with patch("sys.argv", ["openexec-planner", "build-tree", str(intent_file), "-o", str(output_file)]):
            with patch("os.getcwd", return_value=str(tmp_path)):
                main()
                assert output_file.exists()
                assert "goal" in output_file.read_text()


    @patch("openexec_planner.__main__.LLMStoryGenerator")
    def test_generate_with_reviewer(self, mock_gen_class, tmp_path):
        """Test generate command with a reviewer model."""
        intent_file = tmp_path / "INTENT.md"
        intent_file.write_text("# My Project")

        mock_gen = MagicMock()
        mock_gen_class.return_value = mock_gen
        mock_gen.generate.return_value = {"stories": []}
        mock_gen.review.return_value = {"stories": [], "reviewed": True}

        with patch("sys.argv", ["openexec-planner", "generate", str(intent_file), "--reviewer", "opus"]):
            with patch("os.getcwd", return_value=str(tmp_path)):
                with patch("shutil.which", return_value="/usr/bin/claude"):
                    result = main()
                    assert result == 0
                    mock_gen.review.assert_called_once()


    def test_build_tree_command(self, tmp_path, capsys):
        """Test the build-tree command."""
        intent_file = tmp_path / "INTENT.md"
        intent_file.write_text("# Test Project\n\n## Goals\n- Goal 1")

        with patch("sys.argv", ["openexec-planner", "build-tree", str(intent_file)]):
            with patch("os.getcwd", return_value=str(tmp_path)):
                result = main()
                assert result == 0
                captured = capsys.readouterr()
                assert "goal" in captured.out
                assert "Test Project" in captured.out

    @patch("openexec_planner.__main__.LLMStoryGenerator")
    def test_generate_error_fallback(self, mock_gen_class, tmp_path, capsys):
        """Test generate command falling back to rules on LLM error."""
        intent_file = tmp_path / "INTENT.md"
        intent_file.write_text("# My Project\n\n## Goals\n- Goal 1")

        mock_gen = MagicMock()
        mock_gen_class.return_value = mock_gen
        # Simulate an error that triggers fallback
        mock_gen.generate.side_effect = ValueError("LLM Failed")

        with patch("sys.argv", ["openexec-planner", "generate", str(intent_file)]):
            with patch("os.getcwd", return_value=str(tmp_path)):
                with patch("shutil.which", return_value="/usr/bin/claude"):
                    result = main()
                    assert result == 0
                    captured = capsys.readouterr()
                    # Fallback message goes to stderr
                    assert "Falling back to rule-based generation" in captured.err
                    assert "US-001" in captured.out



