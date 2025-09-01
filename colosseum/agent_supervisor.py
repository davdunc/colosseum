from langchain.agents import AgentExecutor, initialize_agent, Tool
from langchain.llms import OpenAI
from colosseum.mcp.loader import load_mcp_servers

class SupervisorAgent:
    def __init__(self, tools=None):
        self.llm = OpenAI(temperature=0)
        self.tools = tools or []
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent="zero-shot-react-description",
            verbose=True
        )
        self.mcp_servers = load_mcp_servers()
        # Make MCP servers available for all agents to use directly
        # Agents can access self.mcp_servers as needed

    def register_tool(self, tool: Tool):
        self.tools.append(tool)
        # Re-initialize agent with new tools
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent="zero-shot-react-description",
            verbose=True
        )

    def run(self, input_text):
        return self.agent.run(input_text)