#!/usr/bin/env python3
"""
CLI tool for the CuratorAgent - The Colosseum's keeper of records.

Usage:
    curator start [--interval SECONDS]    Start the curator worker
    curator fetch <ticker> [--source SRC] Fetch quote for a ticker
    curator watch <ticker>...              Add tickers to watchlist
    curator unwatch <ticker>...            Remove tickers from watchlist
    curator news [--ticker TICKER]         Fetch recent news
    curator backfill <ticker> [--period]   Backfill historical data
    curator stats                          Show curator statistics
    curator health                         Check curator health
"""

import sys
import logging
import argparse
from datetime import datetime

from ..agents.curator_agent import CuratorAgent
from ..config import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_start(args):
    """Start the curator worker."""
    print("🏛️  Starting the Curator - Keeper of Colosseum Records")
    print("=" * 60)

    config = load_config()
    curator = CuratorAgent(config=config)

    # Add any pre-configured watchlist
    if args.tickers:
        for ticker in args.tickers:
            curator.add_to_watchlist(ticker)
        print(f"📋 Watching {len(args.tickers)} tickers")

    print(f"⏱️  Fetch interval: {args.interval} seconds")
    print(f"🔌 MCP Sources: {len(curator.mcp_servers)}")
    print()

    try:
        curator.start_worker(interval=args.interval)
        print("✅ Curator worker started. Press Ctrl+C to stop.")
        print()

        # Keep main thread alive
        while True:
            import time
            time.sleep(10)

            # Print stats periodically
            stats = curator.get_stats()
            print(f"📊 Stats: {stats['quotes_fetched']} quotes | "
                  f"{stats['news_fetched']} news | "
                  f"{stats['cache_hits']} cache hits | "
                  f"Cache: {stats['cache_size']}")

    except KeyboardInterrupt:
        print("\n⏹️  Stopping curator...")
        curator.stop_worker()
        print("✅ Curator stopped")


def cmd_fetch(args):
    """Fetch a quote for a ticker."""
    curator = CuratorAgent()

    print(f"📊 Fetching quote for {args.ticker}...")
    quote = curator.fetch_quote(args.ticker, source=args.source)

    if quote:
        print(f"\n✅ Quote for {args.ticker}:")
        print(f"   Price:  ${quote['price']:.2f}")
        print(f"   Bid:    ${quote['bid']:.2f}")
        print(f"   Ask:    ${quote['ask']:.2f}")
        print(f"   Volume: {quote['volume']:,}")
        print(f"   Source: {quote['source']}")
        print(f"   Time:   {quote['timestamp']}")
    else:
        print(f"❌ No quote available for {args.ticker}")
        sys.exit(1)


def cmd_watch(args):
    """Add tickers to watchlist."""
    curator = CuratorAgent()

    for ticker in args.tickers:
        curator.add_to_watchlist(ticker)

    print(f"✅ Added {len(args.tickers)} tickers to watchlist")
    print(f"📋 Watchlist: {', '.join(curator.watchlist)}")


def cmd_unwatch(args):
    """Remove tickers from watchlist."""
    curator = CuratorAgent()

    for ticker in args.tickers:
        curator.remove_from_watchlist(ticker)

    print(f"✅ Removed {len(args.tickers)} tickers from watchlist")
    print(f"📋 Watchlist: {', '.join(curator.watchlist)}")


def cmd_news(args):
    """Fetch recent news."""
    curator = CuratorAgent()

    print("📰 Fetching news...")
    articles = curator.fetch_news(ticker=args.ticker, limit=args.limit)

    if articles:
        print(f"\n✅ Found {len(articles)} articles:\n")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['headline']}")
            print(f"   Source: {article['source']}")
            print(f"   Published: {article['published_at']}")
            if article.get('tickers'):
                print(f"   Tickers: {', '.join(article['tickers'])}")
            if article.get('sentiment_label'):
                print(f"   Sentiment: {article['sentiment_label']} "
                      f"({article['sentiment_score']:.2f})")
            print()
    else:
        print("❌ No news found")


def cmd_backfill(args):
    """Backfill historical data."""
    curator = CuratorAgent()

    print(f"📥 Backfilling {args.period} of data for {args.ticker}...")
    bars = curator.fetch_historical_data(
        args.ticker,
        period=args.period,
        interval=args.interval
    )

    if bars:
        print(f"✅ Fetched {len(bars)} bars")
        if bars:
            latest = bars[0]
            print(f"\n   Latest bar:")
            print(f"   Date:  {latest['date']}")
            print(f"   Open:  ${latest['open']:.2f}")
            print(f"   High:  ${latest['high']:.2f}")
            print(f"   Low:   ${latest['low']:.2f}")
            print(f"   Close: ${latest['close']:.2f}")
            print(f"   Vol:   {latest['volume']:,}")
    else:
        print(f"❌ No historical data available")


def cmd_stats(args):
    """Show curator statistics."""
    curator = CuratorAgent()
    stats = curator.get_stats()

    print("📊 Curator Statistics")
    print("=" * 60)
    print(f"Session ID:          {stats['session_id']}")
    print(f"Watchlist Size:      {stats['watchlist_size']}")
    print(f"Cache Size:          {stats['cache_size']}")
    print(f"Worker Running:      {stats['worker_running']}")
    print(f"MCP Sources:         {stats['mcp_sources']}")
    print()
    print(f"Quotes Fetched:      {stats.get('quotes_fetched', 0)}")
    print(f"Quotes Persisted:    {stats.get('quotes_persisted', 0)}")
    print(f"News Fetched:        {stats.get('news_fetched', 0)}")
    print(f"Historical Bars:     {stats.get('historical_bars_fetched', 0)}")
    print(f"Cache Hits:          {stats.get('cache_hits', 0)}")
    print(f"Fetch Failures:      {stats.get('fetch_failures', 0)}")
    print(f"Persist Failures:    {stats.get('persist_failures', 0)}")


def cmd_health(args):
    """Check curator health."""
    curator = CuratorAgent()

    print("🏥 Checking Curator Health...")
    print("=" * 60)

    # Check database
    print("🗄️  Database:        ", end="")
    db_healthy = curator.db_client.health_check()
    print("✅ OK" if db_healthy else "❌ FAILED")

    # Check MCP sources
    print(f"🔌 MCP Sources:      {len(curator.mcp_servers)} configured")
    for name, server in curator.mcp_servers.items():
        print(f"   - {name}: ✅")

    # Check S3 sources
    if curator.s3_sources:
        print(f"☁️  S3 Sources:       {len(curator.s3_sources)} configured")
        for name in curator.s3_sources.keys():
            print(f"   - {name}: ✅")

    # Overall health
    print()
    healthy = curator.health_check()
    if healthy:
        print("✅ Curator is healthy")
        sys.exit(0)
    else:
        print("❌ Curator is unhealthy")
        sys.exit(1)


def cmd_s3_list(args):
    """List S3 parquet files."""
    curator = CuratorAgent()

    print(f"☁️  Listing S3 files: {args.source}/{args.prefix}")
    files = curator.list_s3_files(args.source, prefix=args.prefix)

    if files:
        print(f"\n✅ Found {len(files)} files:\n")
        for f in files[:args.limit]:
            print(f"   {f}")
        if len(files) > args.limit:
            print(f"\n   ... and {len(files) - args.limit} more")
    else:
        print("❌ No files found")


def cmd_s3_import(args):
    """Import from S3 parquet files."""
    curator = CuratorAgent()

    print(f"☁️  Importing from S3: {args.source}/{args.prefix}")
    print(f"   Data type: {args.type}")
    print()

    stats = curator.import_from_s3(
        args.source,
        prefix=args.prefix,
        data_type=args.type
    )

    if 'error' in stats:
        print(f"❌ Import failed: {stats['error']}")
        sys.exit(1)

    print("✅ Import complete!\n")
    print(f"📊 Statistics:")
    print(f"   Files processed:  {stats.get('files_processed', 0)}")
    print(f"   Files failed:     {stats.get('files_failed', 0)}")
    print(f"   Quotes imported:  {stats.get('quotes', 0)}")
    print(f"   OHLCV imported:   {stats.get('ohlcv', 0)}")
    print(f"   News imported:    {stats.get('news', 0)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CuratorAgent - The Colosseum's keeper of records",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start curator worker')
    start_parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Fetch interval in seconds (default: 60)'
    )
    start_parser.add_argument(
        '--tickers',
        nargs='+',
        help='Initial watchlist tickers'
    )

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch quote')
    fetch_parser.add_argument('ticker', help='Ticker symbol')
    fetch_parser.add_argument('--source', help='Specific MCP source')

    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Add to watchlist')
    watch_parser.add_argument('tickers', nargs='+', help='Ticker symbols')

    # Unwatch command
    unwatch_parser = subparsers.add_parser('unwatch', help='Remove from watchlist')
    unwatch_parser.add_argument('tickers', nargs='+', help='Ticker symbols')

    # News command
    news_parser = subparsers.add_parser('news', help='Fetch news')
    news_parser.add_argument('--ticker', help='Filter by ticker')
    news_parser.add_argument('--limit', type=int, default=10, help='Max articles')

    # Backfill command
    backfill_parser = subparsers.add_parser('backfill', help='Backfill historical data')
    backfill_parser.add_argument('ticker', help='Ticker symbol')
    backfill_parser.add_argument('--period', default='1M', help='Period (1D, 1W, 1M, 3M, 1Y, 5Y)')
    backfill_parser.add_argument('--interval', default='1day', help='Interval (1min, 5min, 1hour, 1day)')

    # Stats command
    subparsers.add_parser('stats', help='Show statistics')

    # Health command
    subparsers.add_parser('health', help='Check health')

    # S3 list command
    s3_list_parser = subparsers.add_parser('s3-list', help='List S3 parquet files')
    s3_list_parser.add_argument('source', help='S3 source name')
    s3_list_parser.add_argument('--prefix', default='', help='Key prefix')
    s3_list_parser.add_argument('--limit', type=int, default=20, help='Max files to show')

    # S3 import command
    s3_import_parser = subparsers.add_parser('s3-import', help='Import from S3 parquet')
    s3_import_parser.add_argument('source', help='S3 source name')
    s3_import_parser.add_argument('--prefix', default='', help='Key prefix')
    s3_import_parser.add_argument('--type', default='auto', choices=['auto', 'quotes', 'ohlcv', 'news'], help='Data type')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handlers
    commands = {
        'start': cmd_start,
        'fetch': cmd_fetch,
        'watch': cmd_watch,
        'unwatch': cmd_unwatch,
        'news': cmd_news,
        'backfill': cmd_backfill,
        'stats': cmd_stats,
        'health': cmd_health,
        's3-list': cmd_s3_list,
        's3-import': cmd_s3_import,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except Exception as e:
            logger.error(f"Command failed: {e}", exc_info=True)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
