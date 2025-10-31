"""Security utilities for path validation and sanitization"""

import os
from pathlib import Path
from typing import Tuple


class SecurityError(Exception):
    """Raised when a security check fails"""
    pass


def resolve_and_validate_path(base_dir: str, relative_path: str) -> Path:
    """
    Resolve a path relative to base_dir and validate it's within base_dir.

    Args:
        base_dir: The base directory (e.g., skills directory)
        relative_path: The relative path requested

    Returns:
        Path: The validated absolute path

    Raises:
        SecurityError: If path traversal or other security issues detected
    """
    base = Path(base_dir).resolve()

    if not base.exists():
        raise SecurityError(f"Base directory does not exist: {base}")

    if not base.is_dir():
        raise SecurityError(f"Base path is not a directory: {base}")

    # Prevent path traversal attempts
    if ".." in relative_path or relative_path.startswith("/"):
        raise SecurityError("Path traversal detected")

    # Resolve the target path
    target = (base / relative_path).resolve()

    # Ensure target is within base directory
    if not str(target).startswith(str(base)):
        raise SecurityError("Path escapes base directory")

    return target


def validate_skill_path(skill_path: Path) -> None:
    """
    Validate that a skill path is safe to read.

    Args:
        skill_path: Path to skill file

    Raises:
        SecurityError: If validation fails
    """
    if not skill_path.exists():
        raise SecurityError(f"Skill file not found: {skill_path}")

    if not skill_path.is_file():
        raise SecurityError(f"Path is not a file: {skill_path}")

    if not skill_path.suffix == ".md":
        raise SecurityError(f"Skill must be a markdown file: {skill_path}")

    # Check for symlinks that escape the base directory
    if skill_path.is_symlink():
        target = skill_path.resolve()
        if not target.exists():
            raise SecurityError(f"Symlink points to non-existent file: {target}")


def validate_skill_name(name: str) -> None:
    """
    Validate that a skill name is safe.

    Args:
        name: Skill name to validate (can include nested paths like "category/my-skill")

    Raises:
        SecurityError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise SecurityError("Skill name must be a non-empty string")

    if len(name) > 255:
        raise SecurityError("Skill name too long (max 255 chars)")

    # Prevent path traversal attempts
    if ".." in name or name.startswith("/") or name.endswith("/"):
        raise SecurityError("Skill name contains invalid path patterns")

    # Allow alphanumeric, hyphens, underscores, and forward slashes for nesting
    if not all(c.isalnum() or c in "-_/" for c in name):
        raise SecurityError("Skill name contains invalid characters")


def validate_file_content(content: str, max_size: int = 10_000_000) -> None:
    """
    Validate file content.

    Args:
        content: File content to validate
        max_size: Maximum allowed size in bytes

    Raises:
        SecurityError: If content is invalid
    """
    if len(content.encode("utf-8")) > max_size:
        raise SecurityError(f"Content exceeds maximum size: {max_size} bytes")
