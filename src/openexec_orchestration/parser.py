"""Intent document parsing."""

import re
from pathlib import Path
from typing import Any


class IntentParser:
    """Parses intent documents (PRD, specs) into structured format."""

    # Patterns for section headers
    GOAL_PATTERNS = [
        r"#+\s*(?:Goals?|Objectives?|Purpose|Vision)\s*\n([\s\S]*?)(?=\n#+|\Z)",
        r"\*\*(?:Goals?|Objectives?)\*\*[:\s]*([\s\S]*?)(?=\n\*\*|\n#+|\Z)",
    ]

    REQUIREMENT_PATTERNS = [
        r"#+\s*(?:Requirements?|Features?|Functional Requirements?|User Stories?)\s*\n([\s\S]*?)(?=\n#+|\Z)",
        r"\*\*(?:Requirements?|Features?)\*\*[:\s]*([\s\S]*?)(?=\n\*\*|\n#+|\Z)",
    ]

    CONSTRAINT_PATTERNS = [
        r"#+\s*(?:Constraints?|Limitations?|Non-Functional Requirements?|Technical Constraints?)\s*\n([\s\S]*?)(?=\n#+|\Z)",
        r"\*\*(?:Constraints?|Limitations?)\*\*[:\s]*([\s\S]*?)(?=\n\*\*|\n#+|\Z)",
    ]

    def parse(self, path: str | Path) -> dict[str, Any]:
        """Parse an intent document.

        Args:
            path: Path to the intent document (markdown or text)

        Returns:
            Structured intent data with goals, requirements, and constraints
        """
        path = Path(path)
        content = path.read_text()

        return {
            "title": self._extract_title(content),
            "goals": self._extract_goals(content),
            "requirements": self._extract_requirements(content),
            "constraints": self._extract_constraints(content),
            "raw_content": content,
        }

    def _extract_title(self, content: str) -> str:
        """Extract document title from first heading."""
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"

    def _extract_goals(self, content: str) -> list[str]:
        """Extract goals from document using pattern matching."""
        return self._extract_section_items(content, self.GOAL_PATTERNS)

    def _extract_requirements(self, content: str) -> list[str]:
        """Extract requirements from document using pattern matching."""
        return self._extract_section_items(content, self.REQUIREMENT_PATTERNS)

    def _extract_constraints(self, content: str) -> list[str]:
        """Extract constraints from document using pattern matching."""
        return self._extract_section_items(content, self.CONSTRAINT_PATTERNS)

    def _extract_section_items(self, content: str, patterns: list[str]) -> list[str]:
        """Extract list items from a section matching given patterns."""
        items: list[str] = []

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                items.extend(self._parse_list_items(match))

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_items: list[str] = []
        for item in items:
            normalized = item.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_items.append(item.strip())

        return unique_items

    def _parse_list_items(self, text: str) -> list[str]:
        """Parse list items from text (supports various formats)."""
        items: list[str] = []

        # Match numbered lists (1. item, 1) item)
        numbered = re.findall(r"^\s*\d+[.)\]]\s*(.+)$", text, re.MULTILINE)
        items.extend(numbered)

        # Match bullet lists (- item, * item, • item)
        bulleted = re.findall(r"^\s*[-*•]\s*(.+)$", text, re.MULTILINE)
        items.extend(bulleted)

        # Match checkbox lists (- [ ] item, - [x] item)
        checkbox = re.findall(r"^\s*-\s*\[[ xX]\]\s*(.+)$", text, re.MULTILINE)
        items.extend(checkbox)

        # If no list items found, try to split by sentences
        if not items:
            # Split on periods followed by space and capital letter
            sentences = re.split(r"\.\s+(?=[A-Z])", text.strip())
            for sentence in sentences:
                cleaned = sentence.strip().rstrip(".")
                if cleaned and len(cleaned) > 10:  # Ignore very short fragments
                    items.append(cleaned)

        return items


def parse_intent(path: str | Path) -> dict[str, Any]:
    """Convenience function to parse an intent document.

    Args:
        path: Path to the intent document

    Returns:
        Structured intent data
    """
    parser = IntentParser()
    return parser.parse(path)
