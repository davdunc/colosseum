"""
Colosseum Multi-Agent Investment Committee Framework

A framework for managing multiple AI agents with MCP server integration,
designed for investment committee workflows with broker and data source connections.

Uses Podman Quadlets for deployment and PostgreSQL/SQLite for state management.
"""

__version__ = "0.1.0"

from colosseum.agent_supervisor import SupervisorAgent
from colosseum.agent_registry import AgentRegistry, add_agent_to_registry
from colosseum.config import get_config_path, load_config, save_config
from colosseum.database import (
    get_db_manager,
    save_agent_state,
    load_agent_state,
    save_conversation,
    load_conversation_history,
)

__all__ = [
    "SupervisorAgent",
    "AgentRegistry",
    "add_agent_to_registry",
    "get_config_path",
    "load_config",
    "save_config",
    "get_db_manager",
    "save_agent_state",
    "load_agent_state",
    "save_conversation",
    "load_conversation_history",
]
