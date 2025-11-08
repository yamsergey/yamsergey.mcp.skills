# MCP Aggregation Configuration Guide

This guide explains how to configure the MCP Skills Server to aggregate tools from other MCP servers using different transports and authentication methods.

## Overview

The MCP aggregator allows you to:
1. **Discover tools** from multiple remote or local MCP servers
2. **Aggregate tools** with namespaced naming (e.g., `server_name::tool_name`)
3. **Execute tools** by routing calls to the appropriate MCP server
4. **Support multiple transports**: stdio (local), HTTP/HTTPS (remote), SSE (streaming)
5. **Use multiple auth methods**: Bearer tokens, API keys, OAuth 2.0

## Configuration File Format

Configuration is provided via `mcp-servers.json` (or custom path via `--mcp-config` CLI flag).

### Basic Structure

```json
{
  "server_name": {
    "transport": "stdio|http|sse",
    ...transport-specific options...
  }
}
```

## Transport Types

### 1. Stdio Transport (Local Processes)

For local MCP servers running as subprocesses.

**Options:**
- `transport`: `"stdio"` (required)
- `command`: Command to execute (required)
- `args`: Array of command arguments (optional)
- `env`: Dictionary of environment variables (optional)

**Example:**

```json
{
  "local_mcp": {
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server"],
    "env": {
      "DEBUG": "true"
    }
  }
}
```

### 2. HTTP Transport (HTTP/HTTPS Remote Servers)

For MCP servers accessible via HTTP/HTTPS endpoints.

**Options:**
- `transport`: `"http"` (required)
- `url`: Base URL of the MCP server (required)
- `auth`: Authentication configuration (optional)
- `timeout`: Request timeout in seconds (default: 30)
- `verify_ssl`: Verify SSL certificates (default: true)

**Example:**

```json
{
  "remote_api": {
    "transport": "http",
    "url": "https://api.example.com",
    "timeout": 60,
    "verify_ssl": true
  }
}
```

### 3. SSE Transport (Server-Sent Events / Streaming)

For MCP servers that use Server-Sent Events for streaming responses.

**Options:**
- `transport`: `"sse"` (required)
- `url`: Streaming endpoint URL (required)
- `auth`: Authentication configuration (optional)
- `timeout`: Request timeout in seconds (default: 30)
- `verify_ssl`: Verify SSL certificates (default: true)

**Example:**

```json
{
  "stream_server": {
    "transport": "sse",
    "url": "https://stream.example.com/events",
    "timeout": 30
  }
}
```

## Authentication Methods

### 1. No Authentication

If no `auth` field is provided, requests are sent without authentication headers.

### 2. Bearer Token Authentication

For static API keys, JWT tokens, or other bearer tokens.

**Configuration:**

```json
{
  "server_name": {
    "transport": "http",
    "url": "https://api.example.com",
    "auth": {
      "type": "bearer",
      "token": "sk-1234567890abcdef"
    }
  }
}
```

**Supports environment variable expansion:**

```json
{
  "auth": {
    "type": "bearer",
    "token": "${API_TOKEN}"
  }
}
```

The `${API_TOKEN}` will be replaced with the value of the `API_TOKEN` environment variable.

### 3. API Key Authentication

For custom header-based API key authentication.

**Configuration:**

```json
{
  "server_name": {
    "transport": "http",
    "url": "https://api.example.com",
    "auth": {
      "type": "apikey",
      "header": "X-API-Key",
      "key": "my-secret-key"
    }
  }
}
```

**With environment variables:**

```json
{
  "auth": {
    "type": "apikey",
    "header": "Authorization",
    "key": "${API_KEY}"
  }
}
```

### 4. OAuth 2.0 Authentication

For OAuth 2.0 with Client Credentials Flow (service-to-service authentication).

**Configuration:**

```json
{
  "server_name": {
    "transport": "http",
    "url": "https://api.example.com",
    "auth": {
      "type": "oauth",
      "client_id": "your_client_id",
      "client_secret": "your_client_secret",
      "token_url": "https://auth.example.com/oauth/token",
      "scope": "mcp:read mcp:write"
    }
  }
}
```

**With environment variables:**

```json
{
  "auth": {
    "type": "oauth",
    "client_id": "${OAUTH_CLIENT_ID}",
    "client_secret": "${OAUTH_CLIENT_SECRET}",
    "token_url": "${OAUTH_TOKEN_URL}",
    "scope": "mcp:read mcp:write"
  }
}
```

**Features:**
- Automatic token acquisition using Client Credentials Flow
- Automatic token refresh before expiry (with 60-second buffer)
- Fallback to re-authentication if refresh fails
- Token caching during server lifetime

### 5. OAuth 2.0 with Discovery and Interactive Login

For OAuth 2.0 Authorization Code Flow with automatic endpoint discovery and browser-based user login.

**How it works:**
1. Discovers OAuth endpoints from `.well-known/oauth-authorization-server`
2. Opens user's browser for login and consent
3. Receives authorization code via local callback server
4. Exchanges code for access token
5. Automatically refreshes token when needed

**Configuration:**

```json
{
  "server_name": {
    "transport": "http",
    "url": "https://api.example.com",
    "auth": {
      "type": "oauth-discovery",
      "client_id": "${OAUTH_CLIENT_ID}",
      "discovery_url": "https://auth.example.com",
      "scope": "mcp:read mcp:write"
    }
  }
}
```

**Configuration options:**
- `type`: `"oauth-discovery"` (required)
- `client_id`: OAuth client ID (public, no secret needed) (required)
- `discovery_url`: Domain URL for `.well-known` discovery (required)
- `scope`: Requested scopes (optional)
- `redirect_uri`: Callback redirect URI (default: `http://localhost:8080/callback`)
- `port`: Local port for callback server (default: `8080`)

**Features:**
- Automatic endpoint discovery from `.well-known/oauth-authorization-server`
- Interactive browser-based login
- Security: PKCE-style state parameter for CSRF protection
- Automatic token refresh with 5-minute timeout for user login
- Public client (no client secret required)
- Full token lifecycle management

**Example with custom port:**

```json
{
  "custom_port": {
    "transport": "http",
    "url": "https://api.example.com",
    "auth": {
      "type": "oauth-discovery",
      "client_id": "${OAUTH_CLIENT_ID}",
      "discovery_url": "https://auth.example.com",
      "redirect_uri": "http://localhost:9090/callback",
      "port": 9090,
      "scope": "profile email"
    }
  }
}
```

## Environment Variable Expansion

All string configuration values support environment variable expansion using these syntaxes:

- `${VAR_NAME}` - Recommended syntax
- `$VAR_NAME` - Alternative syntax

**Example:**

```json
{
  "my_server": {
    "transport": "http",
    "url": "${MCP_SERVER_URL}",
    "auth": {
      "type": "bearer",
      "token": "${MCP_TOKEN}"
    }
  }
}
```

Set environment variables before running:

```bash
export MCP_SERVER_URL="https://api.example.com"
export MCP_TOKEN="sk-1234567890"
mcp-skills --mcp-config mcp-servers.json
```

## Complete Examples

### Example 1: Mix of Local and Remote Servers

```json
{
  "local_calculator": {
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "calc_mcp"]
  },
  "remote_weather": {
    "transport": "http",
    "url": "https://weather-api.example.com",
    "auth": {
      "type": "bearer",
      "token": "${WEATHER_API_TOKEN}"
    }
  },
  "remote_database": {
    "transport": "http",
    "url": "https://db.example.com",
    "auth": {
      "type": "oauth",
      "client_id": "${DB_CLIENT_ID}",
      "client_secret": "${DB_CLIENT_SECRET}",
      "token_url": "https://auth.db.example.com/token"
    }
  }
}
```

### Example 2: Streaming with OAuth

```json
{
  "streaming_service": {
    "transport": "sse",
    "url": "https://stream.example.com/events",
    "auth": {
      "type": "oauth",
      "client_id": "${STREAM_CLIENT_ID}",
      "client_secret": "${STREAM_CLIENT_SECRET}",
      "token_url": "https://auth.stream.example.com/oauth/token",
      "scope": "stream:read"
    },
    "timeout": 60
  }
}
```

### Example 3: Multiple Auth Methods

```json
{
  "service_a": {
    "transport": "http",
    "url": "https://api-a.example.com",
    "auth": {
      "type": "apikey",
      "header": "X-Service-Key",
      "key": "${SERVICE_A_KEY}"
    }
  },
  "service_b": {
    "transport": "http",
    "url": "https://api-b.example.com",
    "auth": {
      "type": "bearer",
      "token": "${SERVICE_B_TOKEN}"
    }
  },
  "service_c": {
    "transport": "http",
    "url": "https://api-c.example.com",
    "auth": {
      "type": "oauth",
      "client_id": "${SERVICE_C_CLIENT_ID}",
      "client_secret": "${SERVICE_C_CLIENT_SECRET}",
      "token_url": "https://api-c.example.com/oauth/token"
    }
  }
}
```

### Example 4: OAuth Discovery with Interactive Login

```json
{
  "github_mcp": {
    "transport": "http",
    "url": "https://github.example.com/mcp",
    "auth": {
      "type": "oauth-discovery",
      "client_id": "${GITHUB_CLIENT_ID}",
      "discovery_url": "https://github.example.com",
      "scope": "repo:read user:read"
    }
  },
  "aws_mcp": {
    "transport": "http",
    "url": "https://aws.example.com/mcp",
    "auth": {
      "type": "oauth-discovery",
      "client_id": "${AWS_CLIENT_ID}",
      "discovery_url": "https://auth.aws.example.com",
      "port": 9090,
      "redirect_uri": "http://localhost:9090/callback",
      "scope": "sts:AssumeRole"
    }
  }
}
```

**Usage:**
When the server starts, it will:
1. Discover OAuth endpoints from `.well-known/oauth-authorization-server`
2. Open your browser for login when first needed
3. Handle the callback and exchange code for token
4. Automatically refresh tokens when needed

## Using the Configuration

### Via CLI

```bash
# With custom config path
mcp-skills --mcp-config /path/to/mcp-servers.json

# With environment variables
export MCP_CONFIG_PATH="./mcp-servers.json"
mcp-skills --mcp-config "$MCP_CONFIG_PATH"
```

### Programmatically

```python
from mcp_skills.mcp_aggregator import MCPAggregator

aggregator = MCPAggregator(config_path="mcp-servers.json")
await aggregator.load_from_config()

# List all aggregated tools
tools = aggregator.list_tools()
for tool_id, tool in tools.items():
    print(f"{tool_id}: {tool.description}")

# Call a tool
result = await aggregator.call_tool("server_name::tool_name", {"arg": "value"})
```

## Best Practices

1. **Environment Variables for Secrets**: Always use environment variables for tokens, keys, and secrets. Never commit secrets to version control.

   ```json
   {
     "auth": {
      "token": "${API_TOKEN}"
    }
   }
   ```

2. **Timeout Configuration**: Set appropriate timeouts based on server response times.

   ```json
   {
     "timeout": 60
   }
   ```

3. **SSL Verification**: Always use `verify_ssl: true` in production. Only disable for development/testing.

   ```json
   {
     "verify_ssl": true
   }
   ```

4. **Error Handling**: The aggregator logs errors but continues loading other servers. Check logs for connection issues.

5. **Tool Naming**: Tools are exposed with namespace prefix: `{server_name}::{tool_name}`. Choose clear server names to avoid conflicts.

## Troubleshooting

### Connection Issues

- Check that server URLs are correct and accessible
- Verify authentication credentials are valid
- Check network connectivity for remote servers
- Review logs for detailed error messages

### Authentication Failures

- Verify environment variables are set: `echo $VAR_NAME`
- Check token expiry for OAuth tokens
- Ensure correct auth type for your server
- Review OAuth token URL and client credentials

### Timeout Issues

- Increase `timeout` value if servers are slow to respond
- Check server load and availability
- Monitor network latency to remote servers

## Transport Implementation Details

### Stdio Transport
- Spawns subprocess with specified command
- Communicates via JSON-RPC 2.0 over stdin/stdout
- Environment variables passed to subprocess
- Process lifetime managed by aggregator

### HTTP Transport
- Uses async aiohttp for non-blocking requests
- Supports HTTPS with optional SSL verification
- Authentication headers added automatically
- Endpoint: `{url}/mcp`

### SSE Transport
- Maintains persistent connection to streaming endpoint
- Uses async stream listener for event processing
- Response queue for request-response matching
- Works with streaming and event-driven servers

## Authentication Implementation Details

### Bearer Token
- Static token stored in configuration
- Added as `Authorization: Bearer {token}` header
- No refresh mechanism (use OAuth for refreshing tokens)

### API Key
- Custom header name configurable (default: `X-API-Key`)
- Added as `{header_name}: {key}` header
- No refresh mechanism

### OAuth 2.0
- **Flow**: Client Credentials (service-to-service)
- **Token Acquisition**: POST to `token_url` with client credentials
- **Token Refresh**: Automatic refresh 60 seconds before expiry
- **Fallback**: Re-authenticate if refresh fails
- **Scope**: Optional scope parameter sent with token request
- **Caching**: Token cached for lifetime of auth instance

## See Also

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [OAuth 2.0 Client Credentials Flow](https://tools.ietf.org/html/rfc6749#section-4.4)
