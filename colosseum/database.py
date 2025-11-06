"""
Database configuration and state management for Colosseum agents.

Uses SQLAlchemy for ORM and supports PostgreSQL for production,
SQLite for development/testing.
"""

import os
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

Base = declarative_base()


class AgentState(Base):
    """Store agent state and conversation history."""

    __tablename__ = "agent_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    state_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MCPServerState(Base):
    """Store MCP server connection state and cache."""

    __tablename__ = "mcp_server_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_name = Column(String(255), nullable=False, unique=True, index=True)
    server_type = Column(String(100), nullable=False)
    state_data = Column(JSON, nullable=False, default=dict)
    last_connected = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ConversationHistory(Base):
    """Store conversation history for multi-agent interactions."""

    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL. If None, uses DATABASE_URL env var
                         or defaults to SQLite in ~/.local/share/colosseum/state.db
        """
        if database_url is None:
            database_url = os.getenv("DATABASE_URL")

        if database_url is None:
            # Default to SQLite for development
            state_dir = os.path.expanduser("~/.local/share/colosseum")
            os.makedirs(state_dir, exist_ok=True)
            database_url = f"sqlite:///{state_dir}/state.db"

        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        """Initialize database tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def close(self):
        """Close database connections."""
        self.engine.dispose()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.init_db()
    return _db_manager


def save_agent_state(agent_name: str, session_id: str, state_data: dict):
    """
    Save agent state to database.

    Args:
        agent_name: Name of the agent
        session_id: Session identifier
        state_data: State data as dictionary
    """
    db = get_db_manager()
    session = db.get_session()
    try:
        state = AgentState(
            agent_name=agent_name, session_id=session_id, state_data=state_data
        )
        session.add(state)
        session.commit()
    finally:
        session.close()


def load_agent_state(agent_name: str, session_id: str) -> Optional[dict]:
    """
    Load agent state from database.

    Args:
        agent_name: Name of the agent
        session_id: Session identifier

    Returns:
        State data dictionary or None if not found
    """
    db = get_db_manager()
    session = db.get_session()
    try:
        state = (
            session.query(AgentState)
            .filter_by(agent_name=agent_name, session_id=session_id)
            .order_by(AgentState.created_at.desc())
            .first()
        )
        return state.state_data if state else None
    finally:
        session.close()


def save_conversation(session_id: str, agent_name: str, role: str, content: str, metadata: Optional[dict] = None):
    """
    Save conversation message to database.

    Args:
        session_id: Session identifier
        agent_name: Name of the agent
        role: Message role (user, assistant, system)
        content: Message content
        metadata: Optional metadata dictionary
    """
    db = get_db_manager()
    session = db.get_session()
    try:
        message = ConversationHistory(
            session_id=session_id,
            agent_name=agent_name,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        session.add(message)
        session.commit()
    finally:
        session.close()


def load_conversation_history(session_id: str, limit: Optional[int] = None) -> list:
    """
    Load conversation history from database.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return (most recent first)

    Returns:
        List of conversation messages
    """
    db = get_db_manager()
    session = db.get_session()
    try:
        query = (
            session.query(ConversationHistory)
            .filter_by(session_id=session_id)
            .order_by(ConversationHistory.created_at.desc())
        )
        if limit:
            query = query.limit(limit)
        messages = query.all()
        return [
            {
                "agent_name": msg.agent_name,
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.metadata,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in reversed(messages)
        ]
    finally:
        session.close()
