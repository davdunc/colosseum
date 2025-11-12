"""
Simple example showing agent with database persistence.

This example demonstrates:
1. Creating an agent with a persistent session
2. Running multiple queries with conversation history
3. Saving and loading agent state
4. Viewing conversation history
"""

from langchain_core.tools import tool
from colosseum import SupervisorAgent

# Define a simple tool for the agent
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Input should be a valid Python expression."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_portfolio_value() -> str:
    """Get the current portfolio value. Returns a mock value for demonstration."""
    return "Portfolio value: $150,000 (mock data)"


def main():
    print("=== Colosseum Agent with Database Persistence Example ===\n")

    # Create an agent with a named session
    # This allows us to resume the conversation later
    agent = SupervisorAgent(
        tools=[calculator, get_portfolio_value],
        agent_name="investment-advisor",
        session_id="demo-session-001",
        model="gpt-4",
        persist_state=True,
        persist_conversations=True,
    )

    print(f"Agent Name: {agent.agent_name}")
    print(f"Session ID: {agent.session_id}")
    print(f"Number of tools: {len(agent.tools)}")
    print(f"Number of MCP servers: {len(agent.mcp_servers)}\n")

    # Example 1: Simple calculation
    print("--- Query 1: Calculate returns ---")
    result1 = agent.run("What is 150000 * 0.08?")
    print(f"Result: {result1}\n")

    # Example 2: Get portfolio value
    print("--- Query 2: Check portfolio ---")
    result2 = agent.run("What is my current portfolio value?")
    print(f"Result: {result2}\n")

    # Example 3: Multi-step reasoning
    print("--- Query 3: Calculate percentage gain ---")
    result3 = agent.run(
        "If my portfolio was worth $140,000 last month and is now $150,000, "
        "what is the percentage gain?"
    )
    print(f"Result: {result3}\n")

    # Save agent state with custom data
    print("--- Saving agent state ---")
    agent.save_state({"last_query": "percentage_gain", "user": "demo_user"})
    print("State saved to database\n")

    # View conversation history
    print("--- Conversation History ---")
    agent.print_conversation_history(limit=10)

    print("\n=== Session Complete ===")
    print(f"Session data saved with ID: {agent.session_id}")
    print("You can resume this session later by creating a new agent with the same session_id\n")


def resume_session():
    """Example showing how to resume a previous session."""
    print("\n=== Resuming Previous Session ===\n")

    # Create agent with same session ID
    agent = SupervisorAgent(
        tools=[calculator, get_portfolio_value],
        agent_name="investment-advisor",
        session_id="demo-session-001",
        persist_state=True,
        persist_conversations=True,
    )

    print("Previous conversation history:")
    agent.print_conversation_history()

    # Continue the conversation
    print("\n--- New query in resumed session ---")
    result = agent.run("What was my last calculation about?")
    print(f"Result: {result}")


if __name__ == "__main__":
    # Run the main demo
    main()

    # Optionally uncomment to test session resumption
    # resume_session()
