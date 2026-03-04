"""Utility functions for OpenExec Orchestration."""

import os
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
    # Handle absolute target paths by making them relative to root first
    target = Path(target_path)
    if target.is_absolute():
        # Try to make it relative to base if it's already inside
        try:
            target = target.relative_to(base)
        except ValueError:
            # If not inside, just use the name to be safe
            target = target.name
            
    resolved = (base / target).resolve()
    
    if not resolved.is_relative_to(base):
        raise ValueError(f"Security Violation: Path traversal attempt detected: {target_path}")
        
    return resolved
