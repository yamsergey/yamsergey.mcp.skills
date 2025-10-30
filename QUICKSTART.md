# Quick Start Guide

## Installation

```bash
pip install -e .
```

## Create Your First Skill

Create a file `.claude/skills/hello-world.md`:

```markdown
---
description: A simple greeting skill
---

# Hello World Skill

This skill demonstrates basic skill creation.

## What it does

Returns a friendly greeting message.

## Usage

Simply invoke this skill to get a greeting!
```

## Run the Server

```bash
mcp-skills
```

## Use in Claude Code

Add to `.claude/mcp-servers.json`:

```json
{
  "mcp-skills": {
    "command": "mcp-skills"
  }
}
```

Then you can:

1. **Call the skill**: Use `hello-world` tool to read the full markdown content
2. **List skills**: Use `list_skills` tool to see all available skills
3. **Create skills**: Use `create_skill` tool to programmatically create new skills
4. **Update skills**: Use `update_skill` tool to modify existing skills

## Example Workflow

```python
# List all available skills
list_skills()

# Read a specific skill
hello_world_content = call_tool("hello-world")

# Create a new skill
create_skill(
    name="my-custom-skill",
    description="My custom skill",
    content="# My Custom Skill\n\nThis is my skill content.",
    location="project"
)

# Update a skill
update_skill(
    name="hello-world",
    description="Updated description"
)
```

## Directory Structure

```
~/.claude/skills/          # User skills (discovered)
./.claude/skills/          # Project skills (discovered)
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out [tests](tests/) for more usage examples
- Customize skill directories with command-line arguments:
  ```bash
  mcp-skills --user-skills ~/my-skills --project-skills ./skills
  ```

## Troubleshooting

**Skills not found?**
- Ensure `.md` files are in the correct directories
- Restart the server after adding new skills
- Check file permissions

**Path errors?**
- Skill names must be alphanumeric with hyphens/underscores
- Avoid special characters in skill filenames

**Server won't start?**
- Ensure Python dependencies are installed: `pip install -e .`
- Check that skill directories are readable
- Look for error messages in server output
