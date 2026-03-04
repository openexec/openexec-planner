"""Tests for utility functions."""

import os
from pathlib import Path

import pytest

from openexec_planner.utils import safe_resolve_path


def test_safe_resolve_path_relative():
    """Test resolving a safe relative path."""
    base = os.getcwd()
    target = "INTENT.md"
    resolved = safe_resolve_path(base, target)
    assert resolved == Path(base) / target


def test_safe_resolve_path_absolute_inside():
    """Test resolving an absolute path that is inside the base directory."""
    base = Path("/tmp/base").resolve()
    target = "/tmp/base/sub/file.txt"
    # Note: on some systems /tmp is a symlink, so we resolve
    resolved = safe_resolve_path(base, target)
    assert resolved == base / "sub" / "file.txt"


def test_safe_resolve_path_absolute_outside_sanitized():
    """Test that absolute paths outside are sanitized to just their name."""
    base = Path("/tmp/base").resolve()
    target = "/etc/passwd"
    resolved = safe_resolve_path(base, target)
    assert resolved == base / "passwd"


def test_safe_resolve_path_traversal_attack():
    """Test that path traversal attempts raise ValueError."""
    base = os.getcwd()
    target = "../../etc/passwd"
    with pytest.raises(ValueError, match="Security Violation"):
        safe_resolve_path(base, target)


def test_safe_resolve_path_complex_traversal():
    """Test complex traversal with dots and slashes."""
    base = os.getcwd()
    target = "subdir/../../../etc/passwd"
    with pytest.raises(ValueError, match="Security Violation"):
        safe_resolve_path(base, target)
