"""
MCP (Model Context Protocol) integration module

Provides MCP server implementations for various data sources and brokers,
including base classes and a factory pattern for server instantiation.
"""

from colosseum.mcp.base import (
    MCPServer,
    NewsMCPServer,
    TickerMCPServer,
    BrokerMCPServer,
    mcp_server_factory,
)
from colosseum.mcp.loader import load_mcp_servers

__all__ = [
    "MCPServer",
    "NewsMCPServer",
    "TickerMCPServer",
    "BrokerMCPServer",
    "mcp_server_factory",
    "load_mcp_servers",
]
