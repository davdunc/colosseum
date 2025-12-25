# Colosseum Multi-Agent Investment Committee Framework

## Overview

Colosseum is a multi-agent investment committee framework leveraging Langchain, Podman Quadlets, and PostgreSQL for state management. It supports integration with MCP (Model Context Protocol) servers and clients for secure, programmatic access to data, tools, and AI agent management.

Colosseum uses Podman Quadlets for container orchestration via systemd, providing better localhost networking, simpler deployment, and native Fedora integration compared to Kubernetes.

The framework includes a **PostgreSQL data lake** managed by the **CuratorAgent** (the keeper of records) for persistent storage and efficient access to market data, news, and agent decisions.

## ⚡ Quick Start

Get up and running in 10 minutes:

```bash
# 1. Clone repo
git clone https://github.com/davdunc/colosseum.git
cd colosseum

# 2. Install dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r colosseum/requirements.txt

# 3. Deploy PostgreSQL data lake
cd quadlets
./build-postgres-image.sh  # 5-10 min, first time only
./deploy-enhanced.sh

# 4. Initialize database
./init-schema.sh

# 5. Configure
mkdir -p ~/.config/colosseum
cp config.yaml.example ~/.config/colosseum/config.yaml
export DB_PASSWORD=$(podman secret inspect colosseum-db-password --showsecret)

# 6. Run curator
python -m colosseum.cli.curator health
python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL MSFT
```

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed instructions**

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

## Architecture

```
┌──────────────────────────────────────────────────┐
│         SupervisorAgent (Orchestrator)           │
└────────┬─────────────────────────────────────────┘
         │
    ┌────┴────────┬──────────────┬────────────┐
    │             │              │            │
┌───▼────┐  ┌────▼─────┐  ┌─────▼────┐  ┌───▼──────┐
│Research│  │Portfolio │  │ Trading  │  │ Curator  │
│ Agent  │  │  Agent   │  │  Agent   │  │ Agent ⭐ │
└────────┘  └──────────┘  └──────────┘  └────┬─────┘
                                              │
                        ┌─────────────────────┴──────┐
                        │                            │
                  ┌─────▼──────┐            ┌────────▼────────┐
                  │MCP Servers │            │   PostgreSQL    │
                  │(IB, ETrade)│            │   Data Lake     │
                  └────────────┘            └─────────────────┘
```

## Agents

### CuratorAgent - The Keeper of Records

The **CuratorAgent** manages the data lake, collecting and organizing market data:

- **Data Ingestion**: Pulls quotes, news, and historical data from MCP servers
- **Persistence**: Stores all data in PostgreSQL with TimescaleDB and pgvector
- **Caching**: Maintains hot data in memory for fast access
- **Background Worker**: Continuously collects data for watchlist tickers
- **Query Interface**: Provides efficient data access for other agents

See [docs/CURATOR_AGENT.md](docs/CURATOR_AGENT.md) for detailed documentation.

## Data Lake

The PostgreSQL data lake provides:

- **TimescaleDB**: Efficient time-series storage for tick data
- **pgvector**: Semantic search for news articles
- **Three Schemas**: market_data, agent_data, metadata
- **Quadlet Deployment**: Systemd-native container management
- **Automatic Retention**: 90-day policy for raw tick data

See [quadlets/README.md](quadlets/README.md) for deployment guide.

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
