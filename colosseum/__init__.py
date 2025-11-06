"""
Colosseum Multi-Agent Investment Committee Framework

A framework for managing multiple AI agents with MCP server integration,
designed for investment committee workflows with broker and data source connections.
"""

__version__ = "0.1.0"

from colosseum.agent_supervisor import SupervisorAgent
from colosseum.agent_registry import AgentRegistry, add_agent_to_registry
from colosseum.config import get_config_path, load_config, save_config

__all__ = [
    "SupervisorAgent",
    "AgentRegistry",
    "add_agent_to_registry",
    "get_config_path",
    "load_config",
    "save_config",
]
