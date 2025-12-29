# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP Skills Server** is a Python-based Model Context Protocol (MCP) server that exposes Anthropic Claude Code Skills as MCP tools. It enables skill discovery via semantic search, management (CRUD operations), and access through the MCP interface.

**Key Purpose**: Bridge Claude Code Skills (markdown files with YAML frontmatter) and MCP clients by discovering skills from configured directories and exposing them via search-based discovery tools. This reduces token overhead by 98% compared to exposing each skill as a separate tool.

## Development Commands

```bash
# Install from source in development mode
pip install -e .

# Install with dev dependencies (includes embeddings)
pip install -e ".[dev]"

# Install with embeddings only (semantic search)
pip install -e ".[embeddings]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=mcp_skills

# Run specific test file or test
pytest tests/test_security.py -v
pytest tests/test_skill_manager.py::test_skill_manager_init -v

# Run the server with JSON config
mcp-skills --config skills-config.json

# Run with CLI paths (auto-generates nicknames)
mcp-skills --skills-path ~/.claude/skills --skills-path ./.claude/skills

# Debug: Direct Python invocation
python -m mcp_skills.server
```

## Architecture

```
mcp_skills/
├── server.py          # MCP server, CLI entry point, tool handlers
├── skill_manager.py   # Skill discovery, caching, CRUD, search
├── security.py        # Path validation, traversal prevention
└── embeddings.py      # Semantic search with Chroma + Sentence Transformers
```

**Data Flow**:
1. **Startup**: SkillManager scans configured `skills_paths`, extracts metadata, indexes into vector DB
2. **Tool Registration**: Only 5 tools exposed: `search_skills`, `get_skill`, `list_skills`, `create_skill`, `update_skill`
3. **Tool Invocation**: Handlers validate paths, perform operations, return JSON results

## Key Classes

### SkillPath (`mcp_skills/skill_manager.py`)

Configuration for a skill directory:
```python
@dataclass
class SkillPath:
    nickname: str           # Identifier (e.g., "project", "shared")
    path: str               # File system path
    readonly: bool = False  # If True, cannot create/modify skills here
    pattern: str = None     # Regexp to include skills (e.g., "^security_.*")
    exclude_pattern: str = None  # Regexp to exclude skills
```

### SkillManager (`mcp_skills/skill_manager.py`)

```python
manager = SkillManager(
    skills_paths=[
        SkillPath(nickname="project", path="./.claude/skills", readonly=False),
        SkillPath(nickname="shared", path="~/shared-skills", readonly=True),
    ],
    enable_embeddings=True,  # Default: True
)

# Key methods
manager.list_skills()                    # Dict[str, SkillMetadata]
manager.get_skill_metadata(name)         # SkillMetadata | None
manager.read_skill(name)                 # Full markdown content
manager.search_skills(query, limit, tags, category, location)  # List[SearchResult]
manager.create_skill(name, description, content, location)     # SkillMetadata
manager.update_skill(name, description, content)               # SkillMetadata
manager.get_writable_skill_paths()       # List[SkillPath] (readonly=False)
```

### SkillsServer (`mcp_skills/server.py`)

```python
server = SkillsServer(
    skills_paths=[...],                    # List[SkillPath]
    search_tool_description="...",         # Custom description or file path
)
await server.run()  # Start stdio MCP server
```

## Skill File Format

```markdown
---
description: Brief description (required)
tags: ["security", "audit"]              # Optional
category: "security"                     # Optional
keywords: ["vulnerability", "scanning"]  # Optional
use_case: "Identify security issues"     # Optional
---

# Skill Content

Markdown content here...
```

**Discovery Rules**:
- Nested: `skill-dir/SKILL.md` → name derived from parent directory
- Flat: `skill-name.md` → name derived from filename (supports nested paths like `category/skill-name.md`)
- Skipped: README.md, LICENSE, CHANGELOG, THIRD_PARTY_NOTICES, agent_skills_spec.md

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_skills` | Semantic search with query, limit, tags, category filters |
| `get_skill` | Load full content by name (raw markdown or JSON) |
| `list_skills` | List all skills with metadata |
| `create_skill` | Create skill in a writable location |
| `update_skill` | Update existing skill's description/content |

## Semantic Search

- **Vector DB**: Chroma (persistent at `~/.cache/mcp-skills`)
- **Embedding Model**: `all-MiniLM-L6-v2` (384-dim, 22MB)
- **Graceful Degradation**: Falls back to keyword search if embeddings unavailable

```python
results = manager.search_skills(
    query="security validation",
    limit=10,
    tags=["security"],        # AND logic
    category="security",
    location="project",       # Filter by nickname
)
# Returns List[SearchResult] sorted by similarity_score (0-1)
```

## Adding a New MCP Tool

1. Define tool in `_get_management_tools()` with JSON schema
2. Add async handler `_handle_tool_name(arguments) -> CallToolResult`
3. Route in `_call_tool_handler()` if-elif chain
4. Add tests

## Configuration

**JSON Config** (`skills-config.json`):
```json
{
  "skills_paths": [
    {"nickname": "project", "path": "./.claude/skills", "readonly": false},
    {"nickname": "shared", "path": "~/shared-skills", "readonly": true, "pattern": "^prod_.*"}
  ]
}
```

**Pattern Filtering**:
- `pattern`: Regexp to include skills (e.g., `"^security_.*|^audit_.*"`)
- `exclude_pattern`: Regexp to exclude skills (e.g., `".*_deprecated$"`)

## Error Handling

All errors return `CallToolResult(isError=True)`:
- Skill not found, invalid skill name, path traversal, path escape, content too large

`SecurityError` from `mcp_skills/security.py` is the unified exception type.

## Performance

- Metadata cached in memory at startup (O(1) lookups)
- Full content read on-demand (lazy loading)
- No file watching - restart server to reload skills
- Search: ~50-100ms per query (50-1000 skills)
