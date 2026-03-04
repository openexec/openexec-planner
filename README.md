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

The planner follows a logical project lifecycle. Follow these steps to go from an idea to a fully ordered task DAG.

### 1. Initialize Project
First, bootstrap the OpenExec structure in your current directory. This creates the `.openexec` folder and a default configuration.

```bash
openexec-planner init
```

### 2. Gather Intent (Wizard)
If you only have a rough idea, use the interactive wizard to define your project shape, platforms, and technical contracts.

```bash
openexec-planner wizard
```
*The wizard will chat with you, save its progress, and finally render an `INTENT.md` file.*

### 3. Generate User Stories
Transform your `INTENT.md` into structured user stories and technical tasks using an LLM.

```bash
openexec-planner generate INTENT.md -o .openexec/stories.json
```
*This creates high-level stories, but they are not yet ready for the execution engine.*

### 4. Create Execution DAG (Schedule)
Take the generated stories and flatten them into a Directed Acyclic Graph (DAG) of tasks. This step is **required** before running the Go execution engine.

```bash
openexec-planner schedule .openexec/stories.json -o .openexec/tasks.json
```
*The `schedule` command handles:*
- **Topological Sorting:** Ensures prerequisites are built before the features that depend on them.
- **Parallelization:** Groups tasks into phases that can be executed simultaneously.
- **Verification Mapping:** Links acceptance criteria to autonomous test scripts.

---

## Full Ecosystem Workflow

OpenExec is designed as a **Brain (Planner)** and a **Body (Executor)**.

1.  **Plan (Python):** Use `openexec-planner` (this package) to build the `tasks.json` roadmap (Steps 1-4).
2.  **Execute (Go):** Use the [OpenExec Engine](https://github.com/openexec/openexec) to run the tasks.

```bash
# Once .openexec/tasks.json is generated in step 4:
openexec start --ui
openexec run
```

---

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
