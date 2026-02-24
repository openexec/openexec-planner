"""Tests for the planning module."""

import tempfile
from pathlib import Path

import pytest

from planning import (
    ArtifactNotFoundError,
    ArtifactType,
    GoalLevel,
    GoalTree,
    GoalTreeNode,
    GuardrailIssue,
    PlanningArtifact,
    PlanningPhase,
    PlanningState,
    ValidationIssue,
    ValidationResult,
    check_circular_dependencies,
    check_feature_islands,
    check_integration_story_dependencies,
    check_priority_inversion,
    create_planning_artifact,
    decompose_goal_tree,
    ensure_docs_dir,
    get_artifact_path,
    load_artifact_content,
    load_background_context,
    load_planning_state,
    parse_features_from_intent,
    parse_goals_from_intent,
    parse_stories_from_markdown,
    save_planning_state,
    update_artifact,
    validate_architecture,
    validate_intent,
    validate_user_stories,
)


class TestValidationIssue:
    """Tests for ValidationIssue class."""

    def test_validation_issue_creation(self) -> None:
        """Test creating a validation issue."""
        issue = ValidationIssue(
            severity="error",
            message="Test error",
            line_number=10,
            section="Goals",
        )
        assert issue.severity == "error"  # nosec: B101
        assert issue.message == "Test error"  # nosec: B101
        assert issue.line_number == 10  # nosec: B101
        assert issue.section == "Goals"  # nosec: B101

    def test_validation_issue_to_dict(self) -> None:
        """Test converting validation issue to dict."""
        issue = ValidationIssue(
            severity="warning",
            message="Test warning",
        )
        result = issue.to_dict()
        assert result["severity"] == "warning"  # nosec: B101
        assert result["message"] == "Test warning"  # nosec: B101


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_validation_result_valid(self) -> None:
        """Test creating a valid validation result."""
        result = ValidationResult(valid=True, issues=[])
        assert result.valid is True  # nosec: B101
        assert result.has_errors is False  # nosec: B101
        assert result.error_count == 0  # nosec: B101

    def test_validation_result_with_errors(self) -> None:
        """Test validation result with errors."""
        issues = [
            ValidationIssue(severity="error", message="Error 1"),
            ValidationIssue(severity="warning", message="Warning 1"),
        ]
        result = ValidationResult(valid=False, issues=issues)
        assert result.valid is False  # nosec: B101
        assert result.has_errors is True  # nosec: B101
        assert result.error_count == 1  # nosec: B101
        assert result.warning_count == 1  # nosec: B101


class TestPlanningArtifact:
    """Tests for PlanningArtifact class."""

    def test_artifact_creation(self) -> None:
        """Test creating a planning artifact."""
        artifact = PlanningArtifact(
            artifact_type=ArtifactType.INTENT,
            path="docs/INTENT.md",
        )
        assert artifact.artifact_type == ArtifactType.INTENT  # nosec: B101
        assert artifact.path == "docs/INTENT.md"  # nosec: B101
        assert artifact.validated is False  # nosec: B101


class TestPlanningState:
    """Tests for PlanningState class."""

    def test_state_creation(self) -> None:
        """Test creating planning state."""
        state = PlanningState()
        assert state.phase == PlanningPhase.INIT  # nosec: B101
        assert state.current_iteration == 0  # nosec: B101
        assert state.is_blocked is False  # nosec: B101

    def test_add_artifact(self) -> None:
        """Test adding an artifact to state."""
        state = PlanningState()
        artifact = PlanningArtifact(
            artifact_type=ArtifactType.INTENT,
            path="docs/INTENT.md",
        )
        state.add_artifact(artifact)
        assert state.get_artifact(ArtifactType.INTENT) is not None  # nosec: B101

    def test_add_guardrail_issue(self) -> None:
        """Test adding a guardrail issue."""
        state = PlanningState()
        issue = GuardrailIssue(
            guardrail="test",
            severity="error",
            message="Test error",
        )
        state.add_guardrail_issue(issue)
        assert state.is_blocked is True  # nosec: B101
        assert len(state.blocking_issues) == 1  # nosec: B101

    def test_advance_phase(self) -> None:
        """Test advancing planning phase."""
        state = PlanningState()
        state.advance_phase(PlanningPhase.GENERATE)
        assert state.phase == PlanningPhase.GENERATE  # nosec: B101


class TestValidateIntent:
    """Tests for validate_intent function."""

    def test_empty_intent(self) -> None:
        """Test validation of empty INTENT.md."""
        result = validate_intent("")
        assert result.valid is False  # nosec: B101
        assert result.error_count > 0  # nosec: B101

    def test_valid_intent(self) -> None:
        """Test validation of valid INTENT.md."""
        content = """# Intent

## Problem Statement
This is a test problem.

## Goals
1. First goal
2. Second goal

## Features
Test features here.

## Constraints
Some constraints.
"""
        result = validate_intent(content)
        assert result.valid is True  # nosec: B101
        assert result.error_count == 0  # nosec: B101

    def test_missing_required_sections(self) -> None:
        """Test intent missing required sections."""
        content = """# Intent

## Problem Statement
This is a test.
"""
        result = validate_intent(content)
        assert result.valid is False  # nosec: B101
        assert result.error_count > 0  # nosec: B101


class TestValidateArchitecture:
    """Tests for validate_architecture function."""

    def test_empty_architecture(self) -> None:
        """Test validation of empty ARCHITECTURE.md."""
        result = validate_architecture("")
        assert result.valid is False  # nosec: B101

    def test_valid_architecture(self) -> None:
        """Test validation of valid ARCHITECTURE.md."""
        content = """# Architecture

## Overview
System overview.

## Data Flow
Data flows through the system.

## Components
Component descriptions.
"""
        result = validate_architecture(content)
        assert result.valid is True  # nosec: B101

    def test_missing_data_flow(self) -> None:
        """Test architecture missing data flow."""
        content = """# Architecture

## Overview
System overview.

## Components
Component descriptions.
"""
        result = validate_architecture(content)
        assert result.valid is False  # nosec: B101


class TestValidateUserStories:
    """Tests for validate_user_stories function."""

    def test_empty_stories(self) -> None:
        """Test validation of empty USER_STORIES.md."""
        result = validate_user_stories("")
        assert result.valid is False  # nosec: B101

    def test_valid_stories(self) -> None:
        """Test validation of valid USER_STORIES.md."""
        content = """## US-001: Create user account

Tier 1
Priority: 1

As a user, I want to create an account so that I can access the system.

Acceptance Criteria:
- User can enter email and password
- Account is created successfully
"""
        result = validate_user_stories(content)
        assert result.valid is True  # nosec: B101

    def test_missing_story_format(self) -> None:
        """Test stories without US-XXX format."""
        content = """## Story: Create user account

Some content here.
"""
        result = validate_user_stories(content)
        assert result.valid is False  # nosec: B101


class TestParseStoriesFromMarkdown:
    """Tests for parse_stories_from_markdown function."""

    def test_parse_single_story(self) -> None:
        """Test parsing a single user story."""
        content = """## US-001: Create account

Tier 1
Priority: 1

Description here.
"""
        stories = parse_stories_from_markdown(content)
        assert len(stories) == 1  # nosec: B101
        assert stories[0]["id"] == "US-001"  # nosec: B101
        assert stories[0]["tier"] == 1  # nosec: B101
        assert stories[0]["priority"] == 1  # nosec: B101

    def test_parse_multiple_stories(self) -> None:
        """Test parsing multiple user stories."""
        content = """## US-001: First story

Tier 1

Content.

## US-002: Second story

Tier 2

More content.
"""
        stories = parse_stories_from_markdown(content)
        assert len(stories) == 2  # nosec: B101
        assert stories[0]["id"] == "US-001"  # nosec: B101
        assert stories[1]["id"] == "US-002"  # nosec: B101

    def test_parse_story_with_dependencies(self) -> None:
        """Test parsing story with dependencies."""
        content = """## US-001: First story

Tier 1

## US-002: Second story

Depends on: US-001

Tier 2
"""
        stories = parse_stories_from_markdown(content)
        assert stories[1]["depends_on"] == ["US-001"]  # nosec: B101


class TestGuardrails:
    """Tests for guardrail functions."""

    def test_check_feature_islands(self) -> None:
        """Test detecting feature islands."""
        stories = [
            {"id": "US-001", "tier": 1, "title": "Base feature", "depends_on": []},
            {
                "id": "US-002",
                "tier": 2,
                "title": "Enhance base feature",
                "depends_on": [],
            },
        ]
        issues = check_feature_islands(stories)
        assert len(issues) > 0  # nosec: B101
        assert any(i.guardrail == "feature_islands" for i in issues)  # nosec: B101

    def test_check_priority_inversion(self) -> None:
        """Test detecting priority inversions."""
        stories = [
            {"id": "US-001", "priority": 1, "depends_on": []},
            {"id": "US-002", "priority": 2, "depends_on": ["US-001"]},
        ]
        issues = check_priority_inversion(stories)
        # No inversion, so no issues
        assert len(issues) == 0  # nosec: B101

        # Now test with inversion
        stories = [
            {"id": "US-001", "priority": 2, "depends_on": []},
            {"id": "US-002", "priority": 1, "depends_on": ["US-001"]},
        ]
        issues = check_priority_inversion(stories)
        assert len(issues) > 0  # nosec: B101

    def test_check_circular_dependencies(self) -> None:
        """Test detecting circular dependencies."""
        stories = [
            {"id": "US-001", "depends_on": ["US-002"]},
            {"id": "US-002", "depends_on": ["US-001"]},
        ]
        issues = check_circular_dependencies(stories)
        assert len(issues) > 0  # nosec: B101
        assert issues[0].severity == "error"  # nosec: B101

    def test_check_integration_story_dependencies(self) -> None:
        """Test checking integration story dependencies."""
        stories = [
            {"id": "IS-001", "depends_on": []},
            {"id": "US-001", "depends_on": []},
        ]
        issues = check_integration_story_dependencies(stories)
        assert len(issues) > 0  # nosec: B101


class TestPlanningStateFileOperations:
    """Tests for planning state file operations."""

    def test_state_to_file_and_back(self) -> None:
        """Test saving and loading planning state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            state = PlanningState()
            state.advance_phase(PlanningPhase.GENERATE)

            save_planning_state(project_root, state)

            loaded_state = load_planning_state(project_root)
            assert loaded_state.phase == PlanningPhase.GENERATE  # nosec: B101


class TestPlanningArtifactFileOperations:
    """Tests for planning artifact file operations."""

    def test_create_artifact(self) -> None:
        """Test creating a planning artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            content = "# Intent\n\n## Problem Statement\nTest"
            artifact = create_planning_artifact(
                project_root, ArtifactType.INTENT, content
            )
            assert artifact.artifact_type == ArtifactType.INTENT  # nosec: B101

            loaded = load_artifact_content(project_root, ArtifactType.INTENT)
            assert loaded == content  # nosec: B101

    def test_load_nonexistent_artifact(self) -> None:
        """Test loading a nonexistent artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            with pytest.raises(ArtifactNotFoundError):
                load_artifact_content(project_root, ArtifactType.INTENT)

    def test_update_artifact(self) -> None:
        """Test updating a planning artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            state = PlanningState()

            # Create initial artifact
            content1 = "# Intent\n\n## Problem\nInitial"
            create_planning_artifact(project_root, ArtifactType.INTENT, content1)

            # Update it
            content2 = "# Intent\n\n## Problem\nUpdated"
            update_artifact(project_root, ArtifactType.INTENT, content2, state)

            # Verify
            loaded = load_artifact_content(project_root, ArtifactType.INTENT)
            assert loaded == content2  # nosec: B101


class TestLoadBackgroundContext:
    """Tests for loading background context."""

    def test_load_background_context_empty(self) -> None:
        """Test loading background context when directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            context = load_background_context(project_root)
            assert context == []  # nosec: B101

    def test_load_background_context_with_files(self) -> None:
        """Test loading background context files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            bg_dir = project_root / "docs" / "background"
            bg_dir.mkdir(parents=True)

            # Create test files
            (bg_dir / "file1.md").write_text("Content 1")
            (bg_dir / "file2.md").write_text("Content 2")

            context = load_background_context(project_root)
            assert len(context) == 2  # nosec: B101
            assert any(f["name"] == "file1.md" for f in context)  # nosec: B101


class TestEnsureDocsDir:
    """Tests for ensuring docs directory exists."""

    def test_ensure_docs_dir(self) -> None:
        """Test creating docs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            docs_path = ensure_docs_dir(project_root)
            assert docs_path.exists()  # nosec: B101
            assert docs_path.is_dir()  # nosec: B101


class TestGetArtifactPath:
    """Tests for getting artifact paths."""

    def test_get_artifact_paths(self) -> None:
        """Test getting paths for different artifact types."""
        project_root = Path("/test")
        assert get_artifact_path(project_root, ArtifactType.INTENT) == (  # nosec: B101
            project_root / "docs" / "INTENT.md"
        )
        assert get_artifact_path(project_root, ArtifactType.RELEASE) == (  # nosec: B101
            project_root / ".openexec" / "release.json"
        )


class TestGoalTreeNode:
    """Tests for GoalTreeNode class."""

    def test_goal_tree_node_creation(self) -> None:
        """Test creating a goal tree node."""
        node = GoalTreeNode(
            identifier="G-001",
            level=GoalLevel.GOAL,
            title="Main Goal",
            description="This is the main goal",
        )
        assert node.identifier == "G-001"  # nosec: B101
        assert node.level == GoalLevel.GOAL  # nosec: B101
        assert node.title == "Main Goal"  # nosec: B101
        assert node.parent_id is None  # nosec: B101
        assert node.children_ids == []  # nosec: B101

    def test_goal_tree_node_to_dict(self) -> None:
        """Test converting node to dictionary."""
        node = GoalTreeNode(
            identifier="CSF-001",
            level=GoalLevel.CSF,
            title="Critical Success Factor",
            parent_id="G-001",
        )
        node_dict = node.to_dict()
        assert node_dict["identifier"] == "CSF-001"  # nosec: B101
        assert node_dict["level"] == "csf"  # nosec: B101
        assert node_dict["parent_id"] == "G-001"  # nosec: B101


class TestGoalTree:
    """Tests for GoalTree class."""

    def test_goal_tree_creation(self) -> None:
        """Test creating a goal tree."""
        tree = GoalTree()
        assert len(tree.nodes) == 0  # nosec: B101

    def test_add_node(self) -> None:
        """Test adding nodes to tree."""
        tree = GoalTree()
        node1 = GoalTreeNode("G-001", GoalLevel.GOAL, "Goal 1")
        tree.add_node(node1)
        assert len(tree.nodes) == 1  # nosec: B101
        assert tree.get_node("G-001") == node1  # nosec: B101

    def test_get_node(self) -> None:
        """Test getting a node by identifier."""
        tree = GoalTree()
        node = GoalTreeNode("G-001", GoalLevel.GOAL, "Goal 1")
        tree.add_node(node)
        retrieved = tree.get_node("G-001")
        assert retrieved is not None  # nosec: B101
        assert retrieved.identifier == "G-001"  # nosec: B101

    def test_get_children(self) -> None:
        """Test getting children of a node."""
        tree = GoalTree()
        parent = GoalTreeNode("G-001", GoalLevel.GOAL, "Goal 1")
        child1 = GoalTreeNode(
            "CSF-001", GoalLevel.CSF, "CSF 1", parent_id="G-001"
        )
        child2 = GoalTreeNode(
            "CSF-002", GoalLevel.CSF, "CSF 2", parent_id="G-001"
        )
        tree.add_node(parent)
        tree.add_node(child1)
        tree.add_node(child2)

        children = tree.get_children("G-001")
        assert len(children) == 2  # nosec: B101
        assert child1 in children  # nosec: B101
        assert child2 in children  # nosec: B101

    def test_get_by_level(self) -> None:
        """Test getting all nodes at a specific level."""
        tree = GoalTree()
        tree.add_node(GoalTreeNode("G-001", GoalLevel.GOAL, "Goal 1"))
        tree.add_node(GoalTreeNode("G-002", GoalLevel.GOAL, "Goal 2"))
        tree.add_node(GoalTreeNode("CSF-001", GoalLevel.CSF, "CSF 1"))

        goals = tree.get_by_level(GoalLevel.GOAL)
        assert len(goals) == 2  # nosec: B101
        csfs = tree.get_by_level(GoalLevel.CSF)
        assert len(csfs) == 1  # nosec: B101

    def test_get_flattened_view(self) -> None:
        """Test getting a flattened view of the tree."""
        tree = GoalTree()
        goal = GoalTreeNode("G-001", GoalLevel.GOAL, "Goal 1")
        csf = GoalTreeNode("CSF-001", GoalLevel.CSF, "CSF 1", parent_id="G-001")
        goal.children_ids = ["CSF-001"]

        tree.add_node(goal)
        tree.add_node(csf)

        flattened = tree.get_flattened_view()
        assert len(flattened) == 2  # nosec: B101
        assert flattened[0]["identifier"] == "G-001"  # nosec: B101
        assert flattened[0]["depth"] == 0  # nosec: B101
        assert flattened[1]["identifier"] == "CSF-001"  # nosec: B101
        assert flattened[1]["depth"] == 1  # nosec: B101

    def test_goal_tree_to_dict(self) -> None:
        """Test converting tree to dictionary."""
        tree = GoalTree()
        tree.add_node(GoalTreeNode("G-001", GoalLevel.GOAL, "Goal 1"))
        tree_dict = tree.to_dict()
        assert "nodes" in tree_dict  # nosec: B101
        assert "G-001" in tree_dict["nodes"]  # nosec: B101


class TestParseGoalsFromIntent:
    """Tests for parsing goals from INTENT.md."""

    def test_parse_single_goal(self) -> None:
        """Test parsing a single goal."""
        content = """
## Goals
1. Implement advanced planning logic.
"""
        goals = parse_goals_from_intent(content)
        assert len(goals) == 1  # nosec: B101
        assert "advanced planning" in goals[0]  # nosec: B101

    def test_parse_multiple_goals(self) -> None:
        """Test parsing multiple goals."""
        content = """
## Goals
1. Implement advanced intent-parsing logic.
2. Synchronize project state with database.
3. Provide multi-language quality gates.
"""
        goals = parse_goals_from_intent(content)
        assert len(goals) == 3  # nosec: B101

    def test_parse_empty_goals(self) -> None:
        """Test parsing content with no goals section."""
        content = "# Intent\n\n## Problem\nSome problem"
        goals = parse_goals_from_intent(content)
        assert len(goals) == 0  # nosec: B101


class TestParseFeaturesFromIntent:
    """Tests for parsing features from INTENT.md."""

    def test_parse_bold_features(self) -> None:
        """Test parsing bold formatted features."""
        content = """
## Features
1. **Advanced Planning**: Implement planning logic.
2. **State Engine**: Integrate database.
"""
        features = parse_features_from_intent(content)
        assert len(features) >= 1  # nosec: B101

    def test_parse_empty_features(self) -> None:
        """Test parsing content with no features section."""
        content = "# Intent\n\n## Problem\nSome problem"
        features = parse_features_from_intent(content)
        assert len(features) == 0  # nosec: B101


class TestDecomposeGoalTree:
    """Tests for decomposing INTENT.md into goal tree."""

    def test_decompose_basic_intent(self) -> None:
        """Test decomposing a basic INTENT.md."""
        content = """
## Goals
1. Implement advanced planning.
2. Synchronize project state.

## Features
**Advanced Planning**: Implement planning logic.
**State Engine**: Integrate database.
**Quality Gates**: Provide validation.
"""
        tree = decompose_goal_tree(content)

        # Check that tree has nodes
        assert len(tree.nodes) > 0  # nosec: B101

        # Check that goals were created
        goals = tree.get_by_level(GoalLevel.GOAL)
        assert len(goals) == 2  # nosec: B101

        # Check that CSFs were created
        csfs = tree.get_by_level(GoalLevel.CSF)
        assert len(csfs) > 0  # nosec: B101

        # Check that NCs were created
        ncs = tree.get_by_level(GoalLevel.NC)
        assert len(ncs) > 0  # nosec: B101

        # Check that features were created
        features = tree.get_by_level(GoalLevel.FEATURE)
        assert len(features) == 3  # nosec: B101

    def test_decompose_single_goal(self) -> None:
        """Test decomposing with a single goal."""
        content = """
## Goals
1. Implement core functionality.

## Features
**Feature A**: Description A.
"""
        tree = decompose_goal_tree(content)

        goals = tree.get_by_level(GoalLevel.GOAL)
        assert len(goals) == 1  # nosec: B101

        # Each goal should have children (CSFs)
        csfs = tree.get_children("G-001")
        assert len(csfs) > 0  # nosec: B101

    def test_decompose_hierarchical_structure(self) -> None:
        """Test that decomposed tree has proper hierarchy."""
        content = """
## Goals
1. Goal one.

## Features
**Feature 1**: Feature description.
"""
        tree = decompose_goal_tree(content)

        # Get root goal
        goal = tree.get_node("G-001")
        assert goal is not None  # nosec: B101

        # Goal should have CSFs as children
        csf_ids = goal.children_ids if goal else []
        assert len(csf_ids) > 0  # nosec: B101

        # Check first CSF has NCs as children
        if csf_ids:
            csf = tree.get_node(csf_ids[0])
            if csf:
                assert len(csf.children_ids) > 0  # nosec: B101

    def test_decompose_empty_intent(self) -> None:
        """Test decomposing content with no goals or features."""
        content = "# Intent\n\n## Problem\nSome problem"
        tree = decompose_goal_tree(content)

        # Tree should still be valid but may be empty
        assert isinstance(tree, GoalTree)  # nosec: B101

    def test_decompose_goal_tree_to_dict(self) -> None:
        """Test converting decomposed tree to dictionary."""
        content = """
## Goals
1. Goal one.

## Features
**Feature 1**: Description.
"""
        tree = decompose_goal_tree(content)
        tree_dict = tree.to_dict()

        assert "nodes" in tree_dict  # nosec: B101
        assert isinstance(tree_dict["nodes"], dict)  # nosec: B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
