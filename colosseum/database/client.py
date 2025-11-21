"""
Database client for Colosseum data lake.
Provides connection pooling and query helpers for PostgreSQL.
"""
import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from ..config import load_config

logger = logging.getLogger(__name__)


class DataLakeClient:
    """
    Client for interacting with the Colosseum PostgreSQL data lake.

    Uses SQLAlchemy for connection pooling and query execution.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DataLake client.

        Args:
            config: Optional configuration dict. If not provided, loads from config.yaml
        """
        if config is None:
            config = load_config()

        self.config = config.get('database', {})
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info("DataLakeClient initialized")

    def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling."""
        # Get connection parameters
        host = self.config.get('host', 'localhost')
        port = self.config.get('port', 5432)
        database = self.config.get('database', 'colosseum_data_lake')
        user = self.config.get('user', 'colosseum')

        # Get password from config or environment
        password = self.config.get('password', '')
        if password.startswith('${') and password.endswith('}'):
            # Extract environment variable name
            env_var = password[2:-1]
            password = os.environ.get(env_var, '')

        # Build connection URL
        connection_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        # Pool settings
        pool_size = self.config.get('pool_size', 10)
        max_overflow = self.config.get('max_overflow', 20)
        pool_timeout = self.config.get('pool_timeout', 30)
        pool_recycle = self.config.get('pool_recycle', 3600)

        # Create engine
        engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=self.config.get('echo', False)
        )

        logger.info(f"Database engine created: {host}:{port}/{database}")
        return engine

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.

        Usage:
            with client.get_session() as session:
                result = session.execute(text("SELECT * FROM table"))
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a raw SQL query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Optional parameters for the query

        Returns:
            List of dictionaries representing rows
        """
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []

    def execute_many(self, query: str, params_list: List[Dict]) -> int:
        """
        Execute a query multiple times with different parameters (batch insert).

        Args:
            query: SQL query string
            params_list: List of parameter dictionaries

        Returns:
            Number of rows affected
        """
        with self.get_session() as session:
            result = session.execute(text(query), params_list)
            return result.rowcount

    def get_latest_quote(self, ticker: str) -> Optional[Dict]:
        """
        Get the latest quote for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with quote data or None
        """
        query = """
        SELECT * FROM market_data.get_latest_quote(:ticker)
        """
        results = self.execute_query(query, {"ticker": ticker})
        return results[0] if results else None

    def insert_quotes(self, quotes: List[Dict]) -> int:
        """
        Batch insert stock quotes.

        Args:
            quotes: List of quote dictionaries with keys:
                   ticker, timestamp, price, volume, bid, ask, source

        Returns:
            Number of quotes inserted
        """
        query = """
        INSERT INTO market_data.stock_quotes
            (ticker, timestamp, price, volume, bid, ask, bid_size, ask_size, source, metadata)
        VALUES
            (:ticker, :timestamp, :price, :volume, :bid, :ask,
             :bid_size, :ask_size, :source, :metadata::jsonb)
        """
        return self.execute_many(query, quotes)

    def insert_news(self, articles: List[Dict]) -> int:
        """
        Batch insert news articles.

        Args:
            articles: List of article dictionaries with keys:
                     headline, content, summary, source, url, published_at,
                     tickers, sentiment_score, sentiment_label, metadata

        Returns:
            Number of articles inserted
        """
        query = """
        INSERT INTO market_data.news_articles
            (headline, content, summary, source, url, published_at,
             tickers, sentiment_score, sentiment_label, metadata)
        VALUES
            (:headline, :content, :summary, :source, :url, :published_at,
             :tickers, :sentiment_score, :sentiment_label, :metadata::jsonb)
        ON CONFLICT DO NOTHING
        """
        return self.execute_many(query, articles)

    def search_news_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Search news articles by semantic similarity.

        Args:
            embedding: Query embedding vector (1536 dimensions)
            limit: Maximum number of results
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of matching articles with similarity scores
        """
        query = """
        SELECT * FROM market_data.search_news_by_embedding(
            :embedding::vector,
            :limit,
            :threshold
        )
        """
        # Convert list to PostgreSQL array format
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        return self.execute_query(query, {
            "embedding": embedding_str,
            "limit": limit,
            "threshold": threshold
        })

    def insert_agent_decision(self, decision: Dict) -> int:
        """
        Record an agent decision.

        Args:
            decision: Dictionary with keys:
                     agent_name, agent_type, ticker, action, confidence,
                     reasoning, data_sources, metadata, session_id

        Returns:
            Decision ID
        """
        query = """
        INSERT INTO agent_data.decisions
            (agent_name, agent_type, ticker, action, confidence,
             reasoning, data_sources, metadata, session_id)
        VALUES
            (:agent_name, :agent_type, :ticker, :action, :confidence,
             :reasoning, :data_sources, :metadata::jsonb, :session_id)
        RETURNING id
        """
        with self.get_session() as session:
            result = session.execute(text(query), decision)
            return result.scalar()

    def get_ohlcv(
        self,
        ticker: str,
        interval: str = "1min",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get OHLCV data for a ticker.

        Args:
            ticker: Stock ticker symbol
            interval: Time interval (1min, 5min, 1hour, 1day)
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            limit: Maximum number of bars

        Returns:
            List of OHLCV bars
        """
        if interval == "1day":
            query = """
            SELECT ticker, date, open, high, low, close, volume
            FROM market_data.daily_bars
            WHERE ticker = :ticker
            """
        else:
            query = """
            SELECT ticker, bucket as timestamp, open, high, low, close, volume
            FROM market_data.ohlcv_1min
            WHERE ticker = :ticker
            """

        if start_time:
            query += " AND bucket >= :start_time"
        if end_time:
            query += " AND bucket <= :end_time"

        query += " ORDER BY bucket DESC LIMIT :limit"

        return self.execute_query(query, {
            "ticker": ticker,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit
        })

    def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            result = self.execute_query("SELECT 1 as healthy")
            return result[0]['healthy'] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self):
        """Close the database engine and connection pool."""
        self.engine.dispose()
        logger.info("DataLakeClient closed")


# Singleton instance
_client_instance: Optional[DataLakeClient] = None


def get_client() -> DataLakeClient:
    """Get or create singleton DataLakeClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = DataLakeClient()
    return _client_instance
