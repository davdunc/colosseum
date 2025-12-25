-- Colosseum Data Lake Initialization Script
-- This script sets up the database schema for the stock data lake

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create schema for organized data
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS agent_data;
CREATE SCHEMA IF NOT EXISTS metadata;

-- ============================================================================
-- MARKET DATA SCHEMA
-- ============================================================================

-- Real-time stock quotes
CREATE TABLE IF NOT EXISTS market_data.stock_quotes (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price NUMERIC(12,4),
    volume BIGINT,
    bid NUMERIC(12,4),
    ask NUMERIC(12,4),
    bid_size INTEGER,
    ask_size INTEGER,
    source VARCHAR(50) NOT NULL, -- 'ib', 'etrade', 'dastrader'
    metadata JSONB, -- Additional source-specific data
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_quotes_ticker_ts
    ON market_data.stock_quotes(ticker, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_created
    ON market_data.stock_quotes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_source
    ON market_data.stock_quotes(source, timestamp DESC);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable(
    'market_data.stock_quotes',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create continuous aggregate for 1-minute OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data.ohlcv_1min
WITH (timescaledb.continuous) AS
SELECT
    ticker,
    time_bucket('1 minute', timestamp) AS bucket,
    FIRST(price, timestamp) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, timestamp) AS close,
    SUM(volume) AS volume,
    COUNT(*) AS tick_count
FROM market_data.stock_quotes
GROUP BY ticker, bucket
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('market_data.ohlcv_1min',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- Historical OHLCV data (daily)
CREATE TABLE IF NOT EXISTS market_data.daily_bars (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(12,4) NOT NULL,
    high NUMERIC(12,4) NOT NULL,
    low NUMERIC(12,4) NOT NULL,
    close NUMERIC(12,4) NOT NULL,
    volume BIGINT,
    adj_close NUMERIC(12,4), -- Adjusted close for splits/dividends
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, date, source)
);

CREATE INDEX IF NOT EXISTS idx_daily_ticker_date
    ON market_data.daily_bars(ticker, date DESC);

-- News articles with vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS market_data.news_articles (
    id BIGSERIAL PRIMARY KEY,
    headline TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    source VARCHAR(100) NOT NULL,
    url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    tickers TEXT[], -- Array of related ticker symbols
    sentiment_score NUMERIC(3,2), -- -1.0 to 1.0
    sentiment_label VARCHAR(20), -- 'positive', 'negative', 'neutral'
    embedding vector(1536), -- OpenAI ada-002 embeddings
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_published
    ON market_data.news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_tickers
    ON market_data.news_articles USING GIN(tickers);
CREATE INDEX IF NOT EXISTS idx_news_source
    ON market_data.news_articles(source, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_embedding
    ON market_data.news_articles USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================================
-- AGENT DATA SCHEMA
-- ============================================================================

-- Agent decisions and recommendations
CREATE TABLE IF NOT EXISTS agent_data.decisions (
    id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50), -- 'research', 'portfolio', 'datalake', etc.
    ticker VARCHAR(10),
    action VARCHAR(20), -- 'BUY', 'SELL', 'HOLD', 'ANALYZE'
    confidence NUMERIC(3,2), -- 0.0 to 1.0
    reasoning TEXT NOT NULL,
    data_sources TEXT[], -- Which MCP servers were used
    metadata JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id UUID -- To group related decisions
);

CREATE INDEX IF NOT EXISTS idx_decisions_agent
    ON agent_data.decisions(agent_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_ticker
    ON agent_data.decisions(ticker, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_session
    ON agent_data.decisions(session_id, timestamp DESC);

-- Agent communication logs
CREATE TABLE IF NOT EXISTS agent_data.agent_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    log_level VARCHAR(20), -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    message TEXT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_session
    ON agent_data.agent_logs(session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_agent
    ON agent_data.agent_logs(agent_name, timestamp DESC);

-- Investment committee votes
CREATE TABLE IF NOT EXISTS agent_data.committee_votes (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    proposal TEXT NOT NULL,
    votes JSONB NOT NULL, -- {"agent_name": "vote", ...}
    consensus VARCHAR(20), -- 'unanimous', 'majority', 'split', 'no_consensus'
    final_decision VARCHAR(20), -- 'APPROVED', 'REJECTED', 'DEFERRED'
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_votes_session
    ON agent_data.committee_votes(session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_votes_ticker
    ON agent_data.committee_votes(ticker, timestamp DESC);

-- ============================================================================
-- METADATA SCHEMA
-- ============================================================================

-- Ticker metadata and company information
CREATE TABLE IF NOT EXISTS metadata.tickers (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    description TEXT,
    headquarters VARCHAR(200),
    employees INTEGER,
    website VARCHAR(500),
    metadata JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickers_sector
    ON metadata.tickers(sector);
CREATE INDEX IF NOT EXISTS idx_tickers_industry
    ON metadata.tickers(industry);

-- Data source health and status
CREATE TABLE IF NOT EXISTS metadata.mcp_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(50) UNIQUE NOT NULL,
    source_type VARCHAR(50), -- 'broker', 'news', 'ticker'
    status VARCHAR(20), -- 'active', 'degraded', 'down'
    last_successful_fetch TIMESTAMPTZ,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    metadata JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data quality metrics
CREATE TABLE IF NOT EXISTS metadata.data_quality_metrics (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC,
    metadata JSONB,
    measured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_table
    ON metadata.data_quality_metrics(table_name, measured_at DESC);

-- ============================================================================
-- RETENTION POLICIES
-- ============================================================================

-- Drop old raw quote data after 90 days (keep aggregates)
SELECT add_retention_policy(
    'market_data.stock_quotes',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to search news by semantic similarity
CREATE OR REPLACE FUNCTION market_data.search_news_by_embedding(
    query_embedding vector(1536),
    match_count integer DEFAULT 10,
    similarity_threshold float DEFAULT 0.7
)
RETURNS TABLE (
    id bigint,
    headline text,
    summary text,
    published_at timestamptz,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.id,
        n.headline,
        n.summary,
        n.published_at,
        1 - (n.embedding <=> query_embedding) AS similarity
    FROM market_data.news_articles n
    WHERE 1 - (n.embedding <=> query_embedding) > similarity_threshold
    ORDER BY n.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest quote for a ticker
CREATE OR REPLACE FUNCTION market_data.get_latest_quote(p_ticker VARCHAR)
RETURNS TABLE (
    ticker VARCHAR,
    timestamp TIMESTAMPTZ,
    price NUMERIC,
    volume BIGINT,
    bid NUMERIC,
    ask NUMERIC,
    source VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.ticker,
        q.timestamp,
        q.price,
        q.volume,
        q.bid,
        q.ask,
        q.source
    FROM market_data.stock_quotes q
    WHERE q.ticker = p_ticker
    ORDER BY q.timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANTS (adjust as needed)
-- ============================================================================

-- Grant appropriate permissions to the colosseum user
GRANT USAGE ON SCHEMA market_data TO colosseum;
GRANT USAGE ON SCHEMA agent_data TO colosseum;
GRANT USAGE ON SCHEMA metadata TO colosseum;

GRANT ALL ON ALL TABLES IN SCHEMA market_data TO colosseum;
GRANT ALL ON ALL TABLES IN SCHEMA agent_data TO colosseum;
GRANT ALL ON ALL TABLES IN SCHEMA metadata TO colosseum;

GRANT ALL ON ALL SEQUENCES IN SCHEMA market_data TO colosseum;
GRANT ALL ON ALL SEQUENCES IN SCHEMA agent_data TO colosseum;
GRANT ALL ON ALL SEQUENCES IN SCHEMA metadata TO colosseum;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert some initial MCP sources
INSERT INTO metadata.mcp_sources (source_name, source_type, status)
VALUES
    ('interactive_brokers', 'broker', 'active'),
    ('etrade', 'broker', 'active'),
    ('dastrader', 'broker', 'active'),
    ('etrade_news', 'news', 'active')
ON CONFLICT (source_name) DO NOTHING;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Colosseum Data Lake initialized successfully!';
    RAISE NOTICE 'Schemas created: market_data, agent_data, metadata';
    RAISE NOTICE 'TimescaleDB hypertables configured for time-series data';
    RAISE NOTICE 'pgvector extension enabled for semantic search';
END $$;
