"""
S3 Parquet Data Source for Colosseum

This module provides S3 integration for importing parquet files into the
Colosseum data lake. Useful for:
- Historical data backfill
- Bulk data imports
- Integration with external data lakes
- ETL from cloud storage
"""

import logging
import io
from typing import List, Dict, Optional, Any, Iterator
from datetime import datetime
import pandas as pd
import pyarrow.parquet as pq
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..config import load_config

logger = logging.getLogger(__name__)


class S3ParquetSource:
    """
    S3 Parquet data source for Colosseum.

    Reads parquet files from S3 buckets and provides data in a format
    compatible with the CuratorAgent for ingestion into PostgreSQL.
    """

    def __init__(
        self,
        bucket: str,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,  # For S3-compatible storage
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize S3 Parquet source.

        Args:
            bucket: S3 bucket name
            region: AWS region (default: us-east-1)
            aws_access_key_id: AWS access key (or use env/IAM)
            aws_secret_access_key: AWS secret key (or use env/IAM)
            endpoint_url: Custom S3 endpoint (for MinIO, etc.)
            config: Optional configuration dict
        """
        self.bucket = bucket
        self.region = region or 'us-east-1'
        self.endpoint_url = endpoint_url
        self.config = config or {}

        # Initialize S3 client
        session_kwargs = {
            'region_name': self.region
        }

        if aws_access_key_id and aws_secret_access_key:
            session_kwargs['aws_access_key_id'] = aws_access_key_id
            session_kwargs['aws_secret_access_key'] = aws_secret_access_key

        self.session = boto3.Session(**session_kwargs)

        client_kwargs = {}
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url

        self.s3_client = self.session.client('s3', **client_kwargs)

        logger.info(f"S3ParquetSource initialized: bucket={bucket}, region={self.region}")

    def list_files(
        self,
        prefix: str = "",
        suffix: str = ".parquet",
        max_keys: int = 1000
    ) -> List[str]:
        """
        List parquet files in S3 bucket.

        Args:
            prefix: Key prefix to filter files
            suffix: File suffix (default: .parquet)
            max_keys: Maximum number of files to return

        Returns:
            List of S3 keys
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_keys}
            )

            files = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith(suffix):
                            files.append(key)

            logger.info(f"Found {len(files)} parquet files in s3://{self.bucket}/{prefix}")
            return files

        except ClientError as e:
            logger.error(f"Error listing S3 files: {e}")
            return []

    def read_parquet(
        self,
        key: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List[tuple]] = None
    ) -> pd.DataFrame:
        """
        Read a single parquet file from S3.

        Args:
            key: S3 object key
            columns: Optional list of columns to read
            filters: Optional parquet filters

        Returns:
            DataFrame with parquet data
        """
        try:
            # Download file to memory
            obj = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            buffer = io.BytesIO(obj['Body'].read())

            # Read parquet
            df = pd.read_parquet(
                buffer,
                columns=columns,
                filters=filters,
                engine='pyarrow'
            )

            logger.info(f"Read {len(df)} rows from s3://{self.bucket}/{key}")
            return df

        except ClientError as e:
            logger.error(f"Error reading parquet from S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing parquet file: {e}")
            raise

    def read_parquet_batch(
        self,
        keys: List[str],
        columns: Optional[List[str]] = None,
        batch_size: int = 10
    ) -> Iterator[pd.DataFrame]:
        """
        Read multiple parquet files in batches.

        Args:
            keys: List of S3 keys
            columns: Optional columns to read
            batch_size: Number of files to read per batch

        Yields:
            DataFrames for each batch
        """
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i:i + batch_size]
            dfs = []

            for key in batch_keys:
                try:
                    df = self.read_parquet(key, columns=columns)
                    dfs.append(df)
                except Exception as e:
                    logger.error(f"Failed to read {key}: {e}")
                    continue

            if dfs:
                # Concatenate batch
                batch_df = pd.concat(dfs, ignore_index=True)
                logger.info(f"Batch {i//batch_size + 1}: {len(batch_df)} rows from {len(dfs)} files")
                yield batch_df

    def read_quotes_parquet(self, key: str) -> List[Dict]:
        """
        Read stock quotes from parquet file.

        Expected schema:
        - ticker: string
        - timestamp: datetime64
        - price: float64
        - volume: int64
        - bid: float64 (optional)
        - ask: float64 (optional)

        Args:
            key: S3 object key

        Returns:
            List of quote dictionaries
        """
        df = self.read_parquet(key)

        # Normalize schema
        quotes = []
        for _, row in df.iterrows():
            quote = {
            quote = {
                'ticker': row.get('ticker') or row.get('symbol'),
                'timestamp': pd.to_datetime(row.get('timestamp')),
                'price': float(row.get('price', 0)),
                'volume': int(row.get('volume', 0)),
                'bid': float(row['bid']) if pd.notna(row.get('bid')) else None,
                'ask': float(row['ask']) if pd.notna(row.get('ask')) else None,
                'bid_size': int(row.get('bid_size', 0)) if pd.notna(row.get('bid_size')) else None,
                'ask_size': int(row.get('ask_size', 0)) if pd.notna(row.get('ask_size')) else None,
                'source': 's3_parquet',
                'metadata': {'s3_key': key}
            }
            quotes.append(quote)

        return quotes

    def read_ohlcv_parquet(self, key: str) -> List[Dict]:
        """
        Read OHLCV bars from parquet file.

        Expected schema:
        - ticker: string
        - date: date or datetime64
        - open: float64
        - high: float64
        - low: float64
        - close: float64
        - volume: int64

        Args:
            key: S3 object key

        Returns:
            List of OHLCV dictionaries
        """
        df = self.read_parquet(key)

        bars = []
        for _, row in df.iterrows():
            bar = {
                'ticker': row.get('ticker') or row.get('symbol'),
                'date': pd.to_datetime(row['date']).date(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row.get('volume', 0)),
                'adj_close': float(row['adj_close']) if pd.notna(row.get('adj_close')) else None,
                'source': 's3_parquet'
            }
            bars.append(bar)

        return bars

    def read_news_parquet(self, key: str) -> List[Dict]:
        """
        Read news articles from parquet file.

        Expected schema:
        - headline: string
        - content: string (optional)
        - source: string
        - published_at: datetime64
        - tickers: list<string> or string (comma-separated)
        - sentiment_score: float64 (optional)

        Args:
            key: S3 object key

        Returns:
            List of news article dictionaries
        """
        df = self.read_parquet(key)

        articles = []
        for _, row in df.iterrows():
            # Parse tickers
            tickers = row.get('tickers', [])
            if isinstance(tickers, str):
                tickers = [t.strip() for t in tickers.split(',')]
            elif pd.isna(tickers):
                tickers = []

            article = {
            article = {
                'headline': row.get('headline'),
                'content': row.get('content'),
                'summary': row.get('summary'),
                'source': row.get('source', 's3_parquet'),
                'url': row.get('url'),
                'published_at': pd.to_datetime(row.get('published_at')),
                'tickers': tickers,
                'sentiment_score': float(row['sentiment_score']) if pd.notna(row.get('sentiment_score')) else None,
                'sentiment_label': row.get('sentiment_label'),
                'metadata': {'s3_key': key}
            }
            articles.append(article)

        return articles

    def upload_parquet(
        self,
        df: pd.DataFrame,
        key: str,
        compression: str = 'snappy'
    ) -> bool:
        """
        Upload DataFrame as parquet to S3.

        Args:
            df: DataFrame to upload
            key: S3 destination key
            compression: Compression algorithm (snappy, gzip, brotli, none)

        Returns:
            True if successful
        """
        try:
            # Write to buffer
            buffer = io.BytesIO()
            df.to_parquet(
                buffer,
                engine='pyarrow',
                compression=compression,
                index=False
            )
            buffer.seek(0)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType='application/octet-stream'
            )

            logger.info(f"Uploaded {len(df)} rows to s3://{self.bucket}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return False

    def get_file_metadata(self, key: str) -> Optional[Dict]:
        """
        Get metadata for an S3 object.

        Args:
            key: S3 object key

        Returns:
            Metadata dictionary or None
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'etag': response['ETag'],
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            logger.error(f"Error getting file metadata: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if S3 connection is healthy.

        Returns:
            True if connection is healthy
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            return True
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"S3 health check failed: {e}")
            return False


class S3ParquetETL:
    """
    ETL pipeline for importing S3 parquet data into Colosseum data lake.
    """

    def __init__(
        self,
        s3_source: S3ParquetSource,
        db_client,  # DataLakeClient
        batch_size: int = 1000
    ):
        """
        Initialize ETL pipeline.

        Args:
            s3_source: S3ParquetSource instance
            db_client: DataLakeClient instance
            batch_size: Number of rows per database insert batch
        """
        self.s3_source = s3_source
        self.db_client = db_client
        self.batch_size = batch_size

        logger.info("S3ParquetETL initialized")

    def import_quotes(
        self,
        keys: List[str],
        deduplicate: bool = True
    ) -> int:
        """
        Import stock quotes from parquet files.

        Args:
            keys: List of S3 keys
            deduplicate: Remove duplicates before inserting

        Returns:
            Number of quotes imported
        """
        total_imported = 0

        for key in keys:
            try:
                quotes = self.s3_source.read_quotes_parquet(key)

                # Deduplicate if requested
                if deduplicate:
                    # Group by ticker+timestamp, keep first
                    seen = set()
                    unique_quotes = []
                    for quote in quotes:
                        key_tuple = (quote['ticker'], quote['timestamp'])
                        if key_tuple not in seen:
                            seen.add(key_tuple)
                            unique_quotes.append(quote)
                    quotes = unique_quotes

                # Insert in batches
                for i in range(0, len(quotes), self.batch_size):
                    batch = quotes[i:i + self.batch_size]
                    count = self.db_client.insert_quotes(batch)
                    total_imported += count

                logger.info(f"Imported {len(quotes)} quotes from {key}")

            except Exception as e:
                logger.error(f"Failed to import quotes from {key}: {e}")
                continue

        return total_imported

    def import_ohlcv(self, keys: List[str]) -> int:
        """
        Import OHLCV bars from parquet files.

        Args:
            keys: List of S3 keys

        Returns:
            Number of bars imported
        """
        total_imported = 0

        for key in keys:
            try:
                bars = self.s3_source.read_ohlcv_parquet(key)

                # Insert with upsert (ON CONFLICT UPDATE)
                query = """
                INSERT INTO market_data.daily_bars
                    (ticker, date, open, high, low, close, volume, adj_close, source)
                VALUES
                    (:ticker, :date, :open, :high, :low, :close, :volume, :adj_close, :source)
                ON CONFLICT (ticker, date, source) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    adj_close = EXCLUDED.adj_close
                """

                count = self.db_client.execute_many(query, bars)
                total_imported += count

                logger.info(f"Imported {count} bars from {key}")

            except Exception as e:
                logger.error(f"Failed to import OHLCV from {key}: {e}")
                continue

        return total_imported

    def import_news(self, keys: List[str]) -> int:
        """
        Import news articles from parquet files.

        Args:
            keys: List of S3 keys

        Returns:
            Number of articles imported
        """
        total_imported = 0

        for key in keys:
            try:
                articles = self.s3_source.read_news_parquet(key)
                count = self.db_client.insert_news(articles)
                total_imported += count

                logger.info(f"Imported {count} articles from {key}")

            except Exception as e:
                logger.error(f"Failed to import news from {key}: {e}")
                continue

        return total_imported

    def import_all(
        self,
        prefix: str = "",
        data_type: str = "auto"
    ) -> Dict[str, int]:
        """
        Import all parquet files matching a prefix.

        Args:
            prefix: S3 key prefix
            data_type: Type of data (auto, quotes, ohlcv, news)

        Returns:
            Dictionary with import statistics
        """
        stats = {
            'quotes': 0,
            'ohlcv': 0,
            'news': 0,
            'files_processed': 0,
            'files_failed': 0
        }

        files = self.s3_source.list_files(prefix=prefix)

        for key in files:
            try:
                # Auto-detect data type from path
                if data_type == "auto":
                    if 'quote' in key.lower() or 'tick' in key.lower():
                        detected_type = 'quotes'
                    elif 'ohlc' in key.lower() or 'bar' in key.lower() or 'daily' in key.lower():
                        detected_type = 'ohlcv'
                    elif 'news' in key.lower() or 'article' in key.lower():
                        detected_type = 'news'
                    else:
                        logger.warning(f"Could not auto-detect type for {key}, skipping")
                        continue
                else:
                    detected_type = data_type

                # Import based on type
                if detected_type == 'quotes':
                    count = self.import_quotes([key])
                    stats['quotes'] += count
                elif detected_type == 'ohlcv':
                    count = self.import_ohlcv([key])
                    stats['ohlcv'] += count
                elif detected_type == 'news':
                    count = self.import_news([key])
                    stats['news'] += count

                stats['files_processed'] += 1

            except Exception as e:
                logger.error(f"Failed to process {key}: {e}")
                stats['files_failed'] += 1
                continue

        return stats
