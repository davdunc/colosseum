from langchain.agents import AgentExecutor, initialize_agent, Tool
from langchain.llms import OpenAI

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