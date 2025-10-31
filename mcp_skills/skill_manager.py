"""Skill discovery, loading, and management"""

import os
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field
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

    # Optional enrichment fields
    tags: List[str] = field(default_factory=list)
    category: str = ""
    keywords: List[str] = field(default_factory=list)
    use_case: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "tags": self.tags,
            "category": self.category,
            "keywords": self.keywords[:5],  # Only top 5 keywords for API
            "use_case": self.use_case,
        }


class SkillManager:
    """Manages skill discovery and loading"""

    def __init__(
        self,
        user_skills_dir: Optional[str] = None,
        project_skills_dir: Optional[str] = None,
        enable_embeddings: bool = True,
    ):
        """
        Initialize skill manager.

        Args:
            user_skills_dir: Path to user skills directory (defaults to ~/.claude/skills)
            project_skills_dir: Path to project skills directory (defaults to ./.claude/skills)
            enable_embeddings: Enable semantic search with embeddings (default: True)
        """
        self.user_skills_dir = Path(user_skills_dir or "~/.claude/skills").expanduser()
        self.project_skills_dir = Path(project_skills_dir or "./.claude/skills")

        # Metadata cache: skill_name -> SkillMetadata
        self._metadata_cache: Dict[str, SkillMetadata] = {}

        # Initialize embedding search if enabled
        self.search_engine = None
        if enable_embeddings:
            from .embeddings import create_search_engine
            persist_dir = str(Path.home() / ".cache" / "mcp-skills")
            self.search_engine = create_search_engine(persist_dir=persist_dir)

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

        # Index skills for semantic search after discovery
        self._index_skills_embeddings()

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

        # Extract optional enrichment fields from frontmatter
        tags = post.metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        category = post.metadata.get("category", "")
        keywords = post.metadata.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",")]

        use_case = post.metadata.get("use_case", "")

        return SkillMetadata(
            name=skill_name,
            description=description,
            file_path=file_path,
            location=location,
            tags=tags,
            category=category,
            keywords=keywords,
            use_case=use_case,
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
            skill_name: Name for the skill (can include nested paths like "category/my-skill")
            description: Description of the skill
            content: Full markdown content (without frontmatter)
            location: "user" or "project"

        Returns:
            SkillMetadata for the created skill

        Raises:
            SecurityError: If validation fails
        """
        validate_skill_name(skill_name)

        # Determine base directory
        if location == "user":
            base_dir = self.user_skills_dir
        elif location == "project":
            base_dir = self.project_skills_dir
        else:
            raise SecurityError(f"Invalid location: {location}")

        # Handle nested paths (e.g., "category/my-skill")
        parts = skill_name.split("/")
        file_name = f"{parts[-1]}.md"
        relative_dir = "/".join(parts[:-1]) if len(parts) > 1 else ""

        # Resolve and validate the final path to prevent directory traversal
        if relative_dir:
            target_dir = resolve_and_validate_path(base_dir, relative_dir)
        else:
            target_dir = base_dir

        # Create directory structure if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / file_name

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

    def search_skills(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        location: Optional[str] = None,
    ) -> List:
        """
        Search for skills using semantic embeddings or keyword search fallback.

        Args:
            query: Natural language search query
            limit: Max results to return (default: 10)
            tags: Filter by tags (optional, AND logic)
            category: Filter by category (optional)
            location: Filter by location ("user" or "project")

        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not self.search_engine:
            # Fallback: simple keyword search
            return self._search_skills_keyword(query, limit, tags, category, location)

        return self.search_engine.search(
            query=query,
            limit=limit,
            tags_filter=tags,
            category_filter=category,
            location_filter=location,
        )

    def _search_skills_keyword(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        location: Optional[str] = None,
    ) -> List:
        """Fallback keyword search when embeddings not available"""
        from .embeddings import SearchResult

        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for skill_name, metadata in self._metadata_cache.items():
            # Apply filters first
            if location and metadata.location != location:
                continue
            if category and metadata.category != category:
                continue
            if tags:
                # All requested tags must be present
                if not all(tag in metadata.tags for tag in tags):
                    continue

            # Calculate relevance score
            score = 0

            # Name match: highest priority
            if query_lower in skill_name.lower():
                score += 3
            # Word-by-word name matching
            for word in query_words:
                if word in skill_name.lower():
                    score += 1

            # Description match
            desc_lower = metadata.description.lower()
            if query_lower in desc_lower:
                score += 2
            for word in query_words:
                if word in desc_lower:
                    score += 0.5

            # Tag matching
            for tag in metadata.tags:
                if query_lower in tag.lower():
                    score += 1.5

            if score > 0:
                results.append(
                    SearchResult(
                        name=skill_name,
                        description=metadata.description,
                        location=metadata.location,
                        similarity_score=min(score / 5, 1.0),  # Normalize to 0-1
                        tags=metadata.tags,
                        category=metadata.category,
                    )
                )

        # Sort by score (descending)
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]

    def _index_skills_embeddings(self) -> None:
        """Index all discovered skills for semantic search"""
        if not self.search_engine:
            return

        for skill_name, metadata in self._metadata_cache.items():
            try:
                # Read content for better embeddings
                content = self.read_skill(skill_name)
                self.search_engine.index_skill(
                    skill_name=skill_name,
                    description=metadata.description,
                    content=content,
                    location=metadata.location,
                    tags=metadata.tags,
                    category=metadata.category,
                )
            except Exception as e:
                print(f"Warning: Failed to index skill {skill_name}: {e}")
