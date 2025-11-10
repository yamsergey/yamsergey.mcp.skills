# MCP Skills Server

An MCP (Model Context Protocol) server for discovering, managing, and accessing [Anthropic Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) through a standardized interface.

## Installation

### Prerequisites

- Python 3.8+
- pip

### From GitHub

```bash
pip install git+https://github.com/yamsergey/yamsergey.mcp.skills.git
```

### From Source (Development)

```bash
git clone https://github.com/yamsergey/yamsergey.mcp.skills.git
cd yamsergey.mcp.skills
pip install -e .
```

### With Semantic Search Support

```bash
pip install "git+https://github.com/yamsergey/yamsergey.mcp.skills.git[embeddings]"
```

## Configuration

Skills are discovered only from explicitly configured paths. No defaults are applied.

### Quick Start: JSON Configuration

Create a `skills-config.json`:

```json
{
  "skills_paths": [
    {
      "nickname": "project",
      "path": "./.claude/skills",
      "readonly": false
    },
    {
      "nickname": "shared",
      "path": "~/shared-skills",
      "readonly": true
    }
  ]
}
```

Run the server:

```bash
mcp-skills --config skills-config.json
```

### Location Nicknames for Agents

When creating skills, agents can reference skill locations by their **nickname**. For example:

- **User prompt**: "Create a security audit skill for the shared project"
- **Agent understands**: "shared" is a known location, uses it to determine where to create the skill

This allows agents to infer or ask users directly about which location to use for new skills.

### Quick Start: CLI Arguments

```bash
mcp-skills --skills-path ./.claude/skills --skills-path ~/shared-skills
```

## Claude Code Configuration

Add to your Claude Code MCP servers config:

```json
{
  "mcpServers": {
    "mcp-skills": {
      "command": "mcp-skills",
      "args": [
        "--config",
        "~/.mcp-skills-config.json"
      ]
    }
  }
}
```

## Skill Path Configuration

Each skill path has the following properties:

| Property | Type | Description |
|----------|------|-------------|
| `nickname` | string | Identifier for the path (used when creating skills) |
| `path` | string | File system directory with `.md` skill files |
| `readonly` | boolean | If `true`, skills can only be read; if `false`, agents can create/modify skills |
| `pattern` | string (optional) | Regexp pattern to include skill files (e.g., `"^security_.*"` or `"^security_.*\|^audit_.*"` for multiple categories). Uses standard regex with `\|` for alternation |
| `exclude_pattern` | string (optional) | Regexp pattern to exclude skill files (e.g., `".*_deprecated$"` or `".*_deprecated$\|.*_experimental$"`). Uses standard regex with `\|` for alternation |

### Pattern Filtering Examples

**Example 1: Single inclusion pattern**

Filter skills by name prefix:

```json
{
  "skills_paths": [
    {
      "nickname": "security",
      "path": "./skills/all-skills",
      "readonly": true,
      "pattern": "^security_.*"
    }
  ]
}
```

**Example 2: Multiple inclusion patterns**

Include multiple categories using pattern alternation:

```json
{
  "skills_paths": [
    {
      "nickname": "compliance",
      "path": "./skills/all-skills",
      "readonly": true,
      "pattern": "^security_.*|^audit_.*|^compliance_.*"
    }
  ]
}
```

**Example 3: Exclude deprecated and experimental skills**

Use exclude patterns to filter out unwanted skills:

```json
{
  "skills_paths": [
    {
      "nickname": "project",
      "path": "./.claude/skills",
      "readonly": false,
      "exclude_pattern": ".*_deprecated$|.*_experimental$"
    }
  ]
}
```

**Example 4: Include + Exclude (whitelist and blacklist)**

Combine multiple inclusion and exclusion patterns for fine-grained control:

```json
{
  "skills_paths": [
    {
      "nickname": "production",
      "path": "./shared-skills",
      "readonly": true,
      "pattern": "^prod_.*|^stable_.*",
      "exclude_pattern": ".*_testing$|.*_deprecated$"
    }
  ]
}
```

This configuration discovers only skills matching at least one inclusion pattern AND not matching any exclusion pattern, enabling selective skill loading from larger shared directories.

## Running the Server

The server exposes skills via semantic search API for token-efficient discovery and access.

```bash
mcp-skills --config skills-config.json
```

**Available Tools:**

- **`search_skills`** - Semantic search for skills by meaning and keywords
- **`get_skill`** - Load full skill content
- **`list_skills`** - List all available skills
- **`create_skill`** - Create new skill in a writable location
- **`update_skill`** - Update an existing skill

## Skill Format

Skills are Markdown files with YAML frontmatter:

```markdown
---
description: Brief description of the skill
tags: ["category", "tag"]
category: "main-category"
---

# Skill Name

Skill content in Markdown format...

## Features
- Feature 1
- Feature 2
```

**Required:** `description` in frontmatter
**Optional:** `tags`, `category`, `keywords`, `use_case`

## Features

- **Flexible path configuration** - Any number of skill directories with custom nicknames
- **Read-only or writable paths** - Control where agents can create/modify skills
- **Nested skill organization** - Organize skills in subdirectories
- **Semantic search** - Optional embeddings-based intelligent discovery
- **CRUD operations** - Create, read, update skills via MCP tools
- **Security** - Path validation prevents directory traversal
- **Metadata enrichment** - Tags, categories, and keywords for better organization

## Development

### Running Tests

```bash
pytest
pytest --cov=mcp_skills
```

### Project Structure

```
mcp_skills/
├── __init__.py
├── server.py              # MCP server implementation
├── skill_manager.py       # Skill discovery and management
├── security.py            # Path validation and security
└── embeddings.py          # Semantic search (optional)
```

## API Reference

### SkillManager (Python)

```python
from mcp_skills.skill_manager import SkillManager, SkillPath

manager = SkillManager(
    skills_paths=[
        SkillPath(nickname="project", path="./.claude/skills", readonly=False),
        SkillPath(
            nickname="compliance",
            path="~/shared-skills",
            readonly=True,
            pattern="^security_.*|^audit_.*|^compliance_.*"
        ),
        SkillPath(
            nickname="production",
            path="~/shared-skills",
            readonly=True,
            pattern="^prod_.*|^stable_.*",
            exclude_pattern=".*_testing$|.*_deprecated$"
        ),
    ]
)

# List all skills
skills = manager.list_skills()

# Get a specific skill
content = manager.read_skill("skill-name")

# Create a new skill (only in writable locations)
manager.create_skill(
    skill_name="category/my-skill",
    description="Description",
    content="# Markdown content",
    location="project"
)

# Update a skill
manager.update_skill(
    skill_name="skill-name",
    description="New description",
    content="Updated content"
)

# Search skills
results = manager.search_skills(
    query="security audit",
    limit=10,
    tags=["security"],
    location="compliance"
)
```

## License

MIT

## Contributing

Contributions welcome! Please ensure tests pass:

```bash
pytest --cov=mcp_skills
```
