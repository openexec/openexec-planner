"""Utility functions for OpenExec Orchestration."""

from pathlib import Path


def safe_resolve_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """Resolve a target path relative to a base directory safely.

    Prevents path traversal attacks by ensuring the resolved path is
    within the base directory.

    Args:
        base_dir: The directory that should contain the target
        target_path: The path to resolve (can be absolute or relative)

    Returns:
        The absolute resolved path

    Raises:
        ValueError: If the target path is outside the base directory
    """
    base = Path(base_dir).resolve()
    # Handle target path
    target = Path(target_path)

    if target.is_absolute():
        # Resolve target to handle symlinks (like /tmp -> /private/tmp)
        resolved_target = target.resolve()
        # Try to make it relative to base if it's already inside
        try:
            target = resolved_target.relative_to(base)
        except ValueError:
            # If not inside, just use the name to be safe
            target = Path(target.name)

    resolved = (base / target).resolve()

    if not resolved.is_relative_to(base):
        raise ValueError(f"Security Violation: Path traversal attempt detected: {target_path}")

    return resolved
