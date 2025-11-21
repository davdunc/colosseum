# Colosseum PostgreSQL Data Lake - Quadlet Deployment

This directory contains Podman Quadlet configurations for deploying the Colosseum data lake PostgreSQL database using systemd-native container management.

## Overview

The deployment follows **Major Hayden's approach** to using Quadlets for container orchestration with systemd. This provides:

- **Systemd integration**: Containers managed as native systemd services
- **Automatic restarts**: Systemd handles container lifecycle
- **Resource limits**: CPU and memory constraints enforced by systemd
- **Logging**: Integrated with journald for centralized logging
- **Security**: Rootless containers with podman secrets for credentials
- **Networking**: Isolated container network for service communication

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Systemd (User or System)                           │
│  ├─ colosseum-network.service                       │
│  │  └─ Creates: colosseum bridge network            │
│  ├─ colosseum-postgres-data.service                 │
│  │  └─ Creates: persistent volume                   │
│  └─ colosseum-postgres.service                      │
│     └─ Container: pgvector/pgvector:pg16            │
│        ├─ Port: 5432                                 │
│        ├─ Network: colosseum                         │
│        ├─ Volume: colosseum-postgres-data            │
│        └─ Extensions: pgvector, timescaledb          │
└─────────────────────────────────────────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `colosseum-network.network` | Quadlet network definition |
| `colosseum-postgres-data.volume` | Quadlet volume definition |
| `colosseum-postgres.container` | Quadlet container definition |
| `deploy.sh` | Deployment script with podman secrets |
| `cleanup.sh` | Cleanup script to remove all resources |
| `init-db.sql` | Database schema initialization |
| `init-schema.sh` | Script to initialize database schema |
| `config.yaml.example` | Example configuration file |

## Prerequisites

- **Fedora 39+** (or RHEL 9+)
- **Podman 4.6+** with quadlet support
- **systemd** (user or system mode)
- **OpenSSL** (for generating secrets)

## Quick Start

### 1. Deploy the Database

```bash
cd quadlets
./deploy.sh
```

This script will:
- Create podman secret for database password
- Install quadlet files to systemd directory
- Start PostgreSQL container with systemd
- Wait for database to be ready

### 2. Initialize the Schema

```bash
./init-schema.sh
```

This creates:
- Three schemas: `market_data`, `agent_data`, `metadata`
- Tables for quotes, OHLCV, news, agent decisions
- TimescaleDB hypertables for time-series data
- pgvector indexes for semantic search
- Helper functions and retention policies

### 3. Configure Colosseum

Copy the example config and customize:

```bash
mkdir -p ~/.config/colosseum
cp config.yaml.example ~/.config/colosseum/config.yaml
```

Edit the database password or set environment variable:

```bash
export DB_PASSWORD=$(podman secret inspect colosseum-db-password --showsecret)
```

### 4. Verify Installation

```bash
# Check service status
systemctl --user status colosseum-postgres.service

# View logs
journalctl --user -u colosseum-postgres.service -f

# Connect to database
podman exec -it colosseum-postgres psql -U colosseum -d colosseum_data_lake
```

## Database Schema

### market_data Schema

- **stock_quotes**: Real-time tick data (TimescaleDB hypertable)
- **ohlcv_1min**: 1-minute OHLCV aggregates (continuous aggregate)
- **daily_bars**: Historical daily OHLCV data
- **news_articles**: News with pgvector embeddings for semantic search

### agent_data Schema

- **decisions**: Agent trading decisions and recommendations
- **agent_logs**: Agent communication logs
- **committee_votes**: Investment committee voting records

### metadata Schema

- **tickers**: Company and ticker metadata
- **mcp_sources**: Data source health monitoring
- **data_quality_metrics**: Data quality tracking

## Database Features

### TimescaleDB Integration

- **Hypertables**: Automatic time-based partitioning
- **Continuous Aggregates**: Pre-computed OHLCV bars
- **Retention Policies**: Automatic data cleanup (90 days for raw ticks)
- **Compression**: Efficient storage for historical data

### pgvector for AI/ML

- **Embedding Storage**: 1536-dimensional vectors for news articles
- **Similarity Search**: Semantic search using cosine similarity
- **IVFFlat Index**: Fast approximate nearest neighbor search

## Management Commands

### Service Management

```bash
# Start/stop/restart
systemctl --user start colosseum-postgres.service
systemctl --user stop colosseum-postgres.service
systemctl --user restart colosseum-postgres.service

# Enable/disable auto-start
systemctl --user enable colosseum-postgres.service
systemctl --user disable colosseum-postgres.service

# View status
systemctl --user status colosseum-postgres.service
```

### Database Access

```bash
# Interactive psql shell
podman exec -it colosseum-postgres psql -U colosseum -d colosseum_data_lake

# Run SQL file
podman exec -i colosseum-postgres psql -U colosseum -d colosseum_data_lake < query.sql

# Backup database
podman exec colosseum-postgres pg_dump -U colosseum -d colosseum_data_lake > backup.sql

# Restore database
podman exec -i colosseum-postgres psql -U colosseum -d colosseum_data_lake < backup.sql
```

### Monitoring

```bash
# View logs
journalctl --user -u colosseum-postgres.service -f

# Check health
podman exec colosseum-postgres pg_isready -U colosseum

# View connections
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='colosseum_data_lake';"

# Database size
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT pg_size_pretty(pg_database_size('colosseum_data_lake'));"
```

## Automatic Updates

The container is labeled for automatic updates with podman auto-update:

```bash
# Enable auto-update timer
systemctl --user enable --now podman-auto-update.timer

# Manual update check
podman auto-update

# View update logs
journalctl --user -u podman-auto-update.service
```

See [Major Hayden's blog post](https://major.io/p/podman-quadlet-automatic-updates/) for details.

## Security Best Practices

1. **Rootless Containers**: Run as non-root user with `systemctl --user`
2. **Podman Secrets**: Never store passwords in plain text
3. **Network Isolation**: Use dedicated container network
4. **Resource Limits**: Memory and CPU constraints prevent resource exhaustion
5. **Read-Only Root**: Container root filesystem is read-only (except volumes)
6. **Firewall**: Only expose port 5432 if external access needed

## Production Considerations

### For Production Deployment:

1. **Remove Port Publishing** (if internal only):
   - Comment out `PublishPort=5432:5432` in the .container file

2. **Use System-Level Quadlets**:
   - Deploy to `/etc/containers/systemd/` instead of `~/.config/`
   - Use `systemctl` instead of `systemctl --user`

3. **Configure SSL/TLS**:
   - Generate SSL certificates
   - Mount certificates as volumes
   - Update postgresql.conf for SSL

4. **Increase Resources**:
   - Adjust `Memory=` and `CPUShares=` in .container file
   - Configure PostgreSQL shared_buffers, work_mem, etc.

5. **Set Up Backups**:
   - Use systemd timers for automated backups
   - Store backups on separate volume/storage

6. **Monitor Performance**:
   - Enable pg_stat_statements extension
   - Use Prometheus postgres_exporter
   - Set up alerting with AlertManager

## Troubleshooting

### Container won't start

```bash
# Check systemd service status
systemctl --user status colosseum-postgres.service

# View full logs
journalctl --user -u colosseum-postgres.service --no-pager

# Check podman directly
podman ps -a
podman logs colosseum-postgres
```

### Can't connect to database

```bash
# Verify container is running
podman ps | grep colosseum-postgres

# Check health
podman exec colosseum-postgres pg_isready -U colosseum

# Test connection
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "SELECT 1"

# Check port binding
podman port colosseum-postgres
```

### Permission denied errors

```bash
# Verify SELinux context on volumes
ls -laZ ~/.local/share/containers/storage/volumes/

# Relabel if needed
podman volume rm colosseum-postgres-data
# Then re-run deploy.sh
```

### Out of memory errors

```bash
# Check container memory usage
podman stats colosseum-postgres

# Increase memory limit in .container file
Memory=4g  # or higher

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart colosseum-postgres.service
```

## Cleanup

To completely remove the deployment:

```bash
./cleanup.sh
```

This removes:
- PostgreSQL container
- Data volume (**WARNING: ALL DATA LOST**)
- Network configuration
- Quadlet systemd files
- Optionally: podman secrets

## References

- [Major Hayden's Quadlet Networking Blog](https://major.io/p/quadlet-networking/)
- [Major Hayden's Podman Auto-Update Blog](https://major.io/p/podman-quadlet-automatic-updates/)
- [Podman Quadlet Documentation](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

## Support

For issues or questions:
- GitHub Issues: https://github.com/davdunc/colosseum/issues
- Documentation: See main README.md

## License

See LICENSE file in the root of the repository.
