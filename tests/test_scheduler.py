"""Tests for task scheduler."""

from openexec_planner.scheduler import Scheduler, Task


class TestScheduler:
    """Tests for Task Scheduler."""

    def test_schedule_orders_by_dependency(self):
        """Test that tasks are ordered correctly based on depends_on."""
        tasks = [
            Task(id="T2", title="Task 2", depends_on=["T1"]),
            Task(id="T1", title="Task 1", depends_on=[]),
        ]

        scheduler = Scheduler()
        schedule = scheduler.schedule({"tasks": tasks})

        task_ids = [t["id"] for t in schedule["tasks"]]
        assert task_ids == ["T1", "T2"]

    def test_schedule_handles_multiple_dependencies(self):
        """Test complex dependency chains."""
        tasks = [
            Task(id="T3", title="Task 3", depends_on=["T1", "T2"]),
            Task(id="T2", title="Task 2", depends_on=["T1"]),
            Task(id="T1", title="Task 1", depends_on=[]),
        ]

        scheduler = Scheduler()
        schedule = scheduler.schedule({"tasks": tasks})

        task_ids = [t["id"] for t in schedule["tasks"]]
        assert task_ids == ["T1", "T2", "T3"]

    def test_estimate_hours(self):
        """Test hour estimation based on keywords."""
        scheduler = Scheduler()
        assert scheduler._estimate_hours("Design API") == 2.0
        assert scheduler._estimate_hours("Implement UI") == 4.0
        assert scheduler._estimate_hours("Test feature") == 3.0
        assert scheduler._estimate_hours("Document code") == 1.0
        assert scheduler._estimate_hours("Random task") == 4.0

    def test_topological_sort_with_cycle(self):
        """Test that circular dependencies don't crash and return all tasks."""
        tasks = [
            Task(id="T1", title="Task 1", depends_on=["T2"]),
            Task(id="T2", title="Task 2", depends_on=["T1"]),
        ]

        scheduler = Scheduler()
        sorted_tasks = scheduler._topological_sort(tasks)

        # Should still contain both tasks even if order is broken by cycle
        assert len(sorted_tasks) == 2
        ids = [t.id for t in sorted_tasks]
        assert "T1" in ids
        assert "T2" in ids

    def test_extract_tasks_from_tree(self):
        """Test extracting tasks from a nested goal tree."""
        tree = {"goal": "Root", "children": [{"goal": "Sub1", "children": [{"task": "T1"}]}]}

        scheduler = Scheduler()
        tasks = scheduler._extract_tasks_from_tree(tree)

        assert len(tasks) == 1
        assert tasks[0].id == "T1"
        assert "Root" in tasks[0].title
        assert "Sub1" in tasks[0].title

    def test_calculate_schedule_phases(self):
        """Test grouping tasks into sequential phases."""
        tasks = [
            Task(id="T1", title="T1", depends_on=[], estimated_hours=2.0),
            Task(id="T2", title="T2", depends_on=["T1"], estimated_hours=2.0),
        ]

        scheduler = Scheduler()
        schedule = scheduler._calculate_schedule(tasks)

        assert len(schedule["phases"]) == 2  # T2 depends on T1, must be in new phase
        assert schedule["total_hours"] == 4.0
        assert schedule["phases"][0]["tasks"][0]["id"] == "T1"
        assert schedule["phases"][1]["tasks"][0]["id"] == "T2"
