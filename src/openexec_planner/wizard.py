"""Guided Intent Interviewer logic.

This module handles the structured interaction with the user to gather
requirements and constraints before project execution.
"""

import os
from enum import StrEnum

from pydantic import BaseModel, Field

from .utils import safe_resolve_path


class ProjectFlow(StrEnum):
    """The fundamental nature of the project."""

    GREENFIELD = "greenfield"
    REFACTOR = "refactor"
    UNKNOWN = "unknown"


class AppType(StrEnum):
    """Type of application being built."""

    CLI = "cli"
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    API = "api"
    LIBRARY = "library"
    PLUGIN = "plugin"
    OTHER = "other"
    UNKNOWN = "unknown"


class Platform(StrEnum):
    """Target platforms."""

    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    CROSS_PLATFORM = "cross-platform"
    UNKNOWN = "unknown"


class Goal(BaseModel):
    """A high-level, measurable project objective."""

    id: str
    description: str
    success_criteria: str = ""  # How do we know this goal is met?
    verification_method: str = ""  # Manual check, Automated test, Metric?


class Constraint(BaseModel):
    """A project constraint or technical limitation."""

    id: str
    description: str


class Dependency(BaseModel):
    """An external dependency or infrastructure component."""

    name: str
    description: str = ""
    type: str = ""  # e.g., database, api, engine


class Entity(BaseModel):
    """A core business noun and its role."""

    name: str
    description: str = ""
    data_source: str = ""
    attributes: list[str] = Field(default_factory=list)


class Contract(BaseModel):
    """An integration point between components."""

    source: str = ""
    target: str = ""
    protocol: str = ""  # e.g., REST, GraphQL, gRPC
    details: str = ""


class IntentState(BaseModel):
    """The structured state of the project intent."""

    project_name: str = ""
    flow: ProjectFlow = ProjectFlow.UNKNOWN
    app_type: AppType = AppType.UNKNOWN
    platforms: list[Platform] = Field(default_factory=list)
    problem_statement: str = ""

    # Goals
    primary_goals: list[Goal] = Field(default_factory=list)
    success_metric: str = ""

    # Architecture
    entities: list[Entity] = Field(default_factory=list)
    contracts: list[Contract] = Field(default_factory=list)
    system_boundary: str = ""  # What's inside vs outside

    # Refactoring & Legacy
    legacy_repo_path: str | None = None
    refactor_scope: str | None = None  # e.g., Component, System
    dependencies: list[Dependency] = Field(default_factory=list)  # e.g., Supabase, Redis

    # Constraints & SLOs
    slos: dict[str, str] = Field(default_factory=dict)
    constraints: list[Constraint] = Field(default_factory=list)

    # Internal Tracking
    explicit_facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    def is_ready(self) -> bool:
        """Check if the intent has reached minimum viability."""
        if self.flow == ProjectFlow.UNKNOWN:
            return False
        if self.app_type == AppType.UNKNOWN:
            return False
        if not self.problem_statement:
            return False

        # Must have at least one primary goal
        if not self.primary_goals:
            return False

        # Must have at least one constraint
        if not self.constraints:
            return False

        # Must have at least one entity with data source mapping
        if not self.entities or not any(e.data_source for e in self.entities):
            return False

        # Desktop/Mobile requires explicit platforms
        if self.app_type in [AppType.DESKTOP, AppType.MOBILE] and not self.platforms:
            return False

        # Refactor requires repo path
        if self.flow == ProjectFlow.REFACTOR and not self.legacy_repo_path:
            return False

        return True


WIZARD_SYSTEM_PROMPT = """You are an expert Software Architect interviewing a user to gather project requirements for the OpenExec orchestration engine.

Your goal is to fill the provided JSON schema while following a strict "Constraint-First" policy.

RULES:
1. CLASSIFY FIRST: Determine if the project is GREENFIELD (new) or REFACTOR (modifying existing).
2. PIN SHAPE: Do not design architecture until the App Type and Platform (macOS/Win/Linux/iOS/Android) are explicitly chosen.
3. ACKNOWLEDGE: Clearly state your understanding of the flow (New vs Refactor).
4. LAYER RECOGNITION: Proactively identify foundational layers (Docker, DB Schema, Auth, Shared Types) that must be in place before features can be built.
5. GOAL CONVERGENCE: Extract exactly 1-3 primary GOALS (G-001, etc.). Each goal must have measurable success criteria and a proposed verification method.
6. DATA LOCALITY: For every core entity, determine its source of truth (e.g., Local Database, External API like Supabase, Third-party service).
7. VALIDATE: Identify facts that the user stated (Explicit) vs what you are inferring (Assumed).
8. ONE QUESTION: Ask exactly ONE high-leverage question at a time to minimize user fatigue.
9. TECHNICAL AUTONOMY: Early in the interview, ask if the user wants to make specific technical/architectural decisions (e.g., choice of database, framework) or if they prefer you to decide on their behalf based on best practices.
10. ACCESSIBILITY: If the user seems non-technical, explain choices in plain English or make sensible defaults (Assumptions) and ask for confirmation rather than asking them to choose from a list of technologies.
11. CONTRACTS: For Refactoring, prioritize mapping existing API/DB contracts and dependencies.
12. OUTPUT ONLY JSON: Respond with a single JSON object matching the WizardResponse schema. DO NOT include any conversational text, markdown preamble, or explanations outside the JSON.
13. COMPLETION: If all required fields are filled and the user indicates they are ready or happy, set "is_complete": true.

SCHEMA DEFINITION:
- flow: "greenfield", "refactor", or "unknown"
- app_type: "cli", "web", "mobile", "desktop", "api", "library", "plugin", "other", "unknown"
- platforms: List of "macos", "windows", "linux", "ios", "android", "web", "cross-platform"
- legacy_repo_path: Required if flow is "refactor"
- constraints: List of objects with "id" (C-001, etc.) and "description"
- entities: List of objects with "name", "description", and "data_source" (Source of Truth)
- primary_goals: List of objects with "id", "description", "success_criteria"
- explicit_facts: List of strings the user explicitly stated.
- assumptions: List of strings you are assuming but need confirmation on.
- is_complete: Boolean. Set to true ONLY when the intent is fully populated and the user is satisfied.
- next_question: The single next question to ask. If complete, set to "Intent is ready for generation."

RESPONSE FORMAT (JSON):
{{
  "updated_state": {{ ... }},
  "next_question": "string",
  "acknowledgement": "string (optional)",
  "is_complete": boolean,
  "new_facts": ["string"],
  "new_assumptions": ["string"]
}}
"""


class WizardResponse(BaseModel):
    """Response from the wizard agent."""

    updated_state: IntentState
    next_question: str | None = "Do you have any other requirements?"
    acknowledgement: str | None = None
    is_complete: bool = False
    new_facts: list[str] = Field(default_factory=list)
    new_assumptions: list[str] = Field(default_factory=list)


class IntentWizard:
    """Manages the interactive intent gathering session."""

    def __init__(self, model: str = "sonnet"):
        """Initialize wizard with LLM model."""
        from .llm_generator import LLMStoryGenerator

        self.generator = LLMStoryGenerator(model=model)
        self.state = IntentState()

    def process_message(self, message: str) -> WizardResponse:
        """Process a user message and return the next wizard response.

        Args:
            message: User's input text

        Returns:
            WizardResponse containing updated state and next question
        """
        # Sanitize input: trim whitespace and normalize newlines
        # Remove non-printable characters and extra whitespace
        clean_msg = "".join(char for char in message if char.isprintable() or char in "\n\r\t")
        clean_msg = clean_msg.strip()

        if not clean_msg:
            return WizardResponse(
                updated_state=self.state,
                next_question="Could you please provide some details about your project?",
                acknowledgement="Input was empty.",
                is_complete=False,
            )

        # Scan message for mentioned files and include context
        context_files = self._scan_for_files(clean_msg)
        enhanced_message = clean_msg
        if context_files:
            enhanced_message += "\n\nFILE CONTEXT PROVIDED:\n"
            for path, content in context_files.items():
                enhanced_message += f"\n--- {path} ---\n{content}\n"

        prompt = (
            WIZARD_SYSTEM_PROMPT
            + f"\n\nCurrent Intent State:\n{self.state.model_dump_json(indent=2)}\n\nUser Message: {enhanced_message}"
        )

        # Retry loop for self-healing JSON responses
        max_retries = 2
        last_error = ""

        for attempt in range(max_retries + 1):
            if attempt > 0:
                # Add a correction instruction if this is a retry
                correction_prompt = f"{prompt}\n\n⚠️ PREVIOUS ATTEMPT FAILED TO PARSE AS JSON: {last_error}\nSTRICT REQUIREMENT: You MUST respond ONLY with a valid JSON object matching the schema. No conversational text."
                response_text = self.generator._call_llm(correction_prompt)
            else:
                response_text = self.generator._call_llm(prompt)

            try:
                # Parse response using the generator's JSON extraction
                data = self.generator._extract_json_from_response(response_text, expect_array=False)

                # Update local state
                result = WizardResponse.model_validate(data)
                self.state = result.updated_state

                # Check if actually complete based on schema rules
                if self.state.is_ready():
                    result.is_complete = True

                return result
            except (ValueError, Exception) as e:
                last_error = str(e)
                # If we're out of retries, try the safety fallback or return error
                if attempt == max_retries:
                    # SAFETY FALLBACK: If state is already ready and LLM returned text, just finish
                    if self.state.is_ready():
                        return WizardResponse(
                            updated_state=self.state,
                            next_question="Intent is ready.",
                            acknowledgement="Proceeding with finalized intent.",
                            is_complete=True,
                        )

                    # Return a retry question to the user
                    return WizardResponse(
                        updated_state=self.state,
                        next_question="I had trouble processing that response. Could you please rephrase or provide more detail?",
                        acknowledgement=f"Error parsing AI response: {str(e)[:100]}...",
                        is_complete=False,
                        new_facts=[],
                        new_assumptions=[],
                    )

        # Should not be reachable
        return WizardResponse(updated_state=self.state, next_question="...")

    def _scan_for_files(self, message: str) -> dict[str, str]:
        """Scan message for potential file paths and read their content."""
        # Simple heuristic for file paths
        # Look for words containing / or .md, .py, .txt etc.
        words = message.split()
        files = {}

        for word in words:
            # Clean punctuation
            clean_word = word.strip(".,!?;:\"'")
            if "/" in clean_word or "." in clean_word:
                try:
                    # Security: Prevent reading files outside workspace
                    safe_path = safe_resolve_path(os.getcwd(), clean_word)
                    if safe_path.is_file():
                        # Don't read huge files
                        if safe_path.stat().st_size < 100 * 1024:  # 100KB limit
                            files[clean_word] = safe_path.read_text(errors="ignore")
                except (OSError, ValueError):
                    # Skip files that can't be read or are outside workspace
                    continue
        return files

    def render_intent_md(self) -> str:
        """Render the current state as a valid INTENT.md document."""
        lines = []
        lines.append(f"# Intent: {self.state.project_name or 'New Project'}")
        lines.append("")
        lines.append("## Goals")
        if self.state.problem_statement:
            lines.append(f"- {self.state.problem_statement}")

        if self.state.primary_goals:
            for goal in self.state.primary_goals:
                lines.append(f"### {goal.id}: {goal.description}")
                lines.append(f"- Success Criteria: {goal.success_criteria}")
                lines.append(f"- Verification: {goal.verification_method}")
        else:
            lines.append("- TBD: High-level goal definition required")

        lines.append(f"- Global Success Metric: {self.state.success_metric or 'TBD'}")
        lines.append("")
        lines.append("## Requirements")
        lines.append("### REQ-001: Core Architecture")
        lines.append(f"- Shape: {self.state.app_type.value if self.state.app_type else 'TBD'}")
        if self.state.platforms:
            lines.append(f"- Platforms: {', '.join([p.value for p in self.state.platforms])}")
        else:
            lines.append("- Platforms: TBD")

        lines.append("")
        lines.append("### REQ-002: Data Source Mapping")
        if self.state.entities:
            for entity in self.state.entities:
                lines.append(f"- {entity.name}: {entity.description or 'TBD'}")
                if entity.data_source:
                    lines.append(f"  - Source of Truth: {entity.data_source}")
        else:
            lines.append("- TBD: Core entities and data ownership required")

        if self.state.flow == ProjectFlow.REFACTOR:
            lines.append("")
            lines.append("## Legacy Context")
            lines.append(f"- Repo: {self.state.legacy_repo_path or 'TBD'}")
            lines.append(f"- Scope: {self.state.refactor_scope or 'TBD'}")
            if self.state.dependencies:
                lines.append("- Dependencies:")
                for dep in self.state.dependencies:
                    lines.append(f"  - {dep.name}: {dep.description or dep.type or 'No details'}")

        lines.append("")
        lines.append("## Constraints")
        if self.state.constraints:
            for constraint in self.state.constraints:
                lines.append(f"- {constraint.id}: {constraint.description}")
        else:
            lines.append("- TBD: Operational or technical constraints required")

        return "\n".join(lines)
