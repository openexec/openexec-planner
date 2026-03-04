"""Tests for task scheduler."""

import pytest
from openexec_orchestration.scheduler import Scheduler, Task


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
