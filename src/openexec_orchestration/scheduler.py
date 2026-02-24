"""Task scheduling based on dependencies."""

from typing import Any
from dataclasses import dataclass, asdict


@dataclass
class Task:
    """Scheduled task."""

    id: str
    title: str
    dependencies: list[str]
    estimated_hours: float = 4.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class Scheduler:
    """Schedules tasks based on dependencies."""

    def schedule(self, data: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        """Schedule tasks in execution order.

        Args:
            data: List of stories or a goal tree

        Returns:
            Schedule with tasks in topologically sorted order
        """
        # Extract tasks from stories
        if isinstance(data, list):
            tasks = self._extract_tasks_from_stories(data)
        elif isinstance(data, dict) and "goal" in data:
            tasks = self._extract_tasks_from_tree(data)
        else:
            tasks = []

        # Build dependency graph and sort
        sorted_tasks = self._topological_sort(tasks)

        # Calculate schedule
        schedule = self._calculate_schedule(sorted_tasks)

        return schedule

    def _extract_tasks_from_stories(
        self, stories: list[dict[str, Any]]
    ) -> list[Task]:
        """Extract tasks from story list."""
        tasks = []
        task_num = 1

        for story in stories:
            story_id = story.get("id", f"US-{task_num:03d}")
            story_title = story.get("title", "Untitled")

            # Create tasks from story tasks
            story_tasks = story.get("tasks", [])
            prev_task_id = None

            for i, task_title in enumerate(story_tasks, 1):
                task_id = f"{story_id}-T{i}"
                deps = [prev_task_id] if prev_task_id else []

                task = Task(
                    id=task_id,
                    title=f"{story_title}: {task_title}",
                    dependencies=deps,
                    estimated_hours=self._estimate_hours(task_title),
                )
                tasks.append(task)
                prev_task_id = task_id
                task_num += 1

        return tasks

    def _extract_tasks_from_tree(
        self, tree: dict[str, Any], prefix: str = ""
    ) -> list[Task]:
        """Extract tasks from goal tree."""
        tasks = []

        if "task" in tree:
            task_id = tree["task"]
            task = Task(
                id=task_id,
                title=f"Implement {prefix}".strip(),
                dependencies=[],
                estimated_hours=4.0,
            )
            tasks.append(task)
        elif "children" in tree:
            goal = tree.get("goal", "")
            new_prefix = f"{prefix} > {goal}".strip(" >")
            for child in tree["children"]:
                tasks.extend(self._extract_tasks_from_tree(child, new_prefix))

        return tasks

    def _estimate_hours(self, task_title: str) -> float:
        """Estimate hours for a task based on keywords."""
        title_lower = task_title.lower()

        if "design" in title_lower or "plan" in title_lower:
            return 2.0
        if "test" in title_lower:
            return 3.0
        if "document" in title_lower:
            return 1.0
        if "implement" in title_lower or "build" in title_lower:
            return 4.0

        return 4.0  # Default

    def _topological_sort(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by dependencies (topological sort)."""
        if not tasks:
            return []

        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: len(t.dependencies) for t in tasks}

        # Find tasks with no dependencies
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            if current in task_map:
                result.append(task_map[current])

            # Update in-degrees for dependent tasks
            for task in tasks:
                if current in task.dependencies:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)

        # Add any remaining tasks (circular dependencies)
        remaining = [t for t in tasks if t not in result]
        result.extend(remaining)

        return result

    def _calculate_schedule(self, tasks: list[Task]) -> dict[str, Any]:
        """Calculate schedule with phases and timeline."""
        if not tasks:
            return {"phases": [], "total_hours": 0, "tasks": []}

        # Group into phases
        phases = []
        current_phase = []
        current_deps = set()

        for task in tasks:
            # Start new phase if task depends on something in current phase
            if any(dep in current_deps for dep in task.dependencies):
                if current_phase:
                    phases.append(current_phase)
                current_phase = []
                current_deps = set()

            current_phase.append(task)
            current_deps.add(task.id)

        if current_phase:
            phases.append(current_phase)

        # Build output
        total_hours = sum(t.estimated_hours for t in tasks)
        phase_output = []

        for i, phase_tasks in enumerate(phases, 1):
            phase_hours = sum(t.estimated_hours for t in phase_tasks)
            phase_output.append({
                "phase": i,
                "name": f"Phase {i}",
                "hours": phase_hours,
                "tasks": [t.to_dict() for t in phase_tasks],
            })

        return {
            "phases": phase_output,
            "total_hours": total_hours,
            "task_count": len(tasks),
            "phase_count": len(phases),
        }
