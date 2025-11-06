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

from .skill_manager import SkillManager
from .security import SecurityError
from .mcp_aggregator import MCPAggregator, MCPTool


class SkillsServer:
    """MCP Server for exposing skills as tools"""

    def __init__(
        self,
        user_skills_dir=None,
        project_skills_dir=None,
        enable_search_api=False,
        search_tool_description=None,
        mcp_config_path=None,
    ):
        """
        Initialize MCP server.

        Args:
            user_skills_dir: Path to user skills directory
            project_skills_dir: Path to project skills directory
            enable_search_api: If True, use discovery API (search_skills + get_skill).
                             If False, expose all skills as individual tools (original behavior).
                             Default: False (backward compatible)
            search_tool_description: Custom description for search_skills tool.
                                   Can be either:
                                   - A string: used directly as the description
                                   - A file path: description is read from the file
                                   - None: uses default description
                                   Only applies in search API mode.
            mcp_config_path: Path to mcp-servers.json config file to aggregate tools from other MCPs.
                           If provided, tools from configured MCP servers will be discovered and exposed as skills.
        """
        self.skill_manager = SkillManager(user_skills_dir, project_skills_dir)
        self.enable_search_api = enable_search_api
        self.search_tool_description = self._load_description(search_tool_description)
        self.mcp_config_path = mcp_config_path
        self.mcp_aggregator = None  # Initialized in async context

        self.server = Server(
            name="mcp-skills",
            version="0.1.1",
            instructions="MCP server for exposing Anthropic skills as tools"
        )

        # Register handlers - using direct decorator pattern
        self.server.list_tools()(self._list_tools_handler)
        self.server.call_tool()(self._call_tool_handler)

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

            # Add MCP-aggregated tools
            if self.mcp_aggregator:
                for tool_id, mcp_tool in self.mcp_aggregator.list_tools().items():
                    tool = Tool(
                        name=tool_id,  # Format: "server_name::tool_name"
                        description=mcp_tool.description or f"Tool from {mcp_tool.source_server}",
                        inputSchema=mcp_tool.input_schema or {
                            "type": "object",
                            "properties": {},
                            "required": []
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
                elif "::" in name and self.mcp_aggregator:
                    # MCP-aggregated tool (format: "server_name::tool_name")
                    return await self._handle_mcp_tool(name, arguments)
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
        location = arguments.get("location", "project")

        if not all([name, description, content]):
            raise SecurityError("name, description, and content are required")

        metadata = self.skill_manager.create_skill(name, description, content, location)

        result = {
            "message": f"Skill '{name}' created successfully",
            "metadata": metadata.to_dict(),
            "path": str(metadata.file_path),
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

    async def _handle_mcp_tool(self, tool_id: str, arguments: dict) -> CallToolResult:
        """
        Handle execution of a tool from an aggregated MCP server.

        Args:
            tool_id: Tool ID in format "server_name::tool_name"
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            result = await self.mcp_aggregator.call_tool(tool_id, arguments)

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2) if isinstance(result, dict) else str(result))],
                isError=False,
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error calling MCP tool {tool_id}: {str(e)}")],
                isError=True,
            )

    async def run(self):
        """Run the server"""
        # Initialize MCP aggregator if config path provided
        if self.mcp_config_path:
            try:
                self.mcp_aggregator = MCPAggregator(self.mcp_config_path)
                await self.mcp_aggregator.load_from_config()
            except Exception as e:
                print(f"Warning: Failed to load MCP config: {e}")

        try:
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
        finally:
            # Cleanup MCP connections
            if self.mcp_aggregator:
                await self.mcp_aggregator.disconnect_all()


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
    parser.add_argument(
        "--mcp-config",
        type=str,
        default=None,
        help="Path to mcp-servers.json config file to aggregate tools from other MCP servers. "
             "If provided, tools from configured MCP servers will be discovered and exposed as skills. "
             "Supports standard MCP config format (command, args, env fields).",
    )

    args = parser.parse_args()

    server = SkillsServer(
        user_skills_dir=args.user_skills,
        project_skills_dir=args.project_skills,
        enable_search_api=args.search_api,
        search_tool_description=args.search_description,
        mcp_config_path=args.mcp_config,
    )

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
