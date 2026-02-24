"""Planning workflow for UAOS orchestration.

This module provides the core planning functionality for generating
INTENT.md, ARCHITECTURE.md, USER_STORIES.md, release.json, and tasks.json.

Ported from OpenExec core planning logic with refactoring for UAOS context.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Re-export types for backward compatibility
from enum import StrEnum

if TYPE_CHECKING:
    pass

# Default paths for planning artifacts
DOCS_DIR = "docs"
BACKGROUND_DIR = "docs/background"
INTENT_FILE = "docs/INTENT.md"
ARCHITECTURE_FILE = "docs/ARCHITECTURE.md"
USER_STORIES_FILE = "docs/USER_STORIES.md"
RELEASE_FILE = ".openexec/release.json"
TASKS_FILE = ".openexec/tasks.json"
PLANNING_STATE_FILE = ".openexec/planning_state.json"

# Required sections in INTENT.md
INTENT_REQUIRED_SECTIONS = [
    "Problem Statement",
    "Goals",
    "Features",
    "Constraints",
]

# Required sections in ARCHITECTURE.md
ARCHITECTURE_REQUIRED_SECTIONS = [
    "Overview",
    "Data Flow",
    "Components",
]

# Tier patterns for user stories
TIER_PATTERN = re.compile(r"(?:Tier|T)[\s:-]*([1-3])", re.IGNORECASE)


class PlanningPhase(StrEnum):
    """Phase of the planning workflow."""

    INIT = "init"
    GENERATE = "generate"
    REVIEW = "review"
    ELABORATE = "elaborate"
    COMPLETE = "complete"


class ArtifactType(StrEnum):
    """Type of planning artifact."""

    INTENT = "intent"
    ARCHITECTURE = "architecture"
    USER_STORIES = "user_stories"
    RELEASE = "release"
    TASKS = "tasks"


class StoryType(StrEnum):
    """Classification of story types for backend-first workflow."""

    INTEGRATION = "integration"  # IS-* stories, always run first
    BACKEND = "backend"
    FRONTEND = "frontend"
    TEST = "test"
    GENERAL = "general"


class GoalLevel(StrEnum):
    """Levels in the Goal Tree hierarchy."""

    GOAL = "goal"
    CSF = "csf"  # Critical Success Factor
    NC = "nc"  # Necessary Condition
    SO = "so"  # Strategic Objective
    FEATURE = "feature"


class GoalTreeNode:
    """A node in the Goal Tree hierarchy."""

    def __init__(
        self,
        identifier: str,
        level: GoalLevel,
        title: str,
        description: str = "",
        parent_id: str | None = None,
        children_ids: list[str] | None = None,
    ) -> None:
        """Initialize a Goal Tree node.

        Args:
            identifier: Unique identifier for this node
            level: Level in the goal tree hierarchy
            title: Short title for this node
            description: Detailed description
            parent_id: ID of parent node
            children_ids: IDs of child nodes
        """
        self.identifier = identifier
        self.level = level
        self.title = title
        self.description = description
        self.parent_id = parent_id
        self.children_ids = children_ids or []
        self.created_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "identifier": self.identifier,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "created_at": self.created_at.isoformat(),
        }


class GoalTree:
    """A hierarchical decomposition of goals into CSFs, NCs, and Features."""

    def __init__(self) -> None:
        """Initialize an empty Goal Tree."""
        self.nodes: dict[str, GoalTreeNode] = {}
        self.created_at = datetime.now()

    def add_node(self, node: GoalTreeNode) -> None:
        """Add a node to the tree.

        Args:
            node: The node to add
        """
        self.nodes[node.identifier] = node

    def get_node(self, identifier: str) -> GoalTreeNode | None:
        """Get a node by identifier.

        Args:
            identifier: The node identifier

        Returns:
            The node or None if not found
        """
        return self.nodes.get(identifier)

    def get_children(self, parent_id: str) -> list[GoalTreeNode]:
        """Get all children of a node.

        Args:
            parent_id: The parent node identifier

        Returns:
            List of child nodes
        """
        return [
            node for node in self.nodes.values()
            if node.parent_id == parent_id
        ]

    def get_by_level(self, level: GoalLevel) -> list[GoalTreeNode]:
        """Get all nodes at a specific level.

        Args:
            level: The goal level

        Returns:
            List of nodes at that level
        """
        return [node for node in self.nodes.values() if node.level == level]

    def get_flattened_view(self) -> list[dict[str, Any]]:
        """Get a flattened view of the tree.

        Returns:
            List of node dictionaries in hierarchy order
        """
        result = []

        # Get root nodes (goals with no parent)
        roots = [n for n in self.nodes.values() if n.parent_id is None]

        def add_node_recursive(node: GoalTreeNode, depth: int = 0) -> None:
            """Recursively add node and its children."""
            node_dict = node.to_dict()
            node_dict["depth"] = depth
            result.append(node_dict)

            for child_id in node.children_ids:
                child = self.get_node(child_id)
                if child:
                    add_node_recursive(child, depth + 1)

        # Add all roots and their descendants
        for root in roots:
            add_node_recursive(root)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "created_at": self.created_at.isoformat(),
            "nodes": {
                identifier: node.to_dict()
                for identifier, node in self.nodes.items()
            },
        }


class PlanningError(Exception):
    """Base exception for planning errors."""

    pass


class ArtifactNotFoundError(PlanningError):
    """Raised when a required planning artifact is not found."""

    pass


class ValidationError(PlanningError):
    """Raised when artifact validation fails."""

    pass


class GuardrailError(PlanningError):
    """Raised when guardrail check fails."""

    pass


class ValidationIssue:
    """A validation issue found in a planning artifact."""

    def __init__(
        self,
        severity: str,
        message: str,
        line_number: int | None = None,
        section: str | None = None,
    ) -> None:
        """Initialize a validation issue.

        Args:
            severity: "error" or "warning"
            message: Description of the issue
            line_number: Optional line where issue was found
            section: Optional section where issue was found
        """
        self.severity = severity
        self.message = message
        self.line_number = line_number
        self.section = section

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity,
            "message": self.message,
            "line_number": self.line_number,
            "section": self.section,
        }


class ValidationResult:
    """Result of validating a planning artifact."""

    def __init__(self, valid: bool, issues: list[ValidationIssue]) -> None:
        """Initialize validation result.

        Args:
            valid: Whether artifact is valid
            issues: List of validation issues
        """
        self.valid = valid
        self.issues = issues

    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class GuardrailIssue:
    """An issue detected by planning guardrails."""

    def __init__(
        self,
        guardrail: str,
        severity: str,
        message: str,
        affected_items: list[str] | None = None,
    ) -> None:
        """Initialize a guardrail issue.

        Args:
            guardrail: Name of the guardrail that detected the issue
            severity: "error" or "warning"
            message: Description of the issue
            affected_items: IDs of affected stories/tasks
        """
        self.guardrail = guardrail
        self.severity = severity
        self.message = message
        self.affected_items = affected_items or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "guardrail": self.guardrail,
            "severity": self.severity,
            "message": self.message,
            "affected_items": self.affected_items,
        }


class PlanningArtifact:
    """A planning artifact (document) in the workflow."""

    def __init__(
        self,
        artifact_type: ArtifactType,
        path: str,
        validated: bool = False,
        validation_result: ValidationResult | None = None,
    ) -> None:
        """Initialize a planning artifact.

        Args:
            artifact_type: Type of artifact
            path: Path to the artifact file
            validated: Whether validated
            validation_result: Result of last validation
        """
        self.artifact_type = artifact_type
        self.path = path
        self.validated = validated
        self.validation_result = validation_result
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artifact_type": self.artifact_type.value,
            "path": self.path,
            "validated": self.validated,
            "validation_result": (
                self.validation_result.to_dict()
                if self.validation_result
                else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ReviewIteration:
    """A single iteration of AI review on planning artifacts."""

    def __init__(
        self,
        iteration_number: int,
        agent: str,
        artifact_type: ArtifactType,
        feedback: str,
        issues_found: int = 0,
        fixes_applied: bool = False,
        duration_ms: int = 0,
    ) -> None:
        """Initialize a review iteration.

        Args:
            iteration_number: Iteration number (1-indexed)
            agent: Agent that performed the review
            artifact_type: Type of artifact reviewed
            feedback: AI feedback from the review
            issues_found: Number of issues found
            fixes_applied: Whether fixes were applied
            duration_ms: Time taken for the review
        """
        self.iteration_number = iteration_number
        self.reviewed_at = datetime.now()
        self.agent = agent
        self.artifact_type = artifact_type
        self.feedback = feedback
        self.issues_found = issues_found
        self.fixes_applied = fixes_applied
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration_number": self.iteration_number,
            "reviewed_at": self.reviewed_at.isoformat(),
            "agent": self.agent,
            "artifact_type": self.artifact_type.value,
            "feedback": self.feedback,
            "issues_found": self.issues_found,
            "fixes_applied": self.fixes_applied,
            "duration_ms": self.duration_ms,
        }


class PlanningState:
    """State of the planning workflow for a project."""

    def __init__(self) -> None:
        """Initialize planning state."""
        self.phase = PlanningPhase.INIT
        self.artifacts: dict[str, PlanningArtifact] = {}
        self.review_iterations: list[ReviewIteration] = []
        self.guardrail_issues: list[GuardrailIssue] = []
        self.blocking_issues: list[str] = []
        self.started_at = datetime.now()
        self.updated_at = datetime.now()

    @property
    def current_iteration(self) -> int:
        """Get the current review iteration number."""
        return len(self.review_iterations)

    @property
    def is_blocked(self) -> bool:
        """Check if planning is blocked."""
        return len(self.blocking_issues) > 0

    def get_artifact(self, artifact_type: ArtifactType) -> PlanningArtifact | None:
        """Get an artifact by type."""
        return self.artifacts.get(artifact_type.value)

    def add_artifact(self, artifact: PlanningArtifact) -> None:
        """Add or update an artifact."""
        self.artifacts[artifact.artifact_type.value] = artifact
        self.updated_at = datetime.now()

    def add_review_iteration(self, iteration: ReviewIteration) -> None:
        """Add a review iteration."""
        self.review_iterations.append(iteration)
        self.updated_at = datetime.now()

    def clear_guardrail_issues(self) -> None:
        """Clear guardrail issues."""
        self.guardrail_issues = []

    def add_guardrail_issue(self, issue: GuardrailIssue) -> None:
        """Add a guardrail issue."""
        self.guardrail_issues.append(issue)
        if issue.severity == "error":
            self.blocking_issues.append(issue.message)
        self.updated_at = datetime.now()

    def advance_phase(self, new_phase: PlanningPhase) -> None:
        """Advance to a new planning phase."""
        self.phase = new_phase
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phase": self.phase.value,
            "artifacts": {k: v.to_dict() for k, v in self.artifacts.items()},
            "review_iterations": [it.to_dict() for it in self.review_iterations],
            "guardrail_issues": [gi.to_dict() for gi in self.guardrail_issues],
            "blocking_issues": self.blocking_issues,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_file(self, path: Path) -> None:
        """Save the state to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def from_file(cls, path: Path) -> PlanningState:
        """Load the state from a JSON file."""
        data = json.loads(path.read_text())
        state = cls()
        state.phase = PlanningPhase(data.get("phase", "init"))
        state.started_at = datetime.fromisoformat(data.get("started_at", ""))
        state.updated_at = datetime.fromisoformat(data.get("updated_at", ""))
        state.blocking_issues = data.get("blocking_issues", [])
        # Note: artifacts and iterations would need full reconstruction
        return state


def get_planning_state_path(project_root: Path) -> Path:
    """Get the path to the planning state file.

    Args:
        project_root: Root directory of the project.

    Returns:
        Path to the planning state file.
    """
    return project_root / PLANNING_STATE_FILE


def load_planning_state(project_root: Path) -> PlanningState:
    """Load the planning state from disk.

    Args:
        project_root: Root directory of the project.

    Returns:
        PlanningState object (creates new one if file doesn't exist).
    """
    state_path = get_planning_state_path(project_root)
    if state_path.exists():
        return PlanningState.from_file(state_path)
    return PlanningState()


def save_planning_state(project_root: Path, state: PlanningState) -> None:
    """Save the planning state to disk.

    Args:
        project_root: Root directory of the project.
        state: PlanningState to save.
    """
    state_path = get_planning_state_path(project_root)
    state.to_file(state_path)


def get_artifact_path(project_root: Path, artifact_type: ArtifactType) -> Path:
    """Get the file path for an artifact type.

    Args:
        project_root: Root directory of the project.
        artifact_type: Type of artifact.

    Returns:
        Path to the artifact file.
    """
    paths = {
        ArtifactType.INTENT: INTENT_FILE,
        ArtifactType.ARCHITECTURE: ARCHITECTURE_FILE,
        ArtifactType.USER_STORIES: USER_STORIES_FILE,
        ArtifactType.RELEASE: RELEASE_FILE,
        ArtifactType.TASKS: TASKS_FILE,
    }
    return project_root / paths[artifact_type]


def ensure_docs_dir(project_root: Path) -> Path:
    """Ensure the docs directory exists.

    Args:
        project_root: Root directory of the project.

    Returns:
        Path to the docs directory.
    """
    docs_path = project_root / DOCS_DIR
    docs_path.mkdir(parents=True, exist_ok=True)
    return docs_path


def load_background_context(project_root: Path) -> list[dict[str, str]]:
    """Load background context files from docs/background/.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of dicts with 'name' and 'content' keys.
    """
    background_path = project_root / BACKGROUND_DIR
    if not background_path.exists():
        return []

    context_files: list[dict[str, str]] = []
    for file_path in sorted(background_path.glob("*.md")):
        try:
            content = file_path.read_text()
            context_files.append({"name": file_path.name, "content": content})
        except OSError:
            continue

    return context_files


def validate_intent(content: str) -> ValidationResult:
    """Validate INTENT.md content.

    Args:
        content: Content of the INTENT.md file.

    Returns:
        ValidationResult with any issues found.
    """
    issues: list[ValidationIssue] = []

    if not content.strip():
        issues.append(
            ValidationIssue(
                severity="error",
                message="INTENT.md is empty",
            )
        )
        return ValidationResult(valid=False, issues=issues)

    # Check for required sections
    content_lower = content.lower()
    for section in INTENT_REQUIRED_SECTIONS:
        # Match 1-3 # characters followed by optional whitespace and section name
        section_pattern = rf"^#{{1,3}}\s*{re.escape(section.lower())}\b"
        if not re.search(section_pattern, content_lower, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=f"Missing required section: '{section}'",
                    section=section,
                )
            )

    # Check minimum content length
    if len(content.strip()) < 100:
        issues.append(
            ValidationIssue(
                severity="warning",
                message="INTENT.md seems too short. Consider adding more detail.",
            )
        )

    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
    )


def validate_architecture(content: str) -> ValidationResult:
    """Validate ARCHITECTURE.md content.

    Args:
        content: Content of the ARCHITECTURE.md file.

    Returns:
        ValidationResult with any issues found.
    """
    issues: list[ValidationIssue] = []

    if not content.strip():
        issues.append(
            ValidationIssue(
                severity="error",
                message="ARCHITECTURE.md is empty",
            )
        )
        return ValidationResult(valid=False, issues=issues)

    # Check for required sections
    content_lower = content.lower()
    for section in ARCHITECTURE_REQUIRED_SECTIONS:
        # Match 1-3 # characters followed by optional whitespace and section name
        section_pattern = rf"^#{{1,3}}\s*{re.escape(section.lower())}\b"
        if not re.search(section_pattern, content_lower, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=f"Missing required section: '{section}'",
                    section=section,
                )
            )

    # Check for data flow diagram (mermaid or description)
    if "data flow" not in content_lower and "dataflow" not in content_lower:
        issues.append(
            ValidationIssue(
                severity="error",
                message="Missing data flow section",
                section="Data Flow",
            )
        )

    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
    )


def validate_user_stories(content: str) -> ValidationResult:
    """Validate USER_STORIES.md content.

    Args:
        content: Content of the USER_STORIES.md file.

    Returns:
        ValidationResult with any issues found.
    """
    issues: list[ValidationIssue] = []

    if not content.strip():
        issues.append(
            ValidationIssue(
                severity="error",
                message="USER_STORIES.md is empty",
            )
        )
        return ValidationResult(valid=False, issues=issues)

    # Check for story format (US-XXX pattern)
    story_pattern = re.compile(r"US-\d{3}", re.IGNORECASE)
    if not story_pattern.search(content):
        issues.append(
            ValidationIssue(
                severity="error",
                message="No user stories found (expected US-XXX format)",
            )
        )

    # Check for tier assignments
    if not TIER_PATTERN.search(content):
        issues.append(
            ValidationIssue(
                severity="error",
                message="No tier assignments found (expected Tier 1/2/3 or T1/T2/T3)",
            )
        )

    # Check for acceptance criteria
    if "acceptance" not in content.lower() and "criteria" not in content.lower():
        issues.append(
            ValidationIssue(
                severity="warning",
                message="No acceptance criteria section found",
            )
        )

    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
    )


def validate_artifact(
    artifact_type: ArtifactType, content: str
) -> ValidationResult:
    """Validate a planning artifact.

    Args:
        artifact_type: Type of artifact to validate.
        content: Content of the artifact.

    Returns:
        ValidationResult with any issues found.
    """
    validators = {
        ArtifactType.INTENT: validate_intent,
        ArtifactType.ARCHITECTURE: validate_architecture,
        ArtifactType.USER_STORIES: validate_user_stories,
    }

    validator = validators.get(artifact_type)
    if validator:
        return validator(content)

    # For release.json and tasks.json, validate JSON structure
    if artifact_type in (ArtifactType.RELEASE, ArtifactType.TASKS):
        return validate_json_artifact(content, artifact_type)

    return ValidationResult(valid=True, issues=[])


def validate_json_artifact(
    content: str, artifact_type: ArtifactType
) -> ValidationResult:
    """Validate a JSON planning artifact.

    Args:
        content: JSON content to validate.
        artifact_type: Type of artifact.

    Returns:
        ValidationResult with any issues found.
    """
    issues: list[ValidationIssue] = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        issues.append(
            ValidationIssue(
                severity="error",
                message=f"Invalid JSON: {e}",
            )
        )
        return ValidationResult(valid=False, issues=issues)

    if artifact_type == ArtifactType.RELEASE:
        if not isinstance(data, dict):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="release.json must be an object",
                )
            )
        elif "stories" not in data:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="release.json must have 'stories' key",
                )
            )

    elif artifact_type == ArtifactType.TASKS:
        if not isinstance(data, dict):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="tasks.json must be an object",
                )
            )
        elif "tasks" not in data:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="tasks.json must have 'tasks' key",
                )
            )

    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
    )


def check_feature_islands(stories: list[dict[str, Any]]) -> list[GuardrailIssue]:
    """Check for feature islands (stories with no dependencies that should have them).

    Feature islands are stories that:
    - Have no dependencies (depends_on is empty)
    - Are not tier 1 stories
    - Have related keywords suggesting they build on other features

    Args:
        stories: List of story dictionaries.

    Returns:
        List of guardrail issues for feature islands.
    """
    issues: list[GuardrailIssue] = []

    # Keywords suggesting a story builds on others
    dependent_keywords = [
        "extend",
        "enhance",
        "improve",
        "add to",
        "build on",
        "integrate",
        "connect",
    ]

    for story in stories:
        story_id = story.get("id", "")
        depends_on = story.get("depends_on", [])
        title = story.get("title", "").lower()
        tier = story.get("tier", 3)

        # Skip tier 1 stories - they can be independent
        if tier == 1:
            continue

        # If story has no dependencies but title suggests it should
        if not depends_on:
            for keyword in dependent_keywords:
                if keyword in title:
                    issues.append(
                        GuardrailIssue(
                            guardrail="feature_islands",
                            severity="warning",
                            message=(
                                f"Story {story_id} may be a feature island: "
                                f"uses '{keyword}' but has no dependencies"
                            ),
                            affected_items=[story_id],
                        )
                    )
                    break

    return issues


def check_priority_inversion(stories: list[dict[str, Any]]) -> list[GuardrailIssue]:
    """Check for priority inversions (high-priority depends on low-priority).

    Args:
        stories: List of story dictionaries.

    Returns:
        List of guardrail issues for priority inversions.
    """
    issues: list[GuardrailIssue] = []

    # Build priority map
    priority_map = {s.get("id"): s.get("priority", 0) for s in stories}

    for story in stories:
        story_id = story.get("id", "")
        story_priority = story.get("priority", 0)
        depends_on = story.get("depends_on", [])

        for dep_id in depends_on:
            dep_priority = priority_map.get(dep_id, 0)
            # Higher priority number means lower actual priority
            if dep_priority > story_priority:
                msg = (
                    f"Priority inversion: {story_id} (priority {story_priority}) "
                    f"depends on {dep_id} (priority {dep_priority})"
                )
                issues.append(
                    GuardrailIssue(
                        guardrail="priority_inversion",
                        severity="error",
                        message=msg,
                        affected_items=[story_id, dep_id],
                    )
                )

    return issues


def check_circular_dependencies(stories: list[dict[str, Any]]) -> list[GuardrailIssue]:
    """Check for circular dependencies between stories.

    Args:
        stories: List of story dictionaries.

    Returns:
        List of guardrail issues for circular dependencies.
    """
    issues: list[GuardrailIssue] = []

    # Build dependency graph
    deps: dict[str, list[str]] = {}
    for story in stories:
        story_id = story.get("id", "")
        deps[story_id] = story.get("depends_on", [])

    # DFS to detect cycles
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str, path: list[str]) -> list[str] | None:
        if node in rec_stack:
            # Found cycle, return the cycle path
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]
        if node in visited:
            return None

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for dep in deps.get(node, []):
            result = has_cycle(dep, path)
            if result:
                return result

        path.pop()
        rec_stack.remove(node)
        return None

    for story_id in deps:
        if story_id not in visited:
            cycle = has_cycle(story_id, [])
            if cycle:
                issues.append(
                    GuardrailIssue(
                        guardrail="circular_dependencies",
                        severity="error",
                        message=f"Circular dependency detected: {' -> '.join(cycle)}",
                        affected_items=cycle,
                    )
                )
                break  # Report only first cycle found

    return issues


def check_integration_story_dependencies(
    stories: list[dict[str, Any]],
) -> list[GuardrailIssue]:
    """Check that all US-* stories depend on IS-001.

    This guardrail ensures feature stories don't bypass the integration
    validation, preventing disconnected feature islands.

    Args:
        stories: List of story dictionaries.

    Returns:
        List of GuardrailIssue objects for any violations.
    """
    issues: list[GuardrailIssue] = []

    # Find integration story IDs
    integration_ids = {
        story.get("id", "").upper()
        for story in stories
        if story.get("id", "").upper().startswith("IS-")
    }

    if not integration_ids:
        # No integration story exists - this is caught by validate_release
        return issues

    # Check each US-* story
    for story in stories:
        story_id = story.get("id", "")
        if not story_id.upper().startswith("US-"):
            continue

        depends_on = story.get("depends_on", [])
        if not isinstance(depends_on, list):
            depends_on = []

        # Normalize to uppercase for comparison
        depends_on_upper = {d.upper() for d in depends_on if isinstance(d, str)}

        # Check if story depends on at least one integration story
        if not depends_on_upper.intersection(integration_ids):
            issues.append(
                GuardrailIssue(
                    guardrail="integration_dependency",
                    severity="warning",
                    message=(
                        f"Story {story_id} does not depend on integration story. "
                        f"Add 'IS-001' to depends_on to ensure proper sequencing."
                    ),
                    affected_items=[story_id],
                )
            )

    return issues


def run_guardrails(
    stories: list[dict[str, Any]],
    check_integration_deps: bool = True,
) -> list[GuardrailIssue]:
    """Run all planning guardrails on stories.

    Args:
        stories: List of story dictionaries.
        check_integration_deps: Whether to check integration story dependencies.

    Returns:
        List of all guardrail issues found.
    """
    all_issues: list[GuardrailIssue] = []

    all_issues.extend(check_feature_islands(stories))
    all_issues.extend(check_priority_inversion(stories))
    all_issues.extend(check_circular_dependencies(stories))

    # Check that US-* stories depend on IS-* (if enabled)
    if check_integration_deps:
        all_issues.extend(check_integration_story_dependencies(stories))

    return all_issues


def parse_stories_from_markdown(content: str) -> list[dict[str, Any]]:
    """Parse user stories from markdown content.

    Args:
        content: Markdown content with user stories.

    Returns:
        List of story dictionaries.
    """
    stories: list[dict[str, Any]] = []

    # Pattern to match story blocks (## US-XXX: Title)
    story_pattern = re.compile(
        r"##\s*(US-\d{3}):\s*(.+?)(?=\n##\s*US-|\Z)",
        re.DOTALL | re.IGNORECASE,
    )

    for match in story_pattern.finditer(content):
        story_id = match.group(1).upper()
        story_block = match.group(2)

        # Extract tier
        tier_match = TIER_PATTERN.search(story_block)
        tier = int(tier_match.group(1)) if tier_match else 3

        # Extract priority
        priority_pattern = re.compile(r"Priority:\s*(\d+)", re.IGNORECASE)
        priority_match = priority_pattern.search(story_block)
        priority = int(priority_match.group(1)) if priority_match else tier

        # Extract title from first line
        lines = story_block.strip().split("\n")
        title = lines[0].strip() if lines else ""

        # Extract depends_on
        dep_regex = r"Depends\s*on:\s*(US-\d{3}(?:\s*,\s*US-\d{3})*)"
        depends_pattern = re.compile(dep_regex, re.IGNORECASE)
        depends_match = depends_pattern.search(story_block)
        depends_on: list[str] = []
        if depends_match:
            deps_str = depends_match.group(1)
            depends_on = [d.strip().upper() for d in deps_str.split(",")]

        stories.append({
            "id": story_id,
            "title": title,
            "tier": tier,
            "priority": priority,
            "depends_on": depends_on,
        })

    return stories


def parse_goals_from_intent(content: str) -> list[str]:
    """Parse goals from INTENT.md content.

    Extracts goals from the Goals section of INTENT.md.

    Args:
        content: Markdown content of INTENT.md

    Returns:
        List of goal descriptions
    """
    goals: list[str] = []

    # Find the Goals section
    goals_match = re.search(
        r"##\s*Goals\s*\n(.*?)(?=\n##\s*|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )

    if not goals_match:
        return goals

    goals_section = goals_match.group(1)

    # Extract numbered goals (1. Goal text, 2. Goal text, etc.)
    goal_pattern = re.compile(r"^\s*\d+\.\s*(.+?)$", re.MULTILINE)

    for match in goal_pattern.finditer(goals_section):
        goal_text = match.group(1).strip()
        if goal_text:
            goals.append(goal_text)

    return goals


def parse_features_from_intent(content: str) -> list[str]:
    """Parse features from INTENT.md content.

    Extracts feature descriptions from the Features section.

    Args:
        content: Markdown content of INTENT.md

    Returns:
        List of feature descriptions
    """
    features: list[str] = []

    # Find the Features section
    features_match = re.search(
        r"##\s*Features\s*\n(.*?)(?=\n##\s*|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )

    if not features_match:
        return features

    features_section = features_match.group(1)

    # Extract feature blocks (## Feature: Title, ### Sub-features, etc.)
    # Match lines starting with "**" for feature titles
    feature_pattern = re.compile(r"^\s*\*\*(.+?)\*\*:\s*(.+?)$", re.MULTILINE)

    for match in feature_pattern.finditer(features_section):
        feature_name = match.group(1).strip()
        feature_desc = match.group(2).strip()
        if feature_name:
            features.append(f"{feature_name}: {feature_desc}")

    # If no bold features found, try extracting numbered list items
    if not features:
        feat_list_pattern = re.compile(r"^\s*\d+\.\s*\*\*(.+?)\*\*(.+?)$", re.MULTILINE)
        for match in feat_list_pattern.finditer(features_section):
            feature_text = match.group(1).strip() + match.group(2).strip()
            if feature_text:
                features.append(feature_text)

    return features


def decompose_goal_tree(intent_content: str) -> GoalTree:
    """Decompose INTENT.md into a Goal Tree hierarchy.

    Creates a hierarchical Goal Tree with Goals at the top level,
    decomposed into Critical Success Factors (CSFs), Necessary Conditions (NCs),
    Strategic Objectives (SOs), and Features.

    Args:
        intent_content: Content of INTENT.md file

    Returns:
        Populated GoalTree object
    """
    tree = GoalTree()
    goals = parse_goals_from_intent(intent_content)
    features = parse_features_from_intent(intent_content)

    # Create goal nodes at top level
    goal_ids: list[str] = []
    for idx, goal_text in enumerate(goals, 1):
        goal_id = f"G-{idx:03d}"
        goal_node = GoalTreeNode(
            identifier=goal_id,
            level=GoalLevel.GOAL,
            title=goal_text[:100],  # Truncate long titles
            description=goal_text,
        )
        tree.add_node(goal_node)
        goal_ids.append(goal_id)

    # Decompose each goal into CSFs
    csf_counter = 1
    goal_to_csfs: dict[str, list[str]] = {}

    for goal_id in goal_ids:
        csfs_for_goal: list[str] = []

        # Create 2-3 CSFs per goal
        num_csfs = 2 if len(goal_ids) > 1 else 3
        for i in range(num_csfs):
            csf_id = f"CSF-{csf_counter:03d}"
            csf_node = GoalTreeNode(
                identifier=csf_id,
                level=GoalLevel.CSF,
                title=f"Critical Success Factor {csf_counter}",
                description=f"CSF for {goal_id}",
                parent_id=goal_id,
            )
            tree.add_node(csf_node)
            csfs_for_goal.append(csf_id)
            csf_counter += 1

        goal_to_csfs[goal_id] = csfs_for_goal

        # Update parent goal's children
        goal_node = tree.get_node(goal_id)
        if goal_node:
            goal_node.children_ids = csfs_for_goal

    # Decompose CSFs into NCs
    nc_counter = 1
    csf_to_ncs: dict[str, list[str]] = {}

    for goal_id, csf_ids in goal_to_csfs.items():
        for csf_id in csf_ids:
            ncs_for_csf: list[str] = []

            # Create 2-3 NCs per CSF
            for i in range(2):
                nc_id = f"NC-{nc_counter:03d}"
                nc_node = GoalTreeNode(
                    identifier=nc_id,
                    level=GoalLevel.NC,
                    title=f"Necessary Condition {nc_counter}",
                    description=f"NC for {csf_id}",
                    parent_id=csf_id,
                )
                tree.add_node(nc_node)
                ncs_for_csf.append(nc_id)
                nc_counter += 1

            csf_to_ncs[csf_id] = ncs_for_csf

            # Update CSF's children
            csf_node = tree.get_node(csf_id)
            if csf_node:
                csf_node.children_ids = ncs_for_csf

    # Map features to NCs (distribute features across NCs)
    feature_counter = 1
    nc_list = list(csf_to_ncs.values())
    nc_idx = 0

    for feature_text in features:
        feature_id = f"FT-{feature_counter:03d}"

        # Find the next NC to attach this feature to
        if nc_list:
            nc_id = nc_list[nc_idx % len(nc_list)][0]
        else:
            # Fallback: attach to first goal if no NCs
            nc_id = goal_ids[0] if goal_ids else None

        if nc_id:
            parent_id = nc_id
        else:
            parent_id = None

        feature_node = GoalTreeNode(
            identifier=feature_id,
            level=GoalLevel.FEATURE,
            title=feature_text[:100],
            description=feature_text,
            parent_id=parent_id,
        )
        tree.add_node(feature_node)

        # Update parent NC's children
        if parent_id:
            parent_node = tree.get_node(parent_id)
            if parent_node:
                parent_node.children_ids.append(feature_id)

        feature_counter += 1
        nc_idx += 1

    return tree


def create_planning_artifact(
    project_root: Path,
    artifact_type: ArtifactType,
    content: str,
) -> PlanningArtifact:
    """Create a planning artifact file.

    Args:
        project_root: Root directory of the project.
        artifact_type: Type of artifact to create.
        content: Content for the artifact.

    Returns:
        PlanningArtifact representing the created file.
    """
    artifact_path = get_artifact_path(project_root, artifact_type)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(content)

    return PlanningArtifact(
        artifact_type=artifact_type,
        path=str(artifact_path.relative_to(project_root)),
    )


def load_artifact_content(
    project_root: Path, artifact_type: ArtifactType
) -> str:
    """Load the content of a planning artifact.

    Args:
        project_root: Root directory of the project.
        artifact_type: Type of artifact to load.

    Returns:
        Content of the artifact file.

    Raises:
        ArtifactNotFoundError: If the artifact file doesn't exist.
    """
    artifact_path = get_artifact_path(project_root, artifact_type)
    if not artifact_path.exists():
        raise ArtifactNotFoundError(
            f"Artifact {artifact_type.value} not found at {artifact_path}"
        )
    return artifact_path.read_text()


def update_artifact(
    project_root: Path,
    artifact_type: ArtifactType,
    content: str,
    state: PlanningState,
) -> PlanningArtifact:
    """Update a planning artifact with new content.

    Args:
        project_root: Root directory of the project.
        artifact_type: Type of artifact to update.
        content: New content for the artifact.
        state: Current planning state.

    Returns:
        Updated PlanningArtifact.
    """
    artifact_path = get_artifact_path(project_root, artifact_type)
    artifact_path.write_text(content)

    artifact = PlanningArtifact(
        artifact_type=artifact_type,
        path=str(artifact_path.relative_to(project_root)),
    )

    state.add_artifact(artifact)
    save_planning_state(project_root, state)

    return artifact


def record_review_iteration(
    project_root: Path,
    state: PlanningState,
    artifact_type: ArtifactType,
    agent: str,
    feedback: str,
    issues_found: int,
    fixes_applied: bool,
    duration_ms: int,
) -> ReviewIteration:
    """Record a review iteration in the planning state.

    Args:
        project_root: Root directory of the project.
        state: Current planning state.
        artifact_type: Type of artifact reviewed.
        agent: Agent that performed the review.
        feedback: AI feedback from the review.
        issues_found: Number of issues found.
        fixes_applied: Whether fixes were applied.
        duration_ms: Time taken for the review.

    Returns:
        The created ReviewIteration.
    """
    iteration = ReviewIteration(
        iteration_number=state.current_iteration + 1,
        agent=agent,
        artifact_type=artifact_type,
        feedback=feedback,
        issues_found=issues_found,
        fixes_applied=fixes_applied,
        duration_ms=duration_ms,
    )

    state.add_review_iteration(iteration)
    save_planning_state(project_root, state)

    return iteration
