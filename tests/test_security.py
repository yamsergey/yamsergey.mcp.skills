"""Tests for security module"""

import pytest
from pathlib import Path
import tempfile

from mcp_skills.security import (
    resolve_and_validate_path,
    validate_skill_path,
    validate_skill_name,
    validate_file_content,
    SecurityError,
)


def test_resolve_and_validate_path_valid():
    """Test valid path resolution"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "test.md").touch()

        result = resolve_and_validate_path(str(base), "test.md")
        assert result.exists()
        assert str(result).startswith(str(base))


def test_resolve_and_validate_path_traversal():
    """Test path traversal prevention"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        with pytest.raises(SecurityError, match="Path traversal detected"):
            resolve_and_validate_path(str(base), "../outside")


def test_resolve_and_validate_path_escape():
    """Test path escape prevention"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        with pytest.raises(SecurityError, match="Path traversal detected"):
            resolve_and_validate_path(str(base), "../..")


def test_validate_skill_path_not_exists():
    """Test validation of non-existent file"""
    with pytest.raises(SecurityError, match="Skill file not found"):
        validate_skill_path(Path("/nonexistent/file.md"))


def test_validate_skill_path_not_file():
    """Test validation of directory instead of file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(SecurityError, match="Path is not a file"):
            validate_skill_path(Path(tmpdir))


def test_validate_skill_path_wrong_extension():
    """Test validation of non-markdown file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.touch()

        with pytest.raises(SecurityError, match="Skill must be a markdown file"):
            validate_skill_path(file_path)


def test_validate_skill_path_valid():
    """Test validation of valid skill file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.md"
        file_path.touch()

        # Should not raise
        validate_skill_path(file_path)


def test_validate_skill_name_valid():
    """Test validation of valid skill names"""
    for name in [
        "my-skill",
        "my_skill",
        "MySkill",
        "skill123",
        "category/my-skill",
        "category/subcategory/my-skill",
    ]:
        validate_skill_name(name)  # Should not raise


def test_validate_skill_name_invalid():
    """Test validation of invalid skill names"""
    invalid_names = [
        "",
        "skill@name",
        "skill.name",
        "skill name",
        "../skill",
        "/skill",
        "skill/",
        "a" * 256,
    ]

    for name in invalid_names:
        with pytest.raises(SecurityError):
            validate_skill_name(name)


def test_validate_file_content_valid():
    """Test validation of valid content"""
    content = "# Test Skill\n\nThis is a test skill."
    validate_file_content(content)  # Should not raise


def test_validate_file_content_too_large():
    """Test validation of oversized content"""
    content = "x" * 11_000_000

    with pytest.raises(SecurityError, match="Content exceeds maximum size"):
        validate_file_content(content)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
