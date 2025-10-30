#!/usr/bin/env python3
"""Test the MCP server functionality"""

import sys
import json
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent))

from mcp_skills.skill_manager import SkillManager
from mcp_skills.server import SkillsServer

def test_mcp_server():
    """Test MCP server initialization and tools"""
    print("=" * 60)
    print("Testing MCP Skills Server")
    print("=" * 60)

    # Use TMPDIR for test skills
    test_skills_dir = os.path.join(os.environ.get("TMPDIR", "/tmp"), "test-skills")

    # Test 1: Initialize server
    print("\n[1] Initializing MCP Server...")
    try:
        server = SkillsServer(project_skills_dir=test_skills_dir)
        print("✓ MCP Server initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize server: {e}")
        return False

    # Test 2: List tools
    print("\n[2] Listing available tools...")
    try:
        tools = server.list_tools()
        print(f"✓ Found {len(tools)} tools")

        # Separate skills from management tools
        skill_tools = [t for t in tools if t.name not in ["create_skill", "update_skill", "list_skills"]]
        management_tools = [t for t in tools if t.name in ["create_skill", "update_skill", "list_skills"]]

        print(f"\n  Skill Tools ({len(skill_tools)}):")
        for tool in skill_tools:
            print(f"    - {tool.name}: {tool.description}")

        print(f"\n  Management Tools ({len(management_tools)}):")
        for tool in management_tools:
            print(f"    - {tool.name}: {tool.description}")
    except Exception as e:
        print(f"✗ Failed to list tools: {e}")
        return False

    # Test 3: Verify tool schema
    print("\n[3] Verifying tool schemas...")
    try:
        for tool in tools:
            if hasattr(tool, 'inputSchema'):
                print(f"✓ {tool.name} has inputSchema")
            else:
                print(f"✗ {tool.name} missing inputSchema")
    except Exception as e:
        print(f"✗ Failed to verify schemas: {e}")
        return False

    # Test 4: Check skill manager metadata caching
    print("\n[4] Checking metadata caching...")
    try:
        skills_meta = server.skill_manager.list_skills()
        print(f"✓ Metadata cached for {len(skills_meta)} skill(s)")
        for name, meta in skills_meta.items():
            print(f"  - {name}: {meta.location} location")
    except Exception as e:
        print(f"✗ Failed to check metadata: {e}")
        return False

    # Test 5: Verify skill content can be read
    print("\n[5] Testing skill content reading...")
    try:
        if skills_meta:
            first_skill_name = list(skills_meta.keys())[0]
            content = server.skill_manager.read_skill(first_skill_name)
            print(f"✓ Successfully read skill '{first_skill_name}' ({len(content)} bytes)")
            print(f"\n  Content preview:")
            print("  " + "-" * 50)
            for line in content.split('\n')[:5]:
                print(f"  {line}")
            print("  " + "-" * 50)
        else:
            print("⚠ No skills found to test reading")
    except Exception as e:
        print(f"✗ Failed to read skill: {e}")
        return False

    print("\n" + "=" * 60)
    print("All MCP server tests passed! ✓")
    print("=" * 60)
    print("\nServer is ready to be used with Claude Code.")
    print("Configure in .claude/mcp-servers.json with:")
    print('  "mcp-skills": {"command": "mcp-skills"}')
    return True

if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)
