# Contributing to OpenExec Planner

First off, thank you for considering contributing to OpenExec! It's people like you that make OpenExec such a great tool.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/openexec/openexec-planner.git
   cd openexec-planner
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies in editable mode:**
   ```bash
   pip install -e ".[dev,llm]"
   ```

## Workflow

1. **Create a new branch** from `main`.
2. **Make your changes.**
3. **Run tests** to ensure no regressions:
   ```bash
   pytest
   ```
4. **Lint your code** using ruff:
   ```bash
   ruff check .
   ```
5. **Type check** your code:
   ```bash
   mypy src/
   ```
6. **Submit a Pull Request.**

## Standards

- **Python Version:** 3.11 or higher.
- **Testing:** New features should include corresponding tests in the `tests/` directory.
- **Documentation:** Update the `README.md` or docstrings if you change user-facing behavior.
- **Commit Messages:** Use clear, descriptive commit messages.

## Security

If you find a security vulnerability, please do NOT open an issue. Instead, email hello@openexec.io directly.
