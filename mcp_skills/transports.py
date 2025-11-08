"""
MCP Transport Abstraction - Support for multiple transport types.

Implements abstract base classes and concrete implementations for:
- stdio: Local process communication
- http: HTTP/HTTPS with request/response
- sse: Server-sent events with streaming
"""

import asyncio
import json
import subprocess
import logging
import aiohttp
import time
import webbrowser
import secrets
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


def _open_browser(url: str) -> None:
    """
    Open URL in browser.
    Tries termux-open-url first (Termux), then 'am start' (Android), then webbrowser.
    """
    try:
        # Try Termux way first
        subprocess.run(
            ["termux-open-url", url],
            check=True,
            capture_output=True,
        )
        logger.info(f"🌐 Opened browser for authentication")
        return
    except FileNotFoundError:
        pass
    except subprocess.CalledProcessError as e:
        logger.debug(f"termux-open-url failed: {e}")

    try:
        # Try Android way (works without Termux)
        subprocess.run(
            ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            check=True,
            capture_output=True,
        )
        logger.info(f"🌐 Opened browser with 'am start'")
        return
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Fallback to Python's webbrowser
    try:
        webbrowser.open(url)
        logger.info(f"🌐 Opened browser with webbrowser module")
        return
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")
        logger.info(f"\n{'='*80}")
        logger.info("⚠️  Please open this URL in your browser to authenticate:")
        logger.info(f"   {url}")
        logger.info(f"{'='*80}\n")


# ============================================================================
# Authentication Framework
# ============================================================================

@dataclass
class OAuthToken:
    """Represents an OAuth token with expiry"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    acquired_at: float = None

    def __post_init__(self):
        if self.acquired_at is None:
            self.acquired_at = time.time()

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expired (with buffer for refresh)"""
        if not self.expires_in:
            return False
        expiry_time = self.acquired_at + self.expires_in - buffer_seconds
        return time.time() > expiry_time


class MCPAuth(ABC):
    """Base class for MCP authentication"""

    @abstractmethod
    async def authenticate(self) -> Dict[str, str]:
        """
        Perform authentication and return headers to include in requests.

        Returns:
            Dict of headers to include (e.g., {"Authorization": "Bearer token"})
        """
        pass

    @abstractmethod
    async def refresh_if_needed(self) -> bool:
        """
        Refresh authentication if needed.

        Returns:
            True if refreshed, False if no refresh needed
        """
        pass


class BearerTokenAuth(MCPAuth):
    """Bearer token authentication (static API keys, JWT tokens)"""

    def __init__(self, token: str):
        """
        Initialize with a bearer token.

        Args:
            token: The bearer token (API key, JWT, etc.)
        """
        self.token = token

    async def authenticate(self) -> Dict[str, str]:
        """Return authorization header"""
        return {"Authorization": f"Bearer {self.token}"}

    async def refresh_if_needed(self) -> bool:
        """No refresh needed for static tokens"""
        return False


class APIKeyAuth(MCPAuth):
    """API key authentication with custom header"""

    def __init__(self, header_name: str, api_key: str):
        """
        Initialize with API key and header name.

        Args:
            header_name: Name of the header (e.g., "X-API-Key")
            api_key: The API key value
        """
        self.header_name = header_name
        self.api_key = api_key

    async def authenticate(self) -> Dict[str, str]:
        """Return custom header with API key"""
        return {self.header_name: self.api_key}

    async def refresh_if_needed(self) -> bool:
        """No refresh needed for static API keys"""
        return False


class OAuthAuth(MCPAuth):
    """
    OAuth 2.0 authentication with support for multiple flows.

    Supports:
    - Authorization Code Flow (with user interaction)
    - Client Credentials Flow (service-to-service)
    - Refresh token flow
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        auth_url: Optional[str] = None,
        scope: Optional[str] = None,
        redirect_uri: str = "http://localhost:8080/callback",
    ):
        """
        Initialize OAuth authentication.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_url: Token endpoint URL
            auth_url: Authorization endpoint URL (for code flow)
            scope: Requested scopes
            redirect_uri: Redirect URI for authorization code flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.auth_url = auth_url
        self.scope = scope
        self.redirect_uri = redirect_uri
        self.token: Optional[OAuthToken] = None

    async def authenticate(self) -> Dict[str, str]:
        """
        Get OAuth token and return authorization header.
        Uses client credentials flow (service-to-service).
        """
        if self.token and not self.token.is_expired():
            return {"Authorization": f"{self.token.token_type} {self.token.access_token}"}

        # Get new token via client credentials flow
        await self._get_token_client_credentials()
        return {"Authorization": f"{self.token.token_type} {self.token.access_token}"}

    async def refresh_if_needed(self) -> bool:
        """Refresh token if expired or missing"""
        if not self.token or self.token.is_expired():
            if self.token and self.token.refresh_token:
                await self._refresh_token()
            else:
                await self._get_token_client_credentials()
            return True
        return False

    async def _get_token_client_credentials(self) -> None:
        """Get token using client credentials flow"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            if self.scope:
                payload["scope"] = self.scope

            try:
                async with session.post(self.token_url, data=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(f"OAuth token request failed: {error_text}")

                    data = await resp.json()
                    self.token = OAuthToken(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_in=data.get("expires_in"),
                        scope=data.get("scope"),
                    )
                    logger.debug(f"Obtained OAuth token, expires in {self.token.expires_in}s")

            except Exception as e:
                logger.error(f"Failed to obtain OAuth token: {e}")
                raise

    async def _refresh_token(self) -> None:
        """Refresh token using refresh token"""
        if not self.token or not self.token.refresh_token:
            await self._get_token_client_credentials()
            return

        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.token.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            try:
                async with session.post(self.token_url, data=payload) as resp:
                    if resp.status != 200:
                        logger.warning("Token refresh failed, re-authenticating")
                        await self._get_token_client_credentials()
                        return

                    data = await resp.json()
                    self.token = OAuthToken(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_in=data.get("expires_in"),
                        refresh_token=data.get("refresh_token", self.token.refresh_token),
                        scope=data.get("scope"),
                    )
                    logger.debug("Token refreshed successfully")

            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                await self._get_token_client_credentials()


class OAuthDiscoveryAuth(MCPAuth):
    """
    OAuth 2.0 with automatic discovery and interactive user login.

    Discovers OAuth endpoints from .well-known/oauth-authorization-server
    and performs Authorization Code Flow with browser-based user login.
    """

    def __init__(
        self,
        client_id: str,
        discovery_url: str,
        scope: Optional[str] = None,
        redirect_uri: str = "http://localhost:8080/callback",
        port: int = 8080,
    ):
        """
        Initialize OAuth Discovery authentication.

        Args:
            client_id: OAuth client ID (public, not requiring secret)
            discovery_url: Domain URL for .well-known discovery
            scope: Requested scopes
            redirect_uri: Redirect URI for callback (must match registered)
            port: Local port for callback server
        """
        self.client_id = client_id
        self.discovery_url = discovery_url.rstrip("/")
        self.scope = scope
        self.redirect_uri = redirect_uri
        self.port = port
        self.token: Optional[OAuthToken] = None
        self.authorization_code: Optional[str] = None
        self.state: str = secrets.token_urlsafe(32)
        self.auth_endpoint: Optional[str] = None
        self.token_endpoint: Optional[str] = None
        self._callback_ready = asyncio.Event()

    async def authenticate(self) -> Dict[str, str]:
        """
        Authenticate using Authorization Code Flow.
        Opens browser for user login and exchanges code for token.
        """
        if self.token and not self.token.is_expired():
            return {"Authorization": f"{self.token.token_type} {self.token.access_token}"}

        # Discover OAuth endpoints
        await self._discover_endpoints()

        # Perform interactive authentication
        await self._perform_auth_code_flow()

        return {"Authorization": f"{self.token.token_type} {self.token.access_token}"}

    async def refresh_if_needed(self) -> bool:
        """Refresh token if expired or missing"""
        if not self.token or self.token.is_expired():
            if self.token and self.token.refresh_token:
                await self._refresh_token()
            else:
                await self._perform_auth_code_flow()
            return True
        return False

    async def _discover_endpoints(self) -> None:
        """Discover OAuth endpoints from .well-known/oauth-authorization-server"""
        discovery_endpoint = f"{self.discovery_url}/.well-known/oauth-authorization-server"

        logger.debug(f"Discovering OAuth endpoints from {discovery_endpoint}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(discovery_endpoint, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        raise RuntimeError(
                            f"OAuth discovery failed: {resp.status} {await resp.text()}"
                        )

                    discovery = await resp.json()
                    self.auth_endpoint = discovery.get("authorization_endpoint")
                    self.token_endpoint = discovery.get("token_endpoint")

                    if not self.auth_endpoint or not self.token_endpoint:
                        raise RuntimeError(
                            "OAuth discovery missing authorization_endpoint or token_endpoint"
                        )

                    logger.debug(f"Discovered OAuth endpoints: {self.auth_endpoint}, {self.token_endpoint}")

        except Exception as e:
            logger.error(f"Failed to discover OAuth endpoints: {e}")
            raise

    async def _perform_auth_code_flow(self) -> None:
        """Perform Authorization Code Flow with user browser interaction"""
        # Start callback server
        server_task = asyncio.create_task(self._run_callback_server())

        try:
            # Wait for server to be ready
            await asyncio.wait_for(self._callback_ready.wait(), timeout=5)

            # Build authorization URL
            auth_params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "state": self.state,
            }
            if self.scope:
                auth_params["scope"] = self.scope

            auth_url = f"{self.auth_endpoint}?{urllib.parse.urlencode(auth_params)}"

            logger.info(f"Opening browser for authentication...")
            _open_browser(auth_url)

            # Wait for callback (with timeout)
            await asyncio.wait_for(self._wait_for_code(), timeout=300)  # 5 minutes

            if not self.authorization_code:
                raise RuntimeError("Authorization code not received")

            # Exchange code for token
            await self._exchange_code_for_token()

        finally:
            # Stop callback server
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    async def _run_callback_server(self) -> None:
        """Run local HTTP server to receive authorization code"""

        callback_code_received = asyncio.Event()

        class CallbackHandler(BaseHTTPRequestHandler):
            auth_instance = self

            def do_GET(self):
                """Handle OAuth callback"""
                try:
                    # Parse query parameters
                    parsed_url = urllib.parse.urlparse(self.path)
                    query_params = urllib.parse.parse_qs(parsed_url.query)

                    code = query_params.get("code", [None])[0]
                    state = query_params.get("state", [None])[0]
                    error = query_params.get("error", [None])[0]

                    if error:
                        logger.error(f"OAuth error from server: {error}")
                        error_desc = query_params.get("error_description", [error])[0]
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            f"<html><body>Authentication failed: {error_desc}</body></html>".encode()
                        )
                        return

                    if state != self.auth_instance.state:
                        logger.error("OAuth state parameter mismatch")
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"<html><body>State mismatch</body></html>")
                        return

                    if code:
                        self.auth_instance.authorization_code = code
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            b"<html><body>Authentication successful! You can close this window.</body></html>"
                        )
                        logger.debug("Received OAuth authorization code")
                        callback_code_received.set()
                    else:
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"<html><body>Missing authorization code</body></html>")

                except Exception as e:
                    logger.error(f"Error in callback handler: {e}")
                    self.send_response(500)
                    self.end_headers()

            def log_message(self, format, *args):
                """Suppress HTTP server logging"""
                pass

        try:
            server = HTTPServer(("localhost", self.port), CallbackHandler)
            logger.debug(f"Callback server listening on http://localhost:{self.port}")
            self._callback_ready.set()

            # Run server in a loop until code received or cancelled
            while not callback_code_received.is_set():
                server.handle_request()  # Handle single request
                if callback_code_received.is_set():
                    break

        except Exception as e:
            logger.error(f"Callback server error: {e}")
            raise
        finally:
            try:
                server.server_close()
            except:
                pass

    async def _wait_for_code(self) -> None:
        """Wait for authorization code to be received"""
        while not self.authorization_code:
            await asyncio.sleep(0.1)

    async def _exchange_code_for_token(self) -> None:
        """Exchange authorization code for access token"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "authorization_code",
                "code": self.authorization_code,
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
            }

            try:
                async with session.post(self.token_endpoint, data=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(f"Token exchange failed: {error_text}")

                    data = await resp.json()
                    self.token = OAuthToken(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_in=data.get("expires_in"),
                        refresh_token=data.get("refresh_token"),
                        scope=data.get("scope"),
                    )
                    logger.info(f"Obtained OAuth token via code flow, expires in {self.token.expires_in}s")

            except Exception as e:
                logger.error(f"Failed to exchange authorization code: {e}")
                raise

    async def _refresh_token(self) -> None:
        """Refresh token using refresh token"""
        if not self.token or not self.token.refresh_token:
            await self._perform_auth_code_flow()
            return

        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.token.refresh_token,
                "client_id": self.client_id,
            }

            try:
                async with session.post(self.token_endpoint, data=payload) as resp:
                    if resp.status != 200:
                        logger.warning("Token refresh failed, re-authenticating")
                        await self._perform_auth_code_flow()
                        return

                    data = await resp.json()
                    self.token = OAuthToken(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_in=data.get("expires_in"),
                        refresh_token=data.get("refresh_token", self.token.refresh_token),
                        scope=data.get("scope"),
                    )
                    logger.debug("Token refreshed successfully")

            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                await self._perform_auth_code_flow()


# ============================================================================
# Transport Framework
# ============================================================================

class MCPTransport(ABC):
    """Base class for MCP transports"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MCP server"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection"""
        pass

    @abstractmethod
    async def send_request(self, method: str, params: Dict) -> Dict:
        """
        Send JSON-RPC request and receive response.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Response data
        """
        pass


class StdioTransport(MCPTransport):
    """Stdio-based transport for local MCP servers"""

    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        """
        Initialize stdio transport.

        Args:
            command: Command to execute
            args: Arguments to pass to command
            env: Environment variables
        """
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0

    async def connect(self) -> None:
        """Start MCP server process"""
        try:
            cmd = [self.command] + self.args
            logger.debug(f"Starting process: {cmd}")

            import os
            full_env = {**dict(os.environ), **self.env}

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                text=True,
                bufsize=1,
            )

            # Send initialize request
            await self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-skills-aggregator",
                    "version": "0.1.1"
                }
            })

            logger.info("Stdio transport connected")

        except Exception as e:
            if self.process:
                self.process.terminate()
                self.process = None
            raise RuntimeError(f"Failed to connect stdio transport: {e}")

    async def disconnect(self) -> None:
        """Terminate process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
                try:
                    self.process.kill()
                except:
                    pass
            finally:
                self.process = None

    async def send_request(self, method: str, params: Dict) -> Dict:
        """Send request over stdin/stdout"""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Process not running")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }

        try:
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from server")

            response = json.loads(response_line)

            if "error" in response:
                raise RuntimeError(f"RPC error: {response['error']}")

            return response.get("result", {})

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise


class HTTPTransport(MCPTransport):
    """HTTP/HTTPS transport for remote MCP servers"""

    def __init__(
        self,
        url: str,
        auth: Optional[MCPAuth] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Initialize HTTP transport.

        Args:
            url: Base URL of MCP server (e.g., https://mcp.example.com)
            auth: Authentication instance
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        self.url = url.rstrip("/")
        self.auth = auth
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_id = 0

    async def connect(self) -> None:
        """Create HTTP session and initialize"""
        try:
            ssl_context = None
            if not self.verify_ssl:
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)

            # Send initialize request
            await self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-skills-aggregator",
                    "version": "0.1.1"
                }
            })

            logger.info(f"HTTP transport connected to {self.url}")

        except Exception as e:
            if self.session:
                await self.session.close()
                self.session = None
            raise RuntimeError(f"Failed to connect HTTP transport: {e}")

    async def disconnect(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def send_request(self, method: str, params: Dict) -> Dict:
        """Send request over HTTP"""
        if not self.session:
            raise RuntimeError("Session not connected")

        # Refresh auth if needed
        if self.auth:
            await self.auth.refresh_if_needed()

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }

        # Build headers
        headers = {"Content-Type": "application/json"}
        if self.auth:
            auth_headers = await self.auth.authenticate()
            headers.update(auth_headers)

        try:
            async with self.session.post(
                f"{self.url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {error_text}")

                response = await resp.json()

                if "error" in response:
                    raise RuntimeError(f"RPC error: {response['error']}")

                return response.get("result", {})

        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise


class SSETransport(MCPTransport):
    """Server-sent events transport for streaming MCP servers"""

    def __init__(
        self,
        url: str,
        auth: Optional[MCPAuth] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Initialize SSE transport.

        Args:
            url: Base URL of SSE endpoint (e.g., https://sse.example.com/stream)
            auth: Authentication instance
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        self.url = url.rstrip("/")
        self.auth = auth
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_id = 0
        self.response_queue: asyncio.Queue = asyncio.Queue()
        self.stream_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to SSE stream"""
        try:
            ssl_context = None
            if not self.verify_ssl:
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)

            # Start listening to SSE stream
            self.stream_task = asyncio.create_task(self._listen_stream())

            # Send initialize request
            await self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-skills-aggregator",
                    "version": "0.1.1"
                }
            })

            logger.info(f"SSE transport connected to {self.url}")

        except Exception as e:
            if self.session:
                await self.session.close()
                self.session = None
            if self.stream_task:
                self.stream_task.cancel()
            raise RuntimeError(f"Failed to connect SSE transport: {e}")

    async def disconnect(self) -> None:
        """Disconnect from SSE stream"""
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass

        if self.session:
            await self.session.close()
            self.session = None

    async def send_request(self, method: str, params: Dict) -> Dict:
        """Send request and wait for response via SSE"""
        if not self.session:
            raise RuntimeError("Session not connected")

        # Refresh auth if needed
        if self.auth:
            await self.auth.refresh_if_needed()

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }

        # Build headers
        headers = {"Content-Type": "application/json"}
        if self.auth:
            auth_headers = await self.auth.authenticate()
            headers.update(auth_headers)

        try:
            # Send request
            async with self.session.post(
                f"{self.url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status not in (200, 202):
                    error_text = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {error_text}")

            # Wait for response from SSE stream
            timeout = time.time() + self.timeout
            while time.time() < timeout:
                try:
                    response = self.response_queue.get_nowait()
                    if response.get("id") == self.request_id:
                        if "error" in response:
                            raise RuntimeError(f"RPC error: {response['error']}")
                        return response.get("result", {})
                    else:
                        # Put back in queue if not for us
                        await self.response_queue.put(response)
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.1)

            raise RuntimeError(f"Request timeout waiting for response")

        except Exception as e:
            logger.error(f"SSE request failed: {e}")
            raise

    async def _listen_stream(self) -> None:
        """Listen to SSE stream and queue responses"""
        # Refresh auth if needed
        if self.auth:
            await self.auth.refresh_if_needed()

        headers = {}
        if self.auth:
            auth_headers = await self.auth.authenticate()
            headers.update(auth_headers)

        try:
            async with self.session.get(
                self.url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=None),  # Streaming timeout
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"SSE stream error: {resp.status} {error_text}")
                    return

                async for line in resp.content:
                    if not line:
                        continue

                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        try:
                            message = json.loads(data_str)
                            await self.response_queue.put(message)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from SSE: {data_str}")

        except asyncio.CancelledError:
            logger.debug("SSE stream listener cancelled")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
