---
summary: "Technical architecture of the UAOS Management Plane (Orchestration): components, data flow, and system design"
read_when:
  - You are implementing or debugging the planning logic
  - You are integrating new project state engines with Tract
  - You are extending the Python-native quality gates
title: "Architecture"
---

# Architecture

## Overview
The UAOS Management Plane (uaos-orchestration) is the central "Brain" that translates human requirements into actionable work units. It is an evolution of the OpenExec planning logic, designed to handle complex project decomposition and quality assurance.

The system is responsible for the entire planning lifecycle: parsing an `INTENT.md` (PRD), generating a hierarchical Goal Tree, and decomposing it into Feature Work Units (FWUs). It acts as the primary writer to the Tract SQLite database, which serves as the persistent state engine for the system. Additionally, it provides a Python-based Quality Gate suite that is invoked by the Execution Plane to validate all generated code before it is committed.

## Tech Stack
- **Language:** Python 3.11+
- **Data Persistence:** SQLite (Tract Schema)
- **Data Processing:** AI-based PRD parsing and task decomposition
- **Quality Assurance:** Ruff (Lint), MyPy (Types), Pytest (Tests), Bandit (Security)
- **Inter-Process:** CLI Bridge (`uaos-gate`) for Go integration

## Data Flow
1. **Planning Trigger:** A user provides a PRD (`INTENT.md`) to the orchestration engine.
2. **Decomposition:** The OpenExec planning logic generates a Goal Tree and FWUs.
3. **State Persistence:** The engine writes the FWUs and Reasoning Chain to the Tract database.
4. **Validation:** The Execution Plane calls the `uaos-gate` CLI to run quality checks on code changes.
5. **Auto-Fix:** If gates fail, the engine analyzes the errors and generates "Fix Tasks" to be injected back into Tract.
