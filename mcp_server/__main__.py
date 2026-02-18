"""Entry point for the UDAE MCP server.

Usage:
    # stdio (default) — for Claude Code / Claude Desktop
    python -m mcp_server

    # SSE — for Docker / remote access
    MCP_TRANSPORT=sse MCP_PORT=5002 python -m mcp_server
"""

import os

from .server import mcp

transport = os.environ.get("MCP_TRANSPORT", "stdio")

mcp.run(transport=transport)
