#!/usr/bin/env python3
"""Test stdio communication with MCP server"""

import subprocess
import json
import sys
import time

def send_json_rpc(proc, method, params=None):
    """Send a JSON-RPC request to the server"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    request_json = json.dumps(request) + "\n"
    print(f"\n→ Sending: {method}")
    print(f"  {json.dumps(request, indent=2)}")

    try:
        proc.stdin.write(request_json.encode())
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline().decode()
        if response_line:
            response = json.loads(response_line)
            print(f"\n← Received:")
            print(f"  {json.dumps(response, indent=2)}")
            return response
        else:
            print("✗ No response received")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def main():
    print("=" * 60)
    print("Testing MCP Server Stdio Communication")
    print("=" * 60)

    # Start the server
    print("\n[1] Starting mcp-skills server...")
    try:
        proc = subprocess.Popen(
            ["mcp-skills"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=1
        )
        print("✓ Server started (PID: {})".format(proc.pid))
    except Exception as e:
        print(f"✗ Failed to start server: {e}")
        return False

    time.sleep(1)  # Give server time to start

    # Send initialize request
    print("\n[2] Sending initialize request...")
    response = send_json_rpc(proc, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "0.1.0"
        }
    })

    if not response:
        print("✗ Initialize failed")
        proc.terminate()
        return False

    # Send list_tools request
    print("\n[3] Sending tools/list request...")
    response = send_json_rpc(proc, "tools/list", {})

    if not response:
        print("✗ tools/list failed")
        proc.terminate()
        return False

    # Try to call a tool
    print("\n[4] Sending tools/call request...")
    response = send_json_rpc(proc, "tools/call", {
        "name": "list_skills",
        "arguments": {}
    })

    # Cleanup
    print("\n[5] Terminating server...")
    proc.terminate()
    try:
        proc.wait(timeout=2)
        print("✓ Server terminated gracefully")
    except subprocess.TimeoutExpired:
        proc.kill()
        print("✓ Server killed")

    print("\n" + "=" * 60)
    print("Stdio communication test completed")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
