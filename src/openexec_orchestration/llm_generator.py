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

STORY_REVIEW_PROMPT = """You are a senior software architect reviewing generated user stories.

Analyze the stories against the original intent document. Return a JSON object with your review decision.

REVIEW CRITERIA:
1. Each requirement (REQ-XXX) should have exactly ONE story
2. No redundant or overlapping stories
3. Tasks must be specific and actionable (not generic "Design/Implement/Test")
4. Acceptance criteria must be extracted from the intent document
5. Task IDs must follow format: T-US-XXX-YYY
6. Stories should cover ALL requirements in the intent

ORIGINAL INTENT:
{intent}

GENERATED STORIES:
{stories}

Return a JSON object with this structure:
{{
  "approved": true/false,
  "issues": [
    {{
      "story_id": "US-001",
      "issue": "Description of the problem",
      "fix": "How to fix it"
    }}
  ],
  "summary": "Brief overall assessment"
}}

If approved=true, issues should be empty or minor suggestions.
If approved=false, issues must list all problems that need fixing.

Output ONLY valid JSON, no markdown or explanations."""

STORY_FIX_PROMPT = """You are a software architect fixing user stories based on reviewer feedback.

ORIGINAL INTENT:
{intent}

CURRENT STORIES:
{stories}

REVIEWER FEEDBACK:
{feedback}

Fix ALL the issues identified by the reviewer. Return the corrected stories as a JSON array.

RULES:
1. Address every issue in the feedback
2. Keep the same JSON structure for stories
3. Task IDs should follow format: T-US-XXX-YYY
4. Be specific and actionable in task descriptions

Output ONLY valid JSON array of stories, no markdown or explanations."""

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
                print(f"  ✓ Stories approved: {review_result.get('summary', 'OK')}")
                return current_stories

            # Stories rejected - show issues and fix
            issues = review_result.get("issues", [])
            print(f"  ✗ Rejected with {len(issues)} issue(s):")
            for issue in issues[:3]:  # Show first 3 issues
                print(f"    - {issue.get('story_id', '?')}: {issue.get('issue', 'Unknown issue')}")
            if len(issues) > 3:
                print(f"    ... and {len(issues) - 3} more")

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

        try:
            stories = json.loads(response)
        except json.JSONDecodeError as e:
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
