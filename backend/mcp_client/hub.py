"""
MCP Client Hub — connects to all 6 MCP servers and provides a unified interface.
Starts each server as a subprocess, collects all available tools, and routes tool calls.
"""

import os
import sys
import json
import asyncio
import logging
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.config import MCP_SERVERS


class MCPClientHub:
    """Manages connections to all MCP servers and routes tool calls."""

    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.tool_map: dict[str, str] = {}  # tool_name -> server_name
        self.all_tools: list[dict] = []  # OpenAI-format tool definitions
        self.exit_stack = AsyncExitStack()
        self._connected = False

    async def connect_all(self):
        """Connect to all 6 MCP servers."""
        if self._connected:
            return

        for server_name, server_config in MCP_SERVERS.items():
            try:
                await self._connect_server(server_name, server_config)
                logger.info(f"[Hub] Connected to '{server_name}' server")
            except Exception as e:
                logger.error(f"[Hub] Failed to connect to '{server_name}': {e}")
                # Continue — don't let one server failure kill everything

        self._connected = True
        logger.info(f"[Hub] Connected to {len(self.sessions)}/{len(MCP_SERVERS)} servers, {len(self.all_tools)} tools available")

    async def _connect_server(self, server_name: str, config: dict):
        """Connect to a single MCP server."""
        # Build environment — merge current env with server-specific env
        env = dict(os.environ)
        env.update(config.get("env", {}))

        server_params = StdioServerParameters(
            command=config["command"],
            args=config["args"],
            env=env
        )

        # Start the server subprocess and create session
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        # Store the session
        self.sessions[server_name] = session

        # Discover tools from this server
        tools_response = await session.list_tools()
        for tool in tools_response.tools:
            # Map tool name to server for routing
            self.tool_map[tool.name] = server_name

            # Convert to OpenAI function calling format
            # Azure OpenAI requires all schemas to have type "object"
            schema = tool.inputSchema if tool.inputSchema else {}
            if not isinstance(schema, dict) or schema.get("type") != "object":
                schema = {"type": "object", "properties": {}}
            if "properties" not in schema:
                schema["properties"] = {}

            self.all_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": f"[{server_name}] {tool.description or ''}",
                    "parameters": schema
                }
            })

        logger.info(f"[Hub] '{server_name}' registered {len(tools_response.tools)} tools: {[t.name for t in tools_response.tools]}")

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Route a tool call to the correct MCP server and return the result."""
        server_name = self.tool_map.get(tool_name)

        if not server_name:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        if server_name not in self.sessions:
            return json.dumps({"error": f"Server '{server_name}' is not connected"})

        try:
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, arguments=arguments)

            # Extract text content from the result
            response_text = ""
            if result.content:
                for content_block in result.content:
                    if hasattr(content_block, "text"):
                        response_text += content_block.text

            logger.info(f"[Hub] {server_name}.{tool_name} → success")
            return response_text

        except Exception as e:
            logger.error(f"[Hub] {server_name}.{tool_name} → error: {e}")
            return json.dumps({"error": str(e)})

    def get_openai_tools(self) -> list[dict]:
        """Return all tools in OpenAI function-calling format."""
        return self.all_tools

    def get_server_status(self) -> dict:
        """Return connection status of all servers."""
        status = {}
        for name in MCP_SERVERS:
            status[name] = {
                "connected": name in self.sessions,
                "description": MCP_SERVERS[name]["description"],
                "tools": [t for t, s in self.tool_map.items() if s == name]
            }
        return status

    async def disconnect_all(self):
        """Gracefully disconnect from all servers."""
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.tool_map.clear()
        self.all_tools.clear()
        self._connected = False
        logger.info("[Hub] All servers disconnected")
