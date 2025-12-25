import uuid
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from colosseum.mcp.loader import load_mcp_servers
from colosseum.database import (
    save_agent_state,
    load_agent_state,
    save_conversation,
    load_conversation_history,
)

class SupervisorAgent:
    """
    Supervisor agent that manages tools and MCP servers for multi-agent workflows.

    Uses LangGraph's create_react_agent for modern agent creation with ReAct prompting.
    Integrates with database for state persistence and conversation history.
    """

    def __init__(
        self,
        tools=None,
        model="gpt-4",
        agent_name: Optional[str] = None,
        session_id: Optional[str] = None,
        persist_state: bool = True,
        persist_conversations: bool = True,
    ):
        self.agent_name = agent_name or f"supervisor-{uuid.uuid4().hex[:8]}"
        self.session_id = session_id or str(uuid.uuid4())
        self.persist_state = persist_state
        self.persist_conversations = persist_conversations

        self.llm = ChatOpenAI(temperature=0, model=model)
        self.tools = tools or []
        self._initialize_agent()
        self.mcp_servers = load_mcp_servers()

        # Load previous state if it exists
        if self.persist_state:
            previous_state = load_agent_state(self.agent_name, self.session_id)
            if previous_state:
                self._restore_state(previous_state)

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

    def run(self, input_text: str) -> Dict[str, Any]:
        """
        Run the agent with the given input.

        Args:
            input_text: The input query or task for the agent

        Returns:
            The agent's response
        """
        if self.agent is None:
            raise RuntimeError("No tools registered. Agent requires at least one tool to function. Use register_tool() to add tools before running.")

        # Save user message to conversation history
        if self.persist_conversations:
            save_conversation(
                session_id=self.session_id,
                agent_name=self.agent_name,
                role="user",
                content=input_text,
            )

        # LangGraph agents use invoke with messages
        result = self.agent.invoke({"messages": [("user", input_text)]})

        # Extract assistant response
        assistant_response = self._extract_response(result)

        # Save assistant message to conversation history
        if self.persist_conversations:
            save_conversation(
                session_id=self.session_id,
                agent_name=self.agent_name,
                role="assistant",
                content=assistant_response,
                metadata={"full_result": str(result)},
            )

        # Save current state
        if self.persist_state:
            self.save_state()

        return result

    def _extract_response(self, result: Dict[str, Any]) -> str:
        """Extract the text response from LangGraph result."""
        if "messages" in result:
            messages = result["messages"]
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    return last_message.content
                elif isinstance(last_message, dict) and "content" in last_message:
                    return last_message["content"]
        return str(result)

    def save_state(self, additional_data: Optional[Dict] = None):
        """
        Save agent state to database.

        Args:
            additional_data: Optional additional data to store with state
        """
        state_data = {
            "model": self.llm.model_name if hasattr(self.llm, "model_name") else "gpt-4",
            "num_tools": len(self.tools),
            "tool_names": [tool.name for tool in self.tools if hasattr(tool, "name")],
            "num_mcp_servers": len(self.mcp_servers),
        }

        if additional_data:
            state_data.update(additional_data)

        save_agent_state(self.agent_name, self.session_id, state_data)

    def _restore_state(self, state_data: Dict):
        """
        Restore agent state from database.

        Args:
            state_data: State data loaded from database
        """
        # For now, just log that we restored state
        # In future, could restore tool configurations, etc.
        print(f"Restored state for {self.agent_name}: {state_data}")

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for this agent's session.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        return load_conversation_history(self.session_id, limit=limit)

    def print_conversation_history(self, limit: Optional[int] = 10):
        """Print formatted conversation history."""
        history = self.get_conversation_history(limit=limit)
        print(f"\n=== Conversation History for {self.agent_name} ===")
        print(f"Session ID: {self.session_id}\n")

        for msg in history:
            role = msg["role"].upper()
            content = msg["content"]
            timestamp = msg["created_at"]
            print(f"[{timestamp}] {role}: {content}\n")