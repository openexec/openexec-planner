"""Story generation from intent."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Story:
    """User story with acceptance criteria."""

    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    tasks: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class StoryGenerator:
    """Generates user stories from parsed intent."""

    def generate(self, intent: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate stories from intent.

        Args:
            intent: Parsed intent from IntentParser

        Returns:
            List of user stories as dictionaries
        """
        stories = []
        story_num = 1

        # Generate stories from goals
        for goal in intent.get("goals", []):
            story = self._create_story(
                story_num,
                goal,
                self._extract_acceptance_criteria(goal, intent.get("requirements", [])),
            )
            stories.append(story.to_dict())
            story_num += 1

        # Generate stories from requirements that aren't covered by goals
        covered = {s["title"].lower() for s in stories}
        for req in intent.get("requirements", []):
            if req.lower() not in covered:
                story = self._create_story(
                    story_num,
                    req,
                    self._infer_acceptance_criteria(req),
                )
                stories.append(story.to_dict())
                story_num += 1

        return stories

    def _create_story(
        self, num: int, title: str, acceptance_criteria: list[str]
    ) -> Story:
        """Create a story from title and acceptance criteria."""
        # Clean up the title
        title = title.strip()

        # Generate a description
        description = self._generate_description(title)

        # Generate tasks from title and AC
        tasks = self._generate_tasks(title, acceptance_criteria)

        return Story(
            id=f"US-{num:03d}",
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            tasks=tasks,
        )

    def _generate_description(self, title: str) -> str:
        """Generate a user story description from title."""
        # Convert to lowercase and remove leading verbs
        lower = title.lower()
        for verb in ["implement", "create", "add", "build", "develop", "make"]:
            if lower.startswith(verb):
                lower = lower[len(verb):].strip()
                break

        return f"As a user, I want to {lower}"

    def _extract_acceptance_criteria(
        self, goal: str, requirements: list[str]
    ) -> list[str]:
        """Extract acceptance criteria from related requirements."""
        criteria = []
        goal_words = set(goal.lower().split())

        for req in requirements:
            req_words = set(req.lower().split())
            # Check for word overlap
            if len(goal_words & req_words) >= 2:
                criteria.append(f"Given the feature is implemented, {req}")

        if not criteria:
            # Generate default criteria
            criteria = self._infer_acceptance_criteria(goal)

        return criteria

    def _infer_acceptance_criteria(self, title: str) -> list[str]:
        """Infer acceptance criteria from title."""
        criteria = []

        # Common patterns
        if "api" in title.lower() or "endpoint" in title.lower():
            criteria.append("Given the API is deployed, it returns valid responses")
            criteria.append("Given invalid input, it returns appropriate error codes")

        if "ui" in title.lower() or "interface" in title.lower() or "page" in title.lower():
            criteria.append("Given the page loads, all elements are visible and functional")
            criteria.append("Given user interaction, the UI responds appropriately")

        if "database" in title.lower() or "data" in title.lower():
            criteria.append("Given data is saved, it can be retrieved correctly")
            criteria.append("Given concurrent access, data integrity is maintained")

        if "auth" in title.lower() or "login" in title.lower():
            criteria.append("Given valid credentials, user can authenticate")
            criteria.append("Given invalid credentials, access is denied")

        # Default criteria if none matched
        if not criteria:
            criteria.append(f"Given {title} is implemented, it works as expected")
            criteria.append("Given edge cases, the system handles them gracefully")

        return criteria

    def _generate_tasks(self, title: str, criteria: list[str]) -> list[str]:
        """Generate implementation tasks."""
        tasks = []

        # Design task
        tasks.append(f"Design: Plan implementation for {title}")

        # Implementation task
        tasks.append(f"Implement: Build {title}")

        # Test task
        tasks.append("Test: Verify acceptance criteria")

        # Documentation task if substantial
        if len(criteria) > 2:
            tasks.append(f"Document: Write documentation for {title}")

        return tasks
