"""
Command-line interface for Colosseum multi-agent framework.

Provides commands to:
- Initialize database
- Start interactive agent sessions
- View conversation history
- Manage agent state
- Inspect database contents
"""

import sys
import argparse
from typing import Optional
from colosseum.database import (
    get_db_manager,
    AgentState,
    ConversationHistory,
    MCPServerState,
)


def init_db(args):
    """Initialize the database schema."""
    print("Initializing Colosseum database...")
    db_manager = get_db_manager()
    db_manager.init_db()
    print(f"✓ Database initialized successfully")
    print(f"  Database URL: {db_manager.database_url}")


def list_sessions(args):
    """List all agent sessions in the database."""
    db_manager = get_db_manager()
    session = db_manager.get_session()

    try:
        # Get all unique sessions
        sessions = (
            session.query(AgentState.session_id, AgentState.agent_name)
            .distinct()
            .all()
        )

        if not sessions:
            print("No sessions found in database.")
            return

        print(f"\nFound {len(sessions)} session(s):\n")
        print(f"{'Session ID':<40} {'Agent Name':<20}")
        print("-" * 60)

        for session_id, agent_name in sessions:
            print(f"{session_id:<40} {agent_name:<20}")

    finally:
        session.close()


def show_conversation(args):
    """Show conversation history for a session."""
    db_manager = get_db_manager()
    db_session = db_manager.get_session()

    try:
        query = db_session.query(ConversationHistory).filter_by(
            session_id=args.session_id
        )

        if args.agent_name:
            query = query.filter_by(agent_name=args.agent_name)

        messages = query.order_by(ConversationHistory.created_at).all()

        if not messages:
            print(f"No conversation found for session: {args.session_id}")
            return

        print(f"\n=== Conversation History ===")
        print(f"Session ID: {args.session_id}")
        if args.agent_name:
            print(f"Agent: {args.agent_name}")
        print(f"Messages: {len(messages)}\n")

        for msg in messages:
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            role = msg.role.upper()
            agent = msg.agent_name
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content

            print(f"[{timestamp}] {agent} ({role}):")
            print(f"  {content}\n")

    finally:
        db_session.close()


def show_state(args):
    """Show agent state for a session."""
    db_manager = get_db_manager()
    db_session = db_manager.get_session()

    try:
        query = db_session.query(AgentState).filter_by(session_id=args.session_id)

        if args.agent_name:
            query = query.filter_by(agent_name=args.agent_name)

        states = query.order_by(AgentState.updated_at.desc()).all()

        if not states:
            print(f"No state found for session: {args.session_id}")
            return

        print(f"\n=== Agent State ===")
        print(f"Session ID: {args.session_id}\n")

        for state in states:
            print(f"Agent: {state.agent_name}")
            print(f"Updated: {state.updated_at}")
            print(f"State Data:")
            for key, value in state.state_data.items():
                print(f"  {key}: {value}")
            print()

    finally:
        db_session.close()


def clear_session(args):
    """Clear all data for a session."""
    if not args.confirm:
        print(
            f"This will delete all data for session: {args.session_id}"
        )
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return

    db_manager = get_db_manager()
    db_session = db_manager.get_session()

    try:
        # Delete conversation history
        conv_deleted = (
            db_session.query(ConversationHistory)
            .filter_by(session_id=args.session_id)
            .delete()
        )

        # Delete agent states
        state_deleted = (
            db_session.query(AgentState)
            .filter_by(session_id=args.session_id)
            .delete()
        )

        db_session.commit()

        print(f"✓ Deleted {conv_deleted} conversation messages")
        print(f"✓ Deleted {state_deleted} agent states")

    finally:
        db_session.close()


def stats(args):
    """Show database statistics."""
    db_manager = get_db_manager()
    db_session = db_manager.get_session()

    try:
        num_sessions = db_session.query(AgentState.session_id).distinct().count()
        num_messages = db_session.query(ConversationHistory).count()
        num_states = db_session.query(AgentState).count()
        num_mcp = db_session.query(MCPServerState).count()

        print("\n=== Colosseum Database Statistics ===\n")
        print(f"Database URL: {db_manager.database_url}")
        print(f"\nCounts:")
        print(f"  Sessions:      {num_sessions}")
        print(f"  Messages:      {num_messages}")
        print(f"  Agent States:  {num_states}")
        print(f"  MCP Servers:   {num_mcp}")

        # Recent activity
        recent = (
            db_session.query(ConversationHistory)
            .order_by(ConversationHistory.created_at.desc())
            .limit(5)
            .all()
        )

        if recent:
            print(f"\nRecent Activity:")
            for msg in recent:
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  [{timestamp}] {msg.agent_name}: {msg.role}")

    finally:
        db_session.close()


def interactive(args):
    """Start an interactive agent session."""
    from langchain_core.tools import tool
    from colosseum import SupervisorAgent

    # Define a simple calculator tool
    @tool
    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression."""
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

    print("=== Colosseum Interactive Agent ===\n")

    agent = SupervisorAgent(
        tools=[calculator],
        agent_name=args.agent_name or "interactive-agent",
        session_id=args.session_id,
        model=args.model,
    )

    print(f"Agent: {agent.agent_name}")
    print(f"Session: {agent.session_id}")
    print(f"Model: {args.model}")
    print("\nType 'exit' to quit, 'history' to view conversation\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "exit":
                print("Goodbye!")
                break

            if user_input.lower() == "history":
                agent.print_conversation_history()
                continue

            result = agent.run(user_input)
            print(f"Agent: {result}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Colosseum Multi-Agent Framework CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init-db command
    parser_init = subparsers.add_parser("init-db", help="Initialize database")
    parser_init.set_defaults(func=init_db)

    # list-sessions command
    parser_list = subparsers.add_parser("list-sessions", help="List all sessions")
    parser_list.set_defaults(func=list_sessions)

    # show-conversation command
    parser_conv = subparsers.add_parser(
        "show-conversation", help="Show conversation history"
    )
    parser_conv.add_argument("session_id", help="Session ID")
    parser_conv.add_argument("--agent-name", help="Filter by agent name")
    parser_conv.set_defaults(func=show_conversation)

    # show-state command
    parser_state = subparsers.add_parser("show-state", help="Show agent state")
    parser_state.add_argument("session_id", help="Session ID")
    parser_state.add_argument("--agent-name", help="Filter by agent name")
    parser_state.set_defaults(func=show_state)

    # clear-session command
    parser_clear = subparsers.add_parser("clear-session", help="Clear session data")
    parser_clear.add_argument("session_id", help="Session ID")
    parser_clear.add_argument("--confirm", action="store_true", help="Skip confirmation")
    parser_clear.set_defaults(func=clear_session)

    # stats command
    parser_stats = subparsers.add_parser("stats", help="Show database statistics")
    parser_stats.set_defaults(func=stats)

    # interactive command
    parser_interactive = subparsers.add_parser(
        "interactive", help="Start interactive session"
    )
    parser_interactive.add_argument(
        "--agent-name", help="Agent name", default="interactive-agent"
    )
    parser_interactive.add_argument("--session-id", help="Session ID (auto-generated if not provided)")
    parser_interactive.add_argument("--model", default="gpt-4", help="Model to use")
    parser_interactive.set_defaults(func=interactive)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
