"""Skill discovery, loading, and management"""

import os
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import frontmatter

from .security import (
    resolve_and_validate_path,
    validate_skill_path,
    validate_skill_name,
    SecurityError,
)


@dataclass
class SkillMetadata:
    """Metadata for a skill"""

    name: str
    description: str
    file_path: Path
    location: str  # "user" or "project"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "location": self.location,
        }


class SkillManager:
    """Manages skill discovery and loading"""

    def __init__(self, user_skills_dir: Optional[str] = None, project_skills_dir: Optional[str] = None):
        """
        Initialize skill manager.

        Args:
            user_skills_dir: Path to user skills directory (defaults to ~/.claude/skills)
            project_skills_dir: Path to project skills directory (defaults to ./.claude/skills)
        """
        self.user_skills_dir = Path(user_skills_dir or "~/.claude/skills").expanduser()
        self.project_skills_dir = Path(project_skills_dir or "./.claude/skills")

        # Metadata cache: skill_name -> SkillMetadata
        self._metadata_cache: Dict[str, SkillMetadata] = {}

        # Discover skills on init
        self._discover_skills()

    def _discover_skills(self) -> None:
        """Discover all available skills"""
        self._metadata_cache.clear()

        # Discover user skills
        if self.user_skills_dir.exists():
            self._scan_directory(self.user_skills_dir, "user")

        # Discover project skills
        if self.project_skills_dir.exists():
            self._scan_directory(self.project_skills_dir, "project")

    def _scan_directory(self, directory: Path, location: str) -> None:
        """Scan a directory for skill files (recursively)"""
        try:
            # First try to find SKILL.md files in subdirectories (Anthropic agent skills format)
            for skill_file in directory.glob("*/SKILL.md"):
                try:
                    # Use parent directory name as skill name for nested skills
                    metadata = self._extract_metadata(skill_file, location, use_parent_name=True)
                    self._metadata_cache[metadata.name] = metadata
                except Exception as e:
                    # Skip files with parse errors, log them
                    print(f"Warning: Failed to parse skill {skill_file}: {e}")

            # Also find top-level .md files (for flat skill directory structure)
            # Skip common non-skill files
            skip_files = {'README', 'THIRD_PARTY_NOTICES', 'agent_skills_spec', 'LICENSE', 'CHANGELOG'}
            for file_path in directory.glob("*.md"):
                # Skip if filename (without .md) is in skip list
                if file_path.stem not in skip_files:
                    try:
                        metadata = self._extract_metadata(file_path, location)
                        self._metadata_cache[metadata.name] = metadata
                    except Exception as e:
                        # Skip files with parse errors, log them
                        print(f"Warning: Failed to parse skill {file_path}: {e}")
        except Exception as e:
            print(f"Warning: Failed to scan directory {directory}: {e}")

    def _extract_metadata(self, file_path: Path, location: str, use_parent_name: bool = False) -> SkillMetadata:
        """Extract metadata from a skill file"""
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Use parent directory name as skill name if use_parent_name is True (for SKILL.md files)
        # Otherwise use filename (without .md)
        if use_parent_name:
            skill_name = file_path.parent.name
        else:
            skill_name = file_path.stem

        # Extract description from frontmatter or content
        description = post.metadata.get("description", "")
        if not description and post.content:
            # Use first non-empty line as fallback
            for line in post.content.split("\n"):
                if line.strip():
                    description = line.strip()[:200]
                    break

        return SkillMetadata(
            name=skill_name,
            description=description,
            file_path=file_path,
            location=location,
        )

    def list_skills(self) -> Dict[str, SkillMetadata]:
        """Get all available skills metadata"""
        return dict(self._metadata_cache)

    def get_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill"""
        return self._metadata_cache.get(skill_name)

    def read_skill(self, skill_name: str) -> str:
        """
        Read full content of a skill file.

        Args:
            skill_name: Name of the skill

        Returns:
            Full markdown content of the skill

        Raises:
            SecurityError: If skill not found or path is invalid
        """
        metadata = self.get_skill_metadata(skill_name)
        if not metadata:
            raise SecurityError(f"Skill not found: {skill_name}")

        try:
            validate_skill_path(metadata.file_path)
            with open(metadata.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise SecurityError(f"Failed to read skill {skill_name}: {e}")

    def create_skill(
        self,
        skill_name: str,
        description: str,
        content: str,
        location: str = "project",
    ) -> SkillMetadata:
        """
        Create a new skill file.

        Args:
            skill_name: Name for the skill
            description: Description of the skill
            content: Full markdown content (without frontmatter)
            location: "user" or "project"

        Returns:
            SkillMetadata for the created skill

        Raises:
            SecurityError: If validation fails
        """
        validate_skill_name(skill_name)

        # Determine target directory
        if location == "user":
            target_dir = self.user_skills_dir
        elif location == "project":
            target_dir = self.project_skills_dir
        else:
            raise SecurityError(f"Invalid location: {location}")

        # Create directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / f"{skill_name}.md"

        if file_path.exists():
            raise SecurityError(f"Skill already exists: {skill_name}")

        # Create frontmatter
        post = frontmatter.Post(content)
        post.metadata["description"] = description

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        # Update cache
        metadata = SkillMetadata(
            name=skill_name,
            description=description,
            file_path=file_path,
            location=location,
        )
        self._metadata_cache[skill_name] = metadata

        return metadata

    def update_skill(
        self,
        skill_name: str,
        description: Optional[str] = None,
        content: Optional[str] = None,
    ) -> SkillMetadata:
        """
        Update an existing skill.

        Args:
            skill_name: Name of the skill to update
            description: New description (optional)
            content: New content (optional)

        Returns:
            Updated SkillMetadata

        Raises:
            SecurityError: If skill not found or update fails
        """
        metadata = self.get_skill_metadata(skill_name)
        if not metadata:
            raise SecurityError(f"Skill not found: {skill_name}")

        try:
            validate_skill_path(metadata.file_path)

            # Read current file
            with open(metadata.file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Update fields
            if description is not None:
                post.metadata["description"] = description
                metadata.description = description

            if content is not None:
                post.content = content

            # Write file
            with open(metadata.file_path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            # Update cache
            self._metadata_cache[skill_name] = metadata

            return metadata
        except Exception as e:
            raise SecurityError(f"Failed to update skill {skill_name}: {e}")
