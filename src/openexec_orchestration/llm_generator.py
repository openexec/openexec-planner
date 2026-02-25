"""LLM-based story generation from intent documents.

Supports both API-based and CLI-based generation:
- CLI mode (default): Uses claude/codex/gemini CLI commands
- API mode: Uses Anthropic/OpenAI/Google APIs (requires API keys)
"""

import json
import os
import re
import shutil
import subprocess
from typing import Any

# Model to CLI command mapping
CLI_COMMANDS = {
    # Claude Code CLI
    "opus": "claude",
    "sonnet": "claude",
    "haiku": "claude",
    # Codex CLI
    "gpt-5": "codex",
    "gpt-5-codex": "codex",
    # Gemini CLI
    "gemini-3.1-pro-preview": "gemini",
    "gemini-3.1-flash-preview": "gemini",
    # OpenCode CLI
    "opencode": "opencode",
}

# Model mapping for API mode
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

Your goal is to ensure the stories are SUFFICIENT FOR IMPLEMENTATION and have correct dependency modeling for parallel execution.

REVIEW THE STORIES AGAINST THESE CRITERIA:

1. **Requirement Coverage**: Each REQ-XXX in the intent must map to exactly ONE story. No requirements should be missing or buried.

2. **No Redundancy**: Stories should not overlap. If US-001, US-005, and US-010 all cover "basic setup", they must be merged into one.

3. **Dependency Correctness**: Check the "depends_on" lists. 
   - Foundational stories (Docker, Schema, Shared Types) must be dependencies for feature stories.
   - Sequential tasks within a story must have internal dependencies.
   - Independent stories/tasks should have empty "depends_on" to allow parallelism.

4. **Quality & Correctness**: No parsing errors, hallucinations, or corrupted titles.

5. **Acceptance Criteria**: Must be extracted from the intent document, not null or generic. These define "done".

6. **Specific Tasks**: Tasks must be technical and actionable.

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
      "category": "Dependency Error",
      "description": "US-002 (API) should depend on US-001 (Docker/Schema), but depends_on is empty.",
      "examples": ["US-002 is missing dependency on foundational story US-001"]
    }}
  ],
  "refactoring_plan": {{
    "goal": "Refactor to align with requirements and fix dependencies",
    "proposed_stories": [
      {{
        "story": "Docker Development Environment",
        "maps_to": "REQ-001",
        "depends_on": [],
        "tasks": ["Create Dockerfile", "Create docker-compose.yml"]
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
5. DEPENDENCIES: Model dependencies via "depends_on" lists for stories and tasks.

OUTPUT FORMAT - JSON array:
[
  {{
    "id": "US-001",
    "title": "Story title from refactoring plan",
    "description": "As a developer, I want...",
    "requirement_id": "REQ-001",
    "depends_on": [],
    "acceptance_criteria": ["Specific criteria from intent"],
    "tasks": [
      {{
        "id": "T-US-001-001",
        "title": "Specific task from plan",
        "description": "Technical details",
        "depends_on": []
      }}
    ]
  }}
]

Output ONLY valid JSON array, no markdown or explanations."""

STORY_GENERATION_PROMPT = """You are a software architect generating user stories from an intent document.

Analyze the intent document below and generate a JSON array of user stories.

RULES:
1. Create ONE story per requirement (REQ-XXX) in the document.
2. Each story should have specific, actionable tasks (not generic "Design/Implement/Test").
3. Extract acceptance criteria directly from the intent document.
4. DEPENDENCIES: Model execution dependencies via "depends_on" lists (IDs only).
   - Foundational stories (Docker, DB Schema, Configs, Shared Types) must be dependencies for stories that use them.
   - Sequential tasks within a story must also include "depends_on".
5. Task IDs should follow format: T-US-XXX-YYY where XXX is story number, YYY is task number.
6. Avoid redundancy - do not create multiple stories for the same functionality.

OUTPUT FORMAT (JSON array):
[
  {{
    "id": "US-001",
    "title": "Docker Development Environment",
    "description": "As a developer, I want a Docker-based development environment so that I can develop locally with hot-reload",
    "requirement_id": "REQ-001",
    "depends_on": [],
    "acceptance_criteria": [
      "Container starts with 'docker compose up'",
      "Source code changes trigger automatic rebuild"
    ],
    "tasks": [
      {{
        "id": "T-US-001-001",
        "title": "Create development Dockerfile",
        "description": "Create Dockerfile with development target stage",
        "depends_on": []
      }},
      {{
        "id": "T-US-001-002",
        "title": "Create docker-compose.yml",
        "description": "Configure docker-compose with volume mounts",
        "depends_on": ["T-US-001-001"]
      }}
    ]
  }},
  {{
    "id": "US-002",
    "title": "User API Endpoints",
    "description": "As a user, I want to manage my profile via API",
    "requirement_id": "REQ-002",
    "depends_on": ["US-001"],
    "acceptance_criteria": ["GET /user returns 200"],
    "tasks": [
      {{
        "id": "T-US-002-001",
        "title": "Implement User Controller",
        "description": "Create FastAPI controller for users",
        "depends_on": []
      }}
    ]
  }}
]

INTENT DOCUMENT:
{intent}

Generate the JSON array of stories. Output ONLY valid JSON, no markdown or explanations."""


class LLMStoryGenerator:
    """Generates high-quality user stories using LLM."""

    def __init__(self, model: str = "sonnet", use_api: bool = False):
        """Initialize generator with model.

        Args:
            model: Model identifier (opus, sonnet, haiku, gpt-5, gemini-3.1-pro-preview, etc.)
            use_api: If True, use API calls. If False (default), use CLI commands.
        """
        self.model = model
        self.use_api = use_api
        self.provider = self._detect_provider(model)
        self.cli_command = CLI_COMMANDS.get(model, "claude")

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

        # Try CLI first (default), fall back to API if CLI not available
        if not self.use_api:
            cli_path = shutil.which(self.cli_command)
            if cli_path:
                response = self._call_cli(prompt)
                return self._parse_response(response)
            else:
                print(f"CLI '{self.cli_command}' not found, trying API...")

        # API mode
        if self.provider == "anthropic":
            response = self._call_anthropic(prompt)
        elif self.provider == "openai":
            response = self._call_openai(prompt)
        elif self.provider == "google":
            response = self._call_google(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return self._parse_response(response)

    def _call_cli(self, prompt: str) -> str:
        """Call LLM via CLI command (claude, codex, or gemini).

        Uses stdin to send prompt - this is the proven pattern from the initial
        project that works reliably with all CLI tools.
        """
        # Build command based on CLI type
        if self.cli_command == "claude":
            # Claude Code CLI: claude --print
            # Sends prompt via stdin, outputs to stdout
            cmd = ["claude", "--print"]
        elif self.cli_command == "codex":
            # Codex CLI: codex exec --json --full-auto -
            # --json for machine-readable output, --full-auto for non-interactive
            cmd = ["codex", "exec", "--json", "--full-auto", "-"]
        elif self.cli_command == "gemini":
            # Gemini CLI: gemini --prompt - --yolo
            # --prompt - reads from stdin, --yolo for non-interactive mode
            cmd = ["gemini", "--prompt", "-", "--yolo"]
        else:
            raise ValueError(f"Unknown CLI command: {self.cli_command}")

        try:
            # Run the command with prompt via stdin
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # Send prompt to stdin and close
            stdout, _ = process.communicate(input=prompt, timeout=300)

            if process.returncode != 0:
                raise RuntimeError(f"CLI command failed (exit {process.returncode}): {stdout[:500]}")

            # For codex --json, we need to extract the agent_message text from JSONL events
            if self.cli_command == "codex":
                agent_text = []
                for line in stdout.splitlines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("type") == "item.completed":
                            item = event.get("item", {})
                            if item.get("type") == "agent_message":
                                agent_text.append(item.get("text", ""))
                    except json.JSONDecodeError:
                        continue
                
                # Use the last agent message found
                if agent_text:
                    return self._clean_output(agent_text[-1])
                else:
                    # Fallback to raw output if no events found
                    return self._clean_output(stdout)

            return self._clean_output(stdout)

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError("CLI command timed out after 300 seconds")

    def _clean_output(self, output: str) -> str:
        """Strip diagnostic messages and tool-call echoes from CLI output.

        This prevents diagnostic lines and tool calls from ending up in 
        the final response, which improves JSON parsing.
        """
        lines = output.split("\n")
        clean_lines = []
        skip_patterns = [
            "YOLO mode is enabled",
            "Loaded cached credentials",
            "Hook registry initialized",
            "Loading extension:",
            "I will ",
            "Calling tool:",
            "Tool call approved",
            "thinking",
            "tokens used",
            "session id:",
            "reasoning effort:",
            "reasoning summaries:",
            "--------",
        ]

        found_content_start = False
        for line in lines:
            stripped = line.strip()

            # Skip diagnostic lines
            if any(pattern in stripped for pattern in skip_patterns):
                continue

            # Skip tool execution logs like [Tool] write_file
            if stripped.startswith("[") and "]" in stripped and any(x in stripped for x in ["Tool", "workdir", "sandbox"]):
                continue

            if not found_content_start and not stripped:
                continue

            found_content_start = True
            clean_lines.append(line)

        return "\n".join(clean_lines).strip()

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

    def _call_llm(self, prompt: str, model: str | None = None) -> str:
        """Call LLM using CLI or API based on configuration.

        Args:
            prompt: The prompt to send
            model: Optional model override (uses self.model if not specified)
        """
        target_model = model or self.model
        cli_cmd = CLI_COMMANDS.get(target_model, "claude")

        # Try CLI first if not forcing API
        if not self.use_api:
            cli_path = shutil.which(cli_cmd)
            if cli_path:
                # Temporarily update cli_command for the call
                original_cli = self.cli_command
                self.cli_command = cli_cmd
                try:
                    return self._call_cli(prompt)
                finally:
                    self.cli_command = original_cli

        # Fall back to API
        provider = self._detect_provider(target_model)
        if provider == "anthropic":
            return self._call_anthropic(prompt)
        elif provider == "openai":
            return self._call_openai(prompt)
        elif provider == "google":
            return self._call_google(prompt)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _get_review(
        self, stories: list[dict[str, Any]], intent_content: str, reviewer_model: str
    ) -> dict[str, Any]:
        """Get review decision from reviewer model."""
        prompt = STORY_REVIEW_PROMPT.format(
            intent=intent_content, stories=json.dumps(stories, indent=2)
        )

        response = self._call_llm(prompt, model=reviewer_model)
        return self._parse_review_response(response)

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

        response = self._call_llm(prompt)
        return self._parse_response(response)

    def _extract_json_from_response(self, response: str, expect_array: bool = False) -> Any:
        """Extract JSON data from agent response.

        Handles potential markdown code blocks and extracts JSON.
        This is the proven pattern from the initial project.

        Args:
            response: The raw agent response text.
            expect_array: If True, look for array first, then object.

        Returns:
            Parsed JSON data.

        Raises:
            ValueError: If response cannot be parsed as valid JSON.
        """
        # Try to find JSON in markdown code blocks first
        json_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        matches = re.findall(json_block_pattern, response)

        json_text = response
        if matches:
            # Use the first JSON block found
            json_text = matches[0]
        else:
            # Try to extract JSON object or array directly
            json_object_pattern = r"\{[\s\S]*\}"
            json_array_pattern = r"\[[\s\S]*\]"

            obj_match = re.search(json_object_pattern, response)
            arr_match = re.search(json_array_pattern, response)

            # Prioritize based on expect_array parameter
            if expect_array:
                # Look for array first
                if arr_match:
                    json_text = arr_match.group(0)
                elif obj_match:
                    json_text = obj_match.group(0)
            else:
                # Look for object first
                if obj_match and arr_match:
                    if obj_match.start() < arr_match.start():
                        json_text = obj_match.group(0)
                    else:
                        json_text = arr_match.group(0)
                elif obj_match:
                    json_text = obj_match.group(0)
                elif arr_match:
                    json_text = arr_match.group(0)

        try:
            return json.loads(json_text.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from response: {e}\nText: {json_text[:300]}") from e

    def _parse_review_response(self, response: str) -> dict[str, Any]:
        """Parse review JSON response."""
        try:
            result = self._extract_json_from_response(response, expect_array=False)
            if isinstance(result, dict):
                return result
            # If we got an array, it's probably wrong - assume rejection
            return {
                "approved": False,
                "assessment": "Unexpected review response format (got array instead of object)",
            }
        except ValueError:
            # If parsing fails, assume rejection
            return {
                "approved": False,
                "assessment": "Failed to parse review response",
            }

    def _parse_response(self, response: str) -> list[dict[str, Any]]:
        """Parse JSON response from LLM."""
        try:
            result = self._extract_json_from_response(response, expect_array=True)
        except ValueError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Handle if we got an object instead of array
        if isinstance(result, dict):
            # Wrap single story in array
            result = [result]

        # Validate structure
        if not isinstance(result, list):
            raise ValueError(f"Expected list of stories, got {type(result)}")

        # Ensure consistent structure
        for story in result:
            if "acceptance_criteria" not in story:
                story["acceptance_criteria"] = []
            if "tasks" not in story:
                story["tasks"] = []

        return result
