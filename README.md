# Colosseum Multi-Agent Investment Committee Framework

## Overview

Colosseum is a multi-agent investment committee framework leveraging Langchain, Fedora Bootable Containers, and a KIND single-node Kubernetes cluster. It supports integration with MCP (Model Context Protocol) servers and clients for secure, programmatic access to data, tools, and AI agent management.

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

### 1. Deploy the Data Lake

```bash
cd quadlets
./deploy.sh
./init-schema.sh
```

### 2. Install Dependencies

```bash
pip install -r colosseum/requirements.txt
```

### 3. Configure MCP Servers

Create `~/.config/colosseum/mcp.json`:
```json
{
  "etrade": {
    "type": "etrade",
    "base_url": "http://localhost:8080",
    "api_key": "your_key"
  }
}
```

### 4. Configure Database Connection

Copy and edit the config:
```bash
mkdir -p ~/.config/colosseum
cp quadlets/config.yaml.example ~/.config/colosseum/config.yaml
export DB_PASSWORD=$(podman secret inspect colosseum-db-password --showsecret)
```

### 5. Start the Curator

```bash
# Start the curator worker
python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL MSFT

# Or use programmatically
python examples/curator_example.py
```

## CLI Tools

### Curator CLI

```bash
# Fetch a quote
python -m colosseum.cli.curator fetch AAPL

# Start background worker
python -m colosseum.cli.curator start --interval 60

# Manage watchlist
python -m colosseum.cli.curator watch AAPL GOOGL MSFT
python -m colosseum.cli.curator unwatch GOOGL

# Fetch news
python -m colosseum.cli.curator news --ticker AAPL --limit 5

# Backfill historical data
python -m colosseum.cli.curator backfill AAPL --period 1M

# Show statistics
python -m colosseum.cli.curator stats

# Health check
python -m colosseum.cli.curator health
```

## Project Structure

```
colosseum/
├── colosseum/
│   ├── agents/
│   │   └── curator_agent.py        # CuratorAgent implementation
│   ├── cli/
│   │   └── curator.py              # Curator CLI tool
│   ├── database/
│   │   ├── client.py               # DataLakeClient (SQLAlchemy)
│   │   └── __init__.py
│   ├── mcp/
│   │   ├── base.py                 # MCP server base classes
│   │   ├── ib.py                   # Interactive Brokers
│   │   ├── etrade.py               # E*TRADE
│   │   ├── dastrader.py            # DAS Trader
│   │   ├── fetch.py                # Generic fetch server
│   │   └── loader.py               # MCP server loader
│   ├── agent_supervisor.py         # SupervisorAgent
│   ├── agent_registry.py           # Agent registry
│   ├── config.py                   # Configuration management
│   └── requirements.txt
├── quadlets/
│   ├── colosseum-network.network   # Podman network
│   ├── colosseum-postgres.container # PostgreSQL container
│   ├── colosseum-postgres-data.volume # Data volume
│   ├── deploy.sh                   # Deployment script
│   ├── cleanup.sh                  # Cleanup script
│   ├── init-schema.sh              # Schema initialization
│   ├── init-db.sql                 # Database schema
│   ├── config.yaml.example         # Configuration template
│   └── README.md                   # Deployment guide
├── deployment/
│   ├── systemd/                    # Systemd service files
│   ├── kubernetes/                 # Kubernetes manifests
│   ├── docker/                     # Container images
│   └── README.md                   # Deployment overview
├── examples/
│   └── curator_example.py          # Example usage
├── docs/
│   ├── CURATOR_AGENT.md            # Curator documentation
│   └── DEPLOYMENT.md               # Deployment guide
└── README.md
```

## Deployment

Colosseum supports multiple deployment strategies:

- **Local Development**: Direct Python execution for testing
- **Systemd/Quadlet**: Production deployment on Fedora/RHEL ⭐ **Recommended**
- **Kubernetes**: Containerized deployment for multi-node clusters
- **Fedora Bootable Container**: Immutable infrastructure for edge

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for comprehensive deployment guide.

### Quick Deploy (Systemd)

```bash
# Install as system service
cd deployment/systemd
sudo ./install.sh

# Enable and start
sudo systemctl enable --now colosseum-curator.service
```

### Quick Deploy (Kubernetes)

```bash
# Build and deploy
cd deployment/docker && ./build.sh
cd ../kubernetes && ./deploy.sh
```

## Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Comprehensive deployment strategies
- **[CuratorAgent Documentation](docs/CURATOR_AGENT.md)** - Data lake agent details
- **[Quadlets Guide](quadlets/README.md)** - PostgreSQL deployment

## References

- [Model Context Protocol (MCP) Client Quickstart](https://modelcontextprotocol.io/quickstart/client)
- [Langchain Documentation](https://python.langchain.com/)
- [Major Hayden's Quadlet Networking Blog](https://major.io/p/quadlet-networking/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
