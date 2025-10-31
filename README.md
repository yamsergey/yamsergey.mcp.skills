# MCP Skills Server

An MCP (Model Context Protocol) server that exposes [Anthropic Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) as MCP tools. This allows you to manage and access your skills through the Model Context Protocol.

## Features

- **Dual Mode Operation**: Choose between original (all skills as tools) or search API (token-efficient discovery)
- **Semantic Search**: Optional embeddings-based search for intelligent skill discovery
- **Skills as MCP Tools**: Automatically discovers and exposes skills as callable MCP tools
- **Metadata Caching**: Efficiently caches skill metadata while lazily loading full content
- **CRUD Operations**: Create, read, and update skills through MCP tools
- **Security**: Path validation prevents directory traversal and other security issues
- **Flexible Locations**: Support for both user-level and project-level skills
- **Error Handling**: Clear error messages for all failure scenarios

## How It Works

1. **Discovery**: Server scans skill directories on startup for `.md` files
2. **Metadata Extraction**: Parses frontmatter to extract name, description, and metadata
3. **Tool Registration**: Creates MCP tools from skill metadata
4. **Lazy Loading**: Full skill content is only read when a tool is invoked
5. **Management**: Provides tools to create and update skills

## Installation

### Prerequisites

- Python 3.8+
- pip

### From GitHub (Recommended for latest development version)

```bash
# Install directly from GitHub
pip install git+https://github.com/yamsergey/yamsergey.mcp.skills.git

# Or install a specific version/tag
pip install git+https://github.com/yamsergey/yamsergey.mcp.skills.git@v0.1.0

# Or install from a specific branch
pip install git+https://github.com/yamsergey/yamsergey.mcp.skills.git@main
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yamsergey/yamsergey.mcp.skills.git
cd yamsergey.mcp.skills

# Install in development mode
pip install -e . // or pipx install -e . if pip can't install it on your environment

# Or install with dev dependencies
pip install -e ".[dev]"
```

### From PyPI (Once published)

```bash
pip install mcp-skills
```

### Installing with Semantic Search Support

To use semantic search in Search API mode, install with embeddings support:

```bash
# Install with embeddings (semantic search)
pip install -e ".[embeddings]"

# Install with all dev dependencies including embeddings
pip install -e ".[dev]"

# Note: Embeddings are optional. The system works with keyword-based search fallback if embeddings unavailable.
```

**Embeddings Setup:**
- Model: `sentence-transformers/all-MiniLM-L6-v2` (22MB, 384-dimensional)
- Vector Database: Chroma (local, persistent)
- Cache Location: `~/.cache/mcp-skills`

## Usage

### Running the Server

The server supports two modes:

#### Mode 1: Original Mode (Default - Backward Compatible)

Exposes all skills as individual MCP tools. Best for small skill collections.

```bash
# Using default directories (~/.claude/skills and ./.claude/skills)
mcp-skills

# Using custom directories
mcp-skills --user-skills /path/to/user/skills --project-skills /path/to/project/skills
```

#### Mode 2: Search API Mode (Token Efficient)

Exposes only discovery and access tools. Best for large skill collections (100+, 1000+ skills). Implements semantic search-first approach based on [Anthropic's research](https://www.anthropic.com/engineering/code-execution-with-mcp).

```bash
# Enable search API mode
mcp-skills --search-api

# With custom directories
mcp-skills --search-api --user-skills /path/to/user/skills --project-skills /path/to/project/skills
```

**Mode Comparison:**

| Aspect | Original Mode | Search API Mode |
|--------|---------------|-----------------|
| Tools Exposed | All skills + 5 management | 5 tools only |
| Best For | < 50 skills | 100+ skills |
| Token Overhead | ~75,000 tokens | ~1,350 tokens |
| Discovery | Direct tool invocation | Semantic search first |
| CRUD Operations | ✓ All supported | ✓ All supported |

### Configuring in Claude Code

#### Original Mode
```json
{
  "mcp-skills": {
    "command": "mcp-skills",
    "args": [
      "--user-skills",
      "~/.claude/skills",
      "--project-skills",
      "./.claude/skills"
    ]
  }
}
```

#### Search API Mode
```json
{
  "mcp-skills": {
    "command": "mcp-skills",
    "args": [
      "--search-api",
      "--user-skills",
      "~/.claude/skills",
      "--project-skills",
      "./.claude/skills"
    ]
  }
}
```

## Skill Format

Skills are markdown files with YAML frontmatter:

### Basic Format

```markdown
---
description: Brief description of what this skill does
---

# Skill Name

Full markdown content describing the skill, its usage, examples, etc.

## Features

- Feature 1
- Feature 2

## Usage

Example usage here...
```

### Extended Format (Recommended for Search API Mode)

```markdown
---
description: Brief description of what this skill does
tags: ["security", "audit"]              # Optional: categorization tags
category: "security"                     # Optional: primary category
keywords: ["vulnerability", "scanning"]  # Optional: searchable keywords
use_case: "Identify security issues"     # Optional: primary use case
---

# Skill Name

Full markdown content describing the skill, its usage, examples, etc.
```

**File naming**: Use lowercase with hyphens (e.g., `my-awesome-skill.md`)

**Frontmatter Fields:**
- `description` (required): Brief description
- `tags` (optional): List of categorization tags for filtering
- `category` (optional): Primary category for hierarchical organization
- `keywords` (optional): Searchable keywords for discovery
- `use_case` (optional): Primary use case or scenario

**Nested skills**: Skills can be organized in nested directories using forward slashes in the skill name (e.g., `utils/helpers/my-skill.md`). Nested directories are automatically created when skills are created.

## Available Tools

### Original Mode: Skill Tools

In original mode, each discovered skill becomes an MCP tool that returns its full markdown content.

**Skill Tool Parameters:**
- `format` (optional): Output format - `raw` (default) or `json`

**Skill Tool Returns:**
- `raw` format: Full markdown content
- `json` format: JSON object with skill name, content, and metadata

### Search API Mode: Discovery & Access Tools

#### `search_skills`

Search for skills using semantic understanding (with optional keyword fallback).

**Parameters:**
- `query` (required): Natural language search query
- `limit` (optional): Max results to return (default: 10, max: 50)
- `tags` (optional): Filter by tags (all must match)
- `category` (optional): Filter by category

**Returns:**
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

#### `get_skill`

Load full content of a specific skill by name (discovered via `search_skills`).

**Parameters:**
- `name` (required): Skill name to load
- `format` (optional): Output format - `raw` (default) or `json`

**Returns:**
- `raw` format: Full markdown content
- `json` format: JSON object with skill name, content, and metadata

### Management Tools (Both Modes)

#### `list_skills`

List all available skills with metadata.

**Returns:**
```json
{
  "total": 2,
  "skills": {
    "my-skill": {
      "name": "my-skill",
      "description": "Description of my skill",
      "location": "project"
    }
  }
}
```

#### `create_skill`

Create a new skill file.

**Parameters:**
- `name` (required): Skill name (alphanumeric, hyphens, underscores, and forward slashes for nesting)
  - Examples: `my-skill`, `category/my-skill`, `category/subcategory/my-skill`
  - Nested directories are automatically created if they don't exist
- `description` (required): Skill description
- `content` (required): Full markdown content
- `location` (optional): `user` or `project` (default: `project`)

**Returns:**
```json
{
  "message": "Skill 'my-skill' created successfully",
  "metadata": {
    "name": "my-skill",
    "description": "...",
    "location": "project"
  },
  "path": "/path/to/skill/file"
}
```

#### `update_skill`

Update an existing skill.

**Parameters:**
- `name` (required): Skill name
- `description` (optional): New description
- `content` (optional): New markdown content

**Returns:**
```json
{
  "message": "Skill 'my-skill' updated successfully",
  "metadata": {
    "name": "my-skill",
    "description": "...",
    "location": "project"
  }
}
```

## Security Considerations

The server implements multiple security safeguards:

- **Path Traversal Prevention**: Validates all file paths to ensure they stay within skill directories
- **Filename Validation**: Restricts skill names to alphanumeric, hyphens, and underscores
- **File Size Limits**: Enforces maximum content size (10MB default)
- **Symlink Handling**: Validates symlinks don't escape base directory
- **Extension Validation**: Only `.md` files are recognized as skills

## Directory Structure

```
~/.claude/skills/              # User skills (read-only by default)
├── my-skill.md
├── another-skill.md
└── ...

./.claude/skills/              # Project skills
├── project-skill.md
└── ...
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_skills

# Run specific test file
pytest tests/test_security.py -v
```

### Project Structure

```
mcp-skills/
├── mcp_skills/
│   ├── __init__.py
│   ├── server.py           # MCP server implementation
│   ├── skill_manager.py    # Skill discovery and management
│   └── security.py         # Security utilities and validation
├── tests/
│   ├── test_security.py    # Security validation tests
│   └── test_skill_manager.py  # Skill manager tests
├── pyproject.toml          # Project configuration
└── README.md
```

## API Reference

### SkillManager

Main class for skill operations:

```python
from mcp_skills.skill_manager import SkillManager

manager = SkillManager(
    user_skills_dir="~/.claude/skills",
    project_skills_dir="./.claude/skills"
)

# List skills
skills = manager.list_skills()  # Dict[str, SkillMetadata]

# Get metadata for a skill
metadata = manager.get_skill_metadata("skill-name")

# Read full skill content
content = manager.read_skill("skill-name")

# Create a new skill (flat)
metadata = manager.create_skill(
    skill_name="my-skill",
    description="Description",
    content="# Markdown content",
    location="project"
)

# Create a nested skill (directories created automatically)
metadata = manager.create_skill(
    skill_name="category/my-skill",
    description="Description",
    content="# Markdown content",
    location="project"
)

# Update a skill
metadata = manager.update_skill(
    skill_name="my-skill",
    description="New description",  # optional
    content="# New content"          # optional
)
```

### Security Module

Utility functions for path and content validation:

```python
from mcp_skills.security import (
    resolve_and_validate_path,
    validate_skill_path,
    validate_skill_name,
    validate_file_content,
    SecurityError
)

# Validate paths
try:
    safe_path = resolve_and_validate_path("/base/dir", "relative/path.md")
except SecurityError as e:
    print(f"Security error: {e}")

# Validate skill names
try:
    validate_skill_name("my-skill")
except SecurityError:
    print("Invalid skill name")
```

## Error Handling

All errors are returned as MCP tool responses with `isError=True`:

```json
{
  "type": "text",
  "text": "Error: Skill not found: nonexistent-skill"
}
```

Common error scenarios:
- **Skill not found**: Skill doesn't exist in any skill directory
- **Invalid skill name**: Contains special characters or invalid format
- **Path traversal detected**: Attempt to access files outside skill directories
- **File not found**: Skill metadata exists but file is missing
- **Content too large**: File exceeds maximum size limit

## Performance

- **Metadata Caching**: Skill metadata is cached in memory after discovery
- **Lazy Loading**: Full content is only read on-demand
- **No File Watching**: Changes require server restart (by design for simplicity)

To refresh skills after adding new files, restart the server.

## Limitations

- No real-time file watching (restart required for new skills)
- Maximum file size: 10MB (configurable)
- Skill names limited to 255 characters
- Only `.md` files are recognized as skills

## License

MIT

## Contributing

Contributions welcome! Please ensure tests pass before submitting.

```bash
pytest --cov=mcp_skills
```
