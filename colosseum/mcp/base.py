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
