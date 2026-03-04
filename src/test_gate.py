"""Tests for the quality gate CLI module."""

from __future__ import annotations

import json

from gate import GateReport, GateResult, report_to_dict, run_gate


def test_gate_result_creation() -> None:
    """Test creating a GateResult."""
    result = GateResult(
        name="test",
        status=True,
        command="echo test",
        stdout="test output",
        stderr="",
        exit_code=0,
    )
    assert result.name == "test"
    assert result.status is True
    assert result.exit_code == 0


def test_gate_report_creation() -> None:
    """Test creating a GateReport."""
    results = [
        GateResult(
            name="test1", status=True, command="cmd1", stdout="out1", stderr="", exit_code=0
        ),
        GateResult(
            name="test2", status=True, command="cmd2", stdout="out2", stderr="", exit_code=0
        ),
    ]
    report = GateReport(passed=True, gates=results)
    assert report.passed is True
    assert len(report.gates) == 2


def test_report_to_dict() -> None:
    """Test converting GateReport to dictionary."""
    result = GateResult(
        name="test", status=True, command="cmd", stdout="output", stderr="", exit_code=0
    )
    report = GateReport(passed=True, gates=[result])
    report_dict = report_to_dict(report)

    assert report_dict["passed"] is True
    assert len(report_dict["gates"]) == 1
    assert report_dict["gates"][0]["name"] == "test"
    assert report_dict["gates"][0]["status"] is True


def test_report_to_dict_is_json_serializable() -> None:
    """Test that report dict can be serialized to JSON."""
    result = GateResult(
        name="test", status=False, command="cmd", stdout="", stderr="error", exit_code=1
    )
    report = GateReport(passed=False, gates=[result])
    report_dict = report_to_dict(report)

    # Should not raise an exception
    json_str = json.dumps(report_dict)
    assert json_str is not None

    # Deserialize and verify
    parsed = json.loads(json_str)
    assert parsed["passed"] is False
    assert parsed["gates"][0]["status"] is False


def test_run_gate_with_valid_command() -> None:
    """Test running a valid gate command."""
    result = run_gate("echo_test", "echo hello")
    assert result.name == "echo_test"
    assert result.status is True
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_run_gate_with_failing_command() -> None:
    """Test running a command that fails."""
    result = run_gate("fail_test", "false")
    assert result.name == "fail_test"
    assert result.status is False
    assert result.exit_code != 0


