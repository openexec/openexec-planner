<p align="center">
  <h1 align="center">OpenExec Planner</h1>
</p>

<p align="center">
  <strong>AI Project Planning Engine — From Intent to Executable Task DAGs</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"/>
</p>

---

The **OpenExec Planner** module transforms high-level project intents (PRDs, specs, requirements) into structured, executable task hierarchies using AI-powered decomposition and goal tree analysis.

## Features

- **Guided Intent Interviewer** — Interactive chat to gather constraints and shape
- **Intent Parsing** — Extracts goals and requirements from PRD documents
- **Goal Tree Decomposition** — Breaks down objectives into atomic tasks
- **Story Generation** — Creates user stories with acceptance criteria
- **Dependency Modeling** — Infers and models execution prerequisites for parallel processing
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
git clone https://github.com/openexec/openexec-planner.git
cd openexec-planner
pip install -e .
```

### CLI Dependencies

By default, the orchestration engine uses external CLI tools to call LLMs. Ensure you have the relevant tools installed and authenticated:

- **Claude Code**: `claude` CLI
- **Codex**: `codex` CLI
- **Gemini**: `gemini` CLI
- **OpenCode**: `opencode` (Ollama)

To use direct API calls instead, install the optional dependencies:
```bash
pip install "openexec-planner[llm]"
```

## Usage

The orchestration engine follows a logical project lifecycle:

### 1. Gather Intent (Wizard)

Start a guided interview to define your project shape, platform, and contracts. This is the recommended first step for any new project or refactor.

```bash
openexec-planner wizard --message "I want to build a new mobile app for gym tracking"
```

The wizard will track state and ask follow-up questions until the intent is "Ready", then render an `INTENT.md` file.

### 2. Generate Plan (Generate)

Once you have an `INTENT.md` (either from the wizard or manual), transform it into structured user stories and tasks.

```bash
openexec-planner generate INTENT.md -o .openexec/stories.json
```

### 3. Analyze Architecture (Build Tree)

Decompose the goals into a hierarchical tree to visualize the project structure.

```bash
openexec-planner build-tree INTENT.md -o .openexec/goal_tree.json
```

### 4. Order Execution (Schedule)

Generate an optimized execution schedule based on task dependencies.

```bash
openexec-planner schedule .openexec/stories.json -o .openexec/schedule.json
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
openexec-planner/
├── src/
│   └── openexec_planner/
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

- [openexec](https://github.com/openexec/openexec) — Unified Go Execution Engine, Server, and Web Dashboard
- [openexec.io](https://openexec.io) — Official Website and Documentation

## License

MIT License
