class AgentRegistry:
    def __init__(self):
        self.agents = {}
        self.mcp_servers = {}

    def register_agent(self, name, agent):
        self.agents[name] = agent

    def register_mcp(self, name, mcp):
        self.mcp_servers[name] = mcp

    def get_agent(self, name):
        return self.agents.get(name)

    def get_mcp(self, name):
        return self.mcp_servers.get(name)
# create Builder pattern for Adding an agent to the registry
def add_agent_to_registry(name, agent):
    agent_registry.register_agent(name, agent)
    return agent_registry
agent_registry = AgentRegistry()
