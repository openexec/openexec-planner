"""Tests for goal tree building."""

import pytest
from openexec_orchestration.goal_tree import GoalTreeBuilder


class TestGoalTreeBuilder:
    """Tests for GoalTreeBuilder."""

    def test_build_simple_tree(self):
        """Test building a simple goal tree from parsed intent."""
        intent = {
            "title": "Test Project",
            "goals": [
                {"id": "G1", "title": "Goal 1", "description": "Desc 1"},
                {"id": "G2", "title": "Goal 2", "description": "Desc 2", "parent_goal": "G1"}
            ]
        }
        
        builder = GoalTreeBuilder()
        tree = builder.build(intent)
        
        assert tree["goal"] == "Test Project"
        assert len(tree["children"]) >= 1
        # G1's title is "Goal 1"
        goal_names = [c["goal"] for c in tree["children"] if "Goal 1" in c["goal"]]
        assert len(goal_names) > 0
