"""
MCP client classes defined here are the app-side consumers that request data from MCP servers.
They securely ground LLMs, access data, trigger tools, and manage AI agents by providing a unified interface
to various MCP server types (news, tickers, brokers, etc).
"""

from abc import ABC, abstractmethod

class MCPServer(ABC):
    @abstractmethod
    def get_resource(self, resource_type, **kwargs):
        pass

# Some MCP servers may support multiple resource types by inheriting from multiple base classes.
class NewsMCPServer(MCPServer):
    pass

class TickerMCPServer(MCPServer):
    pass

class BrokerMCPServer(MCPServer):
    pass

def mcp_server_factory(config):
    """
    Given a config dict (from mcp.json), instantiate the appropriate MCPServer.
    Example config:
    {
        "type": "fetch",
        "base_url": "http://localhost:8080",
        "api_key": "..."
    }
    """
    mcp_type = config.get("type")
    if mcp_type == "fetch":
        from .fetch import FetchMCPServer
        return FetchMCPServer(
            base_url=config.get("base_url"),
            api_key=config.get("api_key")
        )
    elif mcp_type == "ib":
        from .ib import InteractiveBrokersMCP
        return InteractiveBrokersMCP(config)
    elif mcp_type == "etrade":
        from .etrade import ETradeMCP
        return ETradeMCP(config)
    elif mcp_type == "dastrader":
        from .dastrader import DASTraderMCP
        return DASTraderMCP(config)
    # ...add more as needed...
    else:
        raise ValueError(f"Unknown MCP server type: {mcp_type}")
