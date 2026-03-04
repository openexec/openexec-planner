"""Tests for rule-based story generator."""

import pytest
from openexec_orchestration.generator import StoryGenerator


class TestStoryGenerator:
    """Tests for StoryGenerator."""

    def test_generate_from_goals(self):
        """Test generating stories from goals and related requirements."""
        intent = {
            "goals": ["Build a REST API"],
            "requirements": ["API returns JSON", "API handles errors"]
        }
        
        generator = StoryGenerator()
        stories = generator.generate(intent)
        
        assert len(stories) >= 1
        assert "US-001" == stories[0]["id"]
        assert "Build a REST API" == stories[0]["title"]
        # Should overlap with "API"
        assert len(stories[0]["acceptance_criteria"]) >= 2

    def test_generate_from_orphan_requirements(self):
        """Test requirements not covered by goals get their own stories."""
        intent = {
            "goals": [],
            "requirements": ["Implement Auth", "Add Database"]
        }
        
        generator = StoryGenerator()
        stories = generator.generate(intent)
        
        assert len(stories) == 2
        titles = [s["title"] for s in stories]
        assert "Implement Auth" in titles
        assert "Add Database" in titles

    def test_generate_description(self):
        """Test user story description formatting."""
        generator = StoryGenerator()
        
        desc = generator._generate_description("Implement Login")
        assert desc == "As a user, I want to login"
        
        desc = generator._generate_description("Create Dashboard")
        assert desc == "As a user, I want to dashboard"

    def test_infer_criteria_patterns(self):
        """Test specific pattern matching for AC inference."""
        generator = StoryGenerator()
        
        # API pattern
        ac = generator._infer_acceptance_criteria("Public API")
        assert any("returns valid responses" in c for c in ac)
        
        # UI pattern
        ac = generator._infer_acceptance_criteria("User Interface")
        assert any("UI responds appropriately" in c for c in ac)
        
        # Auth pattern
        ac = generator._infer_acceptance_criteria("User Authentication")
        assert any("valid credentials" in c for c in ac)

    def test_generate_tasks_length(self):
        """Test task list generation."""
        generator = StoryGenerator()
        
        # Short list
        tasks = generator._generate_tasks("Simple Task", ["AC1"])
        assert len(tasks) == 3 # Design, Implement, Test
        
        # Long list adds Documentation
        tasks = generator._generate_tasks("Complex Task", ["AC1", "AC2", "AC3"])
        assert len(tasks) == 4
        assert any("Document" in t for t in tasks)
