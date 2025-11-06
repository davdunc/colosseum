# Colosseum Multi-Agent Investment Committee Framework

## Overview

Colosseum is a multi-agent investment committee framework leveraging Langchain, Podman Quadlets, and PostgreSQL for state management. It supports integration with MCP (Model Context Protocol) servers and clients for secure, programmatic access to data, tools, and AI agent management.

Colosseum uses Podman Quadlets for container orchestration via systemd, providing better localhost networking, simpler deployment, and native Fedora integration compared to Kubernetes.

## MCP Client/Server Integration

- **MCP servers** are defined in a configuration file (e.g., `mcp.json`) and instantiated at runtime.
- The official [MCP client](https://modelcontextprotocol.io/quickstart/client) is used to connect to these servers.
- MCP servers provide access to news, tickers, brokers, and custom data sources.
- All agents can access the shared MCP client(s) for efficient compute and parallelism.

## Plugin Architecture

- Plugins can be placed in the `colosseum/plugins/` directory.
- Each plugin can register tools or integrations with the supervisor agent.
- Example: A plugin that fetches and converts a website to markdown for agent consumption.

## Agent Access

- The `SupervisorAgent` class loads MCP servers and plugins, making them available to all agents.
- Agents can directly use the MCP client(s) for secure, efficient access to resources.

## For GitHub Copilot and Amazon Q Users

- The codebase is modular and extensible, following best practices for dependency management and plugin loading.
- MCP client usage follows the official specification and is available to all agents.
- Configuration files are loaded according to XDG and service conventions for compatibility.

## Quickstart

### Installation

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Configure MCP servers:
   ```bash
   mkdir -p ~/.config/colosseum
   cp examples/mcp.json ~/.config/colosseum/mcp.json
   cp examples/config.yaml ~/.config/colosseum/config.yaml
   # Edit configuration files with your credentials
   ```

3. Deploy with Quadlets (optional, for production):
   ```bash
   python -m colosseum.quadlet_deploy deploy
   ```

### Architecture

```
┌─────────────────────────────────────────┐
│  Colosseum Multi-Agent Framework        │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  PostgreSQL  │  │  Agent Services │ │
│  │   Database   │←─┤  - Supervisor   │ │
│  │  (State)     │  │  - Plugins      │ │
│  └──────────────┘  │  - MCP Clients  │ │
│                    └─────────────────┘ │
│                                         │
│  Podman Quadlets + systemd              │
└─────────────────────────────────────────┘
         ↓
    localhost:5432 (Database)
    localhost:8000 (API)
```

### Development Mode

For development without Quadlets:
```python
from colosseum import SupervisorAgent, load_config

# Load configuration
config = load_config()

# Create supervisor agent
agent = SupervisorAgent()

# Database will use SQLite by default in ~/.local/share/colosseum/state.db
```

## Deployment

See [quadlets/README.md](quadlets/README.md) for detailed deployment instructions using Podman Quadlets.

### Why Quadlets instead of KIND?

- **Better localhost access**: No networking issues accessing host services
- **Simpler setup**: No Kubernetes complexity
- **Native systemd**: Better integration with Fedora
- **Easier debugging**: Direct podman commands work
- **Persistent state**: Built-in volume management
- **Service discovery**: DNS works out of the box

## Database State Management

Colosseum uses PostgreSQL (production) or SQLite (development) for:
- Agent state persistence
- Conversation history
- MCP server cache
- Multi-agent coordination

See [colosseum/database.py](colosseum/database.py) for the state management API.

## References

- [Model Context Protocol (MCP) Client Quickstart](https://modelcontextprotocol.io/quickstart/client)
- [Langchain Documentation](https://python.langchain.com/)
- [Podman Quadlet Documentation](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
