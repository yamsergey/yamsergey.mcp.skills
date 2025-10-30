---
name: skill-creator
description: Guide for creating high-quality, well-formatted Anthropic Agent Skills. Use this skill when you need to create new skills that follow Anthropic's official specifications and best practices. Includes templates, validation rules, and examples.
license: MIT
---

# Anthropic Agent Skill Creator Guide

This skill provides comprehensive guidance for creating well-formatted Anthropic Agent Skills that can be discovered and used by Claude Code and other AI agents.

## Quick Start

A minimal skill requires just one file:

```
my-skill/
  └── SKILL.md
```

The `SKILL.md` file must contain YAML frontmatter followed by Markdown content.

---

## Skill Format Specification

### Required YAML Frontmatter

Every skill must start with YAML frontmatter containing:

#### `name` (required)
- Skill name in hyphen-case (lowercase, alphanumeric + hyphens only)
- Must match the parent directory name
- Examples: `skill-creator`, `mcp-builder`, `template-skill`

```yaml
name: my-awesome-skill
```

#### `description` (required)
- What the skill does and when it should be used
- Used by agents to decide whether to invoke the skill
- Should be clear and actionable
- 100-200 characters recommended

```yaml
description: Guide for creating well-formatted Anthropic Agent Skills with proper documentation and examples.
```

### Optional YAML Properties

#### `license` (optional)
- License for the skill (license name or filename)
- Examples: `MIT`, `Apache-2.0`, `LICENSE.txt`

```yaml
license: MIT
```

#### `allowed-tools` (optional)
- List of pre-approved tools that can run
- Currently supported in Claude Code only
- Useful for security-critical operations

```yaml
allowed-tools:
  - bash
  - python
```

#### `metadata` (optional)
- Custom key-value pairs for additional properties
- Use unique prefixes to avoid conflicts
- Example format:

```yaml
metadata:
  mycompany.version: "1.0.0"
  mycompany.category: "development"
  mycompany.experimental: "false"
```

### Complete Frontmatter Example

```yaml
---
name: skill-creator
description: Guide for creating high-quality, well-formatted Anthropic Agent Skills following official specifications.
license: MIT
allowed-tools:
  - bash
metadata:
  anthropic.category: "development"
  anthropic.complexity: "intermediate"
---
```

---

## Markdown Body

After the frontmatter (separated by `---`), the Markdown body has no restrictions. Structure it as needed for your skill.

### Recommended Structure

```markdown
# Skill Title

One-line description of what the skill does.

## Overview

Detailed explanation of the skill's purpose and use cases.

## When to Use

Specific scenarios where this skill is valuable.

## How to Use

Step-by-step instructions for using the skill.

## Examples

Concrete examples demonstrating the skill in action.

## References

Links to additional resources and documentation.
```

---

## Step-by-Step Skill Creation Process

### Step 1: Plan Your Skill

Before creating, determine:

1. **Purpose**: What specific task does this skill enable?
2. **Name**: What will you call it? (hyphen-case format)
3. **Description**: How would you explain it to an AI agent?
4. **Scope**: What should it cover? What should it exclude?
5. **Complexity**: Is this beginner, intermediate, or advanced?

### Step 2: Create the Directory

Create a directory matching your skill name:

```bash
mkdir my-skill
cd my-skill
```

### Step 3: Write SKILL.md

Create the `SKILL.md` file with frontmatter:

```markdown
---
name: my-skill
description: Clear description of what this skill does and when to use it.
license: MIT
---

# My Skill

## Overview

Detailed explanation here...

## How to Use

Instructions here...

## Examples

Examples here...
```

### Step 4: Add Reference Files (Optional)

For complex skills, add supporting files:

```
my-skill/
  ├── SKILL.md          # Main skill definition
  ├── REFERENCE.md      # Additional documentation
  ├── examples/         # Example files
  │   ├── example1.md
  │   └── example2.md
  └── templates/        # Template files
      └── template.md
```

### Step 5: Validate Your Skill

Ensure your skill meets all requirements:

- ✅ Directory name matches skill name (hyphen-case)
- ✅ `SKILL.md` file exists in root
- ✅ Frontmatter contains `name` and `description`
- ✅ Name matches directory name
- ✅ Name uses only lowercase alphanumeric + hyphens
- ✅ Description is clear and actionable
- ✅ Markdown content is well-structured
- ✅ No syntax errors in YAML or Markdown

---

## Validation Rules

### Name Validation

The skill name must:
- ✅ Be in hyphen-case (lowercase only)
- ✅ Contain only letters, numbers, and hyphens
- ✅ Match the parent directory name exactly
- ✅ Start and end with alphanumeric characters (no hyphens)

**Valid Examples:**
- `my-skill` ✅
- `template-skill` ✅
- `skill-creator` ✅
- `mcp-builder` ✅

**Invalid Examples:**
- `MySkill` ❌ (mixed case)
- `my_skill` ❌ (underscore)
- `my-skill-` ❌ (ends with hyphen)
- `-my-skill` ❌ (starts with hyphen)

### Description Validation

The description should:
- ✅ Explain what the skill does
- ✅ Mention when an agent should use it
- ✅ Be clear and concise (100-200 chars)
- ✅ Be written in plain English
- ✅ Avoid jargon when possible

**Good Example:**
```
Guide for creating well-formatted Anthropic Agent Skills
following official specifications and best practices.
```

**Poor Example:**
```
skill 4 doing things
```

---

## Template for Your Skill

Use this template to create a new skill:

```markdown
---
name: your-skill-name
description: Brief description of what this skill does and when Claude should use it.
license: MIT
---

# Your Skill Title

One-sentence summary of the skill's purpose.

## Overview

Detailed explanation of:
- What the skill does
- When it should be used
- Key capabilities
- Any prerequisites or requirements

## Key Concepts

Define important terms and concepts your skill relies on.

## How to Use This Skill

Step-by-step instructions for using the skill:

1. First step
2. Second step
3. Third step

### Example 1: Basic Usage

```
Example code or instructions here
```

### Example 2: Advanced Usage

```
More advanced example here
```

## Best Practices

- Best practice 1
- Best practice 2
- Best practice 3

## Common Patterns

Useful patterns and recipes using this skill.

## Troubleshooting

Solutions to common problems:

### Problem 1
Solution here...

### Problem 2
Solution here...

## References

- [Link to resource 1](https://example.com)
- [Link to resource 2](https://example.com)
- [Official documentation](https://docs.anthropic.com)

## Additional Resources

Links to supplementary materials, examples, and related skills.
```

---

## Common Skill Categories

### Development Skills
Skills for writing, debugging, and deploying code.
- Examples: `mcp-builder`, `skill-creator`, `webapp-testing`

### Design Skills
Skills for creating visual content and artifacts.
- Examples: `canvas-design`, `artifacts-builder`, `theme-factory`

### Content Skills
Skills for writing, editing, and managing content.
- Examples: `brand-guidelines`, `internal-comms`, `document-skills`

### Data Skills
Skills for analyzing and processing data.
- Examples: Data processing, analysis, visualization

### Integration Skills
Skills for connecting services and APIs.
- Examples: Integration patterns, API wrappers

---

## Best Practices

### 1. Write Clear Descriptions
The description is how agents decide to use your skill. Make it count.

**Before:**
```
skill for things
```

**After:**
```
Guide for creating algorithmic art using p5.js with seeded
randomness and interactive parameters for visual exploration.
```

### 2. Structure Content Logically
Use clear headings and sections to organize information.

```markdown
## Overview
## When to Use
## How to Use
## Examples
## Advanced Usage
## References
```

### 3. Include Practical Examples
Show agents exactly how to use your skill with concrete examples.

```markdown
### Example 1: Simple Usage
[code or instructions]

### Example 2: Complex Usage
[code or instructions]
```

### 4. Be Comprehensive
Cover both basic and advanced usage patterns.

```markdown
## Getting Started
[Basic usage]

## Advanced Techniques
[Complex usage patterns]
```

### 5. Keep Names Consistent
Use the same naming convention throughout (hyphen-case).

### 6. Document Prerequisites
Explain what agents need to know or have before using your skill.

```markdown
## Prerequisites
- Knowledge of [topic]
- Access to [resource]
- Understanding of [concept]
```

---

## Examples of Well-Formatted Skills

### Simple Example: template-skill

```markdown
---
name: template-skill
description: Replace with description of the skill and when Claude should use it.
---

# Insert instructions below
```

### Complex Example: mcp-builder

The mcp-builder skill is comprehensive with:
- Detailed overview of MCP concepts
- Step-by-step implementation guide
- Language-specific examples (Python, TypeScript)
- Reference documentation
- Quality checklists
- Evaluation guidelines

Learn from real skills in the Anthropic agent skills repository.

---

## Directory Structure Examples

### Minimal Skill
```
my-skill/
  └── SKILL.md
```

### Skill with Documentation
```
my-skill/
  ├── SKILL.md
  └── README.md
```

### Skill with Examples
```
my-skill/
  ├── SKILL.md
  ├── README.md
  └── examples/
      ├── example1.md
      ├── example2.md
      └── example3.md
```

### Skill with Templates and Code
```
my-skill/
  ├── SKILL.md
  ├── README.md
  ├── reference/
  │   ├── best-practices.md
  │   └── checklist.md
  ├── examples/
  │   ├── basic.md
  │   └── advanced.md
  └── templates/
      ├── template1.md
      └── template2.md
```

---

## Creating Skills with the MCP Skills Server

Once you've created your skill files, you can register them with the MCP Skills Server:

```bash
# Using the create_skill MCP tool
mcp-skills create_skill \
  --name "my-skill" \
  --description "Clear description..." \
  --content "$(cat my-skill/SKILL.md)" \
  --location "project"
```

Or use the `create_skill` MCP tool directly through Claude Code.

---

## Validation Checklist

Before publishing your skill, verify:

- ✅ Directory name is in hyphen-case and matches skill name
- ✅ `SKILL.md` exists in the skill directory
- ✅ YAML frontmatter has `name` and `description`
- ✅ Skill name matches directory name
- ✅ Name contains only lowercase letters, numbers, and hyphens
- ✅ Description is clear and concise (100-200 chars)
- ✅ Description explains when the skill should be used
- ✅ Markdown is well-formatted and organized
- ✅ No syntax errors in YAML
- ✅ No syntax errors in Markdown
- ✅ Examples are clear and practical
- ✅ References and links are correct
- ✅ Skill is discoverable by agents

---

## Troubleshooting

### Skill Not Being Discovered

**Problem:** My skill isn't showing up in the MCP inspector.

**Solutions:**
1. Verify `SKILL.md` file exists in skill directory
2. Check that directory name matches skill name (hyphen-case)
3. Validate YAML frontmatter has `name` and `description`
4. Ensure YAML syntax is correct (colons, hyphens, etc.)
5. Restart the MCP skills server
6. Check skill path is in discovered directories

### Name Validation Errors

**Problem:** "Skill name contains invalid characters"

**Solutions:**
1. Use only lowercase letters, numbers, and hyphens
2. Remove underscores, spaces, or special characters
3. Ensure name starts and ends with alphanumeric
4. Match directory name exactly

### Description Issues

**Problem:** Agents aren't using my skill

**Solutions:**
1. Make description more descriptive of purpose
2. Add context about when the skill should be used
3. Be more specific than generic descriptions
4. Include keywords that describe the skill's function

---

## Resources

- **Anthropic Agent Skills Spec**: Official specification for skill format
- **Anthropic Documentation**: https://docs.anthropic.com
- **MCP Protocol**: Model Context Protocol specification
- **Claude Code Documentation**: Official Claude Code resources

---

## Next Steps

1. Review the Anthropic Agent Skills Spec
2. Study existing skills in the anthropic.agent.skills directory
3. Plan your skill's purpose and structure
4. Create the directory and SKILL.md file
5. Write comprehensive Markdown content
6. Validate using the checklist above
7. Test with the MCP Skills Server
8. Share and iterate based on feedback

Happy skill creating! 🚀
