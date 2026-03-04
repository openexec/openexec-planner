"""UAOS Quality Gate CLI interface.

This module provides a unified CLI tool (uaos-gate) that wraps Ruff, MyPy, and Pytest,
outputting structured JSON results for quality gate validation.

The CLI supports:
- uaos-gate run --format json: Execute all gates and return JSON output
- uaos-gate run: Execute all gates with human-readable output
"""

from __future__ import annotations

import json
import shlex
import subprocess  # nosec B404
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import typer

# Initialize Typer app
app = typer.Typer(help="UAOS Quality Gate CLI - Unified validation interface")


@dataclass
class GateResult:
    """Result of a single quality gate execution."""

    name: str
    status: bool  # True for pass, False for fail
    command: str
    stdout: str
    stderr: str
    exit_code: int


@dataclass
class GateReport:
    """Complete report of all gate results."""

    passed: bool  # True if all gates passed
    gates: list[GateResult]


def run_gate(name: str, command: str) -> GateResult:
    """Execute a single quality gate and capture results.

    Args:
        name: Name of the gate (e.g., "ruff", "mypy", "pytest")
        command: Shell command to execute

    Returns:
        GateResult with command execution details
    """
    try:
        # Parse command string into list of arguments
        # Using shlex.split to safely parse the command
        args = shlex.split(command)
        result = subprocess.run(  # nosec B603
            args,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        return GateResult(
            name=name,
            status=result.returncode == 0,
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )
    except Exception as e:
        return GateResult(
            name=name,
            status=False,
            command=command,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


def execute_gates() -> GateReport:
    """Execute all quality gates and return unified report.

    Returns:
        GateReport containing results from all gates
    """
    gates = [
        ("ruff", "ruff check ."),
        ("mypy", "mypy ."),
        ("pytest", "pytest"),
    ]

    results: list[GateResult] = []
    for name, command in gates:
        result = run_gate(name, command)
        results.append(result)

    all_passed = all(result.status for result in results)
    return GateReport(passed=all_passed, gates=results)


def report_to_dict(report: GateReport) -> dict[str, Any]:
    """Convert GateReport to dictionary for JSON serialization.

    Args:
        report: GateReport to convert

    Returns:
        Dictionary representation of the report
    """
    return {
        "passed": report.passed,
        "gates": [asdict(gate) for gate in report.gates],
    }


@app.command()
def run(format: str = typer.Option("text", "--format", "-f", help="Output format (json or text)")) -> None:
    """Execute all quality gates and output results.

    Args:
        format: Output format - "json" for structured JSON, "text" for human-readable
    """
    report = execute_gates()

    if format == "json":
        output = json.dumps(report_to_dict(report), indent=2)
        typer.echo(output)
    else:
        # Human-readable format
        typer.echo("Quality Gate Report")
        typer.echo("=" * 50)
        for gate_result in report.gates:
            status_str = "PASS" if gate_result.status else "FAIL"
            typer.echo(f"\n[{status_str}] {gate_result.name}")
            typer.echo(f"    Command: {gate_result.command}")
            typer.echo(f"    Exit Code: {gate_result.exit_code}")
            if gate_result.stdout:
                typer.echo(f"    Output: {gate_result.stdout[:200]}")
            if gate_result.stderr:
                typer.echo(f"    Error: {gate_result.stderr[:200]}")

        typer.echo("\n" + "=" * 50)
        overall_status = "ALL PASSED" if report.passed else "SOME FAILED"
        typer.echo(f"Overall: {overall_status}")

    # Exit with appropriate code
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    app()
