# Colosseum Quick Start Guide

Get Colosseum running in 10 minutes.

## Prerequisites

Before you begin, ensure you have:

- **Fedora 39+** or **RHEL 9+** (recommended) or Ubuntu/Debian
- **Podman 4.6+** (or Docker)
- **Python 3.11+**
- **Git**

### Check Prerequisites

```bash
# Check versions
podman --version  # Should be 4.6+
python3 --version  # Should be 3.11+
git --version
```

## Step 1: Clone the Repository

```bash
git clone https://github.com/davdunc/colosseum.git
cd colosseum
```

## Step 2: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r colosseum/requirements.txt
```

**Note**: S3 dependencies (boto3, pyarrow, pandas) are included. If you don't need S3 support, you can skip them.

## Step 3: Deploy PostgreSQL Data Lake

This is the most important step - it sets up your database with TimescaleDB and pgvector.

```bash
cd quadlets

# Build custom PostgreSQL image (first time only, takes 5-10 minutes)
./build-postgres-image.sh

# Deploy PostgreSQL with quadlets
./deploy-enhanced.sh
```

**What this does**:
- Creates a podman secret for the database password
- Deploys PostgreSQL 16 with TimescaleDB and pgvector
- Starts it as a systemd service
- Waits for it to be ready

**Save your password!** The script will generate and display a password. Save it!

## Step 4: Initialize Database Schema

```bash
# Still in quadlets/ directory
./init-schema.sh
```

This creates:
- ✅ Three schemas (market_data, agent_data, metadata)
- ✅ TimescaleDB hypertables for time-series data
- ✅ pgvector indexes for semantic search
- ✅ Helper functions and retention policies

## Step 5: Configure Colosseum

```bash
# Create config directory
mkdir -p ~/.config/colosseum

# Copy example config
cp config.yaml.example ~/.config/colosseum/config.yaml

# Set database password environment variable
export DB_PASSWORD=$(podman secret inspect colosseum-db-password --showsecret)
```

**Optional**: Edit `~/.config/colosseum/config.yaml` to customize settings.

## Step 6: Verify Installation

```bash
# Check PostgreSQL service
systemctl --user status colosseum-postgres.service

# Test database connection
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "SELECT 1;"

# Check curator health
python -m colosseum.cli.curator health
```

You should see:
```
✅ Database:        OK
🔌 MCP Sources:      0 configured
✅ Curator is healthy
```

## Step 7: Run the Curator

Now you're ready to run the curator!

### Option A: Interactive Test

```bash
# Fetch a quote (will fail gracefully if no MCP servers configured)
python -m colosseum.cli.curator fetch AAPL

# Show statistics
python -m colosseum.cli.curator stats
```

### Option B: Start Background Worker

```bash
# Start curator with a watchlist
python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL MSFT
```

This will:
- ✅ Monitor AAPL, GOOGL, MSFT
- ✅ Fetch quotes every 60 seconds
- ✅ Persist to PostgreSQL
- ✅ Cache recent data

Press `Ctrl+C` to stop.

### Option C: Run Examples

```bash
# Run comprehensive examples
cd ..  # Back to repo root
python examples/curator_example.py
```

## What You Have Now

✅ **PostgreSQL Data Lake** running as systemd service
✅ **TimescaleDB** for time-series data
✅ **pgvector** for semantic search
✅ **CuratorAgent** ready to collect data
✅ **Database schemas** initialized
✅ **CLI tools** ready to use

## Next Steps

### 1. Configure MCP Servers (Optional)

To connect to real data sources (Interactive Brokers, E*TRADE, etc.):

```bash
cat > ~/.config/colosseum/mcp.json <<'EOF'
{
  "etrade": {
    "type": "etrade",
    "base_url": "http://localhost:8080",
    "api_key": "your_api_key_here"
  }
}
EOF
```

See `colosseum/mcp/` for available integrations.

### 2. Configure S3 for Bulk Imports (Optional)

To import historical data from S3:

```bash
# Use the S3 configuration example
cp quadlets/config-s3.yaml.example ~/.config/colosseum/config.yaml

# Edit with your S3 credentials
vim ~/.config/colosseum/config.yaml
```

Then import data:
```bash
python -m colosseum.cli.curator s3-list prod-datalake
python -m colosseum.cli.curator s3-import prod-datalake --prefix market_data/
```

See [docs/S3_PARQUET_INTEGRATION.md](docs/S3_PARQUET_INTEGRATION.md)

### 3. Deploy as Systemd Service (Production)

For production deployment:

```bash
cd deployment/systemd
sudo ./install.sh
sudo systemctl enable --now colosseum-curator.service
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

### 4. Explore the Database

```bash
# Connect to PostgreSQL
podman exec -it colosseum-postgres psql -U colosseum -d colosseum_data_lake

# View schemas
\dn

# View tables
\dt market_data.*

# Query data
SELECT * FROM market_data.stock_quotes LIMIT 10;
```

## Useful Commands

### Managing PostgreSQL

```bash
# Status
systemctl --user status colosseum-postgres.service

# Logs
journalctl --user -u colosseum-postgres.service -f

# Stop
systemctl --user stop colosseum-postgres.service

# Start
systemctl --user start colosseum-postgres.service

# Restart
systemctl --user restart colosseum-postgres.service
```

### Curator Commands

```bash
# Health check
python -m colosseum.cli.curator health

# Show stats
python -m colosseum.cli.curator stats

# Fetch quote
python -m colosseum.cli.curator fetch AAPL

# Manage watchlist
python -m colosseum.cli.curator watch AAPL GOOGL MSFT
python -m colosseum.cli.curator unwatch GOOGL

# Fetch news
python -m colosseum.cli.curator news --ticker AAPL --limit 5

# Backfill historical data
python -m colosseum.cli.curator backfill AAPL --period 1M

# Start worker
python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL
```

### Database Operations

```bash
# Backup
podman exec colosseum-postgres pg_dump -U colosseum colosseum_data_lake > backup.sql

# Restore
podman exec -i colosseum-postgres psql -U colosseum -d colosseum_data_lake < backup.sql

# Check size
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT pg_size_pretty(pg_database_size('colosseum_data_lake'));"
```

## Troubleshooting

### PostgreSQL won't start

```bash
# Check logs
journalctl --user -u colosseum-postgres.service -n 50

# Check container
podman ps -a | grep colosseum-postgres

# Rebuild and redeploy
cd quadlets
./cleanup.sh
./build-postgres-image.sh
./deploy-enhanced.sh
```

### Python dependencies fail

```bash
# Make sure you're in venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies one by one
pip install sqlalchemy psycopg2-binary pyyaml
pip install boto3 pyarrow pandas  # For S3 support
```

### Curator can't connect to database

```bash
# Check if PostgreSQL is running
podman ps | grep colosseum-postgres

# Test connection
podman exec colosseum-postgres pg_isready -U colosseum

# Check password
echo $DB_PASSWORD

# Re-export password
export DB_PASSWORD=$(podman secret inspect colosseum-db-password --showsecret)
```

### Permission errors

```bash
# Make sure scripts are executable
chmod +x quadlets/*.sh

# Check SELinux (Fedora/RHEL)
sudo ausearch -m avc -ts recent

# If needed, relabel
podman volume rm colosseum-postgres-data
cd quadlets && ./deploy-enhanced.sh
```

## Getting Help

- **Documentation**: See `docs/` directory
  - [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide
  - [CURATOR_AGENT.md](docs/CURATOR_AGENT.md) - Curator details
  - [S3_PARQUET_INTEGRATION.md](docs/S3_PARQUET_INTEGRATION.md) - S3 integration
- **Examples**: See `examples/` directory
- **Issues**: https://github.com/davdunc/colosseum/issues

## Summary

You've successfully installed Colosseum! 🏛️

**What's running**:
- PostgreSQL 16 + TimescaleDB + pgvector (systemd service)
- CuratorAgent (on-demand or as background worker)

**What you can do**:
- ✅ Collect market data
- ✅ Store in PostgreSQL data lake
- ✅ Query with TimescaleDB for time-series
- ✅ Semantic search with pgvector
- ✅ Import bulk data from S3
- ✅ Build multi-agent investment strategies

**Next**: Configure MCP servers or import historical data from S3!
