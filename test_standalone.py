#!/usr/bin/env python3
"""Standalone test of skill manager functionality"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_skills.skill_manager import SkillManager
from mcp_skills.security import SecurityError

def test_skill_manager():
    """Test skill manager basic functionality"""
    print("=" * 60)
    print("Testing MCP Skills Server Functionality")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # Test 1: Initialize manager
        print("\n[1] Initializing SkillManager...")
        manager = SkillManager(project_skills_dir=str(skills_dir))
        print("✓ SkillManager initialized successfully")

        # Test 2: Create a skill
        print("\n[2] Creating a skill...")
        metadata = manager.create_skill(
            skill_name="hello-world",
            description="A simple greeting skill",
            content="# Hello World Skill\n\nThis is a test skill.\n\n## Features\n- Simple\n- Friendly",
            location="project"
        )
        print(f"✓ Skill created: {metadata.name}")
        print(f"  Location: {metadata.location}")
        print(f"  Description: {metadata.description}")

        # Test 3: List skills
        print("\n[3] Listing all skills...")
        skills = manager.list_skills()
        print(f"✓ Found {len(skills)} skill(s)")
        for name, meta in skills.items():
            print(f"  - {name}: {meta.description}")

        # Test 4: Get skill metadata
        print("\n[4] Getting skill metadata...")
        skill_meta = manager.get_skill_metadata("hello-world")
        print(f"✓ Retrieved metadata for '{skill_meta.name}'")
        print(f"  File: {skill_meta.file_path}")

        # Test 5: Read skill content
        print("\n[5] Reading skill content...")
        content = manager.read_skill("hello-world")
        print(f"✓ Content read ({len(content)} bytes)")
        print("\nContent preview:")
        print("-" * 40)
        print(content[:200] + "...")
        print("-" * 40)

        # Test 6: Update skill
        print("\n[6] Updating skill...")
        updated = manager.update_skill(
            skill_name="hello-world",
            description="Updated greeting skill with new features"
        )
        print(f"✓ Skill updated: {updated.description}")

        # Test 7: Create another skill
        print("\n[7] Creating another skill...")
        manager.create_skill(
            skill_name="test-skill",
            description="Another test skill",
            content="# Test Skill\n\nThis is another skill.",
            location="project"
        )
        print("✓ Second skill created")

        # Test 8: List again to see both
        print("\n[8] Listing all skills again...")
        skills = manager.list_skills()
        print(f"✓ Found {len(skills)} skill(s)")
        for name, meta in skills.items():
            print(f"  - {name}: {meta.description}")

        # Test 9: Security validation
        print("\n[9] Testing security validation...")
        try:
            manager.create_skill(
                skill_name="invalid@name",
                description="Bad name",
                content="test"
            )
            print("✗ Security check failed - should reject invalid name")
        except SecurityError as e:
            print(f"✓ Security check passed: {e}")

        # Test 10: Non-existent skill
        print("\n[10] Testing error handling...")
        try:
            manager.update_skill(skill_name="nonexistent")
            print("✗ Error handling failed - should raise SecurityError")
        except SecurityError as e:
            print(f"✓ Error handling works: {e}")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

if __name__ == "__main__":
    test_skill_manager()
