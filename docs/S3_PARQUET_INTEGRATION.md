# S3 Parquet Integration for Colosseum

## Overview

Colosseum supports importing market data from S3 parquet files, enabling:
- **Bulk historical data imports** from cloud storage
- **Integration with existing data lakes** (AWS, MinIO, Backblaze B2)
- **ETL pipelines** from external data sources
- **Efficient data transfer** using columnar parquet format

## Architecture

```
┌─────────────────────────────────────────┐
│  S3-Compatible Storage                  │
│  ├─ AWS S3                              │
│  ├─ MinIO (self-hosted)                 │
│  ├─ Backblaze B2                        │
│  └─ Google Cloud Storage (S3 compat)    │
└──────────┬──────────────────────────────┘
           │
           │ Parquet files
           │ (quotes/, ohlcv/, news/)
           ↓
┌──────────────────────────────────────────┐
│  S3ParquetSource                         │
│  - List files                            │
│  - Read parquet                          │
│  - Schema normalization                  │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│  S3ParquetETL                            │
│  - Batch processing                      │
│  - Deduplication                         │
│  - Data validation                       │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│  CuratorAgent.import_from_s3()           │
│  - Auto-detection                        │
│  - Statistics tracking                   │
│  - Error handling                        │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│  PostgreSQL Data Lake                    │
│  - market_data.stock_quotes              │
│  - market_data.daily_bars                │
│  - market_data.news_articles             │
└──────────────────────────────────────────┘
```

## Prerequisites

Install S3 dependencies:

```bash
pip install boto3 pyarrow pandas
```

Or use the full requirements:

```bash
pip install -r colosseum/requirements.txt
```

## Configuration

### 1. Add S3 Sources to Configuration

Edit `~/.config/colosseum/config.yaml`:

```yaml
s3:
  sources:
    # AWS S3 production data lake
    prod-datalake:
      bucket: my-company-market-data
      region: us-east-1
      # Credentials from environment or IAM role
      # aws_access_key_id: ${AWS_ACCESS_KEY_ID}
      # aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}

    # MinIO local storage
    local-minio:
      bucket: colosseum-local
      region: us-east-1
      endpoint_url: http://localhost:9000
      aws_access_key_id: minioadmin
      aws_secret_access_key: minioadmin

    # Backblaze B2
    b2-storage:
      bucket: colosseum-backup
      region: us-west-000
      endpoint_url: https://s3.us-west-000.backblazeb2.com
      aws_access_key_id: ${B2_KEY_ID}
      aws_secret_access_key: ${B2_APPLICATION_KEY}
```

### 2. Set Environment Variables

```bash
# AWS credentials
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Or for B2
export B2_KEY_ID=your_key_id
export B2_APPLICATION_KEY=your_app_key
```

### 3. Test Connection

```bash
# Check S3 sources
python -m colosseum.cli.curator health

# List files in S3
python -m colosseum.cli.curator s3-list prod-datalake --prefix market_data/
```

## Parquet File Schema

### Stock Quotes

```python
# Required columns:
{
    'ticker': 'AAPL',           # or 'symbol'
    'timestamp': datetime,       # datetime64[ns]
    'price': 150.25,            # float64
    'volume': 1000000,          # int64

    # Optional:
    'bid': 150.20,              # float64
    'ask': 150.30,              # float64
    'bid_size': 100,            # int64
    'ask_size': 100,            # int64
}
```

**Example parquet structure**:
```
s3://my-bucket/market_data/quotes/2024/01/15/AAPL_20240115.parquet
```

### OHLCV Bars

```python
{
    'ticker': 'AAPL',           # or 'symbol'
    'date': '2024-01-15',       # date or datetime64[ns]
    'open': 150.00,             # float64
    'high': 152.00,             # float64
    'low': 149.50,              # float64
    'close': 151.00,            # float64
    'volume': 50000000,         # int64

    # Optional:
    'adj_close': 151.00,        # float64 (adjusted for splits)
}
```

**Example parquet structure**:
```
s3://my-bucket/market_data/ohlcv/daily/2024/AAPL_2024.parquet
```

### News Articles

```python
{
    'headline': 'Apple announces...',   # string
    'content': 'Full article...',       # string (optional)
    'summary': 'Brief summary...',      # string (optional)
    'source': 'Reuters',                # string
    'published_at': datetime,           # datetime64[ns]
    'url': 'https://...',               # string (optional)

    # Tickers can be list or comma-separated string
    'tickers': ['AAPL', 'MSFT'],       # list<string> or 'AAPL,MSFT'

    # Optional sentiment:
    'sentiment_score': 0.75,            # float64 (-1.0 to 1.0)
    'sentiment_label': 'positive',      # string
}
```

**Example parquet structure**:
```
s3://my-bucket/market_data/news/2024/01/news_20240115.parquet
```

## Usage

### CLI Commands

#### 1. List S3 Files

```bash
# List all parquet files
python -m colosseum.cli.curator s3-list prod-datalake

# List with prefix
python -m colosseum.cli.curator s3-list prod-datalake --prefix market_data/quotes/

# Limit results
python -m colosseum.cli.curator s3-list prod-datalake --prefix market_data/ --limit 50
```

#### 2. Import Data

```bash
# Auto-detect and import all data types
python -m colosseum.cli.curator s3-import prod-datalake --prefix market_data/

# Import only quotes
python -m colosseum.cli.curator s3-import prod-datalake --prefix market_data/quotes/ --type quotes

# Import OHLCV data
python -m colosseum.cli.curator s3-import prod-datalake --prefix market_data/ohlcv/ --type ohlcv

# Import news
python -m colosseum.cli.curator s3-import prod-datalake --prefix market_data/news/ --type news
```

### Programmatic Usage

```python
from colosseum.agents.curator_agent import CuratorAgent
from colosseum.config import load_config

# Initialize curator
config = load_config()
curator = CuratorAgent(config=config)

# List files
files = curator.list_s3_files('prod-datalake', prefix='market_data/quotes/')
print(f"Found {len(files)} files")

# Import all data from a prefix
stats = curator.import_from_s3(
    source_name='prod-datalake',
    prefix='market_data/2024/01/',
    data_type='auto'
)

print(f"Imported: {stats['quotes']} quotes, {stats['ohlcv']} bars, {stats['news']} articles")

# Import specific file types
count = curator.import_s3_quotes(
    source_name='prod-datalake',
    keys=['market_data/quotes/2024/01/15/AAPL_20240115.parquet']
)
print(f"Imported {count} quotes")
```

### Direct S3ParquetSource Usage

For more control:

```python
from colosseum.data_sources.s3_parquet import S3ParquetSource, S3ParquetETL
from colosseum.database.client import get_client

# Initialize S3 source
s3_source = S3ParquetSource(
    bucket='my-company-market-data',
    region='us-east-1'
)

# List files
files = s3_source.list_files(prefix='market_data/quotes/')

# Read a single file
df = s3_source.read_parquet(files[0])
print(f"Read {len(df)} rows")

# Read specific columns
df = s3_source.read_parquet(
    files[0],
    columns=['ticker', 'timestamp', 'price', 'volume']
)

# Read in batches
for batch_df in s3_source.read_parquet_batch(files, batch_size=10):
    print(f"Processing batch with {len(batch_df)} rows")

# Use ETL pipeline
db_client = get_client()
etl = S3ParquetETL(s3_source, db_client)

# Import quotes
count = etl.import_quotes(files[:10])
print(f"Imported {count} quotes")

# Import with deduplication
count = etl.import_quotes(files, deduplicate=True)
```

## Data Organization Best Practices

### Recommended S3 Structure

```
s3://my-bucket/
├── market_data/
│   ├── quotes/
│   │   └── 2024/
│   │       └── 01/
│   │           ├── 15/
│   │           │   ├── AAPL_20240115_quotes.parquet
│   │           │   ├── GOOGL_20240115_quotes.parquet
│   │           │   └── ...
│   │           └── ...
│   ├── ohlcv/
│   │   ├── daily/
│   │   │   └── 2024/
│   │   │       ├── AAPL_2024_daily.parquet
│   │   │       └── ...
│   │   └── intraday/
│   │       └── 2024/01/
│   │           └── AAPL_20240115_1min.parquet
│   └── news/
│       └── 2024/01/
│           ├── news_20240115.parquet
│           └── ...
└── metadata/
    ├── tickers.parquet
    └── exchanges.parquet
```

### File Naming Conventions

- **Use partitioning**: `year/month/day/` for efficient querying
- **Include data type**: `quotes`, `ohlcv`, `news`
- **Add ticker symbols**: `AAPL_20240115_quotes.parquet`
- **Use dates**: `YYYYMMDD` format
- **Compression**: Use `snappy` (default) for good balance

### Parquet Optimization

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Create optimized parquet file
df = pd.DataFrame({...})

# Write with compression and row groups
df.to_parquet(
    'output.parquet',
    engine='pyarrow',
    compression='snappy',  # or 'gzip', 'brotli'
    index=False,
    row_group_size=100000  # Optimize for reading
)

# Or use PyArrow directly for more control
table = pa.Table.from_pandas(df)
pq.write_table(
    table,
    'output.parquet',
    compression='snappy',
    use_dictionary=True,  # Smaller files for repeated values
    write_statistics=True  # Enable predicate pushdown
)
```

## Performance Considerations

### Batch Sizes

```python
# Adjust batch size based on file size and memory
etl = S3ParquetETL(
    s3_source,
    db_client,
    batch_size=5000  # rows per database insert
)
```

### Parallel Processing

For large imports, use multiprocessing:

```python
from multiprocessing import Pool

def import_file(key):
    curator = CuratorAgent()
    return curator.import_s3_quotes('prod-datalake', [key])

files = curator.list_s3_files('prod-datalake', prefix='market_data/quotes/')

# Import in parallel
with Pool(4) as pool:
    results = pool.map(import_file, files)

total = sum(results)
print(f"Imported {total} quotes from {len(files)} files")
```

### Memory Management

For very large files:

```python
# Read in chunks
for chunk_df in pd.read_parquet(
    file_path,
    engine='pyarrow',
    chunksize=10000
):
    # Process chunk
    curator.db_client.insert_quotes(chunk_df.to_dict('records'))
```

## Monitoring

### Check Import Statistics

```bash
# View curator stats
python -m colosseum.cli.curator stats
```

Output includes:
- `s3_imports`: Total S3 import operations
- `s3_import_failures`: Failed imports
- `s3_quotes_imported`: Total quotes from S3
- `s3_ohlcv_imported`: Total bars from S3
- `s3_news_imported`: Total articles from S3

### Database Verification

```sql
-- Check imported data
SELECT source, COUNT(*) as records
FROM market_data.stock_quotes
WHERE source = 's3_parquet'
GROUP BY source;

-- Check data quality
SELECT
    ticker,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest,
    COUNT(*) as records
FROM market_data.stock_quotes
WHERE source = 's3_parquet'
GROUP BY ticker
ORDER BY ticker;
```

## Troubleshooting

### Import Failures

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check S3 connectivity
s3_source = S3ParquetSource(bucket='my-bucket')
healthy = s3_source.health_check()
print(f"S3 health: {healthy}")

# Verify file exists
metadata = s3_source.get_file_metadata('path/to/file.parquet')
if metadata:
    print(f"File size: {metadata['size']} bytes")
```

### Schema Mismatches

If parquet schema doesn't match expected format:

```python
# Read with pandas to inspect
import pandas as pd
df = pd.read_parquet('s3://bucket/file.parquet')
print(df.dtypes)
print(df.head())

# Transform before importing
df = df.rename(columns={'symbol': 'ticker'})
df['timestamp'] = pd.to_datetime(df['timestamp'])
```

### AWS Credentials

```bash
# Test AWS credentials
aws s3 ls s3://my-bucket/

# Or with boto3
import boto3
s3 = boto3.client('s3')
response = s3.list_objects_v2(Bucket='my-bucket', MaxKeys=10)
print(f"Found {len(response.get('Contents', []))} objects")
```

## Examples

See `examples/s3_import_example.py` for complete examples:
- Importing historical data
- Batch processing
- Custom transformations
- Error handling

## Security Considerations

1. **Use IAM Roles** when running on AWS EC2/ECS instead of access keys
2. **Restrict bucket access** with IAM policies
3. **Enable encryption** at rest (S3 SSE)
4. **Use VPC endpoints** for private S3 access
5. **Rotate credentials** regularly
6. **Audit access** with CloudTrail

## Cost Optimization

- **Use compression**: Snappy or Gzip
- **Partition data**: Reduce S3 list operations
- **Lifecycle policies**: Move old data to Glacier
- **Use S3 Intelligent-Tiering** for automatic cost optimization
- **Monitor data transfer**: Use S3 Transfer Acceleration if needed

## References

- [Apache Parquet Documentation](https://parquet.apache.org/docs/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [PyArrow Parquet Guide](https://arrow.apache.org/docs/python/parquet.html)
- [Boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)

## Support

For issues or questions:
- GitHub Issues: https://github.com/davdunc/colosseum/issues
- See examples: `examples/s3_import_example.py`
