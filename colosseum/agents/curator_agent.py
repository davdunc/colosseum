"""
CuratorAgent - The keeper of records in the Colosseum

Like a Roman curator who managed public archives and records, this agent is
responsible for curating the data lake: collecting market data from various
sources, organizing it efficiently, and making it available to other agents.

Responsibilities:
- Ingest data from MCP servers (Interactive Brokers, E*TRADE, DAS Trader)
- Persist data to PostgreSQL data lake
- Maintain data quality and freshness
- Provide efficient cached access to other agents
- Monitor data source health
- Execute backfill operations for historical data
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from threading import Thread, Event
from collections import defaultdict

from ..database.client import get_client, DataLakeClient
from ..mcp.loader import load_mcp_servers
from ..mcp.base import MCPServer, BrokerMCPServer, NewsMCPServer

logger = logging.getLogger(__name__)

# Lazy import for S3 dependencies (optional)
try:
    from ..data_sources.s3_parquet import S3ParquetSource, S3ParquetETL
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logger.warning("S3 parquet support not available (install boto3, pyarrow, pandas)")


class CuratorAgent:
    """
    CuratorAgent manages the Colosseum data lake.

    This agent continuously fetches market data from configured MCP servers
    and persists it to PostgreSQL for efficient access by other agents.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        db_client: Optional[DataLakeClient] = None,
        mcp_servers: Optional[Dict[str, MCPServer]] = None
    ):
        """
        Initialize the CuratorAgent.

        Args:
            config: Optional configuration dict
            db_client: Optional DataLakeClient instance (creates one if not provided)
            mcp_servers: Optional pre-loaded MCP servers
        """
        self.config = config or {}
        self.agent_config = self.config.get('agents', {}).get('curator', {})

        # Database client
        self.db_client = db_client or get_client()

        # MCP servers (data sources)
        self.mcp_servers = mcp_servers or load_mcp_servers()

        # Agent identity
        self.agent_name = "curator"
        self.session_id = uuid.uuid4()

        # Cache for recent data (ticker -> latest quote)
        self._quote_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl = self.agent_config.get('cache_ttl', 300)  # seconds

        # Watchlist of tickers to monitor
        self.watchlist: List[str] = []

        # Worker thread control
        self._worker_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._running = False

        # Statistics
        self.stats = defaultdict(int)

        # S3 Parquet sources (optional)
        self.s3_sources: Dict[str, S3ParquetSource] = {}
        self._init_s3_sources()

        logger.info(f"CuratorAgent initialized (session: {self.session_id})")

    # =========================================================================
    # Data Ingestion Methods
    # =========================================================================

    def fetch_quote(self, ticker: str, source: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch the latest quote for a ticker from MCP servers.

        Args:
            ticker: Stock ticker symbol
            source: Optional specific MCP server to use

        Returns:
            Quote data or None if unavailable
        """
        # Check cache first
        if self._is_cached(ticker):
            logger.debug(f"Cache hit for {ticker}")
            self.stats['cache_hits'] += 1
            return self._quote_cache[ticker]

        # Fetch from MCP servers
        servers_to_try = []
        if source and source in self.mcp_servers:
            servers_to_try = [(source, self.mcp_servers[source])]
        else:
            # Try all broker MCP servers
            servers_to_try = [
                (name, server) for name, server in self.mcp_servers.items()
                if isinstance(server, BrokerMCPServer)
            ]

        for server_name, server in servers_to_try:
            try:
                quote_data = server.get_resource('quote', symbol=ticker)
                if quote_data:
                    # Enrich with metadata
                    quote = {
                        'ticker': ticker,
                        'timestamp': datetime.now(),
                        'price': quote_data.get('price'),
                        'volume': quote_data.get('volume'),
                        'bid': quote_data.get('bid'),
                        'ask': quote_data.get('ask'),
                        'bid_size': quote_data.get('bid_size'),
                        'ask_size': quote_data.get('ask_size'),
                        'source': server_name,
                        'metadata': quote_data
                    }

                    # Update cache
                    self._update_cache(ticker, quote)

                    # Persist to database (async)
                    self._persist_quote(quote)

                    self.stats['quotes_fetched'] += 1
                    return quote

            except Exception as e:
                logger.warning(f"Failed to fetch quote from {server_name}: {e}")
                self._record_source_error(server_name, str(e))
                continue

        logger.warning(f"No quote available for {ticker}")
        self.stats['fetch_failures'] += 1
        return None

    def fetch_quotes_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Fetch quotes for multiple tickers efficiently.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to quote data
        """
        results = {}
        for ticker in tickers:
            quote = self.fetch_quote(ticker)
            if quote:
                results[ticker] = quote
        return results

    def fetch_news(
        self,
        ticker: Optional[str] = None,
        limit: int = 10,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Fetch news articles from MCP servers.

        Args:
            ticker: Optional ticker to filter news
            limit: Maximum number of articles
            since: Only fetch news after this timestamp

        Returns:
            List of news article dictionaries
        """
        articles = []

        # Try all news MCP servers
        news_servers = [
            (name, server) for name, server in self.mcp_servers.items()
            if isinstance(server, NewsMCPServer)
        ]

        for server_name, server in news_servers:
            try:
                news_data = server.get_resource(
                    'news',
                    symbol=ticker,
                    limit=limit,
                    since=since.isoformat() if since else None
                )

                if news_data:
                    for article in news_data:
                        enriched = {
                            'headline': article.get('headline'),
                            'content': article.get('content'),
                            'summary': article.get('summary'),
                            'source': server_name,
                            'url': article.get('url'),
                            'published_at': article.get('published_at'),
                            'tickers': [ticker] if ticker else article.get('tickers', []),
                            'sentiment_score': article.get('sentiment_score'),
                            'sentiment_label': article.get('sentiment_label'),
                            'metadata': article
                        }
                        articles.append(enriched)

                    # Persist to database
                    if articles:
                        self.db_client.insert_news(articles)
                        self.stats['news_fetched'] += len(articles)

            except Exception as e:
                logger.warning(f"Failed to fetch news from {server_name}: {e}")
                self._record_source_error(server_name, str(e))
                continue

        return articles[:limit]

    def fetch_historical_data(
        self,
        ticker: str,
        period: str = "1M",
        interval: str = "1day"
    ) -> List[Dict]:
        """
        Fetch historical OHLCV data and persist to database.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1D, 1W, 1M, 3M, 1Y, 5Y)
            interval: Bar interval (1min, 5min, 1hour, 1day)

        Returns:
            List of OHLCV bars
        """
        # Try broker servers for historical data
        for server_name, server in self.mcp_servers.items():
            if not isinstance(server, BrokerMCPServer):
                continue

            try:
                bars = server.get_resource(
                    'historical',
                    symbol=ticker,
                    period=period,
                    interval=interval
                )

                if bars:
                    # Transform and persist
                    for bar in bars:
                        bar_data = {
                            'ticker': ticker,
                            'date': bar.get('date'),
                            'open': bar.get('open'),
                            'high': bar.get('high'),
                            'low': bar.get('low'),
                            'close': bar.get('close'),
                            'volume': bar.get('volume'),
                            'adj_close': bar.get('adj_close'),
                            'source': server_name
                        }

                    # Batch insert
                    query = """
                    INSERT INTO market_data.daily_bars
                        (ticker, date, open, high, low, close, volume, adj_close, source)
                    VALUES
                        (:ticker, :date, :open, :high, :low, :close, :volume,
                         :adj_close, :source)
                    ON CONFLICT (ticker, date, source) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        adj_close = EXCLUDED.adj_close
                    """
                    self.db_client.execute_many(query, bars)
                    self.stats['historical_bars_fetched'] += len(bars)

                    logger.info(f"Fetched {len(bars)} bars for {ticker} from {server_name}")
                    return bars

            except Exception as e:
                logger.warning(f"Failed to fetch historical data from {server_name}: {e}")
                continue

        return []

    # =========================================================================
    # Query Methods (for other agents)
    # =========================================================================

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """
        Get the latest quote for a ticker (cache-first).

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quote data or None
        """
        # Check cache
        if self._is_cached(ticker):
            return self._quote_cache[ticker]

        # Check database
        quote = self.db_client.get_latest_quote(ticker)
        if quote:
            self._update_cache(ticker, quote)
            return quote

        # Fetch fresh data
        return self.fetch_quote(ticker)

    def get_ohlcv(
        self,
        ticker: str,
        interval: str = "1min",
        limit: int = 100
    ) -> List[Dict]:
        """
        Get OHLCV data from the data lake.

        Args:
            ticker: Stock ticker symbol
            interval: Time interval (1min, 1day)
            limit: Maximum number of bars

        Returns:
            List of OHLCV bars
        """
        return self.db_client.get_ohlcv(ticker, interval=interval, limit=limit)

    def search_news(
        self,
        query: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search news in the data lake.

        Args:
            query: Text query (for future semantic search)
            ticker: Filter by ticker
            limit: Maximum results

        Returns:
            List of news articles
        """
        # Simple query for now (semantic search requires embeddings)
        sql = """
        SELECT id, headline, summary, published_at, source, tickers, sentiment_score
        FROM market_data.news_articles
        WHERE 1=1
        """
        params = {'limit': limit}

        if ticker:
            sql += " AND :ticker = ANY(tickers)"
            params['ticker'] = ticker

        sql += " ORDER BY published_at DESC LIMIT :limit"

        return self.db_client.execute_query(sql, params)

    # =========================================================================
    # Watchlist Management
    # =========================================================================

    def add_to_watchlist(self, ticker: str):
        """Add a ticker to the watchlist."""
        if ticker not in self.watchlist:
            self.watchlist.append(ticker)
            logger.info(f"Added {ticker} to watchlist")

    def remove_from_watchlist(self, ticker: str):
        """Remove a ticker from the watchlist."""
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)
            logger.info(f"Removed {ticker} from watchlist")

    # =========================================================================
    # Background Worker
    # =========================================================================

    def start_worker(self, interval: int = 60):
        """
        Start background worker to continuously fetch data.

        Args:
            interval: Fetch interval in seconds
        """
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True
        self._stop_event.clear()

        def worker_loop():
            logger.info(f"CuratorAgent worker started (interval: {interval}s)")

            while not self._stop_event.is_set():
                try:
                    # Fetch quotes for watchlist
                    if self.watchlist:
                        logger.debug(f"Fetching quotes for {len(self.watchlist)} tickers")
                        self.fetch_quotes_batch(self.watchlist)

                    # Fetch news (general market news)
                    self.fetch_news(limit=20)

                    # Update source health
                    self._update_source_health()

                except Exception as e:
                    logger.error(f"Worker error: {e}")

                # Sleep with interruptible wait
                self._stop_event.wait(timeout=interval)

            logger.info("CuratorAgent worker stopped")
            self._running = False

        self._worker_thread = Thread(target=worker_loop, daemon=True)
        self._worker_thread.start()

    def stop_worker(self):
        """Stop the background worker."""
        if self._running:
            logger.info("Stopping CuratorAgent worker...")
            self._stop_event.set()
            if self._worker_thread:
                self._worker_thread.join(timeout=5)
            self._running = False

    # =========================================================================
    # Cache Management
    # =========================================================================

    def _is_cached(self, ticker: str) -> bool:
        """Check if ticker data is in cache and still fresh."""
        if ticker not in self._quote_cache:
            return False

        timestamp = self._cache_timestamps.get(ticker)
        if not timestamp:
            return False

        age = (datetime.now() - timestamp).total_seconds()
        return age < self.cache_ttl

    def _update_cache(self, ticker: str, quote: Dict):
        """Update cache with new quote data."""
        self._quote_cache[ticker] = quote
        self._cache_timestamps[ticker] = datetime.now()

    def clear_cache(self):
        """Clear all cached data."""
        self._quote_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cache cleared")

    # =========================================================================
    # Persistence Helpers
    # =========================================================================

    def _persist_quote(self, quote: Dict):
        """Persist a single quote to the database."""
        try:
            self.db_client.insert_quotes([quote])
            self.stats['quotes_persisted'] += 1
        except Exception as e:
            logger.error(f"Failed to persist quote: {e}")
            self.stats['persist_failures'] += 1

    # =========================================================================
    # Monitoring & Health
    # =========================================================================

    def _record_source_error(self, source_name: str, error: str):
        """Record an error from an MCP source."""
        query = """
        UPDATE metadata.mcp_sources
        SET last_error = :error,
            error_count = error_count + 1,
            updated_at = NOW()
        WHERE source_name = :source_name
        """
        try:
            self.db_client.execute_query(query, {
                'source_name': source_name,
                'error': error
            })
        except Exception as e:
            logger.error(f"Failed to record source error: {e}")

    def _update_source_health(self):
        """Update health status for all MCP sources."""
        for source_name, server in self.mcp_servers.items():
            try:
                # Try a lightweight health check
                # (implementation depends on MCP server capabilities)
                status = 'active'  # Assume active if no errors

                query = """
                INSERT INTO metadata.mcp_sources (source_name, status, last_successful_fetch)
                VALUES (:source_name, :status, NOW())
                ON CONFLICT (source_name) DO UPDATE SET
                    status = EXCLUDED.status,
                    last_successful_fetch = NOW(),
                    updated_at = NOW()
                """
                self.db_client.execute_query(query, {
                    'source_name': source_name,
                    'status': status
                })
            except Exception as e:
                logger.error(f"Failed to update source health for {source_name}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with various stats
        """
        return {
            'session_id': str(self.session_id),
            'watchlist_size': len(self.watchlist),
            'cache_size': len(self._quote_cache),
            'worker_running': self._running,
            'mcp_sources': len(self.mcp_servers),
            **dict(self.stats)
        }

    def health_check(self) -> bool:
        """
        Check if the curator is healthy.

        Returns:
            True if healthy, False otherwise
        """
        # Check database connection
        if not self.db_client.health_check():
            return False

        # Check if we have MCP servers
        if not self.mcp_servers:
            return False

        return True

    # =========================================================================
    # S3 Parquet Import Methods
    # =========================================================================

    def _init_s3_sources(self):
        """Initialize S3 parquet sources from configuration."""
        if not S3_AVAILABLE:
            return

        s3_config = self.config.get('s3', {}).get('sources', {})

        for name, config in s3_config.items():
            try:
                source = S3ParquetSource(
                    bucket=config['bucket'],
                    region=config.get('region'),
                    aws_access_key_id=config.get('aws_access_key_id'),
                    aws_secret_access_key=config.get('aws_secret_access_key'),
                    endpoint_url=config.get('endpoint_url'),
                    config=config
                )
                self.s3_sources[name] = source
                logger.info(f"Initialized S3 source: {name} (bucket: {config['bucket']})")
            except Exception as e:
                logger.error(f"Failed to initialize S3 source {name}: {e}")

    def import_from_s3(
        self,
        source_name: str,
        prefix: str = "",
        data_type: str = "auto",
        max_files: int = 100
    ) -> Dict[str, int]:
        """
        Import data from S3 parquet files.

        Args:
            source_name: Name of configured S3 source
            prefix: S3 key prefix to filter files
            data_type: Type of data (auto, quotes, ohlcv, news)
            max_files: Maximum number of files to process

        Returns:
            Dictionary with import statistics
        """
        if not S3_AVAILABLE:
            logger.error("S3 support not available")
            return {'error': 'S3 dependencies not installed'}

        if source_name not in self.s3_sources:
            logger.error(f"S3 source not configured: {source_name}")
            return {'error': f'Source {source_name} not found'}

        s3_source = self.s3_sources[source_name]
        etl = S3ParquetETL(s3_source, self.db_client)

        logger.info(f"Starting S3 import: source={source_name}, prefix={prefix}, type={data_type}")

        stats = etl.import_all(prefix=prefix, data_type=data_type)

        logger.info(f"S3 import complete: {stats}")
        self.stats['s3_imports'] += stats['files_processed']
        self.stats['s3_import_failures'] += stats['files_failed']

        return stats

    def import_s3_quotes(
        self,
        source_name: str,
        keys: List[str]
    ) -> int:
        """
        Import stock quotes from S3 parquet files.

        Args:
            source_name: Name of configured S3 source
            keys: List of S3 keys to import

        Returns:
            Number of quotes imported
        """
        if not S3_AVAILABLE or source_name not in self.s3_sources:
            return 0

        s3_source = self.s3_sources[source_name]
        etl = S3ParquetETL(s3_source, self.db_client)

        count = etl.import_quotes(keys)
        self.stats['s3_quotes_imported'] += count

        return count

    def import_s3_ohlcv(
        self,
        source_name: str,
        keys: List[str]
    ) -> int:
        """
        Import OHLCV bars from S3 parquet files.

        Args:
            source_name: Name of configured S3 source
            keys: List of S3 keys to import

        Returns:
            Number of bars imported
        """
        if not S3_AVAILABLE or source_name not in self.s3_sources:
            return 0

        s3_source = self.s3_sources[source_name]
        etl = S3ParquetETL(s3_source, self.db_client)

        count = etl.import_ohlcv(keys)
        self.stats['s3_ohlcv_imported'] += count

        return count

    def import_s3_news(
        self,
        source_name: str,
        keys: List[str]
    ) -> int:
        """
        Import news articles from S3 parquet files.

        Args:
            source_name: Name of configured S3 source
            keys: List of S3 keys to import

        Returns:
            Number of articles imported
        """
        if not S3_AVAILABLE or source_name not in self.s3_sources:
            return 0

        s3_source = self.s3_sources[source_name]
        etl = S3ParquetETL(s3_source, self.db_client)

        count = etl.import_news(keys)
        self.stats['s3_news_imported'] += count

        return count

    def list_s3_files(
        self,
        source_name: str,
        prefix: str = "",
        suffix: str = ".parquet"
    ) -> List[str]:
        """
        List parquet files in S3 bucket.

        Args:
            source_name: Name of configured S3 source
            prefix: Key prefix to filter
            suffix: File suffix

        Returns:
            List of S3 keys
        """
        if not S3_AVAILABLE or source_name not in self.s3_sources:
            return []

        s3_source = self.s3_sources[source_name]
        return s3_source.list_files(prefix=prefix, suffix=suffix)
