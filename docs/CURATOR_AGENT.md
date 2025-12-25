# CuratorAgent - The Keeper of Colosseum Records

## Overview

The **CuratorAgent** is the guardian of the Colosseum data lake. Like a Roman curator who managed public archives and records, this agent is responsible for collecting, organizing, and maintaining market data from various sources.

## Role in the Colosseum

```
┌─────────────────────────────────────────────────────┐
│          SupervisorAgent (Orchestrator)             │
└──────┬──────────────────────────────────────────────┘
       │
   ┌───┴─────────────┬──────────────┬─────────────┐
   │                 │              │             │
┌──▼──────┐   ┌─────▼──────┐  ┌───▼────┐  ┌─────▼─────┐
│Research │   │ Portfolio  │  │Trading │  │ Curator   │
│ Agent   │   │   Agent    │  │ Agent  │  │ Agent ⭐  │
└────┬────┘   └─────┬──────┘  └───┬────┘  └─────┬─────┘
     │              │              │             │
     │              │              │             │
     └──────────────┴──────────────┴─────────────┘
                                                  │
                    ┌─────────────────────────────┴────────┐
                    │                                      │
            ┌───────▼────────┐                    ┌───────▼────────┐
            │  MCP Servers   │                    │  PostgreSQL    │
            │  (Data Sources)│                    │  Data Lake     │
            └────────────────┘                    └────────────────┘
```

## Core Responsibilities

1. **Data Ingestion**: Pull real-time quotes, news, and historical data from MCP servers
2. **Persistence**: Store all data in the PostgreSQL data lake
3. **Caching**: Maintain hot data in memory for fast access
4. **Data Quality**: Monitor source health and data freshness
5. **Query Interface**: Provide efficient data access for other agents
6. **Background Worker**: Continuously collect data for watchlist tickers

## Architecture

### Components

```python
CuratorAgent
├── Database Client (PostgreSQL via SQLAlchemy)
├── MCP Server Clients (IB, E*TRADE, DAS Trader)
├── Cache Layer (in-memory with TTL)
├── Background Worker (threaded)
├── Watchlist Manager
└── Health Monitor
```

### Data Flow

```
MCP Servers → CuratorAgent → [Cache] → PostgreSQL
                    ↓
              Other Agents
```

## Usage

### Basic Initialization

```python
from colosseum.agents.curator_agent import CuratorAgent

# Initialize with default config
curator = CuratorAgent()

# Or with custom config
from colosseum.config import load_config
config = load_config()
curator = CuratorAgent(config=config)
```

### Fetching Real-Time Quotes

```python
# Fetch a single quote
quote = curator.fetch_quote('AAPL')
print(f"AAPL: ${quote['price']:.2f}")

# Fetch multiple quotes
quotes = curator.fetch_quotes_batch(['AAPL', 'GOOGL', 'MSFT'])
for ticker, quote in quotes.items():
    print(f"{ticker}: ${quote['price']:.2f}")
```

### Collecting News

```python
# Fetch general market news
news = curator.fetch_news(limit=10)

# Fetch ticker-specific news
tesla_news = curator.fetch_news(ticker='TSLA', limit=5)

for article in news:
    print(f"{article['headline']} - {article['source']}")
```

### Historical Data Backfill

```python
# Fetch 1 month of daily bars
bars = curator.fetch_historical_data(
    'AAPL',
    period='1M',
    interval='1day'
)

# Fetch 1 week of 5-minute bars
bars = curator.fetch_historical_data(
    'TSLA',
    period='1W',
    interval='5min'
)
```

### Watchlist Management

```python
# Add tickers to watchlist
curator.add_to_watchlist('AAPL')
curator.add_to_watchlist('GOOGL')
curator.add_to_watchlist('MSFT')

# Remove from watchlist
curator.remove_from_watchlist('GOOGL')

# View current watchlist
print(curator.watchlist)  # ['AAPL', 'MSFT']
```

### Background Worker

```python
# Start worker to continuously fetch data
curator.start_worker(interval=60)  # Fetch every 60 seconds

# Worker will automatically:
# - Fetch quotes for all watchlist tickers
# - Collect recent news
# - Update source health metrics
# - Cache data for fast access

# Stop worker
curator.stop_worker()
```

### Querying from Data Lake

```python
# Get latest quote (cache-first, then DB, then fetch)
quote = curator.get_quote('AAPL')

# Get OHLCV data from data lake
bars = curator.get_ohlcv('AAPL', interval='1min', limit=100)

# Search news in data lake
news = curator.search_news(ticker='AAPL', limit=10)
```

## CLI Tool

The Curator comes with a command-line interface:

```bash
# Start the curator worker
python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL MSFT

# Fetch a single quote
python -m colosseum.cli.curator fetch AAPL

# Add tickers to watchlist
python -m colosseum.cli.curator watch TSLA NVDA AMD

# Fetch recent news
python -m colosseum.cli.curator news --ticker AAPL --limit 5

# Backfill historical data
python -m colosseum.cli.curator backfill AAPL --period 1M --interval 1day

# Show statistics
python -m colosseum.cli.curator stats

# Health check
python -m colosseum.cli.curator health
```

## Integration with Other Agents

### Via Agent Registry

```python
from colosseum.agent_registry import add_agent_to_registry

# Register the curator
curator = CuratorAgent()
registry = add_agent_to_registry('curator', curator)

# Other agents can access it
class ResearchAgent:
    def __init__(self, registry):
        self.curator = registry.get_agent('curator')

    def analyze_stock(self, ticker):
        # Get data from curator
        quote = self.curator.get_quote(ticker)
        news = self.curator.search_news(ticker=ticker)
        ohlcv = self.curator.get_ohlcv(ticker, interval='1day', limit=30)

        # Perform analysis...
```

### Direct Integration

```python
class PortfolioAgent:
    def __init__(self, curator: CuratorAgent):
        self.curator = curator

    def get_portfolio_value(self, positions):
        total_value = 0
        for ticker, shares in positions.items():
            quote = self.curator.get_quote(ticker)
            if quote:
                total_value += quote['price'] * shares
        return total_value
```

## Configuration

Configuration is loaded from `~/.config/colosseum/config.yaml`:

```yaml
agents:
  curator:
    enabled: true
    # Fetch interval for market data (seconds)
    fetch_interval: 60
    # Cache TTL (seconds)
    cache_ttl: 300
    # Batch size for inserts
    batch_size: 1000

database:
  host: localhost
  port: 5432
  database: colosseum_data_lake
  user: colosseum
  password: ${DB_PASSWORD}
```

## Caching

The Curator maintains an in-memory cache for recent quotes:

- **Cache-First Strategy**: Always checks cache before fetching
- **TTL-Based Expiry**: Configurable time-to-live (default: 300s)
- **Automatic Refresh**: Background worker keeps cache hot
- **Cache Statistics**: Track hits and misses

```python
# Clear cache manually
curator.clear_cache()

# Check if cached
is_cached = curator._is_cached('AAPL')

# Configure cache TTL
curator.cache_ttl = 600  # 10 minutes
```

## Monitoring

### Health Checks

```python
# Check overall health
healthy = curator.health_check()

# Checks:
# - Database connectivity
# - MCP server availability
# - Worker thread status
```

### Statistics

```python
stats = curator.get_stats()

# Returns:
# {
#     'session_id': 'uuid',
#     'watchlist_size': 5,
#     'cache_size': 3,
#     'worker_running': True,
#     'mcp_sources': 3,
#     'quotes_fetched': 142,
#     'quotes_persisted': 140,
#     'news_fetched': 23,
#     'historical_bars_fetched': 30,
#     'cache_hits': 89,
#     'fetch_failures': 2,
#     'persist_failures': 0
# }
```

## Data Sources

The Curator pulls data from configured MCP servers:

### Broker Data Sources (Quotes & Historical)
- **Interactive Brokers** (`ib`)
- **E*TRADE** (`etrade`)
- **DAS Trader** (`dastrader`)

### News Sources
- **E*TRADE News** (`etrade`)
- Additional news servers as configured

Configure in `~/.config/colosseum/mcp.json`:

```json
{
  "etrade": {
    "type": "etrade",
    "base_url": "http://localhost:8080",
    "api_key": "your_key"
  }
}
```

## Error Handling

The Curator gracefully handles errors:

- **Source Failures**: Tries alternative MCP servers
- **Database Errors**: Logs failures and continues
- **Network Issues**: Retries with exponential backoff (future)
- **Data Quality Issues**: Records and monitors

```python
# Source errors are tracked in the database
# Query source health:
query = "SELECT * FROM metadata.mcp_sources WHERE status != 'active'"
unhealthy_sources = curator.db_client.execute_query(query)
```

## Best Practices

### 1. Start Worker Early
```python
# Start curator worker at application startup
curator = CuratorAgent()
curator.start_worker(interval=60)
```

### 2. Preload Watchlist
```python
# Add tickers you'll query frequently
common_tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
for ticker in common_tickers:
    curator.add_to_watchlist(ticker)
```

### 3. Query from Data Lake
```python
# Use get_quote() instead of fetch_quote() for cached access
quote = curator.get_quote('AAPL')  # ✅ Cache-first
quote = curator.fetch_quote('AAPL')  # ❌ Always fetches from source
```

### 4. Backfill Historical Data
```python
# Run backfill operations during off-hours
for ticker in portfolio_tickers:
    curator.fetch_historical_data(ticker, period='1Y', interval='1day')
```

### 5. Monitor Health
```python
# Periodically check curator health
if not curator.health_check():
    logger.error("Curator unhealthy!")
    # Alert, restart, or failover
```

## Performance Considerations

### Cache Hit Rate
- Aim for >80% cache hit rate
- Increase `cache_ttl` if hit rate is low
- Ensure worker interval matches query patterns

### Database Batch Size
- Use batch methods for bulk inserts
- Configure `batch_size` based on throughput needs
- Default: 1000 rows per batch

### Worker Interval
- Balance freshness vs. API rate limits
- Default: 60 seconds
- Adjust based on trading strategy (HFT vs. swing trading)

### Connection Pooling
- SQLAlchemy handles connection pooling
- Configure pool size in `config.yaml`
- Default: 10 connections, 20 max overflow

## Troubleshooting

### No Data Fetched

```python
# Check MCP server configuration
print(curator.mcp_servers)  # Should show configured servers

# Check source health
stats = curator.get_stats()
print(f"MCP sources: {stats['mcp_sources']}")
```

### Cache Not Working

```python
# Verify cache TTL
print(f"Cache TTL: {curator.cache_ttl}s")

# Check cache contents
print(f"Cached tickers: {list(curator._quote_cache.keys())}")
```

### Database Connection Errors

```python
# Test database connection
healthy = curator.db_client.health_check()
if not healthy:
    print("Database connection failed!")

# Check connection string in config
```

### Worker Not Running

```python
# Verify worker status
print(f"Worker running: {curator._running}")

# Check logs for errors
# Look for "CuratorAgent worker started" message
```

## Future Enhancements

- **Semantic News Search**: Use pgvector embeddings for similarity search
- **Intelligent Caching**: Predict which tickers will be queried
- **Anomaly Detection**: Flag unusual price movements or data gaps
- **Auto-Scaling**: Dynamically adjust fetch intervals based on load
- **Multi-Source Aggregation**: Combine data from multiple brokers
- **Real-Time Streaming**: WebSocket support for sub-second updates

## Related Documentation

- [Database Schema](../quadlets/README.md#database-schema)
- [MCP Servers](../colosseum/mcp/README.md)
- [Agent Registry](AGENT_REGISTRY.md)
- [Configuration Guide](CONFIGURATION.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/davdunc/colosseum/issues
- See examples: `examples/curator_example.py`
- CLI help: `python -m colosseum.cli.curator --help`
