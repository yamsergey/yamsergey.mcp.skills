"""MCP Server Aggregation - Discover and aggregate tools from other MCP servers"""

import json
import subprocess
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server"""
    name: str
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, name: str, config: Dict) -> "MCPServerConfig":
        """Create from mcp-servers.json format"""
        return cls(
            name=name,
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {})
        )


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

            if "command" not in server_config:
                logger.warning(f"Server {server_name} missing 'command' field")
                continue

            try:
                servers[server_name] = MCPServerConfig.from_dict(server_name, server_config)
            except Exception as e:
                logger.error(f"Error loading server {server_name}: {e}")

        return servers


class MCPServerConnector:
    """Manages connection to a single MCP server via stdio"""

    def __init__(self, config: MCPServerConfig):
        """
        Initialize connector for an MCP server.

        Args:
            config: MCPServerConfig for the server
        """
        self.config = config
        self.process = None
        self.initialized = False

    async def connect(self) -> None:
        """
        Start MCP server process and initialize connection.

        Raises:
            RuntimeError: If server fails to start or initialize
        """
        try:
            # Build command with args
            cmd = [self.config.command]
            if self.config.args:
                cmd.extend(self.config.args)

            logger.debug(f"Starting MCP server: {self.config.name} - {cmd}")

            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**(dict(os.environ) if self.config.env is None else self.config.env)},
                text=True,
                bufsize=1
            )

            # Send initialize request
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-skills-aggregator",
                    "version": "0.1.1"
                }
            })

            self.initialized = True
            logger.info(f"Connected to MCP server: {self.config.name}")

        except Exception as e:
            if self.process:
                self.process.terminate()
                self.process = None
            raise RuntimeError(f"Failed to connect to MCP server {self.config.name}: {e}")

    async def get_tools(self) -> List[MCPTool]:
        """
        Fetch available tools from MCP server.

        Returns:
            List of MCPTool objects

        Raises:
            RuntimeError: If server not connected or request fails
        """
        if not self.initialized:
            raise RuntimeError(f"MCP server {self.config.name} not connected")

        try:
            response = await self._send_request("tools/list", {})

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
        if not self.initialized:
            raise RuntimeError(f"MCP server {self.config.name} not connected")

        try:
            response = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            return response

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.config.name}: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error disconnecting from {self.config.name}: {e}")
                try:
                    self.process.kill()
                except:
                    pass
            finally:
                self.process = None
                self.initialized = False

    async def _send_request(self, method: str, params: Dict) -> Dict:
        """
        Send JSON-RPC request to MCP server and get response.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Response data

        Raises:
            RuntimeError: If request fails or server not running
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError(f"MCP server {self.config.name} not running")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from MCP server")

            response = json.loads(response_line)

            # Check for JSON-RPC errors
            if "error" in response:
                raise RuntimeError(f"MCP error: {response['error']}")

            return response.get("result", {})

        except Exception as e:
            logger.error(f"Request failed for {method}: {e}")
            raise


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
