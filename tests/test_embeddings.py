"""Tests for embedding-based search functionality"""

import pytest
from pathlib import Path
import tempfile
import json
import frontmatter

from mcp_skills.skill_manager import SkillManager
from mcp_skills.embeddings import SkillEmbeddingSearch, SearchResult, EMBEDDINGS_AVAILABLE


@pytest.fixture
def temp_skills_dir():
    """Create temporary skills directory with sample skills"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # Create several test skills with different content
        skills_data = [
            {
                "name": "security-audit",
                "description": "Audit security configurations and identify vulnerabilities",
                "content": "# Security Audit\n\nPerforms comprehensive security scanning and validation.",
                "tags": ["security", "audit"],
                "category": "security",
            },
            {
                "name": "deployment-automation",
                "description": "Automate deployment process for containerized applications",
                "content": "# Deployment Automation\n\nAutomates CI/CD pipelines.",
                "tags": ["deployment", "automation"],
                "category": "devops",
            },
            {
                "name": "testing-framework",
                "description": "Comprehensive testing framework for Python applications",
                "content": "# Testing Framework\n\nUnit and integration testing tools.",
                "tags": ["testing", "quality"],
                "category": "testing",
            },
            {
                "name": "validation-rules",
                "description": "Validate input data against security and compliance rules",
                "content": "# Validation Rules\n\nData validation and sanitization.",
                "tags": ["security", "validation"],
                "category": "security",
            },
        ]

        for skill_data in skills_data:
            skill_content = skill_data["content"]
            post = frontmatter.Post(skill_content)
            post.metadata["description"] = skill_data["description"]
            post.metadata["tags"] = skill_data["tags"]
            post.metadata["category"] = skill_data["category"]

            skill_path = skills_dir / f"{skill_data['name']}.md"
            with open(skill_path, "w") as f:
                f.write(frontmatter.dumps(post))

        yield skills_dir


@pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="Embeddings not available")
class TestSkillEmbeddingSearch:
    """Test embedding-based search"""

    def test_search_engine_initialization(self):
        """Test search engine can be initialized"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)
            assert search_engine is not None
            assert search_engine.embedding_dim == 384  # all-MiniLM-L6-v2

    def test_index_skill(self):
        """Test indexing a single skill"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            search_engine.index_skill(
                skill_name="test-skill",
                description="A test skill for validation",
                content="Test content here",
                location="project",
                tags=["testing", "validation"],
                category="test",
            )

            stats = search_engine.get_stats()
            assert stats["total_indexed_skills"] == 1
            assert stats["collection_count"] == 1

    def test_search_by_description(self):
        """Test semantic search finds skills by description meaning"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            # Index test skills
            search_engine.index_skill(
                skill_name="security-check",
                description="Check for security vulnerabilities and compliance issues",
                content="Security scanning",
                location="project",
            )

            search_engine.index_skill(
                skill_name="deployment",
                description="Deploy applications to cloud infrastructure",
                content="Deployment automation",
                location="project",
            )

            # Search for security-related skills
            results = search_engine.search("security validation")
            assert len(results) > 0
            # First result should be security-related
            assert results[0].name == "security-check"
            assert results[0].similarity_score > 0.5

    def test_search_with_tag_filter(self):
        """Test search with tag filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            # Index skills with tags
            search_engine.index_skill(
                skill_name="security-audit",
                description="Audit security configurations",
                location="project",
                tags=["security", "audit"],
            )

            search_engine.index_skill(
                skill_name="deployment-automation",
                description="Automate deployment",
                location="project",
                tags=["deployment", "automation"],
            )

            # Search with security tag filter
            results = search_engine.search(
                "automation",
                tags_filter=["security"],  # Should find nothing with security tag
            )
            # Should return empty or only security-tagged skills
            for result in results:
                assert "security" in result.tags

    def test_search_with_category_filter(self):
        """Test search with category filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            search_engine.index_skill(
                skill_name="security-scan",
                description="Security scanning tool",
                location="project",
                category="security",
            )

            search_engine.index_skill(
                skill_name="deploy-app",
                description="Deployment automation",
                location="project",
                category="devops",
            )

            # Search with category filter
            results = search_engine.search("automation", category_filter="devops")
            assert len(results) > 0
            assert all(r.category == "devops" for r in results)

    def test_search_with_location_filter(self):
        """Test search with location filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            search_engine.index_skill(
                skill_name="user-skill",
                description="User-level skill",
                location="user",
            )

            search_engine.index_skill(
                skill_name="project-skill",
                description="Project-level skill",
                location="project",
            )

            # Search with location filter
            results = search_engine.search("skill", location_filter="user")
            assert len(results) > 0
            assert all(r.location == "user" for r in results)

    def test_search_result_ordering(self):
        """Test that results are ordered by relevance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            # Index skills
            search_engine.index_skill(
                skill_name="security-audit",
                description="Security auditing and vulnerability assessment",
                content="Audit security systems",
            )

            search_engine.index_skill(
                skill_name="deployment",
                description="Deploy applications",
            )

            search_engine.index_skill(
                skill_name="code-review",
                description="Code review and quality checking",
            )

            # Search for security - should rank security-audit highest
            results = search_engine.search("security audit")
            assert len(results) > 0
            assert results[0].similarity_score >= results[-1].similarity_score

    def test_search_result_limit(self):
        """Test limit parameter works correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            # Index multiple skills
            for i in range(15):
                search_engine.index_skill(
                    skill_name=f"skill-{i}",
                    description=f"Skill number {i} for testing purposes",
                )

            # Search with limit
            results = search_engine.search("skill", limit=5)
            assert len(results) <= 5

    def test_delete_skill(self):
        """Test deleting a skill from index"""
        with tempfile.TemporaryDirectory() as tmpdir:
            search_engine = SkillEmbeddingSearch(persist_dir=tmpdir)

            search_engine.index_skill(
                skill_name="test-skill",
                description="Test skill to delete",
            )

            stats_before = search_engine.get_stats()
            assert stats_before["total_indexed_skills"] == 1

            search_engine.delete_skill("test-skill")

            stats_after = search_engine.get_stats()
            assert stats_after["total_indexed_skills"] == 0

    def test_search_result_to_dict(self):
        """Test SearchResult.to_dict() conversion"""
        result = SearchResult(
            name="test-skill",
            description="Test description",
            location="project",
            similarity_score=0.95,
            tags=["test"],
            category="testing",
        )

        result_dict = result.to_dict()
        assert result_dict["name"] == "test-skill"
        assert result_dict["description"] == "Test description"
        assert result_dict["location"] == "project"
        assert result_dict["similarity_score"] == 0.95
        assert result_dict["tags"] == ["test"]
        assert result_dict["category"] == "testing"


class TestSkillManagerWithSearch:
    """Test SkillManager integration with embeddings"""

    def test_skill_manager_search(self, temp_skills_dir):
        """Test SkillManager.search_skills() method"""
        if not EMBEDDINGS_AVAILABLE:
            pytest.skip("Embeddings not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(
                skills_paths=[str(temp_skills_dir)],
                enable_embeddings=True,
            )

            # Search for security-related skills
            results = manager.search_skills("security")
            assert len(results) > 0
            # Should find security-audit and validation-rules
            skill_names = [r.name for r in results]
            assert "security-audit" in skill_names

    def test_skill_manager_search_without_embeddings(self, temp_skills_dir):
        """Test keyword search fallback when embeddings disabled"""
        manager = SkillManager(
            skills_paths=[str(temp_skills_dir)],
            enable_embeddings=False,
        )

        # Keyword search should still work
        results = manager.search_skills("security")
        assert len(results) > 0
        skill_names = [r.name for r in results]
        assert "security-audit" in skill_names

    def test_skill_manager_search_with_filters(self, temp_skills_dir):
        """Test search with tag and category filters"""
        if not EMBEDDINGS_AVAILABLE:
            pytest.skip("Embeddings not available")

        manager = SkillManager(
            skills_paths=[str(temp_skills_dir)],
            enable_embeddings=True,
        )

        # Search with category filter
        results = manager.search_skills("automation", category="devops")
        assert len(results) > 0
        assert all(r.category == "devops" for r in results)

    def test_skill_manager_search_with_tags(self, temp_skills_dir):
        """Test search with tag filtering"""
        if not EMBEDDINGS_AVAILABLE:
            pytest.skip("Embeddings not available")

        manager = SkillManager(
            skills_paths=[str(temp_skills_dir)],
            enable_embeddings=True,
        )

        # Search with security tag
        results = manager.search_skills("rules", tags=["security"])
        assert len(results) > 0
        for result in results:
            assert "security" in result.tags

    def test_skill_metadata_with_enrichment(self, temp_skills_dir):
        """Test that skill metadata includes enrichment fields"""
        manager = SkillManager(
            skills_paths=[str(temp_skills_dir)],
            enable_embeddings=False,
        )

        metadata = manager.get_skill_metadata("security-audit")
        assert metadata is not None
        assert metadata.tags == ["security", "audit"]
        assert metadata.category == "security"

    def test_keyword_search_scoring(self, temp_skills_dir):
        """Test keyword search relevance scoring"""
        manager = SkillManager(
            skills_paths=[str(temp_skills_dir)],
            enable_embeddings=False,
        )

        # Search for "security" - security-audit should rank high
        results = manager.search_skills("security")
        assert len(results) > 0

        # First result should be a security-related skill
        assert results[0].similarity_score > 0

        # Results should be ordered by score
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)
