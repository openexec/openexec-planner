"""LLM-based story generation from intent documents."""

import json
import os
import re
from typing import Any

# Model mapping
CLAUDE_MODELS = {
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-3-5-haiku-20241022",
}

OPENAI_MODELS = {
    "gpt-5": "gpt-5",
    "gpt-5-codex": "gpt-5-codex",
}

GEMINI_MODELS = {
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3.1-flash-preview": "gemini-3.1-flash-preview",
}

STORY_REVIEW_PROMPT = """You are a senior software architect reviewing generated user stories for implementation readiness.

Your goal is to ensure the stories are SUFFICIENT FOR IMPLEMENTATION - a developer should be able to pick up any task and know exactly what to build.

REVIEW THE STORIES AGAINST THESE CRITERIA:

1. **Requirement Coverage**: Each REQ-XXX in the intent must map to exactly ONE story. No requirements should be missing or buried.

2. **No Redundancy**: Stories should not overlap. If US-001, US-005, and US-010 all cover "basic setup", they must be merged into one.

3. **Quality & Correctness**: No parsing errors, hallucinations, or corrupted titles (e.g., a story titled "**Acceptance Criteria:**" is invalid).

4. **Acceptance Criteria**: Must be extracted from the intent document, not null or generic. These define "done".

5. **Specific Tasks**: Tasks must be technical and actionable:
   - BAD: "Design: Plan implementation", "Implement: Build feature", "Test: Verify"
   - GOOD: "Create Dockerfile with multi-stage build", "Configure docker-compose volumes", "Add health check endpoint"

6. **Technical Completeness**: All technical requirements from the intent must appear as specific tasks.

ORIGINAL INTENT:
{intent}

GENERATED STORIES:
{stories}

Return a JSON object:
{{
  "approved": false,
  "assessment": "The stories are not sufficient for implementation because...",
  "key_issues": [
    {{
      "category": "Redundancy & Fragmentation",
      "description": "There are 12 stories for 4 requirements. US-001, US-005, US-010 all cover the same goal.",
      "examples": ["US-001 and US-010 both cover 'basic setup'"]
    }},
    {{
      "category": "Generic Tasks",
      "description": "All tasks follow 'Design/Implement/Test' template without specifics.",
      "examples": ["US-002 Task 1: 'Implement: Build feature' - what feature? what files?"]
    }}
  ],
  "refactoring_plan": {{
    "goal": "Refactor to align with the N requirements in INTENT.md",
    "proposed_stories": [
      {{
        "story": "Docker Development Environment",
        "maps_to": "REQ-001",
        "tasks": ["Create Dockerfile (dev target)", "Create docker-compose.yml", "Configure hot-reload volumes"]
      }}
    ]
  }}
}}

If stories are good, set approved=true and provide brief positive assessment.

Output ONLY valid JSON, no markdown or explanations."""

STORY_FIX_PROMPT = """You are a software architect fixing user stories based on detailed reviewer feedback.

The reviewer has analyzed the stories and provided a refactoring plan. You MUST follow it.

ORIGINAL INTENT:
{intent}

CURRENT STORIES (problematic):
{stories}

REVIEWER ANALYSIS AND REFACTORING PLAN:
{feedback}

YOUR TASK:
Follow the reviewer's refactoring_plan exactly. Generate the proposed stories with:
1. One story per requirement as specified
2. Specific, technical tasks as listed in the plan
3. Acceptance criteria extracted from the intent document
4. Proper IDs: US-001, US-002, etc. and T-US-001-001, T-US-001-002, etc.

OUTPUT FORMAT - JSON array:
[
  {{
    "id": "US-001",
    "title": "Story title from refactoring plan",
    "description": "As a developer, I want...",
    "requirement_id": "REQ-001",
    "acceptance_criteria": ["Specific criteria from intent"],
    "tasks": [
      {{
        "id": "T-US-001-001",
        "title": "Specific task from plan",
        "description": "Technical details for implementation"
      }}
    ]
  }}
]

Output ONLY valid JSON array, no markdown or explanations."""

STORY_GENERATION_PROMPT = """You are a software architect generating user stories from an intent document.

Analyze the intent document below and generate a JSON array of user stories.

RULES:
1. Create ONE story per requirement (REQ-XXX) in the document
2. Each story should have specific, actionable tasks (not generic "Design/Implement/Test")
3. Extract acceptance criteria directly from the intent document
4. Use technical, specific task descriptions (e.g., "Create Dockerfile with multi-stage build" not "Implement container")
5. Avoid redundancy - do not create multiple stories for the same functionality
6. Task IDs should follow format: T-US-XXX-YYY where XXX is story number, YYY is task number

OUTPUT FORMAT (JSON array):
[
  {
    "id": "US-001",
    "title": "Docker Development Environment",
    "description": "As a developer, I want a Docker-based development environment so that I can develop locally with hot-reload",
    "requirement_id": "REQ-001",
    "acceptance_criteria": [
      "Container starts with 'docker compose up'",
      "Source code changes trigger automatic rebuild",
      "Node modules are persisted in named volume"
    ],
    "tasks": [
      {
        "id": "T-US-001-001",
        "title": "Create development Dockerfile",
        "description": "Create Dockerfile with development target stage, Node.js base image, and hot-reload support"
      },
      {
        "id": "T-US-001-002",
        "title": "Create docker-compose.yml",
        "description": "Configure docker-compose with volume mounts, port mapping, and environment variables"
      }
    ]
  }
]

INTENT DOCUMENT:
{intent}

Generate the JSON array of stories. Output ONLY valid JSON, no markdown or explanations."""


class LLMStoryGenerator:
    """Generates high-quality user stories using LLM."""

    def __init__(self, model: str = "sonnet"):
        """Initialize generator with model.

        Args:
            model: Model identifier (opus, sonnet, haiku, gpt-5, gemini-3.1-pro-preview, etc.)
        """
        self.model = model
        self.provider = self._detect_provider(model)

    def _detect_provider(self, model: str) -> str:
        """Detect provider from model name."""
        if model in CLAUDE_MODELS:
            return "anthropic"
        elif model in OPENAI_MODELS:
            return "openai"
        elif model in GEMINI_MODELS:
            return "google"
        else:
            # Default to anthropic for unknown models
            return "anthropic"

    def generate(self, intent_content: str) -> list[dict[str, Any]]:
        """Generate stories from intent document.

        Args:
            intent_content: Raw content of the intent document

        Returns:
            List of user stories as dictionaries
        """
        prompt = STORY_GENERATION_PROMPT.format(intent=intent_content)

        if self.provider == "anthropic":
            response = self._call_anthropic(prompt)
        elif self.provider == "openai":
            response = self._call_openai(prompt)
        elif self.provider == "google":
            response = self._call_google(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Parse JSON response
        return self._parse_response(response)

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        model_id = CLAUDE_MODELS.get(self.model, self.model)
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=model_id,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        model_id = OPENAI_MODELS.get(self.model, self.model)
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )

        return response.choices[0].message.content

    def _call_google(self, prompt: str) -> str:
        """Call Google Gemini API."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")

        model_id = GEMINI_MODELS.get(self.model, self.model)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_id)

        response = model.generate_content(prompt)
        return response.text

    def review(
        self,
        stories: list[dict[str, Any]],
        intent_content: str,
        reviewer_model: str,
        max_iterations: int = 3,
    ) -> list[dict[str, Any]]:
        """Review and fix stories in a loop until approved.

        Args:
            stories: Generated stories to review
            intent_content: Original intent document
            reviewer_model: Model to use for review
            max_iterations: Maximum review-fix cycles

        Returns:
            Approved stories
        """
        current_stories = stories

        for iteration in range(max_iterations):
            print(f"  Review iteration {iteration + 1}/{max_iterations}")

            # Get review from reviewer model
            review_result = self._get_review(
                current_stories, intent_content, reviewer_model
            )

            if review_result.get("approved", False):
                assessment = review_result.get("assessment", "Stories are implementation-ready")
                print(f"  ✓ Approved: {assessment}")
                return current_stories

            # Stories rejected - show detailed feedback
            print()
            print(f"  ✗ {review_result.get('assessment', 'Stories need improvement')}")
            print()

            # Show key issues
            key_issues = review_result.get("key_issues", [])
            if key_issues:
                print("  Key Issues Found:")
                for i, issue in enumerate(key_issues, 1):
                    category = issue.get("category", "Issue")
                    desc = issue.get("description", "")
                    print(f"    {i}. {category}: {desc}")
                    for example in issue.get("examples", [])[:2]:
                        print(f"       - {example}")
                print()

            # Show refactoring plan
            plan = review_result.get("refactoring_plan", {})
            if plan:
                print(f"  Proposed Refactoring Plan:")
                print(f"    Goal: {plan.get('goal', 'Align with requirements')}")
                print()
                for proposed in plan.get("proposed_stories", []):
                    story = proposed.get("story", "?")
                    maps_to = proposed.get("maps_to", "?")
                    print(f"    * {story} ({maps_to})")
                    for task in proposed.get("tasks", [])[:3]:
                        print(f"        - {task}")
                print()

            # Fix stories using executor model
            print("  Fixing stories...")
            current_stories = self._fix_stories(
                current_stories, intent_content, review_result
            )

        print(f"  ! Max iterations reached, returning best effort")
        return current_stories

    def _get_review(
        self, stories: list[dict[str, Any]], intent_content: str, reviewer_model: str
    ) -> dict[str, Any]:
        """Get review decision from reviewer model."""
        prompt = STORY_REVIEW_PROMPT.format(
            intent=intent_content, stories=json.dumps(stories, indent=2)
        )

        # Use reviewer model
        original_model = self.model
        original_provider = self.provider
        self.model = reviewer_model
        self.provider = self._detect_provider(reviewer_model)

        try:
            if self.provider == "anthropic":
                response = self._call_anthropic(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            elif self.provider == "google":
                response = self._call_google(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            return self._parse_review_response(response)
        finally:
            self.model = original_model
            self.provider = original_provider

    def _fix_stories(
        self,
        stories: list[dict[str, Any]],
        intent_content: str,
        review_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fix stories based on reviewer feedback using executor model."""
        feedback = json.dumps(review_result, indent=2)
        prompt = STORY_FIX_PROMPT.format(
            intent=intent_content,
            stories=json.dumps(stories, indent=2),
            feedback=feedback,
        )

        # Use executor model (self.model is already set to executor)
        if self.provider == "anthropic":
            response = self._call_anthropic(prompt)
        elif self.provider == "openai":
            response = self._call_openai(prompt)
        elif self.provider == "google":
            response = self._call_google(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return self._parse_response(response)

    def _parse_review_response(self, response: str) -> dict[str, Any]:
        """Parse review JSON response."""
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Find JSON object
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            response = response[start:end]

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # If parsing fails, assume rejection
            return {
                "approved": False,
                "issues": [{"issue": "Failed to parse review response"}],
                "summary": "Review parsing error",
            }

    def _parse_response(self, response: str) -> list[dict[str, Any]]:
        """Parse JSON response from LLM."""
        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Find JSON array in response
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end > start:
            response = response[start:end]

        # Try to fix common JSON issues
        # Sometimes LLM outputs [ "key": instead of [ {"key":
        if re.search(r'\[\s*"[^"]+"\s*:', response):
            # Wrap in objects - find each "key": pattern after [ or ,
            response = re.sub(r'(\[|,)\s*("[^"]+")\s*:', r'\1 {\2:', response)
            # Close any unclosed objects before ] or ,
            response = re.sub(r'([^}])\s*(,\s*\{|\])', r'\1}\2', response)

        try:
            stories = json.loads(response)
        except json.JSONDecodeError as e:
            # Try a more aggressive fix - maybe the LLM returned a single object
            try:
                single = json.loads("{" + response.strip("[]{}").strip() + "}")
                stories = [single]
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response[:500]}")

        # Validate structure
        if not isinstance(stories, list):
            raise ValueError(f"Expected list of stories, got {type(stories)}")

        # Ensure consistent structure
        for story in stories:
            if "acceptance_criteria" not in story:
                story["acceptance_criteria"] = []
            if "tasks" not in story:
                story["tasks"] = []

        return stories
