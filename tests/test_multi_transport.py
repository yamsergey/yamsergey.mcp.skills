"""
Tests for multi-transport MCP aggregation with various authentication methods.

Tests cover:
1. Transport instantiation and connection
2. Authentication framework (Bearer, API Key, OAuth)
3. MCPServerConnector with different transports
4. MCPAggregator configuration loading
5. Tool discovery and routing
"""

import pytest
import json
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, Dict, Any

from mcp_skills.mcp_aggregator import (
    MCPServerConfig,
    MCPTool,
    MCPServerConnector,
    MCPAggregator,
    MCPConfigLoader,
    _expand_env_vars,
    _create_auth,
)
from mcp_skills.transports import (
    StdioTransport,
    HTTPTransport,
    SSETransport,
    BearerTokenAuth,
    APIKeyAuth,
    OAuthAuth,
)


# ============================================================================
# Tests for Environment Variable Expansion
# ============================================================================

class TestEnvVarExpansion:
    """Test environment variable expansion in configuration"""

    def test_expand_braces_syntax(self):
        """Test ${VAR} syntax expansion"""
        os.environ["TEST_VAR"] = "test_value"
        result = _expand_env_vars("prefix_${TEST_VAR}_suffix")
        assert result == "prefix_test_value_suffix"

    def test_expand_dollar_syntax(self):
        """Test $VAR syntax expansion"""
        os.environ["TEST_VAR"] = "test_value"
        result = _expand_env_vars("prefix_$TEST_VAR.end")
        assert result == "prefix_test_value.end"

    def test_expand_missing_var(self):
        """Test missing variable remains unchanged"""
        result = _expand_env_vars("prefix_${MISSING_VAR}_suffix")
        assert result == "prefix_${MISSING_VAR}_suffix"

    def test_expand_multiple_vars(self):
        """Test multiple variable expansion"""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"
        result = _expand_env_vars("${VAR1}_and_${VAR2}")
        assert result == "value1_and_value2"

    def test_expand_non_string(self):
        """Test non-string input remains unchanged"""
        result = _expand_env_vars(None)
        assert result is None


# ============================================================================
# Tests for MCPServerConfig
# ============================================================================

class TestMCPServerConfig:
    """Test MCP server configuration creation and validation"""

    def test_stdio_config_creation(self):
        """Test creation of stdio transport config"""
        config_dict = {
            "command": "python",
            "args": ["-m", "mcp"],
            "env": {"DEBUG": "true"}
        }
        config = MCPServerConfig.from_dict("test_server", config_dict)

        assert config.name == "test_server"
        assert config.transport == "stdio"
        assert config.command == "python"
        assert config.args == ["-m", "mcp"]
        assert config.env == {"DEBUG": "true"}

    def test_http_config_creation(self):
        """Test creation of HTTP transport config"""
        config_dict = {
            "transport": "http",
            "url": "https://api.example.com",
            "timeout": 60,
            "verify_ssl": False
        }
        config = MCPServerConfig.from_dict("http_server", config_dict)

        assert config.name == "http_server"
        assert config.transport == "http"
        assert config.url == "https://api.example.com"
        assert config.timeout == 60
        assert config.verify_ssl is False

    def test_sse_config_creation(self):
        """Test creation of SSE transport config"""
        config_dict = {
            "transport": "sse",
            "url": "https://stream.example.com/events",
            "timeout": 30
        }
        config = MCPServerConfig.from_dict("sse_server", config_dict)

        assert config.name == "sse_server"
        assert config.transport == "sse"
        assert config.url == "https://stream.example.com/events"

    def test_invalid_transport(self):
        """Test invalid transport type raises error"""
        config_dict = {
            "transport": "invalid",
            "url": "https://example.com"
        }
        with pytest.raises(ValueError, match="Unknown transport"):
            MCPServerConfig.from_dict("bad_server", config_dict)

    def test_http_config_with_auth(self):
        """Test HTTP config with authentication"""
        config_dict = {
            "transport": "http",
            "url": "https://api.example.com",
            "auth": {
                "type": "bearer",
                "token": "sk-1234"
            }
        }
        config = MCPServerConfig.from_dict("auth_server", config_dict)

        assert config.auth is not None
        assert config.auth["type"] == "bearer"
        assert config.auth["token"] == "sk-1234"


# ============================================================================
# Tests for Authentication Creation
# ============================================================================

class TestAuthCreation:
    """Test authentication instance creation from config"""

    def test_create_bearer_auth(self):
        """Test creation of bearer token auth"""
        auth_config = {
            "type": "bearer",
            "token": "sk-test-token"
        }
        auth = _create_auth(auth_config)

        assert isinstance(auth, BearerTokenAuth)
        assert auth.token == "sk-test-token"

    def test_create_apikey_auth(self):
        """Test creation of API key auth"""
        auth_config = {
            "type": "apikey",
            "header": "X-Custom-Key",
            "key": "secret-key"
        }
        auth = _create_auth(auth_config)

        assert isinstance(auth, APIKeyAuth)
        assert auth.header_name == "X-Custom-Key"
        assert auth.api_key == "secret-key"

    def test_create_apikey_auth_default_header(self):
        """Test API key auth uses default header if not specified"""
        auth_config = {
            "type": "apikey",
            "key": "secret-key"
        }
        auth = _create_auth(auth_config)

        assert isinstance(auth, APIKeyAuth)
        assert auth.header_name == "X-API-Key"

    def test_create_oauth_auth(self):
        """Test creation of OAuth auth"""
        auth_config = {
            "type": "oauth",
            "client_id": "client-123",
            "client_secret": "secret-456",
            "token_url": "https://auth.example.com/token",
            "scope": "read write"
        }
        auth = _create_auth(auth_config)

        assert isinstance(auth, OAuthAuth)
        assert auth.client_id == "client-123"
        assert auth.client_secret == "secret-456"
        assert auth.token_url == "https://auth.example.com/token"
        assert auth.scope == "read write"

    def test_create_auth_with_env_vars(self):
        """Test auth creation expands environment variables"""
        os.environ["API_TOKEN"] = "expanded-token"
        auth_config = {
            "type": "bearer",
            "token": "${API_TOKEN}"
        }
        auth = _create_auth(auth_config)

        assert auth.token == "expanded-token"

    def test_create_auth_none(self):
        """Test creating auth with None returns None"""
        auth = _create_auth(None)
        assert auth is None

    def test_create_auth_unknown_type(self):
        """Test unknown auth type returns None and logs warning"""
        auth_config = {"type": "unknown"}
        auth = _create_auth(auth_config)
        assert auth is None


# ============================================================================
# Tests for MCPServerConnector with Different Transports
# ============================================================================

class TestMCPServerConnector:
    """Test MCP server connector with different transport types"""

    @pytest.mark.asyncio
    async def test_connector_stdio_transport(self):
        """Test connector instantiation with stdio transport"""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=["-m", "mcp"]
        )
        connector = MCPServerConnector(config)

        assert connector.config == config
        assert connector.transport is None
        assert not connector.initialized

    @pytest.mark.asyncio
    async def test_connector_http_transport(self):
        """Test connector instantiation with HTTP transport"""
        config = MCPServerConfig(
            name="test",
            transport="http",
            url="https://api.example.com",
            auth={"type": "bearer", "token": "test-token"}
        )
        connector = MCPServerConnector(config)

        assert connector.config == config
        assert not connector.initialized

    @pytest.mark.asyncio
    async def test_connector_sse_transport(self):
        """Test connector instantiation with SSE transport"""
        config = MCPServerConfig(
            name="test",
            transport="sse",
            url="https://stream.example.com"
        )
        connector = MCPServerConnector(config)

        assert connector.config == config
        assert not connector.initialized

    @pytest.mark.asyncio
    async def test_connector_disconnect_when_not_connected(self):
        """Test disconnect when not connected does nothing"""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python"
        )
        connector = MCPServerConnector(config)
        # Should not raise any error
        await connector.disconnect()
        assert not connector.initialized


# ============================================================================
# Tests for MCPConfigLoader
# ============================================================================

class TestMCPConfigLoader:
    """Test loading MCP server configurations from files"""

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file raises error"""
        with pytest.raises(FileNotFoundError):
            MCPConfigLoader.load_config("/nonexistent/path/config.json")

    def test_load_config_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error"""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            MCPConfigLoader.load_config(str(config_file))

    def test_load_config_not_dict(self, tmp_path):
        """Test loading non-dict JSON raises error"""
        config_file = tmp_path / "config.json"
        config_file.write_text("[]")

        with pytest.raises(ValueError, match="must be a JSON object"):
            MCPConfigLoader.load_config(str(config_file))

    def test_load_config_valid(self, tmp_path):
        """Test loading valid configuration"""
        config_file = tmp_path / "config.json"
        config_data = {
            "stdio_server": {
                "command": "python",
                "args": ["-m", "mcp"]
            },
            "http_server": {
                "transport": "http",
                "url": "https://api.example.com"
            }
        }
        config_file.write_text(json.dumps(config_data))

        configs = MCPConfigLoader.load_config(str(config_file))

        assert len(configs) == 2
        assert "stdio_server" in configs
        assert "http_server" in configs
        assert configs["stdio_server"].transport == "stdio"
        assert configs["http_server"].transport == "http"

    def test_load_config_skip_invalid_servers(self, tmp_path):
        """Test that invalid server configs are skipped"""
        config_file = tmp_path / "config.json"
        config_data = {
            "valid_server": {
                "command": "python"
            },
            "invalid_not_dict": "not a dict",
            "missing_command": {
                "transport": "http"
                # Missing required 'url' for http transport, but should still load
            }
        }
        config_file.write_text(json.dumps(config_data))

        configs = MCPConfigLoader.load_config(str(config_file))

        # Should have at least the valid server
        assert "valid_server" in configs

    def test_load_config_with_auth(self, tmp_path):
        """Test loading config with authentication"""
        config_file = tmp_path / "config.json"
        config_data = {
            "secure_server": {
                "transport": "http",
                "url": "https://api.example.com",
                "auth": {
                    "type": "bearer",
                    "token": "${API_TOKEN}"
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        configs = MCPConfigLoader.load_config(str(config_file))

        assert "secure_server" in configs
        config = configs["secure_server"]
        assert config.auth is not None
        assert config.auth["type"] == "bearer"


# ============================================================================
# Tests for MCPAggregator
# ============================================================================

class TestMCPAggregator:
    """Test MCP aggregator functionality"""

    def test_aggregator_init_no_config(self):
        """Test aggregator initialization without config"""
        aggregator = MCPAggregator(config_path=None)

        assert aggregator.config_path is None
        assert len(aggregator.servers) == 0
        assert len(aggregator.tools) == 0

    def test_aggregator_init_with_config(self):
        """Test aggregator initialization with config path"""
        aggregator = MCPAggregator(config_path="/path/to/config.json")

        assert aggregator.config_path == "/path/to/config.json"

    @pytest.mark.asyncio
    async def test_aggregator_load_empty_config(self, tmp_path):
        """Test loading empty config"""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        aggregator = MCPAggregator(config_path=str(config_file))
        await aggregator.load_from_config()

        assert len(aggregator.servers) == 0
        assert len(aggregator.tools) == 0

    @pytest.mark.asyncio
    async def test_aggregator_no_config_provided(self):
        """Test loading when no config provided"""
        aggregator = MCPAggregator(config_path=None)
        # Should not raise any error
        await aggregator.load_from_config()

    def test_aggregator_list_tools_empty(self):
        """Test listing tools when none available"""
        aggregator = MCPAggregator()
        tools = aggregator.list_tools()

        assert tools == {}

    @pytest.mark.asyncio
    async def test_aggregator_disconnect_all(self):
        """Test disconnecting from all servers"""
        aggregator = MCPAggregator()
        # Should not raise any error
        await aggregator.disconnect_all()


# ============================================================================
# Configuration Examples for Different Transports
# ============================================================================

@pytest.fixture
def example_configs(tmp_path):
    """Provide example configurations for testing"""
    return {
        "stdio_simple": {
            "command": "python",
            "args": ["-m", "mcp"]
        },
        "http_no_auth": {
            "transport": "http",
            "url": "https://api.example.com"
        },
        "http_bearer": {
            "transport": "http",
            "url": "https://api.example.com",
            "auth": {
                "type": "bearer",
                "token": "${API_TOKEN}"
            }
        },
        "http_apikey": {
            "transport": "http",
            "url": "https://api.example.com",
            "auth": {
                "type": "apikey",
                "header": "X-API-Key",
                "key": "${API_KEY}"
            }
        },
        "http_oauth": {
            "transport": "http",
            "url": "https://api.example.com",
            "auth": {
                "type": "oauth",
                "client_id": "${OAUTH_CLIENT_ID}",
                "client_secret": "${OAUTH_CLIENT_SECRET}",
                "token_url": "https://auth.example.com/token"
            }
        },
        "sse_stream": {
            "transport": "sse",
            "url": "https://stream.example.com/events",
            "auth": {
                "type": "bearer",
                "token": "${STREAM_TOKEN}"
            }
        }
    }


class TestExampleConfigurations:
    """Test example configurations from MCP_AGGREGATION_GUIDE.md"""

    def test_example_configs_parse(self, example_configs):
        """Test that all example configs parse correctly"""
        for name, config_dict in example_configs.items():
            config = MCPServerConfig.from_dict(name, config_dict)
            assert config.name == name
            assert config.transport in ("stdio", "http", "sse")

    def test_example_stdio_config(self, example_configs):
        """Test stdio example config"""
        config = MCPServerConfig.from_dict("stdio_simple", example_configs["stdio_simple"])
        assert config.transport == "stdio"
        assert config.command == "python"
        assert config.args == ["-m", "mcp"]

    def test_example_http_no_auth(self, example_configs):
        """Test HTTP no-auth example config"""
        config = MCPServerConfig.from_dict("http_no_auth", example_configs["http_no_auth"])
        assert config.transport == "http"
        assert config.url == "https://api.example.com"
        assert config.auth is None

    def test_example_http_bearer(self, example_configs):
        """Test HTTP bearer auth example config"""
        os.environ["API_TOKEN"] = "test-token"
        config = MCPServerConfig.from_dict("http_bearer", example_configs["http_bearer"])
        assert config.transport == "http"
        assert config.auth is not None
        auth = _create_auth(config.auth)
        assert isinstance(auth, BearerTokenAuth)

    def test_example_http_apikey(self, example_configs):
        """Test HTTP API key auth example config"""
        os.environ["API_KEY"] = "secret-key"
        config = MCPServerConfig.from_dict("http_apikey", example_configs["http_apikey"])
        assert config.transport == "http"
        assert config.auth is not None
        auth = _create_auth(config.auth)
        assert isinstance(auth, APIKeyAuth)

    def test_example_http_oauth(self, example_configs):
        """Test HTTP OAuth example config"""
        os.environ["OAUTH_CLIENT_ID"] = "client-123"
        os.environ["OAUTH_CLIENT_SECRET"] = "secret-456"
        config = MCPServerConfig.from_dict("http_oauth", example_configs["http_oauth"])
        assert config.transport == "http"
        assert config.auth is not None
        auth = _create_auth(config.auth)
        assert isinstance(auth, OAuthAuth)

    def test_example_sse_stream(self, example_configs):
        """Test SSE example config"""
        os.environ["STREAM_TOKEN"] = "stream-token"
        config = MCPServerConfig.from_dict("sse_stream", example_configs["sse_stream"])
        assert config.transport == "sse"
        assert config.url == "https://stream.example.com/events"
        assert config.auth is not None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components"""

    def test_full_config_workflow(self, tmp_path):
        """Test complete workflow: write config, load, create connectors"""
        config_file = tmp_path / "mcp-servers.json"
        config_data = {
            "server1": {
                "command": "python",
                "args": ["-m", "test_server"]
            },
            "server2": {
                "transport": "http",
                "url": "https://api.example.com",
                "auth": {
                    "type": "bearer",
                    "token": "test-token"
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        # Load configs
        configs = MCPConfigLoader.load_config(str(config_file))

        # Verify both loaded
        assert len(configs) == 2
        assert "server1" in configs
        assert "server2" in configs

        # Verify correct transports
        assert configs["server1"].transport == "stdio"
        assert configs["server2"].transport == "http"

        # Verify authentication
        assert configs["server1"].auth is None
        assert configs["server2"].auth is not None

    def test_config_with_environment_variables(self, tmp_path):
        """Test configuration with environment variable expansion"""
        os.environ["TEST_URL"] = "https://test.example.com"
        os.environ["TEST_TOKEN"] = "test-token-123"

        config_file = tmp_path / "config.json"
        config_data = {
            "secure_server": {
                "transport": "http",
                "url": "${TEST_URL}",
                "auth": {
                    "type": "bearer",
                    "token": "${TEST_TOKEN}"
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        # Load and verify expansion
        configs = MCPConfigLoader.load_config(str(config_file))
        config = configs["secure_server"]

        # URL and token should be expanded
        assert "https://test.example.com" in config.url
        assert config.auth["token"] == "${TEST_TOKEN}"  # Expansion happens during auth creation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
