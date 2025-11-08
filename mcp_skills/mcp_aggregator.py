"""MCP Server Aggregation - Discover and aggregate tools from other MCP servers"""

import json
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .transports import (
    MCPTransport,
    StdioTransport,
    HTTPTransport,
    SSETransport,
    MCPAuth,
    BearerTokenAuth,
    APIKeyAuth,
    OAuthAuth,
    OAuthDiscoveryAuth,
)

logger = logging.getLogger(__name__)


def _expand_env_vars(value: str) -> str:
    """Expand environment variables in string (supports $VAR and ${VAR} syntax)"""
    if not isinstance(value, str):
        return value

    import re
    result = value
    # Handle ${VAR} syntax
    def replace_var(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    result = re.sub(r'\$\{([^}]+)\}', replace_var, result)
    # Handle $VAR syntax (variable name followed by non-identifier char)
    result = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)(?=[^A-Za-z0-9_]|$)', lambda m: os.environ.get(m.group(1), m.group(0)), result)
    return result


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server"""
    name: str
    transport: str = "stdio"  # stdio, http, sse
    # Stdio options
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    # HTTP/SSE options
    url: Optional[str] = None
    auth: Optional[Dict[str, Any]] = None  # {"type": "bearer", "token": "..."} etc.
    timeout: int = 30
    verify_ssl: bool = True

    @classmethod
    def from_dict(cls, name: str, config: Dict) -> "MCPServerConfig":
        """Create from mcp-servers.json format"""
        transport = config.get("transport", "stdio")

        if transport == "stdio":
            return cls(
                name=name,
                transport=transport,
                command=config.get("command", ""),
                args=config.get("args", []),
                env=config.get("env", {}),
            )
        elif transport in ("http", "sse"):
            return cls(
                name=name,
                transport=transport,
                url=_expand_env_vars(config.get("url", "")),
                auth=config.get("auth"),
                timeout=config.get("timeout", 30),
                verify_ssl=config.get("verify_ssl", True),
            )
        else:
            raise ValueError(f"Unknown transport type: {transport}")


@dataclass
class MCPTool:
    """Tool information from an MCP server"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    source_server: str


class MCPConfigLoader:
    """Load MCP server configurations from standard format"""

    @staticmethod
    def load_config(config_path: str) -> Dict[str, MCPServerConfig]:
        """
        Load MCP server configurations from file.

        Args:
            config_path: Path to mcp-servers.json file

        Returns:
            Dict of server_name -> MCPServerConfig

        Raises:
            FileNotFoundError: If config file not found
            json.JSONDecodeError: If config is invalid JSON
            ValueError: If config format is invalid
        """
        file_path = Path(config_path).expanduser()

        if not file_path.exists():
            raise FileNotFoundError(f"MCP config file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in MCP config file: {e.msg}",
                e.doc,
                e.pos
            )

        if not isinstance(config_data, dict):
            raise ValueError("MCP config must be a JSON object")

        servers = {}
        for server_name, server_config in config_data.items():
            if not isinstance(server_config, dict):
                logger.warning(f"Skipping invalid server config: {server_name}")
                continue

            # Validate transport-specific required fields
            transport = server_config.get("transport", "stdio")
            if transport == "stdio" and "command" not in server_config:
                logger.warning(f"Server {server_name} (stdio) missing 'command' field")
                continue
            elif transport in ("http", "sse") and "url" not in server_config:
                logger.warning(f"Server {server_name} ({transport}) missing 'url' field")
                continue

            try:
                servers[server_name] = MCPServerConfig.from_dict(server_name, server_config)
            except Exception as e:
                logger.error(f"Error loading server {server_name}: {e}")

        return servers


def _create_auth(auth_config: Optional[Dict[str, Any]]) -> Optional[MCPAuth]:
    """
    Create authentication instance from configuration.

    Args:
        auth_config: Authentication configuration dict with 'type' and type-specific fields

    Returns:
        MCPAuth instance or None if no auth config provided

    Supported auth types:
        - bearer: Static bearer token
        - apikey: Custom header-based API key
        - oauth: OAuth 2.0 Client Credentials Flow
        - oauth-discovery: OAuth 2.0 Authorization Code Flow with .well-known discovery
    """
    if not auth_config:
        return None

    auth_type = auth_config.get("type", "").lower()

    if auth_type == "bearer":
        token = _expand_env_vars(auth_config.get("token", ""))
        return BearerTokenAuth(token)

    elif auth_type == "apikey":
        header_name = auth_config.get("header", "X-API-Key")
        api_key = _expand_env_vars(auth_config.get("key", ""))
        return APIKeyAuth(header_name, api_key)

    elif auth_type == "oauth":
        client_id = _expand_env_vars(auth_config.get("client_id", ""))
        client_secret = _expand_env_vars(auth_config.get("client_secret", ""))
        token_url = _expand_env_vars(auth_config.get("token_url", ""))
        auth_url = auth_config.get("auth_url")
        if auth_url:
            auth_url = _expand_env_vars(auth_url)
        scope = auth_config.get("scope")
        return OAuthAuth(client_id, client_secret, token_url, auth_url, scope)

    elif auth_type == "oauth-discovery":
        client_id = _expand_env_vars(auth_config.get("client_id", ""))
        discovery_url = _expand_env_vars(auth_config.get("discovery_url", ""))
        scope = auth_config.get("scope")
        redirect_uri = auth_config.get("redirect_uri", "http://localhost:8080/callback")
        port = auth_config.get("port", 8080)

        if not client_id or not discovery_url:
            logger.error("oauth-discovery requires 'client_id' and 'discovery_url'")
            return None

        return OAuthDiscoveryAuth(
            client_id=client_id,
            discovery_url=discovery_url,
            scope=scope,
            redirect_uri=redirect_uri,
            port=port
        )

    else:
        logger.warning(f"Unknown auth type: {auth_type}")
        return None


class MCPServerConnector:
    """Manages connection to a single MCP server via transport abstraction"""

    def __init__(self, config: MCPServerConfig):
        """
        Initialize connector for an MCP server.

        Args:
            config: MCPServerConfig for the server
        """
        self.config = config
        self.transport: Optional[MCPTransport] = None
        self.initialized = False

    async def connect(self) -> None:
        """
        Start MCP server and initialize connection via transport.

        Raises:
            RuntimeError: If server fails to start or initialize
        """
        try:
            # Create transport based on config
            if self.config.transport == "stdio":
                self.transport = StdioTransport(
                    command=self.config.command,
                    args=self.config.args,
                    env=self.config.env
                )
            elif self.config.transport == "http":
                auth = _create_auth(self.config.auth)
                self.transport = HTTPTransport(
                    url=self.config.url,
                    auth=auth,
                    timeout=self.config.timeout,
                    verify_ssl=self.config.verify_ssl
                )
            elif self.config.transport == "sse":
                auth = _create_auth(self.config.auth)
                self.transport = SSETransport(
                    url=self.config.url,
                    auth=auth,
                    timeout=self.config.timeout,
                    verify_ssl=self.config.verify_ssl
                )
            else:
                raise ValueError(f"Unknown transport: {self.config.transport}")

            # Connect transport
            await self.transport.connect()
            self.initialized = True
            logger.info(f"Connected to MCP server: {self.config.name}")

        except Exception as e:
            raise RuntimeError(f"Failed to connect to MCP server {self.config.name}: {e}")

    async def get_tools(self) -> List[MCPTool]:
        """
        Fetch available tools from MCP server.

        Returns:
            List of MCPTool objects

        Raises:
            RuntimeError: If server not connected or request fails
        """
        if not self.initialized or not self.transport:
            raise RuntimeError(f"MCP server {self.config.name} not connected")

        try:
            response = await self.transport.send_request("tools/list", {})

            tools = []
            if response and "tools" in response:
                for tool_def in response["tools"]:
                    tools.append(MCPTool(
                        name=tool_def.get("name", ""),
                        description=tool_def.get("description", ""),
                        input_schema=tool_def.get("inputSchema", {}),
                        source_server=self.config.name
                    ))

            logger.debug(f"Retrieved {len(tools)} tools from {self.config.name}")
            return tools

        except Exception as e:
            logger.error(f"Failed to get tools from {self.config.name}: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If server not connected or call fails
        """
        if not self.initialized or not self.transport:
            raise RuntimeError(f"MCP server {self.config.name} not connected")

        try:
            response = await self.transport.send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            return response

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.config.name}: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self.transport:
            try:
                await self.transport.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from {self.config.name}: {e}")
            finally:
                self.transport = None
                self.initialized = False


class MCPAggregator:
    """Aggregate tools from multiple MCP servers"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP aggregator.

        Args:
            config_path: Path to mcp-servers.json config file
        """
        self.config_path = config_path
        self.servers: Dict[str, MCPServerConnector] = {}
        self.tools: Dict[str, MCPTool] = {}  # tool_id -> MCPTool

    async def load_from_config(self) -> None:
        """Load and connect to all configured MCP servers"""
        if not self.config_path:
            logger.debug("No MCP config provided")
            return

        try:
            configs = MCPConfigLoader.load_config(self.config_path)
            logger.info(f"Loaded {len(configs)} MCP server configurations")

            for name, config in configs.items():
                await self._add_server(name, config)

        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            raise

    async def _add_server(self, name: str, config: MCPServerConfig) -> None:
        """
        Connect to a single MCP server and discover its tools.

        Args:
            name: Server name
            config: MCPServerConfig
        """
        try:
            connector = MCPServerConnector(config)
            await connector.connect()

            # Fetch tools
            tools = await connector.get_tools()
            logger.info(f"Discovered {len(tools)} tools from {name}")

            # Store server and tools
            self.servers[name] = connector
            for tool in tools:
                tool_id = f"{name}::{tool.name}"
                self.tools[tool_id] = tool
                logger.debug(f"Added tool: {tool_id}")

        except Exception as e:
            logger.error(f"Failed to connect to server {name}: {e}")

    async def get_tool(self, tool_id: str) -> Optional[MCPTool]:
        """Get tool by ID (format: 'server_name::tool_name')"""
        return self.tools.get(tool_id)

    async def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool from an aggregated MCP server.

        Args:
            tool_id: Tool ID (format: 'server_name::tool_name')
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If tool not found or call fails
        """
        if tool_id not in self.tools:
            raise RuntimeError(f"Tool not found: {tool_id}")

        tool = self.tools[tool_id]
        server = self.servers.get(tool.source_server)

        if not server:
            raise RuntimeError(f"Server not connected: {tool.source_server}")

        return await server.call_tool(tool.name, arguments)

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers"""
        for connector in self.servers.values():
            await connector.disconnect()
        self.servers.clear()
        self.tools.clear()

    def list_tools(self) -> Dict[str, MCPTool]:
        """Get all available tools as a dict (tool_id -> MCPTool)"""
        return dict(self.tools)
