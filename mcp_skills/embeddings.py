"""Semantic search engine using embeddings and vector database"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# Import SearchResult from skill_manager (shared between embeddings and keyword search)
from .skill_manager import SearchResult

logger = logging.getLogger(__name__)


class SkillEmbeddingSearch:
    """Semantic search engine for skills using embeddings and vector database"""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        enable_logging: bool = False,
    ):
        """
        Initialize embedding search engine.

        Args:
            persist_dir: Directory to persist Chroma database (optional, defaults to ~/.cache/mcp-skills)
            model_name: Sentence Transformer model to use
            enable_logging: Enable debug logging

        Raises:
            ImportError: If sentence-transformers or chromadb not installed
        """
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "Embeddings require: pip install 'mcp-skills[embeddings]' "
                "(sentence-transformers>=2.2.0 chromadb>=0.4.0)"
            )

        if enable_logging:
            logger.setLevel(logging.DEBUG)

        logger.debug(f"Initializing SkillEmbeddingSearch with model: {model_name}")

        # Load embedding model (caches after first download)
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.debug(f"Loaded model with {self.embedding_dim} dimensions")
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model {model_name}: {e}")

        # Initialize Chroma database
        if persist_dir is None:
            persist_dir = str(Path.home() / ".cache" / "mcp-skills")

        persist_path = Path(persist_dir)
        persist_path.mkdir(parents=True, exist_ok=True)

        try:
            settings = Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(persist_path),
                anonymized_telemetry=False,
                allow_reset=True,
            )
            self.client = chromadb.Client(settings)
            logger.debug(f"Chroma database initialized at {persist_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Chroma database: {e}")

        # Get or create collection for skills
        try:
            self.collection = self.client.get_or_create_collection(
                name="skills",
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )
            logger.debug("Skills collection created/loaded")
        except Exception as e:
            raise RuntimeError(f"Failed to create/load skills collection: {e}")

        # Track indexed skills to avoid duplicates
        self._indexed_skills = set()
        self._load_indexed_skills()

    def _load_indexed_skills(self) -> None:
        """Load set of already indexed skills from collection"""
        try:
            count = self.collection.count()
            if count > 0:
                # Get all IDs from collection
                all_data = self.collection.get()
                if all_data and all_data.get("ids"):
                    self._indexed_skills = set(all_data["ids"])
                    logger.debug(f"Loaded {len(self._indexed_skills)} existing indexed skills")
        except Exception as e:
            logger.warning(f"Could not load existing indexed skills: {e}")

    def index_skill(
        self,
        skill_name: str,
        description: str,
        content: str = "",
        location: str = "project",
        tags: Optional[List[str]] = None,
        category: str = "",
    ) -> None:
        """
        Add or update skill in embedding index.

        Args:
            skill_name: Unique skill identifier
            description: Short description (required for search)
            content: Full markdown content (optional, enriches embeddings)
            location: "user" or "project"
            tags: List of tags for filtering
            category: Category for filtering
        """
        if not skill_name or not description:
            logger.warning(f"Skipping skill {skill_name}: missing name or description")
            return

        try:
            # Combine text for embedding: name + description + first 1000 chars of content
            text_to_embed = f"{skill_name}. {description}"
            if content:
                # Take first 1000 chars of content (avoid huge documents)
                text_to_embed += f"\n\n{content[:1000]}"

            logger.debug(f"Embedding skill: {skill_name}")

            # Generate embedding
            embedding = self.model.encode(text_to_embed, convert_to_numpy=True)

            # Store in Chroma with metadata
            metadata = {
                "location": location,
                "tags": json.dumps(tags or []),
                "category": category,
                "description": description[:500],  # Store truncated description
            }

            # If skill exists, delete it first
            if skill_name in self._indexed_skills:
                self.collection.delete(ids=[skill_name])

            self.collection.add(
                ids=[skill_name],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                documents=[description],  # Also store raw text for context
            )

            self._indexed_skills.add(skill_name)
            logger.debug(f"Indexed skill: {skill_name}")

        except Exception as e:
            logger.error(f"Failed to index skill {skill_name}: {e}")

    def search(
        self,
        query: str,
        limit: int = 10,
        tags_filter: Optional[List[str]] = None,
        category_filter: Optional[str] = None,
        location_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search for skills using semantic embeddings.

        Args:
            query: Natural language search query
            limit: Max results to return (default: 10)
            tags_filter: Filter by tags (AND logic - skill must have ALL tags)
            category_filter: Filter by category
            location_filter: Filter by location ("user" or "project")

        Returns:
            Sorted list of SearchResult objects by relevance (highest score first)
        """
        if not query or not query.strip():
            logger.warning("Empty search query")
            return []

        try:
            logger.debug(f"Searching for: {query}")

            # Generate embedding for query
            query_embedding = self.model.encode(query, convert_to_numpy=True)

            # Build where clause for filtering
            where_clause = None
            if tags_filter or category_filter or location_filter:
                conditions = []

                if tags_filter:
                    # Filter by tags - each skill must have all requested tags
                    for tag in tags_filter:
                        conditions.append({"tags": {"$contains": tag}})

                if category_filter:
                    conditions.append({"category": {"$eq": category_filter}})

                if location_filter:
                    conditions.append({"location": {"$eq": location_filter}})

                # Combine conditions (AND logic)
                if conditions:
                    where_clause = (
                        {"$and": conditions} if len(conditions) > 1 else conditions[0]
                    )

            logger.debug(f"Search filters: tags={tags_filter}, category={category_filter}, location={location_filter}")

            # Query Chroma - request more results to account for filtering
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(limit * 3, 100),  # Get more, filter down
                where=where_clause,
                include=["metadatas", "documents", "distances"],
            )

            # Convert distances to similarity scores
            search_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, skill_id in enumerate(results["ids"][0]):
                    # Chroma returns distances; convert to similarity
                    # For cosine distance: similarity = 1 - distance
                    distance = results["distances"][0][i]
                    similarity = max(0, 1 - distance)  # Clamp to [0, 1]

                    metadata = results["metadatas"][0][i]

                    search_results.append(
                        SearchResult(
                            name=skill_id,
                            description=metadata.get("description", ""),
                            location=metadata.get("location", "project"),
                            similarity_score=float(similarity),
                            tags=json.loads(metadata.get("tags", "[]")),
                            category=metadata.get("category", ""),
                        )
                    )

            # Return top N results
            result_list = search_results[:limit]
            logger.debug(f"Search returned {len(result_list)} results")
            return result_list

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    def delete_skill(self, skill_name: str) -> None:
        """Remove skill from index"""
        try:
            if skill_name in self._indexed_skills:
                self.collection.delete(ids=[skill_name])
                self._indexed_skills.discard(skill_name)
                logger.debug(f"Deleted skill from index: {skill_name}")
        except Exception as e:
            logger.error(f"Failed to delete skill {skill_name}: {e}")

    def rebuild_index(
        self, skills_data: Dict[str, Dict]
    ) -> None:
        """
        Rebuild entire index from scratch.

        Args:
            skills_data: Dict of skill_name -> {
                'description': str,
                'content': str,
                'location': str,
                'tags': List[str],
                'category': str,
            }
        """
        logger.info(f"Rebuilding index with {len(skills_data)} skills")
        try:
            # Clear existing collection
            self.collection.delete(where={})
            self._indexed_skills.clear()

            # Re-index all skills
            for skill_name, data in skills_data.items():
                self.index_skill(
                    skill_name=skill_name,
                    description=data.get("description", ""),
                    content=data.get("content", ""),
                    location=data.get("location", "project"),
                    tags=data.get("tags", []),
                    category=data.get("category", ""),
                )

            logger.info(f"Index rebuild complete: {len(self._indexed_skills)} skills indexed")

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")

    def get_stats(self) -> Dict:
        """Get index statistics"""
        try:
            return {
                "total_indexed_skills": len(self._indexed_skills),
                "embedding_dimension": self.embedding_dim,
                "model_name": self.model.get_sentence_embedding_dimension(),
                "collection_count": self.collection.count(),
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_indexed_skills": len(self._indexed_skills),
                "error": str(e),
            }


def create_search_engine(
    persist_dir: Optional[str] = None,
    model_name: str = "all-MiniLM-L6-v2",
) -> Optional[SkillEmbeddingSearch]:
    """
    Factory function to safely create search engine.

    Returns None if embeddings not available, allowing graceful fallback.

    Args:
        persist_dir: Directory to persist vector database
        model_name: Embedding model name

    Returns:
        SkillEmbeddingSearch instance or None if unavailable
    """
    if not EMBEDDINGS_AVAILABLE:
        logger.warning(
            "Embeddings not available. Install with: pip install 'mcp-skills[embeddings]'"
        )
        return None

    try:
        return SkillEmbeddingSearch(persist_dir=persist_dir, model_name=model_name)
    except Exception as e:
        logger.error(f"Failed to create search engine: {e}")
        return None
