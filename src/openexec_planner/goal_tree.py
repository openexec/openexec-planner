"""Goal tree building and visualization."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GoalNode:
    """Node in goal tree."""

    goal: str
    children: list["GoalNode"] = field(default_factory=list)
    task_id: str | None = None

    def __post_init__(self) -> None:
        """Handle non-string goal inputs."""
        if isinstance(self.goal, dict):
            self.goal = self.goal.get("title") or self.goal.get("goal") or str(self.goal)
        elif not isinstance(self.goal, str):
            self.goal = str(self.goal)

    def print(self, indent: int = 0) -> None:
        """Print goal tree."""
        prefix = "  " * indent
        if self.task_id:
            print(f"{prefix}Task: {self.task_id}")
        else:
            print(f"{prefix}Goal: {self.goal}")
            for child in self.children:
                child.print(indent + 1)


@dataclass
class GoalTree:
    """Hierarchical goal structure."""

    root: GoalNode

    def print(self) -> None:
        """Print the goal tree."""
        self.root.print()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self._node_to_dict(self.root)

    def _node_to_dict(self, node: GoalNode) -> dict[str, Any]:
        """Convert node to dictionary recursively."""
        if node.task_id:
            return {"task": node.task_id}
        return {
            "goal": node.goal,
            "children": [self._node_to_dict(c) for c in node.children],
        }


class GoalTreeBuilder:
    """Builds goal trees from intent."""

    def __init__(self, max_depth: int = 4) -> None:
        """Initialize builder.

        Args:
            max_depth: Maximum tree depth
        """
        self.max_depth = max_depth

    def build(self, intent: dict[str, Any]) -> dict[str, Any]:
        """Build goal tree from intent.

        Args:
            intent: Parsed intent from IntentParser

        Returns:
            Hierarchical goal tree as dictionary
        """
        root = GoalNode(goal=intent.get("title", "Project"))

        # Add goals as first-level children
        for i, goal_raw in enumerate(intent.get("goals", []), 1):
            goal_node = GoalNode(goal=goal_raw)
            goal_text = goal_node.goal

            # Find related requirements as sub-goals
            goal_words = set(goal_text.lower().split())
            for req_raw in intent.get("requirements", []):
                req_text = req_raw if isinstance(req_raw, str) else req_raw.get("title", str(req_raw))
                req_words = set(req_text.lower().split())
                if len(goal_words & req_words) >= 2:
                    req_node = GoalNode(goal=req_raw)
                    goal_node.children.append(req_node)

            # Add task placeholder if no children
            if not goal_node.children:
                task_node = GoalNode(goal="", task_id=f"TASK-{i:03d}")
                goal_node.children.append(task_node)

            root.children.append(goal_node)

        # Add any orphan requirements as separate goals
        covered = {c.goal.lower() for g in root.children for c in g.children}
        for i, req_raw in enumerate(intent.get("requirements", []), 100):
            req_text = req_raw if isinstance(req_raw, str) else req_raw.get("title", str(req_raw))
            if req_text.lower() not in covered:
                req_node = GoalNode(
                    goal=req_raw,
                    children=[GoalNode(goal="", task_id=f"TASK-{i:03d}")],
                )
                root.children.append(req_node)

        # Add constraints as annotations
        constraints = intent.get("constraints", [])
        if constraints:
            constraint_node = GoalNode(goal="Constraints")
            for constraint in constraints:
                constraint_node.children.append(GoalNode(goal=f"[Constraint] {constraint}"))
            root.children.append(constraint_node)

        tree = GoalTree(root=root)
        return tree.to_dict()
