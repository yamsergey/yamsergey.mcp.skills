# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP Skills Server** is a Python-based Model Context Protocol (MCP) server that exposes Anthropic Claude Code Skills as MCP tools. It enables skill discovery, management (CRUD operations), and access through the MCP interface.

**Key Purpose**: Bridge Claude Code Skills (markdown files with YAML frontmatter) and MCP clients by automatically discovering skills and exposing them as callable tools.

## Development Commands

### Setup and Installation

```bash
# Install from source in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=mcp_skills

# Run specific test file
pytest tests/test_security.py -v

# Run specific test
pytest tests/test_skill_manager.py::test_skill_manager_init -v
```

### Running the Server

```bash
# Default directories (~/.claude/skills and ./.claude/skills)
mcp-skills

# With custom directories
mcp-skills --user-skills /path/to/user/skills --project-skills /path/to/project/skills

# Debug: Direct Python invocation
python -m mcp_skills.server
```

### Development Utilities

- `test_standalone.py`: Standalone testing of SkillManager without MCP
- `test_mcp_server.py`: Testing MCP server functionality
- `debug_mcp.py`: Debug utilities for MCP protocol
- `test_stdio.py`: Testing stdio-based MCP communication

### Installing with Semantic Search

```bash
# Install with embeddings support (semantic search via embeddings)
pip install -e ".[embeddings]"

# Install with all dev dependencies including embeddings
pip install -e ".[dev]"

# Note: Embeddings optional. System works with keyword-based fallback if embeddings unavailable.
```

## Architecture

The server follows a layered architecture:

1. **Entry Point** (`mcp_skills/server.py:main`): CLI argument parsing for skill directory paths
2. **MCP Server** (`mcp_skills/server.py:SkillsServer`):
   - Handles MCP protocol communication via stdio
   - Registers skill tools dynamically based on discovered skills
   - Routes tool calls to handlers for skill reading or management operations
3. **Skill Manager** (`mcp_skills/skill_manager.py:SkillManager`):
   - Discovers skills from two locations: user (`~/.claude/skills`) and project (`./.claude/skills`)
   - Maintains metadata cache for efficient lookups
   - Supports both flat (top-level `.md` files) and nested (subdirectories with `SKILL.md`) skill structures
   - Implements CRUD operations using python-frontmatter for parsing/writing YAML metadata
4. **Security Layer** (`mcp_skills/security.py`):
   - Path traversal prevention
   - Filename validation
   - Symlink validation
   - File size limits (10MB default)

### Data Flow

1. **Startup**: SkillManager scans both skill directories, extracts metadata from frontmatter, caches it
2. **Tool Registration**: SkillsServer creates MCP tools from cached metadata (lazy loading strategy)
3. **Tool Invocation**: Handlers read full skill content on-demand, validate paths, return formatted output

### Skill File Format

Markdown files with YAML frontmatter:
```markdown
---
description: Brief skill description
---

# Skill Title (optional, derived from filename or parent dir)

Content here...
```

**Naming Conventions**:
- Flat structure: `skill-name.md` (name derived from filename without `.md`)
- Nested structure: `skill-dir/SKILL.md` (name derived from parent directory name)
- Skill names must be alphanumeric with hyphens/underscores only

### Skill Discovery

Scans occur at SkillManager initialization:
1. User skills: `~/.claude/skills` - searches for `*/SKILL.md` and `*.md` files
2. Project skills: `./.claude/skills` - searches for `*/SKILL.md` and `*.md` files
3. Skips: README.md, LICENSE, CHANGELOG, THIRD_PARTY_NOTICES, agent_skills_spec.md

## Key Classes and Modules

### SkillManager (`mcp_skills/skill_manager.py`)

- `__init__(user_skills_dir, project_skills_dir)`: Initialize with custom paths or defaults
- `list_skills()`: Return Dict[str, SkillMetadata] from cache
- `get_skill_metadata(skill_name)`: Lookup single skill metadata
- `read_skill(skill_name)`: Read full markdown content with validation
- `create_skill(name, description, content, location)`: Create new skill file
- `update_skill(name, description=None, content=None)`: Update existing skill
- `_discover_skills()`: Scan directories and populate cache (called on init)
- `_scan_directory(directory, location)`: Recursively find skill files
- `_extract_metadata(file_path, location, use_parent_name)`: Parse frontmatter

### SkillsServer (`mcp_skills/server.py`)

- `__init__(user_skills_dir, project_skills_dir)`: Initialize MCP server with SkillManager
- `_list_tools_handler()`: MCP handler - returns Tool objects for all skills + management tools
- `_call_tool_handler(name, arguments)`: MCP handler - routes to appropriate handler
- `_handle_read_skill(skill_name, arguments)`: Read and format skill content
- `_handle_list_skills(arguments)`: Return skills metadata as JSON
- `_handle_create_skill(arguments)`: Create skill with validation
- `_handle_update_skill(arguments)`: Update skill with validation
- `run()`: Start stdio MCP server
- `_get_management_tools()`: Define create_skill, update_skill, list_skills MCP tools

### SkillMetadata (`mcp_skills/skill_manager.py`)

Dataclass holding:
- `name`: Skill name (string)
- `description`: From frontmatter or first line of content
- `file_path`: Path object to the skill file
- `location`: "user" or "project"
- `to_dict()`: Convert to JSON-serializable dict

### Security Module (`mcp_skills/security.py`)

- `resolve_and_validate_path(base_dir, relative_path)`: Prevent path traversal
- `validate_skill_path(skill_path)`: Validate file exists, is `.md`, and symlinks are safe
- `validate_skill_name(name)`: Alphanumeric, hyphens, underscores only, max 255 chars
- `validate_file_content(content, max_size)`: Enforce size limits
- `SecurityError`: Custom exception for all security violations

## Semantic Search System (NEW)

### Overview

The project now includes **embedding-based semantic search** to efficiently discover skills without loading all tool definitions upfront. This solves the token overhead problem identified in Anthropic's [code-execution-with-mcp research](https://www.anthropic.com/engineering/code-execution-with-mcp).

**Impact**: 98.2% reduction in tokens used for skill discovery - from 75,000 tokens to ~1,350 tokens per search.

### Architecture (`mcp_skills/embeddings.py`)

**SkillEmbeddingSearch** class provides:
- **Vector Database**: Chroma (lightweight, local, in-memory + persistent storage)
- **Embedding Model**: Sentence Transformers `all-MiniLM-L6-v2` (384-dim, 22MB)
- **Search Types**: Semantic similarity, tag filtering, category filtering, location filtering
- **Lazy Loading**: Skills indexed once, queried many times (O(1) tag lookups)

**Key Components**:

```python
# Semantic search with embeddings
results = search_engine.search(
    query="security validation",
    limit=10,
    tags_filter=["security"],        # AND logic
    category_filter="security",
    location_filter="project"
)

# Returns: List[SearchResult] sorted by similarity_score (0-1)
```

### MCP Tools Structure

The server exposes **only discovery and access tools** (not individual skill definitions):

#### `search_skills` - Skill Discovery Tool

Search for skills using semantic understanding:

```json
{
  "name": "search_skills",
  "description": "Search for skills using semantic understanding (embeddings)",
  "inputSchema": {
    "query": "Natural language query (required)",
    "limit": "Max results 1-50 (default: 10)",
    "tags": ["Filter by tags"],
    "category": "Filter by category"
  }
}
```

**Response Format** (token-efficient):
```json
{
  "query": "security validation",
  "results_count": 3,
  "results": [
    {
      "name": "security-audit",
      "description": "Audit security configurations...",
      "similarity_score": 0.95,
      "tags": ["security", "audit"],
      "category": "security",
      "location": "project"
    }
  ]
}
```

#### `get_skill` - Skill Access Tool

Load full content of a specific skill by name (discovered via `search_skills`):

```json
{
  "name": "get_skill",
  "description": "Load full content of a specific skill by name",
  "inputSchema": {
    "name": "Skill name (required, e.g., 'security-audit')",
    "format": "Output format: 'raw' (markdown) or 'json' (default: 'raw')"
  }
}
```

**Workflow**:
1. Agent calls `search_skills("security validation")` to discover relevant skills
2. Receives list of matching skills with metadata
3. Agent calls `get_skill("security-audit")` to load full content
4. Agent uses skill content as needed

#### Other Tools

- `list_skills`: List all skills (for small collections or admin use)
- `create_skill`: Create new skill
- `update_skill`: Update existing skill

### Token Efficiency: Why This Approach

**Before** (exposing hundreds of skill tools):
- Tool list alone: 50,000+ tokens
- Agent processing: 25,000+ tokens
- **Total: 75,000+ tokens per call**

**After** (only search + access tools):
- Tool definitions: ~800 tokens (search, get_skill, list, create, update)
- Search results: ~500 tokens (10 skills with metadata)
- **Total: ~1,350 tokens per call**

**Savings: 98% reduction** ✅

### Integration with SkillManager

```python
# Initialize with embeddings enabled (default)
manager = SkillManager(enable_embeddings=True)

# Search skills (uses embeddings if available, falls back to keyword search)
results = manager.search_skills(
    query="deployment automation",
    limit=10,
    tags=["devops"],
    category="deployment"
)

# Graceful fallback: If embeddings unavailable, uses keyword-based search
```

### Graceful Degradation

- **Embeddings Available**: Full semantic search with cosine similarity
- **Embeddings Unavailable**: Automatic fallback to keyword-based search
  - Still scores by relevance (name > description > tags)
  - Preserves tag and category filtering
  - No server failure if dependencies missing

### Enriched Skill Metadata

Extended `SkillMetadata` supports optional frontmatter fields:

```markdown
---
description: Brief description (required)
tags: ["security", "audit"]              # Optional
category: "security"                     # Optional
keywords: ["vulnerability", "scanning"]  # Optional
use_case: "Identify security issues"    # Optional
---

# Content here...
```

### Search Engine Lifecycle

1. **Startup** (`SkillManager.__init__`):
   - Initialize Chroma database (persistent at `~/.cache/mcp-skills`)
   - Load embedding model (`all-MiniLM-L6-v2`)

2. **Discovery** (`_discover_skills`):
   - Scan directories for skill files
   - Extract metadata from frontmatter
   - Index each skill with embeddings

3. **Query** (`search_skills`):
   - Encode search query to embedding
   - Find top-k similar skills via vector DB
   - Apply tag/category filters
   - Return ranked results

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Startup Time** | ~2-5 seconds (first time loads model, then cached) |
| **Search Time** | ~50-100ms per query (50-1000 skills) |
| **Memory** | ~100MB for 1000 skills (including model) |
| **Disk** | ~25MB for vector index (Chroma) + 22MB for model |
| **Model Size** | 22MB (all-MiniLM-L6-v2, downloads once) |
| **Database** | ~/.cache/mcp-skills (local, persistent) |

### Testing

- `tests/test_embeddings.py`: Comprehensive embedding search tests
  - Search by semantic similarity
  - Tag and category filtering
  - Result ranking and ordering
  - Fallback keyword search
  - Integration with SkillManager

Tests are skipped if `sentence-transformers` and `chromadb` unavailable, but keyword search tests always run.

### Dependencies (Optional)

Add to `pyproject.toml` under `[project.optional-dependencies]`:
```toml
embeddings = [
    "sentence-transformers>=2.2.0",
    "chromadb>=0.4.0",
]
```

Install with: `pip install -e ".[embeddings]"` or `pip install -e ".[dev]"`

## Testing Strategy

Tests use pytest with temporary directories for isolation:

- `test_skill_manager.py`: Tests skill discovery, metadata extraction, CRUD operations with temp skills
- `test_security.py`: Tests path traversal prevention, symlink handling, validation functions

**Test Execution**:
```bash
pytest                          # All tests
pytest -v                       # Verbose output
pytest --cov=mcp_skills         # With coverage report
pytest tests/test_security.py   # Single file
```

## Configuration

### Dependencies

Core (pyproject.toml):
- `mcp>=0.1.0`: Model Context Protocol support
- `python-frontmatter>=1.0.0`: YAML frontmatter parsing

Optional - Embeddings (for semantic search):
- `sentence-transformers>=2.2.0`: Embedding model (all-MiniLM-L6-v2)
- `chromadb>=0.4.0`: Vector database

Development (includes embeddings):
- `pytest>=7.0`: Test framework
- `pytest-asyncio>=0.21.0`: Async test support
- `sentence-transformers>=2.2.0`: For embedding tests
- `chromadb>=0.4.0`: For vector database tests

### Python Version Support

Supports Python 3.8 through 3.12

## Common Development Tasks

### Adding a New MCP Tool

1. Define tool in `_get_management_tools()` with schema
2. Add handler method `_handle_tool_name(arguments)`
3. Route in `_call_tool_handler()` if-elif chain
4. Test in test files

### Modifying Skill Discovery

Edit `_scan_directory()` in SkillManager to:
- Change glob patterns for different file structures
- Add new skip_files entries
- Modify metadata extraction logic

### Changing Skill Directory Defaults

Modify SkillManager.__init__() path defaults or pass via CLI args:
```bash
mcp-skills --user-skills ~/.my-skills --project-skills ./my-project-skills
```

## Error Handling

All errors return MCP CallToolResult with `isError=True`:
- **Skill not found**: File missing from cache or filesystem
- **Invalid skill name**: Contains disallowed characters
- **Path traversal**: Detected `..` or absolute paths
- **Path escape**: Resolved path outside base directory
- **Content too large**: Exceeds 10MB limit

SecurityError exceptions are caught and formatted as MCP errors.

## Performance Notes

- **Metadata Caching**: Skill metadata cached in memory at startup (O(1) lookups)
- **Lazy Loading**: Full skill content read only on invocation
- **No File Watching**: Server restart required for new skills (by design)
- **Skill Scanning**: O(n) directory traversal at init time

To reload skills: Restart the server process.

## Git Branches and Workflow

Current branch: `feature/search-api`
Main branch for PRs: `main`

Recent commits show:
- PyPI publishing support added
- Installation documentation
- README updates
- Skill discovery and management implementation
