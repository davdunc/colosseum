#!/usr/bin/env python3
"""
Example usage of the CuratorAgent.

This demonstrates how to use the Curator to manage the data lake:
- Fetching real-time quotes
- Collecting news
- Querying historical data
- Running as a background worker
"""

import time
import logging
from datetime import datetime

from colosseum.agents.curator_agent import CuratorAgent
from colosseum.agent_registry import add_agent_to_registry
from colosseum.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Example 1: Basic quote fetching."""
    print("=" * 70)
    print("Example 1: Basic Quote Fetching")
    print("=" * 70)

    # Initialize the curator
    curator = CuratorAgent()

    # Fetch a single quote
    print("\n📊 Fetching quote for AAPL...")
    quote = curator.fetch_quote('AAPL')

    if quote:
        print(f"   Price:  ${quote['price']:.2f}")
        print(f"   Bid:    ${quote['bid']:.2f}")
        print(f"   Ask:    ${quote['ask']:.2f}")
        print(f"   Volume: {quote['volume']:,}")
        print(f"   Source: {quote['source']}")
    else:
        print("   ❌ No quote available")

    # Fetch multiple quotes
    print("\n📊 Fetching quotes for multiple tickers...")
    tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
    quotes = curator.fetch_quotes_batch(tickers)

    print(f"   Fetched {len(quotes)} quotes:")
    for ticker, quote in quotes.items():
        print(f"   {ticker}: ${quote['price']:.2f}")


def example_news_collection():
    """Example 2: News collection."""
    print("\n" + "=" * 70)
    print("Example 2: News Collection")
    print("=" * 70)

    curator = CuratorAgent()

    # Fetch general market news
    print("\n📰 Fetching general market news...")
    news = curator.fetch_news(limit=5)

    print(f"   Found {len(news)} articles:")
    for i, article in enumerate(news, 1):
        print(f"   {i}. {article['headline']}")
        print(f"      Source: {article['source']}")
        if article.get('sentiment_label'):
            print(f"      Sentiment: {article['sentiment_label']}")

    # Fetch ticker-specific news
    print("\n📰 Fetching news for TSLA...")
    tesla_news = curator.fetch_news(ticker='TSLA', limit=3)

    print(f"   Found {len(tesla_news)} articles:")
    for article in tesla_news:
        print(f"   - {article['headline']}")


def example_historical_data():
    """Example 3: Historical data backfill."""
    print("\n" + "=" * 70)
    print("Example 3: Historical Data Backfill")
    print("=" * 70)

    curator = CuratorAgent()

    # Fetch 1 month of daily data
    print("\n📥 Fetching 1 month of daily data for AAPL...")
    bars = curator.fetch_historical_data('AAPL', period='1M', interval='1day')

    if bars:
        print(f"   Fetched {len(bars)} daily bars")
        print(f"\n   Latest 3 bars:")
        for bar in bars[:3]:
            print(f"   {bar['date']}: O ${bar['open']:.2f} "
                  f"H ${bar['high']:.2f} L ${bar['low']:.2f} "
                  f"C ${bar['close']:.2f} V {bar['volume']:,}")
    else:
        print("   ❌ No historical data available")


def example_watchlist_worker():
    """Example 4: Running as a background worker with watchlist."""
    print("\n" + "=" * 70)
    print("Example 4: Background Worker with Watchlist")
    print("=" * 70)

    config = load_config()
    curator = CuratorAgent(config=config)

    # Add tickers to watchlist
    watchlist = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    print(f"\n📋 Adding {len(watchlist)} tickers to watchlist...")
    for ticker in watchlist:
        curator.add_to_watchlist(ticker)

    print(f"   Watchlist: {', '.join(curator.watchlist)}")

    # Start worker (fetch every 30 seconds)
    print("\n🚀 Starting background worker (30s interval)...")
    curator.start_worker(interval=30)

    # Let it run for 2 minutes
    print("   Worker will run for 2 minutes...")
    try:
        for i in range(12):  # 12 * 10 seconds = 2 minutes
            time.sleep(10)

            # Show stats
            stats = curator.get_stats()
            print(f"   [{i*10}s] Stats: {stats['quotes_fetched']} quotes | "
                  f"{stats['news_fetched']} news | "
                  f"Cache: {stats['cache_size']} | "
                  f"Hits: {stats['cache_hits']}")

    except KeyboardInterrupt:
        print("\n   ⏹️  Interrupted by user")
    finally:
        print("\n⏹️  Stopping worker...")
        curator.stop_worker()
        print("   ✅ Worker stopped")


def example_query_from_datalake():
    """Example 5: Querying data from the data lake."""
    print("\n" + "=" * 70)
    print("Example 5: Querying from Data Lake")
    print("=" * 70)

    curator = CuratorAgent()

    # Get latest quote (cache-first)
    print("\n📊 Getting latest quote from data lake (cache-first)...")
    quote = curator.get_quote('AAPL')
    if quote:
        print(f"   AAPL: ${quote['price']:.2f} (from {quote['source']})")

    # Get OHLCV data
    print("\n📈 Getting OHLCV data from data lake...")
    ohlcv = curator.get_ohlcv('AAPL', interval='1min', limit=10)
    if ohlcv:
        print(f"   Retrieved {len(ohlcv)} 1-minute bars")
        if ohlcv:
            latest = ohlcv[0]
            print(f"   Latest: O ${latest['open']:.2f} "
                  f"H ${latest['high']:.2f} L ${latest['low']:.2f} "
                  f"C ${latest['close']:.2f}")

    # Search news
    print("\n🔍 Searching news in data lake...")
    news = curator.search_news(ticker='AAPL', limit=5)
    print(f"   Found {len(news)} news articles for AAPL")
    for article in news[:3]:
        print(f"   - {article['headline']}")


def example_with_agent_registry():
    """Example 6: Using Curator with Agent Registry."""
    print("\n" + "=" * 70)
    print("Example 6: Agent Registry Integration")
    print("=" * 70)

    # Create and register the curator
    curator = CuratorAgent()
    registry = add_agent_to_registry('curator', curator)

    print("\n✅ Curator registered with agent registry")
    print(f"   Registry agents: {list(registry.agents.keys())}")

    # Other agents can now access the curator
    retrieved_curator = registry.get_agent('curator')
    print(f"\n🔍 Retrieved curator from registry: {retrieved_curator.agent_name}")

    # Use curator through registry
    print("\n📊 Fetching quote through registry...")
    quote = retrieved_curator.fetch_quote('MSFT')
    if quote:
        print(f"   MSFT: ${quote['price']:.2f}")


def example_health_and_stats():
    """Example 7: Health checks and statistics."""
    print("\n" + "=" * 70)
    print("Example 7: Health Checks and Statistics")
    print("=" * 70)

    curator = CuratorAgent()

    # Health check
    print("\n🏥 Running health check...")
    healthy = curator.health_check()
    print(f"   Status: {'✅ Healthy' if healthy else '❌ Unhealthy'}")

    # Get detailed stats
    print("\n📊 Curator statistics:")
    stats = curator.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")


def main():
    """Run all examples."""
    print("\n🏛️  Colosseum CuratorAgent Examples")
    print("=" * 70)
    print("Demonstrating the keeper of records in action")
    print("=" * 70)

    try:
        # Run examples
        example_basic_usage()
        example_news_collection()
        example_historical_data()
        example_query_from_datalake()
        example_with_agent_registry()
        example_health_and_stats()

        # Optional: Run worker example (uncomment to enable)
        # example_watchlist_worker()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        print("\n❌ Example failed - see logs for details")


if __name__ == '__main__':
    main()
