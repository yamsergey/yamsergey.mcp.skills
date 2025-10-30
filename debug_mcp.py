#!/usr/bin/env python3
"""Debug script to test MCP server communication"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_skills.server import SkillsServer

async def test_server_methods():
    """Test server methods directly without stdio"""
    print("=" * 60)
    print("Testing MCP Server Methods Directly")
    print("=" * 60)

    # Initialize server
    print("\n[1] Initializing server...")
    try:
        server = SkillsServer()
        print("✓ Server initialized")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test list_tools
    print("\n[2] Testing list_tools()...")
    try:
        tools = server.list_tools()
        print(f"✓ list_tools() returned {len(tools)} tools")
        for tool in tools[:3]:
            print(f"  - {tool.name}")
    except Exception as e:
        print(f"✗ list_tools() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test call_tool for list_skills
    print("\n[3] Testing call_tool('list_skills')...")
    try:
        result = await server.call_tool("list_skills", {})
        print(f"✓ call_tool() succeeded")
        print(f"  Result type: {type(result)}")
        print(f"  Has content: {hasattr(result, 'content')}")
        print(f"  Has isError: {hasattr(result, 'isError')}")
        if hasattr(result, 'content') and result.content:
            content = result.content[0].text if result.content else ""
            print(f"  Content preview: {content[:100]}...")
    except Exception as e:
        print(f"✗ call_tool() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("Direct method testing completed")
    print("=" * 60)
    return True

async def main():
    await test_server_methods()

if __name__ == "__main__":
    asyncio.run(main())
