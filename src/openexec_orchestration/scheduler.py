"""Task scheduling based on depends_on."""

from typing import Any
from dataclasses import dataclass, asdict


@dataclass
class Task:
    """Scheduled task."""

    id: str
    title: str
    depends_on: list[str]
    estimated_hours: float = 4.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class Scheduler:
    """Schedules tasks based on depends_on."""

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
        elif isinstance(data, dict):
            if "stories" in data:
                tasks = self._extract_tasks_from_stories(data["stories"])
            elif "tasks" in data:
                # If they are already Task objects or dicts representing tasks
                raw_tasks = data["tasks"]
                tasks = []
                for t in raw_tasks:
                    if isinstance(t, Task):
                        tasks.append(t)
                    elif isinstance(t, dict):
                        tasks.append(Task(
                            id=t.get("id", ""),
                            title=t.get("title", ""),
                            depends_on=t.get("depends_on", []),
                            estimated_hours=t.get("estimated_hours", 4.0)
                        ))
            elif "goal" in data:
                tasks = self._extract_tasks_from_tree(data)
            else:
                tasks = []
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
        
        # Track last task of each story for dependency inheritance
        story_last_tasks = {}

        for story in stories:
            story_id = story.get("id", "US-???")
            story_title = story.get("title", "Untitled")
            
            # Story-level depends_on (IDs of other stories)
            story_deps = story.get("depends_on", [])

            # Create tasks from story tasks
            story_tasks = story.get("tasks", [])
            prev_task_id = None

            for i, task_data in enumerate(story_tasks, 1):
                # Handle both structured (dict) and simple (string) tasks
                if isinstance(task_data, dict):
                    task_id = task_data.get("id", f"{story_id}-T{i}")
                    task_title_raw = task_data.get("title", f"Task {i}")
                    # Use provided depends_on
                    deps = task_data.get("depends_on", [])
                    
                    # Inheritance logic:
                    # Every task in this story should depend on the last tasks of the dependent stories
                    if story_deps:
                        for s_dep in story_deps:
                            last_tid = story_last_tasks.get(s_dep)
                            if last_tid and last_tid not in deps:
                                deps.append(last_tid)
                                
                    # Also sequential execution within story if i > 1
                    if i > 1 and prev_task_id and prev_task_id not in deps:
                        deps.append(prev_task_id)
                else:
                    # Fallback for simple string tasks
                    task_id = f"{story_id}-T{i}"
                    task_title_raw = task_data
                    deps = [prev_task_id] if prev_task_id else []
                    
                    # Inherit story-level deps
                    if story_deps:
                        for s_dep in story_deps:
                            last_tid = story_last_tasks.get(s_dep)
                            if last_tid and last_tid not in deps:
                                deps.append(last_tid)

                task = Task(
                    id=task_id,
                    title=f"{story_title}: {task_title_raw}",
                    depends_on=deps,
                    estimated_hours=self._estimate_hours(task_title_raw),
                )
                tasks.append(task)
                prev_task_id = task_id
                story_last_tasks[story_id] = task_id

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
                depends_on=[],
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
        """Sort tasks by depends_on (topological sort)."""
        if not tasks:
            return []

        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        
        # Build adjacency list and initial in-degree (only for internal tasks)
        adj = {t.id: [] for t in tasks}
        in_degree = {t.id: 0 for t in tasks}
        
        for t in tasks:
            for dep in t.depends_on:
                if dep in task_map:
                    adj[dep].append(t.id)
                    in_degree[t.id] += 1

        # Find tasks with no INTERNAL depends_on
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            # Sort queue to ensure deterministic order (e.g. by ID)
            queue.sort()
            current = queue.pop(0)
            result.append(task_map[current])

            # Update in-degrees for dependent tasks
            for neighbor in adj.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add any remaining tasks (circular depends_on or orphaned)
        # This should ideally be empty in a perfect DAG
        remaining_ids = set(task_map.keys()) - set(t.id for t in result)
        if remaining_ids:
            remaining = [task_map[tid] for tid in sorted(list(remaining_ids))]
            result.extend(remaining)

        return result

    def _calculate_schedule(self, tasks: list[Task]) -> dict[str, Any]:
        """Calculate schedule with phases and timeline."""
        if not tasks:
            return {"phases": [], "total_hours": 0, "tasks": []}

        # Build full task map for lookups
        task_map = {t.id: t for t in tasks}

        # Group into phases
        phases = []
        current_phase = []
        current_deps = set()

        for task in tasks:
            # Start new phase if task depends on something in current phase
            # OR if we just want a fresh start. 
            # For simplicity in large sets, we could limit phase size.
            needs_new_phase = False
            for dep in task.depends_on:
                if dep in current_deps:
                    needs_new_phase = True
                    break
            
            if needs_new_phase:
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
        
        # FLAT TASKS: Must include ALL tasks from the input, correctly formatted
        flat_tasks = []
        for t in tasks:
            d = t.to_dict()
            d["status"] = "pending"
            d["kind"] = "task"
            flat_tasks.append(d)

        for i, phase_tasks in enumerate(phases, 1):
            phase_hours = sum(t.estimated_hours for t in phase_tasks)
            phase_tasks_dicts = []
            for t in phase_tasks:
                d = t.to_dict()
                d["status"] = "pending"
                d["kind"] = "task"
                phase_tasks_dicts.append(d)
                
            phase_output.append({
                "phase": i,
                "name": f"Phase {i}",
                "hours": phase_hours,
                "tasks": phase_tasks_dicts,
            })

        return {
            "phases": phase_output,
            "total_hours": total_hours,
            "task_count": len(tasks),
            "phase_count": len(phases),
            "tasks": flat_tasks, # Flat list for execution engine
        }
