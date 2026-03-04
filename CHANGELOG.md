# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-03-04

### Added
- Interactive `init` command for bootstrapping projects.
- Fully interactive CLI loop for the `wizard` command.
- Support for Claude 4.6 and GPT-5.3 models.
- Automated parent directory creation for all output files.

### Fixed
- Improved type safety and resolved all `mypy` issues.
- Hardened security against path traversal attacks.
- Enhanced JSON parsing from LLM responses.

## [0.1.0] - 2026-03-04

### Added
- Initial release of the OpenExec Orchestration engine.
- Guided Intent Interviewer (Wizard).
- Intent parsing from PRD documents.
- Goal Tree decomposition and visualization.
- User Story and Task generation with dependency modeling.
- Automated task scheduling and ordering.
- Multi-agent support (Claude Code, Codex, Gemini, OpenCode).
- PyPI package metadata and distribution configuration.
- Enhanced test suite for parser, scheduler, and goal tree.
