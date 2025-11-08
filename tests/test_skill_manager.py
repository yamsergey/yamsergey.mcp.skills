"""Tests for skill manager"""

import pytest
from pathlib import Path
import tempfile
import frontmatter

from mcp_skills.skill_manager import SkillManager, SkillMetadata
from mcp_skills.security import SecurityError


@pytest.fixture
def temp_skills_dir():
    """Create temporary skills directory with sample skills"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # Create a sample skill
        skill_content = "# Test Skill\n\nThis is a test skill for demonstration."
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = "A test skill"

        skill_path = skills_dir / "test-skill.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

        yield skills_dir


def test_skill_manager_init(temp_skills_dir):
    """Test skill manager initialization"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False  # Disable embeddings for faster test
    )
    skills = manager.list_skills()

    assert len(skills) == 1
    assert "test-skill" in skills


def test_skill_manager_metadata_extraction(temp_skills_dir):
    """Test metadata extraction from skill files"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )
    metadata = manager.get_skill_metadata("test-skill")

    assert metadata is not None
    assert metadata.name == "test-skill"
    assert metadata.description == "A test skill"
    assert metadata.location == str(temp_skills_dir)


def test_read_skill(temp_skills_dir):
    """Test reading skill content"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )
    content = manager.read_skill("test-skill")

    assert "Test Skill" in content
    assert "test skill for demonstration" in content


def test_read_skill_not_found(temp_skills_dir):
    """Test reading non-existent skill"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError, match="Skill not found"):
        manager.read_skill("nonexistent")


def test_create_skill(temp_skills_dir):
    """Test creating a new skill"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )

    metadata = manager.create_skill(
        skill_name="new-skill",
        description="A newly created skill",
        content="# New Skill\n\nContent here",
        location=str(temp_skills_dir),
    )

    assert metadata.name == "new-skill"
    assert metadata.description == "A newly created skill"

    # Verify it's in cache
    assert manager.get_skill_metadata("new-skill") is not None

    # Verify file exists
    skill_path = temp_skills_dir / "new-skill.md"
    assert skill_path.exists()

    # Verify content
    content = manager.read_skill("new-skill")
    assert "New Skill" in content


def test_create_skill_duplicate(temp_skills_dir):
    """Test creating duplicate skill fails"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError, match="Skill already exists"):
        manager.create_skill(
            skill_name="test-skill",
            description="Duplicate",
            content="# Content",
            location=str(temp_skills_dir),
        )


def test_create_skill_invalid_name(temp_skills_dir):
    """Test creating skill with invalid name"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError):
        manager.create_skill(
            skill_name="invalid@name",
            description="Test",
            content="# Content",
        )


def test_update_skill(temp_skills_dir):
    """Test updating skill"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )

    metadata = manager.update_skill(
        skill_name="test-skill",
        description="Updated description",
        content="# Updated\n\nNew content here",
    )

    assert metadata.description == "Updated description"

    # Verify updates persisted
    content = manager.read_skill("test-skill")
    assert "Updated" in content
    assert "New content here" in content


def test_update_skill_not_found(temp_skills_dir):
    """Test updating non-existent skill"""
    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError, match="Skill not found"):
        manager.update_skill(skill_name="nonexistent", description="New description")


def test_multiple_skills_discovery(temp_skills_dir):
    """Test discovering multiple skills"""
    # Create additional skills
    for i in range(3):
        skill_content = f"# Skill {i}\n\nContent {i}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {i} description"

        skill_path = temp_skills_dir / f"skill-{i}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    manager = SkillManager(
        skills_paths=[str(temp_skills_dir)],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    assert len(skills) == 4  # test-skill + 3 new skills


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
