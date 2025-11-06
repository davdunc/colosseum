from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from colosseum.mcp.loader import load_mcp_servers

class SupervisorAgent:
    """
    Supervisor agent that manages tools and MCP servers for multi-agent workflows.

    Uses LangGraph's create_react_agent for modern agent creation with ReAct prompting.
    """

    def __init__(self, tools=None, model="gpt-4"):
        self.llm = ChatOpenAI(temperature=0, model=model)
        self.tools = tools or []
        self._initialize_agent()
        self.mcp_servers = load_mcp_servers()
        # Make MCP servers available for all agents to use directly
        # Agents can access self.mcp_servers as needed

    def _initialize_agent(self):
        """Initialize or re-initialize the agent with current tools."""
        if self.tools:
            # LangGraph's create_react_agent returns a compiled graph that can be invoked
            self.agent = create_react_agent(self.llm, self.tools)
        else:
            self.agent = None

    def register_tool(self, tool: Tool):
        """Register a new tool with the agent and re-initialize."""
        self.tools.append(tool)
        # Re-initialize agent with new tools
        self._initialize_agent()

    def run(self, input_text):
        """
        Run the agent with the given input.

        Args:
            input_text: The input query or task for the agent

        Returns:
            The agent's response
        """
        if self.agent is None:
            raise RuntimeError("No tools registered. Please register at least one tool before running.")

        # LangGraph agents use invoke with messages
        result = self.agent.invoke({"messages": [("user", input_text)]})
        return result