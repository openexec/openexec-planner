import json
import unittest
from unittest.mock import patch

from openexec_planner.llm_generator import LLMStoryGenerator


class TestPRDContext(unittest.TestCase):
    def setUp(self):
        self.generator = LLMStoryGenerator(model="sonnet")

    @patch("openexec_planner.llm_generator.LLMStoryGenerator._call_llm")
    def test_generate_with_prd_context(self, mock_call):
        # Arrange
        intent = """# My App
## Goals
- G1"""
        prd_context = {
            "personas": [{"key": "admin", "content": "Admin user info"}],
            "user_journeys": [{"key": "login", "content": "1. User logs in"}],
        }

        mock_call.return_value = json.dumps(
            {
                "stories": [
                    {
                        "id": "US-001",
                        "title": "Login for Admin",
                        "tasks": [
                            {
                                "id": "T1",
                                "title": "Implement login",
                                "technical_strategy": "strat",
                                "verification_script": "test",
                            }
                        ],
                    }
                ]
            }
        )

        # Act
        self.generator.generate(intent, prd_context=prd_context)

        # Assert
        # Check if the prompt sent to LLM contains our PRD strings
        args, _ = mock_call.call_args
        prompt = args[0]
        self.assertIn("STRUCTURED PRD CONTEXT", prompt)
        self.assertIn("Admin user info", prompt)
        self.assertIn("User logs in", prompt)

    def test_empty_prd_context(self):
        # Arrange
        intent = "# Intent"

        with patch.object(self.generator, "_call_llm") as mock_call:
            mock_call.return_value = json.dumps({"stories": []})

            # Act
            self.generator.generate(intent, prd_context=None)

            # Assert
            args, _ = mock_call.call_args
            prompt = args[0]
            self.assertNotIn("STRUCTURED PRD CONTEXT", prompt)


if __name__ == "__main__":
    unittest.main()
