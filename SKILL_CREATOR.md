# Skill Creator Guide

The MCP Skills Server includes a comprehensive **skill-creator** skill that helps other AI agents create well-formatted, specification-compliant Anthropic Agent Skills.

## What is the skill-creator Skill?

The `skill-creator` skill is a persistent guide that provides:

- **Format Specification**: Complete YAML frontmatter requirements (required and optional properties)
- **Step-by-Step Process**: How to create skills from planning to validation
- **Best Practices**: Guidelines for writing clear descriptions and well-structured content
- **Validation Rules**: Name constraints, description guidelines, and checklist
- **Templates**: Ready-to-use templates for different types of skills
- **Examples**: Real-world examples from the Anthropic agent skills repository
- **Troubleshooting**: Solutions to common issues
- **Directory Structures**: Examples of minimal to complex skill layouts

## How to Access the skill-creator Skill

The skill is automatically discovered when you run the MCP Skills Server:

```bash
# Start the server
mcp-skills --user-skills /path/to/anthropic.agent.skills/

# The skill-creator skill will be available as a tool
# You can call it through Claude Code or MCP inspector
```

## Using skill-creator with Claude Code

In Claude Code or other AI agents, use the skill-creator tool to:

1. **Learn the skill format**: Understand the Anthropic Agent Skills specification
2. **Plan new skills**: Get guidance on skill purpose and structure
3. **Create well-formatted content**: Use templates and examples
4. **Validate skills**: Check against the validation checklist
5. **Troubleshoot issues**: Find solutions to common problems

## Key Topics Covered

### Format Specification
- Required YAML properties: `name` and `description`
- Optional properties: `license`, `allowed-tools`, `metadata`
- Complete frontmatter examples
- Markdown body guidelines

### Step-by-Step Creation
1. Plan your skill (purpose, name, description, scope)
2. Create the directory
3. Write SKILL.md with frontmatter
4. Add reference files (optional)
5. Validate your skill

### Validation Rules
- **Name**: hyphen-case, lowercase alphanumeric + hyphens only
- **Description**: Clear, concise, explains when to use (100-200 chars)
- **Directory**: Matches skill name exactly
- **Files**: SKILL.md exists with valid YAML and Markdown

### Best Practices
- Write clear, actionable descriptions
- Structure content logically with headings
- Include practical examples
- Cover basic and advanced usage
- Keep consistent naming conventions
- Document prerequisites

### Common Skill Categories
- Development skills
- Design skills
- Content skills
- Data skills
- Integration skills

## Example Usage

When creating a new skill, an agent would:

1. **Call skill-creator** to understand the format
2. **Review the template** provided in the skill
3. **Follow step-by-step process** outlined
4. **Use validation checklist** before finalizing
5. **Reference examples** from Anthropic skills for inspiration

## Location

The skill-creator skill is stored in:
- Default location: `~/.claude/skills/skill-creator.md`
- Or where you configured skills: `.claude/skills/skill-creator.md`

When running with Anthropic agent skills:
```bash
mcp-skills --user-skills /path/to/anthropic.agent.skills/
```

The skill-creator will be automatically discovered alongside other skills.

## Size and Content

- **Size**: ~12.5 KB of comprehensive documentation
- **Sections**: 15+ detailed sections with examples
- **Format**: YAML frontmatter + Markdown body
- **License**: MIT

## Integration with MCP Skills Server

The skill-creator works seamlessly with the MCP Skills Server:

1. **Discovery**: Automatically discovered when skills are scanned
2. **Tool Registration**: Registered as a standard MCP tool
3. **Content Delivery**: Full content returned when tool is called
4. **Metadata**: Properly extracted frontmatter for tool definition

## Use Cases

Agents can use skill-creator to:

- ✅ Create new skills from scratch
- ✅ Understand Anthropic's skill specification
- ✅ Learn from templates and examples
- ✅ Validate new skill implementations
- ✅ Troubleshoot skill-related issues
- ✅ Follow best practices and conventions
- ✅ Get guidance on skill structure

## Next Steps

1. Start the MCP Skills Server
2. Access the skill-creator tool
3. Use it to create well-formatted skills
4. Follow the validation checklist
5. Test your skills with the MCP server

The skill-creator makes it easy for any AI agent to create professional, specification-compliant Anthropic Agent Skills!
