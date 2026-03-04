"""Tests for goal tree building."""

import pytest
from openexec_planner.goal_tree import GoalTreeBuilder


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

    def test_build_with_orphan_requirements(self):
        """Test that requirements not matching any goal are added as separate branches."""
        intent = {
            "title": "Project",
            "goals": ["Goal 1"],
            "requirements": ["Goal 1 Detail", "Unrelated Requirement"]
        }
        
        builder = GoalTreeBuilder()
        tree = builder.build(intent)
        
        # Should have 2 main branches: Goal 1 and Unrelated Requirement
        assert len(tree["children"]) == 2
        
    def test_build_with_constraints(self):
        """Test that constraints are added to the goal tree."""
        intent = {
            "title": "Project",
            "goals": [],
            "requirements": [],
            "constraints": ["Must use Python 3.11", "No external network"]
        }
        
        builder = GoalTreeBuilder()
        tree = builder.build(intent)
        
        # Root should have a "Constraints" child
        constraint_nodes = [c for c in tree["children"] if "Constraints" in c["goal"]]
        assert len(constraint_nodes) == 1
        assert len(constraint_nodes[0]["children"]) == 2
        
    def test_goal_node_dict_input(self):
        """Test GoalNode handling dictionary input for title."""
        from openexec_planner.goal_tree import GoalNode
        node = GoalNode(goal={"title": "Dict Goal"})
        assert node.goal == "Dict Goal"
        
        node = GoalNode(goal=123)
        assert node.goal == "123"

