"""Tests for skill manager"""

import pytest
from pathlib import Path
import tempfile
import frontmatter

from mcp_skills.skill_manager import SkillManager, SkillMetadata, SkillPath
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
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False  # Disable embeddings for faster test
    )
    skills = manager.list_skills()

    assert len(skills) == 1
    assert "test-skill" in skills


def test_skill_manager_metadata_extraction(temp_skills_dir):
    """Test metadata extraction from skill files"""
    manager = SkillManager(
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )
    metadata = manager.get_skill_metadata("test-skill")

    assert metadata is not None
    assert metadata.name == "test-skill"
    assert metadata.description == "A test skill"
    assert metadata.location == "test"


def test_read_skill(temp_skills_dir):
    """Test reading skill content"""
    manager = SkillManager(
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )
    content = manager.read_skill("test-skill")

    assert "Test Skill" in content
    assert "test skill for demonstration" in content


def test_read_skill_not_found(temp_skills_dir):
    """Test reading non-existent skill"""
    manager = SkillManager(
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError, match="Skill not found"):
        manager.read_skill("nonexistent")


def test_create_skill(temp_skills_dir):
    """Test creating a new skill"""
    manager = SkillManager(
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )

    metadata = manager.create_skill(
        skill_name="new-skill",
        description="A newly created skill",
        content="# New Skill\n\nContent here",
        location="test",
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
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError, match="Skill already exists"):
        manager.create_skill(
            skill_name="test-skill",
            description="Duplicate",
            content="# Content",
            location="test",
        )


def test_create_skill_invalid_name(temp_skills_dir):
    """Test creating skill with invalid name"""
    manager = SkillManager(
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )

    with pytest.raises(SecurityError):
        manager.create_skill(
            skill_name="invalid@name",
            description="Test",
            content="# Content",
            location="test",
        )


def test_update_skill(temp_skills_dir):
    """Test updating skill"""
    manager = SkillManager(
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
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
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
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
        skills_paths=[SkillPath(nickname="test", path=str(temp_skills_dir), readonly=False)],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    assert len(skills) == 4  # test-skill + 3 new skills


def test_pattern_filtering(temp_skills_dir):
    """Test pattern filtering for skills"""
    # Create skills with different prefixes
    prefixes = ["security_audit", "security_scan", "devops_deploy", "devops_monitor", "generic_skill"]
    for prefix in prefixes:
        skill_content = f"# {prefix}\n\nContent for {prefix}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {prefix}"

        skill_path = temp_skills_dir / f"{prefix}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Create manager with pattern filter for security skills
    manager = SkillManager(
        skills_paths=[
            SkillPath(
                nickname="security",
                path=str(temp_skills_dir),
                readonly=True,
                pattern="^security_.*"
            )
        ],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    # Should only find security_ prefixed skills
    assert len(skills) == 2
    assert "security_audit" in skills
    assert "security_scan" in skills
    assert "devops_deploy" not in skills
    assert "generic_skill" not in skills


def test_multiple_inclusion_patterns(temp_skills_dir):
    """Test multiple inclusion patterns using alternation"""
    # Create skills with different prefixes
    skills_to_create = [
        "security_audit",
        "audit_scan",
        "compliance_check",
        "devops_deploy",
        "generic_skill",
    ]
    for skill_name in skills_to_create:
        skill_content = f"# {skill_name}\n\nContent for {skill_name}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {skill_name}"

        skill_path = temp_skills_dir / f"{skill_name}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Create manager with multiple inclusion patterns
    manager = SkillManager(
        skills_paths=[
            SkillPath(
                nickname="compliance",
                path=str(temp_skills_dir),
                readonly=True,
                pattern="^security_.*|^audit_.*|^compliance_.*"
            )
        ],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    # Should find all skills matching any of the inclusion patterns
    assert len(skills) == 3
    assert "security_audit" in skills
    assert "audit_scan" in skills
    assert "compliance_check" in skills
    assert "devops_deploy" not in skills
    assert "generic_skill" not in skills


def test_pattern_filtering_multiple_paths(temp_skills_dir):
    """Test pattern filtering with multiple skill paths"""
    # Create skills with different prefixes
    prefixes = ["security_audit", "security_scan", "devops_deploy", "devops_monitor"]
    for prefix in prefixes:
        skill_content = f"# {prefix}\n\nContent for {prefix}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {prefix}"

        skill_path = temp_skills_dir / f"{prefix}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Create manager with multiple pattern filters
    manager = SkillManager(
        skills_paths=[
            SkillPath(
                nickname="security",
                path=str(temp_skills_dir),
                readonly=True,
                pattern="^security_.*"
            ),
            SkillPath(
                nickname="devops",
                path=str(temp_skills_dir),
                readonly=False,
                pattern="^devops_.*"
            )
        ],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    # Should find all skills that match at least one pattern
    assert len(skills) == 4
    assert "security_audit" in skills
    assert "security_scan" in skills
    assert "devops_deploy" in skills
    assert "devops_monitor" in skills


def test_exclude_pattern_filtering(temp_skills_dir):
    """Test exclude pattern filtering for skills"""
    # Create skills with various suffixes
    skills_to_create = [
        "security_audit",
        "security_deprecated",
        "security_experimental",
        "security_scan",
        "generic_skill",
    ]
    for skill_name in skills_to_create:
        skill_content = f"# {skill_name}\n\nContent for {skill_name}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {skill_name}"

        skill_path = temp_skills_dir / f"{skill_name}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Create manager with exclude pattern to filter out deprecated/experimental
    manager = SkillManager(
        skills_paths=[
            SkillPath(
                nickname="project",
                path=str(temp_skills_dir),
                readonly=False,
                exclude_pattern=".*_deprecated$|.*_experimental$"
            )
        ],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    # Should find all skills except those matching exclude pattern
    # (includes test-skill from fixture)
    assert len(skills) == 4
    assert "security_audit" in skills
    assert "security_scan" in skills
    assert "generic_skill" in skills
    assert "test-skill" in skills
    assert "security_deprecated" not in skills
    assert "security_experimental" not in skills


def test_include_and_exclude_patterns(temp_skills_dir):
    """Test combining both include and exclude patterns"""
    # Create production and test skills
    skills_to_create = [
        "prod_audit",
        "prod_audit_testing",
        "prod_scan",
        "prod_deprecated",
        "dev_audit",
        "generic_skill",
    ]
    for skill_name in skills_to_create:
        skill_content = f"# {skill_name}\n\nContent for {skill_name}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {skill_name}"

        skill_path = temp_skills_dir / f"{skill_name}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Create manager with both include and exclude patterns
    manager = SkillManager(
        skills_paths=[
            SkillPath(
                nickname="production",
                path=str(temp_skills_dir),
                readonly=True,
                pattern="^prod_.*",
                exclude_pattern=".*_testing$|.*_deprecated$"
            )
        ],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    # Should find only prod_ skills, excluding test and deprecated ones
    assert len(skills) == 2
    assert "prod_audit" in skills
    assert "prod_scan" in skills
    assert "prod_audit_testing" not in skills
    assert "prod_deprecated" not in skills
    assert "dev_audit" not in skills
    assert "generic_skill" not in skills


def test_exclude_pattern_with_none_include_pattern(temp_skills_dir):
    """Test that exclude pattern works without include pattern"""
    # Create skills with mixed names
    skills_to_create = [
        "audit_skill",
        "scan_skill",
        "audit_deprecated",
        "scan_experimental",
    ]
    for skill_name in skills_to_create:
        skill_content = f"# {skill_name}\n\nContent for {skill_name}"
        post = frontmatter.Post(skill_content)
        post.metadata["description"] = f"Skill {skill_name}"

        skill_path = temp_skills_dir / f"{skill_name}.md"
        with open(skill_path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Create manager with only exclude pattern (no include pattern)
    manager = SkillManager(
        skills_paths=[
            SkillPath(
                nickname="project",
                path=str(temp_skills_dir),
                readonly=False,
                exclude_pattern=".*_deprecated$|.*_experimental$"
            )
        ],
        enable_embeddings=False
    )
    skills = manager.list_skills()

    # Should find all skills except those matching exclude pattern
    # (includes test-skill from fixture)
    assert len(skills) == 3
    assert "audit_skill" in skills
    assert "scan_skill" in skills
    assert "test-skill" in skills
    assert "audit_deprecated" not in skills
    assert "scan_experimental" not in skills


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
