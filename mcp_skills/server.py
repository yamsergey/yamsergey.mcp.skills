"""MCP Server implementation"""

import sys
import json
from typing import Any
import argparse

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ToolResult,
)
import mcp.server.stdio

from .skill_manager import SkillManager
from .security import SecurityError


class SkillsServer:
    """MCP Server for exposing skills as tools"""

    def __init__(self, user_skills_dir=None, project_skills_dir=None):
        self.server = Server("mcp-skills")
        self.skill_manager = SkillManager(user_skills_dir, project_skills_dir)

        # Register handlers
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)

    def list_tools(self) -> list[Tool]:
        """List all available tools (skills)"""
        tools = []

        for skill_name, metadata in self.skill_manager.list_skills().items():
            tool = Tool(
                name=skill_name,
                description=metadata.description or f"Skill: {skill_name}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Output format (default: raw markdown)",
                            "enum": ["raw", "json"],
                        }
                    },
                    "required": [],
                },
            )
            tools.append(tool)

        # Add management tools
        management_tools = self._get_management_tools()
        tools.extend(management_tools)

        return tools

    def _get_management_tools(self) -> list[Tool]:
        """Get CRUD operation tools"""
        return [
            Tool(
                name="create_skill",
                description="Create a new skill file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name (alphanumeric, hyphens, underscores)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Skill description",
                        },
                        "content": {
                            "type": "string",
                            "description": "Markdown content of the skill",
                        },
                        "location": {
                            "type": "string",
                            "description": "Where to create the skill",
                            "enum": ["user", "project"],
                            "default": "project",
                        },
                    },
                    "required": ["name", "description", "content"],
                },
            ),
            Tool(
                name="update_skill",
                description="Update an existing skill",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description (optional)",
                        },
                        "content": {
                            "type": "string",
                            "description": "New markdown content (optional)",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="list_skills",
                description="List all available skills with metadata",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool (skill or management operation)"""
        try:
            # Handle management tools
            if name == "list_skills":
                return await self._handle_list_skills(arguments)
            elif name == "create_skill":
                return await self._handle_create_skill(arguments)
            elif name == "update_skill":
                return await self._handle_update_skill(arguments)
            else:
                # Regular skill reading
                return await self._handle_read_skill(name, arguments)

        except SecurityError as e:
            return ToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )
        except Exception as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unexpected error: {str(e)}",
                    )
                ],
                isError=True,
            )

    async def _handle_read_skill(self, skill_name: str, arguments: dict) -> ToolResult:
        """Handle skill reading"""
        content = self.skill_manager.read_skill(skill_name)
        output_format = arguments.get("format", "raw")

        if output_format == "json":
            result = {
                "skill_name": skill_name,
                "content": content,
                "metadata": self.skill_manager.get_skill_metadata(skill_name).to_dict(),
            }
            text_content = json.dumps(result, indent=2)
        else:
            text_content = content

        return ToolResult(
            content=[TextContent(type="text", text=text_content)],
            isError=False,
        )

    async def _handle_list_skills(self, arguments: dict) -> ToolResult:
        """Handle listing skills"""
        skills = self.skill_manager.list_skills()
        result = {
            "total": len(skills),
            "skills": {
                name: metadata.to_dict()
                for name, metadata in skills.items()
            },
        }
        return ToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def _handle_create_skill(self, arguments: dict) -> ToolResult:
        """Handle skill creation"""
        name = arguments.get("name")
        description = arguments.get("description")
        content = arguments.get("content")
        location = arguments.get("location", "project")

        if not all([name, description, content]):
            raise SecurityError("name, description, and content are required")

        metadata = self.skill_manager.create_skill(name, description, content, location)

        result = {
            "message": f"Skill '{name}' created successfully",
            "metadata": metadata.to_dict(),
            "path": str(metadata.file_path),
        }
        return ToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def _handle_update_skill(self, arguments: dict) -> ToolResult:
        """Handle skill update"""
        name = arguments.get("name")
        if not name:
            raise SecurityError("name is required")

        description = arguments.get("description")
        content = arguments.get("content")

        if not (description or content):
            raise SecurityError("At least one of description or content must be provided")

        metadata = self.skill_manager.update_skill(name, description, content)

        result = {
            "message": f"Skill '{name}' updated successfully",
            "metadata": metadata.to_dict(),
        }
        return ToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def run(self):
        """Run the server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, lambda: None)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="MCP Skills Server")
    parser.add_argument(
        "--user-skills",
        type=str,
        default=None,
        help="Path to user skills directory (default: ~/.claude/skills)",
    )
    parser.add_argument(
        "--project-skills",
        type=str,
        default=None,
        help="Path to project skills directory (default: ./.claude/skills)",
    )

    args = parser.parse_args()

    server = SkillsServer(
        user_skills_dir=args.user_skills,
        project_skills_dir=args.project_skills,
    )

    import asyncio

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
