#!/usr/bin/env python3
"""
Simple test MCP server for testing MCP aggregation.
This server exposes a few simple tools for demonstration.
"""

import json
import sys
import logging

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger(__name__)


def send_json_rpc(result=None, error=None):
    """Send JSON-RPC response"""
    response = {
        "jsonrpc": "2.0",
        "id": 1,
    }
    if error:
        response["error"] = error
    else:
        response["result"] = result

    print(json.dumps(response))
    sys.stdout.flush()


def handle_initialize(params):
    """Handle initialize request"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "serverInfo": {
            "name": "test-mcp-server",
            "version": "0.1.0"
        }
    }


def handle_tools_list(params):
    """Handle tools/list request"""
    return {
        "tools": [
            {
                "name": "add",
                "description": "Add two numbers together",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "First number"
                        },
                        "b": {
                            "type": "number",
                            "description": "Second number"
                        }
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "multiply",
                "description": "Multiply two numbers together",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "First number"
                        },
                        "b": {
                            "type": "number",
                            "description": "Second number"
                        }
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "greet",
                "description": "Greet someone by name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name to greet"
                        }
                    },
                    "required": ["name"]
                }
            }
        ]
    }


def handle_tools_call(params):
    """Handle tools/call request"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    logger.debug(f"Calling tool: {tool_name} with args: {arguments}")

    if tool_name == "add":
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        result = a + b
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"The sum of {a} and {b} is {result}"
                }
            ]
        }

    elif tool_name == "multiply":
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        result = a * b
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"The product of {a} and {b} is {result}"
                }
            ]
        }

    elif tool_name == "greet":
        name = arguments.get("name", "stranger")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Hello, {name}! Welcome to the test MCP server."
                }
            ]
        }

    else:
        return {
            "error": f"Unknown tool: {tool_name}"
        }


def main():
    """Main MCP server loop"""
    logger.debug("Test MCP server starting...")

    while True:
        try:
            # Read JSON-RPC request
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})

            logger.debug(f"Received request: {method}")

            # Route to handler
            if method == "initialize":
                result = handle_initialize(params)
                send_json_rpc(result=result)

            elif method == "tools/list":
                result = handle_tools_list(params)
                send_json_rpc(result=result)

            elif method == "tools/call":
                result = handle_tools_call(params)
                send_json_rpc(result=result)

            else:
                send_json_rpc(error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            send_json_rpc(error={
                "code": -32700,
                "message": f"Parse error: {e}"
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            send_json_rpc(error={
                "code": -32603,
                "message": f"Internal error: {e}"
            })


if __name__ == "__main__":
    main()
