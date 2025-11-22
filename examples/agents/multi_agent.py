"""
Multi-agent example showing agents communicating through shared database state.

This example demonstrates:
1. Multiple agents working on the same task
2. Agents sharing state via database
3. Agent handoffs and coordination
4. Persistent multi-agent workflows
"""

from langchain_core.tools import tool
from colosseum import SupervisorAgent, save_agent_state, load_agent_state

# Tools for research agent
@tool
def research_market(ticker: str) -> str:
    """Research a stock ticker. Returns mock market data."""
    mock_data = {
        "AAPL": "Apple Inc. - Current price: $180.50, P/E: 28.5, Market Cap: $2.8T",
        "GOOGL": "Alphabet Inc. - Current price: $140.25, P/E: 25.2, Market Cap: $1.7T",
        "MSFT": "Microsoft Corp. - Current price: $375.80, P/E: 32.1, Market Cap: $2.7T",
    }
    return mock_data.get(ticker.upper(), f"No data available for {ticker}")

# Tools for analysis agent
@tool
def calculate_metrics(price: float, pe_ratio: float) -> str:
    """Calculate investment metrics based on price and P/E ratio."""
    earnings = price / pe_ratio
    return f"EPS: ${earnings:.2f}, Estimated growth: 12%"

# Tools for decision agent
@tool
def make_recommendation(analysis: str) -> str:
    """Make investment recommendation based on analysis."""
    return f"Based on analysis: {analysis}\nRecommendation: BUY (Strong confidence)"


class MultiAgentWorkflow:
    """Coordinate multiple agents working together."""

    def __init__(self, session_id: str):
        self.session_id = session_id

        # Create specialized agents
        self.research_agent = SupervisorAgent(
            tools=[research_market],
            agent_name="researcher",
            session_id=session_id,
            model="gpt-4",
        )

        self.analysis_agent = SupervisorAgent(
            tools=[calculate_metrics],
            agent_name="analyst",
            session_id=session_id,
            model="gpt-4",
        )

        self.decision_agent = SupervisorAgent(
            tools=[make_recommendation],
            agent_name="decision-maker",
            session_id=session_id,
            model="gpt-4",
        )

    def run_investment_workflow(self, ticker: str):
        """Run a complete investment analysis workflow."""
        print(f"\n{'='*60}")
        print(f"Investment Analysis Workflow for {ticker}")
        print(f"Session ID: {self.session_id}")
        print(f"{'='*60}\n")

        # Step 1: Research Agent gathers data
        print("Step 1: Research Agent gathering market data...")
        research_query = f"Research the stock ticker {ticker} and provide market data"
        research_result = self.research_agent.run(research_query)
        print(f"Research complete: {research_result}\n")

        # Save research results to shared state
        save_agent_state(
            "workflow",
            self.session_id,
            {"ticker": ticker, "research_data": str(research_result)},
        )

        # Step 2: Analysis Agent processes the data
        print("Step 2: Analysis Agent calculating metrics...")
        # Load research data from shared state
        shared_state = load_agent_state("workflow", self.session_id)
        analysis_query = (
            f"Analyze this stock data and calculate metrics: {shared_state.get('research_data')}"
        )
        analysis_result = self.analysis_agent.run(analysis_query)
        print(f"Analysis complete: {analysis_result}\n")

        # Update shared state with analysis
        shared_state["analysis_data"] = str(analysis_result)
        save_agent_state("workflow", self.session_id, shared_state)

        # Step 3: Decision Agent makes recommendation
        print("Step 3: Decision Agent making recommendation...")
        shared_state = load_agent_state("workflow", self.session_id)
        decision_query = (
            f"Based on this analysis, make an investment recommendation: "
            f"{shared_state.get('analysis_data')}"
        )
        decision_result = self.decision_agent.run(decision_query)
        print(f"Decision complete: {decision_result}\n")

        # Save final recommendation
        shared_state["recommendation"] = str(decision_result)
        save_agent_state("workflow", self.session_id, shared_state)

        print(f"\n{'='*60}")
        print("Workflow Complete!")
        print(f"{'='*60}\n")

        return shared_state

    def print_workflow_summary(self):
        """Print a summary of the entire workflow from database."""
        print("\n=== Workflow Summary ===\n")

        # Get conversation history from all agents
        print("Research Agent Activity:")
        self.research_agent.print_conversation_history(limit=5)

        print("\nAnalysis Agent Activity:")
        self.analysis_agent.print_conversation_history(limit=5)

        print("\nDecision Agent Activity:")
        self.decision_agent.print_conversation_history(limit=5)

        # Get shared state
        shared_state = load_agent_state("workflow", self.session_id)
        if shared_state:
            print("\nShared Workflow State:")
            for key, value in shared_state.items():
                print(f"  {key}: {value}")


def main():
    print("=== Multi-Agent Investment Committee Example ===\n")

    # Create workflow with shared session
    workflow = MultiAgentWorkflow(session_id="investment-committee-001")

    # Run analysis for a stock
    final_state = workflow.run_investment_workflow("AAPL")

    # Print summary showing how agents communicated
    workflow.print_workflow_summary()

    print("\n=== Key Takeaways ===")
    print("1. Each agent has its own specialized tools")
    print("2. Agents communicate via shared database state")
    print("3. All conversations are persisted for audit trail")
    print("4. Workflow can be resumed or analyzed later")
    print(f"5. Session ID '{workflow.session_id}' can be used to access all data\n")


if __name__ == "__main__":
    main()
