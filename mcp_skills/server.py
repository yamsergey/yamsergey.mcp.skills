"""MCP Server implementation

This server exposes skills as MCP tools via stdio interface.
"""

import sys
import json
from typing import Any
import argparse
import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ServerCapabilities,
    ToolsCapability,
)
import mcp.server.stdio

from .skill_manager import SkillManager, SkillPath
from .security import SecurityError


class SkillsServer:
    """MCP Server for exposing skills as tools"""

    def __init__(
        self,
        skills_paths=None,
        enable_search_api=False,
        search_tool_description=None,
    ):
        """
        Initialize MCP server.

        Args:
            skills_paths: List of SkillPath config objects to scan.
                         Defaults to [user: ~/.claude/skills (readonly), project: ./.claude/skills (writable)] if not provided.
            enable_search_api: If True, use discovery API (search_skills + get_skill).
                             If False, expose all skills as individual tools (original behavior).
                             Default: False (backward compatible)
            search_tool_description: Custom description for search_skills tool.
                                   Can be either:
                                   - A string: used directly as the description
                                   - A file path: description is read from the file
                                   - None: uses default description
                                   Only applies in search API mode.
        """
        self.skill_manager = SkillManager(skills_paths)
        self.enable_search_api = enable_search_api
        self.search_tool_description = self._load_description(search_tool_description)

        self.server = Server(
            name="mcp-skills",
            version="0.1.1",
            instructions="MCP server for exposing Anthropic skills as tools"
        )

        # Register handlers - using direct decorator pattern
        self.server.list_tools()(self._list_tools_handler)
        self.server.call_tool()(self._call_tool_handler)

    def _get_create_skill_description(self) -> str:
        """Generate create_skill tool description with available locations"""
        writable_paths = self.skill_manager.get_writable_skill_paths()
        if writable_paths:
            locations = ", ".join([f"'{sp.nickname}'" for sp in writable_paths])
            return f"Create a new skill file. Available writable locations: {locations}. Specify location using the location parameter."
        else:
            return "Create a new skill file. No writable locations configured."

    def _load_description(self, description_input: str) -> str:
        """
        Load description from string or file.

        Args:
            description_input: Either a description string or path to a file

        Returns:
            The description string (or None if input is None)
        """
        if not description_input:
            return None

        # Try to treat it as a file path first
        file_path = Path(description_input).expanduser()
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception as e:
                # If file reading fails, fall back to treating it as a string
                print(f"Warning: Failed to read description file {file_path}: {e}")

        # If not a file or file is empty, use as-is (treat as a string)
        return description_input.strip() if isinstance(description_input, str) else None

    async def _list_tools_handler(self) -> list[Tool]:
        """List available tools based on configured mode"""
        if self.enable_search_api:
            # Search API mode: only expose discovery, access, and management tools
            # This reduces token overhead by 98% vs exposing hundreds of skill tools
            management_tools = self._get_management_tools(self.search_tool_description)
            return management_tools
        else:
            # Original mode: expose all skills as individual tools plus management tools
            tools = []

            # Add skill tools
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
            management_tools = self._get_management_tools(self.search_tool_description)
            tools.extend(management_tools)

            return tools

    def _get_management_tools(self, search_description=None) -> list[Tool]:
        """
        Get CRUD operation tools.

        Args:
            search_description: Custom description for search_skills tool.
                              If None, uses default description.
        """
        # Use custom description if provided, otherwise use default
        default_search_description = "Search for skills using semantic understanding (embeddings). Finds skills by meaning, not just keywords. Returns top matching skills with relevance scores."
        search_description = search_description or default_search_description

        return [
            Tool(
                name="search_skills",
                description=search_description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query (e.g., 'security validation', 'deployment automation', 'testing framework')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags - skill must have ALL specified tags (optional)",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category (optional)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_skill",
                description=self._get_create_skill_description(),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name (alphanumeric, hyphens, underscores, and forward slashes for nesting). Examples: 'my-skill', 'category/my-skill'",
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
                            "enum": [sp.nickname for sp in self.skill_manager.get_writable_skill_paths()],
                            "description": f"Where to create the skill. Available writable locations: {', '.join(sp.nickname for sp in self.skill_manager.get_writable_skill_paths())}",
                        },
                    },
                    "required": ["name", "description", "content", "location"],
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
                name="get_skill",
                description="Load full content of a specific skill by name. Use search_skills first to discover available skills.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name to load (e.g., 'security-audit', 'deployment-automation')",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format (default: raw markdown)",
                            "enum": ["raw", "json"],
                            "default": "raw",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="list_skills",
                description="List all available skills with metadata. Note: Use search_skills for efficient discovery of large skill collections.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]

    async def _call_tool_handler(self, name: str, arguments: dict) -> CallToolResult:
        """Execute a tool (discovery, access, or management operation)"""
        try:
            if self.enable_search_api:
                # Search API mode: handle discovery, access, and management tools
                if name == "search_skills":
                    return await self._handle_search_skills(arguments)
                elif name == "get_skill":
                    return await self._handle_get_skill(arguments)
                elif name == "list_skills":
                    return await self._handle_list_skills(arguments)
                elif name == "create_skill":
                    return await self._handle_create_skill(arguments)
                elif name == "update_skill":
                    return await self._handle_update_skill(arguments)
                else:
                    # Unknown tool
                    raise SecurityError(f"Unknown tool: {name}. Available tools: search_skills, get_skill, list_skills, create_skill, update_skill")
            else:
                # Original mode: handle all tools including individual skill names
                if name == "list_skills":
                    return await self._handle_list_skills(arguments)
                elif name == "create_skill":
                    return await self._handle_create_skill(arguments)
                elif name == "update_skill":
                    return await self._handle_update_skill(arguments)
                else:
                    # Assume it's a skill name in original mode
                    return await self._handle_get_skill({"name": name, **arguments})

        except SecurityError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )
        except Exception as e:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unexpected error: {str(e)}",
                    )
                ],
                isError=True,
            )

    async def _handle_get_skill(self, arguments: dict) -> CallToolResult:
        """Handle getting a specific skill by name"""
        skill_name = arguments.get("name")
        if not skill_name:
            raise SecurityError("skill name (name parameter) is required")

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

        return CallToolResult(
            content=[TextContent(type="text", text=text_content)],
            isError=False,
        )

    async def _handle_list_skills(self, arguments: dict) -> CallToolResult:
        """Handle listing skills"""
        skills = self.skill_manager.list_skills()
        result = {
            "total": len(skills),
            "skills": {
                name: metadata.to_dict()
                for name, metadata in skills.items()
            },
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def _handle_search_skills(self, arguments: dict) -> CallToolResult:
        """Handle skill search with semantic embeddings"""
        query = arguments.get("query")
        if not query:
            raise SecurityError("query is required")

        limit = arguments.get("limit", 10)
        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            limit = 10

        tags = arguments.get("tags")
        category = arguments.get("category")

        # Perform search
        results = self.skill_manager.search_skills(
            query=query,
            limit=limit,
            tags=tags,
            category=category,
        )

        # Format results compactly
        formatted_results = [
            {
                "name": r.name,
                "description": r.description[:150] if r.description else "",  # Truncate
                "similarity_score": r.similarity_score,
                "location": r.location,
                "tags": r.tags or [],
                "category": r.category,
            }
            for r in results
        ]

        result = {
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results,
            "note": "Use skill name from results to get full content",
        }

        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def _handle_create_skill(self, arguments: dict) -> CallToolResult:
        """Handle skill creation"""
        name = arguments.get("name")
        description = arguments.get("description")
        content = arguments.get("content")
        location = arguments.get("location")

        if not all([name, description, content, location]):
            raise SecurityError("name, description, content, and location are required")

        metadata = self.skill_manager.create_skill(name, description, content, location)

        # Find the skill path config to get full location details
        skill_path_config = None
        for sp in self.skill_manager.skills_paths:
            if sp.nickname == location:
                skill_path_config = sp
                break

        result = {
            "message": f"Skill '{name}' created successfully in location '{location}'",
            "skill_name": name,
            "location": {
                "nickname": location,
                "path": skill_path_config.path if skill_path_config else "unknown",
                "full_path": str(metadata.file_path),
                "readonly": skill_path_config.readonly if skill_path_config else None,
            },
            "metadata": metadata.to_dict(),
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def _handle_update_skill(self, arguments: dict) -> CallToolResult:
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
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))],
            isError=False,
        )

    async def run(self):
        """Run the server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            # Simple object with required attributes for initialization
            class InitOptions:
                server_name = "mcp-skills"
                server_version = "0.1.1"
                website_url = None
                icons = None
                instructions = "MCP server for exposing Anthropic skills as tools"
                # Declare that this server supports tools
                capabilities = ServerCapabilities(tools=ToolsCapability())

            await self.server.run(read_stream, write_stream, InitOptions())


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="MCP Skills Server")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON configuration file with skill paths. "
             "Config should have 'skills_paths' array with objects containing 'nickname', 'path', and 'readonly' fields.",
    )
    parser.add_argument(
        "--skills-path",
        type=str,
        action="append",
        dest="skills_paths",
        help="Path to skills directory (can be specified multiple times). "
             "Only used if --config is not provided. "
             "Defaults to [~/.claude/skills, ./.claude/skills] if neither --config nor --skills-path provided.",
    )
    parser.add_argument(
        "--search-api",
        action="store_true",
        default=False,
        help="Enable search API mode (discovery + access pattern). "
             "If disabled, exposes all skills as individual tools (default: disabled for backward compatibility)",
    )
    parser.add_argument(
        "--search-description",
        type=str,
        default=None,
        help="Custom description for the search_skills tool (optional). "
             "Can be either a string or path to a file. "
             "If a file path is provided, the description is read from the file. "
             "Only applies in search API mode.",
    )

    args = parser.parse_args()

    # Load skill paths from config file or CLI arguments
    skills_path_objects = None

    if args.config:
        # Load from config file
        try:
            config_path = Path(args.config).expanduser()
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            skills_paths_data = config.get("skills_paths", [])
            if skills_paths_data:
                skills_path_objects = []
                for sp_data in skills_paths_data:
                    skills_path_objects.append(
                        SkillPath(
                            nickname=sp_data["nickname"],
                            path=sp_data["path"],
                            readonly=sp_data.get("readonly", False),
                        )
                    )
        except Exception as e:
            print(f"Error loading config file {args.config}: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.skills_paths:
        # Convert CLI paths to SkillPath objects with auto-generated nicknames
        skills_path_objects = []
        for i, path in enumerate(args.skills_paths):
            # Generate nickname from path or use index-based nickname
            nickname = Path(path).expanduser().name or f"skills_{i}"
            skills_path_objects.append(
                SkillPath(nickname=nickname, path=path, readonly=False)
            )

    server = SkillsServer(
        skills_paths=skills_path_objects,
        enable_search_api=args.search_api,
        search_tool_description=args.search_description,
    )

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
