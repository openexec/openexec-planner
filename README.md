<p align="center">
  <h1 align="center">OpenExec Orchestration</h1>
</p>

<p align="center">
  <strong>AI Planning Engine — From Intent to Executable Tasks</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"/>
</p>

---

The **OpenExec Orchestration** module transforms high-level project intents (PRDs, specs, requirements) into structured, executable task hierarchies using AI-powered decomposition and goal tree analysis.

## Features

- **Intent Parsing** — Extracts goals and requirements from PRD documents
- **Goal Tree Decomposition** — Breaks down objectives into atomic tasks
- **Story Generation** — Creates user stories with acceptance criteria
- **Dependency Analysis** — Identifies task relationships and ordering
- **Quality Gate Templates** — Language-aware testing configurations
- **Context Awareness** — Integrates with codebase analysis

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   INTENT    │────▶│    PARSER    │────▶│  GOAL TREE  │
│  (PRD.md)   │     │  (AI Agent)  │     │   (JSON)    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌───────────────────────────┘
                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   STORIES   │────▶│    TASKS     │────▶│   SCHEDULE  │
│  (JSON)     │     │   (JSON)     │     │  (ordered)  │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Installation

```bash
git clone https://github.com/openexec/openexec.git
cd openexec/openexec-orchestration
pip install -e .
```

## Usage

### Parse Intent Document

```bash
openexec-orchestration plan INTENT.md
```

Outputs:
- `stories.json` — User stories with acceptance criteria
- `tasks.json` — Atomic tasks with dependencies
- `goal-tree.json` — Hierarchical goal structure

### Generate Stories from Intent

```python
from openexec_orchestration import IntentParser, StoryGenerator

parser = IntentParser()
intent = parser.parse("INTENT.md")

generator = StoryGenerator()
stories = generator.generate(intent)

for story in stories:
    print(f"{story.id}: {story.title}")
    for criterion in story.acceptance_criteria:
        print(f"  - {criterion}")
```

### Build Goal Tree

```python
from openexec_orchestration import GoalTreeBuilder

builder = GoalTreeBuilder()
tree = builder.build(intent)

# Visualize
tree.print()
# Goal: Build authentication system
#   ├── Subgoal: User registration
#   │   ├── Task: Create registration form
#   │   └── Task: Add email validation
#   └── Subgoal: User login
#       ├── Task: Create login form
#       └── Task: Implement JWT tokens
```

### Schedule Tasks

```python
from openexec_orchestration import Scheduler

scheduler = Scheduler()
ordered_tasks = scheduler.schedule(tasks, dependencies)

for task in ordered_tasks:
    print(f"{task.id}: {task.title} (deps: {task.dependencies})")
```

## Configuration

```yaml
# openexec.yaml
orchestration:
  agent: claude                  # AI agent for planning
  model: sonnet                  # Model for decomposition
  max_depth: 4                   # Goal tree max depth
  min_task_granularity: 2h       # Minimum task size
  max_task_granularity: 8h       # Maximum task size

planning:
  include_tests: true            # Generate test tasks
  include_docs: false            # Generate doc tasks
  language_detection: auto       # Detect project language
```

## Output Formats

### stories.json

```json
{
  "stories": [
    {
      "id": "US-001",
      "title": "User Registration",
      "description": "As a user, I want to register...",
      "acceptance_criteria": [
        "User can enter email and password",
        "Email validation is performed",
        "Success message is shown"
      ],
      "tasks": ["T-001", "T-002", "T-003"]
    }
  ]
}
```

### tasks.json

```json
{
  "tasks": [
    {
      "id": "T-001",
      "story_id": "US-001",
      "title": "Create registration form component",
      "description": "...",
      "status": "pending",
      "dependencies": [],
      "estimated_hours": 4
    }
  ]
}
```

### goal-tree.json

```json
{
  "root": {
    "goal": "Build user authentication",
    "children": [
      {
        "goal": "User registration",
        "children": [
          {"task": "T-001"},
          {"task": "T-002"}
        ]
      }
    ]
  }
}
```

## Project Structure

```
openexec-orchestration/
├── src/
│   └── openexec_orchestration/
│       ├── __init__.py
│       ├── parser.py           # Intent parsing
│       ├── generator.py        # Story generation
│       ├── goal_tree.py        # Goal tree building
│       ├── scheduler.py        # Task scheduling
│       └── templates/          # Prompt templates
├── tests/
├── pyproject.toml
└── README.md
```

## Language Detection

Automatically detects project language and configures appropriate:
- Quality gates (lint, test, typecheck)
- File patterns
- Build commands

Supported languages:
- Python (ruff, mypy, pytest)
- Go (gofmt, golangci-lint, go test)
- TypeScript/JavaScript (eslint, tsc, jest)
- Rust (cargo fmt, clippy, cargo test)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/
```

## Related

- [openexec](../openexec) — Main documentation
- [initial](../initial) — Python CLI (feature-complete)
- [openexec-execution](../openexec-execution) — Execution engine
- [openexec-cli](../openexec-cli) — Go CLI with TUI

## License

MIT License
