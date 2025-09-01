import json
import os
from .base import mcp_server_factory

def load_mcp_servers(config_path=None):
    """
    Loads MCP server definitions from mcp.json and returns a dict of instantiated MCP servers.
    """
    if config_path is None:
        # Default XDG or /etc location
        config_path = os.environ.get(
            "MCP_CONFIG_PATH",
            os.path.expanduser("~/.config/colosseum/mcp.json")
        )
    if not os.path.exists(config_path):
        return {}

    with open(config_path, "r") as f:
        configs = json.load(f)

    servers = {}
    for name, conf in configs.items():
        servers[name] = mcp_server_factory(conf)
    return servers
